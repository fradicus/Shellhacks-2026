---
name: pdf-project-extraction
description: Extract planned transmission projects from the Dominion Energy SC SCRTP lists (2024-2028, 2025-2029) and the Georgia Power IRP Ten-Year Plan into the Gridlock schema, including yearly spend and owner codes. Use for parsing utility filings.
---

# PDF project extraction

Tools: `pdfplumber` or `pdftotext -layout` (poppler), and pandas. Gemini (`gemini-api`) only for rows that
rules can't handle. Output = the `projects` schema in PROJECT.md without coordinates. Page numbers are 1-based physical pages.

## Dominion Energy SC (both lists, same layout, one project per page)
Page text order: `Project N of M` / name / `Project ID` / id / `Project Description` / text / `Project Need` /
text / `Project Status` / text / `Planned In-Service Date` / date / `Estimated Project Cost` / `Previous` and
year labels with amounts / `Total*` or `Total` / amount.
- Split on `Project \d+ of \d+`. Pull fields by label. `_id = "DESC_" + id` with spaces removed (e.g. `6807B`).
- Dates: `12/31/23` and `12/31/2028` -> ISO dates.
- `yearly_spend`: map each year label (and `Previous`) to its amount in document order. Check that the sum equals Total within $1. If it doesn't, keep the record and add a quality flag.
- `cost_usd` = Total. `status` verbatim.
- 2025-2029 is `source.id = desc-2025`; 2024-2028 is `desc-2024`. The same ID in both -> one project with `versions[]` (Current mode uses desc-2025).
- `source.url` = public URL + `#page=N`.

## Georgia Power IRP Vol 3, "GA ITS Ten-Year Plan (2025-2034)"
Columns: `Zone | Year | TEAMS Number | Project Name | Need Date | Project Sponsor | Estimated Cost - GPC | GTC | MEAG | DU | Totals` (all costs REDACTED).
- A row starts with a 3-digit zone at the line start. Following lines without a zone continue the project name. Join them.
- Pages with wrapped rows the rule can't resolve go to the AI Engineer's row-joining helper. Log how many rows went that way.
- `_id = "GPC_" + TEAMS`. `owner_code` = the sponsor column. Name prefixes `SAV:`, `GTC:`, `MEAG:` are tags, not endpoint names.
- Later pages have detail sheets headed by the full project name, e.g. "SAV: MCINTOSH - PURRYSBURG 230KV REACTORS". Pull the description where present and keep its page.
- Don't store any REDACTED value; `cost_usd = null`.
- Order: zones 215 and 219 (the SC border) first, then the rest.

## Endpoint parsing (both utilities)
- Strip tags and work words: `REBUILD|RECONDUCTOR|CONSTRUCT|TIE|TAP|REACTORS?|LINE|UPGRADE|FOLD-IN|ADD SERIES REACTOR|#\d+|:.*$` (after the colon is the work type).
- Split on ` - `, ` – ` (en dash) or `-` between capitalized names -> up to 2 endpoints. Parentheticals like `(SAV)` and `(USA)` go to `match_note`.
- `voltage_kv`: every `\d+\s?kV` (split `230-115kV` into [230, 115]).
- `kind`: rebuild | reconductor | new_line (construct/new/#2) | substation (sub/bus/capacitor/relay/switching) | reactor | tie | other.
- A single-site project -> one endpoint.

## Before the PR
Counts per source, 2/1/0-endpoint counts, number of Gemini-joined rows, and 5 random records with page numbers.
Keep `data/*.json` diffs in their own commit.
