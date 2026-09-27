# F38 New England checkpoint 1

## Outcome

Prepared 300 source-backed project/component research records and a [readable bullet list](new-england-bullets.md).
**Confirmed new locations: 0. Atlas activations: 0. New verified map points: 0.**
The user target remains 250–500 verified project points. This source audit is the first checkpoint toward it.

The bounded cohort contains all 46 June-2026 planned/proposed/construction records and 254 explicitly historical
in-service records. State distribution: MA 101, CT 92, ME 56, NH 18, RI 18, VT 15. A project/component ID is not a
distinct physical site. ID priority does not assert chronology. The source reports status as of June, not now.

## Evidence

- Baseline: `origin/main` revision `84de54ee2209507f1816124a13b80dc18fb8516f`.
- Public workbook: `https://www.iso-ne.com/static-assets/documents/100037/final_rsp_project_list_jun_2026.xlsx`.
- SHA-256: `adfe05f5c0f24e260acca3b10c692785b4298a2067fa2e79efcf1d079953190d`.
- Downloaded again during the run recorded in `data/expansion/manifests/new-england-run.json`; original F30 retrieval
  timestamps remain original. The identical bytes do not establish that this is the publisher's newest artifact.
- Replayed all 1,024 source rows against the F30 snapshot with exact equality, including raw evidence fields.
- Reconciliation: 300 selected; 724 deferred, comprising 389 other in-service and 335 cancelled records. Every native
  ID has one disposition; no row is silently dropped and no deferred row is called a rejected project.
- Cohort JSON includes exact original F30 records, source row locators and a hash of each complete project record.
- [Independent workbook review](new-england-independent-review.md) reports separate source verification. It cannot
  approve coordinates that the source does not contain.

## Plan for verified points

1. Complete [contract request #136](https://github.com/fradicus/Shellhacks-2026/issues/136) for additive evidence/review and national-loader/API/map integration through its owner. Keep the same ISO-NE
   IDs and update evidence through their owner; do not insert 300 duplicate national projects.
2. Inspect latest and prior comparable public RSP/asset-condition vintages. Review rights, markings and cross-list IDs
   before acquisition. Preserve the June baseline and any later status discrepancies as separate observations.
3. Pilot one project-linked site from a public siting document plus supported official geometry. Old Town (`iso-ne:1618`)
   has a promising regulator docket, but the existing substation and adjacent replacement must be distinguished.
4. Investigate facility-ID groups across this cohort. National Grid's official GIS metadata is a promising candidate
   source; blank license metadata and facility meaning still need review. Do not auto-approve same-name joins.
5. Independently inspect every proposed location. Count complete/partial endpoints, distinct sites, historical projects,
   remaining unknowns and source restrictions separately. Research another eligible source if yield is too low.
6. Publish accepted batches through the existing Action, then verify the active dataset and evidence on `/time` and
   `/explore`. No completed geographic milestone until that journey works.

## Resume / replay

From `pipeline/`, use the existing approved `national.fetch.refresh` registry entry `iso-ne-rsp-2026-06` to retrieve
its pinned workbook into a temporary directory outside the checkout. Then:

```bash
uv run python -m expansion.new_england --source /path/to/final_rsp_project_list_jun_2026.xlsx --check
```

Omit `--check` to regenerate only F38-owned research outputs. Hash mismatch or any F30 replay difference stops output.
The command has no network, database or map-publication side effects. Raw workbook bytes are not committed.
The first checkpoint makes no throughput estimate for location verification: zero locations have been reviewed.
