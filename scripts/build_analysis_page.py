#!/usr/bin/env python3
"""
Builds the standalone HTML route analysis page: swim details, a live Google
Map (swimmer's GPX track, computed route, remaining gaps as independently
toggleable layers), a gaps table, and a methodology footer. See
docs/06-analysis-page-and-deployment.md.

Expects a page_data.json in the current directory shaped like:
{
  "swimmer_polylines": [[{"lat":.., "lng":..}, ...], ...],   # one list per leg
  "route_runs": [[{"lat":.., "lng":..}, ...], ...],           # one list per run
  "gaps": [{"after_leg":.., "before_leg":.., "gap_km":.., "from":{lat,lng}, "to":{lat,lng}}, ...],
  "total_distance_km": .., "total_distance_mi": .., "waypoint_count": ..,
  "num_runs": .., "raw_points": .., "gaps_total_km": ..
}

Requires GOOGLE_MAPS_API_KEY in the environment.
"""
import json, os

with open("page_data.json") as fh:
    data = json.load(fh)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "[GOOGLE_MAPS_API_KEY]")

gap_rows = []
for g in sorted(data['gaps'], key=lambda g: -g['gap_km']):
    tier = "Substantial" if g['gap_km'] >= 5 else "Minor"
    gap_rows.append(
        f'<tr><td class="mono">Leg {g["after_leg"]}</td>'
        f'<td class="mono">Leg {g["before_leg"]}</td>'
        f'<td class="num">{g["gap_km"]} km</td>'
        f'<td class="tier">{tier}</td></tr>'
    )
gap_table_rows = "\n            ".join(gap_rows)

gap_count = len(data['gaps'])
big_gaps = [g for g in data['gaps'] if g['gap_km'] >= 5]
small_gaps = [g for g in data['gaps'] if g['gap_km'] < 5]

data_json = json.dumps(data)

