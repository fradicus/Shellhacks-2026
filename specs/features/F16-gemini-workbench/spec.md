---
id: F16
name: Gemini workbench
lane: B
agent: frontend-engineer
phase: 3
depends_on: [F03, F06]
owns: [web/app/gemini/, web/components/gemini/]
cut: allowed
---

# F16 Gemini workbench

The judge-facing proof for the Gemini track.

## Plan
1. `/gemini`: pick a DESC source and a page. Show three columns: the source page text (DESC only, D2), Gemini's structured fields with their quotes, and the deterministic parse. Mark each field match, mismatch or missing, and show `accepted` / rejected with the reason.
2. A summary strip: the model id, prompt version, pages processed, and per-field accuracy with denominators (from `getExtractions` / coverage).
3. A "Briefs" tab: the list of generated briefs with validation passed/rejected and the reasons; clicking one opens `/pair/[id]`.

## Validation
- lint, typecheck, build; a fixture or dev screenshot. If F03 data is unavailable, the page shows its unavailable state.

## Defaults
- The page text comes from the `extraction` record (a stored excerpt), not from re-reading PDFs at runtime.
