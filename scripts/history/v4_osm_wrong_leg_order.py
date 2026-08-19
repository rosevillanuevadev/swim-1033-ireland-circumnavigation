#!/usr/bin/env python3
"""
v4: same run-constrained named-waypoint method + verify-and-repair pass as
v3, but using the precise OSM-derived land polygon (.cache/osm_land_ireland.geojson,
4,287 polygons, cut from the global OSM land-polygons dataset) as the standard
land data source throughout - both the fast pass AND the exact repair pass -
instead of the coarse Natural Earth data. This is a genuine resolution
upgrade (113x more vertices in the previously-flagged Mullet/Blacksod inlet).
"""
import glob, math, os, re, sys, json, time
import gpxpy
from shapely.geometry import Point, LineString, shape
from shapely.strtree import STRtree

GPX_DIR = "/Users/rosevillanueva/Downloads/Garmin GPX Files folder /"
LAND_GEOJSON = "/Users/rosevillanueva/wowsa-builds/swimmable-distance/.cache/osm_land_ireland.geojson"
OUT_JSON = "/private/tmp/claude-501/-Users-rosevillanueva-wowsa-builds-swimmable-distance/2ac1628d-c001-4435-97b8-d30e8d3e66ff/scratchpad/circumnav_result_v4.json"

DOWNSAMPLE_M = 150
GAP_THRESHOLD_KM = 0.3
ANCHOR_KM = 25.0

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def leg_sort_key(path):
    name = os.path.basename(path)
    m = re.search(r'(?i)leg\s*(\d+).*?part\s*(\d+)', name)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.search(r'(?i)leg\s*(\d+)', name)
    return (int(m.group(1)), 0)

def load_land():
    with open(LAND_GEOJSON) as fh:
        d = json.load(fh)
    geoms = [shape(f['geometry']) for f in d['features']]
    return STRtree(geoms), geoms

def is_on_land(lon, lat, tree, geoms):
    pt = Point(lon, lat)
    hits = tree.query(pt, predicate='intersects')
    return any(geoms[k].contains(pt) for k in hits)

def crosses_land_sampled(p1, p2, tree, geoms):
    lon1, lat1 = p1
    lon2, lat2 = p2
    chord_km = haversine_km(lon1, lat1, lon2, lat2)
    n = max(40, min(4000, int(chord_km * 10)))
    skip = max(1, int(n * 0.02))
    for i in range(skip, n - skip + 1):
        t = i / n
        lon = lon1 + t * (lon2 - lon1)
        lat = lat1 + t * (lat2 - lat1)
        if is_on_land(lon, lat, tree, geoms):
            return True
    return False

def crosses_land_exact(p1, p2, tree, geoms):
    line = LineString([p1, p2])
    hits = tree.query(line, predicate='intersects')
    for k in hits:
        inter = geoms[k].intersection(line)
        if inter.is_empty:
            continue
        if inter.length > 5e-4:  # ~50m
            return True
    return False

def perp_distance(p, a, b):
    lat0 = a[1]
    scale = math.cos(math.radians(lat0))
    bx, by = (b[0]-a[0])*scale, (b[1]-a[1])
    px, py = (p[0]-a[0])*scale, (p[1]-a[1])
    seg_len2 = bx*bx + by*by
    if seg_len2 == 0:
        return math.hypot(px, py)
    t = max(0.0, min(1.0, (px*bx + py*by) / seg_len2))
    projx, projy = t*bx, t*by
    return math.hypot(px-projx, py-projy)

def simplify(points, i, j, tree, geoms, keep, stats):
    stats['crossing_checks'] += 1
    if not crosses_land_sampled(points[i], points[j], tree, geoms):
        return
    if j - i <= 1:
        stats['unresolved_gaps'] += 1
        return
    best_k, best_d = None, -1.0
    for k in range(i+1, j):
        dd = perp_distance(points[k], points[i], points[j])
        if dd > best_d:
            best_d, best_k = dd, k
    keep.add(best_k)
    simplify(points, i, best_k, tree, geoms, keep, stats)
    simplify(points, best_k, j, tree, geoms, keep, stats)

