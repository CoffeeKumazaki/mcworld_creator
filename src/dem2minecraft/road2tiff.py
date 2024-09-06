import osmium
from PIL import Image, ImageDraw
import rasterio
import tqdm
import numpy as np

# 道路の幅を指定するための辞書
ROAD_WIDTHS = {
    'motorway': 10,
    'trunk': 8,
    'primary': 6,
    'secondary': 4,
    'tertiary': 3,
    'residential': 2,
    'service': 1
}

# ハンドラの定義
class RoadHandler(osmium.SimpleHandler):
    def __init__(self, min_lat, max_lat, min_lon, max_lon):
        osmium.SimpleHandler.__init__(self)
        self.roads = []
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon

    def is_in_bbox(self, lat, lon):
        return (self.min_lat <= lat <= self.max_lat) and (self.min_lon <= lon <= self.max_lon)

    def way(self, w):
        # "highway" タグが含まれているものが道路とみなされる
        if 'highway' in w.tags:
            for node in w.nodes:
                try:
                    # ノードの位置が有効かどうか確認
                    if node.location.valid() and self.is_in_bbox(node.lat, node.lon):
                        self.roads.append({
                            'highway_type': w.tags['highway'],
                            'nodes': [(n.lat, n.lon) for n in w.nodes if n.location.valid()]
                        })
                        break  # 範囲内のノードが見つかればそれ以上はチェックしない
                except osmium._osmium.InvalidLocationError:
                    # 無効なノードはスキップ
                    continue

# OSMファイルを解析して道路情報を抽出
def extract_roads_in_bbox(osm_file, min_lat, max_lat, min_lon, max_lon):
    handler = RoadHandler(min_lat, max_lat, min_lon, max_lon)
    handler.apply_file(osm_file, locations=True)
    return handler.roads

# 緯度経度範囲の指定
## min_lat = 35.0  # 下限緯度
## max_lat = 36.0  # 上限緯度
## min_lon = 139.0  # 下限経度
## max_lon = 140.0  # 上限経度

# 緯度経度を画像座標に変換する関数
def latlon_to_pixel(lat, lon, min_lat, max_lat, min_lon, max_lon, width, height):
    x = int((lon - min_lon) / (max_lon - min_lon) * width)
    y = int((max_lat - lat) / (max_lat - min_lat) * height)
    return x, y

def road_to_tiff(osm_file, min_lat, max_lat, min_lon, max_lon, output_tiff):
    # 道路データを取得
    roads = extract_roads_in_bbox(osm_file, min_lat, max_lat, min_lon, max_lon)

    # 画像サイズの設定
    width, height = 1024, 1024
    img = Image.new('L', (width, height), 0)  # 'L'はグレースケールモード
    draw = ImageDraw.Draw(img)

    # 道路を描画
    for road in tqdm.tqdm(roads):
        road_type = road['highway_type']
        road_width = ROAD_WIDTHS.get(road_type, 1)  # デフォルト幅は1
        nodes = road['nodes']
        for i in range(len(nodes) - 1):
            x1, y1 = latlon_to_pixel(nodes[i][0], nodes[i][1], min_lat, max_lat, min_lon, max_lon, width, height)
            x2, y2 = latlon_to_pixel(nodes[i+1][0], nodes[i+1][1], min_lat, max_lat, min_lon, max_lon, width, height)
            draw.line((x1, y1, x2, y2), fill=255, width=road_width)

    # Pillowの画像をNumPy配列に変換
    image_array = np.array(img)

    # GeoTIFFに保存
    with rasterio.open(
        output_tiff,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=image_array.dtype,
        crs='+proj=latlong',
        transform=rasterio.transform.from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)
    ) as dst:
        dst.write(image_array, 1)

    print(f"GeoTIFFファイル '{output_tiff}' が生成されました。")


if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--osm", required=True, help="OSM file path")
    parser.add_argument("--output", required=True, help="output GeoTIFF file path")
    parser.add_argument("--min_lat", required=True, type=float, help="min latitude")
    parser.add_argument("--max_lat", required=True, type=float, help="max latitude")
    parser.add_argument("--min_lon", required=True, type=float, help="min longitude")
    parser.add_argument("--max_lon", required=True, type=float, help="max longitude")

    args = parser.parse_args()

    road_to_tiff(args.osm, args.min_lat, args.max_lat, args.min_lon, args.max_lon, args.output)

