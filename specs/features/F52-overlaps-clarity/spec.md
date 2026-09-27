---
id: F52
name: Overlaps clarity pass
lane: B
agent: frontend-engineer
phase: 7
depends_on: [F19, F21]
owns: []
cut: allowed
---

# F52 Overlaps clarity pass

Added by the user on 2026-09-27 after a frontend review of `main` (the review's findings are summarized in
[C54](../../decisions/C54-overlaps-clarity.md)). The Overlaps view ranks audit-rejected filing pairs without saying
so. Its story tour calls a rejected, already-in-service pair "the first call to make", and a few layout bugs
hide the numbers judges read first. F52 fixes what the review found that is still true on `main`. Like F21,
F52 owns no code: each requirement ships as a `[FIX-<ID>]` PR in the owning feature's paths, or in this
contract PR for frozen shared files.

## Requirements

| # | Where | Owner PR | Requirement |
|---|---|---|---|
| 1 | Nav | C54 | Remove the Project map entry. C35 retired `/map`, and this is the nav step C35 assigns to a contract PR. The route itself stays with F05 and issue #193. |
| 2 | Nav | C54 | Remove the `DESC × GPC` chip. `/time` now draws national projects, so the chip misstates the scope on every page. |
| 3 | `/time` filing-pair rows | FIX-F19 | Each row names its effective review state in text: Needs review, Confirmed by audit or Rejected by audit. Rejected rows are visibly dimmed. The stored rank, order and row numbers do not change (`nearby-band-v1`). |
| 4 | `/time` story | FIX-F19 | A pair step's closing line follows its stored state. "The first call to make" appears only for a filing pair that isn't rejected and whose view is `future`. Otherwise the line says which fact applies: provisional candidate, rejected by audit, or at least one project already in service. |
| 5 | `/time` selected pair | FIX-F19 | The distance and day-gap figures never sit under Copy link or the close button, at any digit count. A one-day gap reads "day", not "days". Visible copy uses US spelling ("center to center", "neighborhood"). |
| 6 | `/time` 3D labels | FIX-F19 | Selected-bead and hover labels stay below the scope bar, as they already stay between the side panels. |
| 7 | `/time` copy | FIX-F19 | "Legacy unlocated" reads "Not located". The Projects drawer note says in plain words what the list holds. The "Legacy pairs" tab label stays, because the candidate e2e test selects it by name. |
| 8 | `/gemini` | FIX-F16 | When no stored extraction output exists, the page opens on Briefs, and the unavailable notice stays on the Extraction tab. Decision and feature codes (D2, F01, F12) leave visible text; they may stay in `title` attributes. |

## Not in F52
- The `/map` redirect and deleting the retired map/list components remain F05's issue #193. The optional e2e smoke
  suite (F07) still exercises `/map`, so the redirect needs that owner's test update.
- Pair-page CSV and review wording: FIX-F11 #302 is already doing this.
- Landing, `/explore`, `/history`, `/operations`: the review's notes are recorded in C54 for their owners.
- Duplicate-looking national candidate rows (same two names, different project keys) are F48 data. The row
  `title` already carries both keys.

## Requirements carried from the mission
- Display only. No data, API, schema, ranking or pair-eligibility change. Review state never reorders pairs.
- Unknown stays visible. No text may imply that a candidate or rejected pair is a confirmed overlap.
- Accessible names used by existing tests stay unchanged (see 7). Color never carries review state alone.

## Validation
- Per PR, the change-scoped Checks in `specs/tech-stack.md`.
- For `/time` PRs: check a selected rejected filing pair and the candidate list at 1440 × 900, and the list at
  390 px, in a real browser against the active dataset. Describe what was seen in the PR.
- `/gemini`: check the default tab against the committed (empty) extraction data, and describe it the same way.

## Defaults
- Rejected rows stay in the list, dimmed and labeled. A hide toggle is not part of F52; add one only if the user asks.
- If a `/time` PR conflicts with an open FIX-F19 PR, rebase onto whichever merges first. Keep F52's edits
  small and local so the other author's rebase stays simple.
- The last part adds `changes/F52.md` in an `[F52]` PR that touches only F52's own spec, decision and change files.
