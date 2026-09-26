# Plan E verification results

Status: **PASS** — 505 local assertions. Run: 2026-09-26T08:22:06.565610+00:00.

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

## Three.js date-height arithmetic

Evaluated z_visual = 1000 × calendar-day offset / 365.25 with scene epoch 2023-01-01 on all ten sample projects. These are exaggerated display units, not actual elevation. All six vertical separations recover their exact day gaps. Unknown exact date returns no height; a one-day hypothetical move produces a one-day visual offset.

| Project | Exact date | Day offset | Display height |
|---|---|---:|---:|
| DESC_1 | 2024-12-31 | 730 | 1998.631075 |
| DESC_2 | 2024-12-31 | 730 | 1998.631075 |
| DESC_3 | 2025-12-31 | 1095 | 2997.946612 |
| DESC_4 | 2023-12-31 | 364 | 996.577687 |
| DESC_5 | 2025-06-01 | 882 | 2414.784394 |
| GPC_1 | 2033-06-01 | 3804 | 10414.784394 |
| GPC_2 | 2026-06-01 | 1247 | 3414.099932 |
| GPC_3 | 2027-06-01 | 1612 | 4413.415469 |
| GPC_4 | 2025-05-01 | 851 | 2329.911020 |
| GPC_5 | 2025-06-01 | 882 | 2414.784394 |

Rendered positions, frame rate, latency and visual accessibility remain untested because no application is built.

## Company package

Parsed **41 YAML/frontmatter files** with Ruby Psych safe_load: company + sidecar, 8 agents, 13 skills, 1 project and 17 tasks. All **45 agent-skill references** resolve. Required fields, reporting graph, task owners/projects, acyclic prerequisite graph, skill procedure sections and env input declarations pass local structural checks.

Format checked against the official Agent Companies reference at companies commit `514503bf4f0ca88ebf16d5dc648e085d587f268f`, the normative specification and Paperclip vendor/CLI documentation. No live IDs or secret values are supplied. This is a local structural checker, not the Paperclip importer or an exhaustive schema implementation.

## Sources and preservation

Direct HTTP URL retrieval: **32/33 passed**. See [source-checks.json](source-checks.json) for statuses, redirects and retrieval timestamps. The remaining PJM page resolved through web.run; its separate evidence is in [source-checks-web.json](source-checks-web.json). All 33 cited URLs were retrieved by one of these methods. The direct checker still reports the environment's PJM DNS failure honestly.

All **45 baseline files** outside Plan E remain byte-identical. Baseline excludes Plan D before reading/hashing. The pre-existing docs/spec-driven-development.md is also unchanged against the revision baseline. Additional root AGENTS/CLAUDE/specs work appeared concurrently and was not edited here; its status is recorded in results.json. This revision writes only within Plan E. Plan D contents were not read. No application or cloud resource is created by these checks; prior commits remain intact.

## Not verified

- Live Paperclip import/dry-run, adapter/model execution, runtime skill installation and credentials.
- Gemini evaluation on the new corpus, Atlas provisioning/egress, actual web/API behavior and deployed critical path.
- Independent accuracy of sample coordinates, full new-source classifications/owner mappings, or three non-sample pairs.
- Domain availability/qualifying registration, current event eligibility and submission.
- Three.js rendering, GPU performance, frame-rate/latency targets, coverage UI and national/regional ingestion.
- URL resolution establishes retrieval only; it does not establish page permissions or substantive completeness.
