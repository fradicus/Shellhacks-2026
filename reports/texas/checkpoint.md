# Texas checkpoint 1: ERCOT source inspection

Scope: first F41 research checkpoint; no publication or map-point claim.
Owner: this Codex local session. Southeast F39 and Great Lakes F40 remain separate.

## Acquired source

[ERCOT Market Reports](https://www.ercot.com/gridinfo/sysplan) links the public July TPIT workbook,
published July 17, 2026. The project-sheet heading says as of July 13, 2026.
[Exact workbook](https://www.ercot.com/files/docs/2022/03/02/ERCOT-July-Ad-Hoc-TPIT-No-Cost-071326-UPDATE.xlsx).
The URL directory year is not the source vintage. Raw workbook is outside the repository.

| Sheet | Rows with ERCOT ID | Unique IDs within sheet |
|---|---:|---:|
| FutureTPIT071326NoCost | 1429 | 1424 |
| PlannedTPIT071326NoCost | 358 | 358 |
| CompletedTPIT071326NoCost | 262 | 262 |
| CancelledTPIT071326NoCost | 78 | 78 |

Total observations: 2127. These are not necessarily unique projects, eligible transmission projects or map points.
Future contains repeated IDs; phase identifiers must be inspected before any canonical deduplication.
The additional RTP sheet is a separate planning list with TPIT links and must not be blindly appended.

## Findings

- Project sheets provide IDs, names, descriptions, named terminals, owner codes, voltage, counties and milestones.
  They provide no coordinate columns. Geographic scope can support research, not a precise point.
- Date headers explicitly say Month/Yr even where underlying Excel values carry days. Preserve raw value and number
  format; use month precision unless separate evidence establishes an exact day. Never infer day precision from storage.
- Sheet cohort and row status disagree. Completed contains rows marked Planned; Cancelled contains Planned and
  Under Construction. Preserve both as separate observations and flag conflict rather than asserting active work.
- Workbook text scan found `CONFIDENTIAL Total Project Estimated Cost` in TSPResponsibility!A17, a field-definition
  sheet. The 33-column public project sheets omit this field. No project costs, contacts, bus lists or workbook copy
  are committed. Public access does not grant blanket redistribution rights. Any later adapter must review exact
  content and quarantine restricted fields/material rather than treating the filename as permission.
- Publication and eligible project classification remain pending. No official, candidate or reviewed coordinates
  have been extracted; loaded/visible Texas points from this checkpoint: zero.

## Next bounded task

Extract only public project identity, terminal, county, status and raw milestone fields into a research cohort,
retaining row/phase identity and reconciling repeats. Classify transmission versus distribution-only work before
publication. Then obtain explicit official endpoint/site GIS or apply C25's exact-name-plus-corroboration candidate
rule. Oncor's project pages and public PUCT project filings are starting sources; an Oncor page returned 403 to the
web reader in this session, so it is a recorded access gap, not acquired evidence. Never infer coordinates from
statements such as miles north of a town. Coordinate Texas activation with F30 and tier labels with F31/F19.
