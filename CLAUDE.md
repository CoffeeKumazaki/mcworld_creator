# CLAUDE.md - mcworld_creator

## Overview

Converts real-world geographic data (DEM elevation, CityGML buildings, OSM roads) into Minecraft world files (.mca region format). Two independent pipelines exist.

## Build & Run

```bash
# Docker (primary workflow, required for GDAL)
./run_docker.sh                  # auto-rebuilds image if Dockerfile/requirements.txt changed
docker build -t world_builder .  # manual build

# Inside container, scripts run as:
python dem2minecraft ...
python plateau2minecraft ...
```

- Base image: `osgeo/gdal:ubuntu-small-3.6.3`
- Key dependencies: GDAL, rasterio, numpy, pandas, lxml, trimesh, open3d, osmium, Pillow, shapely, pyproj

## Architecture

### Pipeline 1: `dem2minecraft` (raster-based)

Converts geographic data to TIFF intermediates, then composites them into Minecraft .mca region files.

```
DEM GML ──→ dem2tiff.py ──→ TIFF ─┐
OSM PBF ──→ road2tiff.py ─→ TIFF ─┤
CityGML ──→ citygml2tiff.py → TIFF┤──→ make_minecraft_world.py ──→ .mca
WaterGML ─→ watergml2tiff.py →TIFF┤
TsunamiGML→ tnmgml2tiff.py → TIFF ┘
```

**Entry point:** `src/dem2minecraft/__main__.py` — converts DEM GML to TIFF
**World builder:** `src/dem2minecraft/make_minecraft_world.py`
- `--tiff` (required): DEM elevation TIFF
- `--road`, `--bldg`, `--water`, `--tnm` (optional): overlay TIFFs
- `--output` (required): output folder (creates `region/` subdirectory)

**Coordinate flow:** lat/lon → pixel coords → centered on image midpoint → mapped to Minecraft block coords (x, z) → grouped into 512x512 regions → saved as `r.{rx}.{rz}.mca`

**Block mapping:** terrain layers = grass/dirt/stone; road pixels >200 = gray concrete, >100 = cobblestone; buildings = white concrete columns; water = 3-deep water blocks; tsunami = colored stained glass by class

### Pipeline 2: `plateau2minecraft` (mesh-based, 3D voxelization)

Converts CityGML 3D models directly to Minecraft blocks via voxelization.

```
CityGML ──→ parser.py (triangulate) ──→ voxelizer.py ──→ merge_points.py ──→ converter.py ──→ .mca
```

**Entry point:** `src/plateau2minecraft/__main__.py`
- `--target` (required): one or more CityGML file paths
- `--output` (required): output folder

**Processing steps:**
1. **parser.py** — parses CityGML XML (lxml), extracts polygons (LOD2 preferred, LOD1 fallback), triangulates via earcut, transforms coords from EPSG:6697 → EPSG:3857
2. **voxelizer.py** — subdivides mesh to max 5m edge length, voxelizes at 1m resolution using trimesh, produces hollow voxel shells (multiprocessing Pool)
3. **impart_color.py** — assigns colors per feature type (bldg=gray, tran=dark gray)
4. **merge_points.py** — merges multiple point clouds
5. **converter.py** — centers point cloud, flips Y axis for Minecraft orientation (Y-up right-hand), splits into 512-block regions, writes .mca files

**Supported CityGML feature types:** `bldg` (buildings), `tran` (roads), `brid` (bridges), `frn` (city furniture), `veg` (vegetation)

## Key Conventions

- **Anvil format:** both pipelines include a vendored `anvil/` library for writing Minecraft .mca region files (512x512 block regions, 16x16 chunks)
- **Coordinate systems:** DEM pipeline uses pixel-based centering; plateau pipeline uses EPSG:6697 (JGD2011) → EPSG:3857 (Web Mercator) projection
- **1 pixel/voxel = 1 Minecraft block** (1 meter)
- **Minecraft Y range:** -64 to 319; bedrock placed at -64 to -62
- **Feature type extraction:** derived from filename convention `*_{feature_type}_*` (e.g., `53394525_bldg_6697_op.gml`)

## Project Structure

```
src/
  dem2minecraft/         # Raster-based pipeline
    __main__.py          # DEM→TIFF entry point
    make_minecraft_world.py  # TIFF→Minecraft world
    dem2tiff.py          # DEM GML→TIFF core logic
    road2tiff.py         # OSM roads→TIFF
    citygml2tiff.py      # CityGML buildings→TIFF
    watergml2tiff.py     # Water features→TIFF
    tnmgml2tiff.py       # Tsunami data→TIFF
    demgml2tiff.py       # DEM relief features→TIFF
    roadgml2tiff.py      # Road GML→TIFF
    anvil/               # Vendored Minecraft anvil writer
  plateau2minecraft/     # Mesh-based 3D pipeline
    __main__.py          # CityGML→Minecraft entry point
    parser.py            # CityGML XML parsing & triangulation
    voxelizer.py         # Triangle mesh→voxels
    converter.py         # Point cloud→Minecraft .mca
    merge_points.py      # Point cloud merger
    impart_color.py      # Feature type→color assignment
    feature_color.py     # Color/block mapping tables
    types.py             # TriangleMesh dataclass
    earcut/              # Vendored polygon triangulation
    anvil/               # Vendored Minecraft anvil writer (extended with RO classes)
  citygml2minecraft/     # Shared config (bounding box defaults)
Dockerfile               # osgeo/gdal base + Python deps
requirements.txt         # Pinned Python dependencies
run_docker.sh            # Auto-rebuild & run Docker container
```

## Data Sources

- **DEM elevation:** https://fgd.gsi.go.jp/download/menu.php (Geospatial Information Authority of Japan)
- **Roads (OSM):** https://download.geofabrik.de/asia/japan.html (.osm.pbf files)
- **Buildings (Plateau CityGML v3):** https://www.mlit.go.jp/plateau/open-data/
