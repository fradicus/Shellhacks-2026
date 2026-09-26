---
id: F18
name: Status reports, acceptance, submission draft, STOP
lane: C
agent: ceo
phase: 4
depends_on: []
owns: [reports/status.md, reports/final.md, submission/, STOP]
cut: never
---

# F18 Status, acceptance, submission

Runs the whole night as the reporting agent (`overnight.md` §9–10).

## Plan
1. **Every 30 minutes:** `reports/status.md`, merged as `[F18] status HH:MM`. It covers done and in-progress features with PR links, `main` red or green, time left, cuts made, stale claims closed, and issues labeled `human-morning`.
2. **Stale claims** per `overnight.md` §9. Gate enforcement reminders go as PR comments, never as edits.
3. **After F10 and F11:** draft `submission/devpost.md` with these sections: Inspiration (FERC 1920, the freight anecdote), What it does, How we built it (pipeline -> Atlas -> Next.js, Gemini extraction + briefs, the agent team + spec-driven development), Challenges (the CEII decision D2, owner codes, in-service vs construction), Accomplishments (**measured numbers from `data/**/summary` and coverage only**), What's next. Also `submission/tracks.md` with the evidence for each of the four tracks (links to routes, the Atlas index list, the Gemini model id, the domain), and `submission/pitch.md` (a 2-minute script following Plan E §13, with real numbers).
4. **At the `report` gate:** write `reports/final.md` covering what shipped (with routes), what was cut, the open `human-morning` issues, the decisions to review (000 plus any per-feature ones), and the first 5 things for the human to check. Then add `STOP` and `changes/F18.md` in the same PR.

## Requirements
- Every number in `submission/` must be traceable to a committed data file or the live app. Mark anything unverified as `[unverified]`.

## Validation
- `reports/final.md` exists on main with `STOP`. Every link in `submission/tracks.md` resolves (check with curl) or is marked as not working.

## Defaults
- If the production URL is down at the report gate, say so first in `final.md`.
