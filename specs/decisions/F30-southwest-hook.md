# F30: Append the fixed Southwest release

**Context.** C42 routes F45's Southwest release (`data/southwest/releases/active.json`, `southwest.publish.apply_release`)
through the same fixed-release pattern as California and the Pacific Northwest. On 2026-09-27 the user told this Claude
local session to implement the Southwest rollout end to end ("alright go cook"), which needs this one-entry hook, as
for California (`F30-california-hook.md`). F30 ownership otherwise stays with codex-local.

**Choice.** Append `("southwest", "southwest.publish")` after the Pacific Northwest in `load_snapshot`'s fixed producer
list. A missing active file is a no-op; an invalid one fails before staging. No other F30 behavior changes.

**Undo.** Remove the entry or `data/southwest/releases/active.json`.
