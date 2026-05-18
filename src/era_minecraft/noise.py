"""Pure numpy noise functions: Perlin 2D/3D, fBm, Worley."""

import numpy as np


def _fade(t):
    """Quintic fade curve 6t^5 - 15t^4 + 10t^3."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _hash_coords(xi, yi, seed):
    """Simple integer hash for gradient lookup."""
    h = np.int64(xi) * 374761393 + np.int64(yi) * 668265263 + np.int64(seed)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return h


def _hash_coords_3d(xi, yi, zi, seed):
    """Simple integer hash for 3D gradient lookup."""
    h = np.int64(xi) * 374761393 + np.int64(yi) * 668265263 + np.int64(zi) * 1274126177 + np.int64(seed)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return h


def _grad2d(h, x, y):
    """2D gradient from hash."""
    g = h & 3
    u = np.where(g < 2, x, y)
    v = np.where(g < 2, y, x)
    return np.where(g & 1, -u, u) + np.where(g & 2, -v, v)


def _grad3d(h, x, y, z):
    """3D gradient from hash."""
    g = h & 15
    u = np.where(g < 8, x, y)
    v = np.where(g < 4, y, np.where((g == 12) | (g == 14), x, z))
    return np.where(g & 1, -u, u) + np.where(g & 2, -v, v)


def perlin_2d(x_arr, z_arr, seed=0, octaves=1, persistence=0.5, lacunarity=2.0):
    """2D Perlin noise over coordinate arrays.

    Parameters
    ----------
    x_arr, z_arr : array-like
        1D coordinate arrays. The function evaluates on the 2D grid formed by
        meshgrid(x_arr, z_arr).
    seed : int
    octaves : int
    persistence : float
    lacunarity : float

    Returns
    -------
    np.ndarray
        2D array of shape (len(z_arr), len(x_arr)) with values roughly in [-1, 1].
    """
    x_arr = np.asarray(x_arr, dtype=np.float64)
    z_arr = np.asarray(z_arr, dtype=np.float64)
    xg, zg = np.meshgrid(x_arr, z_arr)

    result = np.zeros_like(xg)
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0

    for _ in range(octaves):
        sx = xg * frequency
        sz = zg * frequency

        xi = np.floor(sx).astype(np.int64)
        zi = np.floor(sz).astype(np.int64)
        xf = sx - xi
        zf = sz - zi

        u = _fade(xf)
        v = _fade(zf)

        n00 = _grad2d(_hash_coords(xi, zi, seed), xf, zf)
        n10 = _grad2d(_hash_coords(xi + 1, zi, seed), xf - 1, zf)
        n01 = _grad2d(_hash_coords(xi, zi + 1, seed), xf, zf - 1)
        n11 = _grad2d(_hash_coords(xi + 1, zi + 1, seed), xf - 1, zf - 1)

        nx0 = n00 + u * (n10 - n00)
        nx1 = n01 + u * (n11 - n01)
        val = nx0 + v * (nx1 - nx0)

        result += val * amplitude
        max_amp += amplitude
        amplitude *= persistence
        frequency *= lacunarity
        seed += 31

    return result / max_amp


def perlin_3d(x, y, z, seed=0):
    """Single-octave 3D Perlin noise. Inputs can be scalars or arrays."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)

    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    zi = np.floor(z).astype(np.int64)
    xf = x - xi
    yf = y - yi
    zf = z - zi

    u = _fade(xf)
    v = _fade(yf)
    w = _fade(zf)

    def g(dxi, dyi, dzi):
        return _grad3d(
            _hash_coords_3d(xi + dxi, yi + dyi, zi + dzi, seed),
            xf - dxi, yf - dyi, zf - dzi,
        )

    n000 = g(0, 0, 0)
    n100 = g(1, 0, 0)
    n010 = g(0, 1, 0)
    n110 = g(1, 1, 0)
    n001 = g(0, 0, 1)
    n101 = g(1, 0, 1)
    n011 = g(0, 1, 1)
    n111 = g(1, 1, 1)

    nx00 = n000 + u * (n100 - n000)
    nx10 = n010 + u * (n110 - n010)
    nx01 = n001 + u * (n101 - n001)
    nx11 = n011 + u * (n111 - n011)
    nxy0 = nx00 + v * (nx10 - nx00)
    nxy1 = nx01 + v * (nx11 - nx01)
    return nxy0 + w * (nxy1 - nxy0)


