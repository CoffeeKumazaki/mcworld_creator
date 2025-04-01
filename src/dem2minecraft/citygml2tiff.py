import lxml.etree as et
import tqdm
import numpy as np
import os
import rasterio
from PIL import Image, ImageDraw
from shapely.geometry import Polygon


BUILDING_PATH = ".//bldg:Building"

def load_polygons(file):

  doc = et.parse(file, None)
  polygons = []
  for obj in doc.iterfind(BUILDING_PATH, namespaces=doc.getroot().nsmap):
    for polygon in obj.iterfind(".//bldg:lod1Solid//gml:Polygon", namespaces=doc.getroot().nsmap):
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
      alt = int(ring[0][2])
      draw.polygon([latlon_to_pixel(lat, lon, min_lat, max_lat, min_lon, max_lon, width, height) for lat, lon, _ in ring], fill=alt)
      
  return img
   
def latlon_to_pixel(lat, lon, min_lat, max_lat, min_lon, max_lon, width, height):
  x = int((lon - min_lon) / (max_lon - min_lon) * width)
  y = int((max_lat - lat) / (max_lat - min_lat) * height)
  return x, y

def is_in_range(polygon, min_lat, max_lat, min_lon, max_lon):
  for ring in polygon:
    for lat, lon, _ in ring:
      if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
        return False
  return True


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
    parser.add_argument("--output", required=True, help="output file path")
    args = parser.parse_args()

    polygons = []
    for file in tqdm.tqdm(os.listdir(args.input)):
      if file.endswith(".gml"):
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