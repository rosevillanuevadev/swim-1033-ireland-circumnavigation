# SWIM-1033: Ireland circumnavigation distance build

A forensic record of how the shortest-swimmable-path distance for Daragh Morgan's Ireland
circumnavigation (SWIM-1033) was computed, from a 101-file GPX log to a published route
analysis page, recorded during the session that built it on 19 to 20 August 2026.

This is the source of truth for how this specific measurement was produced. If you are picking
this up cold, read `docs/` in order before touching the code. The general, reusable version of
this method lives as a Claude Code skill in a separate repository:
[Claude Code Skills](https://github.com/rose2023va/claude-code-skills), file
`circumnavigation-distance/SKILL.md`. This repository is the case study that skill was
distilled from.

---

## Start here

| If you want to | Read |
|---|---|
| Understand the problem and the adopted rule | [docs/01-overview.md](docs/01-overview.md) |
| Know why the coastline data source changed, and to what | [docs/02-data-source.md](docs/02-data-source.md) |
| Understand the waypoint algorithm itself | [docs/03-algorithm.md](docs/03-algorithm.md) |
| Read about the leg-numbering bug, the most important finding in this build | [docs/04-leg-numbering-bug.md](docs/04-leg-numbering-bug.md) |
| See every distance figure produced, in order, and why each changed | [docs/05-results.md](docs/05-results.md) |
| Understand the published analysis page and how it was deployed | [docs/06-analysis-page-and-deployment.md](docs/06-analysis-page-and-deployment.md) |
| Look up a term | [reference/glossary.md](reference/glossary.md) |
| Run the actual code | [scripts/](scripts/) |

---

## The shape of it in one paragraph

A swimmer's circumnavigation distance cannot be measured as a straight line between two points,
because a circumnavigation starts and ends at the same place. The adopted rule instead finds the
fewest possible waypoints, taken from the swimmer's own GPS track, connected by straight lines,
such that none of those lines cross land. That rule needs an accurate map of where land is. The
first attempt used a coarse, widely available dataset (Natural Earth) and produced numbers that
looked plausible but were wrong, both too short in places (real crossings it missed) and too long
in places (real coastline it double counted because of a second, more serious bug). The second,
much larger finding was that the GPX files' own numbering does not reliably reflect the order the
swimmer actually covered the coast in, so consecutive-by-filename legs were repeatedly mistaken
for real gaps in coverage when the true adjacent leg simply had a different number. Fixing both
problems, and switching to a precise, once-downloaded, locally cached global coastline dataset,
produced the final published figure: **1,383.47 km**.

---

## Redactions

This repository is public. One thing is held back and replaced with a placeholder:

| Placeholder | What it is |
|---|---|
| `[GOOGLE_MAPS_API_KEY]` | The Google Maps JavaScript API key used to render the published analysis page |

The real key lives in the swimmable-distance calculator's gitignored `config.py` and in
Cloudflare, not in this repository.

Swimmer contact information, observer contact information, and any content from internal WOWSA
communications (WhatsApp, email) are not recorded here. Only the technical build is.

---

## How this was built

Working from the swimmer's 101 raw Garmin GPX leg files, inside a single continuous working
session with Rose (WOWSA). Every dataset, script, and figure in this repository was produced and
verified during that session, not reconstructed afterward. See
[docs/01-overview.md](docs/01-overview.md) for the full narrative.
