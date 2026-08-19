#!/usr/bin/env python3
"""
Reconstruct the true swim order of a set of GPX leg files by matching every
leg's start and end point against every OTHER leg's endpoints, rather than
trusting file numbering. See docs/04-leg-numbering-bug.md for why this is
necessary: consecutive file numbers do not reliably reflect consecutive
geography on a multi-session expedition swim.

Usage:
    python3 reconstruct_true_chain.py /path/to/gpx/folder "Leg 1.gpx"

The second argument is the filename to start the chain from (the swim's
known start point). Output: a JSON file with the reconstructed chain order
and the list of genuine remaining gaps (leg pairs whose closest match is
still farther than GAP_THRESHOLD_KM apart).
"""
import glob, os, re, sys, json, math
import gpxpy

GAP_THRESHOLD_KM = 0.3


def leg_sort_key(path):
    """Fallback sort only, NOT used to determine true swim order."""
    name = os.path.basename(path)
    m = re.search(r'(?i)leg\s*(\d+).*?part\s*(\d+)', name)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.search(r'(?i)leg\s*(\d+)', name)
    return (int(m.group(1)), 0)


def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_legs(gpx_dir):
    files = sorted(glob.glob(os.path.join(gpx_dir, "*.gpx")), key=leg_sort_key)
    legs = {}
    for f in files:
        name = os.path.basename(f)
        with open(f, "r", encoding="utf-8") as fh:
            gpx = gpxpy.parse(fh)
        pts = [(p.longitude, p.latitude) for trk in gpx.tracks for seg in trk.segments for p in seg.points]
        if not pts:
            continue
        legs[name] = {"points": pts, "start": pts[0], "end": pts[-1]}
    return legs


def reconstruct_chain(legs, start_name):
    """Greedy nearest-endpoint chain reconstruction. Returns (chain, true_gaps)."""
    names = list(legs.keys())
    used = {start_name}
    chain = [start_name]
    cur_end = legs[start_name]["end"]
    true_gaps = []

    while len(used) < len(names):
        best_name, best_dist, best_reversed = None, 1e9, False
        for name in names:
            if name in used:
                continue
            d_fwd = haversine_km(*cur_end, *legs[name]["start"])
            d_rev = haversine_km(*cur_end, *legs[name]["end"])
            if d_fwd < best_dist:
                best_dist, best_name, best_reversed = d_fwd, name, False
            if d_rev < best_dist:
                best_dist, best_name, best_reversed = d_rev, name, True

        chain.append(best_name)
        used.add(best_name)
        if best_reversed:
            legs[best_name]["points"] = list(reversed(legs[best_name]["points"]))
            legs[best_name]["start"], legs[best_name]["end"] = legs[best_name]["end"], legs[best_name]["start"]
        if best_dist > GAP_THRESHOLD_KM:
            true_gaps.append({"after_leg": chain[-2], "before_leg": chain[-1], "gap_km": round(best_dist, 3)})
        cur_end = legs[best_name]["end"]

    return chain, true_gaps


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <gpx_dir> <start_filename>", file=sys.stderr)
        sys.exit(1)
    gpx_dir, start_name = sys.argv[1], sys.argv[2]

    legs = load_legs(gpx_dir)
    print(f"{len(legs)} legs loaded", file=sys.stderr)

    chain, true_gaps = reconstruct_chain(legs, start_name)
    print(f"Reconstructed chain of {len(chain)} legs, {len(true_gaps)} true gaps", file=sys.stderr)
    for g in sorted(true_gaps, key=lambda x: -x["gap_km"]):
        print(f"  {g['after_leg']} -> {g['before_leg']}: {g['gap_km']} km", file=sys.stderr)

    out = {"chain": chain, "true_gaps": true_gaps}
    with open("true_chain.json", "w") as fh:
        json.dump(out, fh, indent=2)
    with open("legs_reordered.json", "w") as fh:
        json.dump({name: legs[name]["points"] for name in chain}, fh)
    print("Wrote true_chain.json and legs_reordered.json", file=sys.stderr)


if __name__ == "__main__":
    main()
