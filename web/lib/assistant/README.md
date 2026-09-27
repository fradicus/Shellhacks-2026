# Gemini app controls

`/assistant` embeds the existing national explorer. The shared layout mounts `AssistantHost` so the same side button is available across the app. The workspace registers its existing filter/selection controller; actions elsewhere open approved pages or the workspace with validated filters. Project data and matching rules remain owned by their existing modules.

The visible assistant calls the server Gemini interpreter. It does not fall back to the old offline grammar or present a test response as AI. Unknown/ambiguous places ask for clarification; stale project identifiers and replies after changed UI context cannot execute. Counts come from loaded records. Moving the viewport cannot create a project location or verify a candidate point.

Configure these variables only on the server:

- `ASSISTANT_ENABLED=true`
- `GEMINI_API_KEY`: an authorized Gemini credential
- `GEMINI_MODEL`: the provisioned model identifier

`GET /api/assistant` checks configuration without contacting Google. Missing configuration reports unavailable. A successful readiness check does not prove provider access; verify a real request separately. `POST /api/assistant` accepts a bounded message and UI context, reads the authoritative national reference and current summaries, and requests one structured Gemini decision. The decision can propose an allowed action, select a documented help topic, request clarification or decline an unsupported task. Facts and action descriptions are constructed by the server from app records/rules; arbitrary model-written facts are not displayed as evidence.

The provider uses a fixed Google endpoint with time/byte limits and bounded per-process rate/concurrency controls. Same-origin JSON requests are required. Server-side provider quotas remain necessary for an account-wide budget. Keys and raw provider responses are not sent to the browser, and the server does not log prompts. Source strings cannot grant tools or override control rules. Requests from the explorer bind to its dataset release; changed releases cause no action. The browser validates again immediately before applying the response, and offers undo/reset.

The `parseOfflineCommand` helper is retained for deterministic development tests and backwards compatibility; the production side panel does not call it. Node transport tests and browser mocks are test-only. No live credential or successful live provider call is implied by those checks. The separate original prototype branch remains available as historical work.

The provider follows Google's [structured-output contract](https://ai.google.dev/gemini-api/docs/generate-content/structured-output). It does not upload files, execute code, edit records, dispatch equipment, certify truck routes or predict construction outcomes.

Examples: `Show planned projects in Florida`, `Focus California`, `Show projects in Orange County, California`, `Find transformer projects`, `Open History`, `What does an overlap mean?`, `What do the location labels mean?`.
