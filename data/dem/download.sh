#!/usr/bin/env bash
# Grand Canyon DEM データダウンロードスクリプト
# USGS 3D Elevation Program (3DEP) 1/3 arc-second (~10m) DEM
# https://apps.nationalmap.gov/downloader/
#
# Usage: bash data/dem/download.sh

set -euo pipefail
cd "$(dirname "$0")"

BASE_URL="https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current"

# Grand Canyon Village 周辺 (約20km範囲)
# USGS 1/3 arc-second DEM タイル: n37w113
TILE="n37w113"
FILENAME="USGS_13_${TILE}.tif"
OUTPUT="grand_canyon_village_20km_raw_usgs10m.tif"

if [ -f "$OUTPUT" ]; then
    echo "$OUTPUT already exists, skipping download."
else
    echo "Downloading ${FILENAME} ..."
    curl -fSL -o "$OUTPUT" "${BASE_URL}/${TILE}/${FILENAME}"
    echo "Saved to $OUTPUT"
fi

# 必要に応じて小範囲を切り出す場合:
# gdal_translate -projwin <ulx> <uly> <lrx> <lry> "$OUTPUT" grand_canyon_village_2km_usgs10m.tif
echo ""
echo "To clip a smaller area, use gdal_translate:"
echo "  gdal_translate -projwin -112.15 36.07 -112.13 36.05 $OUTPUT grand_canyon_village_2km_usgs10m.tif"
