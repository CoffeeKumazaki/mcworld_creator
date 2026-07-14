#!/bin/bash
# build_ska_mid.sh
# SKA-Mid コア領域を Minecraft ワールド化する再現スクリプト（実寸1m/block・実地形）。
#
# 生成物: build/ska_mid_core_5km/world  （そのまま .minecraft/saves/ にコピーで遊べる）
#
# 使う実データ（すべてコミット済み。tif本体はgitignoreなので data/dem/dem/ の
# COP30 DEM だけ別途 ./data/dem/download_ska_mid.sh で取得しておくこと）:
#   - data/dem/dem/ska_mid_south_africa_cop30.tif : Copernicus GLO-30 DEM（30m, 160km）
#   - data/ska/ska_mid_map.osm                    : Karoo/MeerKAT周辺のOSM抽出（道路）
#   - data/ska/ska_mid_antennas.csv               : 197基のディッシュ座標（label,lon,lat）
#
# レシピ（2026-07 ユーザ承認・ビルド検証済み）:
#   コア中心の 5km 四方だけを 1ブロック=1m で切り出す。30m DEM を 5000x5000 へ約30倍
#   アップサンプル（cubic）し、tool側 --smooth でガウシアン平滑化して滑らかな高原に。
#   5km窓の標高差は約130mでバニラ高さ内 → datapack不要。窓内140/197基を配置。
#     地面   = red_desert（赤砂/赤砂岩/橙テラコッタ）
#     道路   = OSM highway を幅3で gray_concrete_powder
#     土台   = 各ディッシュに半径7の円盤(mesh)を gray_concrete_powder
#     マーカー = ディッシュ中心に sea_lantern
#
# 実行: ./build_ska_mid.sh          （ローカルのuvで依存を解決して実行）
# 依存: uv（無ければ https://docs.astral.sh/uv/ ）。GDAL等はwheelで入る。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ================= パラメータ（必要ならここだけ編集） =================
CENTER_LAT=-30.713          # SKA-Mid 配列コア中心
CENTER_LON=21.444
SIZE=5000                   # マップ一辺[m] = ブロック数（1m/block）。例:2000で軽量版
SMOOTH=10                   # 地形平滑化ガウシアンsigma[block]（30m→1m補間の段差を丸める）
PAD_RADIUS=7                # アンテナ土台の円盤半径[block]（直径~15m=ディッシュ相当）
BIOME=red_desert            # 赤砂（red_sand/red_sandstone/orange_terracotta）
ANTENNA_BLOCK=sea_lantern   # ディッシュ位置マーカー
ROAD_BLOCK=gray_concrete_powder   # OSM highway（幅3）
MESH_BLOCK=gray_concrete_powder   # アンテナ土台の円盤

OUT="$ROOT/build/ska_mid_core_5km"
DEM_SRC="$ROOT/data/dem/dem/ska_mid_south_africa_cop30.tif"
OSM="$ROOT/data/ska/ska_mid_map.osm"
ANTENNAS="$ROOT/data/ska/ska_mid_antennas.csv"
UV_DEPS="--with rasterio --with scipy --with numpy --with pandas --with pillow --with osmium --with tqdm --with NBT --with lxml"
# =====================================================================

mkdir -p "$OUT"

echo "[1/2] 前処理: DEM(5000x5000へアップサンプル) / 道路(幅3) / 土台(円盤) TIFF を生成..."
uv run $UV_DEPS python - "$CENTER_LAT" "$CENTER_LON" "$SIZE" "$PAD_RADIUS" \
        "$DEM_SRC" "$OSM" "$ANTENNAS" "$OUT" "$ROOT/src/dem2minecraft" <<'PY'
import sys, math, numpy as np, rasterio
from rasterio.windows import from_bounds
from scipy.ndimage import zoom, binary_dilation
from PIL import Image, ImageDraw

