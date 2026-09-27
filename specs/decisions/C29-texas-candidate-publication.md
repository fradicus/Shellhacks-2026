# C29: Fixed Texas candidate release

Status: accepted contract for the F41, F30, F31 and F19 handoff. Governing display policy: [C25](C25-main-demo-map.md).
Contract claim: [issue #164](https://github.com/fradicus/Shellhacks-2026/issues/164).

## Reason and boundary

F41's July 2026 ERCOT TPIT research has eight schema-valid candidate projects. Source observations and staged
projects cannot activate by folder scan. This contract adds a fixed release input to the existing national
snapshot chain; it does not relax the legacy overlap rule or change another producer's release criteria. The
existing main-only load Action remains the sole Atlas writer. The active dataset pointer and previous valid
dataset survive an invalid release or failed load.

## Producer input and checks

F41 owns `data/texas/releases/active.json` and `pipeline/texas/publish.py`. The release names the exact
`data/texas/publication-source.json` and `data/texas/publication-candidates.json` files with SHA-256 hashes.
It records the workbook hash, City of Georgetown GIS hash, observed retrieval times, expected source/project
IDs and counts, the source sheet/row for each accepted project, terminal and GIS feature IDs, and policy `C25`.
Only these eight native IDs may enter the first release: `80546B`, `92629`, `80546C`, `85973`, `109790`,
`109814`, `110120`, `110122`. The source workbook hash is
`4a08ea0f26af780f0d63c21304f3969ee876a49b152b827be8b48b8edb655b05`; the facility GIS hash is
`8744d520a685689b8166948af6077f8b52447b2b61842a6b25ba72f0e7b97f49`.

The assembler validates the national source/project schemas, exact release file hashes, source hash and row
locators against every project, distinct project/native IDs, finite Texas geometry, declared WGS84 CRS, unique
terminal-to-facility match, county/owner corroboration, center arithmetic, candidate tier and `unreviewed`
state. It also checks month precision and source row status without promoting a Completed-sheet row merely
because of its sheet name. Missing or ambiguous retrieval time or project-site evidence fails the release.
Research observations, asset-only records and unresolved identities stay outside it. A candidate point remains
excluded from every overlap computation; one located endpoint is labeled partial.

F41's eight project records occupy five distinct center coordinates. That is eight project identities and five
drawable points, not eight physical sites or Texas-wide coverage. The complete three-sheet source observation
count is 2,049 rows, including five repeated Future native IDs. The release count is bounded to eight reviewed
project-to-facility links; it makes no claim about the other observations. The producer never sets
`location_review=confirmed` or calls its own candidate independently confirmed.

## Loader and readers

F30's owner appends `texas.publish.apply_release` after the existing expansion, Southeast and Mid-Atlantic
assemblers in `pipeline/national/build.py`, conditional on that exact active file. A missing file preserves
prior behavior. An invalid file fails closed before staging the new national dataset. Existing source/project
IDs may not be overwritten; explicit cross-source identity evidence is needed for any future deduplication.
The assembler adds a Texas coverage section and recomputes national/per-source counts under the same active
dataset pointer. No second load Action, credential or collection is introduced.

F31's national API and `/explore` retain source row, GIS feature, source and geometry hashes, tier, review state,
raw milestone and partial-endpoint meaning. F19's `/time` adapter currently admits confirmed national points
only. Its owner adds labeled candidate markers and selectable evidence before Texas visibility can be claimed.
The candidate layer never earns a Confirmed badge, overlap ring, pair rank or coordination savings. Keep
coincident projects individually selectable.

## Verification and rollback

Run all repository checks and negative tests for changed hash, ID, row, center, county, status, geometry and
duplicate identity. Record staged count, accepted release count, successful load Action/dataset ID, Atlas
read-only count and selectable `/time` count separately. Live completion needs a representative Texas ID in
the active Atlas read, `/explore` and `/time` with matching evidence and dataset ID. If credentials, CI, deploy
or map support are unavailable, report the actual boundary. Revert the Texas active release or activate the
previous valid dataset to roll back, preserving research and audit artifacts.

F41 changes only its producer files, F30 only its loader files, F31 only its read files, and F19 only its map
files. This contract authorizes additive compatibility work in those existing assignments; no worker edits
another feature's implementation or spec.
