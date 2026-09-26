---
name: "git-delivery"
description: "Deliver reviewable changes within Plan E using owned paths, small diffs and explicit validation."
---

# Git delivery

## Inputs
Assigned issue, authorized build branch/worktree, ownership table and base revision.

## Procedure
1. Inspect status and existing changes before editing. Preserve uncommitted work. The planning delivery forbids commits; only a later authorized build may use a commit/PR workflow.
2. Confirm the worktree actually contains the imported plan/package. Untracked files do not automatically follow a new worktree. The operator must copy them deliberately or later commit them with authorization before branching.
3. Write only owned paths under the implementation directory. The lead owns shared schemas, dependency manifests and lockfiles. Request an interface decision through the issue before competing edits, not by rewriting someone else's work.
4. Prefer a separate branch/worktree per agent. If unavailable, serialize shared-file changes and use disjoint paths. Never force-push, discard user changes, or reset unrelated files.
5. Run the checks relevant to the change: matching fixtures for math, extraction evidence for parsing, API checks for schema changes, browser flows for UI. Record failed checks as failures; do not append shell constructs that conceal them.
6. Inspect the final diff for scope, secrets, generated data and accidental source-document edits. Keep credentials and CEII out of version control. Link the diff/commit and test evidence to the issue.
7. Lead integrates after review; QA checks the integrated revision. Release deploys that accepted revision only after deployment authorization.

## Output and checks
Small reviewable diff and clear handoff. State what changed, why, what passed and what remains unverified. Do not claim a branch test proves the deployed build works.
