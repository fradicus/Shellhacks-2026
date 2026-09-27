---
id: F43
name: Route-based fleet mobilization cost comparison
lane: B
agent: technical-lead
phase: 6
depends_on: [F17]
owns: [web/lib/mobilization/, web/components/mobilization/, web/app/mobilization/, web/app/api/mobilization/, data/reference/mobilization/, tests/web/mobilization/]
cut: allowed
status: draft (spec handoff; needs a C-decision and a roadmap row before implementation)
---

# F43 Route-based fleet mobilization cost comparison

## Why this exists

F17 already computes `potential = avoided_mobilizations × unit_mobilization_cost − coordination_cost`, but the
PM has to type `unit_mobilization_cost` from nowhere. F43 builds that number from actual route legs and fleet
facts, then compares two schedules for the same pair of jobs:

- **Separate:** each job gets its own fleet trip: depot → job A → depot, and depot → job B → depot.
- **Sequenced:** one fleet goes depot → job A → job B → depot.

The output is a **modeled difference in transport cost** between those two schedules, computed from user-entered
or cited inputs. It is a number for a follow-up conversation. It is not savings, a quote or a promise
(see [mission](../../mission.md): "Impact dollars only from cited or user-entered inputs", "never savings").

The teammate's routing work supplies distances and drive times. This feature does not do routing.

## Before you start (agent checklist)

1. Read `specs/overnight.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/vocabulary.md`, F17's
   [spec](../F17-impact-scenario/spec.md) and [decision](../../decisions/F17-mobilization-scenario.md), and the
   C15 route contract in [C15](../../decisions/C15-verified-operations.md).
2. Write a decision record, `specs/decisions/C34-mobilization-cost.md` (use the next free C number), that authorizes
   F43 and records the **cited reference value** rule below. F17's decision says "without default rates", and
   F43 must not quietly contradict it.
3. Add the F43 row to `specs/roadmap.md` and to `local_workers` for whichever local worker takes it.
4. Read `web/components/impact/model.ts` and match its idiom: string inputs, blanks stay null, integer cents,
   `Number.isSafeInteger` guards, `node --test` unit tests.

## Hard rules (inherited, non-negotiable)

- **No silent defaults.** Every numeric input starts blank. A blank input makes every dependent output null.
  Explicit zero is allowed and is different from blank.
- **Cited reference values** are allowed only as a visible, opt-in button next to an input
  ("Use EIA Lower Atlantic diesel, week of 2026-09-21: $6.139"). Clicking copies the value into the field and
  records `{source, url, as_of, retrieved_at}` in the input's provenance. The user can overwrite it. A cited value
  that has not been clicked is never used in math.
- **No blanket multipliers.** Never compute the sequenced case as `separate × 0.65` or any fixed ratio. Both cases
  are built from their own legs. The difference comes out of the arithmetic.
- **No invented rates.** No hard-coded diesel price, MPG, wage, escort rate or setup cost in the math module.
  Reference values live in `data/reference/mobilization/*.json` with a citation for every number, or they don't exist.
- **Money in integer cents.** Reject nonfinite, negative (unless stated), oversized or over-precise inputs, as F17 does.
- **Negative results stay visible.** Sequencing can cost more (e.g. a long A→B hop, or days of paid waiting).
- **Milestone ≠ work window.** A pair's in-service gap is not the idle time between jobs. Idle/wait days are a
  separate user input.
- **Language:** "modeled transport difference", "possible shared mobilization". Never "savings", "saves",
  "will cost". Label all scenario output "user scenario".
- **Secrets:** `EIA_API_KEY` and `GSA_API_KEY` are server-only. Never `NEXT_PUBLIC_*`. No keys in git.

## Inputs

### 1. Route legs (from the teammate's routing)

This is the contract the routing work must produce. F43 validates it strictly and does not guess missing fields.

