---
id: F53
name: Overlaps story
lane: B
agent: frontend-engineer
phase: 7
depends_on: [F19, F52]
owns: []
cut: allowed
---

# F53 Overlaps story

Added by the user on 2026-09-27 ([C58](../../decisions/C58-overlaps-story.md)). The `/time` story ("Play the
story", booth mode) still tells the two-utility version of the product: four fixed 7-second steps, a sweep that
lifts every pillar at once in date order, and none of scope, candidates or the scrubber. It is the main live demo
and the source footage for the video, so F53 replaces it with a 35-second film of the national map. Like F52, F53
owns no code. It ships as `[FIX-F19]` PRs in F19's paths.

## The film

One arc: **the country wakes up, then we find one call worth making and one that isn't.** A dawn line crosses the
map from the Atlantic to the Pacific, the way sunrise does, and every project rises to its filed in-service date as
the line passes it. The camera narrows from the nation to a region, then to a state, picks the state's best-timed
pair and reads its evidence. Next it shows a pair that is closer on the ground but years apart in time, and then
it pulls back out.

| # | Beat | Time | Camera and motion | Caption (kicker · line) |
|---|---|---|---|---|
| 1 | Nation | 7 s | National overview at a 50° tilt, orbiting slowly from bearing −16° to +4°. The dawn line crosses the country in 6.5 s. Each pillar grows from the ground to its date over 0.9 s once the line reaches it, and its bead flashes. | `<N> planned grid projects` (live count while rising) · "Each rises to its filed in-service date. The glass is today." |
| 2 | Region | 4 s | Scope arrival (F19 item 18) to the story state's Census region. The region rises in date order. | `<Region> · <n> projects` · "Narrow to a region, a state, a grid plan, or 25 miles around a pin." |
| 3 | State | 4 s | Scope arrival to the story state | `<State> · <n> projects` · "Projects under 25 straight-line miles apart become candidate pairs." |
| 4 | The pair | 5 s | The pair view's side-on flight (66°), rings and the day-gap dimension | Kicker from the gap ("Same week" ≤ 7 d, "Same month" ≤ 31 d, else "Best timing here") · stored distance and gap · both names |
| 5 | Evidence | 5 s | The camera holds. The pair panel slides in. | `The evidence` · both owners and their filing (one filing when they share it), then the F52 verdict line |
| 6 | Bad timing | 6 s | Side-on flight to the contrast pair; its dimension stretches | "Closer, but not sooner" (closer than the pair) or "Near, but not together" · stored distance and gap, plus the stored status when it records a delay · both names |
| 7 | Scale out | 4 s | Overview flight back to the nation, then the quiet settle (F19 item 25) | `Every number traces to a public filing` · "Search a project, or drop a pin." |

**Story state: North Dakota** (FIPS 38). The code names only that state, the same thing a `?scope=state:38` link
names. Everything else is picked by rule from the state's candidate pairs:
- **The pair:** the smallest non-null `time_gap_days`, then the shorter distance, then the pair id.
- **The contrast:** a pair that shares a project with the pair and is closer on the ground, with the largest gap.
  Ties go to the shorter distance, then the pair id. If there's no closer one, take the largest gap among pairs
  sharing a project. If neither exists, skip beat 6.
- If the story state has no pair with a known gap, use the state with the most such pairs among the loaded
  candidates. If there is none, skip beats 4–6.

On the dataset at `489d9c2`, the rule picks a Williston 115 kV terminal upgrade (WAPA, Sep 30, 2027) and a Wheelock
project (BEPC, Oct 1, 2027): 23.86 mi apart and 1 day apart in service. The contrast is Patent Gate–Pioneer
345 kV (BEPC, Nov 30, 2030, filed "Delay – Mitigation"): 6.47 mi from Williston and 1,157 days apart. South
Carolina was considered first and rejected ([C58](../../decisions/C58-overlaps-story.md)).

Captions are built from drawn and stored values only. No count, name, date or status is written into the copy.

## Requirements

1. **Dawn reveal in the layer.** `timeLayer` gains `dawnIn(ms)`: a reveal meridian moves from the easternmost
   drawn project to the westernmost (ease in-out). A project grows to its date over 0.9 s from the moment the line
   reaches it, with its bead riding the top and flashing on arrival. Projects not yet reached draw nothing, not even
   a ground ring. The line is a thin, warm ground line (`#ffd9a0`) with a soft glow, spanning the drawn data's
   latitudes and fading at both ends. It fades out after reaching the west edge. It is a mark, not a fill: the
   basemap is never tinted. The date-order `sweepIn` stays as it is for scope arrivals.
2. **Beats, not ticks.** Each beat has its own duration and an enter action. The fixed 7 s timer goes. Beat 4 waits
   for the story state's candidate page for up to 3 s. If the page doesn't arrive, the story skips to beat 7. The
   progress bar shows one segment per beat.
3. **Cinema mode.** While the story plays, the left column, the dock and the scope bar fade out (0.5 s), and the
   caption becomes a lower-third title card. The pair panel stays hidden during beat 4, then slides in for beats 5
   and 6: it is the evidence. Everything returns when the story stops or ends. The visually hidden status line
   keeps announcing each beat.
4. **The pair view fits its pillars.** With a pair selected, the time axis fits the room above the pair's ground
   line, so both beads and the dimension label stay on screen at 1920 × 1080 and 1440 × 900. A 2030 pillar in the
   pair view no longer runs off the top of the frame. This is a fix to the normal pair view, not only the story.
5. **Stopping.** The Play button, Esc, or any input in booth mode stops the story at once. The view goes back to
   the national overview with no scope, no pair and the glass at today. The story never leaves a person inside
   a scope it picked.
6. **Booth mode (F19 item 10).** Loops this story with a 1.5 s pause between loops. The "Presenting" chip stays.
7. **`?story` link.** `/time?story` plays the story once when the map is ready. This is the demo and recording link.
   It overrides `?pair` and `?scope`. The URL loses `?story` when the story stops, so a reload doesn't replay it.
8. **Reduced motion.** Same beats, captions and durations. Every beat shows its end state at once: everything
   risen, no line, no orbit.
9. **Frame budget.** No sustained drop below 50 fps at 1920 × 1080 in Chrome on the demo laptop (F19's target).
   Rebuilding the buffers every frame during the dawn is acceptable at the current drawn count (about 3.4k); move
   the reveal to a shader uniform if that target fails.

## Requirements carried from the mission
- Display only. No change to data, API, schema, pairs, distances, gaps, ranks, tiers or pair eligibility.
- Both pairs are candidates, and the evidence caption says "A provisional lead to check, not a confirmed overlap" (F52 item 4).
  Nothing in the film implies a confirmed overlap.
- Accessible names used by existing tests stay the same ("Play the story", "Stop the story", the tab labels).

## Validation
- Change-scoped checks in `specs/tech-stack.md`.
- In Chrome at 1920 × 1080 on live data, record `/time?story` from start to end. Attach frames from mid-dawn,
  the state, the pair, the evidence and the contrast, and state the measured fps.
- The contrast pair selected directly from the list, outside the story: both beads and the gap label are on
  screen (requirement 4).
- At 390 px: the story plays and the title card doesn't cover the pair's beads.
- Stop the story mid-beat 5, and separately let booth mode loop: in both cases the view returns to the clean
  national overview.
- Reduced motion (DevTools emulation): the beats advance and nothing animates.

## Defaults
- Dawn runs east to west. The user chose it because sunrise does too.
- The story always reads nearby candidates. It switches the list to candidate mode for its duration.
- A pause or scrub-by-beat control is not part of F53. Add one only if the user asks.
- If a `/time` PR conflicts with an open FIX-F19 PR (the drive-rule drafts #281, #300), rebase onto whichever
  merges first. If the pair view draws a stored road route by then, beat 3 shows the route with no extra
  work.
- The last part adds `changes/F53.md` in an `[F53]` PR that touches only F53's own spec, decision and change
  files.
