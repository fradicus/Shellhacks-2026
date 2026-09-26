---
name: "GridBridge \u2014 Plan E"
description: "Build a public utility coordination workbench from Plan B with auditable evidence, Gemini and MongoDB Atlas."
slug: "gridbridge-e"
schema: "agentcompanies/v1"
version: "1.0.0"
---

# GridBridge company

Plan B supplies the product direction: United States vision, Southeast rollout and GA/SC reviewed proof, with a Three.js date view. This package assigns eight agents, thirteen written skills, one project and seventeen seed tasks to a 36-hour ShellHacks build. Follow the GridBridge project charter for rules, scope gates, dependencies and acceptance. The CEO has seven direct reports; technical lead owns integration and QA reviews independently.

## Active specification handoff
A concurrent root specification defines a separate 8-hour overnight build and treats plans as history. Before launching this 36-hour company, reconcile `references/specs/INTEGRATION.md` with the active spec owner. Import validation alone does not resolve that conflict; do not run both configurations in one workspace.

## Import and launch
Use the local package import preview before applying. Bind workspace, model, credentials and budgets through the running Paperclip instance. Timer heartbeats remain off; keep agents paused until the human starts kickoff. Imported task bodies contain prerequisite slugs; CEO creates native dependency links. Import itself is not build or spending authorization.

The repository workspace contains `docs/` as read-only input. Implementation edits belong only in `plans/plan-E/implementation/`. Do not read Plan D. Source/public-status rules apply before any external processing. Atlas is the application database; Gemini performs visible product work.

## Operator configuration
Use a tested local Claude Code runtime and available model for each `claude_local` adapter. The sidecar declares role-specific env inputs but contains no values. Subscription authentication can replace optional Anthropic API keys. Runtime Paperclip credentials are injected by Paperclip, not supplied as shared company secrets. App hosting credentials are bound separately to the deployed service.

Set budgets through the UI: CEO $10, lead $25, data $20, Gemini $20, geo $20, frontend $20, QA $15, release $10; total $140 only if the operator accepts that limit. Application Gemini and hosting/domain spending are separate. At most three active assignments and one run per agent. Freeze features/data/release at hours 24/28/30. The human handles accounts, purchases, source ambiguity, deployment authorization and submission.

## Portable package conventions
Agent skill shortnames resolve under `skills/`; projects and task assignees use local slugs. All skills are written procedures included here. There are no required external skill packages. The host's supported Paperclip coordination tools must still be available after import. See the attached project for the self-contained build contract and `references/SOURCES.md` for external documentation.
