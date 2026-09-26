# Plan E verification results

Status: **PASS** — 461 local assertions. Run: 2026-09-26T07:54:13.787929+00:00.

## Sponsor workbook calculations

Read the original XLSX directly. Recomputed every center, all 25 cross-utility distances and mixed text/Excel-serial dates. All six pair IDs, labels, rounded distances, exact gaps and project neighbor counts match; all 19 remaining pairs are excluded.

| ID | Pair | Computed miles | Workbook miles | Computed gap | Workbook gap | Priority | Impact |
|---|---|---:|---:|---:|---:|---:|---|
| OVL_1 | DESC_2 / GPC_1 | 4.09 | 4.09 | 3074 | 3074 | 3 | null |
| OVL_2 | DESC_3 / GPC_2 | 5.65 | 5.65 | 152 | 152 | 1 | null |
| OVL_3 | DESC_3 / GPC_3 | 7.55 | 7.55 | 517 | 517 | 2 | null |
| OVL_4 | DESC_1 / GPC_1 | 8.01 | 8.01 | 3074 | 3074 | 4 | null |
| OVL_5 | DESC_5 / GPC_2 | 14.34 | 14.34 | 365 | 365 | 5 | null |
| OVL_6 | DESC_5 / GPC_3 | 14.81 | 14.81 | 730 | 730 | 6 | null |

Priority: OVL_2, OVL_3, OVL_1, OVL_4, OVL_5, OVL_6.

Additional formula/edge checks: **19/19 passed**. Strict boundary, two/one/no endpoint, null gap, leap day, symmetry, band boundary, unknown-gap ordering, stable tie and impact checks are recorded in [results.json](results.json).

None of the six sample pairs has two in-service dates on or after September 26, 2026. This is a dated regression fixture, not evidence of six current future opportunities. All sample savings estimates are null: mobilization inputs are absent. Synthetic arithmetic checks only: 2 × $1,000 − $500 = $1,500; 0 × $1,000 − $500 = −$500. These are not observed savings.

Hypothetical scenario check: changing DESC_3 from its published December 31, 2025 to an assumed January 1, 2026 changes the gap to GPC_2 from 152 to 151 days. The fixture date stays unchanged. No construction feasibility is inferred.

## Company package

Parsed **41 YAML/frontmatter files** with Ruby Psych safe_load: company + sidecar, 8 agents, 13 skills, 1 project and 17 tasks. All **45 agent-skill references** resolve. Required fields, reporting graph, task owners/projects, acyclic prerequisite graph, skill procedure sections and env input declarations pass local structural checks.

Format checked against the official Agent Companies reference at companies commit `514503bf4f0ca88ebf16d5dc648e085d587f268f`, the normative specification and Paperclip vendor/CLI documentation. No live IDs or secret values are supplied. This is a local structural checker, not the Paperclip importer or an exhaustive schema implementation.

## Sources and preservation

URL retrieval: **28/28 passed**. See [source-checks.json](source-checks.json) for statuses, redirects and retrieval timestamps.

All **45 baseline files** outside Plan E remain byte-identical. Baseline excludes Plan D before reading/hashing. Git status reports changes only under Plan E. Plan D contents were not read. This agent made no commit and created no application or cloud resource. Another repository update committed a Plan E draft during authoring; that draft is preserved and remaining changes are uncommitted.

## Not verified

- Live Paperclip import/dry-run, adapter/model execution, runtime skill installation and credentials.
- Gemini evaluation on the new corpus, Atlas provisioning/egress, actual web/API behavior and deployed critical path.
- Independent accuracy of sample coordinates, full new-source classifications/owner mappings, or three non-sample pairs.
- Domain availability/qualifying registration, current event eligibility and submission.
- URL resolution establishes retrieval only; it does not establish page permissions or substantive completeness.
