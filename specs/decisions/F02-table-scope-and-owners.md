# F02 table scope and owner mappings

## Context

The Georgia source contains the current `GA ITS Ten-Year Plan (2025-2034)` table on physical PDF pages 177–190.
Page 191 begins a separate table of cancelled projects removed from the current plan. The current-plan table has
redacted cost columns and sponsor codes `DU`, `GPC`, `GTC`, `MEAG`, and `SAV`.

## Choice

- Extract all 208 current-plan rows from pages 177–190 and exclude the cancelled-projects table on page 191.
- Use only words with x-position below 360 for parsing. This bounds extraction to zone, year, TEAMS number,
  project name, need date, and sponsor code; redacted cost cells are never retained.
- Map `GPC` to Georgia Power Company using the company's official overview. Map `SAV` to Georgia Power Company
  using Georgia Power's SEC-filed Form 8-K, which states that Savannah Electric merged with and into Georgia Power
  on July 1, 2006, with Georgia Power as the surviving corporation.
- Leave `DU`, `GTC`, and `MEAG` unverified and set their project utility to `unknown`. The raw sponsor codes remain
  visible. This follows decision D3 instead of inferring organizations from abbreviations.
- Store the 208-row denominator, per-zone counts, per-owner counts, and excluded-table reason in
  `data/projects/gpc_summary.json`. The loader intentionally skips summary objects without `_id`.

## Undo

Change the page range or owner records, rerun `python -m extract_gpc`, and re-run the F02 schema and deterministic
output tests. No source PDF or frozen contract changes are required.