clat, clon, N, pad_r = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
dem_src, osm, antennas, out, src_dir = sys.argv[5:10]
sys.path.insert(0, src_dir)

# --- bbox（中心±SIZE/2 [m]）を 5km 四方の地上正方形として取る ---
half = N / 2.0
dlat = half / 110540.0
dlon = half / (111320.0 * math.cos(math.radians(clat)))
W, E, S, Nn = clon - dlon, clon + dlon, clat - dlat, clat + dlat
tr = rasterio.transform.from_bounds(W, S, E, Nn, N, N)
prof = dict(driver="GTiff", height=N, width=N, count=1, dtype="uint8",
            crs="EPSG:4326", transform=tr)
print(f"  bbox {2*dlon*111320*math.cos(math.radians(clat)):.0f}x{2*dlat*110540:.0f}m")

def to_px(lat, lon):
    return (lon - W) / (E - W) * N, (Nn - lat) / (Nn - S) * N

# --- 1) 実DEMを窓で切り出し → NxN へ cubic アップサンプル（平滑化はtool側--smooth） ---
with rasterio.open(dem_src) as s:
    win = from_bounds(W, S, E, Nn, s.transform)
    dem = s.read(1, window=win).astype("float32")
up = zoom(dem, (N / dem.shape[0], N / dem.shape[1]), order=3).astype("float32")
with rasterio.open(f"{out}/dem_1m.tif", "w", driver="GTiff", height=N, width=N,
                   count=1, dtype="float32", crs="EPSG:4326", transform=tr) as d:
    d.write(up, 1)
print(f"  DEM {dem.shape[1]}x{dem.shape[0]} -> {N}x{N}  elev {up.min():.0f}-{up.max():.0f}m")

# --- 2) 道路（OSM highway）→ road2tiff → 3px膨張（=幅3） ---
from road2tiff import road_to_tiff
road_to_tiff(osm, f"{out}/road_1m.tif", S, Nn, W, E, N, N)
with rasterio.open(f"{out}/road_1m.tif") as r:
    a = r.read(1); rp = r.profile
dil = np.where(binary_dilation(a > 200, np.ones((3, 3), bool)), 255, 0).astype("uint8")
with rasterio.open(f"{out}/road_1m.tif", "w", **rp) as d:
    d.write(dil, 1)
print(f"  road px(w3): {int((dil>0).sum())}")

# --- 3) 土台(mesh): 各ディッシュ中心に半径 pad_r の円盤 ---
import pandas as pd
p = pd.read_csv(antennas)
img = Image.new("L", (N, N), 0); dr = ImageDraw.Draw(img); n = 0
for lon, lat in zip(p.lon, p.lat):
    x, y = to_px(lat, lon)
    if -pad_r <= x <= N + pad_r and -pad_r <= y <= N + pad_r:
        dr.ellipse([x-pad_r, y-pad_r, x+pad_r, y+pad_r], fill=255); n += 1
with rasterio.open(f"{out}/pad_1m.tif", "w", **prof) as d:
    d.write(np.array(img, "uint8"), 1)
print(f"  pad disks: {n} dishes (r={pad_r})")
PY

echo "[2/2] ワールド生成..."
rm -rf "$OUT/world"
cd "$ROOT/src/dem2minecraft"
uv run $UV_DEPS python make_minecraft_world.py \
  --tiff "$OUT/dem_1m.tif" \
  --road "$OUT/road_1m.tif" --road-block "$ROAD_BLOCK" \
  --mesh "$OUT/pad_1m.tif"  --mesh-block "$MESH_BLOCK" \
  --antennas "$ANTENNAS" --antenna-block "$ANTENNA_BLOCK" \
  --no-resample --scale 1.0 --biome "$BIOME" --smooth "$SMOOTH" \
  --output "$OUT/world" --jobs 3

echo "完了: $OUT/world  （.minecraft/saves/ にコピー。スポーン付近=コア中心, 地表y=-60〜）"
