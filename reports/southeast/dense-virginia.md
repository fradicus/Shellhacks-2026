# Dense Southeast: Virginia (Dominion power-line projects + Virginia SCC case list, C40)

## Sources

| Source | URL | sha256 (retrieved 2026-09-27) | Vintage | Access |
|---|---|---|---|---|
| Dominion Energy power line projects (`document.projectListings` inline JSON, 126 rows, VA/NC/SC) + 118 project pages | https://www.dominionenergy.com/about/delivering-energy/electric-projects/power-line-projects | `6db19db5…aaaa1169` | undated live page | public, no login, no CEII banner |
| Virginia SCC transmission line projects (108 case rows, 5 regions) | https://www.scc.virginia.gov/consumers/public-utility/electricity-faqs/transmission-line-projects/ | `b79dd81c…c64504` | undated live page | public, no login |
| OSM `power=substation` for VA, NC, SC (Overpass) | overpass-api.de | per cache manifest | 2026-09-27 | ODbL |

PJM (pjm.com) is unreachable from this machine, so it was skipped. Neither source publishes coordinates, so no point is
`official`. Every point is an OSM name candidate: `candidate` when an operator or voltage corroborates it, or
`candidate_unique_name` when the name is the only match. Both are `unreviewed`.

## Counts

| State | Source | Projects | Located (cand / unique-name) | Not in service | With events | With a schedule date |
|---|---|---|---|---|---|---|
| VA (51) | Dominion | 107 | 41 (20 / 21) | 106 | 73 | 51 |
| VA (51) | SCC | 44 | 14 (13 / 1) | 44 | 44 | 0 |
| NC (37) | Dominion | 6 | 2 (1 / 1) | 6 | 3 | 2 |
| SC (45) | Dominion | 11 | 4 (2 / 2) | 11 | 2 | 2 |
| **Total** | | **166** (2 listed in both VA and NC) | **60** (35 / 25), 54 distinct points | 165 | | |

- Dominion list: 126 rows became 122 projects, one per project page. There are 4 duplicate rows. Earleys-Tunis-Suffolk
  and Tunis to Boykins are listed under both VA and NC, so each project keeps both states. "Vint Hill to Devlin" links
  the Gainesville-Wheeler page, which covers both projects jointly. "Church Creek" (SC) repeats the page titled "Church
  Creek - Charleston", which is filed under the NC region. When a repeated row has a different title, its region is
  not added to the project's states. `ProjectId` does not identify a project: CR01, CR02 and DC01 each label two
  different projects, and some IDs are blank.
- SCC list: 108 cases break down as follows.
  - 44 are their own projects.
  - 50 are duplicates of the Dominion project whose page cites the case. Two cases are cited by more than one page and
    go to the page that cites the fewest cases:
    - Fredericksburg-Possum Point's page cites PUR-2021-00291 in a copied paragraph, so that case goes to Cannon
      Branch-Winters Branch.
    - Carmel Church and Ruther Glen both cite their joint case PUR-2024-00221.
  - 1 (PUR-2026-00047) is a duplicate of `southeast:aep:virginia/Abert-Reusens`, whose committed update text cites it.
  - 13 are excluded as non-utility solar generating-facility cases.
- Status: the Dominion list's own label (Planning→proposed, Preconstruction→planned, Construction→under_construction,
  Complete→in_service). Blank, "Restoration" and "Other" labels are `unknown`.
- History: each SCC case is a year-precision `source_status` event, a filing and never a certification (96 events).
  A page's single in-service or completion timeline date is a `planned_milestone` (54). Pages that state several years
  (phases) stay unknown. The one `in_service` event is Skiffes Creek, "was energized on February 26, 2019".

Unlocated (106): 66 have no facility named in the title (e.g. "Aviator", "Nova", "Line 224"). 18 name several
facilities, 5 name more than two terminals, and 16 name a facility with no OSM match. In 1, the only same-named
facility belongs to another utility.

## Spot check (12 random located records, seed 39)

I compared each matched OSM facility with the title and the source's own location text. The 12 records were:

- Chesterfield-Hopewell, in both the Dominion list and SCC case PUR-2018-00075
- Clover-Chase City
- Great Bridge Substation (Chesapeake)
- BECO-Firehouse and BECO-DTC (eastern Loudoun)
- Chase City-Cloud
- Chesterfield-Lanexa (New Kent)
- Harrowgate-Locks (Chesterfield/Petersburg)
- Ritter-Yemassee (Yemassee, SC)
- Staunton-Valley (Augusta)
- Reusens-Roanoke

All 12 sit at or between the named places inside the stated counties. **Errors found: 0.** One caveat: the parser cuts
"Mt Storm-Valley" to "Mt" and "Possum Point" to "Possum", so those records are partial, located at the one matched
endpoint.

## Known gaps and possible overlaps

- Same-looking projects are kept separate because no page cites the other's case: Dominion Loudoun-Ox with SCC
  PUR-2019-00128, and Dominion Chesterfield-Hopewell with SCC PUR-2018-00075 (same point). Several Appalachian Power
  SCC cases likely overlap AEP batch projects, but no AEP page cites their case numbers: Fieldale-Ridgeway
  PUR-2021-00219, Reusens-Roanoke PUR-2022-00163, Altavista-Leesville PUR-2026-00012 and Stuart Area PUR-2023-00024.
- Dominion pages also state SCC filing and final-order dates, which are not captured as `certification` events in this
  batch. Counties stay empty because GEOIDs were not derived. Coastal Virginia Offshore Wind links an outside site that
  was not fetched.

Reproduce from `pipeline/`: `uv run python -m southeast.virginia fetch --cache <dir>` then `build --cache <dir> [--check]`.
