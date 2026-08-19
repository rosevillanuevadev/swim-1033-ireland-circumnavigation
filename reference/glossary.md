# Glossary

**Leg**: one GPX file, one continuous recorded swim session. SWIM-1033 has 101 (Legs 1 to 100,
with Leg 88 split into two files). A leg's file number does not reliably indicate its position in
the actual swim order; see `docs/04-leg-numbering-bug.md`.

**Run**: a maximal sequence of legs that connect to each other with no real gap between them
(within 300m). The final published route has 10 runs. Not to be confused with a leg: one run can
contain many legs.

**Gap**: a point where one leg's endpoint has no other leg's endpoint within 300m of it anywhere
in the dataset. A gap ends one run and starts the next. Excluded from the distance total,
reported separately, because there is no GPS record of swimming across it.

**Waypoint**: a point kept in the final route because removing it would cause the straight line
between its neighbors to cross land. The minimum set of waypoints needed defines the shortest
swimmable path.

**Shortest swimmable path**: the sum of great-circle distances between consecutive waypoints.
Always less than or equal to the distance actually swum, by construction (a straight line between
two points on a curve is never longer than the curve itself).

**Fast pass**: the sampled land-crossing check used while choosing candidate waypoints. Cheap,
run many times, not the check the final number is guaranteed against.

**Exact pass / verify and repair**: the precise geometric land-crossing check (true line-polygon
intersection, not sampling) run once per final leg to guarantee the published result has zero
land crossings.

**True chain**: the corrected leg order, built by matching every leg's endpoints against every
other leg's endpoints, rather than trusting file numbers. See `docs/04-leg-numbering-bug.md`.

**OSM Land Polygons**: the global land/water reference dataset this build's coastline checks are
based on, downloaded once from `osmdata.openstreetmap.de`, cached locally as small per-landmass
slices. See `docs/02-data-source.md`.

**marnet / searoute-py**: an existing shipping-route Python package already used elsewhere in
the swimmable-distance calculator. Its pattern of shipping a small, pre-built, locally-read
reference dataset instead of looking anything up live is the pattern this build's coastline
caching copies. See `docs/02-data-source.md`.
