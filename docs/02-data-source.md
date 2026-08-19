# 02. Coastline data source

Every step of this method depends on being able to answer one question precisely: does this
straight line, between these two points, cross land. That answer is only as good as the map of
land and water it is checked against.

## First attempt: Natural Earth (rejected)

The swimmable-distance calculator this build extends already had a cached Natural Earth 10m land
polygon dataset (`.cache/ne_10m_land.shp`), originally fetched for shore-to-shore land-crossing
checks. It was reused here as the first attempt.

It failed in practice. Measured directly: in one test inlet (Mullet Peninsula / Blacksod Bay,
Co. Mayo, roughly 16km by 50km), the raw, unsimplified Natural Earth data had only 181 vertices,
an average spacing over 700 meters. "10m" in the dataset's name refers to a map-scale category
(suitable for maps down to 1:10,000,000), not point resolution. In geometrically complex, tightly
indented coastline, it is not precise enough to make a confident land-crossing call.

Two consequences followed:

- **Real crossings were missed.** Checking specific flagged legs against a finer OSM extract for
  the same area found actual overlaps into land of up to 1.65 km that Natural Earth's coarser
  data reported as clear.
- **The rendering and the check could disagree.** Because the algorithm's crossing check and the
  page's rendered coastline outline were both drawn from the same coarse source, a visually
  "correct" map could still hide a real problem, and a visually "wrong"-looking map (see
  [04-leg-numbering-bug.md](04-leg-numbering-bug.md)) could in fact be reporting the algorithm
  correctly.

## Second attempt: live OSM via Overpass (rejected)

Before settling on a cached dataset, live queries to OpenStreetMap's Overpass API were tried,
first for a single small test region (worked, in seconds), then for the country-scale region
needed for the whole route. That failed repeatedly: a full-country query timed out after three
minutes, mirror fallback with retries still stalled on individual tiles, and even a much smaller,
targeted set of nine tiles hit repeated timeouts and connection refusals. This was true across
several separate attempts on different public Overpass mirrors.

**Conclusion: a production system must not depend on a live Overpass call inside a calculation.**
It is not reliable enough to sit in a request path, regardless of how the request is batched or
retried.

## Third attempt: OSM Land Polygons, downloaded once, cached locally (adopted)

The pattern that solved this was borrowed from `searoute-py`, a shipping-route Python package
already a dependency of the swimmable-distance calculator. searoute-py does not look anything up
live. It ships with a small, pre-built GeoJSON file of known shipping lanes
(`searoute/data/marnet_searoute.geojson`, about 730KB, 4,109 hand-digitized line segments),
loaded into a graph once and read from locally every time it is asked for a route. The lookup
itself is fast and reliable *because the expensive, judgment-requiring work was done once, ahead
of time, and saved.*

The same pattern was applied here, with different content:

1. Downloaded OSM's official Land Polygons dataset once
   (`https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip`, about 900MB,
   870,871 land polygon records covering the entire planet). This is a one-time cost. It never
   needs to happen again for any future landmass.
2. Streamed through the resulting 1.3GB shapefile with `pyshp`'s `iterShapeRecords()` (does not
   load the whole file into memory) and kept only the 4,287 polygons whose bounding box
   intersects Ireland's coastal region. This took 13 seconds.
3. Saved that Ireland-specific slice as a standalone, portable GeoJSON file,
   `.cache/osm_land_ireland.geojson` (18.9MB), in the swimmable-distance calculator's existing
   `.cache/` directory, alongside the older Natural Earth file.
4. Confirmed the resolution gain directly: 20,496 vertices in the same Mullet/Blacksod Bay test
   box that Natural Earth covered with 181. A roughly 113x increase in local detail.

Every future landmass follows the same two-step pattern: cut a fresh slice out of the *same*
already-downloaded global file (no second download), then cache that slice locally. See
`scripts/fetch_osm_coastline.py`.

## What the coastline data is used for, precisely

Two separate checks, at two separate precision levels, both against the same cached data:

- **Fast pass (candidate generation):** sampling along a chord at roughly 100m resolution, used
  while recursively deciding which points to keep as waypoints. Cheap, run many times.
- **Exact pass (verification and repair):** true geometric line-polygon intersection (Shapely),
  with a roughly 50m tolerance to absorb coastline-data and GPS jitter from a swimmer legitimately
  hugging the shore, run once per final leg to guarantee the published result. See
  [03-algorithm.md](03-algorithm.md) for why both passes exist and what the 50m tolerance means in
  practice.
