---
name: pdf-project-extraction
description: Extract planned transmission projects from the Dominion Energy SC and Georgia Power PDFs into the Gridlock project schema. Use for issues about parsing utility filings.
---

# PDF project extraction

Tools: `pdftotext -layout` (poppler) or `pdfplumber` in Python. Gemini (`gemini-api` skill) only for rows
regex can't handle. Output schema = `projects` in PROJECT.md, minus coordinates.

## Dominion Energy SC (44 pages, one project per page)
Each page reads: `Project N of 44` / project name / `Project ID` / id / `Project Description` / text /
`Project Need` / text / `Project Status` / text / `Planned In-Service Date` / `MM/DD/YY` / yearly costs / `Total*` / `$X`.
Split on `Project \d+ of 44`, pull fields by label. `_id = "DESC_" + project_id` (strip spaces).
`cost_usd` = Total*. Dates `12/31/23` -> 2023-12-31.

## Georgia Power IRP Vol 3 (668 pages)
The project list is the "GA ITS Ten-Year Plan (2025-2034)" table (starts ~page 9 of that section).
Columns: `Zone | Year | TEAMS Number | Project Name | Need Date | Project Sponsor | cost columns (REDACTED)`.
Project names wrap across 2-4 lines under the first line; a new row starts when a line begins with a
3-digit zone. Join continuation lines onto the previous name. `_id = "GPC_" + TEAMS number`.
Later pages have per-project detail sheets keyed by the full name (e.g. "SAV: MCINTOSH - PURRYSBURG 230KV REACTORS") - pull the description from there when present.
Prefixes `SAV:`, `GTC:`, `MEAG:` = sponsor/area tag, not part of the endpoint name. Keep rows of all
sponsors; set `sponsor`. Zones 215 (Augusta area) and 219 (Savannah) border SC: do them first and verify by hand.

## Endpoint parsing (both utilities)
- Strip prefix tag and trailing work words: `REBUILD, RECONDUCTOR, CONSTRUCT, TIE, TAP, REACTORS, LINE, UPGRADE, #\d`.
- Split on ` - ` or `-` between names -> up to 2 endpoints. Keep parenthetical qualifiers like `(SAV)`, `(USA)` in `match_note`, not the name.
- Voltage: all `\d+\s?kV` matches. Kind from keywords: rebuild / reconductor / construct|new -> new_line / sub|substation|bus|capacitor|relay -> substation / reactor.
- Single-site projects ("KATHLEEN AREA IMPROVEMENTS") -> one endpoint.

## Check before PR
Print counts per utility, per endpoint-count, and 5 random records with their page numbers; paste in the PR.
