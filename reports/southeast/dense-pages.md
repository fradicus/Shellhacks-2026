# Dense Southeast: small utility project pages (EKPC, FirstEnergy WV/VA, Georgia Power, Georgia Transmission; C45)

## Sources

All were retrieved on 2026-09-27. All are public pages with no login and no CEII banner. None of them is dated as a
whole: the pages are live, and FirstEnergy's pages carry their own "Last Modified" date, which is kept as each event's
`source_date`.

| Source record | URL | sha256 | Rows |
|---|---|---|---|
| `southeast:ekpc`: EKPC current projects (6 accordion blocks; 5 PDF brochures and 1 project page kept as evidence) | https://www.ekpc.coop/current-projects | `fa86862c…9d4649b` | 6 |
| `southeast:firstenergy-wv`: FirstEnergy WV index and its project pages | https://www.firstenergycorp.com/about/transmission_projects/westvirginia.html | `07ec3a59…3c969655` | 6 |
| `southeast:firstenergy-va`: FirstEnergy VA index and its project pages | https://www.firstenergycorp.com/about/transmission_projects/virginia.html | `18251b81…4cf4848d83` | 3 |
| `southeast:georgia-power`: Georgia Power transmission projects index and 10 pages | https://www.georgiapower.com/about/grid-reliability/grid-improvements/grid-projects/transmission-projects.html | `ddaf9ced…2a00bbbd` | 10 |
| `southeast:gtc-ecrp`: GTC East Central Georgia Reliability Projects | https://www.gatransmission.com/ecrp/ | `c9a8c085…e53034f0` | 6 |
| `southeast:gtc-dresden-talbot`: GTC Dresden – Talbot 500 kV | https://www.gatransmission.com/dresden-talbot/ | `a9123336…abc187b78` | 1 |
| OSM `power=substation` for KY, WV, VA and GA (Overpass) | overpass-api.de | per cache manifest | ODbL |

FirstEnergy and GTC each have two source records. This is because a project's `evidence.source_sha256` has to be the
artifact that lists it, and each of those publishers lists its projects on two separate pages with no shared index.

## Counts (projects / located / not in service / with a dated event)

| State | EKPC | FirstEnergy | Georgia Power | GTC |
|---|---|---|---|---|
| KY (21) | 6 / 0 / 6 / 0 | | | |
| WV (54) | | 6 / 2 / 6 / 2 | | |
| VA (51) | | 3 / 2 / 3 / 0 | | |
| MD (24, stated by the page) | | 1 / 1 / 1 / 0 | | |
| GA (13) | | | 7 / 0 / 7 / 4 | 5 / 0 / 5 / 5 |
| AL (01, stated by the page) | | | 1 / 0 / 1 / 0 | |

- **Totals:** 25 projects and 3 located points. All 3 points are in the `candidate` tier, corroborated by voltage, and
  none is `official`. 11 projects carry a `planned_milestone` event. No project has an `in_service` event.
- **Duplicates (7 rows):**
  - 2 FirstEnergy pages appear on both the WV and VA indexes: Gore-Doubs-Goose Creek and Gore-Hampshire. Each is
    counted once, with both states.
  - 5 rows repeat legacy Georgia Power records. The rule is that the normalized endpoint names and the voltages must
    match exactly, using the repo's `facility_key`. The matches are:
    - Ashley Park–Wansley 500 kV → `legacy:GPC:21062`
    - Conyers–Klondike 230 kV → `legacy:GPC:21142`
    - Hatch–Wadley Primary 500 kV → `legacy:GPC:20756`
    - GTC East Walton 500/230 kV Substation → `legacy:GPC:09662`
    - GTC Dresden–Talbot 500 kV → `legacy:GPC:19950`
  - Each duplicate row's disposition keeps the page's own quarter (for example "Q4 2031" for Dresden–Talbot).
- **Dates:**
  - Georgia Power: a "Qn YYYY Project complete(ion)" row becomes a year-precision milestone, with the quarter kept in
    the description. Pages that list only component completion rows get no date: Big Tazewell–Farley ("Substation
    Complete", "Line Construction Complete"), Callaway Road and Effingham.
  - GTC ECRP: the page's single statement, "ready for service Q2 2027", applies to all 5 accepted items.
  - FirstEnergy: Sutton (2024-10-18) and WV MISOP (2024-11-01) are "be complete on or about" dates. They stay
    planned milestones and are not treated as completions.
  - EKPC: the brochures give construction windows but no in-service date, so EKPC projects carry no date.

## Unlocated (22)

- 11 have no OSM facility with the name. Many endpoints are new or not yet mapped: Grassy Hollow, Hills Bridge, Big
  Tazewell, East Walton, Bostwick, Metts, Big Hill, Cub Run, Sutton.
- 3 are blocked by the operator guard:
  - Bonnieville and Campbellsville are tagged Kentucky Utilities, while the title is EKPC's.
  - Bethabara is tagged Georgia Power, while the line is GTC's.
- 4 are area or multi-facility titles: Callaway Road–Thomson "Area", Tomochichi–Towaliga River "Area", Glen Falls and
  Fairview, and WV MISOP.
- 1 names more than two terminals: Gore-Doubs-Goose Creek.
- 2 name no facility: Autumn Leaf and Effingham County.
- 1 is ambiguous: two OSM "Cooper" substations more than 1 km apart.

## Spot check (all 3 located records; fewer than 12 exist)

- **Page–Sperryville:** the page names "the Page Substation in Luray, Virginia, and the Sperryville Substation in
  Sperryville". The matched OSM points are Page at (38.670, -78.452), near Luray, and Sperryville at (38.658, -78.221).
  Both are tagged 138 kV. Correct.
- **Gore–Hampshire:** partial, at Gore Substation (39.276, -78.365) in Frederick County, VA, tagged 138 kV. The Gore-Doubs
  page places "the Gore Substation in Frederick County, Virginia". Correct. Hampshire has no OSM match.
- **Messick Road–Morgan:** partial, at Morgan Substation (39.607, -78.220), which is in Morgan County, WV, as the page
  says, tagged 138 kV. Correct. Messick Road is in Maryland, and Maryland's OSM data was not fetched.

**Errors found: 0.**

## Known gaps

- Two records may still overlap without being merged, because their endpoint names do not match exactly:
  - Big Tazewell–Farley 500 kV (page) and legacy "FARLEY (APC)-TAZEWELL 500KV" (`legacy:GPC:21063`).
  - Coburg–Campbellsville (title) actually ends at Heartland Park substation according to its brochure. Big Hill–Three
    Links taps the Three Links–Sand Gap line. Neither is located, so no wrong point was placed.
- Counties are stated on every page but left empty, because GEOIDs were not derived. MD and AL OSM data was not
  fetched, so endpoints in those states cannot match.
- Reproduce from `pipeline/`: `uv run python -m southeast.pages fetch --cache <dir>`, then
  `build --cache <dir> [--check]`.
