# New England location release: 345 project records

Release `f38-new-england-345-v1` updates existing ISO-NE project/component IDs. It creates zero new project identities. C23 supplies the evidence contract; F30 assembles it; F31 presents and exports it. This is a bounded New England increment, not completion of F38 or national coverage.

## Before and after

The live Atlas API at `http://localhost:3000/api/national?planningregion=iso-ne&limit=1` reported dataset `a0cfee7da1d0e5e097fae74db21f5c8aad9af60e`, 1,024 ISO-NE records and **zero located** before publication. Offline assembly with the F30 hook validates all 1,286 national IDs unchanged and increases located records from 69 to 414. The authorized load Action subsequently activated this same projection; the live receipt below confirms the actual database counts.

| State | Confirmed project/component records |
|---|---:|
| Massachusetts | 115 |
| Connecticut | 91 |
| Maine | 61 |
| New Hampshire | 33 |
| Rhode Island | 27 |
| Vermont | 18 |
| Total | 345 |

The records reference **187 distinct facility IDs/coordinates**: 212 standalone-site projects, 41 projects with both endpoints, and 92 with one endpoint only. Multiple components can share a facility: the 345 records occupy **199 distinct canonical map positions**. Neither 345 nor 199 is a count of separate substations. Line centers are the arithmetic mean of two supported endpoints or the single supported endpoint, following the existing contract. They do not locate individual replacement structures or a route.

Lifecycle cohorts remain the June 2026 workbook observations: **329 in service, 13 planned, 3 under construction**. No cancelled record receives a new location. No new completion dates or historical events are asserted. Unknown contractor, county, geometry accuracy and other original fields remain unknown.

## Source and evidence boundaries

- ISO-NE June 2026 RSP workbook: 1,024 original rows/IDs, pinned SHA256 `adfe05f5c0f24e260acca3b10c692785b4298a2067fa2e79efcf1d079953190d`. Existing project facts are bound in full to each review. The prior checkpoint independently replayed all workbook rows and audited the selected source fields; location reviews inspect each accepted project's identity and row.
- NOAA Coastal Services Center, hosted by Massachusetts CZM: historical **2013-06-05**, 526 facility points, digitized at **1:40,000**. 343 accepted project links use 185 unique facilities. Original Web Mercator coordinates and independently recomputed WGS84 are retained. Numeric precision does not imply survey accuracy; uncertainty in metres remains null. The GIS has no current owner/voltage fields. Only explicit, unambiguous named facility links in the same state passed independent review; aliases and unresolved identities were withheld.
- Vermont PSD/VCGI: two additional sites, Hartford and Chelsea, use utility-submitted/E911 records with stable ESITEIDs, original Vermont State Plane geometry and independently reproduced ArcGIS datum transformation. VELCO's 2017 plan and a regulator-hosted 2018 environmental report support the project/site links. The environmental report is not evidence of an exact construction completion date. Site geometry vintage and accuracy remain unknown.
- NOAA and HIFLD-derived geometry can share ancestry. Their agreement is not independent identity proof. Conflicts at Fall River, Bridgeport Resco and Raven Farm were quarantined. The independent reviewer is separate from the producer and inspects each promoted record; this is not a claim of independent surveys.
- National Grid portal redistribution restrictions excluded its data. Eversource access/rights remain unresolved. Confidential source material was excluded. No raw PDFs or restricted datasets are distributed here; approved factual extracts, evidence links/hashes and review decisions are retained.

## Reconciliation and gaps

`dispositions.json` accounts for every one of the 1,024 ISO-NE records: **345 confirmed, 335 cancelled and deferred, 190 insufficient after review, 154 without an accepted candidate**. 679 remain unlocated. The NOAA review ledger contains 535 candidate dispositions: 343 accepted and 192 withheld; two of the withheld IDs were independently resolved using Vermont evidence. Vermont's additional candidate reviews remain recorded but are not automatically promoted.

