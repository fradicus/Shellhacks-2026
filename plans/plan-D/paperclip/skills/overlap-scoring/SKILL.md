---
name: overlap-scoring
description: Compute Gridlock pair signals (distance, shared facility, time gap, work-window overlap), labels, tiers, score, coordination zones, contention, sequence and the impact scenario. Use for anything that creates, labels or ranks pairs.
---

# Overlap scoring

Deterministic Python only. Gemini never computes any of this.

## 1. Sponsor core (must match the golden sample exactly)
```python
from math import radians, sin, cos, asin, sqrt
def haversine_mi(lat1, lon1, lat2, lon2):
    p1, p2, dp, dl = radians(lat1), radians(lat2), radians(lat2-lat1), radians(lon2-lon1)
    return 2 * 3958.8 * asin(sqrt(sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2))
```
- center = arithmetic mean of the located endpoints' lat and lon (one endpoint -> that point; none -> no center, no spatial pairs).
- nearby = `distance_mi < 25` (strict).
- time_gap_days = `abs((a.in_service - b.in_service).days)`.
- Pairs are cross-utility only; `_id` = sorted ids joined by `__`. Every pair appears once.
- Brute force over all DESC x GPC pairs (about 47 x a few hundred) is fine. Round only for display.

## 2. Extra signals
- **shared_facility**: `set(a.endpoint norms) & set(b.endpoint norms)` is non-empty **and** the matched endpoints' coordinates are within 2 mi. Normalization is in `osm-geocoding`. Store the shared name(s).
- **window**: DESC = `[Jan 1 of first year with spend > 0, in_service]`, kind `budget_proxy`; if there's no spend profile, `unknown`. GPC = `unknown`.
- **window_overlap**: both known -> `max(start) <= min(end)` -> `yes`/`no`; otherwise `unknown`. Never impute a construction duration.
- **confidence** = worst of the two projects' confidence.

## 3. Label and tier (T = 180 days default, editable in the UI)
```python
local  = nearby or shared_facility          # a shared substation counts as local even if long lines push centers > 25 mi apart
timely = window_overlap == "yes" or time_gap_days <= T
label  = "both" if local and timely else "nearby" if local else "timeline" if timely else None   # None -> pair not stored
if label in (None, "timeline"): tier = None  # timeline-only: Timeline matches tab only, sorted by time_gap_days
elif conf == "low":             tier = 3     # "needs review"
elif shared_facility or label == "both": tier = 1
else:                           tier = 2
```
Because the UI changes T, store `time_gap_days` and `window_overlap` and recompute `label`/`tier` in the client with the same rule. The Python version is the reference, and `test_overlaps.py` covers both.

## 4. Score (orders pairs within a tier)
```
proximity = 50 * (1 - d/25)                                   # nearby pairs only
timing    = 25 if window_overlap == "yes" else 25 * max(0, 1 - gap/730)
facility  = 15 if shared_facility else 0
synergy   = 10 * (0.5*same_kind + 0.5*shared_voltage)
score     = round((proximity + timing + facility + synergy) * {"high":1, "medium":0.85, "low":0.6}[conf])
```
Add `# ponytail: hand-tuned weights; tune with Sperry mentor feedback (hour 20)`.
`drivers`: the top 3 human-readable reasons, e.g. "shares McIntosh substation", "5.7 mi apart", "in service 152 days apart", "both 230 kV".

## 5. Coordination zones
Union-find over nearby pairs -> connected components with >= 2 projects. Per zone:
- `project_ids`, `bbox`, `date_span`, `cost_total` (published costs only; count how many are null)
- `contention_years`: years where >= 2 zone projects have overlapping known windows
- `sequence`: zone projects sorted by in_service, with the gap in days to the next one
Name each zone after its most common endpoint area (e.g. "Savannah River - McIntosh"); the CEO can rename it.

## 6. Impact scenario (per Tier 1-2 pair)
```
avoided_cost = avoided_mobilizations * cost_per_mobilization - coordination_cost
```
- `low`: avoided_mobilizations 0, which states the case honestly.
- `base` / `high`: use the researcher's cited unit cost from `data/sources.json`. Without one, use the contractor anecdote (freight ~30% of contract cost, $1.5M of $5M) applied to the **DESC published cost only**, labeled "anecdote, not measured".
- `shared_row_acres`: only when both projects have OSM line geometry and the lines run within 0.5 mi for L miles: `L * 5280 * width_ft / 43560`, width 100 ft (<= 115 kV), 150 ft (230 kV), 200 ft (500 kV). Otherwise null.
- Store every input with `{value, unit, source}` so the UI can show and edit it.

## 7. Tests (in `pipeline/test_overlaps.py`)
Golden sample: exactly OVL_1..6 nearby, distance +/- 0.05 mi, gap exact. Boundaries: 24.999 nearby,
25.000 and 25.001 not nearby; zero distance; same-utility pairs excluded; a missing center never pairs;
window overlap when the later start equals the earlier end is `yes`; leap-year gap; T boundary (180 is timely, 181 not).
