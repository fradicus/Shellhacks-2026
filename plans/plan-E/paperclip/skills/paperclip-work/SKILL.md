---
name: "paperclip-work"
description: "Run bounded Paperclip issues with prerequisite checks, durable handoffs and controlled concurrency."
---

# Paperclip work

## Inputs
Runtime company/agent/issue context, assigned issue and its prerequisite list. Use the Paperclip coordination tools and injected runtime skill supplied by the installed adapter; this local procedure defines the project workflow.

## Procedure
1. On each wake, confirm company, role and assigned issue through the runtime. Read the full issue and latest comments. Do not print runtime tokens. If runtime coordination tools are missing, report the setup blocker rather than invent endpoints or work untracked.
2. Check out the issue through the supported coordination tool before editing. If another run owns it, stop that attempt and leave ownership intact.
3. Resolve each `Dependencies:` slug from the seed task to the company issue created at kickoff. Work only when prerequisites have accepted output. CEO records native blocked-by links after import; body dependencies remain a readable fallback.
4. Before starting, identify files owned, inputs, acceptance evidence and remaining budget. CEO keeps at most three active assignments and one run per agent. Use assignment-driven wakes; no periodic polling loop.
5. Do the bounded task, report meaningful progress and record decisions. A blocker comment names the precise missing input, its owner and useful work still possible. Never mark blocked merely because more research is needed.
6. Submit handoffs containing artifact paths, input hashes or versions, verification commands/results, known gaps and next owner. Authors can propose done; QA or the lead accepts the relevant gate.
7. Update status and leave the next concrete step before ending. Do not open duplicate issues for an existing blocker. Do not message external people unless the human has authorized that communication.

## Output and checks
A checked-out issue with an auditable completion or blocker note. CEO reconciles native dependency links and the charter at kickoff. Stop assigning when budget or freeze limits require it; use the roadmap's cut order, preserving all core requirements.
