#!/bin/bash

# TIFFファイルから指定した緯度経度範囲の切り抜きサイズを計算するスクリプト
# 使用方法: ./tiff_crop_calculator.sh <tiff_file> <top_lat> <left_lon> <bottom_lat> <right_lon>

if [ $# -ne 5 ]; then
    echo "使用方法: $0 <tiff_file> <top_lat> <left_lon> <bottom_lat> <right_lon>"
    echo "例: $0 input.tif 36.5 139.5 35.5 140.5"
    exit 1
fi

TIFF_FILE=$1
TOP_LAT=$2
LEFT_LON=$3
BOTTOM_LAT=$4
RIGHT_LON=$5

# gdalinfoコマンドが必要
if ! command -v gdalinfo &> /dev/null; then
    echo "エラー: gdalinfoコマンドが見つかりません。GDALをインストールしてください。"
    echo "例: sudo apt-get install gdal-bin"
    exit 1
fi

# TIFFファイルの情報を取得
echo "TIFFファイル情報を取得中..."
TIFF_INFO=$(gdalinfo "$TIFF_FILE")

# 画像の幅と高さを取得
SIZE_LINE=$(echo "$TIFF_INFO" | grep "Size is")
WIDTH=$(echo "$SIZE_LINE" | awk '{print $3}' | sed 's/,//')
HEIGHT=$(echo "$SIZE_LINE" | awk '{print $4}')

# Corner Coordinatesから座標を直接取得する
UPPER_LEFT_LINE=$(echo "$TIFF_INFO" | grep "Upper Left")
UPPER_LEFT_LON=$(echo "$UPPER_LEFT_LINE" | awk '{print $4}' | sed 's/[(),]//g')
UPPER_LEFT_LAT=$(echo "$UPPER_LEFT_LINE" | awk '{print $5}' | sed 's/[(),]//g')

LOWER_RIGHT_LINE=$(echo "$TIFF_INFO" | grep "Lower Right")
LOWER_RIGHT_LON=$(echo "$LOWER_RIGHT_LINE" | awk '{print $4}' | sed 's/[(),]//g')
LOWER_RIGHT_LAT=$(echo "$LOWER_RIGHT_LINE" | awk '{print $5}' | sed 's/[(),]//g')

# ピクセルサイズを計算
PIXEL_WIDTH=$(awk -v ul="$UPPER_LEFT_LON" -v lr="$LOWER_RIGHT_LON" -v w="$WIDTH" 'BEGIN {print (lr - ul) / w}')
PIXEL_HEIGHT=$(awk -v ul="$UPPER_LEFT_LAT" -v lr="$LOWER_RIGHT_LAT" -v h="$HEIGHT" 'BEGIN {print (lr - ul) / h}')

echo "元画像情報:"
echo "サイズ: ${WIDTH}x${HEIGHT}ピクセル"
echo "左上座標 (経度,緯度): ($UPPER_LEFT_LON, $UPPER_LEFT_LAT)"
echo "右下座標 (経度,緯度): ($LOWER_RIGHT_LON, $LOWER_RIGHT_LAT)"
echo "ピクセルサイズ (経度,緯度): ($PIXEL_WIDTH, $PIXEL_HEIGHT)"

# 指定された緯度経度範囲のチェック
if $(awk -v left="$LEFT_LON" -v ul_lon="$UPPER_LEFT_LON" 'BEGIN {exit !(left < ul_lon)}'); then
    echo "警告: 指定された左経度が元画像の範囲を超えています"
fi
if $(awk -v right="$RIGHT_LON" -v lr_lon="$LOWER_RIGHT_LON" 'BEGIN {exit !(right > lr_lon)}'); then
    echo "警告: 指定された右経度が元画像の範囲を超えています"
fi
if $(awk -v bottom="$BOTTOM_LAT" -v lr_lat="$LOWER_RIGHT_LAT" 'BEGIN {exit !(bottom < lr_lat)}'); then
    echo "警告: 指定された下緯度が元画像の範囲を超えています"
fi
if $(awk -v top="$TOP_LAT" -v ul_lat="$UPPER_LEFT_LAT" 'BEGIN {exit !(top > ul_lat)}'); then
    echo "警告: 指定された上緯度が元画像の範囲を超えています"
fi

# ピクセル座標に変換
echo "デバッグ: 座標変換計算"
echo "LEFT_LON=$LEFT_LON, UPPER_LEFT_LON=$UPPER_LEFT_LON, PIXEL_WIDTH=$PIXEL_WIDTH"
echo "TOP_LAT=$TOP_LAT, UPPER_LEFT_LAT=$UPPER_LEFT_LAT, PIXEL_HEIGHT=$PIXEL_HEIGHT"
echo "RIGHT_LON=$RIGHT_LON, BOTTOM_LAT=$BOTTOM_LAT"

LEFT_PIXEL=$(awk -v left="$LEFT_LON" -v ul_lon="$UPPER_LEFT_LON" -v pw="$PIXEL_WIDTH" 'BEGIN {result = int((left - ul_lon) / pw + 0.5); print result}')
TOP_PIXEL=$(awk -v top="$TOP_LAT" -v ul_lat="$UPPER_LEFT_LAT" -v ph="$PIXEL_HEIGHT" 'BEGIN {result = int((top - ul_lat) / ph + 0.5); print result}')
RIGHT_PIXEL=$(awk -v right="$RIGHT_LON" -v ul_lon="$UPPER_LEFT_LON" -v pw="$PIXEL_WIDTH" 'BEGIN {result = int((right - ul_lon) / pw + 0.5); print result}')
BOTTOM_PIXEL=$(awk -v bottom="$BOTTOM_LAT" -v ul_lat="$UPPER_LEFT_LAT" -v ph="$PIXEL_HEIGHT" 'BEGIN {result = int((bottom - ul_lat) / ph + 0.5); print result}')

echo "初期ピクセル座標計算結果:"
echo "LEFT_PIXEL=$LEFT_PIXEL, TOP_PIXEL=$TOP_PIXEL"
echo "RIGHT_PIXEL=$RIGHT_PIXEL, BOTTOM_PIXEL=$BOTTOM_PIXEL"

# 切り抜きサイズを計算
echo "切り抜きサイズの計算:"
echo "RIGHT_PIXEL=$RIGHT_PIXEL, LEFT_PIXEL=$LEFT_PIXEL"
echo "BOTTOM_PIXEL=$BOTTOM_PIXEL, TOP_PIXEL=$TOP_PIXEL"

# 単純な引き算で計算（座標順序は既に修正済み）
CROP_WIDTH=$((RIGHT_PIXEL - LEFT_PIXEL))
CROP_HEIGHT=$((BOTTOM_PIXEL - TOP_PIXEL))

echo "計算結果: CROP_WIDTH=$CROP_WIDTH, CROP_HEIGHT=$CROP_HEIGHT"

# 値が負または0の場合は修正
if [ $CROP_WIDTH -le 0 ]; then
    echo "警告: 幅が0以下です。1に設定します。"
    CROP_WIDTH=1
fi

if [ $CROP_HEIGHT -le 0 ]; then
    echo "警告: 高さが0以下です。1に設定します。"
    CROP_HEIGHT=1
fi

# X, Y座標の順序を修正（常に左上から右下への順序にする）
echo "座標順序の修正前:"
echo "LEFT_PIXEL=$LEFT_PIXEL, RIGHT_PIXEL=$RIGHT_PIXEL"
echo "TOP_PIXEL=$TOP_PIXEL, BOTTOM_PIXEL=$BOTTOM_PIXEL"

if [ "$(awk -v right="$RIGHT_PIXEL" -v left="$LEFT_PIXEL" 'BEGIN {print (right < left) ? 1 : 0}')" -eq 1 ]; then
    echo "X座標入れ替え: RIGHT_PIXEL < LEFT_PIXEL"
    TEMP=$LEFT_PIXEL
    LEFT_PIXEL=$RIGHT_PIXEL
    RIGHT_PIXEL=$TEMP
fi

if [ "$(awk -v bottom="$BOTTOM_PIXEL" -v top="$TOP_PIXEL" 'BEGIN {print (bottom < top) ? 1 : 0}')" -eq 1 ]; then
    echo "Y座標入れ替え: BOTTOM_PIXEL < TOP_PIXEL"
    TEMP=$TOP_PIXEL
    TOP_PIXEL=$BOTTOM_PIXEL
    BOTTOM_PIXEL=$TEMP
fi

echo "座標順序の修正後:"
echo "LEFT_PIXEL=$LEFT_PIXEL, RIGHT_PIXEL=$RIGHT_PIXEL"
echo "TOP_PIXEL=$TOP_PIXEL, BOTTOM_PIXEL=$BOTTOM_PIXEL"

# 結果を表示
echo
echo "切り抜き範囲:"
echo "左上座標 (経度,緯度): ($LEFT_LON, $TOP_LAT)"
echo "右下座標 (経度,緯度): ($RIGHT_LON, $BOTTOM_LAT)"
echo
echo "ピクセル座標:"
echo "左上 (X,Y): ($LEFT_PIXEL, $TOP_PIXEL)"
echo "右下 (X,Y): ($RIGHT_PIXEL, $BOTTOM_PIXEL)"
echo
echo "切り抜きサイズ: ${CROP_WIDTH}x${CROP_HEIGHT}ピクセル"

# 切り抜きコマンドの例を表示
echo
echo "以下のgdal_translateコマンドで切り抜きできます:"
echo "gdal_translate -srcwin $LEFT_PIXEL $TOP_PIXEL $CROP_WIDTH $CROP_HEIGHT \"$TIFF_FILE\" output.tif"