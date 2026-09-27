---
id: F32
name: Optional natural-language app controls
lane: B
agent: gemini-engineer
phase: 5
depends_on: [F31]
owns: [web/components/assistant/, web/app/assistant/, web/app/api/assistant/, web/lib/assistant/, tests/web/assistant/]
cut: allowed
---

# F32 Optional AI side panel

The user asked for a separate potential-feature branch. Use `codex-ai-app-control`; retain it as a draft/prototype until its own acceptance. Follow Plan D's Ask-the-grid and Plan B's prompt-injection and truthful-output rules.

Define a strict action contract for applying supported filters, choosing an existing project/pair, focusing supported geography and navigating approved views. Every model output must validate against the available geographic catalog, current result IDs and action allowlist. Ambiguous place names require clarification. Reject unknown actions, arbitrary code, unrestricted URLs, raw DB operators and write operations. Apply actions through the same UI state functions as manual controls and expose what changed with a reset/undo path.

Model credentials remain server-only. No credentials means an explicit unavailable or offline-command-preview state, never a fake model response. Live provider calls require a separately configured and tested provider; the current live-service deferral remains in effect for this worker. Source text cannot override app control instructions, and answers cannot invent project facts or savings.

Test representative supported requests, ambiguous counties, unsupported actions, prompt injection, stale project IDs and model failure. The original deterministic planner workflow must keep working when the side panel is disabled. Do not merge the optional branch merely to mark it complete.

## Live continuation authorized 2026-09-27

The user explicitly resumed the side button and asked to get it ready to ship. C60 supersedes the prototype-only/live-service deferral above for this bounded feature. Preserve the old branch; resume from current main in `codex-f32-live-assistant`. Root coordinates disjoint client and Gemini provider work plus independent review. F32 may merge after its implementation acceptance; separately disclose whether a configured live Gemini call was verified. Missing credentials never become a simulated AI response.

The app-wide launcher is mounted through the root-owned C60 layout integration after F32 exists. `/assistant` wraps the existing national explorer and its current controller, with the same data and filters as manual use. Outside that workspace, validated filter/focus actions open it with supported URL parameters; navigation uses approved existing routes. Preserve the other computers' Time/History code. Reset and undo remain available; changed view/filter context invalidates pending responses.

Gemini interprets one bounded action or chooses a supported help topic. The server reads authoritative current summaries/reference records, validates output, and derives factual answers/action descriptions from those records and documented app rules. Model text cannot invent counts, dates, costs, project facts or savings. Keys and model identifiers come from server configuration; `ASSISTANT_ENABLED=true`, `GEMINI_API_KEY` and `GEMINI_MODEL` are required for provider calls. Add bounded request/concurrency limits, fixed provider host, time/byte limits and same-origin JSON POST validation. No uploads, writes, arbitrary URLs or execution. Local provider tests use injected transports; browser test mocks are explicitly labeled.
