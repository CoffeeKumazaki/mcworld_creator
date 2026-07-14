#!/bin/bash
# build_ska_low.sh
# SKA-Low コア領域を Minecraft ワールド化する再現スクリプト（フラット・実寸1m/block）。
#
# 生成物: build/ska_low_core_5km/world  （そのまま .minecraft/saves/ にコピーで遊べる）
#
# 使う実データ（すべてコミット済み。追加DL不要）:
#   - data/dem/dem/ska_low_australia_cop30.tif  : Copernicus GLO-30 DEM（30m）
#   - data/ska/ska_low_map.osm                  : MRO周辺のOSM抽出（道路/飛行場/造成/建物）
#   - data/ska/ska_low_dipoles_latlon.csv       : 全ダイポール素子の緯度経度（label,lon,lat）
#
# ダイポールCSVの由来（再取得したい場合のメモ。通常は不要）:
#   SKAO配布の OSKAR telescope model "SKA1-LOW_SKO-0000422_Rev3_38m.tm"
#   （Google Drive folder id 1tq8jF0myYyk2BRgAaAyFlb4PcGzWXUtB 内の
#    SKA1-LOW_SKO-0000422_Rev3_38m.tm.zip、file id 1qPJIjRGdoU-W4AwGHy9Jkm3ycDDjBITl）
#   の各 stationNNN/layout.txt（局中心ENU[m]）を局中心(layout_wgs84.txt)で緯度経度化したもの。
#   station中心はこのCSVのラベル接頭辞 "sIDX_" から復元できるので本スクリプトは.tm不要。
#
# 実行: ./build_ska_low.sh          （ローカルのuvで依存を解決して実行）
# 依存: uv（無ければ https://docs.astral.sh/uv/ ）。GDAL等はwheelで入る。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ================= パラメータ（必要ならここだけ編集） =================
CENTER_LAT=-26.82472208     # SKA-Low 配列中心（position.txt）
CENTER_LON=116.7644482
SIZE=5000                   # マップ一辺[m] = ブロック数（1m/block）。例:2000で軽量版
FLAT_ELEV=362               # フラット地形の標高[m]（実標高357-366のほぼ平坦を代表）
MESH_RADIUS=21              # グラウンドプレーン半径[block]（直径42m）
BIOME=red_desert            # 赤砂（red_sand/red_sandstone）
ANTENNA_BLOCK=sea_lantern   # ダイポール素子マーカー
ROAD_BLOCK=packed_mud       # 未舗装道（OSM highway）
PAD_BLOCK=smooth_sandstone  # 滑走路・apron・造成地・建物
MESH_BLOCK=iron_block       # 金網グラウンドプレーン（後でカスタムブロックに差替可）

OUT="$ROOT/build/ska_low_core_5km"
DEM_SRC="$ROOT/data/dem/dem/ska_low_australia_cop30.tif"
OSM="$ROOT/data/ska/ska_low_map.osm"
DIPOLES="$ROOT/data/ska/ska_low_dipoles_latlon.csv"
UV_DEPS="--with rasterio --with scipy --with numpy --with pandas --with pillow --with osmium --with tqdm --with NBT --with lxml"
# =====================================================================

mkdir -p "$OUT"

echo "[1/2] 前処理: フラットDEM / 道路 / pad(飛行場・造成) / mesh(円盤) TIFF を生成..."
uv run $UV_DEPS python - "$CENTER_LAT" "$CENTER_LON" "$SIZE" "$FLAT_ELEV" "$MESH_RADIUS" \
        "$DEM_SRC" "$OSM" "$DIPOLES" "$OUT" "$ROOT/src/dem2minecraft" <<'PY'
import sys, math, numpy as np, rasterio
from PIL import Image, ImageDraw
from lxml import etree

clat, clon, N, flat_elev, mesh_r = (float(sys.argv[1]), float(sys.argv[2]),
    int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]))
dem_src, osm, dipoles, out, src_dir = sys.argv[6:11]
sys.path.insert(0, src_dir)

# --- bbox（中心±SIZE/2 [m]）---
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

