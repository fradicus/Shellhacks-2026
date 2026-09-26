# Product context

Start with the [mission](../mission.md) for current product direction and the [roadmap](../roadmap.md) for authorized
work. These dated notes explain what informed decisions. They do not grant implementation permission.

## Conversations

| Date and setting | Notes | Main observations | Decision and open questions |
|---|---|---|---|
| 2026-09-26, sponsor panel | [Panel notes](2026-09-26-sponsor-panel.md) | Data preparation, field adoption, small useful iterations, production reliability | [C16](../decisions/C16-sponsor-context.md): evaluate a bounded PM task. Which PM and project can support that evaluation? |
| 2026-09-26, prototype reviews | [Demo feedback](2026-09-26-demo-feedback.md) | Desktop PM priority, short-notice mobilization, clear time display, changing information | [PM follow-up](../followup.md): inspect evidence and changes before contacting another team. Which information changes the decision? |

The two notes consolidate the team's local `docs/context/context-1.md` and `context-2.md` notes. This directory is
the committed reference for this feedback. Sponsor input originals under `docs/` remain read-only. Do not maintain
a second evolving copy of these notes elsewhere in the repo.

## Decisions and further investigation

- **Accepted direction:** PM investigation, source traceability, explicit uncertainty, a usable evidence handoff,
  and coverage that reflects the data actually imported. See [C16](../decisions/C16-sponsor-context.md).
- **Acceptance pending:** a deployed end-to-end PM task and observed evaluation with a real user. A positive guided
  demo is evidence of interest, not proof of independent task success or measured savings.
- **Potential—do not implement:** equipment rental/subleasing transactions, automatic dispatch, a new field-account
  product, and unsupported predictive claims. See the [potential-work register](../followup.md#potential-work-do-not-implement).
- **Separate existing scope:** C11/F30/F31 and F32 keep their own authorization. The operations proposal in
  [issue 97](https://github.com/fradicus/Shellhacks-2026/issues/97) has its own contract owner; check its accepted
  specs and claim before acting. It is neither approved nor revoked by these conversation notes.

## Keep context and specs aligned

| Document | Purpose | Maintenance rule |
|---|---|---|
| Dated context notes | What was observed, suggested or questioned | Preserve the account. Append dated corrections or later answers; do not rewrite feedback to fit the implementation. |
| Decision record | Choice, reason, scope and alternatives | State accepted, proposed, deferred or superseded. A changed choice links to its replacement. |
| Mission and feature specs | Current direction and required behavior | Update requirements and acceptance in the same PR that changes the behavior, through the owning feature/contract. |
| Status | Delivery and verification at a named revision | State the checkpoint revision and time; distinguish merged implementation, checks, live integration and user evaluation. |
| Pitch and submission | Claims supported by the selected demo | Check the actual dataset, deployment and evidence before presenting. Label sample/historical/prototype content. |

For a substantial new requirement, link the motivating observation, record the decision, and state how acceptance
will be checked. Link current counts to producer artifacts or the active dataset; keep duplicated snapshot numbers
in dated reports rather than normative specs. Use the [shared vocabulary](../vocabulary.md).

No new maintenance bot or approval layer is required. Each owner checks these links when their change affects
behavior or claims. Missing customer evidence stays pending; agents can complete independent authorized work.
