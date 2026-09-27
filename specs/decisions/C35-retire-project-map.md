# C35 Retire Project map and clarify Texas display

User direction on 2026-09-27: open an issue/spec to delete the separate Project map, remove it from
active agent requirements, then finish the Texas Three.js hookup through merge. Tracking: issue #193.

## Accepted product contract
- `/time` remains the main Three.js planning map. `/history` and `/explore` retain their existing roles.
- Retire `/map`: remove Project map from shared navigation and active entry points, redirect old
  `/map` links to `/time`, and remove unused map/list components after checking importers.
- Do not rebuild or expand the retired view. This supersedes F05's original map/list plan and F21's
  conditional cleanup instruction. Historical decisions and source records remain untouched.
- For `/time`, include accepted tentative facility centers with clear Tentative labeling and source
  notes. Exclude county-only anchors, even where another consumer supports approximate markers.
  This is the latest user override of broader county-display proposals for the Three.js planning map.
- Preserve current lifecycle filtering: records reported in service stay in History. Keep all stored
  locations, source dates/precision, canonical IDs, legacy pairs, distances and rankings unchanged.

## Delivery and ownership
This contract changes specs only. It adds the otherwise unowned `web/app/map/` to F05 for the redirect.
The shared navigation owner removes the frozen nav entry in a contract PR; F05 handles the route and
unused components after active landing claims finish. Other owners repair their entry points in
separate PRs. No reassignment or concurrent edits to active landing work are implied.

The F41/F31 Codex session delivered #189 and verified the existing F19 owner’s compatible #196,
which merged first with the cleanup owner’s agreement. No duplicate F19 implementation was opened.
Issue #190 retains its separate cleanup claim; preserve the merged tentative-point behavior.

## Acceptance
Required repository checks; no visible Project map entry; `/map` redirects to `/time`; Home, 3D
selection/evidence and pair links work. Texas acceptance requires a live tentative project in the
Three.js scene, its note in details, and zero county-only anchors. Spec delivery does not claim route
retirement or frontend integration has already shipped. Undo by a new explicit product decision.
