import os
import re
import glob
import json
import math
import rasterio
import numpy as np
import pandas as pd
from scipy.ndimage import zoom, gaussian_filter
from tqdm import tqdm

from grand_canyon.biome_config import CANYON_LAYERS_CONFIG, LayerConfig, FossilConfig


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


def tiff_to_frame(tiff_file, output_folder, resample=True, meters_per_block=1.0, smooth=0.0):
    with rasterio.open(tiff_file) as src:

        # 幅と高さを取得
        width, height = src.width, src.height
        print(f"width: {width}, height: {height}")

        # ピクセルサイズ（メートル）を計算
        px_m, py_m = _pixel_size_meters(src)
        print(f"Pixel size: {px_m:.2f}m x {py_m:.2f}m")

        # 数値標高データを取得
        data = src.read(1)

        # 1ブロックが meters_per_block メートルを表すようリサンプリング。
        # 拡大(>1)も縮小(<1)も同じ式で扱える。軸別に係数を掛けることで
        # 緯度経度由来の px_m≠py_m でも実メートルで正方ブロックになる。
        scale_x = px_m / meters_per_block
        scale_y = py_m / meters_per_block
        if resample and (abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01):
            # 拡大はcubic、縮小はlinear（cubicは縮小時にリンギングが出やすい）
            order = 3 if (scale_x > 1.0 or scale_y > 1.0) else 1
            print(f"Resampling: {width}x{height} -> "
                  f"{int(width*scale_x)}x{int(height*scale_y)} "
                  f"(target {meters_per_block}m/block, order={order})")
            data = zoom(data, (scale_y, scale_x), order=order)
            height, width = data.shape
            print(f"Resampled size: {width}x{height}")

        # 標高をガウシアンで平滑化（sigma=ブロック単位）。階段状の段差を丸めて地形を滑らかに。
        if smooth and smooth > 0:
            print(f"Smoothing elevation: gaussian sigma={smooth} blocks")
            data = gaussian_filter(data, sigma=smooth)

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

# 砂漠系バイオームの地表/地下ブロック
sand = anvil.Block("minecraft", "sand")
sandstone = anvil.Block("minecraft", "sandstone")
red_sand = anvil.Block("minecraft", "red_sand")
red_sandstone = anvil.Block("minecraft", "red_sandstone")
white_terracotta = anvil.Block("minecraft", "white_terracotta")
orange_terracotta = anvil.Block("minecraft", "orange_terracotta")

# biome名 -> (地表ブロック, 地下ブロック, 深部ブロック)。未登録（default等）は草/土/石。
SURFACE_PALETTE = {
    "desert": (sand, sandstone, white_terracotta),
    "red_desert": (red_sand, red_sandstone, orange_terracotta),
}

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
    # --- 化石クラスター判定（最優先） ---
    for i, fossil in enumerate(layer.fossils):
        cx = x // fossil.cluster_size
        cy = y // fossil.cluster_size
        cz = z // fossil.cluster_size
        cell_h = coord_hash(cx, cy, cz, seed=700 + i)
        if (cell_h % 1000) < fossil.cluster_chance:
            block_h = coord_hash(x, y, z, seed=800 + i)
            if (block_h % 100) < fossil.fill_pct:
                return fossil.block

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
    _all_names = _layer.main + _layer.sub + _layer.accent
    for _fossil in _layer.fossils:
        _all_names.append(_fossil.block)
    for _name in _all_names:
        if _name not in BLOCK_CACHE:
            BLOCK_CACHE[_name] = anvil.Block("minecraft", _name)

# 3種類の草を定義
grass_plant = anvil.Block("minecraft", "grass")
tall_grass_l = anvil.Block("minecraft", "tall_grass", properties={"half": "lower"})
tall_grass_u = anvil.Block("minecraft", "tall_grass", properties={"half": "upper"})

# ブロックを設置する処理
def set_blocks(region, x, y, z, road_type=0, tnm_class=0, biome=None,
               canyon_layer_map=None, canyon_layer_thicknesses=None):

    height_limit = anvil.world_height.WORLD_MAX_Y
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
        # 地表/地下/深部ブロックをバイオームで切替（desert=砂/砂岩/茶テラコ, red_desert=赤砂/赤砂岩/茶テラコ）。
        # 未登録（default等）は従来どおり草ブロック/土/石。
        surface_block, subsurface_block, deep_block = SURFACE_PALETTE.get(biome, (grass, dirt, stone))

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
                region.set_block(deep_block, x, i, z)

        for i in range(max(-64, height-3), height):
            region.set_block(subsurface_block, x, i, z)

        if road_type and road_type > 200:
            ## 道路は gray concrete powder
            region.set_block(gray_concrete_powder, x, height, z)
        elif road_type and road_type > 100:
            region.set_block(cobblestone, x, height, z)
        elif tnm_class > 0:
            ## 津波の高さを設定
            region.set_block(TNM_BLOCK[tnm_class], x, height, z)
        else:
            region.set_block(surface_block, x, height, z)
    

