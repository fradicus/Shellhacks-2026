# Texas main-map delivery receipt

Verified 2026-09-27 at 06:06:04 UTC against the read-only Atlas dataset
`f3b0fc7250451585f1eef2873d452be5779f95aa` on the local integration preview at
`http://localhost:3017/time`. Product code is merged through `29e09d223eb05eeb8d984175bda9e954ce19acf1`.

## Publication chain
- Fixed eight-project Georgetown release: #168, unchanged.
- Statewide contract #178, producer #177, F30 loader #185.
- Initial Texas load: [Action 36296451991](https://github.com/fradicus/Shellhacks-2026/actions/runs/36296451991), successful, dataset `5effc228a094d2ac383a49d9af82feaa2d355160`.
- Current dataset after the F30 consistency release: `f3b0fc7250451585f1eef2873d452be5779f95aa`; Texas counts retained.
- F31 frontend/API #189 (`ee32a8a24b15b7aacf939207fa34e74761227b3b`) and the existing F19 owner's
  tentative renderer #196 (`29e09d223eb05eeb8d984175bda9e954ce19acf1`) are merged.

## Counts
Source: committed `data/texas/statewide/summary.json`, canonical project ledger and actual adapter/API.

| Scope | Count |
|---|---:|
| TPIT observations | 2,049 |
| Canonical projects | 2,044 |
| Tentative facility centers | 635 |
| Full / partial candidates | 183 / 452 |
| County-only projects / anchors | 1,218 / 1,407 |
| Unlocated projects | 191 |
| Ambiguous terminals / affected observations | 80 / 77 |
| Distinct candidate center coordinates | 443 |
| Independently confirmed Texas projects | 0 |
| Tentative projects in the Three.js planning scene | 569 |
| Tentative records excluded because reported in service | 66 |
| County-only markers in the Three.js scene | 0 |

The national API reports all 2,044 Texas records, 635 center-based and 1,218 approximate-location
projects; no map truncation. The Three.js adapter requires a real stored center and preserves its
coordinates. Counts describe projects, not distinct facilities. ERCOT source coverage is not all Texas.

## Visible acceptance
Selected `ercot-tpit:100025`, Naismith: Expand 138 kV Station, AEP TCC, from the searchable Projects
drawer. The amber Three.js pillar, tentative label, partial endpoint, ERCOT source locator and dataset
were visible. The filed month stayed December 2029; the full raw timestamp remained separately shown.
The details displayed: "OSM facility reference point matched by exact name + county; not independently
reviewed; not survey-grade."

Selection survived 2D/3D. At 390×844 the selected card stayed within the viewport with no horizontal
overflow. Home → Overlaps → National explorer → Overlaps rendered the basemap, pillars and year ruler
on re-entry. The browser console reported no errors. Existing booth mode still selected stored legacy
pairs. County-only record 100018 retained its two counties in the explorer and never entered the scene.

Focused checks: 14 national frontend tests and four F19 adapter tests passed. A direct assertion against
the committed Texas ledger produced 635 candidates, 569 planned-scene records and zero county-only
records, with original centers retained. Combined TypeScript checks passed. #189 required CI passed
with 611 pipeline tests and one skip; its three browser suites passed 4, 5 and 20 tests. #196 required CI
and its browser job passed. Existing Big Shoulders fallback-font warning remains.

This is verified local integration using live Atlas, not a hosted deployment or observed user acceptance.
Headed frame rate and explicit tile/WebGL-failure probes were not measured in this final batch. No new
spatial matching, independent location confirmation or survey-grade precision is claimed.
