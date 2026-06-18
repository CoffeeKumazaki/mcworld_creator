import argparse
import logging
from pathlib import Path

from plateau2minecraft.merge_points import merge
from plateau2minecraft.voxelizer import voxelize as voxelize_shell

from model2minecraft import terrain
from model2minecraft.converter import Minecraft
from model2minecraft.heightmap import mesh_to_heightmap
from model2minecraft.loader import load_mesh
from model2minecraft.voxelizer import voxelize_solid

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_solid(args) -> None:
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


def run_terrain(args) -> None:
    if len(args.target) > 1:
        logging.warning("terrain モードは単一モデルのみ対応。最初の %s を使用します。", args.target[0])
    file_path = args.target[0]

    logging.info("Loading: %s", file_path)
    mesh = load_mesh(file_path, target_size=None, up_axis=args.up_axis)

    map_h = args.height if args.height is not None else args.width // 2
    logging.info("Heightmap (%dx%d) を生成", args.width, map_h)
    hm = mesh_to_heightmap(mesh, args.width, map_h)

    logging.info("Building terrain region: %s", args.output)
    terrain.build(
        hm,
        args.output,
        relief=args.relief,
        floor_y=args.floor_y,
        surface_block=args.surface_block,
        body_block=args.body_block,
        jobs=args.jobs,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="3Dモデル（.obj/.stl/.ply/.glb など）から Minecraft ワールド(.mca)を生成する"
    )
    parser.add_argument("--target", required=True, type=Path, nargs="+", help="入力3Dモデルファイル（複数可）")
    parser.add_argument("--output", required=True, type=Path, help="出力フォルダ")
    parser.add_argument(
        "--mode",
        choices=["solid", "terrain"],
        default="solid",
        help="solid: 形そのものをボクセル化 / terrain: 中心からの距離を高さにした地形に展開",
    )
    parser.add_argument("--up-axis", choices=["y", "z"], default="y", help="モデルの上方向軸（terrainの極軸）")

    # --- solid モード ---
    solid = parser.add_argument_group("solid モード")
    solid.add_argument("--target-size", type=int, default=256, help="最長辺のブロック数（自動スケール）")
    solid.add_argument("--block", default="minecraft:stone", help="ボクセルに使うブロック")
    solid.add_argument(
        "--base-y",
        type=int,
        default=128,
        help="モデルを配置する垂直中心Y（既定128: 高さ範囲[-64,319]の中央に収める）",
    )
    solid.add_argument("--hollow", action="store_true", help="中身を詰めず殻だけにする")

    # --- terrain モード ---
    terr = parser.add_argument_group("terrain モード")
    terr.add_argument("--width", type=int, default=1024, help="地形マップの幅（経度方向ブロック数）")
    terr.add_argument("--height", type=int, default=None, help="地形マップの高さ（既定: width//2）")
    terr.add_argument("--relief", type=int, default=200, help="起伏の振幅（ブロック）")
    terr.add_argument("--floor-y", type=int, default=-50, help="起伏の最下面Y")
    terr.add_argument("--surface-block", default="minecraft:gravel", help="地表のブロック")
    terr.add_argument("--body-block", default="minecraft:deepslate", help="本体（地中）のブロック")
    terr.add_argument("--jobs", type=int, default=None, help="並列ワーカー数（既定: CPU数）")

    args = parser.parse_args()

    if args.mode == "terrain":
        run_terrain(args)
    else:
        run_solid(args)
    logging.info("Done.")
