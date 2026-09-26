---
id: F08
name: Release - deploy verification, health, domain, README
lane: C
agent: release-engineer
phase: 1
depends_on: [F05]
owns: [release/, web/app/api/health/, README.md]
cut: never
---

# F08 Release

Pre-flight intended the human to link Vercel, Atlas and DNS, but those live services were deferred for this run.
This feature ships the release checks and keeps the unperformed production acceptance visible; it never turns a
local check or a proposed URL into deployment evidence. See `specs/decisions/F08-execution.md`.

## Plan
1. `GET /api/health`: `{ok, commit: VERCEL_GIT_COMMIT_SHA, db: "up"|"down"|"not_configured", active_dataset}`, with the complete RO ping + active-dataset lookup bounded to 2 s. Never include secrets or raw errors. Missing configuration, an unreachable database, or a reachable database without an active dataset returns 503; the body distinguishes those states.
2. When targets exist, check after each merge to main: the production URL and the custom domain both serve the new commit (`/api/health` commit == main HEAD, within 10 minutes); HTTPS is valid; `/` returns 200. Record actual results in `release/deploys.md` (one line per check; this file is yours). Until then, record the check as deferred without a URL or pass claim.
3. **Secret scan** on production: fetch the main JS bundles, and grep for `mongodb+srv`, `GEMINI`, `AIza`. There must be none.
4. `README.md`: what the product is, the live URL, how to run it locally (fixture mode and Atlas mode), how to run the pipeline, and the architecture diagram (text). Update it when features land.
5. **If the domain, Vercel or Atlas isn't configured:** keep the live checks pending and track the exact missing setup in a `human-morning` issue. Issue #10 already covers this run; do not open a duplicate or invent DNS records. Verify a `*.vercel.app` URL only after its actual value is available.

## Validation
- The health route compiles in fixture mode. Direct checks cover missing configuration, unreachable MongoDB, a reachable database with no active dataset, and the local QA database with an active dataset; unavailable probes finish within 2 s.
- The deployment verifier's focused Node tests pass and invalid/incomplete targets fail closed.
- When live targets are available, `release/deploys.md` has a production check for both origins with the commit match. When the user defers them, it instead states exactly which checks were not run and links the existing `human-morning` issue; that is implementation completion, not production acceptance.

## Defaults
- Rollback: if production is broken and main is being fixed, don't touch Vercel (you have no human approval); rely on the `overnight.md` §6 revert flow.
