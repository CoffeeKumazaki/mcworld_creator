"""Shared utilities for era_minecraft world generators."""

import os
from . import anvil


def coord_hash(x: int, y: int, z: int, seed: int = 0) -> int:
    """FNV-1a inspired hash for coordinate-based deterministic noise."""
    h = 2166136261 ^ seed
    h = ((h ^ (x & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    h = ((h ^ (y & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    h = ((h ^ (z & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    h = ((h ^ ((x >> 16) & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    return h


class BlockCache:
    """Lazy cache for anvil.Block objects to avoid repeated instantiation."""

    def __init__(self):
        self._cache: dict[str, anvil.Block] = {}

    def get(self, block_id: str, properties: dict = None) -> anvil.Block:
        key = block_id if properties is None else f"{block_id}|{sorted(properties.items())}"
        if key not in self._cache:
            self._cache[key] = anvil.Block("minecraft", block_id, properties=properties)
        return self._cache[key]


def generate_regions(size: int, get_block_fn, output_path: str):
    """Generate .mca region files by iterating over a size x size block area.

    The world is centered at (0,0). For each block (x, z), get_block_fn(x, z)
    is called and must return a list of (y, block_id_str) or (y, block_id_str, properties_dict)
    tuples representing blocks to place in that column.

    Parameters
    ----------
    size : int
        World size in blocks (square). Centered at origin.
    get_block_fn : callable(x, z) -> list of tuples
        Returns column data for the given x, z.
    output_path : str
        Output directory; region/ subdirectory is created automatically.
    """
    region_dir = os.path.join(output_path, "region")
    os.makedirs(region_dir, exist_ok=True)

    half = size // 2
    cache = BlockCache()

    # Determine which regions we need
    min_rx = (-half) // 512
    max_rx = (half - 1) // 512
    min_rz = (-half) // 512
    max_rz = (half - 1) // 512

    total_regions = (max_rx - min_rx + 1) * (max_rz - min_rz + 1)
    done = 0

    for rx in range(min_rx, max_rx + 1):
        for rz in range(min_rz, max_rz + 1):
            region = anvil.EmptyRegion(rx, rz)
            region_x_start = rx * 512
            region_z_start = rz * 512

            for bx in range(region_x_start, region_x_start + 512):
                if bx < -half or bx >= half:
                    continue
                for bz in range(region_z_start, region_z_start + 512):
                    if bz < -half or bz >= half:
                        continue

                    column = get_block_fn(bx, bz)
                    for entry in column:
                        if len(entry) == 2:
                            y, block_id = entry
                            props = None
                        else:
                            y, block_id, props = entry
                        if -64 <= y <= 319:
                            region.set_block(cache.get(block_id, props), bx, y, bz)

            fname = os.path.join(region_dir, f"r.{rx}.{rz}.mca")
            region.save(fname)
            done += 1
            print(f"\r  Region {done}/{total_regions}: r.{rx}.{rz}.mca", end="", flush=True)

    print()
