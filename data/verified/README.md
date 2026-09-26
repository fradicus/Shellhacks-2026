# Verified utility directory

This snapshot imports the reviewed 2024 final Form EIA-861 archive. It contains 3,413 Frame utilities, 1,706 utility-activity rows and all 11,866 service-territory rows. Census geography resolves 11,818 county rows uniquely; 37 remain unresolved and 11 remain conflicting. The 48 unresolved/conflicting territory rows and three activity rows whose withheld utility number is absent from Frame remain in `quarantine.json` and do not populate utility county filters.

EIA's county rows mean distribution-equipment presence. They are neither exclusive service polygons nor transmission project locations. Census checks the county identity and state parent only; it does not independently corroborate EIA's service claim. Accordingly, `coverage.json` reports zero independently corroborated service claims.

The tracked artifacts are normalized public records. Raw workbooks and the source ZIP stay in the ignored `data/verified/cache/` directory. Each row retains its EIA archive/member hashes, sheet and row; `manifest.json` binds every tracked artifact. `generated_at` is an explicit replay input and is excluded from the dataset hash. The source retrieval time remains bound to the reviewed source record.

From `pipeline/`, use the pinned environment:

```powershell
uv run python -m verified --repo-root .. --generated-at 2026-09-26T18:00:22.262176+00:00 --check
uv run python -m verified --repo-root .. --generated-at 2026-09-26T18:00:22.262176+00:00
```

The first command validates a replay against the committed dataset without writing. The second writes artifacts after all archive, member, foreign-key, geography-parent, lineage and exact-count checks pass. `--refresh` is optional and accepts only bounded credential-free HTTPS redirects on `www.eia.gov`; the result must still equal the reviewed archive hash. A changed official release requires a new source review and hash update.

`GET /api/verified` accepts only `state`, `county`, `q`, `page` and `limit`. County requires its two-digit parent state; `q` performs bounded literal matching against utility ID/name; page starts at 1 and limit defaults to 25 with a maximum of 100. `GET /api/verified/coverage` exposes vintages, counts and limitations. Missing or hash-invalid artifacts return an unavailable response rather than fixture rows. Public API records omit raw workbook evidence.
