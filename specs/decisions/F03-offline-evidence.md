# F03: honest unavailable evidence and conservative field validation

The user deferred live Gemini credentials. F03 therefore ships the actual SDK batch pipeline with
`desc.json = []`, `eval.json.status = unavailable`, an eligible-corpus denominator of 91, zero
processed pages/calls and null field accuracy. There is no model selection or invented timestamp.
No mismatch examples or API-recorded fixtures are claimed. The two hand-authored fixtures identify
themselves as synthetic and are confined to F03 tests. They exercise local validation, not live model
prompt-injection resistance. An authorized operator can later supply env credentials/model and use
the explicit `--live` flag; simply setting a key never calls the service.

Source support is conservative: quote membership alone is insufficient. Citations must cover the
correct labeled section (including the full cost column context), and the value must agree with
the source interpretation of the current F01 parser. F01 comparison is reported as parser agreement;
F13's independent human check remains null. Parser flags are preserved. Unknown/ambiguous endpoint
values do not authorize new claims, and every cached response is revalidated after parser changes.

The JSON extraction schema already allows optional metadata. F03 uses the optional record contract
documented in `data/extraction/README.md`; additive shared TypeScript typing is coordinated in issue
32. Each real record carries its evaluation summary so existing extraction reads can serve F16.
Summary/cache objects never have a top-level `_id`, because F06 recursively loads data/extraction.

Verification of the pinned installed SDK confirmed `HttpRetryOptions(attempts=1)` disables its
default retries. The runner alone allows at most two transient retries after the initial request.
The implementation uses the official `models.generate_content` structured-output API, not a stub
or a claim of asynchronous Batch API usage. No new dependencies or frozen contracts were edited.

References: https://googleapis.github.io/python-genai/ and
https://ai.google.dev/gemini-api/docs/structured-output (checked 2026-09-26).

Undo: after an authorized live run, commit genuine validated responses/evaluation, keep synthetic
tests labeled, and add separately recorded fixtures and independent QA evidence. Update both the
prompt/schema version and relevant tests when changing extraction semantics.
