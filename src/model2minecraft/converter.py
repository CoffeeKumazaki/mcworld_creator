import logging
from pathlib import Path

import numpy as np
from trimesh.points import PointCloud

from plateau2minecraft.anvil import Block, EmptyRegion
from plateau2minecraft.anvil.errors import OutOfBoundsCoordinates

WORLD_MIN_Y = -64
WORLD_MAX_Y = 319
BLOCK_SIZE = 512


class Minecraft:
    def __init__(self, point_cloud: PointCloud, block: str = "minecraft:stone", base_y: int = 0) -> None:
        self.point_cloud = point_cloud
        self.block = Block.from_name(block)
        self.base_y = base_y

    def _get_world_origin(self, vertices: np.ndarray) -> tuple[float, float]:
        min_x, max_x = vertices[:, 0].min(), vertices[:, 0].max()
        min_y, max_y = vertices[:, 1].min(), vertices[:, 1].max()
        center_x = (max_x + min_x) / 2
        center_y = (max_y + min_y) / 2
        # ボクセル中心を原点とするため 0.5 ずらす
        return (center_x + 0.5, center_y + 0.5)

    def _split_by_region(self, coords: np.ndarray) -> dict[tuple[int, int], list]:
        """グローバルブロック座標 (N,3)=[X, Y(高さ), Z] を 512x512 の領域ごとに分割する。
        キーは (region_x, region_z)。座標はグローバルのまま保持する。"""
        region_x = np.floor(coords[:, 0] / BLOCK_SIZE).astype(int)
        region_z = np.floor(coords[:, 2] / BLOCK_SIZE).astype(int)
        regions: dict[tuple[int, int], list] = {}
        for i in range(len(coords)):
            key = (int(region_x[i]), int(region_z[i]))
            regions.setdefault(key, []).append(coords[i])
        return regions

    def build_region(self, output: Path) -> None:
        points = np.asarray(self.point_cloud.vertices, dtype=float).copy()

        # 水平方向（列0=X, 列1=水平Z）を原点中心へ移動。列2は高さとして扱う。
        origin = self._get_world_origin(points)
        points[:, 0] += -origin[0] + 0.5
        points[:, 1] += -origin[1] + 0.5
        # Y軸（水平Z）を反転して Minecraft の南北とあわせる
        points[:, 1] *= -1

        # 高さ（列2）を base_y 中心に配置
        height = points[:, 2]
        height_center = (height.min() + height.max()) / 2
        points[:, 2] += -height_center + self.base_y

        # グローバルブロック座標 [X, Y(高さ), Z] に変換
        coords = np.empty_like(points)
        coords[:, 0] = np.floor(points[:, 0])  # グローバルX
        coords[:, 1] = np.floor(points[:, 2])  # Minecraft Y（高さ）
        coords[:, 2] = np.floor(points[:, 1])  # グローバルZ（水平）
        coords = coords.astype(int)

        # Minecraft の高さ範囲外は静かに欠落するため、件数を集計して警告する
        y = coords[:, 1]
        out_mask = (y < WORLD_MIN_Y) | (y > WORLD_MAX_Y)
        n_out = int(out_mask.sum())
        if n_out:
            logging.warning(
                "%d 個のボクセルが Minecraft の高さ範囲 [%d, %d] の外側 (Y=%d..%d) にあり省略されます。"
                "--base-y / --target-size を調整してください。",
                n_out,
                WORLD_MIN_Y,
                WORLD_MAX_Y,
                int(y.min()),
                int(y.max()),
            )
        coords = coords[~out_mask]
        if len(coords) == 0:
            logging.warning("配置可能なボクセルがありません。リージョンを生成しませんでした。")
            return

        regions = self._split_by_region(coords)

        region_dir = Path(output) / "world_data" / "region"
        if region_dir.exists():
            for f in region_dir.iterdir():
                if f.is_file():
                    f.unlink()
        else:
            region_dir.mkdir(parents=True, exist_ok=True)

        for (region_x, region_z), region_coords in regions.items():
            # ファイル名の領域座標とチャンクの xPos/zPos を一致させるため、
            # 領域は (region_x, region_z) で生成し、グローバル座標のまま set する。
            region = EmptyRegion(region_x, region_z)
            for gx, gy, gz in np.asarray(region_coords, dtype=int):
                # Minecraft は Y-up の右手系: set_block(block, x, y, z)
                try:
                    region.set_if_inside(self.block, int(gx), int(gy), int(gz))
                except OutOfBoundsCoordinates:
                    continue

            region_name = f"r.{region_x}.{region_z}.mca"
            logging.info("save: %s", region_name)
            region.save(str(region_dir / region_name))
