# F30: Append the fixed California municipal-utility release

**Context.** C51 routes F51's California municipal-utility release (`data/camunis/releases/active.json`, `camunis.publish.apply_release`)
through the same fixed-release pattern as the Interior West (`F30-interiorwest-hook.md`). On 2026-09-27 the user told this Claude
local session to fill sparse areas of the map continuously, naming California; the release reaches the map only
through this one-entry hook. F30 ownership otherwise stays with codex-local.

**Choice.** Append `("camunis", "camunis.publish")` after the Interior West in `load_snapshot`'s fixed producer list. Its
IDs and sources are new and it reads no other producer's output. A missing active file is a no-op; an invalid one
fails before staging. No other F30 behavior changes.

**Undo.** Remove the entry or `data/camunis/releases/active.json`.