# --- 1) フラットDEM ---
with rasterio.open(f"{out}/dem_flat.tif", "w", driver="GTiff", height=N, width=N,
                   count=1, dtype="float32", crs="EPSG:4326", transform=tr) as d:
    d.write(np.full((N, N), flat_elev, "float32"), 1)

# --- 2) 道路（OSM highway）→ road2tiff → 3px膨張 ---
from road2tiff import road_to_tiff
from scipy.ndimage import binary_dilation
road_to_tiff(osm, f"{out}/road_1m.tif", S, Nn, W, E, N, N)
with rasterio.open(f"{out}/road_1m.tif") as r:
    a = r.read(1); rp = r.profile
dil = np.where(binary_dilation(a > 200, np.ones((3, 3), bool)), 255, 0).astype("uint8")
with rasterio.open(f"{out}/road_1m.tif", "w", **rp) as d:
    d.write(dil, 1)
print(f"  road px(3px): {int((dil>0).sum())}")

# --- 3) pad: 飛行場(runway/taxiway/apron)・造成(construction)・建物(building) ---
root = etree.parse(osm).getroot()
nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.iter("node")}
img = Image.new("L", (N, N), 0); dr = ImageDraw.Draw(img); cnt = {}
for w in root.iter("way"):
    tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
    pts = [to_px(*nodes[nd.get("ref")]) for nd in w.findall("nd") if nd.get("ref") in nodes]
    if len(pts) < 2:
        continue
    aw, lu, bld = tags.get("aeroway"), tags.get("landuse"), tags.get("building")
    key = None
    if aw == "runway":     dr.line(pts, fill=255, width=30); key = "runway"
    elif aw == "taxiway":  dr.line(pts, fill=255, width=12); key = "taxiway"
    elif aw == "apron":    dr.polygon(pts, fill=255); key = "apron"
    elif lu == "construction": dr.polygon(pts, fill=255); key = "construction"
    elif bld:              dr.polygon(pts, fill=255); key = "building"
    if key: cnt[key] = cnt.get(key, 0) + 1
with rasterio.open(f"{out}/pad_1m.tif", "w", **prof) as d:
    d.write(np.array(img, "uint8"), 1)
print(f"  pad features: {cnt}")

# --- 4) mesh: 局中心（ダイポールCSVのラベル接頭辞から復元）に半径Rの円盤 ---
import pandas as pd
p = pd.read_csv(dipoles)
p["st"] = p["label"].str.rsplit("_", n=1).str[0]
centers = p.groupby("st")[["lon", "lat"]].mean()
img = Image.new("L", (N, N), 0); dr = ImageDraw.Draw(img); n_st = 0
for lon, lat in centers.itertuples(index=False):
    x, y = to_px(lat, lon)
    if -mesh_r <= x <= N + mesh_r and -mesh_r <= y <= N + mesh_r:
        dr.ellipse([x-mesh_r, y-mesh_r, x+mesh_r, y+mesh_r], fill=255); n_st += 1
with rasterio.open(f"{out}/mesh_1m.tif", "w", **prof) as d:
    d.write(np.array(img, "uint8"), 1)
print(f"  mesh disks: {n_st} stations (r={mesh_r})")
PY

echo "[2/2] ワールド生成..."
rm -rf "$OUT/world"
cd "$ROOT/src/dem2minecraft"
uv run $UV_DEPS python make_minecraft_world.py \
  --tiff "$OUT/dem_flat.tif" \
  --road "$OUT/road_1m.tif" \
  --pad  "$OUT/pad_1m.tif"  --pad-block  "$PAD_BLOCK" \
  --mesh "$OUT/mesh_1m.tif" --mesh-block "$MESH_BLOCK" \
  --antennas "$DIPOLES" \
  --antenna-block "$ANTENNA_BLOCK" --road-block "$ROAD_BLOCK" \
  --scale 1.0 --no-resample --biome "$BIOME" \
  --output "$OUT/world" --jobs 4

echo "完了: $OUT/world  （.minecraft/saves/ にコピー。スポーン付近=コア中心, 地表y=-60）"
