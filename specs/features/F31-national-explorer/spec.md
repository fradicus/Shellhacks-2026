---
id: F31
name: National explorer and geographic filters
lane: B
agent: frontend-engineer
phase: 5
depends_on: [F00]
owns: [web/app/explore/, web/app/api/national/, web/components/national/, web/lib/national/, tests/web/national/]
cut: never
---

# F31 National explorer

Build `/explore` using Plans B/D's synchronized map/table, evidence and uncertainty principles and C11's interfaces. Keep the other agents' original map, time view, MongoDB search and embeddings untouched.

Implementation may run alongside F30 against the national schema contract; final acceptance requires F30's real validated snapshot and geography index. F31 owns a typed mirror of those schemas in its own library; it must not invent demo project records.

## Requirements

- Region, state, county, planning-region, utility/owner, date/status and text filters, limited to what source evidence supports. Census region is not a transmission region. Cascading controls and URL state stay consistent, including back navigation and reset. Unknown geography is visible and never silently matched to a county.
- A nationwide map with current filtered, evidenced project points and a table that remains useful without geometry or tiles. Reference geography may set the viewport but cannot become a project point. Selection and counts refer to the same filtered set.
- Source details include authority, vintage, retrieval evidence and the row/page used. Clearly distinguish real imported coverage from catalog-only regions, unavailable services, no matches within imported data and unknown locations.
- C23 location evidence in the selected project and source details preserves site versus complete/partial endpoints, source precision/date, identity/location citations and the latest independent review. Confirmation describes location, not construction completion. `/api/national/export?format=json` includes the active dataset and embedded evidence within the existing export limit; omitted format and `format=csv` preserve CSV. Duplicate or unsupported formats fail with 400.
- Strict, bounded read-only API parameters and pagination/export sizes. Reuse the existing RO connection helper without editing it. Data comes from the national namespace; no arbitrary database query or URL may pass through a filter.
- Local/CI snapshot mode is explicitly labeled and disabled for production. Unconfigured Atlas or an absent national dataset returns an honest unavailable state. Public government/reference metadata is labeled independently of stored project availability.
- Keep existing sponsor and legacy routes intact. Provide a reusable typed filter/action interface for the optional F32 branch; do not activate or imply a live model.

## Validation

Check cascading region/state/county filters, invalid/cross-state codes, unknown geography, URL/back restoration, exact filtered counts and bounded export, missing DB, empty results, map/list consistency and 390px/desktop layouts. Source dates and evidence links must be readable. Run repo-wide checks and focused web tests. Actual browser evidence and any verification limitation must be reported precisely.

## Candidate and county dots (2026-09-27)

The user explicitly requested the frontend hookup after the Texas release. This Codex local session adopts
F31's frontend-engineer role under the existing codex-local assignment in specs/roadmap.md. No other F31
claim is open. Apply C32 Texas's candidate and separate county-anchor representation to the existing
map/API and evidence/export views. Include valid candidate centers and county display anchors by default;
keep exact centers null for county-only records. Use visible Tentative / Approximate location labels, retain
provenance and all named counties, and keep shared positions individually selectable. Count projects once.
Keep reads bounded and disclose truncation. No new matching, geographic inference or date-policy changes.
F19's main-map hookup is a separate claim and does not change F31's ownership.

The bounded map projection admits at most 10,000 project records (matching the existing snapshot ceiling);
exports remain capped at 2,000 and pages at 100. `locatedTotal` retains center-based counts; the additive
`approximateTotal` counts county-only projects, and `unlocatedTotal` excludes those known county locations.

Latest user direction: county anchors may remain in the explorer, but must not enter F19’s Three.js map.
F19 consumes only accepted facility centers, labeled tentative where unreviewed.

## Dataset cache follow-up (2026-09-27)

The user assigned this Codex local session the [map cache specification](../../decisions/F31-map-cache.md).
Implement within F31: reuse the unfiltered map loader's successful Atlas result by
active dataset ID, with fresh pointer reads, bounded per-instance retention and
failure retry. Preserve payloads and visuals. This also benefits History's existing
call to the same loader; no F19/F37 presentation files are part of this claim.