```ts
type RouteLeg = {
  id: string;                    // e.g. "depotA->jobA"
  from: { label: string; lat: number; lon: number };
  to:   { label: string; lat: number; lon: number };
  miles: number;                 // road miles, > 0
  drive_hours: number;           // routed travel time, > 0 (not construction time)
  miles_by_state?: Record<string, number>; // USPS codes; must sum to `miles` within 0.5 mi
  source: { provider: string; profile: string; retrieved_at: string }; // e.g. "google-routes","TRUCK"
  truck_profile_applied: boolean; // false for car-profile routes; the UI must say so
};
```

- If `truck_profile_applied` is false, show "passenger-car route; heavy-vehicle restrictions not checked".
  C15 forbids a DRIVE fallback being presented as a truck route. Computing a cost on it is allowed only with that label.
- `miles_by_state` is optional. With it, fuel and permits are computed per state. Without it, the UI needs one
  user-chosen fuel price for the leg and permits become "states unknown → permit cost incomplete".
- Scenario = set of legs:
  - Separate: `[D_A→A, A→D_A, D_B→B, B→D_B]` (`D_A` and `D_B` may be the same depot)
  - Sequenced: `[D→A, A→B, B→D]`, where the user picks which depot the shared fleet starts from.
  Missing legs → that scenario's total is null.

### 2. Fleet (user-entered per vehicle; nothing prefilled)

| Field | Unit | Notes |
|---|---|---|
| `label` | text | "Bucket truck 1", "Lowboy + 50-ton trailer" |
| `count` | whole | identical units |
| `mpg` | mi/gal, >0 | From fleet telematics or fuel logs. There is no authoritative public MPG for bucket/digger trucks, so no reference button. |
| `fuel` | `diesel` \| `gasoline` | picks the price series |
| `crew_on_clock` | whole | people paid while this vehicle travels, including riders, not just the driver |
| `cost_basis` | `per_mile` \| `per_hour` | choose one to avoid double counting ownership/wear |
| `equipment_rate` | $/mi or $/hr | internal rate, or rental rate for rented units |
| `oversize` | bool | triggers per-state permit rows and escort inputs |

### 3. Rates

| Input | Unit | Cited reference available? |
|---|---|---|
| Diesel / gasoline price per state or PADD | $/gal | Yes: EIA weekly retail, see Sources |
| Crew loaded labor rate | $/hr | User-entered. Optional reference: BLS OEWS 49-9051 **wage only**, shown with "wage only, excludes benefits, burden and contractor markup". |
| Straight-time hours per day, OT multiplier | h, × | User-entered (union agreement / contract) |
| Max drive hours per day | h | User-entered. See HOS note. |
| Lodging + M&IE per person-night | $ | Yes: GSA per diem by ZIP (reference only; contractor policy may differ) |
| Oversize single-trip permit per state | $ | Yes: state DOT fee table in `data/reference/mobilization/permits.json` |
| Escort vehicles count, $/hr | whole, $ | User-entered (no authoritative public rate) |
| Tolls per leg | $ | User-entered |
| Site setup/teardown per site | $ | User-entered quote. **Not avoided by sequencing**, since both sites still need setup. |
| Wait days between jobs, daily holding cost of fleet | days, $ | User-entered. Same meaning as F17's holding switch. |

## Model

All math lives in `web/lib/mobilization/model.ts` as pure functions. No fetch, no React.

For a leg `L` and vehicle `v` (multiplied by `v.count`):

```
fuel(L,v)   = Σ_state  miles_by_state[s] / v.mpg × price[s][v.fuel]
              (without miles_by_state: L.miles / v.mpg × leg_price)
equip(L,v)  = v.cost_basis == per_mile ? L.miles × v.equipment_rate
                                       : L.drive_hours × v.equipment_rate
labor(L,v)  = paid_hours(L) × v.crew_on_clock × loaded_rate
```

`paid_hours` handles overtime over the whole trip, not per leg:

```
travel_days      = ceil(total_drive_hours / max_drive_hours_per_day)
straight_hours   = min(total_drive_hours, travel_days × straight_hours_per_day)
ot_hours         = total_drive_hours − straight_hours
labor_hours_cost = straight_hours + ot_hours × ot_multiplier
```

