# C11: national public-source discovery and optional app controls

The user authorized a new follow-on on 2026-09-26 after the first run ended: reliable US-wide government and official planning sources, state/county/region filtering, coordination with the independent MongoDB worker, and a separate branch for a potential AI side button. Issue #83 records ownership. Plans B and D are required product references; the sponsor challenge and location guide remain the authority for the matching rule.

## Scope and compatibility

- Keep the existing Python, Next.js, MapLibre and MongoDB stack. The research attachment's PostGIS diagram is an architectural example, not a migration. Plans B and D differ on infrastructure; Plan D matches the built application.
- Retain exact source identities, hashes, source dates, public-status review, row/page evidence, uncertain dates and owner codes. Never reinterpret a milestone as a construction window or the freight anecdote as a savings ratio.
- Geography and source discovery may cover all states before actual project ingestion does. The UI must distinguish imported records, catalogued sources, unavailable sources and places not yet covered. A zero filtered result is not proof that a state has no planned construction.
- FERC identifies planning processes; official regional operators publish project plans. An ISO/RTO is not automatically a government agency. EIA describes utilities and service areas; Census supplies state/county geography. Existing-infrastructure GIS supplies reference geometry, not future construction or a project's confirmed position.
- Census regions, transmission planning regions, utility service areas and project locations are different concepts. Preserve string FIPS/GEOID codes and the basis of every project geography assertion. Never place a project at a county or utility-service-area centroid.
- Start with one verified machine-readable regional project adapter plus a registry for expansion. Unknown source fields stay null. Deterministic spreadsheet/table parsing precedes optional model extraction. No nationwide-completeness claim is permitted without measured ingestion coverage.

## Separate ownership and MongoDB boundary

F30 owns `pipeline/national/`, `data/national/`, and its pipeline tests. F31 owns `/explore`, `/api/national/`, `web/components/national/`, `web/lib/national/` and bounded web tests. Neither modifies the existing loader, server query helpers, semantic search, embeddings, map/time implementation or another agent's feature marker.

National snapshots use separate `national_sources` and `national_projects` collections, optionally `national_utilities` and `national_service_territory` for the explicitly separate EIA directory, namespaced by dataset, and a separate `meta` key `national_active`. `national_runs` contains only national load runs. The national loader validates before writing, promotes only after all writes succeed, and never edits the legacy `meta.active` pointer. The existing load GitHub Action remains the only Atlas writer. Its national invocation is conditional on the module and a validated snapshot existing. Without RW credentials it validates only. Live Atlas configuration stays with the MongoDB worker.

The published interface is `data/national/projects.json` (array), `sources.json` (array), `geography.json` (Census index), and `coverage.json` (source import outcomes and actual counts). National project and source JSON schemas are frozen contracts. The geography index has `states`, `counties`, `regions`, `divisions`, counts and source provenance; string keys are `state_fips`, `county_geoid`, `region_code`, `division_code`. Bounds exist only to frame a reference area. F30 may retain raw downloads in a ignored local cache; committed manifests and cited source rows must support offline replay without pretending unavailable upstream data was refreshed.

The national read API uses the existing read-only connection helper without modifying it. Missing configuration or missing national activation returns unavailable; committed data is only an explicitly labeled local/CI snapshot, never a production fallback. Census/source catalog metadata can be served as published public reference data independently of project database availability.

## Optional AI control branch

Reserve `codex-ai-app-control` for F32. Keep this separate from the national delivery and do not merge it merely because its branch exists. Plan D's Ask-the-grid direction becomes a typed, bounded action plan: apply supported filters, focus a known record or geography, and navigate to an allowed application view. An action cannot contain executable JavaScript, arbitrary MongoDB expressions, filesystem operations, unrestricted URLs or write actions. Questions and retrieved source text are untrusted data. All claimed counts and distances come from the same filtered records and deterministic functions as the UI.

A prototype without a configured model must say that it is an offline command preview; it must not present pattern matching as a live AI response. Existing live-service deferrals do not authorize a new paid model call. The current request authorizes the separate branch and concrete design/prototype, not automatic production activation of a public model endpoint.

## Run boundary

This is a new, explicitly requested follow-on after the first run's hard-stop time. Its authorized IDs are C11, F30, F31 and the separate F32 branch. The original `run_start`, `analysis_date`, historical results and completed-feature claims remain unchanged. First-run elapsed gates do not cancel this new request. Stop on the user's instruction; preserve isolated worktrees, independent review, ownership and CI gates. Old F08/F18 draft work remains untouched and must not claim this new scope complete.

Undo by removing the new routes/collections through their owners; legacy data and sponsor golden behavior are unchanged.
