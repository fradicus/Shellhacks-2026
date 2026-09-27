# F30: Append the fixed California release

**Context.** C37 routes F44's California release through the same fixed-release pattern as the Great Lakes
([F30-great-lakes-hook](F30-great-lakes-hook.md)). The user directed this Claude local session to deliver California
pins, which needs the one-entry hook in F30's loader; F30 ownership otherwise stays with codex-local.

**Choice.** Append `("california", "california.publish")` after Great Lakes in `load_snapshot`'s fixed producer list.
A missing `data/california/releases/active.json` is a no-op; an invalid one fails before staging. No other F30
behavior changes.

**Undo.** Remove the entry or the California active release file.
