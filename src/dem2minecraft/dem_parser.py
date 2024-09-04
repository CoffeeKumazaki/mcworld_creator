
import glob
import re
import xml.etree.ElementTree as ET

def get_dem_info(dem_file_path):

    for file in glob.glob(dem_file_path):
        print(f"Processing start: {file}")

        # open the XML file
        with open(file, "r", encoding = "utf-8") as f:

            # search start position
            r = re.compile("<gml:lowerCorner>(.+) (.+)</gml:lowerCorner>")
            for ln in f:
                m = r.search(ln)
                if m != None:
                    lry = float(m.group(1))
                    ulx = float(m.group(2))
                    break
                    
            # search end position
            r = re.compile("<gml:upperCorner>(.+) (.+)</gml:upperCorner>")
            for ln in f:
                m = r.search(ln)
                if m != None:
                    uly = float(m.group(1))
                    lrx = float(m.group(2))
                    break

            # search area
            r = re.compile("<gml:high>(.+) (.+)</gml:high>")
            for ln in f:
                m = r.search(ln)
                if m != None:
                    xlen = int(m.group(1)) + 1
                    ylen = int(m.group(2)) + 1
                    break

            # search start point
            startx = starty = 0
            r = re.compile("<gml:startPoint>(.+) (.+)</gml:startPoint>")
            for ln in f:
                m = r.search(ln)
                if m != None:
                    startx = int(m.group(1))
                    starty = int(m.group(2))
                    break

        with open(file, "r", encoding = "utf-8") as f:
            tuple_list_regex = re.search(r"<gml:tupleList>([\s\S]+?)</gml:tupleList>", f.read())

            print(f"tuple_list_regex: {tuple_list_regex}")
            if tuple_list_regex:
                tuple_list_content = tuple_list_regex.group(1).strip().split("\n")
                height_values = [float(line.split(",")[1]) for line in tuple_list_content]


        print(f"Processing end: {file}")
        return lry, ulx, uly, lrx, xlen, ylen, startx, starty, height_values
    

if __name__ == "__main__":
    from pathlib import Path
    # このファイルのディレクトリを文字列で取得
    this_dir = Path(__file__).parent
    
    dem_file_path = str(this_dir) + "/../data/dem/FG-GML-5339-45-DEM5A/FG-GML-5339-45-98-DEM5A-20190130.xml"
    lry, ulx, uly, lrx, xlen, ylen, startx, starty, height_values = get_dem_info(dem_file_path)
    print(f"lry: {lry}, ulx: {ulx}, uly: {uly}, lrx: {lrx}, xlen: {xlen}, ylen: {ylen}, startx: {startx}, starty: {starty}")
    print(f"len(height_values): {len(height_values)}")