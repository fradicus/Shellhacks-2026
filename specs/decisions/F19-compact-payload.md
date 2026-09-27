# F19 compact map payload — 2026-09-27

## Ownership and scope
The user assigns this session (codex-local, frontend-engineer) the follow-up to
[F31 compact payload](F31-compact-payload.md), merged in #226. Adopt its summary
loader and dataset-pinned detail component on `/time`.

## Requirements
- Send project summaries to Three.js; retrieve full evidence only on selection.
- Preserve all point IDs, centers, dates, tiers, scope membership, pairs, styling,
  animation and 2D/3D behavior. County-only records remain excluded.
- Preserve the existing evidence card once loaded, including citations and review notes.
- Use the shared loading, retry, stale-response and dataset-refresh handling.
- History already derives its own compact events on the server; retain its semantics.

## Validation
Compare full and compact adapters for geometry, dates, tiers and planning inclusion.
Run map/scope tests, typecheck, lint, build and exact-revision CI. Check browser
selection and 2D/3D. Record serialized payload sizes separately from network timing.

## Decision and rollback
Reuse F31 without a new dependency or cache. Reverting this adapter restores full
initial records. The original overnight gates are historical for this user task.