All six states are partial coverage. This source pass does not establish statewide denominators, all utilities, current activity or historical archive completeness. The June 2026 workbook is the imported project vintage; NOAA's older geometry does not refresh lifecycle status. Priority follow-up is unresolved planned/under-construction project identity, newer eligible utility/regulator geometry, competing-coordinate resolution, prior comparable RSP vintages and F19's `/time` integration (issue #139). `/explore` is the F31 delivery surface; do not mark the main `/time` acceptance complete without its owner.

## Replay and review

Run from the repository root (Python environment from `pipeline/`):

```bash
PYTHONPATH=pipeline pipeline/.venv/bin/python -m expansion.assemble \
  --noaa-review data/expansion/batches/new-england-locations/noaa-review.json \
  --noaa-manifest data/expansion/batches/new-england-locations/noaa-manifest.json \
  --vt-review data/expansion/batches/new-england-locations/vermont-review.json \
  --vt-manifest data/expansion/batches/new-england-locations/vermont-manifest.json \
  --vt-proposals data/expansion/batches/new-england-locations/vermont-proposals.json
PYTHONPATH=pipeline pipeline/.venv/bin/python -m pytest tests/pipeline/test_f38_publication.py -q
```

The exact deterministic proposals hash is `b666d69343b0627be84548083e1aad70378a39a65ca0b53d9ec4b2a8ecb4f5fa`. Final approval receipts cover exactly the proposal set and bind each record excluding only its append-only reviews. The committed release contains the creation timestamp; replaying it is deterministic. The initial finalizer refuses to overwrite an existing release. Future corrections require a reviewed superseding release.

The fixed `data/expansion/releases/active.json` is the only activation input; research files cannot activate points. Missing/stale/rejected/conflicting reviews do not publish centers. Invalid current facts, self-review, future timestamps, bad geometry and invalid events fail closed before mutating the snapshot. Atlas remains writable only by the existing load Action and uses one atomic dataset pointer.

## Validation

24 targeted publication tests pass, including exact approval sets, stale facts, source projection, endpoint semantics, status/date preservation, all 345 committed approvals and all 1,024 dispositions.

F38 release PR #142 merged as `6a038d92b0309f4dd040516ce2f05ad2d0334b22` after required hosted CI passed. Final local checks: ruff passed; **422 pytest passed, 1 skipped**; web lint, typecheck and fixture production build passed; spec lint passed for 31 features; all 17 changed paths passed F38 ownership. Whitespace/stat review found no secrets, read-only inputs or unrelated changes. The existing Big Shoulders fallback-font warning was nonfatal.

F31 evidence/export PR #148 merged as `3ab64daf2833df53cd0e594a4123203993fc5eeb` after required hosted CI passed. Its actual assembled-snapshot browser check selected Chelsea, exposed the pinned evidence and matching review receipt, verified complete/partial endpoint labels, and found no horizontal overflow at 390px. Optional legacy landing smoke failures are tracked separately in #134/#150; optional Azure testgen failure is tracked in #130. These failures were not silently reported as passing.

F30 loader integration PR #147 merged as `8c9d90d85b6a94ea3e2c014a282623ef751a811a` after required hosted CI passed. Its full local checks passed, including **428 pytest passed, 1 skipped**. The original local main checkout has been fast-forwarded through this merge.

## Live Atlas publication

The sole-writer [load Action](https://github.com/fradicus/Shellhacks-2026/actions/runs/36287012823) succeeded on 2026-09-27. Its log reports 26 national sources, 1,286 national projects and active dataset `8c9d90d85b6a94ea3e2c014a282623ef751a811a` at 01:56:20 UTC. A redundant queued manual dispatch was cancelled before execution; no local database writer was used.

At **2026-09-27 01:57:22 UTC**, read-only checks through the actual Atlas-backed app at `http://localhost:3000` verified:

- All 345 published location evidence/review records exactly match the approved release.
- Every published center equals its approved site or endpoint mean; original project IDs, statuses and other facts remain unchanged.
- ISO-NE: **1,024 records, 345 located, 679 unlocated**. National: **1,286 records, 414 located**; the pre-existing 69 locations are not newly verified by this release.
- All six state API/map-record counts match the table above, under the same dataset ID.
- JSON export retains the complete source and review evidence, including unknown precision/uncertainty.

See `new-england-live-api-receipt.json` for the exact timestamp, counts, active dataset and export hash. `new-england-location-coverage.json` reconciles all 28 primary-owner labels, states, lifecycle cohorts and shared positions. These checks establish the real Atlas dataset through the local application; no remote production-host deployment is claimed. The browser receipts below complete the live check.

## Live browser acceptance

Browser checks completed at **2026-09-27 01:59:43 UTC** against the same real Atlas dataset through localhost:3000. Default filters show 1,286 records / 414 evidenced map records / 872 unknown locations, with the New England cohort visible. All six state filters match their API counts. Selected examples were CT 1054 (partial endpoint), MA 1000 (complete endpoints), ME 1029, NH 1137, RI 1095 and VT 1617 (site points). Clicking the actual Chelsea marker opens the selected project's independently reviewed evidence. Expanded source URLs, source dates, precision, original/transformed geometry and review hashes match the JSON export. The 390px mobile view has client and scroll widths of 380px, with no horizontal overflow.

- [Default map](evidence/new-england-default-desktop.jpg)
- [Selected Chelsea marker](evidence/chelsea-map-selected.jpg)
- [Expanded source/review evidence](evidence/chelsea-evidence-desktop.jpg)
- [Mobile evidence](evidence/chelsea-evidence-mobile.jpg)

`new-england-live-browser-receipt.json` retains the six-state browser observations. This completes the bounded Atlas-to-`/explore` delivery. `/time` remains pending with its separate owner in issue #139; broader geographic and history acceptance remains incomplete.

Final audit-checkpoint checks: ruff passed; **428 pytest passed, 1 skipped**; web lint, typecheck and fixture production build passed; spec lint passed for 31 features. Ownership and hosted CI are recorded in PR #155. Only F38 reports and its own spec status are changed in that checkpoint; no release facts or approvals were changed after publication.