def prune(points, keep_sorted, tree, geoms):
    kept = list(keep_sorted)
    changed = True
    while changed:
        changed = False
        i = 1
        while i < len(kept) - 1:
            a, c = kept[i-1], kept[i+1]
            if not crosses_land_sampled(points[a], points[c], tree, geoms):
                kept.pop(i)
                changed = True
            else:
                i += 1
    return kept

def simplify_run(ds_points, tree, geoms, stats):
    n = len(ds_points)
    if n < 2:
        return [0] if n == 1 else []
    if n == 2:
        return [0, 1]
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + haversine_km(*ds_points[i-1], *ds_points[i]))
    anchors = [0]
    target = ANCHOR_KM
    for i in range(1, n):
        if cum[i] >= target:
            anchors.append(i)
            target += ANCHOR_KM
    if anchors[-1] != n - 1:
        anchors.append(n - 1)
    keep = set(anchors)
    for a in range(len(anchors) - 1):
        simplify(ds_points, anchors[a], anchors[a+1], tree, geoms, keep, stats)
    return prune(ds_points, sorted(keep), tree, geoms)

def repair(raw_points, i, j, tree, geoms, keep, stats):
    if not crosses_land_exact(raw_points[i], raw_points[j], tree, geoms):
        return
    stats['repair_checks'] += 1
    if j - i <= 1:
        stats['repair_unresolved'] += 1
        return
    best_k, best_d = None, -1.0
    for k in range(i+1, j):
        dd = perp_distance(raw_points[k], raw_points[i], raw_points[j])
        if dd > best_d:
            best_d, best_k = dd, k
    keep.add(best_k)
    repair(raw_points, i, best_k, tree, geoms, keep, stats)
    repair(raw_points, best_k, j, tree, geoms, keep, stats)

def verify_and_repair(raw_run, raw_idx_kept, tree, geoms, stats):
    kept = set(raw_idx_kept)
    for _ in range(6):
        kept_sorted = sorted(kept)
        any_failed = False
        for idx in range(len(kept_sorted) - 1):
            a, b = kept_sorted[idx], kept_sorted[idx+1]
            if crosses_land_exact(raw_run[a], raw_run[b], tree, geoms):
                any_failed = True
                repair(raw_run, a, b, tree, geoms, kept, stats)
        if not any_failed:
            break
    return sorted(kept)

