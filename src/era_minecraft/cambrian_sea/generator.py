"""Cambrian Sea terrain generator.

Generates an ancient shallow sea with:
- Bedrock base (Y -64 to -62)
- Stone substrate (Y -62 to floor-10)
- Tapeats sandstone layer with trilobite fossils (Y floor-10 to floor)
- Water column (Y floor to sea_level) with kelp, seagrass, coral reefs
"""

import numpy as np
from ..noise import perlin_2d, worley_2d
from ..utils import coord_hash


# World parameters
SEA_LEVEL = 100
FLOOR_BASE = 40
FLOOR_AMPLITUDE = 40   # floor range: 40-80
SANDSTONE_DEPTH = 10

# Noise scales
FLOOR_SCALE = 0.004
CORAL_FREQUENCY = 0.06
KELP_SCALE = 0.015

# Sandstone block palette
SANDSTONE_BLOCKS = ["red_sandstone", "smooth_red_sandstone", "brown_terracotta"]
SANDSTONE_WEIGHTS = [50, 30, 20]  # percentages

# Fossil: trilobite embedded in sandstone
FOSSIL_BLOCK = "bone_block"
FOSSIL_CLUSTER_SIZE = 10
FOSSIL_CLUSTER_CHANCE = 40   # per-mille (4%)
FOSSIL_FILL_PCT = 30         # % of blocks within cluster

# Coral types
CORAL_BLOCKS = [
    "brain_coral_block",
    "bubble_coral_block",
    "fire_coral_block",
    "horn_coral_block",
    "tube_coral_block",
]

# Kelp parameters
KELP_ZONE_THRESHOLD = 0.6
KELP_MIN_HEIGHT = 5
KELP_MAX_HEIGHT = 20

# Seagrass density
SEAGRASS_CHANCE = 15  # percent


def generate_heightmaps(size, seed):
    """Pre-compute noise maps for the sea floor and features."""
    half = size // 2
    coords = np.arange(-half, half, dtype=np.float64)

    floor_noise = perlin_2d(
        coords * FLOOR_SCALE, coords * FLOOR_SCALE,
        seed=seed, octaves=4, persistence=0.5, lacunarity=2.0,
    )
    # Map [-1,1] -> [FLOOR_BASE, FLOOR_BASE + FLOOR_AMPLITUDE]
    floor_h = (floor_noise * 0.5 + 0.5) * FLOOR_AMPLITUDE + FLOOR_BASE

    coral_dist = worley_2d(
        coords, coords,
        seed=seed + 100, frequency=CORAL_FREQUENCY,
    )

    kelp_noise = perlin_2d(
        coords * KELP_SCALE, coords * KELP_SCALE,
        seed=seed + 200, octaves=2, persistence=0.5, lacunarity=2.0,
    )

    return floor_h, coral_dist, kelp_noise


def make_column(x, z, floor_h, coral_dist, kelp_val, seed):
    """Build block list for a single (x, z) column.

    Returns list of (y, block_id) or (y, block_id, properties) tuples.
    """
    floor_height = int(floor_h)
    sandstone_bottom = floor_height - SANDSTONE_DEPTH

    blocks = []

    # Bedrock
    for y in range(-64, -62):
        blocks.append((y, "bedrock"))

    # Stone substrate
    for y in range(-62, sandstone_bottom):
        blocks.append((y, "stone"))

    # Tapeats sandstone layer (with fossils)
    for y in range(sandstone_bottom, floor_height):
        block = _sandstone_block(x, y, z, seed)
        blocks.append((y, block))

    # Water column
    for y in range(floor_height, SEA_LEVEL):
        blocks.append((y, "water"))

    water_depth = SEA_LEVEL - floor_height
    if water_depth <= 0:
        return blocks

    # -- Underwater features (placed within the water column) --

    # Coral reefs: where Worley distance is small (cell centers)
    if coral_dist < 0.3 and water_depth > 5:
        coral_height = max(1, int((0.3 - coral_dist) * 20))
        coral_height = min(coral_height, water_depth - 2)
        h = coord_hash(x, 0, z, seed + 400)
        coral_type = CORAL_BLOCKS[h % len(CORAL_BLOCKS)]
        for y in range(floor_height, floor_height + coral_height):
            # Replace water with coral
            blocks.append((y, coral_type))

    # Kelp: in Perlin noise zones
    elif kelp_val > KELP_ZONE_THRESHOLD and water_depth > 8:
        h = coord_hash(x, 0, z, seed + 500)
        if h % 100 < 40:  # 40% chance within kelp zone
            kelp_h = KELP_MIN_HEIGHT + (h >> 8) % (KELP_MAX_HEIGHT - KELP_MIN_HEIGHT)
            kelp_h = min(kelp_h, water_depth - 2)
            # Kelp plant needs to grow from sea floor
            for y in range(floor_height, floor_height + kelp_h):
                age = 25 if y < floor_height + kelp_h - 1 else (h >> 16) % 26
                blocks.append((y, "kelp_plant", {"age": str(age)}))
            # Top kelp block
            if floor_height + kelp_h < SEA_LEVEL:
                blocks.append((floor_height + kelp_h, "kelp", {"age": str((h >> 16) % 26)}))

    # Seagrass: sparse on the sea floor
    elif coord_hash(x, 0, z, seed + 600) % 100 < SEAGRASS_CHANCE:
        h = coord_hash(x, 1, z, seed + 600)
        if h % 100 < 30 and water_depth > 3:
            # Tall seagrass
            blocks.append((floor_height, "tall_seagrass", {"half": "lower"}))
            blocks.append((floor_height + 1, "tall_seagrass", {"half": "upper"}))
        else:
            blocks.append((floor_height, "seagrass"))

    return blocks


def _sandstone_block(x, y, z, seed):
    """Select sandstone block, with fossil chance."""
    # Fossil cluster check
    cx = x // FOSSIL_CLUSTER_SIZE
    cy = y // FOSSIL_CLUSTER_SIZE
    cz = z // FOSSIL_CLUSTER_SIZE
    cell_h = coord_hash(cx, cy, cz, seed=700)
    if (cell_h % 1000) < FOSSIL_CLUSTER_CHANCE:
        block_h = coord_hash(x, y, z, seed=800)
        if (block_h % 100) < FOSSIL_FILL_PCT:
            return FOSSIL_BLOCK

    # Normal sandstone selection
    h = coord_hash(x, y, z, seed + 50)
    threshold = h % 100
    if threshold < SANDSTONE_WEIGHTS[0]:
        return SANDSTONE_BLOCKS[0]
    elif threshold < SANDSTONE_WEIGHTS[0] + SANDSTONE_WEIGHTS[1]:
        return SANDSTONE_BLOCKS[1]
    else:
        return SANDSTONE_BLOCKS[2]
