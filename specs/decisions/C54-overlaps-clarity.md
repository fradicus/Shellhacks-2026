# C54: Overlaps clarity pass (F52)

Recorded 2026-09-27. The user asked Claude local for a frontend review and then said to "own a spec and drive it".
This contract adds [F52](../features/F52-overlaps-clarity/spec.md), assigns it to claude-local, and makes the two
frozen nav edits F52 needs.

## Evidence (checked against `main` at 9548c28, 1440 × 900 headless)
- The filing pairs from `/api/matches` break down as 15 rejected (all historical), 4 needs_review (1 historical,
  3 tentative), 0 confirmed and 0 future. The filing-pair rows gave no sign of review state. The story's second
  step called rank 1 "the first call to make". That pair is rejected, and both of its dates (2026-05-31 and
  2026-06-01) are before the analysis date.
- The selected-pair figure "395" rendered under Copy link. The selected bead label rendered under the scope bar.
  The pair panel read "1 days" for a one-day gap.
- Nav still listed Project map (retired by C35) and a `DESC × GPC` chip. `/gemini` opened on "Gemini extraction
  unavailable" even though 15 stored briefs exist.

## Choices
- **Label and dim rather than hide or reorder.** The mission's rank must stay as stored. Hiding rows would change
  the numbers people cite, and a toggle is extra UI nobody has asked for yet. Undo: remove the row chip and the dim style.
- **Contract PR for the nav.** `web/components/nav/` is frozen, and C35 already said a contract PR removes the entry.
- **`/map` redirect left to F05.** Redirecting changes what the optional F07 smoke tests visit. Their owner should move
  those tests in the same change.

## Notes for other owners (not assigned)
The review also found items outside F52 that owners may take up:
- Landing (F05): the page never says "transmission". "50 States in the national view" can read as project coverage.
  Five different labels link to `/time`.
- `/explore` (F31): a light basemap and marker colors that don't match `/time`'s tier shapes. A dataset hash sits in the hero.
- `/coverage` (F15): the page is titled "Data quality" but the nav says "Coverage". Its scope is the DESC/GPC filings only.
- `/operations` (F36): the page has four names. The coordinate placeholders point to Seattle, outside every dataset.
