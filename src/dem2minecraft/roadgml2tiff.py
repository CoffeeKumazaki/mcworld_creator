import lxml.etree as et
import numpy as np
import tqdm
import os
import rasterio
from PIL import Image, ImageDraw
from citygml2tiff import latlon_to_pixel

ROAD_PATH = [".//tran:Road", ".//tran:TrafficArea"]

def load_polygons(file):

  doc = et.parse(file, None)
  polygons = []
  for obj_path in ROAD_PATH:
    for obj in doc.iterfind(obj_path, namespaces=doc.getroot().nsmap):
      for polygon in obj.iterfind(".//gml:Polygon", namespaces=doc.getroot().nsmap):
        pos_list = polygon.find("./gml:exterior//gml:posList", namespaces=doc.getroot().nsmap)
        vertices = np.fromstring(pos_list.text, dtype=np.float64, sep=" ")
        assert len(vertices) % 3 == 0
        assert len(vertices) / 3 >= 3
        exterior = vertices.reshape(-1, 3)[:-1]
        rings = []
        rings.append(exterior)
      polygons.append(rings)
    return polygons

def polygon_to_image(polygons, min_lat, max_lat, min_lon, max_lon, width, height):
  img = Image.new("L", (width, height), 0)
  draw = ImageDraw.Draw(img)
  for polygon in polygons:
    for ring in polygon:
      alt = 255
      draw.polygon([latlon_to_pixel(lat, lon, min_lat, max_lat, min_lon, max_lon, width, height) for lat, lon, _ in ring], fill=alt)
      
  return img

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CityGML dir path")
    parser.add_argument("--min_lat", required=True, type=float, help="min latitude")
    parser.add_argument("--max_lat", required=True, type=float, help="max latitude")
    parser.add_argument("--min_lon", required=True, type=float, help="min longitude")
    parser.add_argument("--max_lon", required=True, type=float, help="max longitude")
    parser.add_argument("--width", required=True, type=int, help="image width")
    parser.add_argument("--height", required=True, type=int, help="image height")  
    parser.add_argument("--output", required=True, help="output GeoTIFF file path")  
    args = parser.parse_args()

    polygons = []
    for file in tqdm.tqdm(os.listdir(args.input)):
      if not file.endswith(".gml"):
        continue
      polygons.extend(load_polygons(os.path.join(args.input, file)))

    img = polygon_to_image(polygons, args.min_lat, args.max_lat, args.min_lon, args.max_lon, args.width, args.height)
    image_array = np.array(img)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with rasterio.open(
        args.output,
        'w',
        driver='GTiff',
        height=args.height,
        width=args.width,
        count=1,
        dtype=image_array.dtype,
        crs='+proj=latlong',
        transform=rasterio.transform.from_bounds(args.min_lon, args.min_lat, args.max_lon, args.max_lat, args.width, args.height)
    ) as dst:
        dst.write(image_array, 1)