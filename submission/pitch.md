# Project-manager workflow pitch — draft

About two minutes; timing remains unverified until rehearsed. Before presenting, check the selected revision and
active dataset against [status](../reports/status.md) and [release evidence](../release/deploys.md). Use the actual
mode label: sponsor sample, local snapshot, or verified live dataset. This script does not establish deployment.

## Spoken flow

“GridBridge helps project managers investigate nearby transmission work before starting a coordination conversation.
Utilities and regional planners publish project information separately. The contractor still has to find the
relevant records, understand their dates, and check whether the locations and project identities are right.

Our sponsor conversations made the operational problem clearer: a job can wait for approval and then need crews
and equipment at very short notice. Earlier visibility is useful, but it has to come with evidence and uncertainty.

Here is the time view. Height represents the filed in-service milestone, preserving the source's date precision.
It helps explain geographic proximity and separation in time. It does not tell us when construction happens.

Select this candidate and open its evidence. The card shows the stored distance and date gap, source references,
location basis and review state. Nearby projects with close milestones are leads to investigate; they are not
proof that equipment or crews can be shared.

The filing-change view preserves earlier statements, so we can explain a changed milestone when comparable
versions are available. The national explorer adds searchable regional planning records and reference geography,
while showing where project locations and coverage are missing.

We want a PM to leave with a useful evidence packet: what the sources say, what remains uncertain, and what to ask
before contacting the neighboring project team. Our next acceptance step is observing that workflow on a real project.

What would you check first before deciding this candidate is worth a conversation?”

## Evidence to have ready

- Pick and rehearse one pair; identify sample versus real data and show its actual effective review state.
- The legacy [audit](../reports/audit/summary.md) confirms no pairs. Do not call a rejected pair an actionable opportunity.
- If explaining scale, take numbers from [legacy coverage](../data/locations/coverage.json) and
  [national coverage](../data/national/coverage.json), with their different denominators and statuses.
- Show Gemini output only when the selected revision and dataset actually contain it. Pending PR91 reports do not
  establish what the demo serves. [Main extraction](../data/extraction/eval.json), [main brief summary](../data/briefs/summary.json).
- Keep a table/evidence route available if the 3D view fails. The mobile-heading issue is tracked in the status report.

## Expansion answer — optional

“We can extend discovery source by source, preserving each source's meaning, update history and location evidence.
The national explorer already separates imported records from reference geography. We will measure useful coverage
and validate the PM workflow as we expand. Equipment rental/subleasing, automatic dispatch and predictive claims
are potential later work requiring separate evidence and decisions.”

The accepted context integration and potential-work register are in [C16 / PR99](https://github.com/fradicus/Shellhacks-2026/pull/99).
