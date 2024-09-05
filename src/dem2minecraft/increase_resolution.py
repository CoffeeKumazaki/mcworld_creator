import sys
sys.path.append('/usr/lib/python3/dist-packages')
from osgeo import gdal

def inc_resolution_5to1(inputfilename, outputfilename):
    # 入力ファイルを開く
    print(f"{inputfilename=}")
    print(f"{outputfilename=}")
    tiff_5m = gdal.Open(inputfilename, gdal.GA_ReadOnly)

    cwidth = tiff_5m.RasterXSize               # "coarse lattice width"
    cheight = tiff_5m.RasterYSize              # "coarse lattice height"
    raster_count = tiff_5m.RasterCount
    print(f"{cwidth=}, {cheight=}, {raster_count=}")

    # 変換パラメーターを設定
    dst_size_x = 0.00001
    dst_size_y = 0.00001

    # 立方体補間(Cubic Convolution) で解像度を変更する
    warp_options = gdal.WarpOptions(xRes=dst_size_x, yRes=dst_size_y, resampleAlg=gdal.GRIORA_Cubic)

    # ラスターの変換を実行
    print(f"Converting {inputfilename} to {outputfilename}")
    gdal.Warp(outputfilename, tiff_5m, options=warp_options)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="input tiff file path")
    parser.add_argument("--output", required=True, help="output tiff file path")

    args = parser.parse_args()

    inc_resolution_5to1(args.input, args.output)