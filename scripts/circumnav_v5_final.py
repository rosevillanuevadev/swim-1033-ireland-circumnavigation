#!/usr/bin/env python3
"""
Final, corrected circumnavigation distance calculation. Named-waypoint
method (fewest points, straight lines, none cross land) run against a
TRUE swim-order leg chain (see reconstruct_true_chain.py, not file-number
order) and verified with exact geometry against a precise, locally cached
coastline dataset (see fetch_osm_coastline.py). See docs/03-algorithm.md
for the full explanation of each step and docs/04-leg-numbering-bug.md for
why true chain order matters.

Usage:
    python3 reconstruct_true_chain.py <gpx_dir> "Leg 1.gpx"
    python3 circumnav_v5_final.py <land_geojson_path>

Reads true_chain.json and legs_reordered.json from the current directory
(written by reconstruct_true_chain.py). Writes result.json.
"""
import json, math, sys, time
from shapely.geometry import Point, LineString, shape
from shapely.strtree import STRtree

DOWNSAMPLE_M = 150
ANCHOR_KM = 25.0
EXACT_TOLERANCE_DEG = 5e-4  # ~50m. See docs/03-algorithm.md: 5e-6 (~0.5m) was a real bug.


def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_land(geojson_path):
    with open(geojson_path) as fh:
        d = json.load(fh)
    geoms = [shape(f["geometry"]) for f in d["features"]]
    return STRtree(geoms), geoms


def is_on_land(lon, lat, tree, geoms):
    pt = Point(lon, lat)
    hits = tree.query(pt, predicate="intersects")
    return any(geoms[k].contains(pt) for k in hits)


def crosses_land_sampled(p1, p2, tree, geoms):
    lon1, lat1 = p1
    lon2, lat2 = p2
    chord_km = haversine_km(lon1, lat1, lon2, lat2)
    n = max(40, min(4000, int(chord_km * 10)))  # ~100m/sample
    skip = max(1, int(n * 0.02))
    for i in range(skip, n - skip + 1):
        t = i / n
        if is_on_land(lon1 + t * (lon2 - lon1), lat1 + t * (lat2 - lat1), tree, geoms):
            return True
    return False


def crosses_land_exact(p1, p2, tree, geoms):
    line = LineString([p1, p2])
    hits = tree.query(line, predicate="intersects")
    for k in hits:
        inter = geoms[k].intersection(line)
        if not inter.is_empty and inter.length > EXACT_TOLERANCE_DEG:
            return True
    return False


def perp_distance(p, a, b):
    lat0 = a[1]
    scale = math.cos(math.radians(lat0))
    bx, by = (b[0] - a[0]) * scale, (b[1] - a[1])
    px, py = (p[0] - a[0]) * scale, (p[1] - a[1])
    seg_len2 = bx * bx + by * by
    if seg_len2 == 0:
        return math.hypot(px, py)
    t = max(0.0, min(1.0, (px * bx + py * by) / seg_len2))
    return math.hypot(px - t * bx, py - t * by)


def simplify(points, i, j, tree, geoms, keep):
    if not crosses_land_sampled(points[i], points[j], tree, geoms):
        return
    if j - i <= 1:
        return
    best_k, best_d = None, -1.0
    for k in range(i + 1, j):
        dd = perp_distance(points[k], points[i], points[j])
        if dd > best_d:
            best_d, best_k = dd, k
    keep.add(best_k)
    simplify(points, i, best_k, tree, geoms, keep)
    simplify(points, best_k, j, tree, geoms, keep)


def prune(points, keep_sorted, tree, geoms):
    kept = list(keep_sorted)
    changed = True
    while changed:
        changed = False
        i = 1
        while i < len(kept) - 1:
            if not crosses_land_sampled(points[kept[i - 1]], points[kept[i + 1]], tree, geoms):
                kept.pop(i)
                changed = True
            else:
                i += 1
    return kept


def repair(raw, i, j, tree, geoms, keep):
    if not crosses_land_exact(raw[i], raw[j], tree, geoms):
        return
    if j - i <= 1:
        return  # true resolution limit of the recorded GPS data
    best_k, best_d = None, -1.0
    for k in range(i + 1, j):
        dd = perp_distance(raw[k], raw[i], raw[j])
        if dd > best_d:
            best_d, best_k = dd, k
    keep.add(best_k)
    repair(raw, i, best_k, tree, geoms, keep)
    repair(raw, best_k, j, tree, geoms, keep)


