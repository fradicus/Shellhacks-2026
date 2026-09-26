# F03 execution and unavailable live integration

Runtime: Windows Codex / codex-local. Logical role: Gemini engineer. Coding model: GPT-6 Astra with high reasoning; root performs integration and independent QA reviews acceptance.

The user explicitly deferred live Gemini credentials on 2026-09-26. Ship the actual DESC-only SDK batch pipeline, offline validation/cache/retry tests, and an unavailable evaluation with zero live calls. Synthetic test responses must be labeled as synthetic; do not fabricate recorded API evidence, model identities, accuracy, or mismatch examples.

Only F03 owns pipeline/gemini_extract/, tests/pipeline/test_f03_, data/extraction/, its feature spec and F03 decision files. Additive shared UI typing is requested from the technical lead in issue 32. Georgia inputs remain prohibited from Gemini under D2.
