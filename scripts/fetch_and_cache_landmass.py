#!/usr/bin/env python3
"""
The adopted coastline data pipeline. See docs/02-data-source.md.

A live Overpass-based fetcher was tried first and rejected for reliability
(see scripts/history/rejected_live_overpass_fetch.py: repeated timeouts and
connection failures across multiple public mirrors, even for small regions).

This script instead:
  1. Downloads OSM's official Land Polygons dataset ONCE (~900MB, full
     planet, every future landmass reuses this same file, never re-fetched).
  2. Streams through the resulting ~1.3GB shapefile with pyshp's
     iterShapeRecords() (does not load the whole file into memory) and keeps
     only the polygons whose bounding box intersects the target region.
  3. Saves that slice as a small, portable GeoJSON file.

Usage:
    python3 fetch_and_cache_landmass.py <name> <west> <south> <east> <north>

Example (Ireland):
    python3 fetch_and_cache_landmass.py ireland -11.5 50.5 -5.0 55.8

Output: .cache/osm_land_<name>.geojson
"""
import sys, os, time, json, zipfile, urllib.request

import shapefile as sf
from shapely.geometry import mapping, shape

GLOBAL_ZIP_URL = "https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip"
CACHE_DIR = ".cache"
GLOBAL_DIR = os.path.join(CACHE_DIR, "osm-global")


def ensure_global_download():
    """Downloads the ~900MB global land polygons dataset once. Safe to call
    every run; skips if already present. Resumable via curl -C - if you
    prefer to run that manually instead of urllib for a large, flaky link."""
    shp_path = os.path.join(GLOBAL_DIR, "land-polygons-split-4326", "land_polygons.shp")
    if os.path.exists(shp_path):
        return shp_path

    os.makedirs(GLOBAL_DIR, exist_ok=True)
    zip_path = os.path.join(GLOBAL_DIR, "land-polygons-split-4326.zip")
    if not os.path.exists(zip_path):
        print(f"Downloading {GLOBAL_ZIP_URL} (~900MB, one time only)...", file=sys.stderr)
        urllib.request.urlretrieve(GLOBAL_ZIP_URL, zip_path)

    print("Extracting...", file=sys.stderr)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(GLOBAL_DIR)
    return shp_path


def bbox_intersects(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def extract_region(shp_path, bbox):
    t0 = time.time()
    reader = sf.Reader(shp_path)
    print(f"Opened shapefile, {reader.numRecords} total global records", file=sys.stderr)

    matched = []
    checked = 0
    for shape_rec in reader.iterShapeRecords():
        checked += 1
        shp = shape_rec.shape
        if not shp.points:
            continue
        if bbox_intersects(shp.bbox, bbox):
            matched.append(shp.__geo_interface__)
        if checked % 200000 == 0:
            print(f"  scanned {checked}, matched {len(matched)}, {time.time()-t0:.1f}s", file=sys.stderr)

    print(f"Scanned {checked}, matched {len(matched)} in {time.time()-t0:.1f}s", file=sys.stderr)
    return matched


def main():
    if len(sys.argv) != 6:
        print(f"Usage: {sys.argv[0]} <name> <west> <south> <east> <north>", file=sys.stderr)
        sys.exit(1)
    name = sys.argv[1]
    bbox = tuple(float(x) for x in sys.argv[2:6])

    shp_path = ensure_global_download()
    matched = extract_region(shp_path, bbox)
    geoms = [shape(g) for g in matched]

    out = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": mapping(g)} for g in geoms],
    }
    os.makedirs(CACHE_DIR, exist_ok=True)
    out_path = os.path.join(CACHE_DIR, f"osm_land_{name}.geojson")
    with open(out_path, "w") as fh:
        json.dump(out, fh)

    size_mb = os.path.getsize(out_path) / 1e6
    print(f"Saved {out_path}, {size_mb:.1f}MB, {len(geoms)} polygons", file=sys.stderr)


if __name__ == "__main__":
    main()
