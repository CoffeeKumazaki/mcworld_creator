import os
import re
import rasterio
import numpy as np
import pandas as pd


def tiff_to_frame(tiff_file, output_folder):
    with rasterio.open(tiff_file) as src:

        # 幅と高さを取得
        width, height = src.width, src.height
        print(f"width: {width}, height: {height}")

        # 中心点のオフセットを計算
        # 偶数の場合は0.5、奇数の場合は0
        offset_x = 0.5 if width % 2 == 0 else 0
        offset_y = -0.5 if height % 2 == 0 else 0

        # トランスフォーメーション行列から中心座標を計算
        transform = src.transform
        # center_x = transform.c + width / 2.0 * transform.a + offset_x
        # center_y = transform.f + height / 2.0 * transform.e + offset_y
        center_x = width / 2.0 + offset_x
        center_y = height / 2.0 + offset_y

        # 数値標高データを取得
        data = src.read(1)

        # 各ピクセルの中心座標を取得
        y_indices, x_indices = np.indices(data.shape)
        #x_coords = x_indices * transform.a + transform.c + transform.a / 2.0
        #y_coords = y_indices * transform.e + transform.f + transform.e / 2.0

        # xmin, ymax はアフィン変換の左上の座標
        xmin, ymax = transform * (0, 0)
        # xmax, ymin はアフィン変換の右下の座標
        xmax, ymin = transform * (width, height)

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

        # 文字列に変換
        ## region_x_str = np.char.mod("%d", region_x)
        ## region_z_str = np.char.mod("%d", region_z)

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

# 3種類の草を定義
grass_plant = anvil.Block("minecraft", "grass")
tall_grass_l = anvil.Block("minecraft", "tall_grass", properties={"half": "lower"})
tall_grass_u = anvil.Block("minecraft", "tall_grass", properties={"half": "upper"})

# ブロックを設置する処理
def set_blocks(region, x, y, z, road_type=0, tnm_class=0):

    height_limit = 319
    height = np.clip(y, -64, height_limit)
    height = int(height)

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
    

def df_to_map(df, road_df=None, bldg_df=None, df_water=None, df_tnm=None):

    # 0より大きい値の最小値を取得
    min_value = df[df['y'] > 0]['y'].min()
    max_value = df['y'].max()
    print(f"min: {min_value}, max: {max_value}")

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
        y = group["y"] - min_value - 60
        z = group["z"]
        road_type = group["road"]
        bldg_height = group["bldg"]
        is_water = group["water"]
        tnm_class = group["tnm"]

        for xi, yi, zi, road_typei, bh, water, tnm in zip(x, y, z, road_type, bldg_height, is_water, tnm_class):
            set_blocks(region, xi, yi, zi, road_typei, tnm)

            if bh > 0:
                org_alt = yi + min_value + 60
                for i in range(int(bh - org_alt)):
                    region.set_block(white_concrete, xi, yi + i, zi)
            elif water > 0:
                for i in range(3): ## 水深3
                    region.set_block(water_block, xi, yi - i, zi)

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
    args = parser.parse_args()

    tiff_file = args.tiff
    road_file = args.road
    bldg_file = args.bldg
    water_file = args.water
    tnm_file = args.tnm
    output_folder = args.output
    os.makedirs(output_folder, exist_ok=True)

    # tiffファイルを読み込む
    print(f"Reading tiff file: {tiff_file}")
    df = tiff_to_frame(tiff_file, output_folder)
    df_road = None
    df_bldg = None
    df_water = None
    df_tnm = None
    # 道路ファイルを読み込む
    if road_file is not None:
        df_road = tiff_to_frame(road_file, output_folder)

    if bldg_file is not None:
        df_bldg = tiff_to_frame(bldg_file, output_folder)

    if water_file is not None:
        df_water = tiff_to_frame(water_file, output_folder)
    if tnm_file is not None:
        df_tnm = tiff_to_frame(tnm_file, output_folder)

    # マップを作成
    df_to_map(df, df_road, df_bldg, df_water, df_tnm)