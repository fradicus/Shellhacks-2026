# Dense Southeast 002: SCRTP (South Carolina)

Sources (public SCRTP site; the CEII-NDA study reports behind secure.scana.com were not used):
- DESC "Planned Transmission Projects $2M and above", 2026–2030 (`assets/pdfs/home/2026-2030-2million-and-above-project-descriptions.pdf`),
  54 one-page project blocks.
- Every archived SCRTP stakeholder deck (`meeting-archives.html`, 2013–2026). Santee Cooper's "Committed Transmission
  Facilities" table (title plus in-service date) appears in 10 decks from 2017-01-24 to 2026-03-11; earlier decks
  use another layout and contribute nothing. The 2015-12-09 deck exceeds the 16 MB fetch bound and is recorded as skipped.

| Source | Rows | New projects | Located (candidate / unique name) | Not in service | Dated |
|---|---|---|---|---|---|
| DESC 2026–2030 | 54 | 14 (40 duplicates of legacy DESC IDs) | 4 (–) | 14 | 14 |
| Santee Cooper decks | 132 | 73 (59 earlier-deck listings) | 17 | 17 | 73 |
| **SC total** | 186 | **87** | **21** (16 / 5) | 21 | 87 |

- DESC rows whose project ID (whitespace ignored) is already in the legacy DESC register are duplicates of that
  record; the legacy record keeps its own filing facts.
- Santee Cooper rows have no IDs: one project per exact normalized title across decks, with owner tags such as
  "(DESC)" ignored. Reworded titles ("Pine Level-Allen" / "Pinelevel-Allen") remain separate projects.
- Each deck's changed in-service date is a `planned_milestone` event dated to the day. 61 projects last listed in an
  older deck have status `unknown`: dropping out of a later deck is not evidence of completion.
- Unlocated (66): mostly `no_facility`. Many Santee Cooper and DESC substations (Wassamassaw, Varnville, Purrysburg,
  Indian Field) have no named OSM substation. Operator conflicts (Bluffton, Yemassee: a same-name facility with
  another utility's operator) stay unlocated under C38.

## Spot check

All 21 located records were compared with their titles. Each point is the named substation (Columbia Canal, Adams
Run, Holly Hill, Graniteville, Bucksville, Market Place, Carolina Forest, Conway, Cross, Red Bluff, Sandy Run,
Richburg, Tillman, Batesburg); 15 are single-endpoint (partial) lines. Errors found: 0.

Reproduce from `pipeline/`: `uv run python -m southeast.scrtp fetch --cache <dir>` then `build --cache <dir> [--check]`.