def _atomic_write_json(path, obj):
    """Write JSON to a temp file then os.replace into place (atomic on same fs)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


# ---- region build worker (top-level so multiprocessing 'spawn' can pickle it) ----
# Read-only shared context, populated per worker via Pool initializer (or directly
# in the serial path). Avoids re-pickling the layer maps for every region.
_RCTX = {}


def _worker_init(ctx):
    global _RCTX
    _RCTX = ctx
    # spawn re-imports this module, resetting WORLD_MAX_Y to the vanilla default,
    # so every worker process must restore the active ceiling before building.
    anvil.set_world_height(ctx["active_max_y"])


def _build_one_region(task):
    """Build and atomically save a single region. Returns (status, region_path)."""
    region_path, rx, ry, cols, resume = task

    if resume and os.path.exists(region_path) and os.path.getsize(region_path) > 0:
        return ("skipped", region_path)

    ctx = _RCTX
    min_value = ctx["min_value"]
    scale = ctx["scale"]
    biome = ctx["biome"]
    water_level_y = ctx["water_level_y"]
    canyon_layer_map = ctx["canyon_layer_map"]
    canyon_layer_thicknesses = ctx["canyon_layer_thicknesses"]

    region = anvil.EmptyRegion(rx, ry)
    y = ((cols["y"] - min_value) * scale - 60).astype(int)
    y_original = cols["y"]

    for xi, yi, zi, road_typei, bh, water, tnm, y_orig in zip(
            cols["x"], y, cols["z"], cols["road"], cols["bldg"], cols["water"], cols["tnm"], y_original):
        set_blocks(region, xi, yi, zi, road_typei, tnm, biome=biome,
                   canyon_layer_map=canyon_layer_map,
                   canyon_layer_thicknesses=canyon_layer_thicknesses)

        if bh > 0:
            for i in range(int((bh - y_orig) * scale)):
                region.set_if_inside(white_concrete, xi, yi + i, zi)
        elif water > 0:
            for i in range(3):  ## 水深3
                region.set_if_inside(water_block, xi, yi - i, zi)
        elif water_level_y is not None and yi < water_level_y:
            for wy in range(yi + 1, water_level_y + 1):
                region.set_if_inside(water_block, xi, wy, zi)

    # atomic save: write temp then rename, so an interrupted run never leaves a
    # half-written region that --resume would mistake for complete.
    tmp_path = region_path + ".tmp"
    region.save(tmp_path)
    os.replace(tmp_path, region_path)
    return ("done", region_path)


def write_extended_height_datapack(output_folder, min_y, height, logical_height, pack_format=12):
    """Write a datapack that overrides ``minecraft:overworld`` with extended height.

    Creates ``<output>/datapacks/extended_height/`` with a ``pack.mcmeta`` and a
    ``data/minecraft/dimension_type/overworld.json`` carrying the raised
    ``min_y``/``height``/``logical_height``. The world must be created with this
    datapack enabled for Minecraft to accept blocks above the vanilla ceiling.
    """
    base = os.path.join(output_folder, "datapacks", "extended_height")
    dim_dir = os.path.join(base, "data", "minecraft", "dimension_type")
    os.makedirs(dim_dir, exist_ok=True)

    mcmeta = {
        "pack": {
            "pack_format": pack_format,
            "description": "Extended world height (1:1 terrain)",
        }
    }
    _atomic_write_json(os.path.join(base, "pack.mcmeta"), mcmeta)

    # Vanilla overworld dimension_type with only the height fields raised.
    overworld = {
        "ultrawarm": False,
        "natural": True,
        "coordinate_scale": 1.0,
        "has_skylight": True,
        "has_ceiling": False,
        "ambient_light": 0.0,
        "monster_spawn_light_level": {
            "type": "minecraft:uniform",
            "value": {"min_inclusive": 0, "max_inclusive": 7},
        },
        "monster_spawn_block_light_limit": 0,
        "piglin_safe": False,
        "bed_works": True,
        "respawn_anchor_works": False,
        "has_raids": True,
        "logical_height": logical_height,
        "min_y": min_y,
        "height": height,
        "infiniburn": "#minecraft:infiniburn_overworld",
        "effects": "minecraft:overworld",
    }
    _atomic_write_json(os.path.join(dim_dir, "overworld.json"), overworld)

    print(f"Wrote extended-height datapack: {base}")
    print("  To use: create a NEW world with this datapack enabled "
          "(World > Data Packs, or place the 'datapacks' folder in the world before first load),")
    print("  then copy the generated 'region' folder into that world.")


def df_to_map(df, road_df=None, bldg_df=None, df_water=None, df_tnm=None, scale=None, biome=None, water_level=None,
              extend_height=False, max_height=None, datapack_format=12, output_folder=None, resume=False, jobs=None):

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

    # 地形の最高 Y（マッピング後）。バニラ上限(319)を超えるなら高さ拡張が必要
    required_max_y = int(math.ceil((max_value - min_value) * scale - 60))
    min_y = anvil.world_height.WORLD_MIN_Y

    if extend_height:
        # 拡張高さの region はバニラでは読めない。datapack を必ず同梱するため出力先は必須。
        if output_folder is None:
            raise ValueError("extend_height requires output_folder so the matching "
                             "dimension datapack can be written alongside the regions")
        # 高さ制限撤廃モード: 既定は構造的上限(2031)まで確保し、地形上に建築余裕を残す
        requested_max_y = anvil.world_height.ABSOLUTE_MAX_Y if max_height is None else int(max_height)
        if requested_max_y < required_max_y:
            raise ValueError(
                f"--max-height ({requested_max_y}) is below the terrain top Y ({required_max_y}); "
                "raise --max-height or lower --scale")
        if requested_max_y > anvil.world_height.ABSOLUTE_MAX_Y:
            raise ValueError(
                f"--max-height ({requested_max_y}) exceeds the structural limit "
                f"{anvil.world_height.ABSOLUTE_MAX_Y}")
        # datapack の height は 16 の倍数。天井を section 境界へ正規化し、effective ceiling
        # (min_y+height-1) を writer・ログ・datapack 共通の唯一の上限とする。
        height = ((requested_max_y - min_y) // 16 + 1) * 16
        logical_height = height
        world_max_y = min_y + height - 1
        anvil.set_world_height(world_max_y)
        # datapack はここでは書かず、resume の整合性検証に通ってから書き出す（下記）。
        datapack_params = (min_y, height, logical_height)
        print(f"Extended height ON: floor Y={min_y}, ceiling Y={world_max_y} "
              f"(datapack height={height}, sections={anvil.world_height.SECTION_COUNT})")
        print(f"Terrain top ~Y={required_max_y}, build headroom ~{world_max_y - required_max_y} blocks")
    else:
        datapack_params = None
        # 通常（バニラ）モード: 直前の拡張実行の状態が同一プロセスに残らないよう毎回リセット
        anvil.set_world_height(anvil.world_height.VANILLA_MAX_Y)
        if required_max_y > anvil.world_height.WORLD_MAX_Y:
            print(f"[WARN] Terrain top Y={required_max_y} exceeds the vanilla limit "
                  f"{anvil.world_height.WORLD_MAX_Y}; everything above will be clipped flat.")
            print("       Pass --extend-height to remove the limit, or lower --scale.")

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
        water_level_y = int(np.clip(water_level_y, anvil.world_height.WORLD_MIN_Y, anvil.world_height.WORLD_MAX_Y))
        print(f"Water level: {water_level}m -> MC Y={water_level_y}")

    # regionごとにグループ分け
    print("Grouping by region...")
    grouped = df.groupby(["region"])
    n_regions = df["region"].nunique()

    # --- 成果物の書き出し前に resume 整合性を検証する（datapack/region/manifest より先） ---
    # 生成設定の manifest。--resume 時に設定が一致しない出力への追記（混在ワールド）を防ぐ。
    manifest = {
        "scale": float(scale),
        "biome": biome,
        "extend_height": bool(extend_height),
        "world_max_y": int(anvil.world_height.WORLD_MAX_Y),
        "water_level": None if water_level is None else float(water_level),
    }
    manifest_path = None
    if output_folder is not None:
        region_dir = os.path.join(output_folder, "region")
        manifest_path = os.path.join(region_dir, "gen_manifest.json")
        if resume:
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    prev = json.load(f)
                if prev != manifest:
                    raise ValueError(
                        "--resume parameters differ from the existing output "
                        f"({prev} != {manifest}); use a fresh --output instead")
            elif glob.glob(os.path.join(region_dir, "r.*.mca")):
                # manifest 無しの既存 region は設定不明 → 混在を防ぐため再開を拒否
                raise ValueError(
                    "--resume found existing regions but no gen_manifest.json (unknown "
                    "config); use a fresh --output or remove the old regions")

        # 検証通過後にのみ書き出す。datapack→manifest の順（どちらも atomic）。
        if datapack_params is not None:
            write_extended_height_datapack(output_folder, *datapack_params, datapack_format)
        _atomic_write_json(manifest_path, manifest)

    # 各 region は一時ファイルへ書いてから atomic rename で確定（=途中保存・中断耐性）。
    # --resume 指定時は、確定済みの region をスキップして続きから生成する。
    active_max_y = anvil.world_height.WORLD_MAX_Y

    def _iter_tasks():
        for _name, group in grouped:
            region_path = _name[0]
            m = re.search(r"r\.(-?\d+)\.(-?\d+)\.mca", region_path)
            rx, ry = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
            cols = {
                "x": group["x"].to_numpy(),
                "y": group["y"].to_numpy(),
                "z": group["z"].to_numpy(),
                "road": group["road"].to_numpy(),
                "bldg": group["bldg"].to_numpy(),
                "water": group["water"].to_numpy(),
                "tnm": group["tnm"].to_numpy(),
            }
            yield (region_path, rx, ry, cols, resume)

    ctx = {
        "min_value": min_value, "scale": scale, "biome": biome,
        "water_level_y": water_level_y,
        "canyon_layer_map": canyon_layer_map,
        "canyon_layer_thicknesses": canyon_layer_thicknesses,
        "active_max_y": active_max_y,
    }

    n_jobs = os.cpu_count() if jobs is None else max(1, int(jobs))
    skipped = 0
    progress = tqdm(total=n_regions, desc="Writing regions", unit="region")
    if n_jobs == 1:
        _worker_init(ctx)
        for task in _iter_tasks():
            status, path = _build_one_region(task)
            if status == "skipped":
                skipped += 1
            progress.set_postfix_str(os.path.basename(path))
            progress.update(1)
    else:
        from multiprocessing import Pool
        print(f"Building regions with {n_jobs} processes...")
        with Pool(processes=n_jobs, initializer=_worker_init, initargs=(ctx,)) as pool:
            for status, path in pool.imap_unordered(_build_one_region, _iter_tasks()):
                if status == "skipped":
                    skipped += 1
                progress.set_postfix_str(os.path.basename(path))
                progress.update(1)
    progress.close()
    if resume and skipped:
        print(f"Resume: skipped {skipped} already-generated regions")


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
    parser.add_argument("--biome", type=str, default=None,
                        choices=["default", "canyon", "desert", "red_desert"],
                        help="ブロックパレット: default=草/土/石, canyon=砂岩/テラコッタ地層, "
                             "desert=砂/砂岩, red_desert=赤砂/赤砂岩")
    parser.add_argument("--water-level", type=float, default=None,
                        help="水面の標高（メートル）。この標高以下の地形に水を充填")
    parser.add_argument("--no-resample", action="store_true",
                        help="1ピクセル=1ブロックのまま（リサンプリングしない）")
    parser.add_argument("--meters-per-block", type=float, default=1.0,
                        help="水平縮尺: 1ブロックが表す実メートル数（既定1.0。例:100で100m/block）")
    parser.add_argument("--smooth", type=float, default=0.0,
                        help="地形の平滑化: 標高にかけるガウシアンのsigma（ブロック単位、既定0=無効。例:1.5）")
    parser.add_argument("--extend-height", action="store_true",
                        help="高さ制限を撤廃（カスタムdimension datapackを出力し、最大Y=2031まで生成）")
    parser.add_argument("--max-height", type=int, default=None,
                        help="--extend-height時の天井Y（省略時は最大の2031）")
    parser.add_argument("--datapack-format", type=int, default=12,
                        help="datapackのpack_format（既定12=MC1.19.4）")
    parser.add_argument("--resume", action="store_true",
                        help="既に書き出し済みのregion(.mca)をスキップして続きから生成")
    parser.add_argument("--jobs", type=int, default=None,
                        help="region生成の並列プロセス数（既定=CPUコア数、1で逐次）")
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
    mpb = args.meters_per_block
    df = tiff_to_frame(tiff_file, output_folder, resample=resample, meters_per_block=mpb,
                       smooth=args.smooth)
    df_road = None
    df_bldg = None
    df_water = None
    df_tnm = None
    # 道路ファイルを読み込む
    if road_file is not None:
        df_road = tiff_to_frame(road_file, output_folder, resample=resample, meters_per_block=mpb)

    if bldg_file is not None:
        df_bldg = tiff_to_frame(bldg_file, output_folder, resample=resample, meters_per_block=mpb)

    if water_file is not None:
        df_water = tiff_to_frame(water_file, output_folder, resample=resample, meters_per_block=mpb)
    if tnm_file is not None:
        df_tnm = tiff_to_frame(tnm_file, output_folder, resample=resample, meters_per_block=mpb)

    # マップを作成
    df_to_map(df, df_road, df_bldg, df_water, df_tnm,
              scale=args.scale, biome=args.biome, water_level=args.water_level,
              extend_height=args.extend_height, max_height=args.max_height,
              datapack_format=args.datapack_format, output_folder=output_folder,
              resume=args.resume, jobs=args.jobs)