# C58: Overlaps story (F53)

Recorded 2026-09-27. The user asked Claude local to redesign the `/time` story as the main live demo and the
source footage for the submission video. This contract adds [F53](../features/F53-overlaps-story/spec.md) and
assigns it to claude-local. Code ships as `[FIX-F19]` PRs, the same way F52's did.

## Evidence (read from `main` at 568fcc5)
- The story (`web/components/time/TimeView.tsx`, `story`/`goStep`) has four steps on a fixed 7 s timer. Its first
  caption, "N utility projects from public filings", dates from the two-utility build.
- Its opening replays `sweepIn`, which grows every pillar nationwide at once in date order. Geography plays no
  part in the reveal.
- Its pair steps read `visible[0]` and the widest gap. In candidate mode that's the first loaded page, and if the
  page hasn't loaded yet, the pair steps are missing.
- It never shows scope, the pin, candidate search or the scrubber, all of which shipped after it.

## Choices
- **3D from the first frame, revealed geographically.** The user rejected a top-down opening: the rising pillars
  are the strongest asset, so they rise from frame one. A longitude reveal gives a clear direction of travel that
  a date-order sweep doesn't.
- **East to west.** The user's choice. Sunrise crosses the country that way. The dense Eastern Interconnection
  also fills the screen in the first second.
- **Cinema mode during the story.** A recording with panels over a third of the frame reads as a UI tour, not a
  film. The panels come back the moment the story stops.
- **No hard-coded numbers in captions.** Every count and name comes from the drawn data. The film stays true as
  datasets change.
- **Nation → region → state → one good pair → one bad pair → back out.** This was the user's arc: a story with a
  finding, not a tour of features. It runs about 35 s.
- **North Dakota, not South Carolina or Florida.** Measured against the live candidate API at dataset `489d9c2`:
  only 17 of 1,352 candidates have a known day gap (9 in ND, 5 in SC, 3 in SD). Florida has 93 candidates and none
  with a gap. 40 of its 51 paired projects have no date, so in 3D it would be mostly flat. South Carolina's
  largest-gap pair (Columbia Canal ↔ Sandy Run, "2,359 days") uses a Santee Cooper record dated 2019. That record
  was last listed in a 2019 deck, and the source says this is not evidence of completion. Its date also falls
  before the axis ground, so the gap can't be drawn. In Williston, ND, one project has a partner of another
  owner 1 day apart and a partner 6.47 mi away but 1,157 days apart. That contrast is the product's argument.
- **Pair view fit.** At 1920 × 1080, the contrast pair's 2030 pillar and gap label ran off the top of the frame
  because the axis fit 75% of the canvas height regardless of where the ground sat. F53 fixes it for every pair.
- **Rejected:** hopping region by region, which is choppy and slower. Animating the pin, which only means something
  when a person clicks. A top-down opening.
