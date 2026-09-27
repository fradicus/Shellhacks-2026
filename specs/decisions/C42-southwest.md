# C42: Southwest rollout (AZ, NM, CO, UT, NV)

## Authority

On 2026-09-27 the user told this Claude local session to cover the Four Corners states and Nevada with about
100–200 pins in total: as many as the data covers well, only a few in Nevada and Utah, "doesn't have to be that
good". Claude local adopts the technical-lead contract role for this change only; no existing ownership changes.

## Findings (origin/main `d8d048d`)

- The national snapshot has **0** records in AZ, NM, CO, UT or NV. WestConnect is catalogued only.
- WestConnect's public Transmission Plan Project List workbook ([TPPL](https://regplanning.westconnect.com/tppl.htm),
  `doc.westconnect.com` NID 21174, no login) has 389 sponsor-submitted projects with named origin and termination
  facilities, in-service year, development status and state: Arizona 119, Colorado 97, New Mexico 46, **none** in
  Utah or Nevada. SRP, NV Energy and PacifiCorp do not file in it.
- The WestTEC 10-year planned-projects layer (BPA-hosted, already used by F42) draws about a dozen planned lines in
  Nevada and Utah with source geometry and no dates. F42 imported only features touching WA/OR/ID/MT.

## Decision

1. **F45 (claude-local).** WestConnect TPPL rows whose state is Arizona, New Mexico or Colorado; other and
   multi-state rows are excluded with a reason. A numeric in-service year is a `planned_milestone` event at year
   precision; an `In-Service` status is an `in_service` event; `Withdrawn` maps to `cancelled`. Never a day or
   month the workbook does not state.
2. **Locations follow C33's tiers with C38's operator guard,** matched against OpenStreetMap substations in the
   row's state. The project's endpoints are the workbook's own Origin and Termination facilities (mission rule:
   mean of two located endpoints, one located endpoint is partial). Every point stays `unreviewed`.
3. **Nevada and Utah, a few:** WestTEC planned-project features F42 did not import whose terminal-vertex mean lies in
   Nevada or Utah, as the `official` tier. They have no dates, so they reach Overlaps only.
4. **Publication:** fixed release `data/southwest/releases/active.json`; F30's `load_snapshot` appends
   `("southwest", "southwest.publish")` after the Pacific Northwest under a separate `[FIX-F30]` claim.
5. Deferred, not rejected: WECC Annual Progress Report PDFs (NV Energy, PacifiCorp Utah rows), SRP and Arizona
   Corporation Commission ten-year plans. They need page-verified transcription.

## Undo

Delete `data/southwest/releases/active.json` (the hook becomes a no-op) or `data/southwest/`.
