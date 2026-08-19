# 06. The analysis page and deployment

## Two different documents, not one

Partway through this build it became clear two separate deliverables were needed, and conflating
them was a mistake worth recording:

1. **A route analysis document**, to send to the swimmer and observer, asking them to account for
   the remaining real gaps. This needs the full GPX track, the computed route, the gap list, and
   is explicitly a work-in-progress request for information, not a finished record.
2. **A public source-of-truth ratification page**, the eventual permanent record, which should
   show the final adopted distance and hide the internal review process (rejected methods, gap
   review notes, and so on).

Only (1) was built and published in this session. (2) is future work once the swimmer and
observer respond.

## Why a static Artifact preview was not enough

An early version of this page was built and iterated on as a Claude Artifact, which is useful for
fast iteration but runs under a strict content security policy that blocks any live network
request, including the Google Maps JavaScript API and live map tiles. The final page needed a
real, interactive map showing both the swimmer's actual GPX track and the computed route
together, which requires a live Google Maps embed. The page was rebuilt as a standalone HTML file
outside the Artifact sandbox once that requirement was clear, and Chrome was used locally
(`open file.html`) to preview it during development, since Artifact preview could not render it.

## Page contents

- Swim details (swimmer name, SWIM ID, start and finish date/time, taken directly from the GPX
  files' own timestamps, not estimated)
- A stat strip: total distance, waypoint count, run count, raw point count, excluded gap total
- A live Google Map (`mapTypeId: roadmap`, custom dark style array matching WOWSA's internal
  visual style) with three independently toggleable layers: the swimmer's GPX track, the computed
  route, and the remaining gaps
- A gaps table, largest first, tiered as substantial (>=5km) versus minor (<1km, most likely GPS
  drift on resuming a swim)
- A plain-language methodology footer

Colors were iterated several times based on visual contrast feedback against the live map's own
default coloring (which uses blue for water and green for land in most Google map styles): ended
on magenta for the swimmer's track, green for the computed route, and yellow for gaps, against a
custom dark basemap style, none of which collide with each other or with the map's own default
palette.

## Deployment

Deployed as a Cloudflare Worker with static assets (`wrangler deploy`, not the older
Pages-specific flow), to the WOWSA Cloudflare account (`contact@openwaterswimming.com`).

**The `openwaterswimming.com/ratifications/` path is served by a separate WordPress
installation, not this Workers-routed infrastructure.** This was discovered mid-deployment and
avoided by choosing a path outside that prefix.

Final URL: `openwaterswimming.com/routes/swim-1033`, wired up as four Cloudflare Worker Routes
(the exact path and a wildcard, both apex and `www`) pointing at the `swim-1033` Worker script,
alongside the existing `learn-router` and `wowsa-staff-hub` Workers already running on the same
zone.

**One real deployment bug**: the first route configuration returned 404 on the custom path even
though the Worker itself was correctly triggered (confirmed via DNS proxy status and Worker
script existence checks). Cause: the Workers static-assets system only serves a file at a path
that exactly matches something in the deployed asset bundle, and the bundle only contained
`index.html` at the root. A request for `/routes/swim-1033` had nothing to match. Fix: set
`"not_found_handling": "single-page-application"` in the assets config of `wrangler.jsonc`, which
serves `index.html` for any unmatched path. See `scripts/wrangler.jsonc` for the working config.

## What to reuse for the next swim

Everything in this document except the WOWSA-specific dark color palette and the specific
Cloudflare route path is landmass-agnostic. See the
[Claude Code skill](https://github.com/rose2023va/claude-code-skills) for the packaged, reusable
version of this whole pipeline.
