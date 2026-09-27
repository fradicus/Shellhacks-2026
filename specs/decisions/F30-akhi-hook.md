# F30: Append the fixed Alaska and Hawaii release

**Context.** C49 routes F49's Alaska and Hawaii release (`data/akhi/releases/active.json`,
`akhi.publish.apply_release`) through the same fixed-release pattern as the other rollouts. On 2026-09-27 the user
told this Claude local session to fill in Alaska and Hawaii and see it through, which needs this one-entry hook, as
for the Southwest (`F30-southwest-hook.md`). F30 ownership otherwise stays with codex-local.

**Choice.** Append `("akhi", "akhi.publish")` after the California municipal utilities (C51) in `load_snapshot`'s fixed producer list. A
missing active file is a no-op; an invalid one fails before staging. No other F30 behavior changes.

**Undo.** Remove the entry or `data/akhi/releases/active.json`.
