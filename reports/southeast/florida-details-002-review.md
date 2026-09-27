# Independent Florida detail acquisition002 review

Reviewer `/root/f39_florida_review`. All11 cached files independently read using a separate stdlib HTML parser and narrative inspection; all11 SHA256 values match acquisition receipts. Review time: 2026-09-27T02:16:18.736330+00:00. No producer changes, coordinates or final release approval.

## Key discrepancies

1. **Duval–Poinsett description conflicts with its identity and GIS.** The detail page says two500kV lines from Duval through Rice end at Kathleen. Previously inspected GIS says Rice/Rima/Poinsett; the page title/index name is Duval–Poinsett. Preserve raw wording but quarantine the Kathleen endpoint claim. Do not locate the project using Kathleen or quietly substitute a corrected description without an explicit primary-source resolution.
2. **DeLand West–Dona Vista uses narrative, not a General Information table.** A table-only extractor must report unsupported layout or use an explicit tested narrative adapter; empty extraction must not pass as complete. Narrative gives TA25-20, Duke Energy Florida, new230kV line, approximately26.26miles, DeLand West/Volusia to Dona Vista/Lake, crossing Umatilla/Eustis. Project Filings lists application filed2025-08-22, final certification order filed2026-01-20. The latter is a filing date, not necessarily a separately verified certification-effective date. Inspect the order before creating a plain Date Certified event. Hearing cancellation notices are not project cancellation. Stale narrative 'application is being processed' coexists with a final-order link; do not infer current construction status from either.
3. **Sweatt–Whidden Voltage cell contains230 without units.** Title independently says230kV, allowing explicit title-supported voltage normalization. Preserve raw230. Date Certified9/22/2022 supports day-precision certification only, not operation.80miles, Sweatt/Okeechobee to Whidden/DeSoto; listed counties DeSoto/Glades/Highlands/Okeechobee.
4. **Midway–Jensen–Crane route wording differs.** Detail describes branch east to Jensen and then south ending Crane; GIS describes distinct eastward Jensen and southward Crane branches from Turnpike3. Named facilities agree, but route topology should not be inferred from either paraphrase without route evidence.
5. County and length discrepancies already identified remain: Central Florida–Kathleen detail includes Hernando/Pasco absent historical register; DeBary19.1 vs register19; Levee detail Miami-Dade vs legacy Dade is a name variation that needs explicit geographic normalization.

## Reviewed General Information facts

All certification IDs below match current index, aside from the separately resolved Bobwhite record not in this acquisition. Dates are sourced MM/DD/YYYY converted to ISO day precision; no day/month precision invented.

| Project/code | Certification date | Length miles | Voltage | Source counties |
| --- | --- | --- | --- | --- |
| Central Florida–Kathleen TA81-02 |1982-07-26|44.5|500kV|Sumter,Polk,Hernando,Pasco|
| Duval–Poinsett TA81-03 |1982-11-18|175|500kV|Duval,Clay,Flagler,Putnam,Volusia,Orange,Seminole|
| Midway–Jensen–Crane TA83-04 |1984-01-17|22.5|230kV|St.Lucie,Martin|
| Crane–Bridge–Plumosus TA88-06 |1989-08-08|40|230kV|Martin,Palm Beach|
| Levee–Midway TA89-07 |1990-04-20|150|500kV|St.Lucie,Martin,Palm Beach,Broward,Miami-Dade|
| DeBary–Winter Springs TA92-09 |1993-05-11|19.1|230kV|Seminole,Volusia|
| Collier–Orange River TA03-12 |2004-07-19|53.9|230kV|Collier,Lee|
| St.Johns–Pellicer–Pringle TA05-13 |2006-04-27|26.1|230kV|St.Johns,Flagler|
| Willow Oak–Wheeler–Davis TA07-15 |2008-08-07|30|230kV|Hillsborough,Polk|
| Sweatt–Whidden TA22-19 |2022-09-22|80|230 raw; title230kV|DeSoto,Glades,Highlands,Okeechobee|
| DeLand West–Dona Vista TA25-20 |not supplied as Date Certified|26.26 approximate|230kV narrative|Volusia,Lake|

Licensees: Duke Energy Florida LLC for Central Florida–Kathleen and DeBary; Tampa Electric for Willow Oak–Wheeler–Davis; FPL for the other seven tabular pages. DeLand narrative names Duke Energy Florida as applicant/project company, not a tabular equipment-owner field. Preserve these role meanings. None of these pages establishes current asset ownership merely by listing a licensee, and none supplies an actual in-service date. General prose 'connects' is not independent evidence of current service status.

