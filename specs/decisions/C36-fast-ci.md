# C36: proportional CI checks

The user authorized faster CI and agent validation on 2026-09-27. Issue #207 assigns
this bounded workflow/process change to Codex local in the technical-lead role;
original run gates are historical for this task. Feature ownership is unchanged.

## Contract

- A conservative Markdown allowlist determines documentation-only changes. Unknown
  paths, code, data, schemas, dependencies, tests and workflow changes run full CI.
- Spec lint, ownership, and the classifier/ownership regression tests always run.
- Keep the required `ci` status. It must fail if an applicable prerequisite fails
  or is cancelled; skipping expensive jobs for docs must not leave it pending.
- Run Python and web checks concurrently for full changes. Preserve the existing
  browser coverage and its non-blocking status. Pushes to main always run full CI.
- Successful CI on the exact PR revision satisfies repo-wide checks. Run focused
  checks locally while editing; do not repeat a successful full suite locally.
  Reclassify and check new revisions after edits/rebases. Do not repeatedly rebase
  merely because main advanced while checks run; refresh when integration requires it.
- Print the slowest pytest durations so further tuning follows measured evidence.

The allowlist and negative cases are executable in `scripts/ci_scope.py` and
`tests/golden/test_ci_scope.py`. The workflow itself uses that classifier.
No dependency or branch-protection change is required. Revert C36 to restore the
previous full-suite-on-every-PR policy.

GitHub documents that skipping an entire required workflow through path filters
can leave checks pending; classification therefore happens inside the workflow:
https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs

Temporary docs-only CI smoke check; this branch will be closed without merging.
