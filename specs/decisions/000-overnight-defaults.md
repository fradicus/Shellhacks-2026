# 000: Overnight defaults (read before every feature)

Plan E (`plans/plan-E/`) is the product basis, but several of its steps need a human mid-run. Tonight has no
human, so these defaults replace those steps. Each one says how to undo it in the morning. The human should
review this file first after the run.

| # | Topic | Plan E said | Tonight's default | Undo / morning check |
|---|---|---|---|---|
| D1 | Code location | `plans/plan-E/implementation/` | Repo root (`pipeline/`, `web/`, `data/`, ...) so the deploy and judges see a normal repo | none needed |
| D2 | Georgia PDF (mixed PUBLIC DISCLOSURE + CEII banner pages) | Quarantine until a human resolves | **Parse only the Ten-Year Plan table fields deterministically** (zone, year, TEAMS number, project name, need date, sponsor code) from the sponsor-supplied PDF. **Never send those pages to Gemini. Never publish page images or excerpts beyond the project name.** Cite by page number. Rationale: the sponsor supplied this file as challenge data and drew the golden sample from it; without it there's no second utility. | If Sperry says no, delete `data/projects/gpc*` and rerun; the app falls back to the golden sample in historical mode |
| D3 | Owner codes (GPC / SAV / GTC / MEAG ...) | Verify from a legend or official record | Map a code only with a citation (a legend page in the PDF or a public official source). `SAV` -> Georgia Power **only** with a citation (Savannah Electric merged into Georgia Power; cite a public source). No citation -> `unknown`: shown, but excluded from two-utility matching | Review `data/owners/` |
| D4 | Atlas network access | Fixed-egress host, no `0.0.0.0/0` | Human sets `0.0.0.0/0` in pre-flight, with **separate users**: RW (GitHub Actions secret only) and RO (Vercel + machines). Random 32+ character passwords | Move to a fixed-egress host after the event |
| D5 | Deploy authorization | Human approves releases | `main` auto-deploys to Vercel production; `main` must stay green (`overnight.md` §6) | Roll back in Vercel if needed |
| D6 | QA sign-off | Blocks release | CI (golden, tests, build, ownership) blocks merges. QA audits **after** merge (F07, F13) and files `[FIX-]` issues. Featured pairs need QA's `confirmed` before the UI marks them "reviewed" | none |
| D7 | Brief regeneration | Operator-token protected route | **No mutation routes at all.** Briefs are generated in the pipeline (F12), committed to `data/briefs/`, loaded by CI. No `OPERATOR_API_TOKEN` | none |
| D8 | Review decisions | `reviews` collection | Append-only JSON files per producing feature (`data/review/<area>/`), loaded to Atlas `reviews` | none |
| D9 | Extraction evaluation | 12 hand-labeled rows | Gemini's DESC extraction is compared field by field against the deterministic DESC parse on **all** cards, plus 12 cards QA checks by reading the page. Report both, with denominators | none |
| D10 | Schedule | 36 hours, R0–R4 | 8 hours, phases 0–4. E's R3 (third utility) and R4 are out of scope. E's scenario drawer = F17 stretch | none |
| D11 | Geocoding | Official maps + OSM, no automated Nominatim | Same. OSM Overpass bulk pulls, cached. No Nominatim automation. Gemini never asserts coordinates | none |
| D12 | Timeline-only matches | Excluded | Excluded. Geography alone decides overlap (mission rules) | none |
| D13 | Machines unknown | none | 3 lanes (A data, B app, C quality) from the roadmap front matter; the machine mapping is filled in at launch (`preflight.md` §6) | none |
| D14 | Model ids | Pick an available stable model | Gemini: the `GEMINI_MODEL` env value set in pre-flight. Claude agents: whatever each machine's adapter is configured with. Record both in the PR body | none |
| D15 | Other regional sources | none | **Don't ingest** the 2026 SERTP preliminary expansion report: it's labeled Non-CEII but its text carries CEII headings (found by Plan E's review). Only the sources in F01's manifest are ingested tonight | Revisit after the sponsor clarifies |

## Ambiguity rules (when neither the spec nor this table covers it)
1. Keep every mission rule exact.
2. Prefer showing "unknown / needs review" over guessing.
3. Prefer the smaller change that another agent can undo.
4. Prefer deterministic code over a model call; a model call over manual guessing.
5. Log it: `specs/decisions/<ID>-<slug>.md`.
