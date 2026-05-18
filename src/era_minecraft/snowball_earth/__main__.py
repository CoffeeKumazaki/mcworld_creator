"""CLI entry point: python -m era_minecraft.snowball_earth"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ..utils import generate_regions
from .generator import generate_heightmaps, make_column


def main():
    parser = argparse.ArgumentParser(description="Snowball Earth world generator")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--size", type=int, default=2048, help="World size in blocks (default: 2048)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    print(f"Snowball Earth: size={args.size}, seed={args.seed}")
    print("Generating heightmaps...")

    terrain_h, ice_thickness, voronoi_edge, wind_noise, crevasse_segments = \
        generate_heightmaps(args.size, args.seed)
    half = args.size // 2

    def get_block_fn(x, z):
        ix = x + half
        iz = z + half
        return make_column(
            x, z,
            terrain_h[iz, ix],
            ice_thickness[iz, ix],
            voronoi_edge[iz, ix],
            wind_noise[iz, ix],
            crevasse_segments,
            args.seed,
        )

    print("Generating regions...")
    generate_regions(args.size, get_block_fn, args.output)
    print(f"Done! World saved to {args.output}")


if __name__ == "__main__":
    main()
