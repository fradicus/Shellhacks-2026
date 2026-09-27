# C52: audit hardening (M4–M12)

The user asked on 2026-09-27 for the audit's M4–M12 findings to be implemented in full. These are contract-style
changes, and some touch frozen or other-owned paths, which the user authorised for this batch. Behaviour already
covered by owners' tests is preserved; each item below has its own tests.

## Contracts

- **Legacy result contract (M4).** `web/lib/legacy/contract.ts` carries filters, the selected project or pair,
  release ID and record mode (`current` or `all_versions`). Table rows operate the map and list. CSV exports state
  release, filters, total, page and truncation in headers, and `format=manifest` returns them as JSON.
- **History (M5).** The ledger comes from the full filtered dataset; only the map uses the located subset.
  Documented and mappable counts are separate (`data-documented-events` / `data-mappable-events`). Coordinates are
  never invented.
- **Loaders (M6, M12).** `pipeline/common/load_summary.py` defines the load outcomes: `activated`, `already_active`,
  `retained_inactive`, `reactivated`, `pruned_receipt`, `validated_only`, `validation_failed` and
  `publication_failed`. Each run emits a sentence, a JSON summary, `LOAD_METRICS_PATH` and the step summary.
  - Both loaders check that a receipt is intact against actual document counts before reactivating it.
  - `--rollback` restores the previous pointer. `--activate` and `--restage` are deliberate.
  - `load.yml` exposes these as its `mode` input.
- **Repository and caches (M7).** Pages and handlers share one repository with projections, pagination, deadlines,
  aborts and release-keyed caches. Verified artifacts are cached by file identity, and a failed check is never
  cached. `scripts/capture_explain_plans.mjs` captures read-only query plans.
- **Matcher (M8).** `candidate_pairs` is a latitude-window candidate search, and exact haversine remains the final
  check. It is proven equal to brute force by tests. `python -m matches.benchmark` reports timings. TimeView was
  split into `model.ts`, `panels.tsx` and the orchestrator; disposal is unchanged.
- **Tests (M9).**
  - `scripts/run_node_tests.mjs` is the exhaustive Node registry and fails if a registered file is missing.
  - `scripts/run_browser_suites.mjs` names every Playwright suite.
  - The new required `acceptance` CI job runs the real-data parity pytest files, then `tests/acceptance`, offline.
  - `e2e` stays non-blocking, and live-service checks stay out of CI.
- **Planning status (M10).** There is an explicit planning-eligible status policy, with named `cancelled` and
  `status unknown` categories.
- **Docs (M11).** The README was revised, `.env.example` completed and `SITE_URL` removed because no code reads it.
  Provider and upload policy is in [C53](C53-provider-routing-and-upload.md).
- **Health and errors (M12).**
  - `/api/health` keeps F08's fields and 200/503 semantics. It adds per-capability readiness: legacy dataset,
    national dataset, verified artifacts and providers, each without secrets.
  - Operations routes classify failures as `invalid_input`, `body_too_large`, `departure_window`, `not_configured`,
    `provider_failure`, `timeout`, `publication_failure` or `internal`, and return `{error, code}`.

## Ownership

New paths that no feature owned are assigned; existing ownership is unchanged.

| Path | Owner |
|---|---|
| `web/lib/legacy/`, `tests/web/legacy/` | F06 |
| `web/components/scene/`, `tests/web/time/` | F19 |
| `tests/web/health/`, `.env.example` | F08 |
| `tests/web/export/` | F11 |
| `tests/acceptance/` | F07 |
| `tests/web/loader.mjs` | frozen |

The work ships as one PR per owner in dependency order. Shared and frozen files go in `[C52]` PRs.

## Undo

Revert the audit PRs. The loaders' new flags are additive; without them the loaders behave as before and also print the
summary.
