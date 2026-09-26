---
id: F20
name: Semantic search over matches, projects and briefs
lane: B
agent: technical-lead
phase: 5
depends_on: [F10]
owns: [pipeline/embeddings/, tests/pipeline/test_f20_, data/embeddings/, data/neighbors/, web/app/search/, web/app/api/search/, web/components/search/]
cut: allowed
---

# F20 Semantic search

Post-run feature requested by the human operator: vector search over the stored corpus with
Gemini embeddings, plus precomputed "similar items" per record. Schemas and the loader's
collection/index support arrived via `[C10]` and `[FIX-F06]`; the nav link via `[C10]`.

## Plan

1. `pipeline/embeddings/` builds a deterministic search text for every match, every active
   project, and every passed brief; embeds new/changed texts with Gemini
   (`GEMINI_EMBED_MODEL`, default `gemini-embedding-001`, `output_dimensionality=768`);
   reuses cached vectors when `text_hash` and model are unchanged. Offline-first like F12:
   without `--live` and `GEMINI_API_KEY` it writes nothing and reports
   `live_execution_deferred`.
2. Precompute top-K cosine neighbors per record into `data/neighbors/` (pure Python; no new
   dependencies).
3. The `load` workflow stores both collections (dataset-namespaced) and ensures the Atlas
   vector index `embedding_vector` (768 dims, cosine, `dataset` filter).
4. `web/app/api/search/` serves two modes: `?ref_id=` returns stored neighbors (no Gemini
   call); `?q=` embeds the query server-side and runs `$vectorSearch` filtered to the active
   dataset. `web/app/search/` is the UI; matches link to their `/pair/` page.

## Requirements

- Every embedding record stores the exact embedded `text`, its `text_hash`, the model id,
  dimensions and timestamp (traceability, like every other Gemini output).
- Query-time embedding is the **only** live Gemini call the site makes; it returns vectors,
  never generated text shown to users. Recorded in `specs/decisions/F20-live-query-embedding.md`.
- No new dependencies anywhere: pipeline uses the pinned `google-genai`; the web route calls
  the Gemini REST endpoint with `fetch`.
- The API keeps the repo rule: database problems -> 503 `{unavailable: true}`, never fixtures.

## Validation

- `tests/pipeline/test_f20_*.py`: text builders on synthetic records, cosine/top-K correctness,
  cache reuse (no re-embed of unchanged text), offline mode writes nothing, end-to-end run with
  an injected fake embedder produces schema-valid `embeddings.json` and `neighbors.json`.
- `cd pipeline && uv run ruff check . && uv run pytest -q`
- `cd web && npm run lint && npm run typecheck && DATA_MODE=fixture npm run build`
- Live smoke (needs Atlas + `GEMINI_API_KEY`): `uv run python -m embeddings --live`, then the
  `load` workflow, then `GET /api/search?q=savannah%20river` returns ranked matches.

## Defaults

- K = 10 neighbors per record; query `k` capped at 50.
- Corpus: matches, active projects, passed briefs. Extraction raw text is out (page-size blobs;
  revisit if judges ask).
- If the Atlas index is missing, the API route still serves `ref_id` neighbor lookups; `q` mode
  reports unavailable.
