---
name: source-audit
description: Build and check Gridlock's public-source manifest - download, hash, public-status review, owner-code mapping, version linking, citations. Use when adding, questioning, or verifying a data source.
---

# Source audit

## Manifest: `data/sources.json`
One entry per source:
`{id, title, publisher, url, local_path, sha256, filing_date, retrieved_at, pages, public_status, notes}`
- `public_status`: `public` | `public_with_banner` (GPC: "PUBLIC DISCLOSURE" plus a CEII banner) | `excluded`.
- `excluded` sources are never parsed, sent to Gemini, or linked.
- Compute sha256 with `hashlib`. `source-watch.yml` re-hashes the URLs weekly and opens an issue when one changes.

## Owner codes (GPC Ten-Year Plan "Project Sponsor")
Build `owner_codes` in the manifest, e.g. GPC = Georgia Power, SAV = Savannah area (verify from the IRP text),
GTC = Georgia Transmission Corp, MEAG = MEAG Power. Cite the page for each code. Unknown codes stay `unknown`.
The product labels a row "Georgia Power" only when its code maps to GPC. Other ITS owners are kept, get a distinct
map style, and are called out in the UI.

## Version linking (DESC)
Match projects across the 2024-2028 and 2025-2029 lists by Project ID (fall back to normalized name). Record
changed in-service dates, costs and status in `versions[]`. Changes are a feature in the UI ("date moved +12 months").

## Unit costs for the impact scenario
Look for public, citable mobilization or crew/equipment day rates for transmission construction (utility rate
cases, PSC dockets, state DOT bid tabulations, federal cost studies). Record `{value, unit, year, url, page, quote}`.
If none is defensible within about 1 hour, record `none_found`; the scenario then uses the labeled anecdote.

## Citations
Every factual claim another agent asks about gets `{source_id, page, quote}`. PDF page numbers are the physical
page (1-based), which is what the `#page=N` URL fragment uses.
