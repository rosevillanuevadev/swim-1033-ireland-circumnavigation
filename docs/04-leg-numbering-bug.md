# 04. The leg-numbering bug

This was the single largest correction in this build, larger in effect than the coastline data
source change described in [02-data-source.md](02-data-source.md). It is documented in detail
because the same mistake is easy to repeat on any future multi-leg swim.

## The assumption that broke

The 101 GPX files are named `Leg 1.gpx` through `Leg 100.gpx` (with `Leg 88 Part 1` and
`Leg 88 Part 2` as one split file). The first version of the "which legs are continuous, and
where are the real gaps" check assumed that if `Leg N`'s end point was far from `Leg N+1`'s start
point, that meant no GPS-recorded swimming connected them, a genuine gap, most likely boat
transit.

That assumption produced **24 flagged gaps totaling 511.7 km**, several individually as large as
43 to 55 km. That result was drafted directly into a message intended for the swimmer and
observer, asking them to account for boat transits that, as it turned out, never happened.

## How it was caught

Not by a test. Rose asked to see the swimmer's actual GPX track overlaid on the computed route on
a real map (Google Maps, not the earlier schematic SVG), specifically so gaps could be sanity
checked by eye. Looking at the rendered map, in more than one region (Galway Bay to the Cliffs of
Moher area, and separately near Ardmore/Dungarvan Bay on the south coast), the swimmer's actual
track ran smoothly and continuously along the coast, curving naturally around the headland, while
the flagged "gap" line cut a straight chord across land, well inland of where the real track
actually went.

The direct quote that identified the mechanism: *"there are some gaps, but others are not real
gaps, just went different direction, but still continuous... the gap must fill in the gpx, and
the gpx must clearly show the gap."*

## Confirming it computationally

For the largest flagged gap (Leg 95 end to Leg 96 start, claimed 54.9 km), every *other* leg's
points were checked against that specific corridor. Two things fell out:

- Leg 98 ends at essentially the exact coordinate where Leg 96 starts (0.0008 km apart).
- The broader corridor (Galway Bay mouth to Doonbeg, including Doolin and the Cliffs of Moher)
  is fully covered by Legs 93, 94, 95, 96, 98, and 99, none of which are numerically adjacent to
  each other in the way the file-number assumption required.

The conclusion: **leg file numbers do not reliably reflect the geographic or chronological order
the coastline was actually swum in.** Over a 7-month, 101-session expedition, sections were
evidently filled in out of order, most likely due to tides, weather windows, and logistics, and
the numbering does not capture that.

## The fix

Replaced file-number adjacency with a proper nearest-endpoint reconstruction:

1. For every leg, compute its start and end point.
2. Starting from `Leg 1` (the known start, Foudra Rock), greedily walk the chain: from the
   current end point, find whichever *unused* leg has a start or end point closest to it
   (checking both orientations, since a leg might need to be traversed in reverse), and continue
   with that leg.
3. If the closest available leg's matching endpoint is still farther than 300m away, that is a
   genuine, real gap, recorded as such.
4. Continue until all 101 legs are placed into the chain.

Implementation: `scripts/reconstruct_true_chain.py`.

## Result of the fix

| | File-number order (wrong) | True endpoint-matched order (correct) |
|---|---|---|
| Flagged gaps | 24 | 9 |
| Total gap distance | 511.7 km | 15.2 km |
| Largest single gap | 54.9 km | 9.5 km |
| Gaps over 5 km | 18 | 1 |

Every one of the 18 "substantial" gaps that would have been sent to the swimmer and observer for
explanation was an artifact of this bug. The 9 real gaps that remain are all consistent with
normal GPS drift on resuming a swim, except one (Leg 90 to Leg 89, 9.5 km), which is a legitimate
open question.

A second, related question in the original flawed analysis, an apparent "sequencing" ambiguity
around Legs 75 to 83 on the Iveragh and Dingle coasts, where several legs shared near-identical
coordinates, turned out to be the same bug in a different form: those legs were simply
non-adjacent in file number but geographically continuous once matched correctly. The corrected
chain reconstruction connected all of them with no gap at all. That question did not need to be
asked.

## The general lesson

A gap-detection method built on any externally imposed ordering (file name, upload timestamp,
sequence number) is only as trustworthy as the assumption that the ordering reflects reality. For
a multi-session expedition swim recorded as separate files, that assumption should be treated as
unverified until checked, not as a given. The correct check is geometric: does *any* other
recorded segment, regardless of its name or number, actually connect to this endpoint. See
`scripts/reconstruct_true_chain.py` for the reusable implementation, and the
[Claude Code skill](https://github.com/rosevillanuevadev/claude-code-skills) for how this is packaged for
reuse on future circumnavigation swims.
