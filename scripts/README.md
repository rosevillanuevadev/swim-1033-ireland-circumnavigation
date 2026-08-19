# Scripts

The adopted pipeline, in order. See `docs/` for why each step exists and what it caught.

```
pip install -r requirements.txt

# 1. Fetch and cache precise coastline data for the landmass (one time, reused forever)
python3 fetch_and_cache_landmass.py ireland -11.5 50.5 -5.0 55.8

# 2. Reconstruct the true swim order from the GPX files (not file-number order)
python3 reconstruct_true_chain.py /path/to/gpx/folder "Leg 1.gpx"

# 3. Run the named-waypoint algorithm against the true chain and cached coastline
python3 circumnav_v5_final.py .cache/osm_land_ireland.geojson

# 4. Build the public route analysis page (requires GOOGLE_MAPS_API_KEY in the environment,
#    and a page_data.json shaped as described in the script's docstring, built from result.json)
GOOGLE_MAPS_API_KEY=... python3 build_analysis_page.py
```

`wrangler.jsonc` is the Cloudflare Workers config that made deployment work, specifically
`"not_found_handling": "single-page-application"`, without which a custom route path 404s even
though the Worker is correctly triggered. See `docs/06-analysis-page-and-deployment.md`.

`history/` holds earlier, rejected versions of steps 1 to 3, kept for the record. See
`history/README.md`.
