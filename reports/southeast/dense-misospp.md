# Dense Southeast: MISO South and SPP planning workbooks (C40)

Batch `misospp`: 197 projects (131 MISO, 66 SPP) in LA, AR, MS and KY. 86 located, all unreviewed OSM name
candidates (84 `candidate`, 2 `candidate_unique_name`, 0 official), at 48 distinct points. 0 verified.

## Sources

| Source | URL | sha256 | Vintage | Access / CEII |
|---|---|---|---|---|
| MISO MTEP25 Appendix A (App. A, App. B, Facility sheets) | `cdn.misoenergy.org/MTEP25%20Appendix%20A%20-%20New%20Local%20Reliability%20Projects720399.xlsx` | `53f74cfe…335bbb` | as of 2025-08-28 | public CDN, no login; no CEII text in the workbook |
| MISO MTEP Projects Under Evaluation (MTEP26) | `cdn.misoenergy.org/MTEP%20Projects%20Under%20Evaluation368757.xlsx` | `40f325fe…4e72e` | as of 2026-07-31 | same |
| SPP Quarterly Project Tracking Appendix 1, 3Q 2026 and 4Q 2017–4Q 2025 (10 editions) | linked from `spp.org/spp-documents-filings/?id=18641` | pinned per edition in `sources.json` | quarter | public, no login; no CEII text in any Appendix 1/2 workbook |

OSM `power=substation` for LA, AR, MS, KY (Overpass, ODbL) is candidate geometry only. MISO's own project status
report is login-only and was not used (gap). `www.misoenergy.org` and third-party re-uploads were not used. SPP
editions before 2017 are `.xls`, which the installed stack does not read, so SPP history starts at 4Q 2017.

## Per state

| State | Projects (MISO/SPP) | Located (candidate / name-only) | Located, not in service | Located with dated events |
|---|---|---|---|---|
| LA (22) | 106 (65/41) | 58 (57/1) | 43 | 37 |
| AR (05) | 60 (35/25) | 24 (23/1) | 21 | 18 |
| MS (28) | 28 (28/0) | 5 (5/0) | 5 | 5 |
| KY (21) | 4 (4/0) | 0 | 0 | 0 |
| **Batch** | **197** | **86** | **68** | **59** |

Multi-state rows count in each state they list (El Dorado–Smalling is AR and LA). Some SPP lines also list OK, KS
or TX. Events: 156 `planned_milestone` (one for each changed expected in-service date in each edition), and 30
`in_service`, all dated from the listing's in-service date. 30 projects are in service (29 SPP, 1 MISO M4).

## Rules

- **MISO:** one MTEP project ID is one project. The newer workbook's facts win, and every row stays as an
  observation. No ID appears in both workbooks. One MTEP26 row (51433, IL; KY) is a duplicate of F40's
  `miso-mtep26-eval:51433`. One Appendix A ID cell is a date-formatted number, decoded to 50396 and confirmed by the
  Facility sheet. Locations come from the Facility sheet's From/To Sub when these give one site, or one line
  joining the only two substations. Otherwise they come from the project name. A program's facility row
  ("Asset Renewal Program") is never used as its location.
- **SPP:** one UID is one upgrade. The newest edition that lists the upgrade decides its state, owner and status.
  Older editions add 26 upgrades that later reports dropped after close-out, 24 of which have dated in-service
  events. The upgrade name is parsed first. From/To bus names are used only when the upgrade name repeats them:
  model buses such as `WESTERN ELECTRIC T` / `WARWICK 138` on the Southwest Shreveport–Seminole rows are ignored.
- **SPP owner check for state tags:** AEP (SWEPCO: LA, AR) and AECC (AR) are accepted as tagged. SPS, NWE, ITCGP
  and EKC are excluded because their systems are in other states (10 upgrades, 14 rows across editions, e.g. NWE "Groton to Aberdeen", ITCGP
  "Thistle", SPS "Roadrunner"). Other owners (OG&E, GRDA, EDE, WFEC, SWPA, ETEC, TBD) are accepted only when a
  facility the row names matches an OSM substation in the tagged state. That check keeps OG&E's Fort Smith rows
  and excludes Oklahoma rows mis-tagged AR (Tahlequah, Northwest–Spring Creek) and OG&E's LA-tagged Seminole line.
- The C38 operator guard applies throughout. `Ft` is expanded to `Fort`, and leading queue or coop tags
  (`J2143`, `DEMCO`) are removed before parsing. The OSM name match itself stays exact.

## Unlocated (111)

no OSM facility with the exact name 76, work or program names with no facility named 25, multi-facility 5,
operator conflict 4 (e.g. SPP "Welsh" is an Entergy 69 kV substation in LA, and the source's Welsh is SWEPCO's plant
in Texas), ambiguous 1 (Sterlington: four OSM areas more than 1 km apart). Many are new stations such as Benoit,
Bluepoint and RiverPlex.

## Spot check (12 random located records, seed 39)

Independence (Tangipahoa Par.), Baxter Wilson (Vicksburg), Fort Smith ×3 (terminal upgrade, transformer, and the
Fort Smith–Sooner partial), Richard (Acadia Par.), Tiger (Baton Rouge), McAdams (Attala Co.), Southwest Shreveport,
Webre (Babel–Webre partial), Ellerbe Road–Lucas (Shreveport), Waterford (St. Charles Par.). Each matched facility
is at the named place, with operator and voltage consistent with the text. **Errors: 0.** One caveat: "Waterford
500 kV" matched the only Waterford in OSM, the 230 kV yard. It is labeled name-only.

## Known gaps and overlaps

- The `aep` batch has SWEPCO's own point for "South Shreveport – Wallace Lake". SPP UID 122730 (Rebuild #2, complete
  2025-12-29) is the same corridor. Flint Creek and Lieberman work may be related. These are not merged.
- Several located upgrades share a site: 21 Southwest Shreveport rows and 9 Fort Smith rows (including partial lines) sit on one
  point each.
- Borderline exclusions: GRDA "Siloam Springs City" (the city is in AR, but GRDA's AR presence is not
  established), ETEC "Stanley–Huxley" (LA–TX), and TBD "Chamber Springs – South Fayetteville" (OSM spells it
  "Chambers Springs").
- MS and KY coverage is thin: Cooperative Energy and Big Rivers names rarely match OSM, and MISO has no Mississippi
  Power or TVA projects.

Reproduce from `pipeline/`: `uv run python -m southeast.misospp fetch --cache <dir>`, then `build --cache <dir> [--check]`.
