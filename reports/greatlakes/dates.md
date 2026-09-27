# F40: in-service dates for projects published without one

`greatlakes.dates` writes `data/greatlakes/dates/<source>.json`; `greatlakes.publish` fills only unknown
`in_service` values from it and keeps the evidence in `in_service_evidence`. A date is the utility's stated plan
("subject to change"), never proof of completion.

| Source | Dated | How |
|---|---|---|
| AEP project timelines (OH, IN, MI) | 99 of 127 | Timeline graphics are outlined SVG/JPG with no text layer, so each is rendered (qlmanage) and OCR'd (tesseract TSV). The date is the season/month + year printed directly under an in-service/complete label (bounding boxes, not reading order). Month names give month precision; seasons give year precision. |
| FirstEnergy 2026 LTFR (PUCO 26-0504-EL-FOR), Form FE3-T9 | 6 of 42 | "Operation" year, joined by OPSB case number (4) or the same two line terminals (2). Forms that disagree leave the date unknown. |

Effect on the national snapshot: Ohio 117 -> 46 undated, Indiana 31 -> 6, Michigan 11 -> 0.

**Check.** Reading-order OCR first mis-dated Delphos (axis year 2025) and Wheelersburg (Late 2027, the
pre-construction row); the bounding-box rule reads both correctly (Spring 2028). Seven images checked by eye under
the final rule, all correct: Wheelersburg, Delphos, Beatty-Canal, Fostoria-East Lima, Morse-Gahanna-East Broad, Lyka,
Pettit-Larez.

**Not done.** FirstEnergy's remaining projects state dates in OPSB Letters of Notification / Construction Notices
(10-130 MB PDFs, linked from each project page and on PUCO DIS by case number). PJM planning data was unreachable
(DNS failure) on 2026-09-27. AEP's own 2026 LTFR (26-0501-EL-FOR) names different lines than its public map.

Reproduce from `pipeline/` (macOS for qlmanage; tesseract 5.5.1): `uv run python -m greatlakes.aep fetch --cache <p>`,
`uv run python -m greatlakes.dates aep --pages <p> --cache <c> [--check]`,
`uv run python -m greatlakes.dates firstenergy --cache <c> [--check]`, `uv run python -m greatlakes.publish [--check]`.