Per trip:

```
nights     = max(travel_days − 1, 0) + user_extra_nights
lodging    = nights × Σ_v (v.count × v.crew_on_clock) × per_diem_person_night
permits    = Σ_oversize trips  Σ_states traversed  permit_fee[state]   (unknown state → incomplete)
escorts    = escort_count × escort_rate × Σ oversize drive_hours
tolls      = Σ leg tolls
```

Scenario totals:

```
separate  = trip(D_A→A→D_A) + trip(D_B→B→D_B) + setup_A + setup_B
sequenced = trip(D→A→B→D) + setup_A + setup_B
            + wait_days × (daily_holding_cost + crew_count × per_diem_person_night)
difference = separate − sequenced            // may be negative
```

Setup appears in both scenarios on purpose, which makes clear that sequencing does not remove site work. The
difference comes only from avoided legs, avoided per-trip permits, and the extra cost of waiting.

Return every component, not just the total. The UI shows a component table per scenario. Any null component makes
the scenario total null and is listed as "missing: …".

**Low/base/high:** like F17, three independent input sets, not a statistical range. Warn if results are not ordered.

**Hand-off to F17:** show `unit_mobilization_cost = trip(D_A→A→D_A)` (and B) with a "Copy to impact worksheet"
button that links to `/impact` with nothing prefilled, and puts the value on the clipboard. Prefilling F17 inputs
would break F17's blank-start rule, so leave that to a later F17-owned change if the user wants it.

## Sources (checked 2026-09-27)

