# C49: Alaska and Hawaii rollout

## Authority

On 2026-09-27 the user told this Claude local session to fill in Alaska and Hawaii with details and to see it
through. C22/F38 had left both states as stretch work needing their own source discovery. Claude local adopts the
technical-lead contract role for this change only; no existing ownership changes.

## Findings (origin/main `561351e`)

- The national snapshot has **0** records in Alaska (02) or Hawaii (15). The Census geography already carries
  both states; Alaska's bounds cross the antimeridian (`west` 172.46, `east` -129.97), so the per-rollout
  `west <= lon <= east` center check every CONUS release uses would reject every Alaska point. The web map already
  fits with `fit_west`/`fit_east_unwrapped`.
- Neither state publishes a machine-readable transmission project list (no RTO, no NERC region filing, no
  WestConnect/WestTEC rows). Public project facts are spread across documents:
  - **Hawaii:** the Hawaii PUC's public-hearing notices for overhead lines of 46 kV and more (HRS §269-27.5), the
    PUC FY2025 annual report's table of capital-improvement dockets, Hawaiian Electric's 2026 IGP Action Plan
    update and its project pages.
  - **Alaska:** the Alaska Energy Authority's September 2025 update, the USFWS September 2025 final EA for the
    Sterling–Quartz Creek rebuild, the Alaska Electric & Energy Cooperative project page and ARCTEC's project
    pages.
- OpenStreetMap names 143 substations in Hawaii but only 26 in Alaska; Sterling, Soldotna, Beluga, Bernice Lake,
  Healy and Teeland are absent, so most Railbelt projects will stay unlocated.
- Hawaiian Electric's Renewable Project Status Board lists generating facilities; F39 part 8 excludes generation,
  so these are excluded here too.

## Decision

1. **F49 (claude-local).** A committed, hand-transcribed file names each project, its state, owner, status,
   endpoint facilities and dated events. Every fact carries short verbatim quotes and a locator; the importer
   fetches each cited public document into a cache outside the checkout, hashes it and refuses to build when a
   quote is absent from the document text. Dates keep the stated precision (day, month or year); nothing is
   imputed.
2. **Locations follow C33's tiers with C38's operator guard,** matched by exact name against named OpenStreetMap
   substations in the project's state. The mission's center rule applies: mean of two located endpoints, one
   located endpoint is partial, a substation project is its site. Every point stays `unreviewed`. No county or
   area anchors.
3. **The release center check is antimeridian-safe:** longitudes are compared on the state's unwrapped
   `fit_west..fit_east_unwrapped` interval.
4. **Publication:** fixed release `data/akhi/releases/active.json`; F30's `load_snapshot` appends
   `("akhi", "akhi.publish")` after the last rollout under a separate `[FIX-F30]` claim.
5. Deferred, not rejected: individual PUC/RCA docket filings (in-service dates live there but need page-verified
   transcription), AEA's GRIP kickoff deck (the server truncates the download), Kauai Island Utility Cooperative
   and Southeast Alaska (SEAPA, AEL&P) projects.

## Undo

Delete `data/akhi/releases/active.json` (the hook becomes a no-op) or `data/akhi/`.
