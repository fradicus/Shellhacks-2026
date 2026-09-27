# F40 Wisconsin (part 1)

**348 projects, 125 with an unverified candidate location (107 distinct points), 0 verified.** Rule: [C26](../../specs/decisions/C26-great-lakes-candidates.md).

| | Count |
|---|---|
| Projects | 348 accepted from 352 table rows: 3 duplicates of Minnesota records (same MTEP number: LRTP 04, 21, 26), 1 row with no name rejected |
| Status | planned 166, proposed 167 (ATC "Proposed" and "Provisional"), cancelled 10 (withdrawn), in service 4, unknown 1 |
| Candidate located | 125: 33 sites, 56 lines with both endpoints, 36 partial lines (one endpoint) |
| Candidate located by status | planned 51, proposed 66, cancelled 8 |
| States (from ATC zone pages) | WI only 145, WI+IL (zone 3) 120, WI+MI (zone 2) 43, unknown ("Various" programs) 40 |
| Unlocated | 223: no single facility named 64, no OSM facility with that exact name 63, name found but no operator/voltage corroboration 43, program/area/multi-facility 31, multi-terminal line 8, mixed endpoint reasons 9, endpoints unnamed 5 |

## Sources

- Project register: [ATC's 2025 10-Year Assessment Project List](https://www.atc10yearplan.com/wp-content/uploads/2025/11/TYA-2025-Network-Project-List.pdf)
  (network projects, created 2025-11-19), parsed with pdfplumber. Estimated in-service month, ATC status, MISO MTEP
  appendix/PRJID and estimated cost are kept per row. The cost is ATC's estimate, not an award or actual spend.
- States: each project's ATC zone, mapped to the states in that zone's own "includes the counties of" list
  (zones 1, 4, 5: WI; zone 2: MI and WI; zone 3: WI and IL). Zone states are labeled `geography_basis: source_zone`.
- Owner: American Transmission Company, from the document title ("ATC's 2025 10-Year Assessment Project List").
- Candidate geometry: OpenStreetMap substations in WI, MI and IL (ODbL), fetched from the VK Maps public Overpass
  instance after overpass-api.de refused connections from this network; `data/greatlakes/osm/sources.json` records it.

## Spot check

All candidates were reviewed by the producer against the project name and the matched OSM name, state, operator
and voltage. Systematic errors found and fixed before commit: leading short numbers ("9 Mile", "3 Mile")
were stripped as line numbers; "X SS – Transformer Asset Renewal" was read as a line instead of a site; an unclosed
bracket after the comma cut let a bracketed line name leak into endpoints. OSM names ending in "Station" now match
(e.g. Edgewater, Columbia, Kewaunee), which added 11 candidates. Same-name substations in other states (e.g. ComEd, DTE, Consumers) were correctly left unmatched.
Not an independent review.

## Gaps

- 43 exact-name matches lack OSM operator/voltage tags that agree with the project; official ATC facility GIS or
  PSC dockets could corroborate them.
- Other Wisconsin transmission owners (Xcel NSPW, Dairyland, municipal utilities) are not in ATC's list; their
  sources remain to be reviewed. Not in the national snapshot or Atlas yet (see issue #153).

Replay: from `pipeline/`, `uv run python -m greatlakes.wisconsin fetch --cache DIR` then `build --cache DIR --check`.
