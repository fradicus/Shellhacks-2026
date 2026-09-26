---
name: overlap-scoring
description: Compute project centers, haversine distances, in-service time gaps, overlap rows, ranking score and cost/impact estimates for Gridlock. Use for anything that creates or ranks overlaps.
---

# Overlap scoring

## Core (must match the sponsor exactly)
```python
from math import radians, sin, cos, asin, sqrt
def haversine_mi(lat1, lon1, lat2, lon2):
    p1, p2, dp, dl = radians(lat1), radians(lat2), radians(lat2-lat1), radians(lon2-lon1)
    return 2 * 3958.8 * asin(sqrt(sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2))
```
Center = mean of the located endpoints' lat and lon. Compare every DESC project with every GPC project
(~44 x a few hundred: brute force is fine). Keep pairs with `distance_mi < 25`. `time_gap_days = abs((a.date - b.date).days)`.
Round distance to 2 dp only for display.

## Score (0-100) for ranking
```
distance  = 60 * (1 - d/25)
timing    = 25 * max(0, 1 - gap_days/730)        # full credit same day, zero past 2 years
synergy   = 15 * (0.5*same_kind + 0.5*shared_voltage)
score     = (distance + timing + synergy) * {high:1.0, medium:0.8, low:0.5}[min confidence]
```
Mark in code: `# ponytail: hand-tuned weights; revisit with sponsor feedback`.
`drivers` = the top 2-3 human-readable reasons ("4.1 mi apart", "both 115 kV rebuilds", "5 months apart").

## Cost / impact estimate (bonus requirement)
Show assumptions next to every number.
- **Freight / mobilization savings**: freight ~30% of contract cost (contractor quote: $1.5M of $5M).
  If both projects are construction (not relay/reactor-only) and gap <= 365 days:
  `savings = 0.30 * min(cost_a, cost_b) * 0.25` (assume a quarter of freight avoided by sequencing one mobilization).
  GPC cost is REDACTED -> use the DESC cost for both and say so.
- **Shared right-of-way**: only when both are lines and their geometries run within 1 mi of each other for L miles:
  `acres = L * 5280 * width_ft / 43560`, width 100 ft (<=115 kV), 150 ft (230 kV), 200 ft (500 kV).
- **Crew-months**: note only qualitatively (finite state-bound line-worker pool).

## Output
`data/overlaps.json` sorted by score desc, `rank` 1..n, schema in PROJECT.md.
