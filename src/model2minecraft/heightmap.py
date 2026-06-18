import logging

import numpy as np
from scipy import ndimage
from trimesh import Trimesh
from trimesh.sample import sample_surface

from plateau2minecraft.types import TriangleMesh


def mesh_to_heightmap(mesh: TriangleMesh, width: int, height: int) -> np.ndarray:
    """メッシュ表面を「中心からの距離（半径）」の等距円筒ハイトマップに展開する。

    各セルは方向（方位角 θ × 極角 φ）に対応し、その方向で最も外側にある表面の
    半径を高さとして格納する。レイキャストは pyembree 無しでは低速なため、表面点を
    球面ビンに入れて最大半径を取るベクトル化方式を用いる。

    Parameters
    ----------
    mesh
        入力メッシュ（loader.load_mesh で up軸を +Z に正規化済みを想定。極が +Z）。
    width, height
        出力ハイトマップの幅（経度方向）・高さ（緯度方向）。

    Returns
    -------
    np.ndarray
        形状 (height, width) の半径2D配列（float）。
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width / height は正である必要があります: ({width}, {height})")

    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.triangles, dtype=np.int64)

    # 中心は bounding box 中心（頂点平均だと細分化の偏りで中心が動き高さが歪むため）。
    # solid モードの座標規約とも一致。
    center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2.0

    # 被覆を保証するため表面を一様サンプリング（疎なメッシュ対策）。
    n_samples = max(len(vertices), width * height * 2)
    tri = Trimesh(vertices=vertices, faces=faces, process=False)
    points, _ = sample_surface(tri, n_samples)
    points = np.asarray(points, dtype=float)

    vec = points - center
    r = np.linalg.norm(vec, axis=1)
    valid = r > 0
    vec = vec[valid]
    r = r[valid]

    theta = np.arctan2(vec[:, 1], vec[:, 0])  # [-π, π]
    phi = np.arccos(np.clip(vec[:, 2] / r, -1.0, 1.0))  # [0, π], 0 が +Z 極

    u = ((theta + np.pi) / (2.0 * np.pi) * width).astype(np.int64) % width
    v = np.clip((phi / np.pi * height).astype(np.int64), 0, height - 1)

    # 各セルの最大半径を集約（外側の表面を採用）
    flat = v * width + u
    acc = np.full(width * height, -np.inf)
    np.maximum.at(acc, flat, r)
    hm = acc.reshape(height, width)

    # 空セル（点が落ちなかった所）を最近傍で補間。
    # 等距円筒は経度方向(u=0 と u=width-1)が隣接する周期境界なので、左右にタイルしてから
    # 最近傍補間し中央タイルを取り出すことで、人工的な縦シームを防ぐ。
    empty = ~np.isfinite(hm)
    n_empty = int(empty.sum())
    if n_empty:
        logging.info("ハイトマップ空セル %d/%d を最近傍補間で充填（経度=周期境界）", n_empty, hm.size)
        tiled = np.concatenate([hm, hm, hm], axis=1)
        tiled_empty = ~np.isfinite(tiled)
        idx = ndimage.distance_transform_edt(tiled_empty, return_distances=False, return_indices=True)
        filled = tiled[tuple(idx)]
        hm = filled[:, width : 2 * width]

    return hm
