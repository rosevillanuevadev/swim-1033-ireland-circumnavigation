# 03. The algorithm

Implementation: `scripts/circumnav_v5_final.py` (the corrected, final version; earlier
iterations v1 through v4 are kept in `scripts/history/` for the record, see
[05-results.md](05-results.md) for what each one got wrong).

## Input

The swimmer's raw GPX leg files, parsed in the *corrected* order (see
[04-leg-numbering-bug.md](04-leg-numbering-bug.md)), concatenated into one long sequence of
`(lon, lat)` points per continuous run.

## Step 1: downsample for speed

The raw track has 1,473,905 points. Working with all of them in the simplification step below
would be prohibitively slow. Points are kept only if they are at least 150m from the last kept
point (or are a leg boundary, always kept). This drops the working set to roughly 9,600 points
without losing anything geometrically meaningful, since 150m is far below the scale of any real
coastal feature that matters for this method.

## Step 2: recursive simplification (fast pass)

This is a Douglas-Peucker line-simplification algorithm, with one change: instead of a fixed
distance tolerance, the stopping condition is *does the simplified line cross land*.

```
simplify(points, i, j):
    if straight_line(points[i], points[j]) does not cross land: return
    if j - i <= 1: return  # cannot subdivide further at this resolution
    k = point in (i, j) with maximum perpendicular distance from the line i→j
    keep k
    simplify(points, i, k)
    simplify(points, k, j)
```

The point chosen at each split, the one furthest from the straight line, is a proxy for "the
outermost point on the track at this headland," which is exactly the placement rule described in
the adopted methodology document. This is not a coincidence: Douglas-Peucker's split criterion
and "find the outermost point of a headland" are the same operation.

Because the coastline is a closed loop and start equals finish, a naive single call to
`simplify(points, 0, len(points)-1)` degenerates (the chord from the loop's start back to itself
is length zero). The fast pass seeds recursion with anchor points spaced every 25km of
along-track distance around the loop first, then runs the same recursive split within each
anchor-bounded segment.

A subsequent prune pass removes any waypoint that turns out to be unnecessary once its neighbors
are known, keeping the set minimal.

The land-crossing test used in this pass is a *sampled* check: walk along the candidate chord in
roughly 100m steps (adaptive to chord length) and test whether any sample point is on land. This
is cheap, and it is precise enough to find candidate waypoints, but it is not the check the
published number is guaranteed against. See step 3.

## Step 3: verify and repair (exact pass)

The fast pass's sampled check can miss a crossing if the true land-crossing point falls between
two samples, or if the 150m downsampling in step 1 discarded a point that was actually needed.
Both happened in this build; see [05-results.md](05-results.md) for the specific legs it affected
(Legs 13, 15, 16, 17 near Achill/Mullet, and 53/54 near Dublin).

The fix: after the fast pass produces a candidate waypoint set, every resulting leg is
re-checked with *exact geometric intersection* (Shapely `LineString.intersection` against the
actual land polygon, not sampling). Any leg that fails is locally re-split, using the *original
full-resolution GPS points* in that specific stretch (not the 150m-downsampled ones), and
re-verified. This repeats until every leg in the route passes the exact check.

```
repair(raw_points, i, j):
    if not crosses_land_exact(raw_points[i], raw_points[j]): return
    if j - i <= 1: return  # true resolution limit of the recorded GPS data
    k = point in (i, j) with maximum perpendicular distance from the line i→j
    keep k
    repair(raw_points, i, k)
    repair(raw_points, k, j)
```

**Tolerance matters here and was a real bug.** The first version of this exact check used a
tolerance of `5e-6` degrees (about 0.5 meters), which is close to zero. A swimmer legitimately
hugging a coastline will have GPS points within a meter or two of the mapped shoreline
constantly, just from normal GPS jitter and the coastline data's own resolution limit. At 0.5m
tolerance the repair pass found thousands of false "crossings" and could not resolve most of
them, producing 3,973 waypoints (should have been a few hundred) and 3,646 legs still reported as
crossing land. The fix was raising the tolerance to `5e-4` degrees (about 50 meters), matching
the tolerance already used successfully in earlier manual diagnostic checks. That single constant
was the entire bug.

## Output

A sequence of waypoints, the sum of great-circle (haversine) distances between consecutive
waypoints, and a `remaining_land_crossings` count that should always be zero in a published
result. If it is not zero, the result should not be published; see
[05-results.md](05-results.md) for what a non-zero count looked like and how it was caught.

## What this method deliberately does not attempt

It does not decide *which* bays get cut across or which headlands must be rounded. That decision
belongs to the pioneering swimmer's own route, taken as given. The algorithm only ever removes
points that are geometrically unnecessary and adds points only where geometry demands them (a
straight line would cross land). See the adopted methodology document referenced in
[01-overview.md](01-overview.md) for the fuller argument for why this is the correct division of
labor between human judgment and computation.
