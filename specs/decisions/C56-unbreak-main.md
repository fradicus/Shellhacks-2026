# C56 Unbreak main after more_weather_final (2026-09-27)

Twice today a direct push to main committed unresolved stash-conflict markers into two frozen files:
`8ee00f5 weather_final` (fixed by #318) and `717cd7e more_weather_final` (this change). Each time lint, typecheck,
the fixture build and e2e failed for main and every PR based on it.

Resolution: main's side of both conflicts, which restores `web/next.config.ts` and
`web/components/nav/Nav.module.css` byte-for-byte to their state after #318. No other change.

Frozen paths change only through `[C<n>]` PRs (`specs/overnight.md`). Prevention is procedural: resolve a
`git stash pop` conflict before committing, or run `npm run typecheck` before pushing to main.
