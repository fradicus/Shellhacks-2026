# data/neighbors/

Precomputed top-K cosine neighbors per embedded record (F20), written by the same
`python -m embeddings` run that writes `data/embeddings/`. Served by `/api/search?ref_id=…`
without any live model call. Records validate against `schemas/neighbor.schema.json`.
