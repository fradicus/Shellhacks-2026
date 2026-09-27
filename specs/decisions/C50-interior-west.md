# C50: Interior West rollout (WY, NV, UT, ID, MT)

## Authority

On 2026-09-27 the user told this Claude local session to keep filling sparse areas of the map as a continuous goal
(C47 was Oklahoma). Claude local adopts the technical-lead contract role for this change only; no existing ownership
changes. C48 and C49 were taken by other sessions, so this is C50/F50.

## Findings (origin/main `dfe5a2e`, national snapshot with every release applied)

- Located records: Wyoming 0 (no record at all), Nevada 3, Utah 7, Montana 11, Idaho 29. These are the emptiest
  contiguous states.
- The **WestConnect TPPL workbook** F45 pins (sha256 `ed926173…570b3a`, same artifact) has 24 Wyoming rows F45 excluded
  by scope: 22 Cheyenne Light Fuel and Power (115/230 kV lines and substations around Cheyenne, 2024–2028) and
  2 Tri-State (Archer–Stegall, Kinnan). Substation rows give "Cheyenne, WY" as Origin/Termination; their
  `ProjectName` names the facility.
- The **2026 WECC Annual Progress Reports** are public PDFs on wecc.org (no login): NV Energy (10 pages, ~25 Nevada
  projects naming substations/lines with in-service dates), PacifiCorp (15 pages; Gateway West/South/Central
  segments in WY/UT/ID and Utah projects) and Idaho Power (15 pages). F42 transcribed the *2025* PacifiCorp and Idaho
  Power reports for OR/ID only; F45 used none of them.
- Rejected: NorthernGrid's submittal xlsx files are blank templates; WestTEC layers are already imported (F42/F45);
  EIA-411's latest file is 2016. Idaho Power's Local Transmission Plan (~97 projects) is served by OATI with a
  certificate from a private root CA; it is deferred rather than fetched without TLS verification.

## Decision

1. **F50 (claude-local)** covers WY, NV, UT, ID and MT.
2. **Part 1: Wyoming TPPL rows.** F45's reader, endpoint parser and C33/C38 locator by import. Source
   `westconnect-tppl-2026-02-wy` cites the same artifact and hash; F45's source and counts are untouched. IDs
   `westconnect-tppl-2026-02-wy:<projectid>`. When neither Origin nor Termination names a facility, a substation
   row's `ProjectName` may name the site (the same F40 name parser). Generation interconnection rows whose only
   endpoint is a line stay unlocated.
3. **Part 2: 2026 WECC progress reports** (NV Energy, PacifiCorp, Idaho Power). Rows are transcribed into
   `data/interiorwest/transcriptions/*.json`, each with the page and a verbatim quote the build re-finds on that page.
   Only rows in WY, NV, UT, ID or MT; the state comes from the text or the owner's single-state territory. A project
   F42 or F45 already publishes (same owner and title, or the same owner's line between the same two facilities) is
   excluded with the reason. Dates keep the report's precision; nothing is inferred.
4. **Locations follow C33's tiers with C38's operator guard** against OpenStreetMap substations in the row's state.
   Every point stays `unreviewed`; no county-reference points.
5. **Publication:** fixed release `data/interiorwest/releases/active.json`, appended by F30's `load_snapshot` after
   SPP South under a separate `[FIX-F30]` claim.

No point quota: reported counts are the counts found.

## Undo

Delete `data/interiorwest/releases/active.json` (the hook becomes a no-op) or `data/interiorwest/`.
