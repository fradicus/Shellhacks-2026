# C39: parallel pipeline pytest

The user asked for faster CI on 2026-09-27. Claude local takes this bounded
workflow/dependency change in the technical-lead role. Feature ownership is unchanged.

## Evidence

After [C36](C36-fast-ci.md), full-scope PRs wait on the `pipeline` job. In runs
36300697472 and 36301091082 pytest took 466s and 462s of a 526s/521s job; web
checks took 47s and ran alongside it. Pytest ran 626 tests serially on one core.
The slowest tests each rebuild or re-validate the national snapshot (15–36s each).

## Contract

- `pytest-xdist` joins the pipeline `dev` dependency group; `uv.lock` pins it
  (3.8.0, with `execnet` 2.1.2). The lock change adds packages only.
- The full-suite command in CI and in `specs/tech-stack.md` Checks becomes
  `uv run pytest -q -n auto --durations=10`. `-n auto` uses one worker per CPU.
- `addopts` is unchanged, so focused local runs of one file stay single-process.
- Every test must pass in any order and on any worker. A test that shares mutable
  files or global state with another test is a bug in that test's owning feature.

## Options

- `uv run --with pytest-xdist` in CI only: no manifest change, but unpinned by the
  lock and unavailable to the documented local command. Rejected.
- Share one validated snapshot across the heavy F30/F33/F39/F40/F42 tests: large
  saving, but edits five features' tests. Left to those owners; `--durations=10`
  keeps naming the slowest tests.

## Undo

Revert this PR. That removes `-n auto` and the dependency together.
