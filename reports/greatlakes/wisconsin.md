# F40 Wisconsin (part 1)

**348 projects, 114 with an unverified candidate location (100 distinct points), 0 verified.** Rule: [C26](../../specs/decisions/C26-great-lakes-candidates.md).

| | Count |
|---|---|
| Projects | 348 accepted from 352 table rows: 3 duplicates of Minnesota records (same MTEP number: LRTP 04, 21, 26), 1 row with no name rejected |
| Status | planned 166, proposed 167 (ATC "Proposed" and "Provisional"), cancelled 10 (withdrawn), in service 4, unknown 1 |
| Candidate located | 114: 25 sites, 48 lines with both endpoints, 41 partial lines (one endpoint) |
| Candidate located by status | planned 46, proposed 60, cancelled 8 |
| States (from ATC zone pages) | WI only 145, WI+IL (zone 3) 120, WI+MI (zone 2) 43, unknown ("Various" programs) 40 |
| Unlocated | 234: no OSM facility with that exact name 71, no single facility named 64, name found but no operator/voltage corroboration 43, program/area/multi-facility 31, multi-terminal line 8, mixed endpoint reasons 12, endpoints unnamed 5 |

## Sources

- Project register: [ATC's 2025 10-Year Assessment Project List](https://www.atc10yearplan.com/wp-content/uploads/2025/11/TYA-2025-Network-Project-List.pdf)
  (network projects, created 2025-11-19), parsed with pdfplumber. Estimated in-service month, ATC status, MISO MTEP
  appendix/PRJID and estimated cost are kept per row. The cost is ATC's estimate, not an award or actual spend.
- States: each project's ATC zone, mapped to the states in that zone's own "includes the counties of" list
  (zones 1, 4, 5: WI; zone 2: MI and WI; zone 3: WI and IL). Zone states are labeled `geography_basis: source_zone`.
- Owner: American Transmission Company, from the document title ("ATC's 2025 10-Year Assessment Project List").
- Candidate geometry: OpenStreetMap substations in WI, MI and IL (ODbL), fetched from the VK Maps public Overpass
  instance after overpass-api.de refused connections from this network; the manifest records the endpoint used.

## Spot check

All 114 candidates were reviewed by the producer against the project name and the matched OSM name, state, operator
and voltage. Two systematic errors were found and fixed before commit: leading short numbers ("9 Mile", "3 Mile")
were stripped as line numbers, and "X SS – Transformer Asset Renewal" was read as a line with a missing endpoint
instead of a site. Same-name substations in other states (e.g. ComEd, DTE, Consumers) were correctly left unmatched.
Not an independent review.

## Gaps

- 43 exact-name matches lack OSM operator/voltage tags that agree with the project; official ATC facility GIS or
  PSC dockets could corroborate them.
- Other Wisconsin transmission owners (Xcel NSPW, Dairyland, municipal utilities) are not in ATC's list; their
  sources remain to be reviewed. Not in the national snapshot or Atlas yet (see issue #153).

Replay: from `pipeline/`, `uv run python -m greatlakes.wisconsin fetch --cache DIR` then `build --cache DIR --check`.
