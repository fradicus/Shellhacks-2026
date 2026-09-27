# F30: Append the fixed Great Lakes release

**Context.** C26 routes F40's Great Lakes release through the C29 fixed-release pattern. Issue #153 asked F30's owner
(codex-local) for the one-entry hook; it was unanswered, and on 2026-09-27 the user explicitly told the Claude local
session to make the F30 change itself, overriding the one-owner rule for this change only.

**Choice.** Append `("greatlakes", "greatlakes.publish")` after Mid-Atlantic in `load_snapshot`'s fixed producer list.
A missing `data/greatlakes/releases/active.json` is a no-op; an invalid one fails before staging. No other F30 behavior,
legacy ID or matching rule changes. F30 ownership stays with codex-local; the concurrent Texas entry (#185) is
independent; Great Lakes runs after the Texas entry that merged first (#185).

**Undo.** Remove the entry or the Great Lakes active release file; the snapshot returns to the previous producers.
