# C32: History in the navigation, F37 to claude-local

Date: 2026-09-27. Requested by the user in a local Claude Code session ("implement the frontend redesign for history").

## Decision

- Add `{ href: "/history", label: "History" }` to the frozen nav `ROUTES`, right after Overlaps, its sibling. C19
  reserved the History nav item for the contract owner.
- Reassign F37 from codex-local to claude-local in `local_workers`. No F37 branch or PR existed, so no feature has two
  owners.
- The shared-scene contract C19 anticipated is not needed for part 1: F37 imports F19's pure time math and keeps its
  own layer in its own paths, editing no F19 file (see `specs/decisions/F37-history-part-1.md`).

## Undo

Remove the one `ROUTES` line and move F37 back in `local_workers`. `/history` keeps working by URL.
