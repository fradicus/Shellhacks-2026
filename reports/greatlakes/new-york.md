# F40 New York

**423 project components, 279 with an unverified candidate location (172 distinct points), 0 verified.** Rule: [C26](../../specs/decisions/C26-great-lakes-candidates.md).

| | Count |
|---|---|
| Rows | 423 rows of Table VII, every row with a season/in-service mark and year (the text has 424 such lines; the extra one is footnote 2) |
| Grouping | 102 rows belong to a queue-numbered project (`parent_project`, e.g. queue 1125 = NYPA/National Grid Smart Path Connect); the rest are owner-numbered |
| Owners | National Grid 140, NYSEG 78, LIPA 67, NYPA 43, Con Edison 28, NYPA/Transco 20, Central Hudson 19, RG&E 10, others 18 |
| Status | planned 281 (Class Year, TIP and Firm Plans sections), proposed 88 (Non-Firm Plans), in service 54 (listed "In-Service", kept one year) |
| Candidate located | 279: 134 station sites, 68 lines with both terminals, 77 partial lines |
| Candidate located by status | planned 175, proposed 64, in service 40 |
| Unlocated | 144: terminal name not in OSM 126 (often new stations), not corroborated 15, state-line/tap/TBD terminals 3 |

## Source

- NYISO 2026 Load & Capacity Data Report (Gold Book), Table VII, "as of March 15, 2026".
  URL: https://www.nyiso.com/documents/20142/2226333/2026-Gold-Book-Public.pdf/a8fd42fe-5a8c-88cb-5052-f93dfd6423b8
- NYISO answers scripted requests with an empty HTTP 202 challenge, so the user downloaded the PDF in a browser on
  2026-09-27; the adapter refuses any file whose SHA-256 differs from `43865c1c…908bf`.
- Parsed from word positions (the PDF's table grid merges each row into one cell). Each row is a component; the From
  and To terminal columns are the facility names. "(New Station)" terminals are only matched once the row is In-Service.
- In-service is the stated year; the season (S/W) stays in the raw value. Negative line lengths are retirements of
  existing circuits and are kept as projects.
- Candidate geometry: OSM substations in New York (1,275 named), operator keys per owner (e.g. NGRID → National Grid /
  Niagara Mohawk, LIPA → Long Island Power / PSEG).

## Spot check

All 279 candidates reviewed by the producer; most carry both operator and voltage agreement. Fixed before commit:
a lone footnote number was read as a queue position; "Willis (Existing) – Willis (New)" was a two-endpoint line
instead of one site; "TBD" terminals were matched. Not an independent review.

Replay: from `pipeline/`, `uv run python -m greatlakes.nyiso build --source <downloaded PDF> --check`.
