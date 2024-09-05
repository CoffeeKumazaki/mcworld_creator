# ライブラリのインポート
import rasterio
import numpy as np
import pandas as pd


def tiff_to_frame(tiff_file):
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

        # ピクセル座標と標高値を一次元化
        x_coords = x_indices.ravel()
        y_coords = y_indices.ravel()
        data = data.ravel()

        # マイクラの基準にする中心の座標を引く
        x_coords = x_coords - center_x
        y_coords = y_coords - center_y

        # y軸(北南)を反転。マイクラ座標に合わせるため
        y_coords = y_coords * -1

        # 小数点以下を排除
        x_coords = np.trunc(x_coords).astype(int)
        y_coords = np.trunc(y_coords).astype(int)
        data = np.trunc(data).astype(int)

        # マイクラのブロック座標からregion(.mca)のファイル名を取得
        region_x = (x_coords // 512).astype(int)
        region_z = (y_coords // 512).astype(int)

        # 文字列に変換
        region_x_str = np.char.mod("%d", region_x)
        region_z_str = np.char.mod("%d", region_z)

        # ベクトル化した文字列フォーマット操作を適用
        region = np.vectorize("r.{}.{}.mca".format)(region_x, region_z)

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

# 3種類の草を定義
grass_plant = anvil.Block("minecraft", "grass")
tall_grass_l = anvil.Block("minecraft", "tall_grass", properties={"half": "lower"})
tall_grass_u = anvil.Block("minecraft", "tall_grass", properties={"half": "upper"})

# ブロックを設置する処理
def set_blocks(region, x, y, z):

    # 319以下の場合にブロック設置を開始
    if y <= 319:
        # 設定するブロックのリスト(草ブロック１、土ブロック１、石ブロック３のレイヤーをつくる)
        blocks = [grass, dirt, stone, stone, stone]

        # 5%の確率で草を生やす
        if random.random() > 0.95 and y < 319:
            region.set_block(random.choice([grass_plant, tall_grass_l, tall_grass_u]), x, y + 1, z)

        # ブロックのレイヤーを設置する。ブロック設置ができない範囲はbreakで抜ける
        for i, block in enumerate(blocks):
            if -64 <= y - i <= 319:
                region.set_block(block, x, y - i, z)
            else:
                break

def df_to_map(df):

    # 0より大きい値の最小値を取得
    min_value = df[df['y'] > 0]['y'].min()
    max_value = df['y'].max()
    print(f"min: {min_value}, max: {max_value}")

    # yが0の行に64を加算
    df['y'] = df['y'].replace(0, min_value)
    # df.mask(df["y"] == 0, min_value, inplace=True)

    # regionごとにグループ分け
    grouped = df.groupby(["region"])

    for _name, group in grouped:
        # 先頭行をスキップ
        group = group.iloc[1:]

        # regionを作成
        region = anvil.EmptyRegion(0, 0)
        x = group["x"] % 512
        y = group["y"] - min_value - 64
        z = group["z"] % 512

        for xi, yi, zi in zip(x, y, z):
            set_blocks(region, xi, yi, zi)

        # regionを保存
        region.save(group.iloc[1]["region"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiff", required=True, help="tiff file path")
    args = parser.parse_args()

    tiff_file = args.tiff

    # tiffファイルを読み込む
    df = tiff_to_frame(tiff_file)

    # マップを作成
    df_to_map(df)