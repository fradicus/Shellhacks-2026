# C51: California municipal utilities from WECC progress reports

## Authority

On 2026-09-27 the user told this Claude local session to keep filling sparse areas of the map as a continuous goal and
named California as sparse. Claude local adopts the technical-lead contract role for this change only; no existing
ownership changes.

## Findings (origin/main `04c59d2`)

- California has 146 located records, all from F44's CAISO Transmission Development Forum workbooks: 360 projects,
  214 unlocated. CAISO's forum covers only its participating transmission owners (PG&E, SCE, SDG&E and others).
- The utilities that plan and own transmission outside CAISO, LADWP (about 40% of Los Angeles's load path plus
  Intermountain in Utah), IID, SMUD, TANC, TID and MID, have no record. Each filed a 2026 WECC Annual Progress Report,
  public on wecc.org (plain HTTPS, no login): `https://www.wecc.org/sites/default/files/documents/progress_report/2026/<ORG>%202026%20APR.pdf`.
- F50 (C50) already reads WECC progress reports: page-cited transcriptions re-verified against the pinned PDF, C33/C38
  locations, territory placement only with corroboration. Its reader takes a rollout's own reports and territory.
- PG&E, SCE and SDG&E also file reports, but their projects are the CAISO forum's; they are left to F44.

## Decision

1. **F51 (claude-local)** transcribes the six reports into `data/camunis/transcriptions/`, one record per
   transmission project, through `interiorwest.apr` by import. Sources `wecc-apr-2026-<org>`; IDs
   `<source>:<native id>`.
2. Rows in CA, and LADWP's rows in UT or NV, are in scope. A row F44, F45 or F50 already publishes is excluded with
   the reason. Generation-only and non-transmission rows are excluded.
3. A row whose text names no place is placed only by an operator- or voltage-corroborated OSM substation in the
   owner's territory (CA; LADWP also UT and NV) and takes that facility's state. Every point stays `unreviewed`.
4. **Publication:** fixed release `data/camunis/releases/active.json`, appended by F30's `load_snapshot` after the
   Interior West under a separate `[FIX-F30]` claim.

No point quota: reported counts are the counts found.

## Undo

Delete `data/camunis/releases/active.json` (the hook becomes a no-op) or `data/camunis/`.
