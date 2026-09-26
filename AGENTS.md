# Agent rules

This repo is built with spec-driven development by autonomous agents. The **spec is the source of truth**; chat
memory and old plans aren't.

## Every run
1. Follow `specs/overnight.md`. It's the process: picking work, branches, PRs, merging, ownership, stop switch, gates.
2. Load `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md` and your feature's `specs/features/<ID>-*/spec.md` from `origin/main`.
3. Only facts from the spec, the read-only inputs named in `specs/tech-stack.md`, and cited public sources count. Anything else (old plans, chat) is background, never authority.

## Repo-wide checks
Run every command in the **Checks** section of `specs/tech-stack.md` before marking any PR ready, and paste the results.
Then review your diff (`git diff origin/main --stat`): no secrets, no `.env`, nothing in read-only paths, nothing outside your feature's `owns`.

## Never
- Invent data (coordinates, dates, costs, owners, counts). Unknown stays null and visible.
- Commit secrets, or put a server secret in a browser-exposed variable.
- Force-push anything but your own feature branch. Edit another feature's spec. Resolve conflicts in files you don't own.
- Add `Co-Authored-By` or other trailers to commits.
- Ask a human and wait. Decide using the spec's defaults, log it, keep going.
