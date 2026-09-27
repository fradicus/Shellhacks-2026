# F40 FirstEnergy transmission projects (OH, PA)

**42 projects, 23 with an unverified candidate location (22 distinct points), 0 verified.** Rule: [C26](../../specs/decisions/C26-great-lakes-candidates.md).

| | Count |
|---|---|
| Projects | 42 project pages: Ohio 30, Pennsylvania 12 (all pages linked from FirstEnergy's two state index pages) |
| Status | proposed 35 (page says the company proposes the work), in service 1, unknown 6 (page states neither) |
| Candidate located | 23 (OH 14, PA 9): 4 sites, 11 lines with both endpoints, 8 partial lines |
| Unlocated | 19: name not in OSM 6, multi-terminal/multi-line 6, program/area 6, no facility named 1 |
| Counties and siting cases | taken from page text ("Erie County, Ohio"; "Case No. 25-1038-EL-BLN") where stated |

## Source

- `https://www.firstenergycorp.com/about/transmission_projects/{ohio,pennsylvania}.html` and each linked project page
  (title, owning subsidiary such as ATSI / Met-Ed / MAIT, counties, Ohio Power Siting Board case). No coordinates.
- Candidates from the endpoint/site names in the title, matched to OSM substations in the page's state with
  FirstEnergy-family operator keys (Ohio Edison, Toledo Edison, The Illuminating Company, ATSI, Met-Ed, Penelec,
  West Penn, MAIT) or voltage. These are the first Pennsylvania records; PJM's own list remains unreachable.

## Spot check

All 23 candidates reviewed by the producer. Extraction fixes found here and applied to every state (no other state's
output changed): hyphenated voltages ("Hayes 138-kV"), "No. 3" line numbers, and "Improvements"/"Reliability" as work
words. Not an independent review.

Replay: from `pipeline/`, `uv run python -m greatlakes.firstenergy fetch --cache DIR` then `build --cache DIR --check`.
