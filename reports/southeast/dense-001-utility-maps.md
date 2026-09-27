# Dense Southeast 001: AEP and Duke utility project maps (C45)

Source: AEP Transmission's public project maps (`/<state>/geojson/map-setup.json`) and one page per project, for
Kentucky, Virginia, West Virginia, Tennessee, Louisiana and Arkansas. Every point is AEP's own marker for the project
(C45 `official` tier), with unstated placement precision, never independently reviewed.

| State | Batch | Projects (all located) | Not in service | Dated |
|---|---|---|---|---|
| VA | aep | 28 | 27 | 7 |
| WV | aep | 25 | 24 | 8 |
| KY | aep / duke | 9 / 7 | 9 / 7 | 2 / 0 |
| LA | aep | 9 | 9 | 4 |
| AR | aep | 7 | 6 | 3 |
| FL | duke | 22 | 21 | 15 |
| NC | duke | 22 | 22 | 4 |
| SC | duke | 12 | 12 | 7 |
| TN | aep | 0 | 0 | 0 |
| **Total** | | **140** (137 distinct points) | 137 | 50 |

Two Duke Ohio/Kentucky projects also count in Ohio (39). "Dated" means a dated event or in-service value.

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

## Duke Energy (`duke`)

Duke's transmission-project map (`/-/media/json/maps/transmission-projects/data.json`) gives one point per project;
63 of its 92 entries are in F39 states (Ohio/Indiana-only entries excluded). The map has no status. A project page's
schedule is read only from an explicit completion statement ("Expected Completion : 2026", "In-service Date:
November 2023", "expected to be completed by mid-2026"): a planned milestone at month or year precision, or a
`completion` event for past tense ("This project was completed in March 2023"). Pages whose phases state different
years stay unknown. 26 projects are dated; 3 pages returned HTTP 404 (map facts kept).

Spot check (12 random, seed 39): Brooker Creek–Tarpon Springs, Archer, Crystal River–Bronson, Wilmington NE, Perth
Road (Iredell), Eustis–Dona Vista, Patriot (Anderson Co.), Morrisville, Fayetteville–DuPont, Piedmont and Lee,
North Central Florida (Hamilton/Madison), Robinson Plant–Rockingham. All 12 points fall in the named city/county.
Errors found: 0.

Reproduce from `pipeline/`: `uv run python -m southeast.<aep|duke> fetch --cache <dir>` then `build --cache <dir> [--check]`.
