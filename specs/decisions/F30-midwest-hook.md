# F30: Append the fixed Midwest release

**Context.** C43 routes F46's Midwest release (`data/midwest/releases/active.json`, `midwest.publish.apply_release`)
through the same fixed-release pattern as California, the Pacific Northwest and the Southwest. On 2026-09-27 the user
told this Claude local session to do the Midwest ("let's do the Midwest", then "alright lets do this!"); the release
reaches the map only through this one-entry hook, as for the Southwest (`F30-southwest-hook.md`). F30 ownership
otherwise stays with codex-local.

**Choice.** Append `("midwest", "midwest.publish")` after the Southwest in `load_snapshot`'s fixed producer list. Its
IDs and sources are new and it reads no other producer's output. A missing active file is a no-op; an invalid one
fails before staging. No other F30 behavior changes.

**Undo.** Remove the entry or `data/midwest/releases/active.json`.
