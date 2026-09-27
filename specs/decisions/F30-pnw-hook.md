# F30: Append the fixed Pacific Northwest release

**Context.** C33 routes F42's Pacific Northwest release (`data/pnw/releases/active.json`, `pnw.publish.apply_release`)
through the same fixed-release pattern as C26/C29. Issue #199 asked F30's owner (codex-local) for the one-entry hook.
On 2026-09-27 the user explicitly approved ("yes you are ok!") the Claude local session making this F30 change itself, as for Great Lakes
(`F30-great-lakes-hook.md`), overriding the one-owner rule for this change only.

**Choice.** Append `("pnw", "pnw.publish")` after Great Lakes and California in `load_snapshot`'s fixed producer list. A missing
active file is a no-op; an invalid one fails before staging. No other F30 behavior, legacy ID or matching rule changes.
F30 ownership stays with codex-local.

**Undo.** Remove the entry or `data/pnw/releases/active.json`; the snapshot returns to the previous producers.
