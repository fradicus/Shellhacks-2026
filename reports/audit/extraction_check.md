# Independent DESC extraction spot check

A fixed purposive sample of 12 cards (six per filing) was read independently from the source pages. Nine non-location field groups per card agree with the deterministic parse: **108 agreements / 108 comparisons, zero mismatches**. This is sample agreement, not corpus accuracy or Gemini accuracy. Observations, source hashes, pages and the post-correction comparison are in [evidence.json](evidence.json).

The field groups are native ID, name, description, need, status, in-service value/precision, cost, annual spending and voltage. Nulls and printed inconsistencies are preserved. The original endpoint observations precede PR52 and are labelled historical; they are not current accepted endpoints. The refreshed snapshot confirms that DESC 0139 M,N (2024) and 6238 H (2025) now retain three candidates and zero accepted endpoints because the scope is ambiguous.

| Gemini metric | Observed |
|---|---|
| Real records processed | 0 |
| Field accuracy | unavailable (null) |
| Live evaluation | deferred by user |

No synthetic test result is presented as a real model measurement. The current deterministic comparison is the only reported spot-check result. A future live Gemini run must evaluate the full approved DESC corpus with explicit denominators before publishing model accuracy.
