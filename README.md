# minecraft_world_builder

```
docker build -t world_builder ./
```


## データ
### 基盤地図情報 ダウンロードサービス
- https://fgd.gsi.go.jp/download/menu.php
### OpenStreetMap 日本地図データダウンロード
- ここから全Regionの .osm.pbf をダウンロード
- https://download.geofabrik.de/asia/japan.html


## 使い方
- DEMデータ（標高データ）をダウンロード
- DEMデータをtiff形式に変換
    ```
    python dem2minecraft \
    --dem ./data/dem/FG-GML-5135-63-DEM5A/ \
    --tiff ./data/output/dem/FG-GML-5135-63-DEM5A/
    ```
- DEM tiffを1つのDEMにまとめる
    ```
    gdal_merge.py \
    -o data/output/dem/Hirakawacho.tiff  \
    -ot Float32 -co COMPRESS=LZW \
    data/output/dem/FG-GML-5135-63-DEM5A/*
  ```
- 道路データをtiff形式に変換
  - road2tiff.pyを実行
  ```
  python dem2minecraft/road2tiff.py \
  --osm ./data/osm/kanto-latest.osm.pbf \ 
  --min_lon 139.7250000 \
  --max_lon 139.7500000 \
  --min_lat 35.6750000 \
  --max_lat 35.6916667 \
  --output ./data/output/road/hirakawacho_rail.tiff
  ```
- 建物データをtiff形式に保存
  - citygml2tiff.py を実行
  ```
  python dem2minecraft/citygml2tiff.py --input data/gml/24202_yokkaichi-shi_2022_citygml_1_op/udx/bldg/ \
  --max_lat 34.97094 \
  --max_lon 136.63632 \
  --min_lat 34.95882 \
  --min_lon 136.61486 \
  --width 2146 \
  --height 1212 \ 
  --output data/output/bldg/yokkaichi.tiff
  ```

- tiff形式のデータを元にマインクラフトのワールドを生成
    ```
    python dem2minecraft/make_minecraft_world.py \
    --tiff data/output/dem/Hirakawacho.tiff \
    --output data/output/world_data/hirakawacho \
    --bldg data/output/bldg/hikarawacho_bldg.tiff \
    --road ./data/output/road/hirakawacho_rail.tiff 
    ```