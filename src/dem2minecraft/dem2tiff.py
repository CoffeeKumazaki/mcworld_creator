# -*- coding: utf-8 -*-
import re
import numpy as np
import sys
sys.path.append('/usr/lib/python3/dist-packages')
from osgeo import gdal
from os.path import join,relpath
from glob import glob

def dem2tiff(dem_dir_name, tiff_dir_name):

    #XMLを格納するフォルダ
    path = dem_dir_name
    #GeoTiffを出力するフォルダ
    geopath = tiff_dir_name
    #ファイル名取得
    files = [relpath(x,path) for x in glob(join(path,'*'))]

    for fl in files:
        xmlFile = join(path,fl)
        #XMLを開く
        with open(xmlFile, "r", encoding = "utf-8") as f:
            r = re.compile("<gml:lowerCorner>(.+) (.+)</gml:lowerCorner>")
            for ln in f:
                m = r.search(ln)
                #検索パターンとマッチした場合、スタートポジションを格納
                if m != None:
                    lry = float2(m.group(1))
                    ulx = float2(m.group(2))
                    break

            r = re.compile("<gml:upperCorner>(.+) (.+)</gml:upperCorner>")

            for ln in f:
                m = r.search(ln)

                #検索パターンとマッチした場合、スタートポジションを格納
                if m != None:
                    uly = float2(m.group(1))
                    lrx = float2(m.group(2))
                    break


            # 検索パターンをコンパイル
            r = re.compile("<gml:high>(.+) (.+)</gml:high>")
            for ln in f:
                m = r.search(ln)
                #検索パターンとマッチした場合、縦横の領域を格納
                if m != None:
                    xlen = int(m.group(1)) + 1
                    ylen = int(m.group(2)) + 1
                    break

            startx = starty = 0

            # 検索パターンをコンパイル
            r = re.compile("<gml:startPoint>(.+) (.+)</gml:startPoint>")
            for ln in f:
                m = r.search(ln)
                #検索パターンとマッチした場合、スタートポジションを格納
                if m != None:
                    startx = int(m.group(1))
                    starty = int(m.group(2))
                    break

        #numpy用にデータを格納しておく
        with open(xmlFile, "r", encoding = "utf-8") as f:
            src_document = f.read()
            lines = src_document.split("\n")
            num_lines = len(lines)
            l1 = None
            l2 = None
            for i in range(num_lines):
                if lines[i].find("<gml:tupleList>") != -1:
                    l1 = i + 1
                    break
            for i in range(num_lines - 1, -1, -1):
                if lines[i].find("</gml:tupleList>") != -1:
                    l2 = i - 1
                    break

        #セルのサイズを算出
        psize_x = (lrx - ulx) / xlen
        psize_y = (lry - uly) / ylen

        geotransform = [ulx, psize_x, 0, uly, 0, psize_y]
        # 変換パラメーターを設定
        dst_size_x = 1
        dst_size_y = 1        
        create_options = [] # gdal.WarpOptions(xRes=dst_size_x, yRes=dst_size_y, resampleAlg=gdal.GRIORA_Cubic)

        driver = gdal.GetDriverByName("GTiff")

        #拡張子を変更する（ファイル名はそのまま）
        dst = fl.replace('.xml', '.tif')
        tiffFile = join(geopath,dst)
        print(f"{tiffFile=}")
        dst_ds = driver.Create(tiffFile, xlen, ylen, 1, gdal.GDT_Float32, create_options)

        dst_ds.SetProjection('GEOGCS["JGD2000",DATUM["Japanese_Geodetic_Datum_2000",SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6612"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4612"]]')
        dst_ds.SetGeoTransform(geotransform)
        rband = dst_ds.GetRasterBand(1)

        narray = np.empty((ylen, xlen), np.float32)
        narray.fill(0)

        num_tuples = l2 - l1 + 1

        #スタートポジションを算出
        start_pos = starty*xlen + startx

        i = 0
        sx = startx

        #標高を格納
        for y in range(starty, ylen):
            for x in range(sx, xlen):
                if i < num_tuples:
                    vals = lines[i + l1].split(",")
                    if len(vals) == 2 and vals[1].find("-99") == -1:
                        narray[y][x] = float(vals[1])
                    i += 1
                else:
                    break
            if i == num_tuples: break
            sx = 0

        rband.WriteRaster(0, 0, xlen, ylen, narray.tostring())
        dst_ds.FlushCache()

def float2(str):
    lc = ""
    for i in range(len(str)):
        c = str[i]
        if c == lc:
            renzoku += 1
            if renzoku == 6:
                return float(str[:i+1] + c * 10)
        else:
            lc = c
            renzoku = 1
        return float(str)