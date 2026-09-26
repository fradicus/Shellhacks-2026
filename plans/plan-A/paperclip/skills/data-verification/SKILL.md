---
name: data-verification
description: Verify Gridlock location matches and overlap rows against the source PDFs and the sponsor golden sample; confidence downgrades and the verification log. Use for QA of data.
---

# Data verification

## Golden test (`pipeline/test_overlaps.py`)
Build the 10 sample projects from `docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx` (sheet `projects`;
read with `openpyxl`, convert Excel serial dates). Run them through the real `overlaps.py` functions. Assert:
- exactly OVL_1..OVL_6 pairs come out, nothing else;
- `abs(distance - expected) <= 0.05` mi; time gap equal.
Plain asserts, runnable with `uv run python pipeline/test_overlaps.py`, exits non-zero on failure.

## Match verification (sponsor guide, Part 2)
For every endpoint graded `high` or `medium`:
1. Open the PDF page in `source.page`; re-read name, zone, description, landmarks.
2. Check the OSM feature: right state, plausible county for the GPC zone / DESC area, operator tag consistent.
3. Similar name in the wrong county -> downgrade to `low` or `unlocated` and say why.
Log each check to `data/verification_log.csv`: `project_id, endpoint, verdict (confirmed|downgraded), reason, checked_at`.

For every overlap in the top 20: recompute the distance by hand from the stored coordinates; confirm both dates against the PDFs.

## UI checks (live URL)
Every judge requirement visible without instructions: map with both utilities, highlighted overlaps, ranked list, one estimate card. Phone width 390px usable. No console errors. Use `webapp-testing` for Playwright checks.
