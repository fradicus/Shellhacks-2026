# Project demo and mentor feedback — notes

September 26, 2026 · GridBridge demo conversations

## Main takeaways

- The operational reviewer identified the desktop project manager as the most important initial user.
- Foremen need a simpler field experience for immediate decisions, particularly when mobilization happens at short notice.
- The geographic/time visualization and the ability to open source evidence received positive feedback.
- Keeping project information accurate and current is a central challenge.

## Demo observations

- We showed the map, nearby project comparisons, the vertical time view, and links to filing evidence.
- The first demonstration encountered a visualization problem. Demo reliability needs attention.
- Reviewers responded positively to the interface and the way the vertical axis makes differences in filed dates visible.
- One reviewer asked whether the records were real. We opened the evidence view and the source PDF.
- The positive response came during a guided demonstration. Independent task completion and repeat use still need evaluation.

## Project manager workflow

- Project managers plan ahead and investigate schedule relationships across projects.
- A project can wait a long time for approval, then receive a request to mobilize almost immediately.
- Better visibility into nearby work could help a PM decide which teams to contact and what questions to ask.
- The reviewer emphasized the desktop PM workflow even while discussing possible mobile use.

## Field workflow and equipment

- Foremen may need to secure crews and equipment with very little notice.
- The reviewer described limited equipment availability and competition for labor.
- Equipment rented for a longer period may be idle between uses. Nearby jobs could potentially coordinate its use.
- Subleasing was discussed as a possible future capability. The reviewer said it was less common and explicitly
  did not expect the team to build it during the hackathon.
- Simple, readable mobile interactions would matter for field users working in difficult conditions.
- Separate logins were discussed, but specific permissions and role-based tasks were not established.

## Changing schedules and uncertainty

- Emergency work can disrupt planning and compete with scheduled projects for resources.
- The reviewer suggested permitting, wetlands, terrain, weather, regulation, and differences between utilities
  as possible influences on schedule reliability.
- These are hypotheses to investigate. We do not yet have a validated model establishing their predictive value.
- Historical changes may help identify patterns if we can obtain reliable observations, actual outcomes, and context.
- Accuracy and keeping information updated were explicit priorities in the feedback.

## Expansion ideas

- The sponsor described an ambition to serve utilities and contractors nationwide.
- We proposed expanding coverage from Georgia and South Carolina into the Southeast and then more broadly.
- We also raised equipment sharing and a public explorer for people researching infrastructure projects.
- The reviewer was receptive. Those responses do not yet establish which feature should be built next or who
  would regularly use it.

## Other mentor feedback

- Design around the user's next action and explain the practical use case.
- Routing, travel sequence, and transportation constraints were raised as examples of operational concerns.
- A clearly labeled example scenario could make the product easier to understand. Hypothetical scenarios must
  remain distinct from actual project evidence.

## Presentation language to tighten

- Use “filed in-service date” when that is the field we have. It is different from contract completion,
  construction start, or notice to proceed.
- Describe nearby projects with close dates as candidates to investigate. Their milestones do not establish
  compatible construction schedules.
- Identify the actual source: utility filing, regional planning list, government record, or contract.
- Keep possible future integrations separate from completed data ingestion.
- Show the evidence and review state behind each location and candidate pair.
- Matching information across sources helps only when source independence, meaning, and revision dates are understood.

## Follow-up questions

1. Can a PM show us a recent project where earlier visibility would have changed a decision?
2. What information was missing, and when was it needed?
3. Which location evidence and dates would justify contacting another project team?
4. Would a shortlist, change summary, or evidence packet be the most useful first output?
5. Can the sponsor provide a permitted, redacted example and help assess the next iteration?

## Working direction

Focus the next iteration on a PM investigating one real project, understanding nearby work and uncertainty, and
preparing a useful follow-up packet. Keep field tools, equipment transactions, and predictive scheduling as
separate areas for discovery.

These notes distinguish reviewer observations from our proposals. They capture feedback and open questions;
the accepted product direction and separate-work boundaries are in [C16](../decisions/C16-sponsor-context.md).
