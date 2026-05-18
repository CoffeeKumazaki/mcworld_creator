"""Snowball Earth terrain generator.

7-layer generation pipeline:
1. Smooth base terrain (low-octave fBm)
2. Thick ice sheet over land
3. Sea ice over ocean areas
4. Voronoi ice cracks (F2-F1) & pressure ridges along cell boundaries
5. Random polyline crevasses carved into the ice
6. Wind-aligned snow streaks on the surface
7. Nunataks (exposed rock), moulins (ice holes), sample collection points
"""

import numpy as np
from ..noise import perlin_2d, worley_2d_edge
from ..utils import coord_hash

# ── 1. Base terrain ──
TERRAIN_BASE = 80
TERRAIN_AMPLITUDE = 25
TERRAIN_SCALE = 0.0015

# ── 2. Ice sheet ──
ICE_SHEET_MIN = 15
ICE_SHEET_MAX = 40
ICE_SCALE = 0.004

# ── 3. Sea ice ──
FROZEN_SEA_LEVEL = 90
SEA_ICE_THICKNESS = 6

# ── 4. Voronoi cracks & pressure ridges ──
VORONOI_FREQ = 0.012          # cell size ~83 blocks
CRACK_THRESHOLD = 0.08        # F2-F1 below this = crack
RIDGE_LOW = 0.08
RIDGE_HIGH = 0.15             # F2-F1 in this band = pressure ridge
RIDGE_HEIGHT = 3              # extra blocks piled up at ridges

# ── 5. Polyline crevasses ──
NUM_CREVASSES = 12
CREVASSE_HALF_WIDTH = 2
CREVASSE_DEPTH = 8
CREVASSE_POINTS = 6           # vertices per polyline
CREVASSE_SEGMENT_LEN = 80

# ── 6. Wind streaks ──
WIND_ANGLE = 0.3              # radians from +X axis
WIND_SCALE = 0.025
WIND_THRESHOLD = 0.55         # above this -> extra snow layer

# ── 7. Nunataks, moulins, sample points ──
NUNATAK_CELL = 120            # grid cell for nunatak check
NUNATAK_CHANCE = 8            # percent of cells
NUNATAK_RADIUS = 6
MOULIN_CELL = 60
MOULIN_CHANCE = 3
MOULIN_RADIUS = 2
SAMPLE_CELL = 200
SAMPLE_CHANCE = 5


def generate_heightmaps(size, seed):
    """Pre-compute all 2D noise maps."""
    half = size // 2
    coords = np.arange(-half, half, dtype=np.float64)

    # 1. Smooth base terrain
    terrain_h = perlin_2d(
        coords * TERRAIN_SCALE, coords * TERRAIN_SCALE,
        seed=seed, octaves=3, persistence=0.35, lacunarity=2.0,
    )
    terrain_h = (terrain_h * 0.5 + 0.5) * TERRAIN_AMPLITUDE + TERRAIN_BASE

    # 2. Ice thickness variation
    ice_noise = perlin_2d(
        coords * ICE_SCALE, coords * ICE_SCALE,
        seed=seed + 100, octaves=2, persistence=0.4, lacunarity=2.0,
    )
    ice_thickness = (ice_noise * 0.5 + 0.5) * (ICE_SHEET_MAX - ICE_SHEET_MIN) + ICE_SHEET_MIN

    # 4. Voronoi edge distance (F2-F1)
    voronoi_edge = worley_2d_edge(coords, coords, seed=seed + 300, frequency=VORONOI_FREQ)

    # 6. Wind streak noise (directional Perlin)
    cx = np.cos(WIND_ANGLE)
    cz = np.sin(WIND_ANGLE)
    wind_coords_x = coords * WIND_SCALE * cx
    wind_coords_z = coords * WIND_SCALE * cz * 3.0  # stretch perpendicular to wind
    wind_noise = perlin_2d(
        wind_coords_x, wind_coords_z,
        seed=seed + 400, octaves=2, persistence=0.5, lacunarity=2.0,
    )

    # 5. Pre-generate polyline crevasses as a set of line segments
    crevasse_segments = _generate_crevasse_polylines(size, seed + 500)

    return terrain_h, ice_thickness, voronoi_edge, wind_noise, crevasse_segments


