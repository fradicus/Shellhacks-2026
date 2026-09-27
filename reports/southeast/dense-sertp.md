# Dense Southeast: SERTP expansion plans (C40)

Source: the Southeastern Regional Transmission Planning (SERTP) public [archive](https://www.southeasternrtp.com/archive.cshtml).
Each project block gives In-Service Year, Project Name, Description and Supporting Statement under a Balancing
Authority Area (BAA) heading. There is no state, owner or status column. Retrieved 2026-09-27; publication dates are
not stated, so `publication_date` and event `source_date` stay null.

| Edition | sha256 | CEII lines / markings | Use | Rows | Accepted | Duplicate (history) | Excluded |
|---|---|---|---|---:|---:|---:|---:|
| 2025 Preliminary Expansion Plan Report (Non-CEII) | `462f9f3d…` | 0 / 0, pass | current | 424 | 331 | 93 (legacy GPC) | 0 |
| 2024 Regional Transmission Plan (final) | `fa960646…` | 5 / 0, pass | history | 364 | 0 | 78 (11 to legacy GPC) | 286 |
| 2024 Preliminary Expansion Plan Report (Non-CEII) | `4ea25c3d…` | 0 / 0, pass | history | 301 | 0 | 50 (4 to legacy GPC) | 251 |
| 2023 Regional Transmission Plan (final) | `32350b2b…` | 5 / 0, pass | history | 244 | 0 | 35 (3 to legacy GPC) | 209 |
| 2025 Regional Transmission Plan (final) | `9183e3ff…` | 319 / 194, **fail** (`TRANSMISSION PROJECTS (CEII)` headings) | not used | — | | | |
| 2022 / 2021 finals (Non-CEII) | `bf4fbdfb…` / `679d4f16…` | 5 / 0, pass | not used | — | | | |
| 2026 preliminary | not downloaded | D15 exclusion stands | not used | — | | | |

The full hashes and the check rule are in `specs/decisions/F39-sertp-editions.md` and each source's `notes`. The build
re-runs the check and refuses to build if it finds a CEII marking.

## Results

331 projects are accepted; 93 more rows are duplicates of legacy Georgia Power projects (see below). All 331 are
`planned`: listed with a future In-Service Year, which is year precision. Every project has at least the 2025
`planned_milestone` event. 69 link to an older edition, and 35 of those record a changed year. Located
records are C40 `candidate` (OSM exact name plus operator or voltage) or `candidate_unique_name`, and all are
`unreviewed`. There are 0 official points and 0 verified.

| State | Projects | Candidate | Name-only | Not in service | Dated |
|---|---:|---:|---:|---:|---:|
| GA | 45 | 45 | 0 | 45 | 45 |
| AL | 30 | 29 | 1 | 30 | 30 |
| NC | 28 | 28 | 0 | 28 | 28 |
| SC | 8 | 8 | 0 | 8 | 8 |
| TN | 5 | 5 | 0 | 5 | 5 |
| KY | 2 | 2 | 0 | 2 | 2 |
| FL, MS | 1 each | 1 each | 0 | 1 each | 1 each |
| state unknown (unlocated) | 214 | — | — | 214 | 214 |
| **Total** | **331** | **116** | **1** | 331 | 331 |

The 117 located records fall on 87 distinct points. By BAA: Southern 74 of 200 located, SOCO 1/4, Duke Carolinas
24/65, Duke Progress East 9/24, Duke Progress West 0/1, TVA 7/25, LG&E/KU 2/8, AECI 0/4.

**Unlocated (214).** Counts from `summary.json`:

| Reason | Rows |
|---|---:|
| `no_facility` | 116 |
| `ambiguous_in_footprint`, alone or with another endpoint status | 30 |
| `program_area_or_multi_facility` | 28 |
| `no_named_facility` | 17 |
| `no_facility` + `voltage_conflict` | 9 |
| `no_facility` + `not_a_facility` | 5 |
| `no_facility` + `operator_conflict` | 2 |
| `multi_terminal_line` | 4 |
| `operator_conflict` | 3 |

**Rules added for a multi-state footprint.** A name must be unique across the whole BAA footprint. A name-only match
whose OSM voltage excludes the project's voltage is rejected: without that rule Georgia's Decatur–Scottdale 115 kV
matched a 161 kV "Decatur" in Alabama, Atkinson–Northside Drive matched Mississippi, and Duke Carolinas' Lee Steam
(SC) matched an NC 115 kV "Lee Steam". A parsed name must start a segment of the project name ("Yates - Line Creek"
must not yield "Creek").

**Legacy Georgia Power duplicates (93 rows).** A Southern/SOCO row is a `duplicate` of a legacy `legacy:GPC:*` project
only when exactly one legacy project names the same place, and no other SERTP row claims that project. For a line,
the same place means the same two endpoints after `facility_key` normalization, in either order. For a site, it
means the same site name and the same kV when both rows state one. The disposition carries the legacy `_id` and the
reason "same two named endpoints as <name> (legacy GPC register)". 82 lines and 11 sites matched. Older-edition rows
linked to those rows now point at the legacy ID too. Their SERTP year events are not attached, because legacy
records are not edited.

29 rows stayed new with a `location_candidate.legacy_overlap` note. In 15, two legacy projects name the same place
(for example Gordon–Sandersville #1, and Ray Place Rd–Washington). In 14, two SERTP rows claim one legacy project
(for example the two Adamsville–Buzzard Roost rows, and Robins Spring bus vs capacitor bank). Following the rule
literally gives one doubtful site match: "East Watkinsville 230 kV series reactors, replacement" is matched to
"East Watkinsville 230 kV station modification". They may be two work items at one station.

## Spot check (12 random located, seed 2026, then 12 more at seed 99 after the fix)

Run on the 424-project build before the legacy duplicate step. Some sampled Georgia rows (such as Kraft and
Offerman–Thalmann) are now legacy duplicates. The matching rules did not change.

I checked each matched facility against the project name, description and state. First sample: 1 error.
"ROCKVILLE - TIGER CREEK -WARTHEN 500 KV" is a three-terminal line, but the one-sided dash had hidden the third
terminal, so it was placed partially at Tiger Creek. A one-sided dash now separates terminals, and both such rows
are unlocated (`multi_terminal_line`). The other 11 were consistent: Offerman–Thalmann, Fort Valley, Fortson, Durham,
Calvert, Wansley, Radnor ("Nashville Area"), Kraft, South Bainbridge, Meldrim and Rockingham. Second sample: 0 errors
(Villa Rica, South Coweta, Big Shanty, Bradley TN, Bay Creek, Cartersville Primary, Dresden, Pineville KY, Tiger Tie
SC, Dawson Crossing–Nelson, East Moultrie, Opp–South Enterprise).

## Known gaps

- **History is thin.** The 2025 report renamed most projects ("X 115KV REBUILD" became "X 115 KV TRANSMISSION LINE,
  REBUILD"). Only an exact name link, or the name without its ", ACTION" phrase, is used, so 746 older rows are
  excluded. A dropout cannot be told apart from a rename, and neither means built. No in-service event is claimed.
- **Remaining overlap.** The 29 kept Southern rows above may still overlap the legacy register. The Duke map batch
  may overlap the Duke sections in the same way; I did not measure it.
- AECI's 4 rows (Crocker South–Lebanon and others) are probably Missouri lines. Only Arkansas OSM is searched, so they
  stay unlocated with `states: []`. The VA and AR footprints produced no located project.
- Owner is set only from a "GTC:", "MEAG:", "DU:" or "PS:" tag (45 accepted rows). "SAV:", "GRID:" and "CC -" are area or
  program tags.

Reproduce from `pipeline/`: `uv run python -m southeast.sertp fetch --cache <dir>`, then run
`build --cache <dir> [--check]`.
