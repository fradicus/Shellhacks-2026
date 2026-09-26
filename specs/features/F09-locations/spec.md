---
id: F09
name: Endpoint locations with evidence and confidence
lane: A
agent: geo-engineer
phase: 2
depends_on: [F01, F02, F04]
owns: [pipeline/locations/, tests/pipeline/test_f09_, data/locations/, data/review/locations/]
cut: never
---

# F09 Locations

## Plan
1. For each endpoint of each **active** project (DESC and Georgia), find OSM candidates:
   - an exact `norm` match, else `difflib.get_close_matches(norm, n=5, cutoff=0.85)`
   - keep candidates in SC or GA; allow the other state within 10 mi of the border for ties
2. **Grade:**
   - `high`: one candidate, consistent with the project's area (DESC description / GPC zone) and with the operator tag if present
   - `medium`: several candidates, one chosen by stated evidence (county, voltage, operator)
   - `low`: fuzzy only
   - `rejected`: record why
   
   **Gemini never picks or asserts coordinates.**
3. Write `data/locations/locations.json` (schema `location`, one per endpoint, including the rejected candidates considered), and review decisions to `data/review/locations/geo.json`.
4. The golden sample keeps its own workbook coordinates; production projects never borrow them without a matching OSM feature.

## Requirements
- Every located endpoint has `osm_id` + `evidence`. No coordinate without a source.
- Report coverage: endpoints located per utility and per confidence, with denominators.

## Validation
- `tests/pipeline/test_f09_*.py`: grading logic on crafted candidate lists (single, multiple, fuzzy, none).
- Sanity: `DESC:6888`'s endpoints (Okatie, McIntosh) resolve within 1 mi of the sample coordinates above, if OSM has them.
- PR body: the coverage table and 5 random located endpoints with OSM links.

## Defaults
- **At 4:30 elapsed and not done:** restrict to projects whose names include AUGUSTA, EVANS, THURMOND, HOOKS, STEVENS CREEK, SAVANNAH, MCINTOSH, PURRYSBURG, GOSHEN, OKATIE, JASPER, BLUFFTON, YEMASSEE, or DESC projects in Aiken/Edgefield/Beaufort/Jasper counties. Ship, and mark the coverage as `border_only`.
