# C45: Dense Southeast coverage with loose, labeled locations

## Authority

On 2026-09-27 the user told this Claude local session to make the Southeast much denser, with both present
(`/time`) and past (`/history`) points, across the whole F39 scope, split into several PRs by geography.
Claude local adopts the technical-lead contract role for this change only.

## Findings (assembled snapshot at `5279de7`)

| State | Records | Located | With events |
|---|---|---|---|
| FL | 254 | 130 (129 tentative) | 17 (1 located) |
| GA | 55 | 55 (legacy) | 0 |
| SC | 14 | 14 (legacy) | 0 |
| KY | 1 | 0 | 0 |
| AL, MS, NC, TN, VA, WV, AR, LA | 0 | 0 | 0 |

Existing public sources and adapters already cover much of the gap. PJM's construction XML (reused by C28) lists
VA, WV, KY and NC upgrades with separate projected and actual in-service dates. AEP publishes state project maps for
KY, VA, WV, TN, LA and AR in the same format as F40's `greatlakes.aep`. F40's MISO workbook has LA, AR, MS and KY
rows that it dropped as out of scope.

## Decision

1. **F39 moves to claude-local.** Codex has no open F39 claim (#167 closed 03:43Z; its branch is kept). The strict
   C27 release and its reviewed Florida records are unchanged.
2. **Locations follow C33 tiers with C38's operator guard.** Tiers: `official` (the publisher's own map marker for
   the project), `candidate` (exact normalized OSM name in the reported state plus operator or voltage) and
   `candidate_unique_name` (one same-named facility in the state, no other utility's operator). Every point is
   `location_review: "unreviewed"` and is never counted as verified. County anchors are not drawn (C31 not adopted).
3. **History from source dates only.** PJM's actual, projected, revised, required and ISA dates become typed events
   with their field names (as C28 does). A source's in-service status becomes an `in_service` event only with a
   source date. No construction window is inferred from a milestone.
4. **Publication.** One fixed release, `data/southeast/dense/releases/active.json`, pins each batch's file hashes and
   expected counts. `southeast.publish.apply_release` applies it after the Florida tentative release. New
   `southeast:` IDs only; no source/project ID may collide with the assembled corpus. A row already represented
   elsewhere is recorded as a duplicate with its canonical ID.
5. **Parts by geography**, one open F39 PR at a time: PJM VA/NC, then PJM WV/KY, AEP maps (KY, VA, WV, TN, LA, AR),
   Florida plan history, MISO/SPP South (LA, AR, MS), Carolinas (NCTPC, SCRTP), then GA/AL/MS/TN utility sources.
   SERTP stays excluded under D15 unless a content-level check clears a specific edition.
6. **Target, not quota:** about 100 present and 100 past points per state where public sources allow. Report the
   counts found, per state, with unlocated reasons. A hand spot check of 12 located records per part is reported.

## Undo

Delete `data/southeast/dense/releases/active.json` (the hook becomes a no-op) and move F39 back to codex-local.
