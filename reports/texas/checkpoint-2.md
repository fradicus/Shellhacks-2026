# Texas checkpoint 2: planned cohort and Georgetown candidates

Source-bounded extract: `PlannedTPIT071326NoCost` from the [ERCOT July TPIT workbook](https://www.ercot.com/gridinfo/sysplan).
The [ERCOT terms](https://www.ercot.com/help/terms) permit public raw data in compilations. We retain bounded
factual fields and locators, while excluding descriptions, contact details, costs, SSWG bus lists and the raw file.
The source workbook SHA-256 is recorded in `data/texas/source-audit.json`. Reproduce with:

`PYTHONPATH=pipeline python -m texas.tpit <local-workbook.xlsx> <local-city-gis.geojson> data/texas`

The complete sheet has 358 rows with 358 distinct native IDs: 301 Planned, 25 Under Construction,
13 Conceptual, 11 In-Service and 8 with no row status. Seven titles are blank. Every row retains the raw
planned/actual milestone and explicit month precision where the workbook header specifies Month/Yr; a day
in Excel storage is not treated as an exact day. The sheet cohort remains "planned" even for In-Service rows.
Every observation currently has `needs_scope_review`; this is a research cohort, not an active snapshot.
Across all four TPIT project sheets, 2,127 rows contain 2,122 unique IDs. Five repetitions occur within the
Future sheet; none of the Planned IDs appear in another project sheet. This does not prove other sources are distinct.

The [City of Georgetown public Electric Substations layer](https://gis.georgetowntexas.gov/arcgis/rest/services/GUS/GUSOPERATIONS_Webmap/MapServer/31)
returns seven facility points. We used three named facilities. A facility point is location evidence for a named
endpoint, not proof that construction is underway there. The source names and the exact normalized terminal
matches are preserved. All three facility points resolve to Williamson County (48491) in the
[US Census Geocoder](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html):

| ERCOT row / ID | Named terminal | City GIS facility | Location meaning |
|---|---|---|---|
| Planned row 67 / 80546B | Georgetown East (to) | GEORGETOWN EAST | Candidate, one endpoint |
| Planned row 105 / 92629 | Gabriel Substation (from) | GABRIEL | Candidate, one endpoint |
| Planned row 285 / 80546C | Georgetown East (from) | GEORGETOWN EAST | Candidate, one endpoint |
| Planned row 333 / 85973 | Georgetown Substation (from) | GEORGETOWN | Candidate, one endpoint |

Four project observations share three physical points. The city GIS does not establish a construction project
link on its own. We make the project link only through the explicit terminal in the ERCOT row, unique normalized
facility name and the named county. `Substation` is removed only as a generic facility suffix. There is no fuzzy
matching or owner substitution. The GIS layer's `OWNER` values remain raw; ERCOT's `LCRATSC` and city `LCRA`
are not silently made identical. Every point is **candidate**, has no independent review and is excluded from
pair matching. None is an official project coordinate. Source coordinates are WGS84 query output; they are not
survey-grade location claims. Counts: 358 extracted, 4 candidate projects, 3 distinct candidate facilities,
0 confirmed, 4 schema-valid records staged for publication, 0 loaded and 0 visible on `/time` from this batch.

## Checks and next gate

The extractor rejects changed sheet/column headers, an unexpected row count, duplicate IDs, ambiguous facility
names, wrong county labels and out-of-Texas coordinates. Its focused test verifies month precision, candidate
labels, nonmatching rows and fail-closed duplicates. `data/texas/publication-candidates.json` and `publication-source.json` stage only the four manually
scope-reviewed transmission projects as national-schema-valid candidates. The other 354 observations still
need individual scope review. The exact fixed Texas activation path and national build hook need a contract and
F30 owner implementation; F19/F31 must display candidate evidence distinctly.
A successful research extract is not a completed map delivery.