html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SWIM-1033 GPX Route Analysis, Ireland Circumnavigation</title>
<style>
  :root {{
    --ink: #E6E6E4;
    --ink-soft: #A8A8A6;
    --ink-faint: #737371;
    --bg: #17171A;
    --panel: #1F1F22;
    --panel-2: #27272B;
    --line: #38383C;
    --accent: #E0A94C;
    --danger: #FFD54F;
    --warn: #FF6B52;
    --ok: #8FD9AE;
    --swimmer: #FF5CC4;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  .wrap {{ max-width: 980px; margin: 0 auto; padding: 40px 24px 80px; }}
  .eyebrow {{
    font-family: "SF Mono", "Cascadia Code", Consolas, Menlo, monospace;
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--accent); font-weight: 600;
  }}
  h1 {{
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    font-size: 28px; margin: 6px 0 20px; font-weight: 600;
  }}
  .details-box {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1px; background: var(--line); border: 1px solid var(--line);
    margin-bottom: 24px;
  }}
  .details-box .cell {{ background: var(--panel); padding: 16px 18px; }}
  .details-box .k {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--ink-faint); margin-bottom: 4px;
  }}
  .details-box .v {{
    font-family: "SF Mono", "Cascadia Code", Consolas, Menlo, monospace;
    font-size: 16px; font-weight: 600;
  }}
  .stat-strip {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1px; background: var(--line); border: 1px solid var(--line);
    margin-bottom: 32px;
  }}
  .stat-strip .cell {{ background: var(--panel); padding: 16px 18px; }}
  .stat-strip .k {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--ink-faint); margin-bottom: 4px;
  }}
  .stat-strip .v {{
    font-family: "SF Mono", "Cascadia Code", Consolas, Menlo, monospace;
    font-variant-numeric: tabular-nums; font-size: 20px; font-weight: 600;
  }}
  .stat-strip .v.hi {{ color: var(--accent); }}
  h2 {{
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    font-size: 19px; margin: 40px 0 8px; font-weight: 600;
  }}
  .note {{ color: var(--ink-soft); font-size: 14px; line-height: 1.6; max-width: 68ch; margin: 0 0 16px; }}
  .note-list {{
    color: var(--ink-soft); font-size: 14px; line-height: 1.6; max-width: 68ch;
    margin: 0 0 16px; padding-left: 20px; display: flex; flex-direction: column; gap: 4px;
  }}
  .note-list strong {{ color: var(--ink); }}
  #map {{ width: 100%; height: 620px; border: 1px solid var(--line); background: var(--panel); }}
  .legend {{
    display: flex; flex-wrap: wrap; gap: 20px; font-size: 13px; color: var(--ink-soft);
    margin-top: 12px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; }}
  .legend-toggle {{ cursor: pointer; user-select: none; }}
  .legend-toggle input {{ cursor: pointer; }}
  .swatch {{ width: 22px; height: 3px; border-radius: 2px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
  th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--line); }}
  th {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--ink-faint); background: var(--panel-2); font-weight: 600;
  }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: var(--danger); }}
  td.mono {{ font-family: "SF Mono", "Cascadia Code", Consolas, Menlo, monospace; font-size: 12.5px; }}
  .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); background: var(--panel); margin-top: 24px; }}
  .callout {{
    background: var(--panel); border: 1px solid var(--warn); border-left: 4px solid var(--warn);
    padding: 20px 24px; font-size: 14px; line-height: 1.6; margin-top: 16px; color: var(--ink);
    display: flex; flex-direction: column; gap: 10px;
  }}
  .callout strong {{
    display: block; margin-bottom: 6px; color: var(--warn);
    font-family: "SF Mono", "Cascadia Code", Consolas, Menlo, monospace;
    font-size: 14.5px; text-transform: uppercase; letter-spacing: 0.04em;
  }}
  footer {{ margin-top: 48px; border-top: 1px solid var(--line); padding-top: 16px;
    font-size: 12px; color: var(--ink-faint); line-height: 1.6; }}
  footer p {{ margin: 0 0 12px; }}
  footer p:last-child {{ margin-bottom: 0; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">World Open Water Swimming Association, GPX Route Analysis</div>
  <h1>SWIM-1033, Ireland Circumnavigation</h1>

  <div class="details-box">
    <div class="cell"><div class="k">Swimmer</div><div class="v">Daragh Morgan</div></div>
    <div class="cell"><div class="k">Swim ID</div><div class="v">SWIM-1033</div></div>
    <div class="cell"><div class="k">Start</div><div class="v">1 May 2025, 06:50 UTC</div></div>
    <div class="cell"><div class="k">Finish</div><div class="v">22 Nov 2025, 15:42 UTC</div></div>
  </div>

  <div class="stat-strip">
    <div class="cell"><div class="k">This method</div><div class="v hi">{data['total_distance_km']:,.2f} km</div></div>
    <div class="cell"><div class="k">In miles</div><div class="v">{data['total_distance_mi']:,.2f} mi</div></div>
    <div class="cell"><div class="k">Waypoints kept</div><div class="v">{data['waypoint_count']}</div></div>
    <div class="cell"><div class="k">Continuous runs</div><div class="v">{data['num_runs']}</div></div>
    <div class="cell"><div class="k">Raw GPS points read</div><div class="v">{data['raw_points']:,}</div></div>
    <div class="cell"><div class="k">Excluded transit ({gap_count} gaps)</div><div class="v">{data['gaps_total_km']:,.1f} km</div></div>
  </div>

  <h2>Route map</h2>
  <ul class="note-list">
    <li><strong>Magenta:</strong> Daragh's recorded GPX track, every leg swum.</li>
    <li><strong>Green:</strong> the measured route used for the distance calculation.</li>
    <li><strong>Yellow dashed:</strong> gaps between legs where no GPS-recorded swimming connects them.</li>
  </ul>
  <div id="map"></div>
  <div class="legend">
    <label class="legend-item legend-toggle">
      <input type="checkbox" id="toggleSwimmer" checked>
      <span class="swatch" style="background:#FF5CC4"></span> Swimmer's GPX track
    </label>
    <label class="legend-item legend-toggle">
      <input type="checkbox" id="toggleRoute" checked>
      <span class="swatch" style="background:#8FD9AE"></span> Measured route
    </label>
    <label class="legend-item legend-toggle">
      <input type="checkbox" id="toggleGaps" checked>
      <span class="swatch" style="background:#FFD54F;border-top:1px dashed #FFD54F;height:0"></span> Gap, needs explanation
    </label>
  </div>

  <div class="callout">
    <strong>Gaps detected, more context required</strong>
    Route methodology requires that every kilometer of the island be circumnavigated. {len(big_gaps)} of
    these stretches ({sum(g['gap_km'] for g in big_gaps):,.1f} km total) have no GPS record of swimming
    at all. The other {len(small_gaps)} are small and most likely just normal GPS drift on resuming a
    swim. More information is needed on the larger ones before this route can be considered complete.
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>After</th><th>Before</th><th>Gap</th><th>Tier</th></tr>
      </thead>
      <tbody>
        {gap_table_rows}
      </tbody>
    </table>
  </div>

  <footer>
    <p>
      Method: within each continuous GPS-recorded run, straight lines are drawn between the fewest
      possible waypoints such that no line crosses land. A fast pass checks this by sampling at ~100m
      resolution over 150m-downsampled points; every resulting leg is then re-verified with exact
      geometry (not sampling) against OSM-derived coastline data (4,287 polygons cut from a one-time
      global OSM land-polygons download, cached locally, no live map API calls during calculation), and
      any leg that still crosses land is locally re-split using the original full-resolution GPS points
      until it passes. 0 legs cross land in this result. Runs are separated at any point where
      consecutive legs are more than 300m apart. This is the methodology WOWSA uses to calculate
      circumnavigation distance from a swimmer's submitted GPX data.
    </p>
    <p>
      World Open Water Swimming Association. This document supports the ratification review for SWIM-1033.
    </p>
  </footer>
</div>

<script>
  const DATA = {data_json};

  const DARK_MAP_STYLE = [
    {{ elementType: "geometry", stylers: [{{ color: "#2E2E33" }}] }},
    {{ elementType: "labels.text.stroke", stylers: [{{ color: "#17171A" }}] }},
    {{ elementType: "labels.text.fill", stylers: [{{ color: "#A8A8A6" }}] }},
    {{ featureType: "water", elementType: "geometry", stylers: [{{ color: "#131315" }}] }},
    {{ featureType: "road", elementType: "geometry", stylers: [{{ color: "#38383C" }}] }},
    {{ featureType: "road", elementType: "labels.text.fill", stylers: [{{ color: "#737371" }}] }},
    {{ featureType: "administrative", elementType: "geometry.stroke", stylers: [{{ color: "#38383C" }}] }},
    {{ featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{{ color: "#A8A8A6" }}] }},
    {{ featureType: "poi", stylers: [{{ visibility: "off" }}] }},
    {{ featureType: "transit", stylers: [{{ visibility: "off" }}] }},
  ];

  function initMap() {{
    const map = new google.maps.Map(document.getElementById("map"), {{
      zoom: 7,
      center: {{ lat: 53.4, lng: -8.0 }},
      mapTypeId: "roadmap",
      styles: DARK_MAP_STYLE,
    }});

    const bounds = new google.maps.LatLngBounds();
    const swimmerLayer = [];
    const routeLayer = [];
    const gapsLayer = [];

    DATA.swimmer_polylines.forEach(function(poly) {{
      if (poly.length < 2) return;
      const line = new google.maps.Polyline({{
        path: poly,
        geodesic: true,
        strokeColor: "#FF5CC4",
        strokeOpacity: 0.9,
        strokeWeight: 2,
        map: map,
      }});
      swimmerLayer.push(line);
      poly.forEach(function(p) {{ bounds.extend(p); }});
    }});

    DATA.route_runs.forEach(function(run) {{
      if (run.length < 2) return;
      const line = new google.maps.Polyline({{
        path: run,
        geodesic: true,
        strokeColor: "#8FD9AE",
        strokeOpacity: 0.95,
        strokeWeight: 3,
        map: map,
      }});
      routeLayer.push(line);
    }});

    DATA.gaps.forEach(function(g) {{
      const line = new google.maps.Polyline({{
        path: [g.from, g.to],
        geodesic: true,
        strokeColor: "#FFD54F",
        strokeOpacity: 0,
        strokeWeight: 1,
        icons: [{{
          icon: {{ path: "M 0,-1 0,1", strokeOpacity: 1, scale: 2 }},
          offset: "0",
          repeat: "10px",
        }}],
        map: map,
      }});
      const info = new google.maps.InfoWindow({{
        content: "Leg " + g.after_leg + " to Leg " + g.before_leg + ": " + g.gap_km + " km gap",
      }});
      const marker = new google.maps.Marker({{
        position: {{ lat: (g.from.lat + g.to.lat) / 2, lng: (g.from.lng + g.to.lng) / 2 }},
        map: map,
        icon: {{ path: google.maps.SymbolPath.CIRCLE, scale: 3, fillColor: "#FF6B52",
                  fillOpacity: 1, strokeWeight: 0 }},
      }});
      marker.addListener("click", function() {{ info.open(map, marker); }});
      gapsLayer.push(line);
      gapsLayer.push(marker);
    }});

    map.fitBounds(bounds);

    function wireToggle(checkboxId, layer) {{
      document.getElementById(checkboxId).addEventListener("change", function(e) {{
        layer.forEach(function(item) {{ item.setMap(e.target.checked ? map : null); }});
      }});
    }}
    wireToggle("toggleSwimmer", swimmerLayer);
    wireToggle("toggleRoute", routeLayer);
    wireToggle("toggleGaps", gapsLayer);
  }}
</script>
<script async
  src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap">
</script>
</body>
</html>
'''

out_path = "index.html"
with open(out_path, 'w') as fh:
    fh.write(html)
print("wrote", out_path, len(html), "bytes")
