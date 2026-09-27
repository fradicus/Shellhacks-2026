# Southeast checkpoint 001: Florida certification reconciliation

Research only. 0 new confirmed locations; 0 newly activated projects. All twelve states remain incomplete.
Run/ownership: C24/F39, Codex Southeast session, 2026-09-27 UTC. C23/F38 work stays with its separate owner.

## Acquired official sources

- [Florida DEP certified facilities list](https://floridadep.gov/sites/default/files/list_certified_facilities.pdf),
  SHA256 `cdf0c45a140723769d3aa5921b430b07aa220dca4c245148cf00cc3a6eddbb63`, seven pages. Footer prepared
  2022-01-20. Landing page modified 2025-07-25 does not establish a newer document vintage. Transmission rows are
  on pages 6–7. Power plants and gas pipelines are outside this batch. Raw artifact cached outside Git.
- [DEP transmission GIS layer](https://cadev.dep.state.fl.us/arcgis/rest/services/OpenData/ARMS/MapServer/5),
  bounded attributes-only query, SHA256 in the research manifest. Returned 16 features, no exceededTransferLimit;
  an independent count/IDs query is still required to prove full acquisition. These contain 14 certification IDs.
  No geometry acquired or promoted. Layer CRS metadata reports 102967 / latest 6439, polyline geometry.

## Reconciliation findings

- TA07-16 occurs in two GIS rows (Duke and Tampa Electric); TA90-08 occurs in two (Seminole and JEA).
  Preserve component/licensee observations and establish canonical project identity before counting projects.
- The PDF page 7 notes only the DEF portion constructed for Lake Agnes–Gifford. GIS descriptions alone do not
  support presenting both portions as completed. PDF length 32.5 miles differs from GIS and the
  [official project page](https://floridadep.gov/water/siting-coordination-office/content/duke-energy-florida-llc-and-tampa-electric-company-lake-agnes)
  stating 27.5 miles. Preserve conflicting observations until scope/vintage is resolved.
- PDF page 6 contains Lake Tarpon–Kathleen certification history including denial, appeal, approval and
  relinquishment. It is absent from the returned GIS features. GIS therefore cannot alone reconcile this register.
- Page 7 has multirow/merged cells around Duval–Raven and St. Cloud East–Magnolia Ranch North. Text extraction
  is ambiguous about certification ID placement; visually inspect the PDF and corroborate individual official
  pages before normalizing either record. Do not silently assign the extracted adjacent ID.
- Certifications date to historical periods. They are permitting evidence, not actual in-service dates.
  The selected GIS source has no supported publication date; retrieval is recorded separately.

## Next work and gaps

Complete visual PDF reconciliation, validate GIS count/IDs, review individual official pages and public geometry
metadata/access, then independently verify exact endpoint/project links. No route vertex will be treated as an
endpoint solely because it appears first/last in an array. Current Florida utility plans and provider inventory
remain required; this historical certification source is only one part of statewide coverage. Georgia repair and
AL/MS/SC/NC/TN/KY/VA/WV/AR/LA source inventories remain outstanding. Publication requires a shared additive contract
for new national projects/sources, followed by F30/F31/F19 integration and Atlas/map acceptance.

## Follow-up evidence: 2026-09-27

Independent review is recorded in independent-source-review-001.md. The complete GIS ID query matches all 16
returned feature IDs, proving acquisition completeness for that layer response. The current official transmission
index contains 17 rows. It includes Sweatt–Whidden and DeLand West–Dona Vista beyond the older GIS/PDF coverage.
The historical relinquished Lake Tarpon entry remains separately relevant. This is not all Florida construction.

Five individual DEP pages are now hash-pinned. Their General Information tables corroborate St. Cloud as OUC,
TA21-18, and Duval–Raven as FPL, TA16-17. The PDF's St. Cloud ID/licensee cells are erroneous. The index itself
labels Bobwhite TA07-14 while its individual page, PDF and GIS say TA06-14; these remain distinct observations
of one identity discrepancy, not two approved projects. Joint-licensee detail pages support the two GIS duplicate
pairs. No construction-status or coordinate approval follows from this review.

Replay: from pipeline, `uv run python -m southeast.florida --cache /private/tmp/gridbridge-southeast-sources --check`.
The parser requires pinned hashes, exact reviewed index row count, unique source IDs and matching GIS ID lists.
It preserves all factual observations and never fetches document links or creates a non-null center. The new-project
publication contract request is issue 146. Source observations still need canonical assembly and endpoint evidence.
