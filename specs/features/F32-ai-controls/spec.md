---
id: F32
name: Optional natural-language app controls
lane: B
agent: gemini-engineer
phase: 5
depends_on: [F31]
owns: [web/components/assistant/, web/app/api/assistant/, web/lib/assistant/, tests/web/assistant/]
cut: allowed
---

# F32 Optional AI side panel

The user asked for a separate potential-feature branch. Use `codex-ai-app-control`; retain it as a draft/prototype until its own acceptance. Follow Plan D's Ask-the-grid and Plan B's prompt-injection and truthful-output rules.

Define a strict action contract for applying supported filters, choosing an existing project/pair, focusing supported geography and navigating approved views. Every model output must validate against the available geographic catalog, current result IDs and action allowlist. Ambiguous place names require clarification. Reject unknown actions, arbitrary code, unrestricted URLs, raw DB operators and write operations. Apply actions through the same UI state functions as manual controls and expose what changed with a reset/undo path.

Model credentials remain server-only. No credentials means an explicit unavailable or offline-command-preview state, never a fake model response. Live provider calls require a separately configured and tested provider; the current live-service deferral remains in effect for this worker. Source text cannot override app control instructions, and answers cannot invent project facts or savings.

Test representative supported requests, ambiguous counties, unsupported actions, prompt injection, stale project IDs and model failure. The original deterministic planner workflow must keep working when the side panel is disabled. Do not merge the optional branch merely to mark it complete.
