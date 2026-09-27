# Texas statewide checkpoint — 2026-09-27

F41 part 4 processes all 2,049 observations in the July 2026 ERCOT TPIT Planned, Future and Completed sheets.
Five identical Future ID repeats retain both row citations and produce 2,044 canonical projects. This is
source-bounded ERCOT coverage, not an inventory of every Texas project. No independent review is claimed.

| Location evidence | Source rows | Unique projects |
|---|---:|---:|
| Both endpoints matched | 184 | 183 |
| One endpoint matched (partial) | 453 | 452 |
| County only, approximate display dots | 1,221 | 1,218 |
| Unlocated | 191 | 191 |
| Total | 2,049 | 2,044 |

The 635 candidate projects (443 distinct centers) and 1,218 county-reference projects make 1,853 projects geographically displayable.
County projects have 1,407 linked anchors because some name multiple counties. They remain 1,218 projects;
coincident county dots are not separate physical sites. Exact centers stay null for these projects. All candidate
and county locations are excluded from overlap calculations. Nothing is promoted to independently confirmed.

Of 3,078 named terminal observations, 821 match uniquely, 80 are ambiguous and 2,177 do not match; another
1,020 endpoints are unnamed. The 80 ambiguous terminals affect 77 source rows. An ambiguous endpoint can
coexist with one uniquely located endpoint, or fall back to an explicitly named county.

## Evidence and reproduction

- [ERCOT TPIT workbook](https://www.ercot.com/files/docs/2022/03/02/ERCOT-July-Ad-Hoc-TPIT-No-Cost-071326-UPDATE.xlsx),
  publication 2026-07-17, source as of 2026-07-13; reacquired 2026-09-27T03:35:39.681487+00:00.
  SHA-256 `4a08ea0f26af780f0d63c21304f3969ee876a49b152b827be8b48b8edb655b05` is recorded in the source audit
  and release (use those machine-readable values for validation).
- [OpenStreetMap](https://www.openstreetmap.org/copyright), 3,303 named Texas `power=substation` elements,
  retrieved 2026-09-27T04:27:42.066573+00:00 through the existing Overpass URL and User-Agent.
  Raw SHA-256 `06761811150e2b77d014db261d06f4d94d2557b9763cc72a514fb6331a6f6a69`.
- [Census TIGERweb county layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1),
  all 254 Texas counties in WGS84, full-detail geometry, retrieved 2026-09-27T04:28:01.907936+00:00.
  Raw SHA-256 `91cd7e6a83d9e7993981cae980dfe4a76bba147a94abd94f71d7f15019d773c4`.
- County display coordinates reuse the committed Census Gazetteer representative points. The facility ledger
  retains the Gazetteer URL, retrieval time and hash separately from TIGERweb containment evidence.

Raw workbook, OSM and TIGER downloads remain outside Git. `data/texas/statewide/facilities.json` is a derived
ledger with OSM IDs and links, names/aliases, reference points, county assignments, exact requests, hashes and
observed retrieval times. OSM-derived entries are © OpenStreetMap contributors under
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Retain this attribution with selection and exports.

Run `PYTHONPATH=pipeline python -m texas.statewide_acquire /private/tmp/f41-statewide-raw` to fetch the
fixed queries, then `PYTHONPATH=pipeline python -m texas.statewide /private/tmp/f41-statewide-raw` to derive
the artifacts. New upstream responses require a separately checked and pinned release; acquisition never
silently updates the active manifest. `texas.statewide_publish.apply_release` verifies file pins and replays
matching, centers, source row identities, duplicate reconciliation and tier counts before national assembly.

## Differences from the supplied prototype

The reacquired OSM elements equal the supplied prototype's elements. Full-detail TIGERweb boundaries place
Fowlerton Substation (`way/489376594`) in McMullen County; the prototype's simplified boundary assigned it to
LaSalle. Consequently `15TPIT0044` loses its tentative endpoint and uses its named county reference, while
`110228` gains the Fowlerton endpoint and becomes a two-endpoint candidate. The raw misspelling `Stonwall` on
`105424` is retained and unresolved; it is not silently corrected to Stonewall. These explain the differences
from the prototype counts. No fuzzy facility or county correction is used.

Future duplicate IDs `102795`, `110733`, `110749`, `110751`, `110753` collapse only because all extracted facts
except source row number agree. Conflicting duplicates stop publication. Completed-sheet/row-status conflicts
remain visible with unknown lifecycle grouping; projected and actual dates retain their source precision.

## Publication state

The eight-project C29 checkpoint (#168) merged unchanged. This broader release uses C32 (#178, issue #179)
and a separate fixed manifest. The F30 slot must select statewide when active, otherwise C29, never both.
This checkpoint supplies validated producer artifacts; it does not yet claim an Atlas load or selectable map
dots. F31/F19 retain their existing API and map ownership. The UI uses the same map with “Tentative” or
“County reference — exact site unknown” labels and keeps all projects at shared county anchors accessible.
