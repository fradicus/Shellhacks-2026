# C57 — Restore the C56 build repair

Codex local / technical-lead owns the main-red repair in issue #323. Commit
717cd7e restored merge-conflict markers after C56 #318 had removed them.
Restore C56's exact resolution in `web/next.config.ts` and
`web/components/nav/Nav.module.css`: keep both weather JSON tracing patterns
and the existing navigation scope styles. No API, data or visual change.

Validation: diff must match these two files at 4c4ff84; spec ownership and
exact-head full CI must pass. Search frontend #320 remains blocked until this
repair merges. Do not undo unrelated weather or landing work.
