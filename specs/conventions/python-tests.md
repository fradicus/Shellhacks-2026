# Conventions: generated pytest tests (pipeline)

These conventions are injected into every test-generation prompt (`ci/generate_tests.py`). They are
distilled from the existing suite (`tests/pipeline/test_f01_desc.py`, `test_f06_load.py`) and
`specs/tech-stack.md`. Human-written tests follow them too.

## Framework and layout

- `pytest`, plain test functions. Never test classes, never `unittest`.
- Test files live at the repo root under `tests/pipeline/`, named `test_fNN_*.py` where `NN` is the
  owning feature. Auto-generated files are named `test_fNN_auto_<module>.py`.
- Tests run from `pipeline/` (`uv run pytest`), which puts `pipeline/` on `sys.path`: import pipeline
  packages as **top-level modules**, e.g. `from common.schema import validate`,
  `from extract_desc.parser import build_outputs`. Never `from pipeline.extract_desc import ...`.
- `--import-mode=importlib` is set; no `__init__.py` games, no relative imports in test files.

## Style

- Start the file with `from __future__ import annotations`.
- Ruff-clean: line-length 130, rules `E, F, W, I, B, UP`. Imports sorted stdlib / third-party / local.
- Helper functions are prefixed `_` and return values, not assertions.
- Test names describe behavior: `test_full_rerun_is_byte_identical`, not `test_parser_1`.
- One behavior per test function; several focused asserts are fine.

## Data and determinism

- **Never invent data** (mission rule): no made-up coordinates, dates, costs, owners, or counts.
  Unknown stays `None` and the test asserts it is `None`.
- No network, no OSM Overpass, no Gemini calls, no MongoDB Atlas. Use `mongomock` for `pymongo`,
  monkeypatch module-level clients, or build the small dict the function actually consumes.
- Deterministic: fixed inputs, no wall-clock dependence. Where outputs are written, a second run must
  be byte-identical (compare `hashlib.sha256` digests, see `test_f01_desc.py`).
- Use `tmp_path` for any filesystem writes. Never write into `data/` — it is committed, reviewable
  product data.
- Read committed fixtures under `data/fixtures/` read-only.

## Domain rules worth asserting (from `specs/mission.md`)

- Project center = arithmetic mean of the two located endpoints; one located endpoint -> that point;
  none -> no center.
- Overlap = different utilities AND both centers known AND haversine (R = 3958.8 mi) < 25 miles.
  Exactly 25 is **not** an overlap. Classify on unrounded values; round to 2 dp for display only.
- Time gap = exact-date difference in days; missing/imprecise dates -> `None`, never imputed.
- Priority `nearby-band-v1`: band 0 (< 10 mi) before band 1 (10-25 mi), then exact gap ascending
  (unknown last), then unrounded distance, then canonical pair id.

## What a generated test must do

- Exercise the changed module's public functions with small, hand-built inputs.
- Validate any emitted record against its JSON Schema via `common.schema.validate` when a schema exists.
- Assert `None`/unknown behavior explicitly for missing inputs.
- Pass on the first CI run, offline, with no secrets.