def verify_and_repair(raw, kept_idx, tree, geoms):
    kept = set(kept_idx)
    for _ in range(6):
        ks = sorted(kept)
        failed = False
        for idx in range(len(ks) - 1):
            a, b = ks[idx], ks[idx + 1]
            if crosses_land_exact(raw[a], raw[b], tree, geoms):
                failed = True
                repair(raw, a, b, tree, geoms, kept)
        if not failed:
            break
    return sorted(kept)


def simplify_run(raw_run, tree, geoms):
    """Downsample, simplify, verify+repair one continuous run. Returns kept raw indices."""
    ds, ds_idx = [raw_run[0]], [0]
    last = raw_run[0]
    for i in range(1, len(raw_run)):
        p = raw_run[i]
        if haversine_km(*last, *p) * 1000 >= DOWNSAMPLE_M or i == len(raw_run) - 1:
            ds.append(p)
            ds_idx.append(i)
            last = p
    n = len(ds)
    if n < 2:
        kept_idx = list(range(n))
    else:
        cum = [0.0]
        for i in range(1, n):
            cum.append(cum[-1] + haversine_km(*ds[i - 1], *ds[i]))
        anchors, target = [0], ANCHOR_KM
        for i in range(1, n):
            if cum[i] >= target:
                anchors.append(i)
                target += ANCHOR_KM
        if anchors[-1] != n - 1:
            anchors.append(n - 1)
        keep = set(anchors)
        for a in range(len(anchors) - 1):
            simplify(ds, anchors[a], anchors[a + 1], tree, geoms, keep)
        kept_idx = prune(ds, sorted(keep), tree, geoms)
        kept_idx = [ds_idx[k] for k in kept_idx]
    return verify_and_repair(raw_run, kept_idx, tree, geoms)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <land_geojson_path>", file=sys.stderr)
        sys.exit(1)
    land_path = sys.argv[1]

    t0 = time.time()
    with open("true_chain.json") as fh:
        chain_data = json.load(fh)
    with open("legs_reordered.json") as fh:
        legs_pts = json.load(fh)

    chain = chain_data["chain"]
    true_gaps = chain_data["true_gaps"]
    gap_after_set = {g["after_leg"] for g in true_gaps}

    raw_points, run_starts = [], [0]
    for name in chain:
        if name in gap_after_set and raw_points:
            run_starts.append(len(raw_points))
        raw_points.extend(legs_pts[name])
    run_starts.append(len(raw_points))
    runs = [(run_starts[i], run_starts[i + 1]) for i in range(len(run_starts) - 1)]
    print(f"{len(raw_points)} points, {len(runs)} continuous runs", file=sys.stderr)

    tree, geoms = load_land(land_path)
    print(f"Loaded {len(geoms)} land polygons in {time.time()-t0:.1f}s", file=sys.stderr)

    all_waypoints, total_km = [], 0.0
    for (rs, re_) in runs:
        raw_run = raw_points[rs:re_]
        kept_idx = simplify_run(raw_run, tree, geoms)
        wps = [raw_run[k] for k in kept_idx]
        all_waypoints.extend(wps)
        for i in range(len(wps) - 1):
            total_km += haversine_km(*wps[i], *wps[i + 1])

    remaining = 0
    for i in range(len(all_waypoints) - 1):
        if crosses_land_exact(all_waypoints[i], all_waypoints[i + 1], tree, geoms):
            remaining += 1

    print(f"Done in {time.time()-t0:.1f}s. Waypoints: {len(all_waypoints)}. "
          f"Distance: {total_km:.3f} km. Remaining land crossings: {remaining}", file=sys.stderr)

    result = {
        "total_distance_km": round(total_km, 3),
        "total_distance_mi": round(total_km * 0.621371, 3),
        "waypoint_count": len(all_waypoints),
        "num_runs": len(runs),
        "remaining_land_crossings": remaining,
        "true_gaps": true_gaps,
        "waypoints": [[round(w[0], 5), round(w[1], 5)] for w in all_waypoints],
    }
    with open("result.json", "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "waypoints"}, indent=2))


if __name__ == "__main__":
    main()
