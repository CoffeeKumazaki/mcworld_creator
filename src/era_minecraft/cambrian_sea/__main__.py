"""CLI entry point: python -m era_minecraft.cambrian_sea"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ..utils import generate_regions
from .generator import generate_heightmaps, make_column


def main():
    parser = argparse.ArgumentParser(description="Cambrian Sea world generator")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--size", type=int, default=2048, help="World size in blocks (default: 2048)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    print(f"Cambrian Sea: size={args.size}, seed={args.seed}")
    print("Generating heightmaps...")

    floor_h, coral_dist, kelp_noise = generate_heightmaps(args.size, args.seed)
    half = args.size // 2

    def get_block_fn(x, z):
        ix = x + half
        iz = z + half
        return make_column(
            x, z,
            floor_h[iz, ix],
            coral_dist[iz, ix],
            kelp_noise[iz, ix],
            args.seed,
        )

    print("Generating regions...")
    generate_regions(args.size, get_block_fn, args.output)
    print(f"Done! World saved to {args.output}")


if __name__ == "__main__":
    main()