def main():
    t0 = time.time()
    files = sorted(glob.glob(os.path.join(GPX_DIR, "*.gpx")), key=leg_sort_key)
    print(f"Found {len(files)} GPX files", file=sys.stderr)

    raw_points = []
    leg_boundaries = []
    leg_labels = []
    for f in files:
        with open(f, 'r', encoding='utf-8') as fh:
            gpx = gpxpy.parse(fh)
        leg_boundaries.append(len(raw_points))
        leg_labels.append(os.path.basename(f))
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    raw_points.append((pt.longitude, pt.latitude))
    print(f"Parsed {len(raw_points)} raw points in {time.time()-t0:.1f}s", file=sys.stderr)

    run_starts = [0]
    inter_run_gaps = []
    for idx in range(1, len(leg_boundaries)):
        prev_end = raw_points[leg_boundaries[idx]-1]
        this_start = raw_points[leg_boundaries[idx]]
        gap_km = haversine_km(prev_end[0], prev_end[1], this_start[0], this_start[1])
        if gap_km > GAP_THRESHOLD_KM:
            run_starts.append(leg_boundaries[idx])
            inter_run_gaps.append({
                'gap_km': round(gap_km, 3), 'after_leg': leg_labels[idx-1], 'before_leg': leg_labels[idx],
                'from': [round(prev_end[0],5), round(prev_end[1],5)],
                'to': [round(this_start[0],5), round(this_start[1],5)],
            })
    run_starts.append(len(raw_points))
    runs = [(run_starts[i], run_starts[i+1]) for i in range(len(run_starts)-1)]
    print(f"{len(runs)} continuous runs, {len(inter_run_gaps)} inter-run gaps excluded", file=sys.stderr)

    tree, geoms = load_land()
    print(f"Loaded {len(geoms)} OSM-derived land polygons in {time.time()-t0:.1f}s", file=sys.stderr)

    stats = {'crossing_checks': 0, 'unresolved_gaps': 0, 'repair_checks': 0, 'repair_unresolved': 0,
              'repaired_legs': 0}
    all_waypoints = []
    run_waypoint_spans = []
    total_km = 0.0

    for (rs, re_) in runs:
        raw_run = raw_points[rs:re_]
        ds = [raw_run[0]]
        ds_raw_idx = [0]
        last = raw_run[0]
        for i in range(1, len(raw_run)):
            p = raw_run[i]
            d_m = haversine_km(last[0], last[1], p[0], p[1]) * 1000
            if d_m >= DOWNSAMPLE_M or i == len(raw_run) - 1:
                ds.append(p)
                ds_raw_idx.append(i)
                last = p
        kept_idx = simplify_run(ds, tree, geoms, stats)
        raw_idx_kept = [ds_raw_idx[k] for k in kept_idx]

        before = set(raw_idx_kept)
        raw_idx_kept = verify_and_repair(raw_run, raw_idx_kept, tree, geoms, stats)
        stats['repaired_legs'] += len(set(raw_idx_kept) - before)

        wps = [raw_run[k] for k in raw_idx_kept]
        start_i = len(all_waypoints)
        all_waypoints.extend(wps)
        run_waypoint_spans.append((start_i, len(all_waypoints)-1))
        for i in range(len(wps)-1):
            total_km += haversine_km(wps[i][0], wps[i][1], wps[i+1][0], wps[i+1][1])

    print(f"Simplification+repair done in {time.time()-t0:.1f}s, {stats}", file=sys.stderr)
    print(f"Total swimmable-path distance: {total_km:.3f} km", file=sys.stderr)

    legs_out = []
    remaining_failures = 0
    for (s, e) in run_waypoint_spans:
        for i in range(s, e):
            a, b = all_waypoints[i], all_waypoints[i+1]
            fails = crosses_land_exact(a, b, tree, geoms)
            if fails:
                remaining_failures += 1
            legs_out.append({
                'from': [round(a[0],5), round(a[1],5)],
                'to': [round(b[0],5), round(b[1],5)],
                'distance_km': round(haversine_km(a[0],a[1],b[0],b[1]), 3),
            })
    print(f"Final verification: {remaining_failures} legs still crossing land (should be 0)", file=sys.stderr)

    result = {
        'method': 'Named-waypoint method, run-constrained, verify-and-repair against OSM-derived land data',
        'input_files': len(files),
        'raw_points': len(raw_points),
        'num_runs': len(runs),
        'waypoint_count': len(all_waypoints),
        'total_distance_km': round(total_km, 3),
        'total_distance_mi': round(total_km * 0.621371, 3),
        'remaining_land_crossings': remaining_failures,
        'waypoints': [[round(w[0],5), round(w[1],5)] for w in all_waypoints],
        'legs': legs_out,
        'inter_run_gaps_excluded': inter_run_gaps,
        'inter_run_gaps_total_km': round(sum(g['gap_km'] for g in inter_run_gaps), 3),
        'stats': stats,
        'runtime_s': round(time.time()-t0, 1),
        'reference_figures_km': {
            'dijkstra_globe_raster': 1240.78,
            'named_waypoint_doc_v1': 1418.93,
            'gpx_derived_manual_adjusted': 1441.996,
            'gpx_full_track_swum': 1460.57,
            'v3_natural_earth_based': 1369.012,
        }
    }
    with open(OUT_JSON, 'w') as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('waypoints','legs')}, indent=2))

if __name__ == '__main__':
    main()
