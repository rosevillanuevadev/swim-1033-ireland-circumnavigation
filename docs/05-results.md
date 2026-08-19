# 05. Results, in order

Every figure produced during this build, in the order it was produced, with what changed and
why. Kept in full because the sequence itself is the useful record, not just the final number.

## Figures that predate this build (for context)

| Figure | Value | Source |
|---|---|---|
| Dijkstra / GLOBE raster | 1,240.78 km | Rejected in the prior methodology document, understates |
| Doc adopted V1 (leg endpoints) | 1,418.93 km | The methodology document this build implements against full-resolution data |
| GPX-derived, manually adjusted | 1,441.996 km | An earlier manual pass using an offshore-buffer heuristic |
| Full GPX track swum | 1,460.57 km | The swimmer's actual recorded distance, the ceiling any shortest-path figure must sit under |

## Figures produced in this build

### v1 (rejected: loop-closure bug)

First run of the algorithm against Natural Earth data. A single top-level call to
`simplify(points, 0, len(points)-1)` on the full closed loop degenerated, because start and
finish are the same point (Foudra Rock), so the chord was near zero length. Result: 2 waypoints,
0.086 km. Obviously wrong, caught immediately.

### v2 (rejected: leg-numbering gaps not yet handled)

Fixed the loop-closure bug by seeding recursion with anchors every 25km around the loop.
Result: **1,541.36 km**, larger than the full GPX swum distance (1,460.57 km), which is
impossible for a shortest-path figure by definition. Cause: file-number-adjacent legs were
connected by straight chords even where they were actually distant boat-transit jumps, at full
value. See [04-leg-numbering-bug.md](04-leg-numbering-bug.md).

### v3 (rejected: excluded the leg-number gaps, still had the coastline precision bug)

Split the route into 25 "continuous runs" at every file-number gap over 300m (24 gaps, 511.7 km,
matching the wrong assumption in 04). Result: **1,368.51 km**. Land-crossing checked against
Natural Earth. A visual check found real crossings this had missed (Legs 13, 15, 16, 17 near
Achill/Mullet; Legs 53/54 near Dublin).

A same-day repair attempt introduced a units bug (tolerance `5e-6` degrees instead of `5e-4`,
roughly 0.5m instead of 50m) that caused catastrophic false-positive land-crossing detection:
3,973 waypoints, 3,646 legs still reported as crossing land. Reverted, tolerance corrected, rerun.
Corrected result: **1,369.01 km**, 0 remaining land crossings against Natural Earth.

### v4 (adopted data source, still wrong leg order)

Rebuilt the land-crossing check against the newly cached OSM Land Polygons data (see
[02-data-source.md](02-data-source.md)) instead of Natural Earth. Result: **1,381.87 km**,
0 remaining land crossings against the precise data, still using the 25-run, 24-gap file-number
split.

### v5 (final: corrected leg order, precise coastline data)

Replaced the file-number-based run splitting with the true endpoint-matched chain reconstruction
(see [04-leg-numbering-bug.md](04-leg-numbering-bug.md)). Result: **1,383.47 km**, 10 continuous
runs (not 25), 9 real gaps totaling 15.2 km (not 24 gaps totaling 511.7 km), 161 waypoints,
0 remaining land crossings verified by exact geometry.

This is the published figure.

## Summary table

| Version | Distance | Runs | Gaps | Gap total | Land crossings | Status |
|---|---|---|---|---|---|---|
| v1 | 0.086 km | | | | | Rejected, loop-closure bug |
| v2 | 1,541.36 km | | | | | Rejected, exceeds GPX ceiling |
| v3 | 1,369.01 km | 25 | 24 | 511.7 km | 0 (Natural Earth) | Rejected, coastline too coarse |
| v4 | 1,381.87 km | 25 | 24 | 511.7 km | 0 (OSM) | Rejected, leg order still wrong |
| **v5** | **1,383.47 km** | **10** | **9** | **15.2 km** | **0 (OSM, exact)** | **Published** |

## Why the final number barely moved from v4 to v5, despite the gap analysis changing completely

The total *distance* changed by less than 2 km between v4 and v5, even though the gap
methodology changed enormously. This makes sense: the coastline itself was always fully covered
by the union of all 101 legs, correcting the leg order did not add or remove any real swimming
distance, it just stopped incorrectly inserting long straight chords across sections that were
never actually disconnected. What changed was *correctness and defensibility*, not the headline
number. That distinction matters when explaining this to a non-technical audience: the number
looked almost right by coincidence, the methodology behind it was not.
