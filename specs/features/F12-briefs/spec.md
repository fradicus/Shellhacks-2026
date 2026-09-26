---
id: F12
name: Grounded Gemini coordination briefs
lane: A
agent: gemini-engineer
phase: 2
depends_on: [F10]
owns: [pipeline/briefs/, tests/pipeline/test_f12_, data/briefs/]
cut: never
---

# F12 Briefs

## Plan
1. For the top 15 matches (priority order, `future` first, then `historical`), build an input of fact objects, each with an id: both projects' names, dates, owners, statuses and descriptions (**DESC text only**; Georgia contributes names, dates and codes), plus the match's distance, gap and band.
2. Gemini structured output (schema `brief`): `supported_facts[{text, fact_ids}]`, `possible_shared_activities[]` (from: crews, equipment, freight/mobilization, matting, outage window, landowner outreach, procurement), `questions[]` (3–5, for planners), `limitations[]`.
3. **Validate:** every number in any text appears among the input facts; every `fact_id` exists; the wording rule holds (no "built at the same time", no "savings"). If validation fails, regenerate once; if it fails again, `validation: rejected` with the reasons.
4. Write `data/briefs/briefs.json` with the model id, prompt version, `input_hash` and timestamp. Invalidate a brief when its `input_hash` changes.

## Requirements
- Gemini key from env only. Cache by `input_hash`. No live calls from the web.

## Validation
- `tests/pipeline/test_f12_*.py`, offline: the validator rejects a brief containing a number not in the input, and accepts a clean one (recorded responses).
- PR body: generated / passed / rejected counts and one full example brief.

## Defaults
- Gemini unavailable: skip the generation, keep the validator and tests, and log it. The UI shows "brief unavailable".
