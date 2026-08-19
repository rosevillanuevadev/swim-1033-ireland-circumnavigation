#!/usr/bin/env python3
"""
General-purpose OSM coastline fetcher: given ANY bounding box, tiles it to
stay under Overpass query limits, fetches natural=coastline data per tile,
merges everything, and polygonizes into a single land/water polygon set.

This is the standard replacement for the coarse Natural Earth 10m land mask
(which had ~700m+ average vertex spacing in tested inlets and missed real
crossings up to 1.6km). Not Ireland-specific - takes any (west, south, east,
north) bbox, so the same function works for any future circumnavigation.
"""
import time, pickle, sys
import warnings
warnings.filterwarnings('ignore')
import osmnx as ox
from shapely.geometry import box, shape
from shapely.ops import linemerge, polygonize, unary_union
import shapefile as sf

# Public Overpass mirrors to try in order - the primary (overpass-api.de) was
# rate-limiting/refusing connections after ~2 prior requests in this session.
OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api",
    "https://overpass.openstreetmap.ru/api",
    "https://overpass-api.de/api",
]

ox.settings.requests_timeout = 120

def fetch_one_tile(tw, ts, te, tn, max_retries=3):
    last_err = None
    for mirror in OVERPASS_MIRRORS:
        ox.settings.overpass_url = mirror
        for attempt in range(max_retries):
            try:
                gdf = ox.features_from_bbox((tw, ts, te, tn), tags={'natural': 'coastline'})
                return gdf, mirror
            except Exception as e:
                err = str(e)
                if 'no matching features' in err.lower() or 'not found' in err.lower():
                    return None, mirror  # genuinely empty tile, not a failure
                last_err = e
                time.sleep(5 * (attempt + 1))  # backoff: 5s, 10s, 15s
        # this mirror failed all retries, try the next one
    raise last_err if last_err else RuntimeError("all mirrors failed")

def fetch_coastline_lines(bbox, tile_deg=1.0, pause_s=3.0):
    """bbox = (west, south, east, north). Returns list of LineString/Polygon
    coastline geometries, fetched tile by tile to stay under Overpass limits."""
    west, south, east, north = bbox
    all_geoms = []
    nx = max(1, int((east - west) / tile_deg) + 1)
    ny = max(1, int((north - south) / tile_deg) + 1)
    total = nx * ny
    done = 0
    for i in range(nx):
        for j in range(ny):
            tw = west + i * tile_deg
            te = min(west + (i + 1) * tile_deg, east)
            ts = south + j * tile_deg
            tn = min(south + (j + 1) * tile_deg, north)
            done += 1
            try:
                result, mirror = fetch_one_tile(tw, ts, te, tn)
                n = len(result) if result is not None else 0
                if result is not None:
                    all_geoms.extend(list(result.geometry))
                print(f"[{done}/{total}] tile ({tw:.2f},{ts:.2f},{te:.2f},{tn:.2f}) via {mirror}: {n} features",
                      file=sys.stderr)
            except Exception as e:
                print(f"[{done}/{total}] tile ({tw:.2f},{ts:.2f},{te:.2f},{tn:.2f}): FAILED after all mirrors/retries - {type(e).__name__} {str(e)[:150]}",
                      file=sys.stderr)
            time.sleep(pause_s)
    return all_geoms

def build_land_polygon(bbox, coastline_geoms, reference_land_geoms):
    """Polygonize merged coastline lines against the bbox boundary, then
    classify each resulting face as land/water using a reference dataset
    (coarse but topologically correct) for orientation."""
    lines = []
    for geom in coastline_geoms:
        if geom.geom_type == 'LineString':
            lines.append(geom)
        elif geom.geom_type == 'Polygon':
            lines.append(geom.exterior)
        elif geom.geom_type == 'MultiLineString':
            lines.extend(list(geom.geoms))
    bbox_ring = box(*bbox).exterior
    merged = linemerge(unary_union(lines + [bbox_ring]))
    faces = list(polygonize(merged))
    land_faces = []
    for f in faces:
        c = f.representative_point()
        if any(g.contains(c) for g in reference_land_geoms):
            land_faces.append(f)
    return unary_union(land_faces)

def load_reference_land(bbox):
    reader = sf.Reader("/Users/rosevillanueva/wowsa-builds/swimmable-distance/.cache/ne_10m_land.shp")
    geoms_all = [shape(s.__geo_interface__) for s in reader.shapes()]
    bx = box(*bbox)
    return [g for g in geoms_all if g.intersects(bx)]

if __name__ == '__main__':
    SCRATCH = "/private/tmp/claude-501/-Users-rosevillanueva-wowsa-builds-swimmable-distance/2ac1628d-c001-4435-97b8-d30e8d3e66ff/scratchpad"
    # Ireland's actual coastal extent (tighter than the full search bbox used
    # elsewhere, to keep tile count reasonable)
    IRELAND_BBOX = (-11.0, 51.2, -5.3, 55.5)
    t0 = time.time()
    ref = load_reference_land(IRELAND_BBOX)
    print(f"Loaded {len(ref)} reference (Natural Earth) polygons for classification", file=sys.stderr)
    geoms = fetch_coastline_lines(IRELAND_BBOX, tile_deg=1.0, pause_s=1.0)
    print(f"Fetched {len(geoms)} total coastline features in {time.time()-t0:.1f}s", file=sys.stderr)
    land = build_land_polygon(IRELAND_BBOX, geoms, ref)
    print(f"Built land polygon: {land.geom_type}, {len(land.geoms) if hasattr(land,'geoms') else 1} parts, "
          f"{time.time()-t0:.1f}s total", file=sys.stderr)
    with open(f"{SCRATCH}/osm_land_ireland.pkl", 'wb') as fh:
        pickle.dump(land, fh)
    print("saved osm_land_ireland.pkl", file=sys.stderr)