def _generate_crevasse_polylines(size, seed):
    """Generate random polyline crevasses. Returns list of (x1,z1,x2,z2) segments."""
    half = size // 2
    rng = np.random.default_rng(seed)
    segments = []
    for _ in range(NUM_CREVASSES):
        # Random start point
        px = rng.uniform(-half * 0.8, half * 0.8)
        pz = rng.uniform(-half * 0.8, half * 0.8)
        angle = rng.uniform(0, 2 * np.pi)
        for _ in range(CREVASSE_POINTS - 1):
            angle += rng.uniform(-0.6, 0.6)
            length = rng.uniform(CREVASSE_SEGMENT_LEN * 0.5, CREVASSE_SEGMENT_LEN * 1.5)
            nx = px + np.cos(angle) * length
            nz = pz + np.sin(angle) * length
            segments.append((px, pz, nx, nz))
            px, pz = nx, nz
    return segments


def _point_to_segment_dist_sq(px, pz, x1, z1, x2, z2):
    """Squared distance from point (px,pz) to segment (x1,z1)-(x2,z2)."""
    dx = x2 - x1
    dz = z2 - z1
    len_sq = dx * dx + dz * dz
    if len_sq < 1e-6:
        return (px - x1) ** 2 + (pz - z1) ** 2
    t = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / len_sq))
    proj_x = x1 + t * dx
    proj_z = z1 + t * dz
    return (px - proj_x) ** 2 + (pz - proj_z) ** 2


def make_column(x, z, terrain_h, ice_thick, voronoi_edge_val, wind_val,
                crevasse_segments, seed):
    """Build block list for a single (x, z) column."""
    terrain_height = int(terrain_h)
    base_ice = int(ice_thick)
    is_sea = terrain_height < FROZEN_SEA_LEVEL

    blocks = []

    # ── 7. Check special features ──
    nunatak = _is_nunatak(x, z, seed)
    moulin = _is_moulin(x, z, seed)
    sample_point = _is_sample_point(x, z, seed)

    # ── Bedrock ──
    for y in range(-64, -62):
        blocks.append((y, "bedrock"))

    # ── Rock fill ──
    rock_top = terrain_height if not is_sea else terrain_height
    for y in range(-62, rock_top):
        blocks.append((y, _rock_block(x, y, z)))

    # ── 7a. Nunatak: exposed rock peak, no ice ──
    if nunatak and not is_sea:
        dist = _nunatak_dist(x, z, seed)
        if dist <= NUNATAK_RADIUS:
            peak_extra = max(0, int((NUNATAK_RADIUS - dist) * 2.5))
            for y in range(rock_top, min(rock_top + peak_extra, 320)):
                blocks.append((y, _nunatak_block(x, y, z)))
            # Sparse gravel on top
            if peak_extra > 0 and coord_hash(x, 0, z, seed + 770) % 100 < 40:
                blocks.append((min(rock_top + peak_extra, 319), "gravel"))
            return blocks

    # ── 3. Sea: water + sea ice ──
    if is_sea:
        for y in range(terrain_height, FROZEN_SEA_LEVEL):
            blocks.append((y, "water"))
        ice_bottom = FROZEN_SEA_LEVEL
        ice_top = FROZEN_SEA_LEVEL + SEA_ICE_THICKNESS
    else:
        # ── 2. Land ice sheet ──
        ice_bottom = terrain_height
        ice_top = terrain_height + base_ice

    # ── 4. Voronoi: cracks reduce ice, ridges add height ──
    if voronoi_edge_val < CRACK_THRESHOLD:
        # Crack: deep cut through ice
        crack_depth = int((1.0 - voronoi_edge_val / CRACK_THRESHOLD) * CREVASSE_DEPTH)
        ice_top = max(ice_bottom + 1, ice_top - crack_depth)
    elif RIDGE_LOW <= voronoi_edge_val <= RIDGE_HIGH:
        # Pressure ridge: piled ice blocks
        ridge_factor = 1.0 - abs(voronoi_edge_val - (RIDGE_LOW + RIDGE_HIGH) / 2) / ((RIDGE_HIGH - RIDGE_LOW) / 2)
        ice_top += int(RIDGE_HEIGHT * ridge_factor)

    # ── 5. Polyline crevasses ──
    crevasse_cut = 0
    hw_sq = CREVASSE_HALF_WIDTH ** 2
    for seg in crevasse_segments:
        d_sq = _point_to_segment_dist_sq(float(x), float(z), *seg)
        if d_sq < hw_sq * 9:  # within 3x half-width for tapering
            closeness = 1.0 - (d_sq / (hw_sq * 9)) ** 0.5
            cut = int(closeness * CREVASSE_DEPTH)
            crevasse_cut = max(crevasse_cut, cut)
    if crevasse_cut > 0:
        ice_top = max(ice_bottom + 1, ice_top - crevasse_cut)

    # ── 7b. Moulin: vertical hole through ice ──
    if moulin:
        mdist = _moulin_dist(x, z, seed)
        if mdist <= MOULIN_RADIUS:
            # Only place a thin ring of ice, interior is air/water
            if mdist == MOULIN_RADIUS:
                for y in range(ice_bottom, min(ice_top, 320)):
                    blocks.append((y, "blue_ice"))
            # else: leave as air (no ice blocks)
            return blocks

    # ── Place ice blocks ──
    ice_top = min(ice_top, 319)
    for y in range(ice_bottom, ice_top):
        blocks.append((y, _ice_block(y, ice_bottom, ice_top)))

    # ── 6. Wind streaks + snow cap ──
    is_crack = voronoi_edge_val < CRACK_THRESHOLD
    is_deep_crevasse = crevasse_cut > CREVASSE_DEPTH // 2
    if not is_crack and not is_deep_crevasse:
        snow_depth = _snow_depth(x, z, seed)
        if wind_val > WIND_THRESHOLD:
            snow_depth += 1  # wind-deposited extra snow
        # Wind erosion on exposed ridges
        if voronoi_edge_val > RIDGE_HIGH and wind_val < -0.3:
            snow_depth = max(0, snow_depth - 1)
        for y in range(ice_top, min(ice_top + snow_depth, 320)):
            blocks.append((y, "snow_block"))

    # ── 7c. Sample collection point ──
    if sample_point and not is_sea:
        sdist = _sample_dist(x, z, seed)
        if sdist <= 2:
            top_y = ice_top + _snow_depth(x, z, seed)
            top_y = min(top_y, 319)
            # Place markers: lantern + banner
            if sdist == 0:
                blocks.append((top_y, "sea_lantern"))
            elif sdist <= 1:
                blocks.append((top_y, "cyan_stained_glass"))

    return blocks


