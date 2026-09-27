# F40 MISO projects under evaluation (MI, IN, IL, MN, WI)

**310 new Great Lakes projects, 60 with an unverified candidate location (58 distinct points), 0 verified.** Rule: [C26](../../specs/decisions/C26-great-lakes-candidates.md).

| | Count |
|---|---|
| Workbook rows | 597: 310 accepted, 94 linked to already-imported MN/ATC records by MTEP project ID (not duplicated), 193 outside F40 states |
| Accepted by state (a project can list several) | MN 78, IN 77, MI 69, IL 60, WI 29, other MISO states on multi-state rows 5 |
| Candidate located by state | MI 29, MN 13, IN 11, WI 5, IL 2 |
| Status (MISO planning status) | proposed 256 (M1), planned 43 (M2, Appendix A approved), in service 11 (M4) |
| Candidate located | 60: 23 sites, 18 lines with both endpoints, 19 partial lines |
| Unlocated | 250: no OSM facility with that exact name 96 (many are *new* substations not yet built), no single facility named 89, program/area/multi-facility 28, multi-terminal line 25, not corroborated 6, mixed 6 |

## Source

- [MTEP Projects Under Evaluation](https://cdn.misoenergy.org/MTEP%20Projects%20Under%20Evaluation368757.xlsx),
  public workbook on cdn.misoenergy.org (MTEP26 cycle). Fields kept: submitting TO (as owner), states, MTEP project ID,
  name, description, need, type, expected ISD (as given, day precision), current cost (estimate), planning status, kV.
- These are mostly **proposals under evaluation**, not approved or active construction. M2 rows are Appendix A approved.
- MISO's Appendix A status workbook (approved projects with quarterly status) returned HTTP 403 and was not used.
- Candidate geometry: shared OSM extracts for MN, WI, MI, IL, IN (`data/greatlakes/osm/`), matched only within the
  row's own states. Operator corroboration maps each submitting TO to its OSM operator names (e.g. METC → ITC/METC).

## Spot check

All 60 candidates reviewed by the producer (name, matched OSM facility, state, operator, voltage). Errors found and
fixed: "X - DC Redundancy" was a site read as a line (now unlocated, no equipment word proves a site); "Remediate Sag
on A - B" took the verb phrase as an endpoint; lowercase "tap" endpoints were not voided. Not an independent review.

Replay: from `pipeline/`, `uv run python -m greatlakes.miso fetch --cache DIR` then `build --cache DIR --check`
(after `greatlakes.minnesota` and `greatlakes.wisconsin`, whose MTEP IDs it links against).
