# FPL next-source audit

Review UTC: 2026-09-27T02:56:43.404613+00:00
Reviewer: /root/f39_florida_review
Disposition: useful next source, but no acquisition/import or geometry approval of plan contents in this checkpoint.

## Access and restrictions change the next action

The official landing https://www.fpl.com/about/10-year-site-plan.html links a public Plan and Maps. Its Terms link points to https://www.nexteraenergy.com/legal-notice.html. The introduction explicitly includes fpl.com. Restrictions of Use limits copying/reuse and says personal use; Site Rules prohibits automated mining without prior express permission. These are an evidenced F39 source-safety issue, not a claim that public visibility licenses data extraction. I stopped further FPL-hosted acquisition after reading those terms. No raw FPL plan/maps were downloaded, no permissions were sought, and no access control was bypassed. The initial web-tool Maps click returned Internal Error; exact map artifact and geometry remain uninspected.

## Independently published regulatory path

PSC explicitly provides utility plans for agency/public review. Its public page https://www.psc.state.fl.us/ten-year-site-plans is an Angular shell. The published script defines GetTenYearSitePlans at the public API https://pscweb.floridapsc.com/api/Files/TenYearSitePlans and provides the filing base. Reading this ordinary page API exposed these exact links; filenames were not guessed:

- 2026: https://www.floridapsc.com/pscfiles/website-files/PDF/Utilities/Electricgas/TenYearSitePlans/2026/Florida%20Power%20and%20Light%20Company.pdf
- 2025: https://www.floridapsc.com/pscfiles/website-files/PDF/Utilities/Electricgas/TenYearSitePlans/2025/Florida%20Power%20and%20Light%20Company.pdf
- 2024 is also listed. The API listing is provenance for availability, not proof the contents or rights are identical across copies.

The 2026 API fileSize is28428 and2025 is54057 (consistent with KB). Web opening the exact2026 PSC link returned an explicit content-length rejection:29110791 bytes. Both exceed the current run's15000000-byte response cap. I did not split/range-download or circumvent that limit. Plan bytes/hash are therefore not acquired in this review. An explicit revised bounded acquisition checkpoint is needed before downloading these larger filings. The independently posted PSC version still requires content restriction inspection; government hosting alone does not establish unrestricted copyright permission.

The PSC2025 agency-review letter https://www.psc.state.fl.us/library/FILINGS/2025/03303-2025/03303-2025.pdf describes the plans as planning documents rather than permit-level detail. The PSC order https://www.psc.state.fl.us/library/FILINGS/2025/14797-2025/14797-2025.pdf page7 footnote2 independently cites the2025 FPL archive URL. Its Sweatt–Whidden discussion also demonstrates a possible existing-pilot match: dated construction information must become sourced history on the existing identity, not another certification project or unqualified current status.

## Preliminary content assessment from initial public web view

The landing identifies April2026 submission for2026–2035. The441-page Plan has III.E Transmission Plan at printed96; Schedule10 is labeled84 pages. These are source-section/form counts, not verified eligible-project counts. Sample Monarch BESS text (PDF page146, printed133) specifies a34.5kV bus extension and protective equipment but no additional transmission work. Schedule10 Sawgrass (PDF page357, printed344) states zero line miles. Excluding all zero-mile rows would miss actual substation work; accepting every form as a new line would fabricate work. Distinguish new/rebuilt transmission, qualifying substation construction, generation/storage-only work and explicit no-work records, then reconcile repeated components between sections. Preferred-site maps describe generation/storage sites; their boundaries or centroids cannot automatically locate transmission equipment. The exact eligible denominator, component grouping and map precision are unverified.

## Next action

Use an explicitly sized PSC2026 acquisition checkpoint, pin its complete hash, inspect restrictions and rendered III.E/Schedule10 pages, then enumerate every section/form with a disposition. Retain source dates and planned timing without inferring actual operation. Compare2025 by stable facility/work identity to build history. Seek public project-linked substation plans or regulatory GIS with coordinate meaning; do not promote generation labels, schematic route vertices or map centroids. No geometry source is approved by this audit.

## Request limits and receipts

Read data/southeast/manifests/run.json:45seconds,15000000bytes/response,one retry,30requests/source checkpoint. Three successful bounded raw responses were stored outside Git (HTML, published script, public API); one shell DNS failure preceded the HTML success. Web reconnaissance and failed opens remained below30 total source requests. No full plan or maps acquisition. Receipt JSON: /private/tmp/gridbridge-f39-fpl-source-receipts.json.

- /private/tmp/gridbridge-southeast-sources/fpl-psc-index.html: SHA-256 `1cb72ef2bafc94c3ba50a39a3e1bc80aecfbf661c1d8cdd31520514f34c4bd00`, 34665 bytes, retrieved 2026-09-27T02:54:55.433739+00:00; https://www.psc.state.fl.us/ten-year-site-plans
- /private/tmp/gridbridge-southeast-sources/fpl-psc-app.js: SHA-256 `f8b3534a38fed57c98d3aca3acccdd082dea86f1cd23ebe341e11c3b77b3b4ff`, 2893170 bytes, retrieved 2026-09-27T02:55:21.384052+00:00; https://www.psc.state.fl.us/main.67940d22092bb0d0.js
- /private/tmp/gridbridge-southeast-sources/fpl-psc-plans-index.json: SHA-256 `5e8aa0717f5ecbad5abfce44acd50cb70494fd0c96051fd3714389bc210dda05`, 155657 bytes, retrieved 2026-09-27T02:55:41.634576+00:00; https://pscweb.floridapsc.com/api/Files/TenYearSitePlans

No producer worktree, candidate, active release or database was changed.
