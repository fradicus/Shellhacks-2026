# F41 part 3: Fixed Texas candidate release

The July 2026 [ERCOT TPIT workbook](https://www.ercot.com/gridinfo/sysplan) and the
[City of Georgetown utility GIS layer](https://gis.georgetowntexas.gov/arcgis/rest/services/GUS/GUSOPERATIONS_Webmap/MapServer/31)
were downloaded again on 2026-09-27 at 03:35:39 UTC. The local file completion times are recorded separately
in `data/texas/source-audit.json` and `data/texas/geo-source.json`; both new SHA-256 digests exactly match the
previously pinned source files. This supplies an observed retrieval time without asserting when the earlier
inspection download happened. The raw workbook and GIS response remain outside the repository.

`data/texas/releases/active.json` is the sole proposed activation input. It freezes the exact source and project
file hashes, observation ledgers, eight project IDs, ERCOT sheet/row locators, named terminal links, GIS feature
IDs, centers and expected counts. A separate seven-feature `facility-ledger.json` pins the public GIS names,
IDs, owners and coordinates used for unique terminal matching; these are assets, not project records.
`texas.publish.apply_release` validates those records before adding the source
and projects to an in-memory national snapshot. Missing active input leaves the snapshot unchanged; a changed
hash, row, identity, status, date, county link, CRS, center or retrieval time fails closed. No observation file
is imported by a directory scan.

| Stage | Texas projects | Meaning |
|---|---:|---|
| Three-sheet ERCOT observations | 2,049 rows | Research ledger, includes repeated native IDs |
| Staged publication candidates | 8 | Seven partial one-endpoint centers; one two-endpoint mean |
| Fixed accepted release | 8 | All `unreviewed` candidates at five distinct center coordinates |
| Atlas load receipt | 0 verified | F30 loader hook and successful Action still needed |
| Active Atlas read | 0 verified | No read-only response for this batch yet |
| Selectable `/time` Texas project | 0 verified | F19 currently filters confirmed national points |

The one-endpoint location is a partial line reference, not a route or construction site. Candidate records stay
outside overlap matching and receive no confirmed badge. The three-sheet observation count is not a count of
unique Texas projects or statewide coverage. The source/GIS and project evidence remain visible in the released
records. C29 and [issue #164](https://github.com/fradicus/Shellhacks-2026/issues/164) define the separate F30,
F31 and F19 integration work before a live map claim.
