# F30: Append the fixed Interior West release

**Context.** C50 routes F50's Interior West release (`data/interiorwest/releases/active.json`, `interiorwest.publish.apply_release`)
through the same fixed-release pattern as SPP South (`F30-sppsouth-hook.md`). On 2026-09-27 the user told this Claude
local session to fill sparse areas of the map continuously, continuing with Wyoming after Oklahoma; the release reaches the map only
through this one-entry hook. F30 ownership otherwise stays with codex-local.

**Choice.** Append `("interiorwest", "interiorwest.publish")` after SPP South in `load_snapshot`'s fixed producer list. Its
IDs and sources are new and it reads no other producer's output. A missing active file is a no-op; an invalid one
fails before staging. No other F30 behavior changes.

**Undo.** Remove the entry or `data/interiorwest/releases/active.json`.
