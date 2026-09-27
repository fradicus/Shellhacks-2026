# Overnight protocol: autonomous multi-agent spec-driven build

A project-agnostic protocol for running many coding agents on several machines with no human in the loop. The
agents open and merge their own PRs. It adapts spec-driven development (`docs/spec-driven-development.md`) as
follows:
- the human's interview, review and validation happen **before** launch
- automated gates and logged defaults replace them during the run
- parallel lanes with disjoint file ownership replace one-feature-at-a-time

**The spec is the only source of project facts.** This file never names features, paths or agents. It reads them from:

| Source | Provides |
|---|---|
| `specs/mission.md`, `specs/tech-stack.md` | What we build and with what. Load both at the start of every run. |
| `specs/roadmap.md` | Front matter: `run_start`, `lanes`, `frozen_paths`, `gates`, `stretch`. Body: phases and the feature table. |
| `specs/features/<ID>-<slug>/spec.md` | Front matter: `id, name, lane, agent, phase, depends_on, owns, cut`. Body: Plan, Requirements, Validation, Defaults. |
| `specs/decisions/` | Project-wide defaults (`000-*.md`) and per-feature decisions made during the run. |

If these files conflict with anything else in the repo (old plans, skills, READMEs), the spec wins. If this
protocol conflicts with the spec on project facts, the spec wins. On process rules, this protocol wins.

## Execution mode
Read `execution_mode` and `local_workers` from the roadmap. Paperclip runs the existing role/lane assignments. Local sessions adopt the role/lane of their allocated features. In hybrid mode, Paperclip must skip every feature assigned to a local worker. Both use the same PR claim and checks; no feature has two active owners.

Local sessions have no Paperclip heartbeat or automatic restart. While active, they can recheck pending prerequisites between tasks; if the session exits, the operator resumes it. F18 reporting happens at checkpoints in its assigned local session, or through the CEO agent in Paperclip mode.

## 1. Start of every run (every agent, every heartbeat)

1. `git fetch origin`. If `STOP` exists at the root of `origin/main`: comment "stopped" on your open PR, push nothing, and end the run.
2. If `origin/main` CI is red (`gh run list --branch main --limit 1`): don't merge anything; follow section 6.
3. Read `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md` and your current feature's spec, from `origin/main`. Don't rely on memory from earlier runs.
4. Compute elapsed time: now minus `run_start` from the roadmap front matter. Find the active gate (section 8).
5. Check your open PRs first: fix if red, finish if in progress; rebase when required under section 3.8. Then pick new work (section 2).

## 2. Picking work

- A feature is **done** when `changes/<ID>.md` exists on `origin/main`. Nothing else counts (no checkboxes, no issue states).
- A feature is **ready** when:
  - you own it under the execution-mode rules above; Paperclip also matches its named role/lane, while a local worker adopts the assigned feature's role/lane
  - every ID in `depends_on` is done
  - no open PR has a title starting `[<ID>]`
  - the active gate allows its `phase`
- Take the lowest-numbered ready feature. One implementation feature at a time per worker. Each feature runs in its own git worktree. A local F18 owner may make short reporting checkpoints in a separate worktree between implementation steps.
- No ready feature? Look for work in your lane's open issues (`contract-change`, `main-red`, bugs labeled with your lane). If there's none, leave a resume note. Paperclip can wake again on its configured heartbeat; an ended local session needs the operator to resume it. Don't invent scope.

## 3. Branch, PR, merge

1. Use a separate feature worktree: `git worktree add ../gridbridge-f09-locations -b f09-locations origin/main` (example). Open the assigned worker in that folder; never switch branches in another worker's directory. Paperclip may provision the equivalent isolated workspace.
2. Push and open a **draft** PR titled `[<ID>] <name>` right away. That draft PR is your claim. Include the runtime/session and logical role in its body, especially when both tools use one GitHub account.
3. Edit only files that match your feature's `owns` globs, plus `changes/<ID>.md`, `specs/features/<ID>-*/**` and `specs/decisions/<ID>-*.md`.
4. Commit small; messages say why. **No `Co-Authored-By` or other trailers.**
5. Run your feature's Validation section and the change-scoped checks in `specs/tech-stack.md`. Successful CI on the exact PR revision satisfies repo-wide checks without a duplicate local run. Paste results or CI links into the PR; report failing and optional checks honestly.
6. Write `changes/<ID>.md` **last** (3–8 lines: shipped, cut, known gaps). It's the done marker.
7. Mark the PR ready and run `gh pr merge --auto --squash --delete-branch`. Branch protection merges it once the required check is green and the branch is up to date.
8. Keep a checked revision stable while CI runs. Rebase when conflicts, branch protection or a known integration dependency require it: `git fetch && git rebase origin/main`, reclassify the diff, validate the new revision under `specs/tech-stack.md`, then `git push --force-with-lease`. Being behind unrelated merges alone does not require repeated rebases. Force-push only your own feature branch; never `main` or someone else's branch.
9. A feature may ship as sequential parts (`[<ID>] part 1/3`), with one open PR per feature at a time. Only the last part adds `changes/<ID>.md`.
10. Never resolve a rebase conflict in a file you don't own. Abort the rebase, open an issue labeled `conflict` for the owning lane, and wait on it.
11. Data releases carry their own receipt ([C37](decisions/C37-publication-receipts.md)): paste the expected table from `python -m common.publication` into the PR, then link the load Action's verification summary on the merged PR. Never open receipt-only PRs.

