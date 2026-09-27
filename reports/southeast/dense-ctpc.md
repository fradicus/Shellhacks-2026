# Dense Southeast: CTPC Collaborative Transmission Plans (C45)

Source: the Carolinas Transmission Planning Collaborative (formerly NCTPC) reference library,
<https://carolinastpc.org/reference/>. Public PDFs, no login; the plans are not the CEII-marked study reports.
Each plan lists Duke Energy Carolinas (DEC) and Duke Energy Progress (DEP) major projects with ID, name, owner,
status, projected in-service date and cost. Parsed with pdfplumber table extraction (wrapped names are one cell).

| Edition (vintage) | Report date | sha256 (first 12) | Rows | Accepted |
|---|---|---|---|---|
| 2016-2026 NCTPC Report | 2017-01-13 | 1419a962b645 | 10 | 0 |
| 2017-2027 NCTPC Report | 2018-01-16 | a749d8007c89 | 17 | 1 |
| 2018-2028 NCTPC Report | 2019-01-17 | e21266021c1b | 21 | 2 |
| 2019-2029 NCTPC Report | 2020-01-22 | b4747b87846d | 16 | 1 |
| 2020-2030 NCTPC Report | 2021-01-15 | 9a421f647b14 | 18 | 4 |
| 2021-2031 NCTPC Report | 2022-01-24 | 7fb629a97cf8 | 16 | 1 |
| 2022 NCTPC Report | 2023-02-21 | 6ac092f6551a | 38 | 1 |
| 2023 NCTPC Plan | 2024-02-22 | 802d0852e4a2 | 73 | 3 |
| 2024 CTPC Plan | 2025-02-28 | 003e49adfc3f | 120 | 0 |
| 2025 Mid-Year Update to the 2024 Plan | 2025-07-24 | 49f46623db18 | 120 | 17 |
| 2025 CTPC Plan | 2026-04-16 | 9374c5f9565c | 122 | 4 |
| 2025 Plan Mid-Year Update (newest) | 2026-08-13 | 1f16698d87d4 | 116 | 116 |

Full hashes, URLs and retrieval times are in `data/southeast/dense/ctpc/sources.json`. All 689 listing rows have a
disposition: 150 accepted, 538 excluded (older listings of a newer project, or not in service and dropped), 1 duplicate.

**Rules.** The newest edition (Aug 2026 mid-year update) gives current projects. An older edition adds a project only
if it reports it In-Service and no newer edition lists it. Each changed projected date is a `planned_milestone`
(printed day precision; the plans say ±6 months); an In-Service row is an `in_service` event dated only by the date
printed there (a newer edition's date wins). Events: 249 planned milestones, 51 in service.
IDs are stable within a scheme: NCTPC reference numbers ("0043") through the 2023 plan, owner IDs ("W200126") from
2024. There is no crosswalk, so the schemes are never linked; an NCTPC in-service project with exactly the same name
as an owner-ID project would be excluded as a likely duplicate (no row triggered it). A listing whose name
shares no word with the newest name for its ID is not linked: E220378 appears on the Asheboro–Siler City row in the
2025 mid-year update but is Durham–RTP everywhere else; 0043 is unnamed in 2017.

**Locations.** C45 OSM candidates over NC+SC substations combined; `states` come from the matched facility.
Operator keys DEC → DUKE, DEP → DUKE/PROGRESS. Added guards: a DEC match to a Progress-operated facility (or DEP to
"Duke Energy Carolinas") is an operator conflict; a name-only match whose OSM voltages exclude the project's voltage
is a voltage conflict. VEPCO/SCEG terminals match only a facility operated by Dominion (Everetts matched).

| State | Projects | Located (candidate / name-only) | Not in service | Dated |
|---|---|---|---|---|
| NC (37) | 41 | 41 (40 / 1) | 21 | 40 |
| SC (45) | 8 | 8 (8 / 0) | 4 | 7 |
| Unlocated, state unknown | 101 | 0 | 69 | 96 |
| **Total** | **150** | **49** (40 distinct points; 25 partial lines) | 94 | 143 |

Unlocated reasons: no OSM facility of that exact name 55 (+4 with a tap endpoint), no named facility 20
(RAS/program rows, "Kennedy 100 kV Line"), multi-facility names 9, ambiguous 5, voltage conflict 3, operator
conflict 1, multi-terminal 2, other 2. Owners: 95 DEC, 55 DEP; DEC is under-located because OSM names DEC stations
"X Tie"/"X Ret" while line names give bare terminals ("Rural Hall – Shattalon"). No "Tie" is added to bare names:
DEP's Newport would otherwise match DEC's Newport Tie in SC.

## Spot check (12 random located records, seed 39)

E220071, E220084, E230041, 0039, E210150, E220082, E240038, W200170, 0037, W240278, E220378, E210081: name, owner,
status and date match the PDF rows; each point is at a substation with the named place (Fayetteville, Erwin,
Richmond 500 kV near Rockingham, Asheboro, Havelock, Cape Fear/Moncure–West End, H.F. Lee/Goldsboro, Lakewood
Charlotte, Cane River/Yancey Co., Central SC, Durham). Errors: 0 in the final sample. An earlier sample found
Wateree matched to a 230 kV "Wateree Substation" near Eastover (Dominion's plant) for DEC's 100 kV Great Falls–Wateree
line, and DEC's Durham–Ashe St matched to DEP's Durham 500 kV. Both led to the guards above, which dropped 5 endpoints (Wateree ×2, Sumter, Wake by voltage;
Durham by operator).

## Known gaps

- Pre-2016 plans, NCTPC mid-year updates, the plans' own comparison appendices (prior-plan values) and the Appendix D
  narratives are not read. Projects in service before 2024 whose last listing was not In-Service are not recovered.
- 2016 shows planned rows only. Removed/Deferred rows keep `cancelled`/`unknown` with no cancellation event.
- Duke map overlap (not merged): Craggy–Enka, Cape Fear–West End, Erwin–Fayetteville, Fayetteville–Fayetteville DuPont,
  Robinson Plant–Rockingham, Weatherspoon–Marion, Clayton Industrial–Selma, Rocky Mount–Battleboro,
  Lilesville–Oakboro, Sevier, Clinton, Newberry, Pinewood and Sutton–Castle Hayne (Wilmington NE) likely appear in
  both. Lilesville–Oakboro is listed twice in CTPC itself (E230124 DEP, W230323 DEC).

Reproduce from `pipeline/`: `uv run python -m southeast.ctpc fetch --cache <dir>` then `build --cache <dir> [--check]`.
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