# ── Rock blocks ──

def _rock_block(x, y, z):
    if y < 20:
        h = coord_hash(x, y, z, seed=10)
        return "deepslate" if h % 100 < 75 else "tuff"
    elif y < 50:
        h = coord_hash(x, y, z, seed=15)
        return "deepslate" if h % 100 < 40 else "blackstone"
    else:
        diagonal = (x + 2 * y + z) % 14
        if diagonal < 5:
            return "blackstone"
        elif diagonal < 8:
            return "basalt"
        else:
            h = coord_hash(x, y, z, seed=20)
            return "basalt" if h % 100 < 55 else "blackstone"


def _nunatak_block(x, y, z):
    """Exposed rock at nunataks — dark, weathered stone."""
    h = coord_hash(x, y, z, seed=750)
    if h % 100 < 50:
        return "blackstone"
    elif h % 100 < 80:
        return "basalt"
    else:
        return "gravel"


# ── Ice blocks ──

def _ice_block(y, ice_bottom, ice_top):
    thickness = ice_top - ice_bottom
    if thickness <= 0:
        return "ice"
    progress = (y - ice_bottom) / thickness
    if progress < 0.5:
        return "blue_ice"
    elif progress < 0.8:
        return "packed_ice"
    else:
        return "ice"


def _snow_depth(x, z, seed):
    h = coord_hash(x, 0, z, seed + 300)
    return (h % 3) + 1


# ── Feature placement helpers ──

def _grid_feature(x, z, seed, cell_size, chance_pct):
    """Check if (x,z) is in a cell that has a feature."""
    cx = x // cell_size
    cz = z // cell_size
    h = coord_hash(cx, 0, cz, seed)
    return (h % 100) < chance_pct


def _grid_center(x, z, seed, cell_size):
    """Return distance from (x,z) to the center of its grid cell feature point."""
    cx = x // cell_size
    cz = z // cell_size
    h = coord_hash(cx, 0, cz, seed + 1)
    h2 = coord_hash(cx, 0, cz, seed + 2)
    # Feature point within cell
    fx = cx * cell_size + (h % cell_size)
    fz = cz * cell_size + (h2 % cell_size)
    return int(((x - fx) ** 2 + (z - fz) ** 2) ** 0.5)


def _is_nunatak(x, z, seed):
    return _grid_feature(x, z, seed + 700, NUNATAK_CELL, NUNATAK_CHANCE)

def _nunatak_dist(x, z, seed):
    return _grid_center(x, z, seed + 700, NUNATAK_CELL)

def _is_moulin(x, z, seed):
    return _grid_feature(x, z, seed + 710, MOULIN_CELL, MOULIN_CHANCE)

def _moulin_dist(x, z, seed):
    return _grid_center(x, z, seed + 710, MOULIN_CELL)

def _is_sample_point(x, z, seed):
    return _grid_feature(x, z, seed + 720, SAMPLE_CELL, SAMPLE_CHANCE)

def _sample_dist(x, z, seed):
    return _grid_center(x, z, seed + 720, SAMPLE_CELL)
