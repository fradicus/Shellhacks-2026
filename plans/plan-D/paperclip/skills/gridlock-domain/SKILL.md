---
name: gridlock-domain
description: Domain knowledge for Gridlock - the problem, both utilities and their sources, sponsor overlap rules, our signals and labels, golden sample, vocabulary, hard rules. Load before touching any Gridlock data or feature.
---

# Gridlock domain

## Problem
Neighboring utilities plan transmission construction in isolation. Projects that are close in space and time
could share crews, equipment, freight/mobilization, matting, outage windows and right-of-way. They could also
compete for the same scarce line crews, which pushes contractor prices up. A contractor told the sponsor that
freight alone was $1.5M of a $5M job, that sequencing jobs would stabilize prices, and that qualified line workers
are a finite, state-bound pool. FERC Order No. 1920 (2024) reformed long-term regional planning. Gridlock is a
coordination discovery aid, not a compliance tool, and it doesn't claim FERC requires crew sharing.

## Utilities and sources (manifest: `data/sources.json`)
- **DESC**, Dominion Energy South Carolina. Two public SCRTP lists, "Planned Transmission Projects $2M and above", one card per page with ID, description, need, status, in-service date and yearly budget:
  - 2025-2029: 47 projects, https://www.scrtp.com/assets/pdfs/home/2025-2029-2million-and-above-project-descriptions.pdf (Current mode)
  - 2024-2028: 44 projects, `docs/Sperry-Tech-Challenge/Project Listings/Dominion Energy/...` (Snapshot mode)
- **GPC**, Georgia Power. `docs/.../Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`, the "GA ITS Ten-Year Plan (2025-2034)" tables: zone, year, TEAMS number, name, need date, sponsor code. Costs are REDACTED.
- They meet along the Savannah River: the Augusta/Thurmond Lake area (GPC zone 215) and the Savannah/Jasper/Hilton Head area (zone 219). The 2025-2029 DESC list adds **Okatie - McIntosh 115 kV Tie: Add Series Reactor (ID 6888, 2028-12-31)**, a literal cross-utility tie into GPC's McIntosh, which is also in GPC projects. It's our headline shared-facility example once verified.

## Sponsor rules (exact)
Center = midpoint of the two located endpoints (one located -> that point). Nearby = haversine < 25 mi. Time gap = in-service difference in days. Geography primary, timing secondary. Most pairs don't overlap.

## Our additions (see `overlap-scoring`)
Signals: distance, shared_facility, time_gap_days, window_overlap (budget-window proxy), confidence.
Labels: both / nearby / timeline (T = 180 days, our editable assumption). Tiers 1-3. Coordination zones, contention, sequence.
An in-service date is a milestone, not a construction period. Say "in service N days apart", never "built at the same time".

## Golden sample (`Projects_Overlaps.xlsx`)
| id | mi | days | pair |
|----|----|------|------|
| OVL_1 | 4.09 | 3074 | DESC_2 Hooks-Thurmond 115kV / GPC_1 Evans Primary-Thurmond Dam #5 115kV |
| OVL_2 | 5.65 | 152 | DESC_3 Jasper-Okatie 230kV #2 / GPC_2 McIntosh-Purrysburg 230kV reactors |
| OVL_3 | 7.55 | 517 | DESC_3 / GPC_3 Goshen-McIntosh 115kV rebuild |
| OVL_4 | 8.01 | 3074 | DESC_1 Stevens Creek-Hooks 115kV / GPC_1 |
| OVL_5 | 14.34 | 365 | DESC_5 Okatie-Bluffton 115kV / GPC_2 |
| OVL_6 | 14.81 | 730 | DESC_5 / GPC_3 |
The other 19 of 25 pairs are correct negatives. Some xlsx dates are Excel serials (45809 = 2025-06-01, 45778 = 2025-05-01).

## Vocabulary
Transmission line, substation, right-of-way (ROW), tie line (connects two utilities), series reactor, rebuild,
reconductor, IRP, PSC, FERC, SERTP (SE regional forum; GPC is a founder, DESC is joining), SCRTP (publishes DESC's lists), CEII (never use).

## Hard rules
Public filings only; for GPC, only the table fields (see PROJECT.md). Never invent coordinates, dates, costs or
owners. Missing = null and visible. Deterministic code decides overlaps.
