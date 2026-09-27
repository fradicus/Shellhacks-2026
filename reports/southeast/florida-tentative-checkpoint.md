# Florida tentative locations checkpoint — 2026-09-27

The user asked for about 100 Florida markers, accepting tentative locations but not county centers. This release adds
237 source-backed Florida projects. 129 have a tentative point, at 99 distinct coordinates. With the reviewed DEP
Hopkins–Bainbridge point, the national snapshot draws 130 Florida projects at 100 distinct positions. 108 new
projects stay unlocated and searchable. **No county center is used, and nothing is independently confirmed.**

| Source | Rows | Projects | Tentative points |
|---|---:|---:|---:|
| FRCC Regional Load & Resource Plan, Form 13, editions 2012–2026 | 266 | 118 (+4 DEP duplicates) | 53 |
| FPL Ten Year Site Plan, Schedule 10, 2024–2026 | 168 | 119 | 76 |

Location basis: two terminal references (midpoint) 10; one terminal/site reference 56; EIA-860M plant point 63.

## How locations were chosen

- **FRCC lines:** each terminal name is matched exactly against named OSM `power=substation|plant` elements in Florida.
  A match fails when the OSM operator belongs to a different utility (for example, TECO "Davis" does not
  match FPL's Davis substation), when more than one compatible facility exists, or when the two endpoints lie farther
  apart than max(3× the reported length, 40 km). With both terminals matched, the point is their midpoint.
  With one, it is partial: that terminal only.
- **FPL Schedule 10:** the order is (1) an OSM match for the new substation Schedule 10 names; (2) EIA-860M plant
  coordinates for the named energy center, only when EIA's county equals the reported county (this rejected
  Saddle Solar: DeSoto vs Calhoun); (3) the OSM point-of-origin substation (partial).
- A line appears once across editions. The latest listing supplies owner, status and date; every edition's row
  is kept as an observation. Lines absent from the 2026 edition have `status_group: unknown` and no
  in-service date. A projected date is not completion.
- Four FRCC lines match reviewed DEP certifications (TA05-13, TA16-17, TA22-19, TA89-07). They are recorded as
  duplicates of those IDs, not as new projects.

## Gaps

- FRCC 2010–2011 are image-only PDFs and 2009 is poorly OCR'd; they are not parsed. 2014's PSC copy under
  `FRCC_RLRP.pdf` is a presentation; the plan comes from `FRCC_2014_Load_Resource_Plan.pdf`.
- 157 FRCC terminal names have no OSM match (mostly new Duke solar substations). FERC Form 1 page 424
  (lines added) was not ingested; the PUDL SQLite exceeded available local disk.
- Other utilities' Ten Year Site Plans (Duke, TECO, JEA, Seminole) are not yet parsed beyond their FRCC Form 13 rows.

## Reproduce

```sh
cd pipeline
uv run python -m southeast.florida_tentative acquire /private/tmp/f39-fl-raw
uv run python -m southeast.florida_tentative build /private/tmp/f39-fl-raw
```

`build` needs poppler's `pdftotext`. National assembly replays the committed observations and ledger through
`southeast.publish.apply_release` and stops on any hash, count or identity drift. OSM-derived references are
© OpenStreetMap contributors, ODbL 1.0.
