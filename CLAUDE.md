# CLAUDE.md

Context for an AI agent picking up this repository cold.

## What this is

A forensic record of one specific measurement (SWIM-1033, Ireland circumnavigation distance),
not a running application. There is no server to start and no tests to run. The value here is
the documentation in `docs/` and the scripts in `scripts/`, which are a record of exactly what
was computed, in what order, and why each earlier attempt was wrong.

## If you are asked to redo or extend this measurement

Read `docs/01-overview.md` through `docs/06-analysis-page-and-deployment.md` in order first. Do
not start from the scripts. The two bugs documented in `docs/02-data-source.md` and
`docs/04-leg-numbering-bug.md` are easy to reintroduce if you rebuild this from first principles
without reading why they happened the first time.

## If you are asked to do this for a different landmass or swimmer

Do not fork this repository. Use the packaged, general version instead:
[Claude Code Skills](https://github.com/rosevillanuevadev/claude-code-skills), file
`circumnavigation-distance/SKILL.md`. This repository is the case study that skill was written
from; the skill is what should actually be invoked for new work.

## House style

No em dashes or en dashes anywhere in this repository, including generated content. Use commas,
periods, or restructure the sentence instead.

## Known gaps in this record

The raw GPX files themselves are not included in this repository (swimmer's original data,
provided by WOWSA, not this project's to redistribute). `scripts/` assumes they are available
locally at a path passed as an argument; see each script's docstring.
