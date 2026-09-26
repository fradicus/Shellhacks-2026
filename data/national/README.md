# National data snapshot

This directory contains the reviewed, schema-validated national discovery snapshot. It currently has 1,286 projects: all 1,024 rows from ISO-NE's June 2026 Regional System Plan list and 262 current GridBridge filing projects. The 69 exposed centers all come from current legacy records whose location evidence remains eligible after the source audit. ISO-NE supplies no county or coordinate columns. Legacy records do not contain reviewed project state or county assignments. All current project counties and all legacy project states therefore remain unknown rather than inferred.

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
