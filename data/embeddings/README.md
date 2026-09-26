# data/embeddings/

Gemini embedding records for the search corpus (matches, active projects, passed briefs).
Produced by `cd pipeline && uv run python -m embeddings --live` (F19). Every record carries the
exact embedded `text`, its `text_hash`, the model id, dimensions and timestamp. Records validate
against `schemas/embedding.schema.json`; the `load` workflow stores them dataset-namespaced and
maintains the Atlas vector index `embedding_vector`.