| Data | Source | Access | Notes for implementation |
|---|---|---|---|
| Diesel retail, weekly | [EIA Gasoline & Diesel Update](https://www.eia.gov/petroleum/gasdiesel/); series `EMD_EPD2D_PTE_R1Z_DPG` ([Lower Atlantic PADD 1C](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=w&n=pet&s=emd_epd2d_pte_r1z_dpg)) | EIA API v2, free key (`EIA_API_KEY`) | Week of 2026-09-21: US $6.529, PADD 1C $6.139. EIA does **not** publish GA or SC state diesel; use PADD 1C (FL, GA, NC, SC, VA, WV) and label it "regional average". Updates Mondays; show week date; older than 14 days → "stale". |
| Trucking cost benchmark | [ATRI Operational Costs of Trucking](https://truckingresearch.org/about-atri/atri-research/operational-costs-of-trucking/); [2025 summary](https://www.ttnews.com/articles/atri-truck-costs-2025) | report | $2.336/mi total; driver wages $0.818 + benefits $0.210; R&M $0.404; tires $0.05. These are **for-hire Class 8 long-haul** figures. Show them only as a comparison line ("long-haul trucking average"), never as a default for utility fleets. |
| HOS | [49 CFR 395.1(n)](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-395/subpart-A/section-395.1); definition in §395.2 | eCFR | Drivers of *utility service vehicles* are exempt from Part 395. A contractor's heavy haul may or may not qualify. Don't decide it in code: max drive hours/day is a user input, and the UI links the rule. |
| Oversize permits | [GDOT Oversize Permits](https://www.dot.ga.gov/GDOT/Pages/OversizePermits.aspx); [SCDOT OS/OW](https://www.scdot.org/business/permits-osow.html) | fee tables | Single-trip base about $30 in each state, plus surcharges by width/weight (SC adds charges above 16 ft width). Before committing `permits.json`, the agent must confirm each fee on the **official** page and record URL + retrieval date. Superloads → "quote required", null. |
| Per diem | [GSA Per Diem API](https://open.gsa.gov/api/perdiem/) `api.gsa.gov/travel/perdiem/v2/rates/zip/{zip}/year/{fy}` | free key (`GSA_API_KEY`) | Federal travel rates; label "GSA reference". |
| Lineman wages | [BLS OEWS 49-9051](https://www.bls.gov/oes/) state tables | download/API | Not verified in this spec because the page wouldn't load during research. The agent pulls the GA/SC mean hourly wage, records the vintage, and labels it "wage only". Loaded contractor rates run much higher; the user enters the rate they actually pay. |

Other figures in the source chat have no citation here and must not enter code: "$1.5–3M per transmission mile",
"$10k crane setup", "bucket truck 5–8 MPG", "$90–160/hr contractor rate", "40–70% deadhead cut". They can go in
pitch text only if the pitch cites a source for them.

## UI (`/mobilization`)

1. Pair picker (optional, reuse F17's GET picker pattern) shows the two job centers and filed milestones read-only.
   Standalone use without a pair works.
2. Legs panel: paste/upload legs JSON, or a form per leg. Show provider, profile, retrieval time and the
   truck-profile flag per leg.
3. Fleet table with add/remove rows.
4. Rates with "Use cited value" buttons that show the source and date.
5. Results: separate vs sequenced side by side, a component table, the difference (negative in plain text, not red
   alarm), a missing-inputs list, low/base/high tabs, and an ATRI comparison line.
6. Print/export CSV with every input and its provenance, like F11/F17.

Reuse existing tokens/components. Keyboard reachable. No horizontal overflow at 390 px. No edits to shared nav.
Nav entry is a separate integration commit by the nav owner.

## Server routes (`web/app/api/mobilization/`)

- `GET /api/mobilization/fuel?padd=1C` → `{value, unit, series, week, retrieved_at, source_url}` or
  `{status:"unavailable", reason}`. Fixed EIA host and series allowlist; no client-supplied URLs; 5 s timeout;
  cache ≤ 6 h in memory.
- `GET /api/mobilization/perdiem?zip=31401&year=2026` → lodging + M&IE with FY and source. Strict 5-digit ZIP.
- No route/geometry calls here. Legs come from the routing feature.

## Worked example (illustrative inputs, not a quote)

Legs (made up for the test): D→A 60 mi / 1.5 h; A→D 60 mi / 1.5 h; D→B 75 mi / 1.8 h; B→D 75 mi / 1.8 h;
A→B 20 mi / 0.6 h. One depot. Fleet: 1 vehicle, 8 mpg, 3 crew, $1.00/mi equipment. Fuel $6.00. Labor $80/h,
10 straight h/day, 12 max drive h/day. No oversize, no tolls, setup $0 both.

- Separate: 270 mi, 6.6 h → fuel 270/8×6 = $202.50; equip $270.00; labor 6.6×3×80 = $1,584.00 → **$2,056.50**
- Sequenced: 155 mi, 3.9 h → fuel $116.25; equip $155.00; labor $936.00 → **$1,207.25**
- Difference: **$849.25**. Add 2 wait days × ($500 holding + 3 crew × $150 per diem) = +$1,900 → difference
  **−$1,050.75**. The test should assert both, which shows the waiting days change the sign.

## Validation

- `node --test web/lib/mobilization/model.test.mjs`: blank vs zero; one missing leg nulls one scenario only;
  miles_by_state sum mismatch rejected; per-state fuel split; per_mile vs per_hour basis; OT across days; nights;
  permit incomplete on unknown state; negative difference; overflow guard; the worked example exactly (cents).
- Route handler tests with mocked fetch: EIA ok / stale / 500 / malformed / missing key → `unavailable`; per diem
  bad ZIP rejected.
- Playwright (CI server, mocked APIs labeled synthetic): empty state, filled state, cited-value click records
  provenance, car-profile warning visible, 390 px no overflow, print.
- All repo-wide checks in `specs/tech-stack.md`; `git diff origin/main --stat` stays within `owns`.

## Done means

Merged model + page + tests; `data/reference/mobilization/` has citations for every stored number; the worked
example passes; screenshots (empty/filled, desktop/mobile) in this folder; `changes/F43.md` states what live
provider paths were actually exercised (EIA/GSA with a real key, or "not exercised").

## Out of scope

Routing, route drawing on MapLibre, dispatch/scheduling optimization, rental booking, CO₂ estimates, predicted
durations, any "savings" claim, and the transmission capital-cost figures from the chat.
