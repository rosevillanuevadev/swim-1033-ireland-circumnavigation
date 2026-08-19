# 01. Overview

## The problem

WOWSA ratifies open water swims. For a shore-to-shore crossing, the official distance is
unambiguous: the shortest straight line between the two fixed endpoints, checked against a
coastline so it never crosses land. Two coordinates fully define the route.

A circumnavigation cannot be measured the same way. The start and end coordinates are the same
point, so a straight-line tangent between them is always zero. Two coordinates tell you nothing
about which way around the island the swimmer went, how close to shore, or which bays were cut
across and which headlands were rounded. The route has to be defined from evidence, not derived
from two points.

For SWIM-1033 (Daragh Morgan, first documented swimming circumnavigation of Ireland, 1 May to
22 November 2025), the evidence is his own GPS track: 101 separate Garmin GPX files, one per
swim session ("leg"), 1,473,905 raw points in total.

## The adopted rule

The shortest swimmable path is the fewest possible waypoints, taken from the swimmer's own GPS
track, connected by straight (great-circle) lines, such that none of those lines cross land.

A waypoint is only kept where removing it would cause the line between its neighbors to cross
land. Everywhere the water is open, points get discarded. This is the standard being measured
against, not an approximation of it: every waypoint in the final set has a specific geometric
reason to exist, and that reason is checkable by anyone with the same GPX file and the same
coastline data.

This mirrors, deliberately, an existing methodology document adopted for this same swim
(`WOWSA_SWIM1033_Distance_Methodology_v1.docx`, not in this repository, referenced for context).
That document proposed the same named-waypoint principle using the 100-leg digital log's endpoint
coordinates as an approximation. This build implements the same rule against the full-resolution
GPS track instead, which is more precise but, as it turned out, exposed problems the coarser
approximation did not.

## What actually happened, in order

1. Built a first version of the algorithm against Natural Earth coastline data (a coarse, widely
   used general dataset). It ran, produced a route, and looked plausible.
2. Rose visually inspected the resulting map against the swimmer's actual GPX track and found
   the computed route cutting across land in several places where the real track clearly did
   not. This was the first real finding: **the coastline data was too coarse to trust**. See
   [02-data-source.md](02-data-source.md).
3. Fixed the data source by downloading and caching a precise, purpose-built global coastline
   dataset (OSM Land Polygons) and rebuilding the algorithm's land-crossing check against it.
4. Rose then spotted something else on the map: long, straight, red "gap" lines connecting two
   legs that were flagged as having no swimming between them, while the swimmer's actual GPX
   track ran continuously and smoothly through that exact area. This was the second, much bigger
   finding: **legs were being compared by file number, not by geography**, and the file numbers
   did not reliably reflect the order the coast was actually swum in. See
   [04-leg-numbering-bug.md](04-leg-numbering-bug.md).
5. Rebuilt the leg ordering from scratch by matching every leg's endpoints against every other
   leg's endpoints, rather than assuming file N+1 follows file N. This collapsed the flagged
   "gaps" from 24 (511.7 km, several as large as 55 km) down to 9 real ones (15.2 km total, the
   largest under 10 km).
6. Recomputed the final distance against the corrected leg order and the precise coastline data:
   **1,383.47 km**. Verified zero remaining land crossings by exact geometry, not sampling.
7. Built and published a public route analysis page (Google Maps, both tracks, the remaining
   gaps, the methodology) at `openwaterswimming.com/routes/swim-1033`, deployed as a Cloudflare
   Worker. See [06-analysis-page-and-deployment.md](06-analysis-page-and-deployment.md).

## Why this matters beyond one swim

Both major bugs were caught by a human looking at a map, not by a test suite or an assertion.
That is not a weakness specific to this build, it is a structural property of this kind of
problem: a wrong coastline dataset and a wrong leg ordering both produce a *plausible-looking*
number. The only cheap, reliable check that caught either bug was overlaying the computed route
on top of the swimmer's actual recorded track and looking for daylight between them. Any future
implementation of this method, automated or not, should keep that visual check as a required
step, not an optional one.
