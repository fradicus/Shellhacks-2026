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
   - keep candidates in SC or GA; allow the other state within 10 mi of the border only when the filed source
     positively identifies a tie
2. **Grade:**
   - `high`: one candidate, consistent with the project's area (DESC description / GPC zone) and with the operator tag if present
   - `medium`: several candidates, one chosen by stated evidence (county, voltage, operator)
   - `low`: fuzzy only
   - `rejected`: record why
   
   **Gemini never picks or asserts coordinates.**
3. Write `data/locations/locations.json` (schema `location`, one per endpoint, including the rejected candidates considered), and review decisions to `data/review/locations/geo.json`.
4. The golden sample keeps its own workbook coordinates; production projects never borrow them without a matching OSM feature.

### Conservative review policy used for the full-corpus run

- Cache only the Georgia and South Carolina state features from U.S. Census Bureau TIGERweb layer 4. Bind replay to
  the exact query, January 1, 2026 layer vintage and raw-response SHA-256. State membership and the numeric Georgia
  zone are coarse filters; neither is positive fine-area evidence. Compute border proximity as spherical
  point-to-great-circle-segment distance with the canonical 3,958.8-mile radius; 10.0 miles is inclusive.
- An opposite-state candidate needs both a distance of at most 10 miles and a positive `tie`/`tie line` quote in the
  filed name or description evidence. State proximity, matching operator, and matching voltage cannot substitute for
  source-supported tie context.
- A unique exact OSM substation with compatible state, operator and voltage evidence may be `medium` with the
  explicit `project_area_unverified` limitation. `high` still requires independent positive project-area evidence.
  Fuzzy names without that fine-area evidence remain `rejected` rather than being promoted from similarity alone.
- Source gates run before location acceptance. The 16 active DESC and 8 active Georgia `endpoint_ambiguous` records
  keep zero endpoints, including `DESC:6238 H@desc-2025` after the source parser recorded its title/description scope
  conflict. `GPC:20482@gpc-2025` keeps its two actual endpoints but stays unlocated for `source_status_conflict`.
- Each output is bound to the active version through explicit `project_id` and `source_id`. Its stable `_id` hashes
  the versioned project identity, actual endpoint index and normalized name, plus the selected OSM evidence identity
  (or an unlocated sentinel). Adding or reordering unrelated projects or candidates cannot retarget a review.
- Emit at most one accepted candidate for each actual filed endpoint. Keep every considered alternative and rejection
  reason nested on that endpoint. Never synthesize endpoint indices for the 24 active zero-endpoint projects.
- Automatic location decisions form an append-only event history. Use the actual UTC generation time for a new
  decision. Exact replay of the latest unchanged v2 decision preserves its event and timestamp; a changed decision
  appends an event linked to its predecessor, including an A-to-B-to-A sequence. Preserve the provisional v1 midnight
  records as historical evidence and supersede matching active-endpoint decisions with v2 events that identify the
  provisional timestamp. F09 decision hashes are separate from C7/F13 confirmed-audit subject fingerprints.
- `DESC:6888` is an honest partial sanity result: McIntosh's exact Georgia Power/230 kV feature conflicts with the
  filed DESC 115 kV tie evidence, while Okatie has no named OSM identity. The nearby unnamed 230 kV way remains a
  diagnostic candidate only; sponsor workbook coordinates never enter production locations.

## Requirements
- Every located endpoint has `osm_id` + `evidence`. No coordinate without a source.
- Report coverage: endpoints located per utility and per confidence, with denominators.
- Record canonical parsed-JSON fingerprints for project and normalized OSM inputs, because checkout line endings are
  not semantic input identity. Label byte hashes only for exact raw source caches protected from text conversion.

## Validation
- `tests/pipeline/test_f09_*.py`: grading logic on crafted candidate lists (single, multiple, fuzzy, none).
- Sanity: `DESC:6888`'s endpoints (Okatie, McIntosh) resolve within 1 mi of the sample coordinates above, if OSM has them.
- PR body: the coverage table and 5 random located endpoints with OSM links.

## Defaults
- **At 4:30 elapsed and not done:** restrict to projects whose names include AUGUSTA, EVANS, THURMOND, HOOKS, STEVENS CREEK, SAVANNAH, MCINTOSH, PURRYSBURG, GOSHEN, OKATIE, JASPER, BLUFFTON, YEMASSEE, or DESC projects in Aiken/Edgefield/Beaufort/Jasper counties. Ship, and mark the coverage as `border_only`.
