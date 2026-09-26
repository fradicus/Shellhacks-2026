---
id: F02
name: Georgia register - Ten-Year Plan table rows and owner codes
lane: A
agent: data-researcher
phase: 1
depends_on: [F00]
owns: [pipeline/extract_gpc/, tests/pipeline/test_f02_, data/projects/gpc, data/owners/]
cut: never
---

# F02 Georgia register

Read decision **D2** first: deterministic table parsing only, **no Gemini**, no page excerpts beyond project names.

## Plan
1. **Locate the tables:** "GA ITS Ten-Year Plan (2025-2034)" in `docs/.../Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`. Columns: `Zone | Year | TEAMS Number | Project Name | Need Date | Project Sponsor | cost columns (REDACTED)`.
2. **Parse rows** with `pdfplumber` words and x-positions, or `pdftotext -layout`. A new row starts with a 3-digit zone at the line start. Following lines with no zone continue the project name (join them with spaces).
   - `native_id` = TEAMS number; `project_key = "GPC:" + TEAMS` (the prefix names the source plan, not the owner)
   - `owner_code` = the sponsor column
   - `in_service.raw` = the need date; parse to day precision
   - never store REDACTED values; `cost_usd: null`
3. **Owner codes** (`data/owners/owners.json`): map each code to an organization **only with a citation** (a legend page in the PDF, or a public official source URL). Decision D3: `SAV` -> Georgia Power only with a citation. `utility` = `GPC` when the mapped organization is Georgia Power, otherwise `unknown`.
4. **Endpoints:** strip prefix tags (`SAV:`, `GTC:`, `MEAG:`) and work words (`REBUILD, RECONDUCTOR, LINE, REACTORS, UPGRADE, #n`), split on ` - `. Parentheticals (`(SAV)`, `(USA)`) go into `endpoint.qualifier`. Parse voltage.
5. **Order:** zones 215 and 219 (the SC border) first, then all others. If time is short, ship the border zones with `coverage_note` saying so; the denominator (total rows seen) is always recorded.

## Requirements
- No Gemini calls in this feature. No page images. Cite `source.page` for every row.
- Rows with ambiguous wrapping are kept with `quality_flags: ["wrap_ambiguous"]`.

## Validation
- `tests/pipeline/test_f02_gpc.py` asserts that these exist with the right need dates:
  - TEAMS `20277` (SAV: MCINTOSH - PURRYSBURG 230KV REACTORS, 6/1/2026)
  - `11821` (JESUP - LUDOWICI PRIMARY, 6/1/2025)
  - one `EVANS PRIMARY - THURMOND DAM` row (6/1/2033)
  
  It also checks the row counts per zone are non-zero for zones 215 and 219, and that every record validates.
- PR body: total rows, rows per owner code, mapped vs unknown owners with citations.

## Defaults
- Can't find a legend? Map only `GPC`; leave the others `unknown`, and log the decision.
