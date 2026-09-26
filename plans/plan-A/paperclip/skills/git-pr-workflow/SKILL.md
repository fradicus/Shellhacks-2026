---
name: git-pr-workflow
description: How Gridlock agents branch, commit, push, and open PRs against fradicus/Shellhacks-2026. Load before any git operation.
---

# Git and PR workflow

Repo: `https://github.com/fradicus/Shellhacks-2026.git`, default branch `main`. Auth: `GH_TOKEN` env (used by `gh` and git over HTTPS).

1. Work in the Paperclip execution workspace for your issue (a git worktree). If none, `git switch -c <issue-id>-<short-slug> origin/main`.
2. One issue = one branch = one PR. Keep diffs small; split if > ~400 lines excluding data files.
3. Commit messages say **why**, not what the diff shows. Mechanical changes (formatting, lockfile, regenerated `data/`) go in their own commit.
4. **No `Co-Authored-By:` or other trailers.** Strip them if tooling adds them.
5. Before pushing: run `uv run python pipeline/test_overlaps.py` and, if `web/` changed, `cd web && npm run lint && npm run build`.
6. `git push -u origin HEAD` then `gh pr create --fill --base main`, title `[#<issue>] <summary>`, body links the Paperclip issue and lists how you verified.
7. Assign the CTO as reviewer in the Paperclip issue. Never merge your own PR. Never force-push `main`.
8. Never commit `.env*` except `.env.example`. Secrets only via env.