## 4. Ownership (enforced by CI)

`scripts/check_ownership.py` runs on every PR. It reads the PR title prefix and the spec front matter and fails the PR
if any changed file falls outside what's allowed:

| Title prefix | Allowed paths |
|---|---|
| `[<ID>]` | that feature's `owns` + the extras in section 3.3 |
| `[FIX-<ID>]` | same as `<ID>` |
| `[C<n>]` (contract change) | `frozen_paths` + `specs/**`; only the lane named `contract_owner` in the roadmap |
| `[REVERT-<sha>]` | exactly the files the reverted commit touched |
| `[<ID>]` where the spec has `bootstrap: true` | anything. Exactly one feature is bootstrap: it creates the skeleton, the contracts, the frozen files and CI, and every gate waits for it. |

Rules:
- `owns` and `frozen_paths` entries are **path prefixes**: a file matches an entry if its path starts with it. `web/app/pair/` covers a directory; `reports/status.md` covers one file; `tests/pipeline/test_f09_` covers every file with that prefix. No wildcards.
- `frozen_paths` (roadmap front matter) are shared files such as schemas, dependency manifests, lockfiles, the app shell, CI and scripts. After bootstrap, only `[C<n>]` PRs change them.
- No entry may be a prefix of another feature's entry or of a frozen path. `check_ownership.py --lint-specs` verifies this over all specs in CI on every PR.
- The bootstrap feature may create placeholder files inside other features' prefixes (for example, a placeholder page for every route, so the shared nav never needs editing). The owning feature then replaces them.
- **Contract change:** open an issue labeled `contract-change` naming the exact field or package and why, then keep working on something else. The contract owner ships `[C<n>]` within one run. Tonight, changes are **additive only** (new optional fields, new packages); never rename or remove.
- No shared append-only files. The changelog is one file per feature under `changes/`, decisions are one file per feature, and status reports live only in the reporting lane's `owns`.

## 5. When the spec is silent or wrong

Don't wait for a human. Resolve it in this order:
1. The feature spec's Defaults section.
2. `specs/decisions/000-*.md`.
3. The option that is smaller and reversible and keeps every rule in `mission.md` exact.

Log each choice in `specs/decisions/<ID>-<slug>.md` (context, options, choice, how to undo). If your own spec was
wrong, amend it in the same PR, so spec and code stay in sync (SDD's no-drift rule). If another feature's spec is
wrong, open an issue for its lane and don't edit it.

## 6. Keeping main green

- CI runs on every push to `main`. If it's red, nobody merges except the fix.
- The first agent to notice opens an issue labeled `main-red` that names the suspected commit.
- The owning lane gets 20 minutes to land `[FIX-<ID>]`. After that, any lane may open `[REVERT-<sha>]` (a plain `git revert`).
- Assume `main` deploys to production. Whatever is on `main` is the product.

## 7. Budgets

At 75% of an observable chosen budget, take no new feature work. In Paperclip mode configure its agent budgets; in local mode use the actual Claude/Codex account or API limits. Set Gemini application quotas/billing separately in both modes. Billing alerts and these instructions are not hard spending caps. All workers obey the elapsed-time gates.

## 8. Gates

`gates` in the roadmap front matter lists `{at: "H:MM", rule}` entries measured from `run_start`. Gate kinds this protocol understands:

| Kind | Effect |
|---|---|
| `only: [IDs]` | Only these features may run. |
| `no_new_phase: N` | Features in phase N that haven't started yet may not start. |
| `freeze` | No new `[<ID>]` branches. Only `[FIX-]`, `[REVERT-]`, and features listed in `allow`. |
| `report` | The reporting agent writes the final report and commits `STOP`. |
| `hard_stop` | Nobody runs, whether or not `STOP` has landed. |

When every feature is done or cut, only the `stretch` IDs from the roadmap may start, and only before `freeze`.
A feature with `cut: never` is never skipped because of a gate. If it's late, the other lanes keep working, and the reporting agent flags it.

## 9. Stale claims

- A draft PR with no push for 45 minutes is stale. The reporting agent comments on it.
- At 60 minutes, the reporting agent closes it and logs the decision.
- Reassign only after the old worker has stopped writing; preserve the feature role/lane and update the mode assignment if transferring between Paperclip and a local session. A closed PR alone is not permission for two workers to continue the same feature.

## 10. Reporting

The roadmap names one `reporting_agent`. Every 30 minutes, that agent merges `reports/status.md` covering:
- done and in-progress features, with PR links
- `main` red or green
- time left and cuts made
- blockers
At the `report` gate, it writes `reports/final.md`: what shipped, what was cut, the open risks, and what the human should check first in the morning.

## 11. Keep documentation aligned

When a change affects behavior or product claims, its owner updates the relevant spec and acceptance criteria
in the same PR, or opens the needed contract change for shared scope. Link the motivating evidence and decision
for substantial new requirements. Do not turn an interview suggestion into a ready feature without an explicit
scope and assignment. Potential ideas remain deferred until promoted by a decision.

Preserve dated context notes; append corrections and later answers. Supersede changed decisions explicitly.
Use the project's shared vocabulary and link volatile counts to producer artifacts or active-dataset evidence.
Status and pitch updates must distinguish merged implementation, automated checks, verified live integration
and observed user acceptance. Include the revision/time and inspect individual CI jobs, including optional failures.
Existing feature ownership applies; documentation maintenance is not permission to edit another worker's files.
