import argparse
import logging
from pathlib import Path

from plateau2minecraft.merge_points import merge
from plateau2minecraft.voxelizer import voxelize as voxelize_shell

from model2minecraft.converter import Minecraft
from model2minecraft.loader import load_mesh
from model2minecraft.voxelizer import voxelize_solid

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="3Dモデル（.obj/.stl/.ply/.glb など）から Minecraft ワールド(.mca)を生成する"
    )
    parser.add_argument("--target", required=True, type=Path, nargs="+", help="入力3Dモデルファイル（複数可）")
    parser.add_argument("--output", required=True, type=Path, help="出力フォルダ")
    parser.add_argument("--target-size", type=int, default=256, help="最長辺のブロック数（自動スケール）")
    parser.add_argument("--block", default="minecraft:stone", help="ボクセルに使うブロック（例: minecraft:deepslate）")
    parser.add_argument(
        "--base-y",
        type=int,
        default=128,
        help="モデルを配置する垂直中心Y（既定128: 高さ範囲[-64,319]の中央に収める）",
    )
    parser.add_argument("--up-axis", choices=["y", "z"], default="y", help="モデルの上方向軸")
    parser.add_argument("--hollow", action="store_true", help="中身を詰めず殻だけにする")
    args = parser.parse_args()

    point_cloud_list = []
    for file_path in args.target:
        logging.info("Loading: %s", file_path)
        mesh = load_mesh(file_path, args.target_size, args.up_axis)

        logging.info("Voxelizing (%s): %s", "hollow" if args.hollow else "solid", file_path)
        point_cloud = voxelize_shell(mesh) if args.hollow else voxelize_solid(mesh)
        point_cloud_list.append(point_cloud)

    merged = point_cloud_list[0] if len(point_cloud_list) == 1 else merge(point_cloud_list)

    logging.info("Building region: %s", args.output)
    Minecraft(merged, block=args.block, base_y=args.base_y).build_region(args.output)
    logging.info("Done.")
