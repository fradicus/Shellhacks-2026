# 000: Azure DevOps test-generation pipeline

## Context

The human operator asked (2026-09-26, mid-run) for a CI/CD pipeline that automatically creates
tests for new commits, using Azure DevOps, with the OpenAI API as the generator and auto-commit
to the working branch as the delivery mode.

This conflicts with two standing rules:

- `specs/tech-stack.md` names GitHub Actions as the CI and freezes `.github/`.
- New product dependencies ship only via `[C<n>]` contract PRs, and `pipeline/pyproject.toml` is frozen.

## Options

1. **Replace GitHub Actions with Azure Pipelines.** Rejected: violates the frozen CI contract
   mid-run and would remove the required `ci` check that branch protection and the ownership
   gate depend on.
2. **Add Azure Pipelines alongside, generating tests onto feature branches.** Chosen. GitHub
   Actions stays the required PR gate; Azure adds opt-in test generation on top.
3. **Generate with Gemini (`google-genai`, already a product dependency).** Rejected for CI
   tooling: the operator specified OpenAI, and CI tooling is not product code. The generator's
   packages live in `ci/requirements.txt`, installed only in the Azure agent, never imported by
   `pipeline/` or `web/`. If the operator prefers, switching `ci/generate_tests.py` to Gemini is
   a one-file change.

## Choice

- New root files `azure-pipelines.yml` and `ci/` (generator, validator, requirements) are added
  to `frozen_paths` in this change, so a single `[C<n>]` PR can carry the whole feature.
- Generation runs only on feature branches (`fNN-*`, `codex-fNN-*`, `claude-fNN-*`,
  `features/*`); `main` gets the plain test suite only. The bot never pushes to `main`.
- Generated tests are named `tests/pipeline/test_fNN_auto_*.py`: they land inside the owning
  feature's `owns` prefix, so the ownership gate stays green on the feature's PR.
- Only `pipeline/` Python modules are generation targets. `web/` has no unit-test framework in
  the frozen lockfiles (its checks are `lint`/`typecheck`/`build`), and adding one is a separate
  contract change.
- A generated test is committed only if it passes; failures get one retry with the pytest output
  fed back, then are deleted. The commit never carries `[skip ci]`, so the GitHub PR check
  reruns on the bot commit. Azure-side loops are impossible because the trigger excludes
  `tests/**`.
- Scope: pipeline tests only. Secrets (`OPENAI_API_KEY`, `GITHUB_BOT_PAT`) live in an Azure
  DevOps variable group, never in the repo.

## How to undo

Delete `azure-pipelines.yml` and `ci/`, remove the two `frozen_paths` entries, and delete any
`tests/pipeline/test_*_auto_*.py` files. No product code, schema, or workflow is affected.
