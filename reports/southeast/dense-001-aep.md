# Dense Southeast 001: AEP Transmission state maps (C40)

Source: AEP Transmission's public project maps (`/<state>/geojson/map-setup.json`) and one page per project, for
Kentucky, Virginia, West Virginia, Tennessee, Louisiana and Arkansas. Every point is AEP's own marker for the project
(C40 `official` tier), with unstated placement precision, never independently reviewed.

| State | Projects | Located | Not in service | With a dated update |
|---|---|---|---|---|
| VA (51) | 28 | 28 | | |
| WV (54) | 25 | 25 | | |
| KY (21) | 9 | 9 | | |
| LA (22) | 9 | 9 | | |
| AR (05) | 7 | 7 | | |
| TN (47) | 0 | 0 | | |
| **Total** | **77** | **77** (74 distinct points) | 74 | 24 |

- Excluded: Virginia's two "Projects Overview" umbrella pages (CVTRP, Independence) and Tennessee's "No Active
  Projects" placeholder marker (lat −55). The Pure Salmon and Sourwood–Hales Branch pages appear on both the
  Virginia and West Virginia maps; each is one project, recorded once with the other listing as a duplicate.
- Status comes from each map's own legend label (pending → proposed; approved/current → planned), overridden only by
  a plain past/present statement in the newest page update (F40's rule): 3 in service, 2 under construction.
- History: a page's newest "Project Updates" entry becomes a `source_status` event dated only to the year its heading
  names (e.g. "Summer 2026"); no exact date is invented. One Virginia page returned HTTP 404; its map facts remain.

## Spot check (12 random records, seed 39)

Compared each marker with the place names in the project title: Altavista–Leesville, Fort Robinson–Hill (Scott Co.),
Stuart, Claytor, Washington County (Abingdon), Fieldale–Ridgeway, Reusens–Roanoke, DeQueen–Nashville (midway),
Ashdown–12th Street (between Ashdown and Texarkana), Sabine Parish, South Shreveport–Wallace Lake, Tri-State–East
Lynn. All 12 fall at or between the named places. Errors found: 0. Ashdown–12th Street is marked in service from
"the majority of construction … concluded, and assets were placed in service"; the full update text is retained.

Reproduce from `pipeline/`: `uv run python -m southeast.aep fetch --cache <dir>` then `build --cache <dir> [--check]`.
