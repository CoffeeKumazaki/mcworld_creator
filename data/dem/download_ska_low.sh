#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Download DEM for SKA-Low / Murchison Radio-astronomy Observatory
# Source: OpenTopography Global DEM API
# DEM: Copernicus GLO-30 / COP30
# Output: GeoTIFF
# ============================================================

# Load .env if it exists
if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

API_KEY="${OPENTOPOLOGY_API_KEY:-}"

if [ -z "$API_KEY" ]; then
  echo "Error: OPENTOPOLOGY_API_KEY is not set."
  echo "Please add OPENTOPOLOGY_API_KEY=your_key to .env"
  exit 1
fi

DEM_TYPE="${DEM_TYPE:-COP30}"
OUTPUT_DIR="${OUTPUT_DIR:-dem}"
OUTPUT_FILE="${OUTPUT_FILE:-ska_low_australia_cop30.tif}"

# Approx. 80 km x 80 km around MRO / SKA-Low area
# Center approx: lat -26.7033, lon 116.6708
SOUTH="${SOUTH:--27.063}"
NORTH="${NORTH:--26.343}"
WEST="${WEST:-116.266}"
EAST="${EAST:-117.076}"

BASE_URL="https://portal.opentopography.org/API/globaldem"

mkdir -p "$OUTPUT_DIR"

echo "Downloading DEM..."
echo "  Site: SKA-Low / Australia"
echo "  DEM: $DEM_TYPE"
echo "  BBOX: west=$WEST south=$SOUTH east=$EAST north=$NORTH"
echo "  Output: $OUTPUT_DIR/$OUTPUT_FILE"

curl -fL \
  --get "$BASE_URL" \
  --data-urlencode "demtype=$DEM_TYPE" \
  --data-urlencode "south=$SOUTH" \
  --data-urlencode "north=$NORTH" \
  --data-urlencode "west=$WEST" \
  --data-urlencode "east=$EAST" \
  --data-urlencode "outputFormat=GTiff" \
  --data-urlencode "API_Key=$API_KEY" \
  -o "$OUTPUT_DIR/$OUTPUT_FILE"

echo "Done: $OUTPUT_DIR/$OUTPUT_FILE"