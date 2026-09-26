# GridBridge build status

Checkpoint: 2026-09-26T17:44:07-04:00. Inspected main: `ac2c506`. Analysis date: 2026-09-26.
This is a dated checkpoint, not a live dashboard. Recheck main, individual CI jobs and the deployed dataset before presenting.

## Current result

F00–F16, F19, F30 and F31 have completion markers on main. Coverage, the Three.js time view, national source
import and the national explorer are implemented. F17 has no completion marker; F18 final acceptance and STOP
have not landed. F21 has a merged visual-system spec, with implementation still pending; F32 remains a separate prototype. Implementation completion is separate from live integration
and user-task evaluation.

The follow-up product direction is a PM investigating one real project, checking nearby work and changes,
inspecting uncertainty, and exporting evidence for a conversation. The sponsor notes, acceptance scenario,
shared vocabulary and deferred-work register are in [C16 / PR99](https://github.com/fradicus/Shellhacks-2026/pull/99).
This documentation checkpoint does not start the potential equipment-rental/subleasing or field-account product.

## Delivery and verification

| Area | Evidence at this checkpoint | Remaining limitation |
|---|---|---|
| Required main checks | [Run 36273811311](https://github.com/fradicus/Shellhacks-2026/actions/runs/36273811311): Ruff, 342 pipeline tests, web lint/typecheck/build, nine national module checks and spec lint passed | Main's optional browser job failed; workflow-level success is not an all-checks-green claim. |
| Browser checks | Four national browser cases passed; legacy suite: 17 passed, one failed | Time-view mobile heading tracked in [issue88](https://github.com/fradicus/Shellhacks-2026/issues/88). [PR96](https://github.com/fradicus/Shellhacks-2026/pull/96) has successful ci/e2e on its own head but is not merged at this checkpoint. |
| Legacy source/location audit | [Audit](audit/summary.md): effective pair states 15 rejected, four needs review, zero confirmed | Project-area identity remains insufficient for confirmation. Correct distance arithmetic does not establish the identity of the locations. |
| Gemini extraction on main | [Evaluation](../data/extraction/eval.json): zero processed responses/calls and null model/accuracy | No main extraction result should be presented as a live model evaluation. |
| Gemini briefs on main | [Summary](../data/briefs/summary.json): zero calls/generated briefs | [PR91](https://github.com/fradicus/Shellhacks-2026/pull/91) reports a real 15-call/15-pass run on its branch. This is pending PR evidence, not delivered-main or deployed evidence. |
| Atlas, deployment and domain | [Release log](../release/deploys.md) does not yet establish production acceptance; [issue10](https://github.com/fradicus/Shellhacks-2026/issues/10) remains open | Account setup, local MongoDB checks and green validation-only workflows do not establish a live deployed read path. |
| User evaluation | Sponsor conversations show interest and guided comprehension | An observed PM task, independent completion and measured usefulness are pending. |

## Data coverage

The legacy corpus has 299 filing versions and 262 active projects. It contains 400 endpoint records, 89 accepted
by the location pipeline at medium confidence, and 79 calculated project centers. Independent review can further
restrict their use. [Location coverage](../data/locations/coverage.json), [match summary](../data/matches/summary.json).

The 19 legacy candidates comprise 16 historical and three tentative pairs, with zero future pairs. Their effective
audit states are 15 rejected and four needing review. None is a confirmed coordination opportunity. The 12-card
DESC spot check found 108/108 agreement across the selected non-location fields; it is neither corpus nor Gemini
accuracy. [Spot check](audit/extraction_check.md).

The separate national explorer imports 1,286 records: 1,024 ISO-NE rows and 262 current legacy projects. ISO-NE
includes 643 in-service and 335 cancelled records; the total is not an upcoming-project count. The explorer exposes
69 needs-review points and leaves 1,217 records without displayed locations. Every current county assignment is
unknown. Catalogue/reference geography does not imply complete US project coverage. [National coverage](../data/national/coverage.json),
[national data notes](../data/national/README.md), [F31 delivery](../changes/F31.md).

## Open work and ownership

At this checkpoint:

- [PR91](https://github.com/fradicus/Shellhacks-2026/pull/91): F12 live-brief fixes and branch results.
- [PR92](https://github.com/fradicus/Shellhacks-2026/pull/92): C13 optional Azure test-generation infrastructure.
- [PR93](https://github.com/fradicus/Shellhacks-2026/pull/93), [PR94](https://github.com/fradicus/Shellhacks-2026/pull/94),
  [PR95](https://github.com/fradicus/Shellhacks-2026/pull/95): C14 contracts, F06 embedding loader and F20 semantic search.
  Their proposed Gemini configuration does not change main's delivered configuration until the contracts land.
- [PR96](https://github.com/fradicus/Shellhacks-2026/pull/96): F19 mobile accessibility fix.
- [PR89](https://github.com/fradicus/Shellhacks-2026/pull/89): F32 separate optional app-controls prototype.
- [PR102](https://github.com/fradicus/Shellhacks-2026/pull/102), tracked in [issue97](https://github.com/fradicus/Shellhacks-2026/issues/97): another coordinator's C15 operations contracts.
  Its independently authorized scope remains separate from the sponsor-feedback documentation and deferred product ideas.
- [PR101](https://github.com/fradicus/Shellhacks-2026/pull/101) merged the F21 visual-system spec; its foundation
  implementation is separately claimed in [PR103](https://github.com/fradicus/Shellhacks-2026/pull/103). A merged spec
  does not establish that the visual redesign is delivered.
- [PR99](https://github.com/fradicus/Shellhacks-2026/pull/99) and this [PR100](https://github.com/fradicus/Shellhacks-2026/pull/100):
  bounded Mac documentation integration under [issue98](https://github.com/fradicus/Shellhacks-2026/issues/98).
- [PR78](https://github.com/fradicus/Shellhacks-2026/pull/78) and [PR77](https://github.com/fradicus/Shellhacks-2026/pull/77):
  old release/final-acceptance drafts remain paused under C11. This checkpoint does not take over their implementation.

The original 04:45–12:45 run gates are historical. C11's explicitly authorized national follow-on and later bounded
assignments have their own scope; no new run or STOP is inferred from a reporting update.

## Next acceptance evidence

Resolve the current browser failure through its owner; finish verification of the configured live data path; use the
PM scenario to identify bounded evidence/workflow gaps; and observe a real PM doing the task. Use separate statuses
for merged implementation, automated checks, live integration and user evaluation. Refresh this report and the
pitch from the selected dataset/revision when any of those claims changes. This checkpoint does not submit the project.
