---
id: F01
name: DESC register - both public filings, version links, source manifest
lane: A
agent: data-researcher
phase: 1
depends_on: [F00]
owns: [pipeline/extract_desc/, tests/pipeline/test_f01_, data/sources/, data/projects/desc, data/versions/]
cut: never
---

# F01 DESC register

## Plan
1. **Source manifest** (`data/sources/sources.json`, schema `source`). One entry each for:
   - `desc-2024`: sponsor copy `docs/Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf`, 44 cards, public URL https://www.scrtp.com/assets/pdfs/home/2024-2028-2million-and-above-project-descriptions.pdf
   - `desc-2025`: https://www.scrtp.com/assets/pdfs/home/2025-2029-2million-and-above-project-descriptions.pdf, 47 cards; download to `data/sources/desc-2025.pdf`
   - `gpc-2025`: the sponsor Georgia PDF, `public_status: public_with_banner` (see decision D2)
   - `sample`: the workbook
   
   Record sha256, page count and filing date where printed.
2. **Parser** (`pipeline/extract_desc/`, `pdfplumber`). One card per page, fields in order: `Project N of M`, name, `Project ID`, id, `Project Description`, `Project Need`, `Project Status`, `Planned In-Service Date`, yearly cost labels and amounts, `Total`/`Total*`.
   - `native_id` = id with inner whitespace normalized (`0139 M,N` keeps its comma)
   - `project_key = "DESC:" + native_id`
   - `cost_usd` = Total; `yearly_spend` = {label: amount}
   - dates like `12/31/23` or `12/31/2028` -> ISO, precision `day`
3. **Endpoints from names:** strip work words after a colon (`: Rebuild`, `: Construct`, `: Tap`), split on ` - ` or ` – ` into up to 2 endpoint names, and parse `voltage_kv` from every `\d+\s?kV`. Store `norm` via `pipeline.common.norm_name`.
4. **Versions:** the same `project_key` in both filings -> both records kept (`_id` has `@desc-2024` / `@desc-2025`). `active` = the newest filing containing it. Write one `version_change` per changed field (in_service, cost, status, name) to `data/versions/desc.json`.
5. Outputs: `data/projects/desc.json` (all versions), validated against the schema.

## Requirements
- 44 + 47 cards parsed, or every miss listed with its page in `data/projects/desc_unparsed.json`.
- Sum of yearly spend = Total within $1, otherwise the record gets a `quality_flags` entry.
- Deterministic: running it twice gives byte-identical output.

## Validation
- `tests/pipeline/test_f01_desc.py` asserts:
  - card counts 44 / 47
  - `DESC:0139 M,N` in service 2024-12-31 in desc-2024 and 2026-05-31 in desc-2025, with a version_change emitted
  - `DESC:6888` (Okatie – McIntosh 115kV Tie: Add Series Reactor) exists in desc-2025 with in-service 2028-12-31
  - every record validates
- PR body: counts per filing, number of 2/1/0-endpoint records, 5 random records with pages.

## Defaults
- A card that won't parse cleanly is kept with the fields that did parse, plus `quality_flags`; it's never dropped.
- If the public URL fails, use only the sponsor copy and log a decision.
