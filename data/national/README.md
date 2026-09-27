# National data snapshot

This directory contains the reviewed, schema-validated national discovery snapshot. The unchanged base has 1,286 projects: all 1,024 rows from ISO-NE's June 2026 Regional System Plan list and 262 current GridBridge filing projects. Its 69 base centers all come from current legacy records whose location evidence remains eligible after the source audit. ISO-NE supplies no county or coordinate columns. Eligible legacy endpoint coordinates now establish state membership by containment in the pinned Census boundaries: 55 Georgia records and 14 South Carolina records. These remain candidate locations; containment does not confirm the endpoint or establish the full route. The other 193 legacy records retain unknown states. All base project counties remain unknown.

`sources.json` records 26 source entries. Eleven regional planning pages are catalogued only; their pages were verified, but no project count or geographic footprint is inferred. EIA-861 and FERC material is also reference-only. The snapshot does not claim nationwide project completeness or utility service-territory coverage.

From `pipeline/`, use the pinned Python environment:

```powershell
uv run python -m national validate
uv run python -m national build
uv run python -m national rebuild-legacy
uv run python -m national refresh --source iso-ne-rsp-2026-06
uv run python -m national.load
```

`validate` checks the committed artifacts without source downloads. `build` requires the reviewed files in the ignored `data/national/cache/` directory and reproduces all four JSON artifacts. `refresh` accepts only source IDs in `source-manifest.json`, follows only bounded credential-free HTTPS redirects on reviewed hosts, and rejects changed bytes, hashes, media types, or archive limits. A changed official file requires a new source review and manifest update; it is never accepted silently.

`national.load` is validation-only when `MONGODB_URI_RW` is absent. The existing GitHub `load` Action is the only place that supplies the write URI. It writes only the isolated national collections, persists candidate coverage, and then activates `meta._id = national_active`; later status or retention-cleanup failures are reported as warnings without claiming that activation was rolled back. It does not modify the legacy active dataset. Local commands validate without write credentials, and no live Atlas load is claimed by the committed evidence.

`geography.json` contains the full Census reference hierarchy, 2026 Gazetteer names and representative points, and 2025 cartographic boundary bounds. Those reference coordinates frame filters and labels; they are never substituted for project locations. `coverage.json` reports imported denominators and unknown fields so consumers can distinguish measured zero from unavailable data.

## Reviewed expansion locations

`national.build.load_snapshot` first validates these base files, then applies these fixed releases in order:

1. New England locations: `data/expansion/releases/active.json` (C23).
2. Southeast additions: `data/southeast/releases/active.json` (C27).
3. Mid-Atlantic additions: `data/expansion/mid-atlantic/releases/active.json` (C28).
4. Texas: `data/texas/statewide/releases/active.json` (C32) when present; otherwise
   `data/texas/releases/active.json` (C29). One exclusive slot; an invalid statewide release fails the load.
5. Great Lakes additions: `data/greatlakes/releases/active.json` (C26).

Each producer validates its facts-bound release. The loader recomputes source/total
coverage and validates the assembled snapshot before the national loader can stage it. Missing active releases
leave the base unchanged; invalid releases fail before staging. Candidate and research folders never activate.

Expansion geometry and its source/review evidence are embedded in the same national project document and move
with the existing atomic dataset pointer. Project IDs, original source rows, statuses and milestone precision
remain unchanged. Runtime `coverage.expansion`, `coverage.southeast`, `coverage.mid_atlantic`, `coverage.texas` and `coverage.greatlakes` preserve
each producer’s coverage, review counts and gaps separately from the recomputed national totals.
The workbook still supplies no coordinates; separate reviewed evidence supplies any accepted ISO-NE locations.
`national build` continues to write base snapshots only, so repeated loads do not bake overlays into originals.

The statewide Texas release contains 2,044 ERCOT TPIT projects from 2,049 observations: 635 tentative facility
locations (183 full, 452 partial), 1,218 county-reference projects and 191 unlocated. Its 1,407 county anchors
preserve all named counties under the existing project IDs. Exact centers and indexed `geo` remain null for
county-only projects; the separate attributed anchors may display labeled approximate dots. OSM-derived
facility references retain © OpenStreetMap contributors / ODbL 1.0 attribution. These records never create
national overlap pairs. F41 validates source rows, unique IDs, ledger links/hashes, geometry and tier counts.
The unchanged C29 fallback contains eight candidate projects at five centers. Removing only the statewide
activation manifest restores that fallback on the next load, without double-counting Texas native IDs.
The main-only load Action is triggered by this data documentation change; its receipt and the active Atlas
dataset still need verification before calling the batch loaded or visible.

## Location consistency

`rebuild-legacy` refreshes only the base legacy projection from the committed source, location and review
artifacts. It validates before writing, preserves non-legacy observations and never bakes regional overlays
into the base. State assignments retain endpoint IDs and the Census boundary URL, vintage and SHA-256.
Rejected endpoints supply neither centers nor state assignments. Unknown geometry stays unknown.

Aggregate `coverage.location_counts` separates confirmed centers, candidate centers, approximate-only
references and records with no display location. Those four counts partition the assembled records.
`rejected_projects` is an overlapping review count. `located_count` still means a non-null project center;
county reference anchors do not increase it. These counts describe stored location evidence, not how many
markers a renderer displays after filtering or clustering.

The September 27 audit found ten legacy project centers excluded by current endpoint rejections in the
national projection but retained by the legacy loader. This change preserves their national exclusions.
The legacy display correction is tracked with its owner in
[issue 191](https://github.com/fradicus/Shellhacks-2026/issues/191).
See `consistency-audit.json` for the reproducible source snapshot counts and affected project IDs.
