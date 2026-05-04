import os
import re
import math
import rasterio
import numpy as np
import pandas as pd
from scipy.ndimage import zoom

from grand_canyon.biome_config import CANYON_LAYERS_CONFIG, LayerConfig


def _pixel_size_meters(src):
    """TIFFのピクセルサイズをメートルで返す"""
    if src.crs and src.crs.is_geographic:
        # 地理座標系（度）→メートルに変換
        center_lat = (src.bounds.top + src.bounds.bottom) / 2.0
        lat_rad = math.radians(center_lat)
        meter_per_deg_x = 111320.0 * math.cos(lat_rad)
        meter_per_deg_y = 110540.0
        px_m = abs(src.transform.a) * meter_per_deg_x
        py_m = abs(src.transform.e) * meter_per_deg_y
    else:
        # 投影座標系（メートル等）
        px_m = abs(src.transform.a)
        py_m = abs(src.transform.e)
    return px_m, py_m


def tiff_to_frame(tiff_file, output_folder, resample=True):
    with rasterio.open(tiff_file) as src:

        # 幅と高さを取得
        width, height = src.width, src.height
        print(f"width: {width}, height: {height}")

        # ピクセルサイズ（メートル）を計算
        px_m, py_m = _pixel_size_meters(src)
        print(f"Pixel size: {px_m:.2f}m x {py_m:.2f}m")

        # 数値標高データを取得
        data = src.read(1)

        if resample and (px_m > 1.5 or py_m > 1.5):
            # 1ピクセル≒1mになるようCubic補間でリサンプリング
            scale_x = px_m
            scale_y = py_m
            print(f"Resampling: {width}x{height} -> {int(width*scale_x)}x{int(height*scale_y)} (cubic interpolation)")
            data = zoom(data, (scale_y, scale_x), order=3)
            height, width = data.shape
            print(f"Resampled size: {width}x{height}")

        # 中心点のオフセットを計算
        offset_x = 0.5 if width % 2 == 0 else 0
        offset_y = -0.5 if height % 2 == 0 else 0

        center_x = width / 2.0 + offset_x
        center_y = height / 2.0 + offset_y

        # 各ピクセルの中心座標を取得
        y_indices, x_indices = np.indices(data.shape)

        # xmin, ymax はアフィン変換の左上の座標
        transform = src.transform
        xmin, ymax = transform * (0, 0)
        # xmax, ymin はアフィン変換の右下の座標
        xmax, ymin = transform * (src.width, src.height)

        print(f"{xmin=}, {xmax=}")
        print(f"{ymin=}, {ymax=}")

        # ピクセル座標と標高値を一次元化
        x_coords = x_indices.ravel()
        y_coords = y_indices.ravel()
        data = data.ravel()

        # マイクラの基準にする中心の座標を引く
        x_coords = x_coords - center_x
        y_coords = y_coords - center_y

        # 小数点以下を排除
        x_coords = np.trunc(x_coords).astype(int)
        y_coords = np.trunc(y_coords).astype(int)
        data = np.trunc(data).astype(int)

        # マイクラのブロック座標からregion(.mca)のファイル名を取得
        region_x = (x_coords // 512).astype(int)
        region_z = (y_coords // 512).astype(int)

        # ベクトル化した文字列フォーマット操作を適用
        output_folder = os.path.join(output_folder, "region")
        os.makedirs(output_folder, exist_ok=True)
        region= [f"{output_folder}/r.{rx}.{rz}.mca"
                    for rx, rz in zip(region_x, region_z)]

        # データフレームを作成
        df = pd.DataFrame({
            "x": x_coords,
            "z": y_coords,
            "y": data,
            "region": region
        })
        return df

# ライブラリのインポート
import anvil
import random

# 3種類のブロックを定義
grass = anvil.Block("minecraft", "grass_block")
dirt = anvil.Block("minecraft", "dirt")
stone = anvil.Block("minecraft", "stone")
cobblestone = anvil.Block("minecraft", "cobblestone")
gray_concrete_powder = anvil.Block("minecraft", "gray_concrete_powder")
white_concrete = anvil.Block("minecraft", "white_concrete")
water_block = anvil.Block("minecraft", "water")

TNM_BLOCK = [
    anvil.Block("minecraft", "yellow_stained_glass"),
    anvil.Block("minecraft", "orange_stained_glass"),
    anvil.Block("minecraft", "red_stained_glass"),
    anvil.Block("minecraft", "purple_stained_glass"),
    anvil.Block("minecraft", "blue_stained_glass"),
    anvil.Block("minecraft", "cyan_stained_glass"),]

def coord_hash(x: int, y: int, z: int, seed: int = 0) -> int:
    """FNV-1a inspired hash for coordinate-based deterministic noise."""
    h = 2166136261 ^ seed
    h = ((h ^ (x & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    h = ((h ^ (y & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    h = ((h ^ (z & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    h = ((h ^ ((x >> 16) & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    return h


def temple_butte_present(x: int, z: int) -> bool:
    """30% of 12x12 patches have Temple Butte."""
    h = coord_hash(x // 12, 0, z // 12, seed=99)
    return (h % 100) < 30


def get_boundary_factor(y_within_layer: int, layer_thickness: int) -> float:
    """Returns 0.0 at center, up to 1.0 at edges (within 2 blocks)."""
    if layer_thickness <= 4:
        return 0.0
    dist_from_bottom = y_within_layer
    dist_from_top = layer_thickness - 1 - y_within_layer
    dist_from_edge = min(dist_from_bottom, dist_from_top)
    if dist_from_edge >= 2:
        return 0.0
    return 1.0 - dist_from_edge / 2.0


def _select_with_pattern(x: int, y: int, z: int, h: int, blocks: list, pattern: str, role: str) -> str:
    """Apply spatial patterns to select among blocks within a role."""
    if len(blocks) == 1:
        return blocks[0]

    if pattern == "horizontal_band":
        if role == "sub":
            band = (y // 4) % len(blocks)
        elif role == "accent":
            band = (y // 2) % len(blocks)
        else:
            band = h % len(blocks)
        return blocks[band]

    elif pattern == "veins":
        diagonal = (x + 2 * y + z) % (len(blocks) * 7)
        return blocks[diagonal % len(blocks)]

    elif pattern == "irregular":
        cell = coord_hash(x // 3, y // 3, z // 3, seed=42)
        return blocks[cell % len(blocks)]

    else:  # "default"
        return blocks[h % len(blocks)]


def select_canyon_block(x: int, y: int, z: int, layer: LayerConfig, boundary_factor: float) -> str:
    """Pick Main/Sub/Accent block based on hash threshold and pattern."""
    h = coord_hash(x, y, z)
    threshold = h % 100

    # At boundaries, boost sub percentage for blending
    main_pct = layer.main_pct
    sub_pct = layer.sub_pct
    if boundary_factor > 0.0 and layer.sub_pct > 0:
        shift = int(15 * boundary_factor)
        main_pct = max(main_pct - shift, 10)
        sub_pct = sub_pct + shift

    if threshold < main_pct:
        return _select_with_pattern(x, y, z, h >> 8, layer.main, layer.pattern, "main")
    elif threshold < main_pct + sub_pct:
        return _select_with_pattern(x, y, z, h >> 8, layer.sub, layer.pattern, "sub")
    else:
        return _select_with_pattern(x, y, z, h >> 8, layer.accent, layer.pattern, "accent")


def build_canyon_layer_map(total_height: int, scale: float):
    """Returns (layer_map, scaled_thicknesses).

    layer_map: list of (layer_index, y_within_layer) for each Y offset.
    scaled_thicknesses: list of actual thicknesses per layer.
    """
    original_thicknesses = [layer.thickness for layer in CANYON_LAYERS_CONFIG]

    # Scale each layer directly using the terrain scale factor
    scaled = [max(1, round(t * scale)) for t in original_thicknesses]

    # Adjust topmost layer to fill remaining space
    diff = total_height - sum(scaled)
    if diff != 0:
        scaled[-1] = max(1, scaled[-1] + diff)

    layer_map = []
    for layer_idx, thickness in enumerate(scaled):
        for y_in_layer in range(max(thickness, 0)):
            layer_map.append((layer_idx, y_in_layer))

    return layer_map, scaled


# Pre-instantiate all unique Block objects for canyon layers
BLOCK_CACHE: dict[str, anvil.Block] = {}
for _layer in CANYON_LAYERS_CONFIG:
    for _name in _layer.main + _layer.sub + _layer.accent:
        if _name not in BLOCK_CACHE:
            BLOCK_CACHE[_name] = anvil.Block("minecraft", _name)

# 3種類の草を定義
grass_plant = anvil.Block("minecraft", "grass")
tall_grass_l = anvil.Block("minecraft", "tall_grass", properties={"half": "lower"})
tall_grass_u = anvil.Block("minecraft", "tall_grass", properties={"half": "upper"})

# ブロックを設置する処理
def set_blocks(region, x, y, z, road_type=0, tnm_class=0, biome=None,
               canyon_layer_map=None, canyon_layer_thicknesses=None):

    height_limit = 319
    height = np.clip(y, -64, height_limit)
    height = int(height)

    if biome == "canyon":
        tb_present = temple_butte_present(x, z)
        for i in range(-64, height):
            if -64 <= i < -62:
                region.set_block(anvil.Block("minecraft", "bedrock"), x, i, z)
            else:
                idx = (i + 64) % len(canyon_layer_map)
                layer_idx, y_in_layer = canyon_layer_map[idx]
                layer = CANYON_LAYERS_CONFIG[layer_idx]
                # Handle Temple Butte absence
                if layer.discontinuous and not tb_present:
                    layer_idx = layer_idx - 1
                    layer = CANYON_LAYERS_CONFIG[layer_idx]
                    y_in_layer = canyon_layer_thicknesses[layer_idx] - 1
                boundary = get_boundary_factor(y_in_layer, canyon_layer_thicknesses[layer_idx])
                block_name = select_canyon_block(x, i, z, layer, boundary)
                region.set_block(BLOCK_CACHE[block_name], x, i, z)
        # 地表面
        if road_type and road_type > 200:
            region.set_block(gray_concrete_powder, x, height, z)
        elif road_type and road_type > 100:
            region.set_block(cobblestone, x, height, z)
        else:
            idx = (height + 64) % len(canyon_layer_map)
            layer_idx, y_in_layer = canyon_layer_map[idx]
            layer = CANYON_LAYERS_CONFIG[layer_idx]
            if layer.discontinuous and not tb_present:
                layer_idx = layer_idx - 1
                layer = CANYON_LAYERS_CONFIG[layer_idx]
                y_in_layer = canyon_layer_thicknesses[layer_idx] - 1
            boundary = get_boundary_factor(y_in_layer, canyon_layer_thicknesses[layer_idx])
            block_name = select_canyon_block(x, height, z, layer, boundary)
            region.set_block(BLOCK_CACHE[block_name], x, height, z)
    else:
        # 設定するブロックのリスト(草ブロック１、土ブロック１、石ブロック３のレイヤーをつくる)
        blocks = [grass, dirt, stone, stone, stone]

        # 5%の確率で草を生やす
        # if random.random() > 0.95 and y < 319:
        #    region.set_block(random.choice([grass_plant, tall_grass_l, tall_grass_u]), x, y + 1, z)

        # ブロックのレイヤーを設置する。ブロック設置ができない範囲はbreakで抜ける
        for i in range(-64, height-3):

            ##-62以下は岩盤ブロック
            if -64 <= i < -62:
                bedrock = anvil.Block("minecraft", "bedrock")
                region.set_block(bedrock, x, i, z)
            else:
                region.set_block(stone, x, i, z)

        for i in range(max(-64, height-3), height):
            region.set_block(dirt, x, i, z)

        if road_type > 200:
            ## 道路は gray concrete powder
            region.set_block(gray_concrete_powder, x, height, z)
        elif road_type > 100:
            region.set_block(cobblestone, x, height, z)
        elif tnm_class > 0:
            ## 津波の高さを設定
            region.set_block(TNM_BLOCK[tnm_class], x, height, z)
        else:
            region.set_block(grass, x, height, z)
    

def df_to_map(df, road_df=None, bldg_df=None, df_water=None, df_tnm=None, scale=None, biome=None, water_level=None):

    # 0より大きい値の最小値を取得
    min_value = df[df['y'] > 0]['y'].min()
    max_value = df['y'].max()
    print(f"min: {min_value}, max: {max_value}")

    elevation_range = max_value - min_value
    mc_height_available = 379  # -60 to 319

    if scale is None:
        if elevation_range > mc_height_available:
            scale = mc_height_available / elevation_range
            print(f"Auto-scaling: {elevation_range}m -> {mc_height_available} blocks (factor: {scale:.4f})")
        else:
            scale = 1.0
    else:
        print(f"Manual scale: {scale}")

    # yが0の行に64を加算
    df['y'] = df['y'].replace(0, min_value)
    # df.mask(df["y"] == 0, min_value, inplace=True)

    if road_df is not None:
        road_df = road_df.rename(columns={'y': 'road'})
        df = pd.merge(df, road_df[['x', 'z', 'road']], on=['x', 'z'], how='left')
    else:
        df['road'] = None

    if bldg_df is not None:
        bldg_df = bldg_df.rename(columns={'y': 'bldg'})
        df = pd.merge(df, bldg_df[['x', 'z', 'bldg']], on=['x', 'z'], how='left')
    else:
        df['bldg'] = -1

    if df_water is not None:
        df_water = df_water.rename(columns={'y': 'water'})
        df = pd.merge(df, df_water[['x', 'z', 'water']], on=['x', 'z'], how='left')
    else:
        df['water'] = -1

    if df_tnm is not None:
        df_tnm = df_tnm.rename(columns={'y': 'tnm'})
        df = pd.merge(df, df_tnm[['x', 'z', 'tnm']], on=['x', 'z'], how='left')
    else:
        df['tnm'] = -1

    # Canyon レイヤーマップをスケール適用後の高さで生成
    canyon_layer_map = None
    canyon_layer_thicknesses = None
    if biome == "canyon":
        total_height = int((max_value - min_value) * scale) + 5
        canyon_layer_map, canyon_layer_thicknesses = build_canyon_layer_map(total_height, scale=scale)

        print("=== Canyon Layer Elevations ===")
        print(f" {'#':>2} {'Name':<20} {'Y_start':>7} {'Y_end':>7} {'Thickness':>9}")
        y_cursor = -60
        for i, layer in enumerate(CANYON_LAYERS_CONFIG):
            t = canyon_layer_thicknesses[i]
            y_end = y_cursor + t - 1
            print(f" {i:>2} {layer.name:<20} {y_cursor:>7} {y_end:>7} {t:>9}")
            y_cursor += t
        print("================================")

    # 水位のMinecraft Y座標を計算
    water_level_y = None
    if water_level is not None:
        water_level_y = int((water_level - min_value) * scale - 60)
        water_level_y = int(np.clip(water_level_y, -64, 319))
        print(f"Water level: {water_level}m -> MC Y={water_level_y}")

    # regionごとにグループ分け
    print("Grouping by region...")
    grouped = df.groupby(["region"])

    for _name, group in grouped:
        # 先頭行をスキップ
        # group = group.iloc[1:]

        # regionを作成
        match = re.search(r"r\.(-?\d+)\.(-?\d+)\.mca", _name[0])
        if match:
            rx, ry = match.groups()
            rx = int(rx)
            ry = int(ry)

        region = anvil.EmptyRegion(rx, ry)
        x = group["x"]
        y_original = group["y"]
        y = ((group["y"] - min_value) * scale - 60).astype(int)
        z = group["z"]
        road_type = group["road"]
        bldg_height = group["bldg"]
        is_water = group["water"]
        tnm_class = group["tnm"]

        for xi, yi, zi, road_typei, bh, water, tnm, y_orig in zip(x, y, z, road_type, bldg_height, is_water, tnm_class, y_original):
            set_blocks(region, xi, yi, zi, road_typei, tnm, biome=biome,
                       canyon_layer_map=canyon_layer_map,
                       canyon_layer_thicknesses=canyon_layer_thicknesses)

            if bh > 0:
                for i in range(int((bh - y_orig) * scale)):
                    region.set_block(white_concrete, xi, yi + i, zi)
            elif water > 0:
                for i in range(3): ## 水深3
                    region.set_block(water_block, xi, yi - i, zi)
            elif water_level_y is not None and yi < water_level_y:
                for wy in range(yi + 1, water_level_y + 1):
                    if -64 <= wy <= 319:
                        region.set_block(water_block, xi, wy, zi)

        # regionを保存
        region.save(group.iloc[1]["region"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiff", required=True, help="tiff file path")
    parser.add_argument("--output", required=True, help="output folder")
    parser.add_argument("--road", required=False, help="road tiff file path", default=None)
    parser.add_argument("--bldg", required=False, help="building tiff file path", default=None)
    parser.add_argument("--water", required=False, help="water tiff file path", default=None)
    parser.add_argument("--tnm", required=False, help="tnm tiff file path", default=None)
    parser.add_argument("--scale", type=float, default=None,
                        help="垂直スケール係数（省略時は自動計算）")
    parser.add_argument("--biome", type=str, default=None, choices=["default", "canyon"],
                        help="ブロックパレット: default=草/土/石, canyon=砂岩/テラコッタ地層")
    parser.add_argument("--water-level", type=float, default=None,
                        help="水面の標高（メートル）。この標高以下の地形に水を充填")
    parser.add_argument("--no-resample", action="store_true",
                        help="1ピクセル=1ブロックのまま（リサンプリングしない）")
    args = parser.parse_args()

    resample = not args.no_resample

    tiff_file = args.tiff
    road_file = args.road
    bldg_file = args.bldg
    water_file = args.water
    tnm_file = args.tnm
    output_folder = args.output
    os.makedirs(output_folder, exist_ok=True)

    # tiffファイルを読み込む
    print(f"Reading tiff file: {tiff_file}")
    df = tiff_to_frame(tiff_file, output_folder, resample=resample)
    df_road = None
    df_bldg = None
    df_water = None
    df_tnm = None
    # 道路ファイルを読み込む
    if road_file is not None:
        df_road = tiff_to_frame(road_file, output_folder, resample=resample)

    if bldg_file is not None:
        df_bldg = tiff_to_frame(bldg_file, output_folder, resample=resample)

    if water_file is not None:
        df_water = tiff_to_frame(water_file, output_folder, resample=resample)
    if tnm_file is not None:
        df_tnm = tiff_to_frame(tnm_file, output_folder, resample=resample)

    # マップを作成
    df_to_map(df, df_road, df_bldg, df_water, df_tnm,
              scale=args.scale, biome=args.biome, water_level=args.water_level)