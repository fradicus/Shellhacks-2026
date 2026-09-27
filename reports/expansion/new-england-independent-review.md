# F38 New England independent source review

**Result: pass for this non-publishable source-research checkpoint. Confirmed locations: 0.**

Reviewer: independent Codex session `/root/f38_source_review`, separate from the producer.
Review completed at actual UTC `2026-09-27T00:59:36.475690+00:00` (September 26 locally).
No production data, parser, loader, map, or other feature files were edited by this reviewer.
This review verifies transcription and source-bounded reconciliation; it does not approve locations or current construction activity.

## Evidence bound to this review

| Artifact | SHA-256 |
|---|---|
| [ISO-NE June 2026 RSP workbook](https://www.iso-ne.com/static-assets/documents/100037/final_rsp_project_list_jun_2026.xlsx) | `adfe05f5c0f24e260acca3b10c692785b4298a2067fa2e79efcf1d079953190d` |
| `data/expansion/batches/iso-ne-rsp-2026-06/research-cohort.json` | `fab174d1663138f1992375cb44b3ddb16dfe4ca1ee0ac9a331cf77a127df632c` |
| `data/expansion/batches/iso-ne-rsp-2026-06/dispositions.json` | `039ed3eb0911d310c4b3c7528002577bb07379fa45512539aca39994b7797b27` |
| `reports/expansion/new-england-bullets.md` | `6f2cf98b1b845e88b2380483a3ab01214440ae040285769543ee2620d730a5da` |

A change to these facts or artifacts needs a new review. The cohort also contains 300 individually recomputed project facts hashes.

## Independent method and results

Opened the original pinned XLSX directly with `openpyxl.load_workbook(read_only=True, data_only=True)`.
The verification script did not import or call `national.iso_ne`, `expansion.new_england`, or their helpers.
Source columns were checked by position against the actual header: C identity, D state, E/F owners, G footnote,
H projected month/year, I major program, J project, BF June status, and DE June estimated PTF cost.
A separate scan covered every worksheet cell and the workbook XML for conflicting restriction markings.

- `RSP_sortable` contains exactly 1,024 nonempty native IDs, all numeric and unique, in rows 2–1025.
- All 1,024 disposition IDs, rows, normalized statuses, selection decisions and reasons were recomputed and matched.
- All 300 cohort records were checked, not sampled: identity, name, primary and other owners, state, source status,
  normalized status, sheet/row/hash, projected date and precision, raw/numeric cost, major program, primary driver,
  part and footnote. All nine exported raw evidence fields matched the source cells.
- All 300 centers remain null, counties remain empty, and location review remains `unlocated`.
- All 300 project facts hashes matched independent JSON serialization and SHA-256 computation.
- Selection order and summary counts matched. The Markdown contains the same 300 IDs in the same order and labels every location unlocated.
- The direct workbook audit completed **14,010 assertions with zero mismatches**; the Markdown checks also passed.

| June 2026 source status | All source records | Selected |
|---|---:|---:|
| Planned | 37 | 37 |
| Proposed | 2 | 2 |
| Under construction | 7 | 7 |
| In service | 643 | 254 |
| Cancelled | 335 | 0 |
| Total | 1,024 | 300 |

Selection includes every planned/proposed/under-construction record, then the 254 in-service records with the
highest numeric native IDs. Native ID order does not establish chronology. The remaining 724 records are explicitly
deferred: 389 in-service and 335 cancelled. Case and whitespace variants in source statuses were correctly normalized.
Selected state counts are CT 92, ME 56, MA 101, NH 18, RI 18 and VT 15. These are source-reported state associations.

## Access and source scope

`06_2026_RSP!A1` explicitly labels this vintage **ISO-NE Public**. No conflicting CEII, confidential, proprietary,
restricted, copyright or disclaimer marking was found in the scanned cells or XML. No workbook license grant was
found; public access must not be described as an open license. This review supports the existing approved public-source
research use and does not establish new redistribution rights. The raw workbook remains outside committed artifacts.

The workbook has 20 sheets: five visible and 15 hidden/veryHidden. Only `RSP_sortable` contributes records; the other
current layouts overlap it and hidden historical sheets are excluded. Embedded external-link and VBA parts were absent.

The [publisher's source description](https://www.iso-ne.com/system-planning/system-plans-studies/rsp/rsp-project-list-and-the-asset-condition-list)
identifies the RSP as regional transmission planning projects and distinguishes its separate Asset Condition List.
It reports a typical March/June/October publication cadence, subject to change. This checkpoint replays the pinned
June vintage; latest-eligible and prior-comparable artifact acquisition remain pending. The inherited publication
and retrieval timestamps were not independently re-established by this workbook review.

## Factual caveats and retained evidence

1. **Projected dates:** all 300 H values are Excel datetimes under the projected month/year header. The source display
   uses month/year formatting. All exported normalized dates correctly retain month precision, including cells with
   hidden day values other than 1. These are not actual start or completion dates. June statuses do not establish
   September activity.
2. **Costs:** DE is estimated PTF cost with dollar formatting. Of 300 selected cells, 190 are numeric; 90 say `NR` and
   20 refer to a program or another project. The latter 110 correctly retain their text and have null numerical costs.
   No total-project-cost, award-value or actual-spend claim is supported, and these costs should not simply be summed.
3. **Programs and components:** the cohort has 300 distinct native project/component IDs, with 90 distinct nonempty
   major-program labels and 19 rows without such a label. Repeated programs, multi-site descriptions and shared
   facilities mean neither 300 distinct programs nor 300 distinct physical sites has been established.
4. **Explicit cross-list/cost notes:** `06_2026_RSP!A1051` says RSP 1815 covers ACL 98; `A1052` says the Eversource
   $3.7 million portion is added to RSP 1881. Both selected records retain their respective footnote numbers 1 and 2.
   These locators must be considered before future cross-source counting or cost aggregation.
5. **Scope and geography:** interconnection-driven transmission upgrades qualify as transmission work, but queue
   positions are not themselves construction-site IDs. Some descriptions cross regional or international boundaries
   (for example RSP 1545 mentions Quebec and Vermont); a source state is not full route geometry. No coordinate or
   endpoint is present in the reviewed extraction, and no geography was inferred from facility names.

## Code review and remaining gates

Read `pipeline/expansion/new_england.py` after the independent extraction. The bounded replay checks the pinned
workbook hash and source size, requires equality with the existing F30 corpus, rejects duplicate IDs and unexpected
statuses/states, and refuses non-null centers or already reviewed locations. The outputs explicitly disable publication.
No blocking source-audit defect was found in that bounded path.

This review does not satisfy the shared publication contract, latest/prior-vintage comparison, canonical program
and component reconciliation, independent project-to-location review, Atlas activation, or visible-map acceptance.
No source-backed row is promoted to a verified point. F38 remains incomplete.
