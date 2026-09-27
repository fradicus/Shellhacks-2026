# F30: Append the fixed SPP South release

**Context.** C47 routes F47's SPP South release (`data/sppsouth/releases/active.json`, `sppsouth.publish.apply_release`)
through the same fixed-release pattern as the Midwest (`F30-midwest-hook.md`). On 2026-09-27 the user told this Claude
local session to fill sparse areas of the map continuously, starting with Oklahoma; the release reaches the map only
through this one-entry hook. F30 ownership otherwise stays with codex-local.

**Choice.** Append `("sppsouth", "sppsouth.publish")` after the Midwest in `load_snapshot`'s fixed producer list. Its
IDs and source are new and it reads no other producer's output. A missing active file is a no-op; an invalid one
fails before staging. No other F30 behavior changes.

**Undo.** Remove the entry or `data/sppsouth/releases/active.json`.
