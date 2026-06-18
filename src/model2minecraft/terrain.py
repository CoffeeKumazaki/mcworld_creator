import logging
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from plateau2minecraft.anvil import Block, EmptyRegion

WORLD_MIN_Y = -64
WORLD_MAX_Y = 319
BLOCK_SIZE = 512
BEDROCK_TOP = -62  # 岩盤は -64, -63 の2層（-64 <= i < -62）
SURFACE_LAYERS = 3  # 地表（砂利）の層数

# 領域並列ワーカーの read-only 共有コンテキスト（spawn の再import後に initializer で設定）
_CTX: dict = {}


def _worker_init(ctx: dict) -> None:
    global _CTX
    _CTX = ctx


def _build_one_region(task: tuple) -> str:
    """1領域を構築して保存する。トップレベル関数（spawn の pickle 対応）。"""
    region_x, region_z, cols, region_path = task

    bedrock = Block.from_name(_CTX["bedrock"])
    body = Block.from_name(_CTX["body"])
    surface = Block.from_name(_CTX["surface"])

    region = EmptyRegion(region_x, region_z)
    for gx, gz, y in cols:
        # 地表 y から下へ: 砂利(上 SURFACE_LAYERS 層) → 深層岩 → 岩盤(最下2層)
        surface_bottom = max(BEDROCK_TOP, y - SURFACE_LAYERS + 1)
        for i in range(WORLD_MIN_Y, y + 1):
            if i < BEDROCK_TOP:
                block = bedrock
            elif i >= surface_bottom:
                block = surface
            else:
                block = body
            region.set_if_inside(block, gx, i, gz)

    region.save(region_path)
    return region_path


def build(
    heightmap: np.ndarray,
    output: Path,
    relief: int,
    floor_y: int,
    surface_block: str = "minecraft:gravel",
    body_block: str = "minecraft:deepslate",
    bedrock_block: str = "minecraft:bedrock",
    jobs: int | None = None,
) -> None:
    """半径ハイトマップから地形 .mca を生成する。

    Parameters
    ----------
    heightmap
        (H, W) の半径2D配列（heightmap.mesh_to_heightmap の出力）。
    output
        出力フォルダ。``{output}/world_data/region/`` に .mca を書き出す。
    relief
        起伏の振幅（ブロック）。半径 min→floor_y、max→floor_y+relief にストレッチ。
    floor_y
        起伏の最下面 Y。
    surface_block / body_block / bedrock_block
        地表 / 本体 / 最下層のブロック名。
    jobs
        並列ワーカー数（None で既定= CPU 数）。
    """
    if relief < 0:
        raise ValueError(f"relief は 0 以上である必要があります: {relief}")

    h, w = heightmap.shape
    r = heightmap.astype(float)
    r_min, r_max = float(r.min()), float(r.max())
    if r_max > r_min:
        norm = (r - r_min) / (r_max - r_min)
    else:
        norm = np.zeros_like(r)

    # 半径 → Minecraft Y（ストレッチ）
    y_grid = np.floor(floor_y + norm * relief).astype(int)

    # 実際の Y 分布で範囲外判定（floor_y/relief だけでなく丸め後の値で判断）
    pre_min, pre_max = int(y_grid.min()), int(y_grid.max())
    if pre_min < WORLD_MIN_Y or pre_max > WORLD_MAX_Y:
        logging.warning(
            "地形の高さ範囲 [%d, %d] が Minecraft の [%d, %d] を超えるためクランプします。"
            "--relief / --floor-y を調整してください。",
            pre_min,
            pre_max,
            WORLD_MIN_Y,
            WORLD_MAX_Y,
        )
    y_grid = np.clip(y_grid, WORLD_MIN_Y, WORLD_MAX_Y)

    # 水平配置: マップを原点中心に置く（列→X, 行→Z）
    gx_axis = np.arange(w) - w // 2
    gz_axis = np.arange(h) - h // 2
    gx_grid, gz_grid = np.meshgrid(gx_axis, gz_axis)  # (H, W)

    gx = gx_grid.ravel()
    gz = gz_grid.ravel()
    y = y_grid.ravel()

    # 512x512 領域ごとに分割（グローバル座標を保持）
    region_x = np.floor(gx / BLOCK_SIZE).astype(int)
    region_z = np.floor(gz / BLOCK_SIZE).astype(int)
    regions: dict[tuple[int, int], list] = {}
    for k in range(len(gx)):
        key = (int(region_x[k]), int(region_z[k]))
        regions.setdefault(key, []).append((int(gx[k]), int(gz[k]), int(y[k])))

    region_dir = Path(output) / "world_data" / "region"
    if region_dir.exists():
        for f in region_dir.iterdir():
            if f.is_file():
                f.unlink()
    else:
        region_dir.mkdir(parents=True, exist_ok=True)

    tasks = [
        (rx, rz, cols, str(region_dir / f"r.{rx}.{rz}.mca"))
        for (rx, rz), cols in regions.items()
    ]
    ctx = {"bedrock": bedrock_block, "body": body_block, "surface": surface_block}

    logging.info("地形リージョン %d 個を構築（jobs=%s）", len(tasks), jobs or "auto")
    with Pool(processes=jobs, initializer=_worker_init, initargs=(ctx,)) as p:
        for path in p.imap_unordered(_build_one_region, tasks):
            logging.info("save: %s", os.path.basename(path))