## Access assessment

All receipts stay on official floridadep.gov domains; old /air paths redirect to /water. Read page bodies and scanned for confidential/CEII/restricted/distribution wording: no source-specific access prohibition identified. Standard DEP copyright footer is present; use bounded factual extraction with attribution, not copying whole prose/pages into product. Do not automatically acquire linked application or regulatory attachments without their own content/access review. No private contact details need incorporation in project data.

## Exact source provenance

Locators are General Information table field labels for the first10; DeLand uses opening project paragraph and Project Filings list. Each source listed below was individually read; hashes recomputed match receipts.

- https://floridadep.gov/water/siting-coordination-office/content/duke-energy-florida-llc-central-florida-kathleen-line
  - File: `duke-energy-florida-llc-central-florida-kathleen-line.html`; SHA256 `5a4f3e82ea6b959ef0b8abe257536ae699799b4de30c4766816c010460b79d60`; retrieved 2026-09-27T02:14:38.252400+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-duval-poinsett-line
  - File: `florida-power-light-duval-poinsett-line.html`; SHA256 `60ffdb3435b722f9470de4a778d7cc7f20d6aa3d45867fca96563a3339ce6afb`; retrieved 2026-09-27T02:14:38.251986+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-midway-jensen-crane-line
  - File: `florida-power-light-midway-jensen-crane-line.html`; SHA256 `a52c7b79768de771608a9fd6916344f26ac541ff26f62ea5d179cc56706be490`; retrieved 2026-09-27T02:14:38.288737+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-crane-bridge-plumosus-line
  - File: `florida-power-light-crane-bridge-plumosus-line.html`; SHA256 `f7f5309706b6bd008a758d543d12e4d9f90d5a15c4ae22274897a5bfb6ebd0c8`; retrieved 2026-09-27T02:14:38.284388+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-levee-midway-line
  - File: `florida-power-light-levee-midway-line.html`; SHA256 `1d0104161037ee19fed04cb475f6d0883a5b2cc10e1bc3e27b97076e54d327c8`; retrieved 2026-09-27T02:14:39.044164+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/duke-energy-florida-llc-debary-winter-springs-line
  - File: `duke-energy-florida-llc-debary-winter-springs-line.html`; SHA256 `4cb95394272d2db953779c81005fa99fc5135e2c43a70a5b5e61ed0c0964ff6c`; retrieved 2026-09-27T02:14:39.006179+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-collier-orange-river-line
  - File: `florida-power-light-collier-orange-river-line.html`; SHA256 `7b79b867a134ff5790366babbbda50f35d58aaa261f89118dcf3b45126f929ae`; retrieved 2026-09-27T02:14:39.041444+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/florida-power-light-st-johns-pellicer-pringle-line
  - File: `florida-power-light-st-johns-pellicer-pringle-line.html`; SHA256 `e83e291f25aaa0b1b45f66d2f7cbbc2e7bf681b3a5236ae7c66e6ac1858cf527`; retrieved 2026-09-27T02:14:39.050573+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/tampa-electric-company-wheeler-davis-willow-oak-line
  - File: `tampa-electric-company-wheeler-davis-willow-oak-line.html`; SHA256 `8a804e957dbe5a185a455e54a3c22d8f19f5d983768842f5d31b8f1a9d4ab3d4`; retrieved 2026-09-27T02:14:39.746003+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/fpl-sweatt-whidden-230kv-line
  - File: `fpl-sweatt-whidden-230kv-line.html`; SHA256 `6f7a214b74f49dedd36c203dba4147b194b1cdabad66a3b5e0bad271a86d42e6`; retrieved 2026-09-27T02:14:39.556665+00:00.
- https://floridadep.gov/water/siting-coordination-office/content/def-deland-west-dona-vista-230kv-transmission-line-project
  - File: `def-deland-west-dona-vista-230kv-transmission-line-project.html`; SHA256 `50ab4237d0d43f143164c024d0e44a8079ecfde4dd7cb3aa7bbc1683a0528c32`; retrieved 2026-09-27T02:14:39.501557+00:00.

## Decision

Acquisition integrity verified for all11. Ten table records support factual extraction with explicit discrepancies above; DeLand requires narrative-specific handling. This plus prior5 details and Hopkins covers17 linked detail pages, not a claim that all17 normalized records are ready or all Florida projects are covered. No current-status, endpoint geometry or final release approval.