def fbm_3d(x, y, z, seed=0, octaves=4, persistence=0.5, lacunarity=2.0):
    """Fractal Brownian Motion wrapper around 3D Perlin."""
    result = np.zeros_like(np.asarray(x, dtype=np.float64))
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0

    for _ in range(octaves):
        result += perlin_3d(x * frequency, y * frequency, z * frequency, seed) * amplitude
        max_amp += amplitude
        amplitude *= persistence
        frequency *= lacunarity
        seed += 31

    return result / max_amp


def worley_2d(x_arr, z_arr, seed=0, frequency=1.0):
    """2D Worley (cellular) noise. Returns distance to nearest cell point.

    Parameters
    ----------
    x_arr, z_arr : array-like
        1D coordinate arrays; evaluated on meshgrid(x_arr, z_arr).
    seed : int
    frequency : float

    Returns
    -------
    np.ndarray
        2D array with values in [0, ~1]. Lower values = closer to cell center.
    """
    x_arr = np.asarray(x_arr, dtype=np.float64) * frequency
    z_arr = np.asarray(z_arr, dtype=np.float64) * frequency
    xg, zg = np.meshgrid(x_arr, z_arr)

    xi = np.floor(xg).astype(np.int64)
    zi = np.floor(zg).astype(np.int64)

    min_dist = np.full_like(xg, 999.0)

    for di in range(-1, 2):
        for dj in range(-1, 2):
            cx = xi + di
            cz = zi + dj
            h = _hash_coords(cx, cz, seed)
            # Deterministic point within cell [0,1)
            px = cx + (h & 0xFFFF).astype(np.float64) / 65536.0
            h2 = _hash_coords(cx, cz, seed + 17)
            pz = cz + (h2 & 0xFFFF).astype(np.float64) / 65536.0
            dist = np.sqrt((xg - px) ** 2 + (zg - pz) ** 2)
            min_dist = np.minimum(min_dist, dist)

    return min_dist


def worley_2d_edge(x_arr, z_arr, seed=0, frequency=1.0):
    """2D Worley noise returning F2-F1 (cell edge proximity).

    Low values = near a cell boundary (crack/edge).
    High values = deep inside a cell (solid plate).

    Returns
    -------
    np.ndarray
        2D array. Values near 0 = on cell edge.
    """
    x_arr = np.asarray(x_arr, dtype=np.float64) * frequency
    z_arr = np.asarray(z_arr, dtype=np.float64) * frequency
    xg, zg = np.meshgrid(x_arr, z_arr)

    xi = np.floor(xg).astype(np.int64)
    zi = np.floor(zg).astype(np.int64)

    f1 = np.full_like(xg, 999.0)
    f2 = np.full_like(xg, 999.0)

    for di in range(-1, 2):
        for dj in range(-1, 2):
            cx = xi + di
            cz = zi + dj
            h = _hash_coords(cx, cz, seed)
            px = cx + (h & 0xFFFF).astype(np.float64) / 65536.0
            h2 = _hash_coords(cx, cz, seed + 17)
            pz = cz + (h2 & 0xFFFF).astype(np.float64) / 65536.0
            dist = np.sqrt((xg - px) ** 2 + (zg - pz) ** 2)
            # Update F1 and F2
            new_f2 = np.where(dist < f1, np.minimum(f1, f2), np.minimum(f2, dist))
            new_f1 = np.minimum(f1, dist)
            f1 = new_f1
            f2 = new_f2

    return f2 - f1
