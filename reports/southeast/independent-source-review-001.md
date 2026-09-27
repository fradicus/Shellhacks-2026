# Independent Florida TLSA source review

Reviewer: `/root/f39_florida_review` (separate session from producer).
Reviewed at: 2026-09-27 01:24:54 UTC; final report written after this observation.
Scope: source counts, duplicate licensing records, identity discrepancies. No coordinate review or approval. No repository files changed.

## Pinned artifacts independently inspected

- `/private/tmp/gridbridge-southeast-sources/certified-facilities.pdf`, SHA256 `cdf0c45a140723769d3aa5921b430b07aa220dca4c245148cf00cc3a6eddbb63`. Official URL: https://floridadep.gov/sites/default/files/list_certified_facilities.pdf . Visually inspected supplied page renders `register-6.png` and `register-7.png`; page footer states prepared 1/20/2022. Page 6 has 11 TLSA rows; page 7 has 5 TLSA rows, followed by 2 natural-gas rows outside transmission scope. Total 16 named transmission projects in this PDF vintage.
- `/private/tmp/gridbridge-southeast-sources/transmission-attributes.json`, SHA256 `4d0611f68b0743df874795cfb1ea7921ab5a18c0b80bd2c00009295f61a5a483`. DEP layer: https://cadev.dep.state.fl.us/arcgis/rest/services/OpenData/ARMS/MapServer/5 . Exact original query parameters were not independently available in supplied file. Counted 16 features, 14 distinct certification strings. This is attributes only and contains no feature geometry.

## Findings

1. **Do not count GIS feature rows as projects.** TA07-16 has OBJECTID 11 (Duke Energy Florida) and 13 (Tampa Electric). TA90-08 has OBJECTID 15 (Seminole Electric) and 16 (JEA). These pairs describe jointly licensed lines. Official individual pages corroborate joint licenses. Retain both underlying records and ownership evidence; count each certification project once, unless subsequent primary evidence explicitly separates project components. Different SHAPE.LEN values do not themselves establish separate construction projects.
2. **PDF page 7 visibly contains an identity error.** Duval–Raven row has blank application/utility cells; following St. Cloud East–Magnolia Ranch North row bears TA16-17/FPL. Do not copy that assignment into normalized St. Cloud identity. Individual DEP Duval–Raven page establishes TA16-17, FPL, certification 2016-06-29. Individual OUC page establishes TA21-18, Orlando Utilities Commission, certification 2021-12-13. Each gives 230 kV. This independently resolves the licensing identities while retaining the incorrect PDF cells as source observations.
3. **The supplied pair of sources is not the current full certified-line inventory.** The live Conditions of Certification transmission table lists 17 facility entries: the GIS 14 project identities, St. Cloud–Magnolia, Sweatt–Whidden TA22-19, and DeLand West–Dona Vista TA25-20. It omits historical relinquished Lake Tarpon–Kathleen TA85-05, present on PDF p6. Thus union with historical PDF is at least 18 named certification-project identities, subject to acquiring/pinning current source and individual records. The current table says last modified 2026-08-11. This does not demonstrate that all Florida projects are covered; TLSA is a scoped permitting universe.
4. **Other discrepancies must remain explicit.** PDF Lake Agnes–Gifford row says 32.5 miles, only DEF portion constructed; GIS records and individual page say 27.5 miles. PDF counties Polk/Orange; GIS and individual page include Osceola. Do not infer entire project in service from certification or partial-construction note. TA90-08 PDF and individual page list Putnam/Duval, while GIS also includes Marion/Clay; retain discrepancy pending authoritative route review. DeBary PDF length 19 vs GIS 19.10000038; do not silently equate precision. Central Florida–Kathleen PDF lists Sumter/Polk while GIS additionally lists Hernando/Pasco. The duplicate county statements need reconciliation, not coordinate invention.
5. **Current index itself has another code discrepancy:** Bobwhite–Manatee label says TA07-14 on live Conditions table; individual page says TA06-14, agreeing with supplied PDF/GIS. Preserve discrepancy. Do not create separate TA07-14 project solely from index label.
6. **No location or current operating-status confirmation.** All centers should remain null for this checkpoint. Regulatory certification dates are not actual in-service dates. Official line descriptions identify endpoints but this review did not inspect endpoint geometries or establish coordinates.

## Exact official follow-up sources and locators

The following were independently browsed; their raw bytes were not downloaded/pinned by this reviewer, so no invented hashes are supplied. Producer should acquire and hash before using in a release.

- https://floridadep.gov/water/siting-coordination-office/content/conditions-certification — section `Transmission Lines`, rows Duval–Raven, St. Cloud–Magnolia, Sweatt–Whidden, DeLand West–Dona Vista, Bobwhite–Manatee; current table 17 rows. Displayed last modified 2026-08-11 13:07. Certification meaning explained above table.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-duval-raven-line — `General Information`: licensee FPL, TA16-17, 06/29/2016, 39 miles, 230 kV; Duval/Nassau/Baker/Columbia. Last modified 2024-10-11 13:46. Source line locator in web extraction 193–203.
- https://floridadep.gov/water/siting-coordination-office/content/ouc-st-cloud-magnolia-230-kv-line — `General Information`: OUC, TA21-18, 12/13/2021, 21 miles, 230 kV, Osceola/Orange. Endpoint text Magnolia North and St. Cloud East. Last modified 2024-10-11 13:47. Web extraction 193–203.
- https://floridadep.gov/water/siting-coordination-office/content/duke-energy-florida-llc-and-tampa-electric-company-lake-agnes — `General Information`: joint licensees, TA07-16, 02/18/2009, 27.5 miles, 230 kV, Polk/Osceola/Orange. Last modified 2024-10-11 13:46. Web extraction 193–206.
- https://floridadep.gov/water/siting-coordination-office/content/seminole-electric-cooperative-inc-and-jea-keystone-firestone — `General Information`: SECI and JEA, TA90-08, 06/12/1991, 70 miles, 230 kV, Putnam/Duval. Last modified 2024-10-11 13:42. Web extraction 193–203.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-bobwhite-manatee-line — `General Information`: TA06-14, 11/06/2008, 25.5 miles, 230 kV, Sarasota/Manatee. Last modified 2024-10-11 13:45. Web extraction 193–206.

## Decision

Source-count and duplicate findings above independently verified. Licensing ambiguity can be resolved by adding the independently identified official pages as pinned evidence. Do not publish a current source-complete claim from the two supplied artifacts alone. Do not promote any coordinates or treat this report as current-facts-hash approval of a generated release: no proposed release was provided for review.
