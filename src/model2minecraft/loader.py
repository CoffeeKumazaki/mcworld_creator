from pathlib import Path

import numpy as np
import trimesh

from plateau2minecraft.types import TriangleMesh


def load_mesh(file_path: Path, target_size: int, up_axis: str = "y") -> TriangleMesh:
    """汎用3Dモデル（.obj/.stl/.ply/.glb など）を読み込み、Minecraft向けに正規化した
    TriangleMesh を返す。

    Parameters
    ----------
    file_path
        読み込む3Dモデルファイル
    target_size
        最長辺をこのブロック数になるよう自動スケールする
    up_axis
        モデルの上方向軸。``"y"`` のとき Y/Z を入れ替え、内部表現を Z-up に統一する
        （plateau の voxelizer / converter は Z を高さとして扱うため）。``"z"`` はそのまま。
    """
    # force="mesh" で Scene でも単一 Trimesh に結合して返す
    loaded = trimesh.load(file_path, force="mesh")

    vertices = np.asarray(loaded.vertices, dtype=float).copy()
    faces = np.asarray(loaded.faces, dtype=np.int32)

    if vertices.size == 0 or faces.size == 0:
        raise ValueError(f"メッシュに頂点または面がありません: {file_path}")

    # 上方向軸を Z-up に正規化
    if up_axis == "y":
        vertices[:, [1, 2]] = vertices[:, [2, 1]]

    # 最長辺が target_size ブロックになるよう等方スケール
    extent = vertices.max(axis=0) - vertices.min(axis=0)
    max_extent = float(extent.max())
    if max_extent <= 0:
        raise ValueError(f"メッシュの寸法がゼロです: {file_path}")
    scale = target_size / max_extent
    vertices *= scale

    return TriangleMesh(vertices=vertices, triangles=faces)
