---
id: F05
name: Landing page and retired map cleanup
lane: B
agent: frontend-engineer
phase: 1
depends_on: [F00]
owns: [web/app/page.tsx, web/app/map/, web/components/map/, web/components/list/, web/components/landing/]
cut: never
---

# F05 Landing page and retired map cleanup

## Current direction — 2026-09-27

The user retired the separate Project map. [C35](../../decisions/C35-retire-project-map.md)
and [issue #193](https://github.com/fradicus/Shellhacks-2026/issues/193) supersede the original
map/list requirements. Do not rebuild or expand that view. `/time` is the main Three.js planning map.
The original implementation requirements remain in Git history, not in the active work plan.

## Plan
1. Preserve the landing page and its active contributor's work.
2. Replace `web/app/map/page.tsx` with a redirect to `/time`.
3. Remove obsolete `web/components/map/` and `web/components/list/` files only after checking all
   importers. Preserve shared evidence components, APIs, pair routes and stored overlap facts.
4. Coordinate shared navigation and other owners' links through their respective PRs; do not edit
   another active F05 claim. No new map UI or dependency is required.

## Validation
- Run the required repository checks.
- Verify `/map` redirects to `/time`, Home still renders, and no deleted component has an importer.
- Verify the Three.js map, project selection, evidence and pair navigation still work.

## Defaults
The retirement implementation remains pending under issue #193. This specification is not a claim
that the route or navigation has already been removed. Existing landing-page claims retain ownership.
