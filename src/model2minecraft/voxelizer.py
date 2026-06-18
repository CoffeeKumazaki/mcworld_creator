import numpy as np
from scipy import ndimage
from trimesh.points import PointCloud

from plateau2minecraft.types import TriangleMesh
from plateau2minecraft.voxelizer import voxelize as voxelize_shell

# 密グリッドのボクセル数上限（bool 約500MB相当）。これを超える --target-size は拒否する。
MAX_GRID_VOXELS = 500_000_000


def voxelize_solid(mesh: TriangleMesh) -> PointCloud:
    """メッシュを中身の詰まった（ソリッド）ボクセル点群に変換する。

    plateau の ``voxelize`` は表面（殻）ボクセル化専用（サブメッシュ分割のため各断片は
    閉じておらず ``.fill()`` では充填できない）。そこで殻を取得したうえで、密な3Dグリッド
    上で ``scipy.ndimage.binary_fill_holes`` により内部を充填する。
    """
    shell = voxelize_shell(mesh)
    pts = np.asarray(shell.vertices, dtype=float)
    if len(pts) == 0:
        return shell

    # ボクセルは pitch=1。floor で整数格子に落とし、各点共通の小数オフセットを保持して
    # 殻と同じサブ格子上に充填結果を戻す。
    lattice = np.floor(pts).astype(np.int64)
    frac = pts[0] - lattice[0]

    mn = lattice.min(axis=0)
    idx = lattice - mn

    # 外周に1ボクセルのパディングを入れ、グリッド境界が確実に背景になるようにする
    dims = idx.max(axis=0) + 1 + 2

    # 密グリッドは O(target-size^3) メモリ。過大な --target-size での OOM を防ぐ。
    n_voxels = int(np.prod(dims))
    if n_voxels > MAX_GRID_VOXELS:
        raise ValueError(
            f"ソリッド充填グリッドが大きすぎます: {dims.tolist()} = {n_voxels} ボクセル "
            f"(上限 {MAX_GRID_VOXELS})。--target-size を小さくするか --hollow を使ってください。"
        )

    grid = np.zeros(tuple(dims), dtype=bool)
    grid[idx[:, 0] + 1, idx[:, 1] + 1, idx[:, 2] + 1] = True

    filled = ndimage.binary_fill_holes(grid)

    fi = np.argwhere(filled) - 1
    out = fi.astype(float) + mn + frac
    return PointCloud(out)
