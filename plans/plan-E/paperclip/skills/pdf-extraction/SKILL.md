---
name: "pdf-extraction"
description: "Prepare approved PDF pages and normalize extracted records with field-level provenance and no invented values."
---

# PDF extraction and normalization

## Inputs
Approved page manifest, original PDF hash, project schema and reference examples. Never process quarantined pages while waiting for review.

## Procedure
1. Inspect layout before parsing. Use Python PDF text tools for readable text and render the approved pages when tables or ordering are ambiguous. Preserve the mapping between segment page numbers and original PDF pages.
2. Split by complete project card or table row with its headers. Avoid sending an entire long filing when a small approved range suffices. Store segment hash and source version.
3. Extract original names, native IDs, owner codes, endpoint names, published voltage/type, raw date text and costs only when explicitly public. Gemini extraction follows the separate gemini-evidence procedure; deterministic parsing can assist but must retain provenance.
4. Normalize dates to exact calendar dates only when the source gives a day. Keep precision and date kind. An Excel serial in the golden fixture uses the workbook's date system; a year in a PDF is not an exact December 31 date.
5. Validate the schema and every field citation. Redacted or missing values are null. Reject impossible dates, unsupported costs, merged rows and cross-page citation mistakes into review rather than silently repairing them.
6. Deduplicate by verified owner/native ID and source version, not name similarity alone. Record extraction model/prompt/schema versions and review amendments separately.
7. Produce counts of extracted, rejected and reviewed rows, and hand off accepted records to the loader. Reprocessing the same source hash must not add duplicates.

## Output and checks
Versioned normalized rows plus field provenance and review queue. QA compares against 12 reviewed approved reference rows spanning both utilities and missing-value cases. Unavailable approved examples are a data gate, not a reason to fill the set with guesses.
