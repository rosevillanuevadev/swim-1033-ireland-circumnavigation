# History

Earlier, rejected versions of the pipeline, kept for the record. See
`docs/05-results.md` for what each one produced and why it was replaced.

| File | What it is | Why it was rejected |
|---|---|---|
| `rejected_live_overpass_fetch.py` | First coastline data attempt: live OpenStreetMap Overpass API queries | Repeated timeouts and connection failures across multiple public mirrors, even for small regions. See `docs/02-data-source.md` |
| `v3_natural_earth_final.py` | First working end-to-end version, against Natural Earth coastline data | Coastline data too coarse, missed real land crossings up to 1.6km. See `docs/02-data-source.md` |
| `v4_osm_wrong_leg_order.py` | Switched to precise OSM coastline data, but still split runs by file-number adjacency | 24 flagged gaps, 511.7km, almost all false. See `docs/04-leg-numbering-bug.md` |

The current, adopted pipeline is `../fetch_and_cache_landmass.py` →
`../reconstruct_true_chain.py` → `../circumnav_v5_final.py` →
`../build_analysis_page.py`.
