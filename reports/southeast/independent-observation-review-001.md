# Florida TLSA independent review addendum

Reviewer: `/root/f39_florida_review`, independent from producer.
UTC review time: 2026-09-27 01:29:12 UTC.
Reviewed artifact: `/private/tmp/gridbridge-f39-southeast/data/southeast/batches/florida-tlsa/observations.json`.
Reviewed artifact SHA256: `d6a06d3b03ef25373052a360a93d7bbd6e07e3172cb742ccf41f08bd97f71a51`.

## Result

PASS for a **nonpublishable factual-observation checkpoint**, subject to the limitations below. No factual transcription defect found in the reviewed 38 observations. This is not canonical-project, construction-status, coordinate, release, or statewide-coverage approval.

## Independent work performed

Read every generated observation, independently inspected the raw HTML table cells and hyperlinks with a separate stdlib HTML parser, and compared their meanings to the official pages previously browsed in the first review. Did not import or invoke producer extraction code. Compared all 16 GIS attribute dictionaries directly against the pinned ArcGIS JSON. Recomputed every declared source SHA256 from cached bytes. Checked the separate GIS object-ID response against the returned features. Checked all generated centers/review labels and publication flags.

- 38 observations = 17 current-index entries + 16 GIS records + 5 individual-page observations. They are not 38 distinct projects.
- Every GIS field/value equals the raw feature attributes, including floating-point source precision and conflicting county strings. The 16 feature IDs exactly match independently acquired IDs 1–16. There are 14 unique GIS certification IDs. `gis_acquisition_reconciled=true` is supported for this captured layer response.
- All 17 index facility names, licensing strings, raw certification codes, project hyperlinks, and certification-document hyperlinks correspond to the raw table. HTML linebreak/whitespace normalization is appropriate. In particular the raw index label TA07-14 remains visible and has not been silently changed to TA06-14.
- All 35 selected detail facts (7 fields on each of 5 pages) match their raw General Information table cells, with whitespace normalization and the Counties Crossed label's trailing colon removed. No construction/in-service fact is inferred from Date Certified.
- Every observation has `center=null`, `location_review=unlocated`, and `disposition=pending_project_reconciliation`; `new_confirmed_points=0`, `publication_eligible=false`.
- Set differences are correct as raw code comparisons: GIS-only TA06-14; index-only TA07-14, TA21-18, TA22-19, TA25-20. TA07-14 and TA06-14 should not be described as two unique projects.

## Source pin verification

All 8 source hashes match cached bytes:

| Cached file | SHA256 |
| --- | --- |
| conditions-certification.html | eb4ba8f79804e48ed53cd7cbc7d1018d4567af5439104363851c60cc8b3f5216 |
| transmission-attributes.json | 4d0611f68b0743df874795cfb1ea7921ab5a18c0b80bd2c00009295f61a5a483 |
| transmission-ids.json | ad2301c2b7ecfb0f6f1844e00bc8bb4eb080159cf02d1017ebecff02ba473124 |
| duke-energy-florida-llc-and-tampa-electric-company-lake-agnes.html | 3b6644336997e23d96815d80f3be786c65b7693cb1ff05cd351cba03cc6a3332 |
| florida-power-light-bobwhite-manatee-line.html | 2e8249d5f714a27082b8839e9127e2e1b8fd244ba272917fc9e2eea2e66f9fd3 |
| florida-power-light-duval-raven-line.html | abd249bdbc370bb8dc80f00043ee720e1d5fa8bf47cbae7072400e1eb12dd3eb |
| ouc-st-cloud-magnolia-230-kv-line.html | caeb2e5a52296c2f15a6f1c11f18a876d6486bf2ed0de17df34713d4c9423add |
| seminole-electric-cooperative-inc-and-jea-keystone-firestone.html | 08b9465e37f3de597dfcd6490fe62aeab9d94806102d8bf82643d6211f29f510 |

Source URLs are recorded in reviewed artifact and in original independent review. Locators: current index `Transmission Lines` table, one row per raw certification; GIS `features[].attributes.OBJECTID`; each individual page's `General Information` table. Linked certification documents were not reviewed and are only link observations.

## Outstanding factual issues

1. Bobwhite identity discrepancy remains unresolved by merely counting agreeing sources: index and its linked filename use TA07-14, while detail table, GIS, and historical PDF use TA06-14. The detail page's application hyperlink also filters SCO Number TA07-14. Obtain actual certification/decision evidence before choosing a canonical native ID; the present raw observations appropriately preserve both.
2. Lake Agnes length and construction scope, and Seminole–Keystone–Firestone county differences remain as described in first report. Joint-license GIS duplicates require canonical reconciliation.
3. The historical PDF is not represented by these 38 observations. Its relinquished Lake Tarpon–Kathleen record and its explicit source errors must remain in a separate historical disposition/evidence record before claiming historical-universe completion.
4. No geometry was included or reviewed. Endpoint descriptions are source statements, not location verification. No current operation dates or complete Florida project coverage have been established.
5. Retrieval timestamps were read as acquisition metadata but cannot independently be proven by hashes alone. Null publication dates do not assert that retrieval establishes source freshness.

No repository mutation performed. Only this requested addendum was written.
