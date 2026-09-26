# Follow-up: a useful project-manager investigation

Status: accepted product direction from C16. Implementation gaps and live/user acceptance remain pending.
This document defines the outcome to evaluate; it does not allocate a new feature or activate deferred ideas.

## Outcome

A project manager investigates one real project, finds relevant nearby work where evidence permits, checks filed
milestones and changes, inspects uncertainty, and exports evidence and questions for a follow-up conversation.
An explicit unresolved result is valid when the evidence cannot support a candidate. Never require a successful
match merely to make the demo compelling.

## Why this outcome

- [Panel feedback](context/2026-09-26-sponsor-panel.md#adoption-and-product-development): involve actual users and
  deliver small useful tasks. Begin with an observed task rather than treating feature count as user value.
- [Demo feedback](context/2026-09-26-demo-feedback.md#project-manager-workflow): the desktop PM is the initial
  user; short-notice mobilization makes earlier visibility useful.
- [Changing information](context/2026-09-26-demo-feedback.md#changing-schedules-and-uncertainty): freshness and
  interpretable changes matter. Predictive usefulness is still a hypothesis.
- [Demo observations](context/2026-09-26-demo-feedback.md#demo-observations): retain the map/time-to-evidence path
  and verify that users can understand it without a guided explanation.

## Acceptance scenario

1. Select a real project from the current dataset. Show its source, filing/version, published status and unknowns.
2. Inspect relevant nearby work using the unchanged canonical rule where identities and centers qualify. Records
   without adequate geography remain searchable and visibly unlocated; reference geography never substitutes.
3. Read milestones with original date precision and meaning. Do not infer work windows from date proximity.
4. Inspect available comparable filing changes and their old/new evidence. Missing history is explicitly unavailable.
5. Identify location basis, effective review state and questions to resolve before contacting another team.
6. Export the supporting facts, citations and limitations through the existing card/export workflow. Missing
   capabilities are recorded as implementation gaps instead of described as delivered.

Technical acceptance checks the selected deployed revision, active legacy/national datasets where used, map/list
consistency, evidence links, effective review states and export. Exercise desktop/mobile, missing location,
partial/unknown dates, rejected candidates, absent history and unavailable services. Reuse existing checks where
they already establish the behavior. Optional AI failure must not prevent access to deterministic facts.

User acceptance requires an actual PM evaluation: record the task, outcome, assistance needed, missing evidence
and usefulness of the output. Compare with their current process if observable. No invented savings percentage,
time improvement, willingness-to-pay claim, or completion claim while that evaluation is pending.

## Work sequence and ownership

| Step | Existing owners / boundary | Completion evidence |
|---|---|---|
| Clear language and uncertainty | F05/F11/F15/F19/F31 own their views; F18 owns presentation material | The selected record makes date meaning, source, location limit and review state understandable. |
| Bounded location investigation | F09 produces, F13 independently reviews; F04/F10/F30 handle their dependent inputs/outputs | Evidence and a current decision for each inspected endpoint. A confirmation quota is prohibited. |
| Freshness and changes | F14 legacy history; F30 national source observations; F11/F31 display; shared fields require a contract | Old/new evidence where available; distinct publication/check/event meanings; failed refresh keeps the last valid dataset. |
| Assemble and evaluate PM task | F11/F31 workflow, F07 QA, F08 release, F18 reporting | Separate technical, live and user evidence against a named revision. |

The existing 14 endpoints supporting the top 15 legacy pairs are a bounded starting sample for investigation;
a PM may identify a more useful sample. The work starts only after the roadmap assigns any implementation gaps
and existing owners claim them. This documentation change does not reopen every completed feature or take paused
F08/F18 work away from its owner.

National discovery continues under C11/F30/F31. Prioritize new sources by evidence quality, date/status meaning,
update history, usable geography and relevance to the PM task. Historical/cancelled records can support research,
but must not be counted as upcoming construction. Unlocated records remain useful as searchable documents.

## Potential work: do not implement

These are product ideas for discovery, not assigned features or implicit permission to code.

| Idea | Status / why deferred | Evidence or decision needed before starting |
|---|---|---|
| Excavator/equipment availability, rental, subleasing, booking or payments | Potential. A reviewer described idle rental time; no transaction workflow was established. | A concrete customer task, permitted availability data, decision-maker responsibilities and explicit feature assignment. |
| Foreman-specific accounts, permissions or a new field app | Potential. Field simplicity is supported; exact tasks and access requirements are unresolved. | Observe a field task, identify necessary information and sharing boundaries, then scope the minimum workflow. |
| Automatic crew/equipment dispatch or emergency coordination | Potential. The conversation describes urgency, not verified schedules or operational authority. | Authorized operational inputs, a responsible operator, acceptance criteria and a separate decision. |
| Published delay probabilities or utility reliability scores | Potential. Terrain/permitting/utility effects are hypotheses. | Authorized historical actual outcomes, a time-aware evaluation and a documented release decision. Planned dates are not actual outcomes. |
| A separate civic-information product | Potential. Public exploration is useful, but the primary civic task has not been evaluated. | A distinct user and task; demonstrate value before expanding the core product promise. |

The operations research/contracts separately claimed in [issue 97](https://github.com/fradicus/Shellhacks-2026/issues/97)
retain their own authorization. A prototype for environmental evidence, route constraints or outcome evaluation
does not authorize the transactions, automatic dispatch or proven predictive claims above. F32's existing
separate prototype is governed by its own spec, not automatically promoted by this follow-up.

## Sponsor follow-up

Draft message, not sent:

> We took away that the project manager is the first user to serve, that short-notice mobilization makes earlier
> visibility valuable, and that changing information is a major difficulty. We are focusing on investigating a
> project, comparing nearby work, and producing an evidence packet. Could we walk through one recent example with
> a PM using public or permitted redacted material, and learn what information would have changed their decision?

Capture which decision was made, when information was needed, what evidence would justify contact, how often
sources need checking, and whether the useful output is a shortlist, change summary or packet. Record subsequent
answers as dated additions to the context; update the owning decision/spec when they change our direction.
