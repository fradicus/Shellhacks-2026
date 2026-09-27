# F41 part 2: July 2026 ERCOT Future and Completed cohorts

The pinned public [ERCOT TPIT workbook](https://www.ercot.com/gridinfo/sysplan) has 1,429 nonblank Future-sheet
rows (1,424 unique native IDs) and 262 Completed-sheet rows (262 unique IDs). The five repeated Future IDs are
`102795`, `110733`, `110749`, `110751` and `110753`. These remain separate source observations; none enters
the staged set. Together with the 358 Planned-sheet rows from part 1, this is 2,049 observations across three
sheets, not a count of unique Texas projects. Rows retain their source sheet and row, raw status, month-precision
milestones, source hash and nullable location. The workbook hash is recorded in `data/texas/more-summary.json`.
The raw workbook remains outside the repository.

Four Future-sheet line projects join the four Planned-sheet candidates. Their named terminals match unique
features in the [City of Georgetown utility GIS layer](https://gis.georgetowntexas.gov/arcgis/rest/services/GUS/GUSOPERATIONS_Webmap/MapServer/31).
[Census coordinate-to-county checks](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html) placed
the relevant facilities in Williamson County (48491). All eight are **candidate** locations with
`location_review=unreviewed`; the GIS facilities are supporting asset evidence, not separate projects.

| ERCOT ID | Future row | Location used | Basis | Projected service month |
|---|---:|---|---|---|
| `109790` | 940 | Gabriel and Rivery | Mean of two endpoints | 2029-05 |
| `109814` | 1140 | Glasscock | One endpoint | 2030-02 |
| `110122` | 1358 | Gabriel | One endpoint | 2031-12 |
| `110120` | 1366 | Gabriel | One endpoint | 2031-12 |

For row 1140, the terminal county cell is blank. The source owner is `LCRATSC`, the matching GIS facility is
marked `LCRA`, and [LCRA identifies its transmission role](https://www.lcra.org/energy/electric-transmission/).
That supports a labeled candidate, while the missing county remains null in the evidence. The other three
candidate rows have a Williamson County entry at each used terminal. One-endpoint centers do not locate the
full line route or its unknown other endpoint.

Future row 555 describes an Aviation Substation addition between Gabriel and Glasscock; those line terminals do
not locate Aviation. Completed row 48 likewise describes a Florence Substation addition whose named terminals
do not locate Florence. Completed row 35 names Chief Brady and Georgetown line terminals, but its row status is
`Planned` despite appearing on the Completed sheet. The source conflict remains visible in the observation, and
this checkpoint stages no Completed-sheet project. A row on that sheet does not by itself establish completion.

**Release state:** 8 staged candidates at 5 distinct center coordinates; 0 accepted release entries, 0 Atlas load
receipts and 0 verified visible Texas selections from this batch. No independently confirmed or official-coordinate
project has been claimed. The next task is the fixed publication contract and loader/map handoff in
[issue #164](https://github.com/fradicus/Shellhacks-2026/issues/164).
