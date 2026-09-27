# F42 Pacific Northwest: part 1 checkpoint

Policy: [C33](../../specs/decisions/C33-pacific-northwest.md). No location is independently reviewed; every pin is
labeled official source geometry, candidate, or name-only candidate. At the user's request (2026-09-27) there are
**no county dots** (a named county is kept only as `counties` GEOIDs; the project stays unlocated), and the release is
limited to work in **2025-2035**: completed, cancelled and pre-2024 waiver-list rows, and in-service dates outside the window, are
excluded with that reason in `data/pnw/dispositions.json`.

## Totals (release `pacific-northwest-2026-09-1`)

323 projects. **176 pins** (53 official, 115 candidate, 8 name-only) at 146 distinct coordinates. 147 unlocated
(searchable, with the reason). 0 independently confirmed. A project that touches two states is counted in
each state row.

| State | Projects | Official | Candidate | Name-only | Unlocated |
|---|---|---|---|---|---|
| WA | 100 | 16 | 41 | 4 | 39 |
| OR | 118 | 34 | 52 | 4 | 28 |
| ID | 39 | 12 | 17 | 0 | 10 |
| MT | 15 | 4 | 7 | 0 | 4 |
| no state in source | 67 | 0 | 0 | 0 | 67 |

Pins by in-service year: 2025: 5, 2026: 8, 2027: 15, 2028: 9, 2029: 5, 2030: 5, 2031: 6, 2032: 4, 2033: 4,
2035: 9; 106 have no stated date (current plans and 2024-2026 NEPA decisions).

## Sources (56 national source records, one per file)

| Source | Projects kept | How it is read |
|---|---|---|
| BPA GERP line/substation layers (ArcGIS) | 26 | Official geometry; line center = mean of terminal vertices |
| WestTEC 10-year planned / identified layers (hosted by BPA) | 31 | Official geometry; interstate lines whose midpoint leaves WA/OR/ID/MT stay unpinned |
| BPA categorical exclusion memos, 2024-2026 (`pnw/cx.py`) | 36 | Parsed header: title, BPA project no., `Location:` counties, CX classes B4.6/B4.11/B4.12/B4.13 only |
| NorthernGrid 2026-2027 and 2024-2025 study scopes | 63 | Transcribed rows |
| BPA 2025 and 2023 Transmission Plans, GERP Project Update, BPA 2025 APR | 87 | Transcribed rows |
| WECC 2025 APRs (AVA, CHPD, GCPD, IPC, PGE, PSE, PacifiCorp) and waiver-list summary | 58 | Transcribed rows |
| Snohomish PUD and Idaho Power project pages | 22 | Transcribed rows |

Transcribed rows live in `data/pnw/transcriptions/`. The build re-extracts each pinned file's text (pdfplumber) and
fails if a row's quote, name or facility names are not on its cited page. Facility geometry for candidates: OSM
named substations (ODbL), BPA's substation GIS, and HIFLD Open "Electric Substations" via a February 2021 copy
hosted on ArcGIS Online by user SGT_Peterson (item `45505e134cb14bbda4e939117459eb6b`; HIFLD Open's own service is
gone). Census TIGERweb county polygons assign state/county. All URLs, hashes and retrieval times are in
`data/pnw/sources.json` and `data/pnw/references.json`.

## Matching rules added beyond F40

- **Name-only (C33):** an exact normalized name held by one facility in the state places a pin without
  operator/voltage corroboration, unless the facility contradicts the source: tagged voltages that miss every
  voltage the source names, or a county outside the source's counties (or a county PUD's own county).
- **Owner territory:** single-state utilities (PGE, PSE, PUDs, Seattle City Light, NorthWestern) take their state;
  multi-state owners with no stated state (Idaho Power, Avista, BPA, PacifiCorp) search their territory and then need
  operator or voltage corroboration.
- **Identity:** BPA bundle numbers, the same owner's line between the same two real facilities, and the same owner
  with the same exact title are one project; an ownerless WestTEC line joins the one owned project with its endpoints.

## Spot check (seed 42, 10 pins per state; MT has 11)

Checked each pin's facility and county against the source text. No wrong location was found in the 40 samples
(e.g. Heyburn-Minico → Minidoka County as the CX memo states; Tillamook, McNary-Roundup, Chief Joseph match their
memos' counties; Snow Goose and La Pine corroborated by voltage/operator). Before sampling, a review of every
name-only pin caught two wrong matches (Grant PUD's new Mountain View → a Mason County substation; the new 500 kV
Bonanza → a 69 kV Bonanza) and added the contradiction guard above. Known remaining issue: sources that spell a
project differently are not merged (NorthernGrid "SHUL install series caps" vs GERP P04364; "Harborton-St Mary" vs
"Harborton-St Marys"), so a few projects appear twice.

## Gaps

- Utility local transmission plans on OATI OASIS (PacifiCorp, PGE, Idaho Power, Avista, NorthWestern, PSE) fail TLS
  verification (private OATI root CA). Not bypassed. A browser download of those PDFs would be the largest next batch.
- New substations not yet in any facility dataset (Apex, Full Circle, Mayfield, Crosswind, ...) stay unlocated.
- Montana is thin: NorthWestern's APR lists only generation interconnections.
- Not live: F30's owner adds `("pnw", "pnw.publish")` to `load_snapshot`'s fixed producer list.

## Reproduce

From `pipeline/`: `uv run python -m greatlakes.osm fetch --cache <osm> WA OR ID MT`,
`uv run python -m pnw.shared osm --cache <osm>`, `uv run python -m pnw.build fetch --cache <c>`,
`uv run python -m pnw.build build --cache <c> [--check]`, `uv run python -m pnw.publish [--check]`.
