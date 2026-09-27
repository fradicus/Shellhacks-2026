# C32: Statewide Texas tentative terminal references

The user requested this contract as C30 on 2026-09-27. C30 was already claimed by PR #173 for planning/history
dates, and C31 by PR #175; C32 preserves those owners. This contract implements the user's statewide Texas
instruction and extends C29 without changing its committed eight-project release.

## Fixed release and identity

F41 owns `data/texas/statewide/releases/active.json` and `texas.statewide_publish.apply_release`. The release
pins derived facilities, projects, source, row observations and summary by SHA-256, alongside the three pinned
TPIT observation inputs. It lists every canonical project ID and independently recomputable expected counts.
The 2,049 July 2026 TPIT rows yield 2,044 native IDs. Five Future IDs repeat with identical extracted facts;
publish each once and retain both source row citations. Conflicting duplicate facts fail closed.

OSM facilities are supporting evidence, never separate transmission projects. Retain exact Overpass query,
URL, User-Agent, observed retrieval time, raw-response SHA-256, OSM element IDs and ODbL attribution in the
derived ledger. Census TIGERweb State_County layer 1 supplies 254 Texas county polygons in WGS84; retain its
query, retrieval time and raw hash. Raw downloads stay outside Git. Source vintages and retrieval times differ.

## Matching and tiers

Use the existing `_facility` normalizer equally on source terminal and OSM `name`, `alt_name`, `old_name`.
Require exact normalized equality, containment of the OSM reference point in the row's exact named county,
and one surviving OSM element ID. Repeated aliases on one element count once; two elements are ambiguous.
Boundary/ambiguous county membership does not qualify. No fuzzy match, nearby substitute or county centroid.
One matching endpoint is partial; two use the mission arithmetic mean. These are tentative terminal references,
not surveyed construction sites or line routes. Retain that distinction for new substations named along lines.

Display Candidate / tentative with this visible note:
"OSM facility reference point matched by exact name + county; not independently reviewed; not survey-grade."
Keep `location_review=unreviewed`. Preserve source links, both row citations where duplicated, OSM attribution
and reference-point meaning in selection and exports. Candidate geometry never enters overlap calculations.
Area-only rows retain recognized named counties and null center; unlocated rows retain raw unknown geography.
Texas county-only records never become dots, including under any broader C31 county-location policy.
Completed-sheet names do not override conflicting row statuses; preserve the conflict and actual/projected
milestones independently. No inferred dates or completion claims.

## Loader and consumers

F30 adds one exclusive Texas slot after existing expansion, Southeast and Mid-Atlantic assemblers: use the
statewide fixed release when present; otherwise use C29's eight-project release. Do not append both. This
replaces Texas representations through stable `ercot-tpit:<native ID>` identities without changing other
producers. A missing statewide release preserves the C29 fallback; an invalid statewide release fails the load
rather than silently falling back. Validate file hashes, source URLs/vintage, row/native identity, exact matching,
geometry and arithmetic, unique canonical IDs, provenance times, tier counts and final national schema/counts
before staging. The main-only load Action remains the sole Atlas writer and preserves the previous active
dataset on failure. Roll back by removing the statewide activation file and loading the C29 fallback.

F31 preserves candidate/area/unlocated evidence and ODbL attribution in API, explorer and exports. F19 admits
candidate points only with the visible tentative distinction, partial-endpoint meaning and selection evidence;
area-only remains searchable without a point. Each existing owner implements its own paths. No new worker is
assigned. Report observation and canonical counts separately: full/partial candidates, area-only, unlocated,
ambiguous terminals and affected rows. Staged, merged, loaded, active-read and selectable-map counts are distinct.
Live delivery requires the successful Action, matching active RO read and selectable `/time` candidate evidence.
