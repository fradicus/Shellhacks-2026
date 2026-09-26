---
name: gridlock-domain
description: Domain knowledge for the Gridlock utility-overlap project - vocabulary, the sponsor's overlap rules, data sources, golden sample, CEII rule. Load before touching any Gridlock data or feature.
---

# Gridlock domain

## The problem
Neighboring utilities plan transmission construction in isolation. When two projects are close in
space and time, the utilities could share crews, equipment, freight/mobilization, and right-of-way.
FERC Order No. 1920 (2024) pushes utilities toward coordinated regional planning. A contractor told the
sponsor freight alone can be $1.5M of a $5M job, and line crews are a finite, state-bound labor pool.

## Utilities
- **DESC** - Dominion Energy South Carolina. Source: `docs/Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf` (SCRTP list, 44 project cards, has costs).
- **GPC** - Georgia Power. Source: `docs/Sperry-Tech-Challenge/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf` (668 pages; "GA ITS Ten-Year Plan (2025-2034)" tables; costs REDACTED).
- They meet along the Savannah River (Augusta/Thurmond area and Savannah/Hilton Head area). Real overlaps cluster there.

## Overlap rules (sponsor, exact)
- Center = midpoint of the project's two named endpoints; one endpoint located -> that point.
- Distance = haversine between centers, miles. **< 25 mi** -> one overlap row. Otherwise nothing.
- Time gap = |in_service_a - in_service_b| in days. Ranking signal only.
- Most pairs don't overlap. That's correct, not a bug.

## Golden sample (`docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx`)
| id | distance_mi | gap_days | pair |
|----|-------------|----------|------|
| OVL_1 | 4.09 | 3074 | DESC_2 Hooks-Thurmond 115kV / GPC_1 Evans Primary-Thurmond Dam #5 115kV |
| OVL_2 | 5.65 | 152 | DESC_3 Jasper-Okatie 230kV #2 / GPC_2 McIntosh-Purrysburg 230kV reactors |
| OVL_3 | 7.55 | 517 | DESC_3 / GPC_3 Goshen-McIntosh 115kV rebuild |
| OVL_4 | 8.01 | 3074 | DESC_1 Stevens Creek-Hooks 115kV / GPC_1 |
| OVL_5 | 14.34 | 365 | DESC_5 Okatie-Bluffton 115kV / GPC_2 |
| OVL_6 | 14.81 | 730 | DESC_5 / GPC_3 |
DESC_4 (Charleston) and GPC_4/GPC_5 (south Georgia) have zero overlaps. Some xlsx dates are Excel
serials (45809 = 2025-06-01, 45778 = 2025-05-01).

## Vocabulary
Transmission line (high-voltage, long distance) - Substation (voltage step/routing node) -
Right-of-way (ROW, land strip for a line) - IRP (long-term plan filed with state PSC) - PSC (state regulator) -
FERC (federal regulator) - SERTP (SE regional planning forum; GPC founder, DESC joining) -
SCRTP (SC process that publishes DESC's list) - CEII (confidential grid data: never use).

## Hard rules
- Public filings only. The GPC PDF is the public-disclosure version; use only what is printed, never try to recover REDACTED values.
- Never invent coordinates, dates, or costs. Missing = null + shown as missing.
