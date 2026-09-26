# F20: live query embedding on the public site

## Context

`specs/mission.md` says "The public site shows stored results; it never calls Gemini." F20's
search box needs a vector for an arbitrary user query, which only an embedding model can produce
at request time.

## Options

1. **Precomputed neighbors only** (stored top-K per record; zero live calls). Kept: it is the
   `?ref_id=` mode of `/api/search` and needs no key.
2. **Live query embedding via Gemini REST.** Chosen alongside (1), decided by the human operator
   post-run (2026-09-26). Scope is deliberately narrow: the route sends the query text and
   receives a vector. No generated prose is ever shown; grounding rules for briefs are unchanged.
3. Client-side embeddings (onnx etc.). Rejected: new dependency, heavier bundle, worse quality.

## Choice

- `/api/search?q=` calls `embedContent` server-side with `GEMINI_API_KEY` (Vercel env, never
  `NEXT_PUBLIC_`). Without the key the route answers 503 `{unavailable: true}` like every other
  database-backed route; the page shows the explicit unavailable state.
- Batch corpus embedding stays pipeline-side under `--live`, unchanged from F12's convention.

## How to undo

Remove `web/app/api/search/` query mode (keep `ref_id` mode), unset `GEMINI_API_KEY` in Vercel,
and the site is back to stored-results-only.
