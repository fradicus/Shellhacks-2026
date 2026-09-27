---
id: F41
name: Texas transmission project data
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/texas/, data/texas/, reports/texas/, tests/pipeline/test_f41_]
cut: never
---

# F41 Texas project research and map delivery

## Authority and launch

The user explicitly requested Texas work on 2026-09-26 while another agent handles the Southeast.
Assigned to this Codex local session only, separately from F38 New England, F39 Southeast and F40 Great Lakes.
Use the simplified evidence tiers in [C25](../../decisions/C25-main-demo-map.md). No second reviewer is required
for explicit official project coordinates after basic validation. Candidate locations remain labeled and unmatched.
This is a bounded first Texas checkpoint, not a statewide completeness promise or a background scheduler.
Original run gates are historical; STOP and main-red rules remain effective. No user budget/deadline was supplied.

## Plan

1. Inspect ERCOT's public Transmission Project and Information Tracking workbook and its access markings.
2. Extract a complete bounded sheet/cohort with native IDs, row locators, source hash/vintage, raw date precision,
   owner and lifecycle fields. Preserve unknowns, reconcile duplicates and report eligible/accepted/excluded rows.
3. Inspect official utility project pages and public PUCT filings for explicit site/endpoint geometry. Start with
   sources actually accessible in this session. ERCOT coverage must not be described as all Texas coverage.
4. Retain official points, bounded candidate matches, area-only and unlocated records separately. Asset inventories
   support location research only; they are not construction projects. Never manufacture geometry to fill the map.
5. Coordinate a fixed Texas publication input with F30 and evidence-tier support with F31/F19 through a contract
   claim. Research files do not activate automatically. Only the load Action writes Atlas.

## Requirements

Texas only; cross-border records preserve their evidence and require explicit identity deduplication with other
producers. No edits in another feature's owns/spec. Raw downloads stay outside the repository. Source manifests
include exact URL, content hash, retrieval time, publication vintage, rights/access observations and sheet/page.
Do not ingest restricted/CEII-marked content. A public download alone is not a license to redistribute the workbook.
Keep dates as stated, costs as stated, and planned/actual events separate. Use mission endpoint-center math.

## Validation

Run repository checks and deterministic extraction reconciliation. Check IDs, duplicate rows, dates and precision,
source locators, malformed geometry and publication tier counts. Independently confirmed is never assigned by the
producer. Live completion requires the accepted release, Action receipt, active RO read and visible selectable
Texas project in `/time` with matching evidence; a research checkpoint does not add `changes/F41.md`.

## Defaults

Use existing Python libraries and simple JSON artifacts. Prefer structured official reports; keep inaccessible
sources as documented gaps and continue accessible ones. No new service, credentials, automated geocoder or invented
point quota. First checkpoint ends with actual acquired/extracted/located/published counts and a concrete next task.
