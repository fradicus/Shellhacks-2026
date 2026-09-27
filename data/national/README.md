# National data snapshot

This directory contains the reviewed, schema-validated national discovery snapshot. The unchanged base has 1,286 projects: all 1,024 rows from ISO-NE's June 2026 Regional System Plan list and 262 current GridBridge filing projects. Its 69 base centers all come from current legacy records whose location evidence remains eligible after the source audit. ISO-NE supplies no county or coordinate columns. Legacy records do not contain reviewed project state or county assignments. All current project counties and all legacy project states therefore remain unknown rather than inferred.

`sources.json` records 26 source entries. Eleven regional planning pages are catalogued only; their pages were verified, but no project count or geographic footprint is inferred. EIA-861 and FERC material is also reference-only. The snapshot does not claim nationwide project completeness or utility service-territory coverage.

From `pipeline/`, use the pinned Python environment:

```powershell
uv run python -m national validate
uv run python -m national build
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

Each producer validates its facts-bound release. The loader recomputes source/total
coverage and validates the assembled snapshot before the national loader can stage it. Missing active releases
leave the base unchanged; invalid releases fail before staging. Candidate and research folders never activate.

Expansion geometry and its source/review evidence are embedded in the same national project document and move
with the existing atomic dataset pointer. Project IDs, original source rows, statuses and milestone precision
remain unchanged. Runtime `coverage.expansion`, `coverage.southeast` and `coverage.mid_atlantic` preserve
each producer’s coverage, review counts and gaps separately from the recomputed national totals.
The workbook still supplies no coordinates; separate reviewed evidence supplies any accepted ISO-NE locations.
`national build` continues to write base snapshots only, so repeated loads do not bake overlays into originals.
