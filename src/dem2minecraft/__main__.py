import argparse
from glob import glob

from dem2tiff import dem2tiff
from increase_resolution import inc_resolution_5to1

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--dem", required=True, type=str, help="DEM dir path")
    parser.add_argument("--tiff", required=True, type=str, help="TIFF dir path")
    args = parser.parse_args()

    dem_dir = args.dem
    tiff_dir = args.tiff
    print(f"Converting {dem_dir} to {tiff_dir}")
    # dem2tiff(dem_dir, tiff_dir)

    for tiffile in glob(f"{tiff_dir}/*.tif"):
        print(f"{tiffile=}")
        newfile = tiffile.replace(".tif", "_1m.tif")
        inc_resolution_5to1(tiffile, newfile)