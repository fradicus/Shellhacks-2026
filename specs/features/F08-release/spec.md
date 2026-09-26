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

The human linked Vercel and set the DNS in pre-flight (`specs/preflight.md`). This feature verifies it, and keeps verifying.

## Plan
1. `GET /api/health`: `{ok, commit: VERCEL_GIT_COMMIT_SHA, db: "up"|"down"|"not_configured", active_dataset}`, with a 2 s DB ping using the RO URI. Never include secrets.
2. After each merge to main (check every run): the production URL and the custom domain both serve the new commit (`/api/health` commit == main HEAD, within 10 minutes); HTTPS is valid; `/` returns 200. Record the results in `release/deploys.md` (one line per check; this file is yours).
3. **Secret scan** on production: fetch the main JS bundles, and grep for `mongodb+srv`, `GEMINI`, `AIza`. There must be none.
4. `README.md`: what the product is, the live URL, how to run it locally (fixture mode and Atlas mode), how to run the pipeline, and the architecture diagram (text). Update it when features land.
5. **If the domain or Vercel isn't configured:** open an issue labeled `human-morning` with the exact missing step and the DNS records Vercel shows. Keep verifying the `*.vercel.app` URL.

## Validation
- The health route compiles in fixture mode. `release/deploys.md` has at least one production check with the commit match.

## Defaults
- Rollback: if production is broken and main is being fixed, don't touch Vercel (you have no human approval); rely on the `overnight.md` §6 revert flow.
