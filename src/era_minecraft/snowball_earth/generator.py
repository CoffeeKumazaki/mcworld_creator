"""Snowball Earth terrain generator.

Generation pipeline:
1. Smooth base terrain (low bedrock)
2. Massive ice sheet (150-200 blocks)
3. Frozen sea with thick sea ice
4. Voronoi cracks + ice ridges along cell boundaries
5. Polyline crevasses (realistic ~40m depth)
6. Snow plain surface
7. Nunataks (exposed rock peaks)
8. Glacial U-valleys carved into bedrock
9. Moraine bands (rock/gravel strips on ice surface)
"""

import numpy as np
from ..noise import perlin_2d, worley_2d_edge
from ..utils import coord_hash

# ── 1. Base terrain ──
TERRAIN_BASE = -40
TERRAIN_AMPLITUDE = 20       # Y -40 to -20
TERRAIN_SCALE = 0.001

# ── 2. Ice sheet ──
ICE_SHEET_MIN = 150
ICE_SHEET_MAX = 200
ICE_SCALE = 0.002

# ── 3. Sea ice ──
FROZEN_SEA_LEVEL = -30
SEA_ICE_THICKNESS = 150

# ── 4. Voronoi cracks & ridges ──
VORONOI_FREQ = 0.006
CRACK_THRESHOLD = 0.015      # narrow cracks (2-4 blocks wide)
RIDGE_BAND = 0.05            # ridge surface texture band

# ── 5. Polyline crevasses ──
NUM_CREVASSES = 4
CREVASSE_HALF_WIDTH = 1
CREVASSE_DEPTH = 35
CREVASSE_TAPER_RADIUS = 2    # very steep walls
CREVASSE_POINTS = 5
CREVASSE_SEGMENT_LEN = 100

# ── 7. Nunataks ──
NUNATAK_CELL = 200
NUNATAK_CHANCE = 6           # percent of cells
NUNATAK_RADIUS = 8

# ── 8. Glacial valleys ──
VALLEY_SCALE = 0.003
VALLEY_THRESHOLD = 0.6       # noise > this = valley zone
VALLEY_DEPTH = 30            # extra depth carved into bedrock

# ── 9. Moraine bands ──
MORAINE_SCALE = 0.015
MORAINE_THRESHOLD = 0.7      # directional noise > this = moraine


def generate_heightmaps(size, seed):
    """Pre-compute all 2D noise maps."""
    half = size // 2
    coords = np.arange(-half, half, dtype=np.float64)

    # 1. Smooth base terrain
    terrain_h = perlin_2d(
        coords * TERRAIN_SCALE, coords * TERRAIN_SCALE,
        seed=seed, octaves=1,
    )
    terrain_h = (terrain_h * 0.5 + 0.5) * TERRAIN_AMPLITUDE + TERRAIN_BASE

    # 2. Ice thickness variation
    ice_noise = perlin_2d(
        coords * ICE_SCALE, coords * ICE_SCALE,
        seed=seed + 100, octaves=1,
    )
    ice_thickness = (ice_noise * 0.5 + 0.5) * (ICE_SHEET_MAX - ICE_SHEET_MIN) + ICE_SHEET_MIN

    # 4. Voronoi edge distance
    voronoi_edge = worley_2d_edge(coords, coords, seed=seed + 300, frequency=VORONOI_FREQ)

    # 8. Glacial valley noise (elongated in one direction)
    valley_noise = perlin_2d(
        coords * VALLEY_SCALE * 0.5,   # stretched along x
        coords * VALLEY_SCALE * 2.0,   # compressed along z -> linear valleys
        seed=seed + 600, octaves=1,
    )

    # 9. Moraine noise (directional bands)
    moraine_noise = perlin_2d(
        coords * MORAINE_SCALE * 0.3,  # stretched -> long parallel bands
        coords * MORAINE_SCALE * 3.0,
        seed=seed + 700, octaves=1,
    )

    # 5. Polyline crevasses
    crevasse_segments = _generate_crevasse_polylines(size, seed + 500)

    return (terrain_h, ice_thickness, voronoi_edge,
            valley_noise, moraine_noise, crevasse_segments)


def _generate_crevasse_polylines(size, seed):
    """Generate random polyline crevasses."""
    half = size // 2
    rng = np.random.default_rng(seed)
    segments = []
    for _ in range(NUM_CREVASSES):
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
    dx = x2 - x1
    dz = z2 - z1
    len_sq = dx * dx + dz * dz
    if len_sq < 1e-6:
        return (px - x1) ** 2 + (pz - z1) ** 2
    t = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / len_sq))
    proj_x = x1 + t * dx
    proj_z = z1 + t * dz
    return (px - proj_x) ** 2 + (pz - proj_z) ** 2


