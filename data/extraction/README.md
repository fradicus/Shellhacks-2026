# DESC Gemini extraction

Current committed state: **unavailable**. The user deferred live Gemini credentials; `desc.json`
contains no model responses, and `eval.json` reports the 91-card eligible corpus with zero processed
pages, zero live calls, and null accuracy. No synthetic response is product data.

From `pipeline/`, run `uv run python -m gemini_extract` for the offline unavailable artifact.
An authorized operator can run `uv run python -m gemini_extract --live` with `GEMINI_API_KEY`
and an explicitly chosen `GEMINI_MODEL` in the process environment. There is no default model and
no automatic live mode. Offline mode writes an empty response list; use a separate checkout if
preserving a previously generated response list. Never place credentials in command arguments or git.

Live mode sends each of the 91 approved DESC card texts to the real `google-genai` SDK, sequentially.
This is a local batch pipeline using `models.generate_content`, not the asynchronous Gemini Batch
API. It sends no PDF uploads. Both PDFs must match the pinned F01 hashes; manifest edits alone
cannot authorize new documents. The model sees F01's canonical extracted page text (trimmed lines,
normalized nonbreaking spaces and the documented replacement glyph), freshly derived from the PDF.
That exact text is saved as `source_text`. The transport rechecks approved PDF bytes and text before
each request. Georgia is never accepted, including via direct transport calls or cache lookup.

The request has temperature 0, no tools, a separate instruction treating document content as data,
and a strict JSON response schema. Local validation requires the correct original page, an exact
contiguous quote in the relevant labeled section, correct types, source-supported normalized values,
valid IDs and valid published calendar dates. Budget citations must cover the header and amount row.
Unrelated quotes and matching quotes with wrong values are rejected. Date text containing multiple
milestones or a partial date stays raw; no exact date or construction window is invented. Parser
quality flags remain visible and acceptance is **not** human confirmation of source quality.

## Record contract for F16

`desc.json` is an array of extraction-schema records. It is empty in the current unavailable state.
Each actual response/failure record has the required schema keys plus:

- `source_sha256`, `source_text`, `source_quality_flags`: DESC provenance and parser caveats.
- `deterministic`: F01 reference values under the same field names as `fields`.
- `fields`: each entry is `{value, quote, page, valid, reasons}`. Malformed responses use `{}`.
- `comparison`: each field maps to `match`, `mismatch`, or `missing`. A matching value with an
  invalid citation still fails validation and is excluded from the accuracy numerator.
- `status`: `accepted`, `rejected` (a response failed checks), or `failed` (no response).
- `rejection_reason`: safe reason codes joined with `; `, or null.
- `validation`: `{passed, reasons}` computed locally; never trusted from the model.
- `call_attempted`, `attempts`, `cache_hit`: current-run request counts. At most three SDK calls
  per page (initial attempt plus two transient retries), with 1- and 2-second backoff. SDK retries
  are disabled. A cache hit has zero attempts and preserves the original `generated_at`.
- `evaluation`: the same summary as `eval.json`, so the existing extraction API can expose it.

The field names are `project_id`, `name`, `description`, `need`, `status`, `in_service_raw`,
`total_cost`, `yearly_spend`, `endpoints`, `voltage_kv`. Text scalars may be null; identity and name
must be present to accept the record. `total_cost` is integer USD/null, `yearly_spend` maps the
published columns including `Previous` to integer USD/null, and endpoints/voltages are arrays.
No normalized location coordinates are produced.

`eval.json` measures **validated field agreement with F01**, not independent human accuracy. Per
field it stores matched/mismatched/missing/invalid counts, processed-page denominator and accuracy.
Invalid counts overlap the other categories. The separate `corpus_pages` denominator is 91.
Failed attempted pages stay in the processed denominator. With no responses/attempted pages,
accuracy is null, not zero. `qa_checked` stays null until F13 supplies independent evidence.

Cache files are summary envelopes `{metadata, text_sha256, generated_at, response}` without a
top-level `_id`; the loader skips them and `eval.json`. Cache keys cover source SHA-256, original
page, exact model and prompt version. Raw parsed responses are always revalidated against the
current parser/reference; accepted status and comparison are never replayed from cache. Changed
PDF bytes are rejected until a reviewed allowlist change, regardless of cache contents.

The two offline response fixtures under `tests/pipeline/test_f03_fixtures/` are explicitly synthetic.
They test validation, including hostile source text, not measured Gemini performance. Replace or
supplement them with actual recorded, reviewed responses only after an authorized live run.