def make_column(x, z, terrain_h, ice_thick, voronoi_edge_val,
                valley_val, moraine_val, crevasse_segments, seed):
    """Build block list for a single (x, z) column."""
    terrain_f = float(terrain_h)
    ice_f = float(ice_thick)

    # ── 8. Glacial valley: carve bedrock deeper ──
    if valley_val > VALLEY_THRESHOLD:
        valley_factor = (valley_val - VALLEY_THRESHOLD) / (1.0 - VALLEY_THRESHOLD)
        terrain_f -= VALLEY_DEPTH * valley_factor

    terrain_height = round(terrain_f)
    is_sea = terrain_f < FROZEN_SEA_LEVEL

    blocks = []

    # ── 7. Nunatak check ──
    nunatak = _is_nunatak(x, z, seed)

    # ── Bedrock ──
    for y in range(-64, -62):
        blocks.append((y, "bedrock"))

    # ── Rock fill ──
    for y in range(-62, terrain_height):
        blocks.append((y, _rock_block(x, y, z)))

    # ── 7. Nunatak: exposed rock peak piercing through ice ──
    if nunatak and not is_sea:
        dist = _nunatak_dist(x, z, seed)
        if dist <= NUNATAK_RADIUS:
            # Rock peak rises above ice surface
            ice_surface = round(terrain_f + ice_f)
            peak_extra = max(0, round((NUNATAK_RADIUS - dist) * 3.0))
            peak_top = min(ice_surface + peak_extra, 319)
            for y in range(terrain_height, peak_top):
                blocks.append((y, _nunatak_block(x, y, z)))
            if coord_hash(x, 0, z, seed + 770) % 100 < 40:
                blocks.append((peak_top, "gravel"))
            return blocks

    # ── 2+3. Ice sheet (unified: land and sea use same ice_top) ──
    if is_sea:
        for y in range(terrain_height, FROZEN_SEA_LEVEL):
            blocks.append((y, "water"))
        ice_bottom_f = float(FROZEN_SEA_LEVEL)
    else:
        ice_bottom_f = terrain_f
    # Ice top is always terrain + ice_thickness (continuous across sea/land)
    ice_top_f = terrain_f + ice_f

    # ── Compute crevasse depth (vertical slit from surface down) ──
    crevasse_depth = 0.0

    # 4. Voronoi cracks
    if voronoi_edge_val < CRACK_THRESHOLD:
        t = voronoi_edge_val / CRACK_THRESHOLD  # 0=center, 1=edge
        crevasse_depth = max(crevasse_depth, CREVASSE_DEPTH * (1.0 - t))

    # 5. Polyline crevasses
    taper_r_sq = CREVASSE_TAPER_RADIUS ** 2
    for seg in crevasse_segments:
        d_sq = _point_to_segment_dist_sq(float(x), float(z), *seg)
        if d_sq < taper_r_sq:
            dist = d_sq ** 0.5
            t = dist / CREVASSE_TAPER_RADIUS
            crevasse_depth = max(crevasse_depth, CREVASSE_DEPTH * (1.0 - t))

    # ── Single round ──
    ice_bottom = round(ice_bottom_f) if is_sea else terrain_height
    ice_top = min(round(ice_top_f), 319)

    # ── Place ice blocks, with vertical slit carved from top ──
    crevasse_bottom = max(ice_bottom, ice_top - round(crevasse_depth))
    has_crevasse = crevasse_depth > 1.0

    for y in range(ice_bottom, ice_top):
        if has_crevasse and y >= crevasse_bottom:
            pass  # air: don't place block (vertical slit)
        else:
            blocks.append((y, _ice_block(y, ice_bottom, ice_top)))

    # ── 6. Snow surface ──
    is_ridge = CRACK_THRESHOLD <= voronoi_edge_val < RIDGE_BAND
    if has_crevasse:
        pass  # no snow on open crevasse
    elif is_ridge:
        # Ridge: surface texture only
        h = coord_hash(x, 0, z, seed + 450)
        blocks.append((min(ice_top, 319), "packed_ice" if h % 100 < 60 else "blue_ice"))
    elif moraine_val > MORAINE_THRESHOLD:
        moraine_factor = (moraine_val - MORAINE_THRESHOLD) / (1.0 - MORAINE_THRESHOLD)
        h = coord_hash(x, 0, z, seed + 800)
        if moraine_factor > 0.5:
            blocks.append((min(ice_top, 319), "gravel" if h % 100 < 60 else "cobblestone"))
        else:
            blocks.append((min(ice_top, 319), "snow_block"))
            if h % 100 < 30:
                blocks.append((min(ice_top + 1, 319), "gravel"))
    else:
        blocks.append((min(ice_top, 319), "snow_block"))
        blocks.append((min(ice_top + 1, 319), "snow_block"))

    return blocks


# ── Rock blocks ──

def _rock_block(x, y, z):
    if y < -50:
        h = coord_hash(x, y, z, seed=10)
        return "deepslate" if h % 100 < 75 else "tuff"
    else:
        h = coord_hash(x, y, z, seed=15)
        return "deepslate" if h % 100 < 40 else "blackstone"


def _nunatak_block(x, y, z):
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
    if progress < 0.6:
        return "blue_ice"
    elif progress < 0.85:
        return "packed_ice"
    else:
        return "ice"


# ── Feature placement ──

def _grid_feature(x, z, seed, cell_size, chance_pct):
    cx = x // cell_size
    cz = z // cell_size
    h = coord_hash(cx, 0, cz, seed)
    return (h % 100) < chance_pct


def _grid_center(x, z, seed, cell_size):
    cx = x // cell_size
    cz = z // cell_size
    h = coord_hash(cx, 0, cz, seed + 1)
    h2 = coord_hash(cx, 0, cz, seed + 2)
    fx = cx * cell_size + (h % cell_size)
    fz = cz * cell_size + (h2 % cell_size)
    return int(((x - fx) ** 2 + (z - fz) ** 2) ** 0.5)


def _is_nunatak(x, z, seed):
    return _grid_feature(x, z, seed + 700, NUNATAK_CELL, NUNATAK_CHANCE)

def _nunatak_dist(x, z, seed):
    return _grid_center(x, z, seed + 700, NUNATAK_CELL)
