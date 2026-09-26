# Plan D: Gridlock (consolidated)

Plan D merges plans A, B and C and adds new ideas aimed at beating about 100 other teams on the Sperry Tech track,
while also covering Gemini, MongoDB Atlas and the GoDaddy Registry domain.

- **Humans read this file.**
- **Agents run `paperclip/`**, an importable Paperclip company. Its product spec is `paperclip/projects/gridlock/PROJECT.md`.

---

## 1. How we win

Most teams will put the sponsor's 10 sample projects on a map and list the 6 overlaps. That's the minimum.
We win on four things they won't have:

1. **Real scale.** We parse every project in both utilities' public filings: Dominion's 2024–2028 list (44) and
   2025–2029 list (47), plus Georgia Power's whole Ten-Year Plan. The sample becomes our test, not our dataset.
2. **Evidence on every number.** Click any distance, date, cost or coordinate to see the source page, the
   OpenStreetMap feature, or the formula. Sperry's AI team hires people to "trace a number back through the system."
   We make that the product's signature.
3. **Planner judgment, not just proximity.**
   - Shared-facility detection: both utilities working on the same substation.
   - Construction-window estimates from Dominion's yearly budgets.
   - Coordination zones, with a sequencing view that shows where projects can *share* crews and where they'll *compete* for them.
4. **Visible pipeline quality.** A Data Quality page, a golden test in CI, a measured extraction accuracy, and a
   weekly job that detects when a utility posts a new filing. This mirrors the intern listing almost line for line.

We already found a headline lead: the 2025–2029 Dominion list adds **"Okatie – McIntosh 115 kV Tie: Add Series
Reactor" (ID 6888, in service 12/31/2028)**, a line that literally ties into Georgia Power's McIntosh
substation, which also appears in two Georgia Power projects. QA must verify it before it goes in the pitch.

---

## 2. Where each part came from

| Idea | From |
|---|---|
| Importable Paperclip package, per-track owner agents, sponsor golden test (verified 6/6) | A |
| Python pipeline + Next.js + MapLibre + key-free tiles + Vercel | A |
| Gemini: table extraction, geocode adjudication, briefs, "Ask the grid" | A |
| Separate **Timeline matches** view; labels `nearby` / `timeline` / `both`; 180-day editable window | B |
| Distance boundary tests (24.999 / 25.000 / 25.001), Gemini-down fallback, prompt-injection rule | B |
| Owner-code verification in Georgia tables (GPC / SAV / GTC / MEAG); analysis date and past-dated badge | B |
| Editable low/base/high impact scenario instead of a flat 30% freight guess | B + C |
| Utility Data Researcher agent; CSV export | B |
| Newer Dominion 2025–2029 filing (confirmed downloadable, 47 projects) | C |
| **Budget-window proxy**: Dominion's yearly spend gives an estimated work window | C |
| Pitch: best lead first, then the 4.09-mi / 3,074-day counterexample | C |
| Tie the product to Sperry's intern listing (ETL, validation, refresh) | C |
| **Shared-facility signal** (same substation in both utilities' projects) | New |
| **Coordination zones + contention + sequencing Gantt** (share vs compete for scarce crews) | New |
| **Evidence popovers on every number** | New |
| **Data Quality page + source-change watcher** (GitHub Action) | New |
| **One-page coordination memo** via print CSS (no PDF library) | New |
| **Mentor checkpoints** at hours 1 and 20 (Sperry judges its own track) | New |
| Time plan: feature freeze at hour 30, explicit cut order, at most 4 agents running at once | New |

Left out on purpose: PostgreSQL (C; it would forfeit the Atlas track), MapTiler key and Render (B; extra keys plus
Atlas IP allowlisting), source/run versioning tables and heavy date-precision modeling (B; post-hackathon work).

---

## 3. What judges see

**Home:** full-screen map of both utilities, with a side panel of three tabs.
- **Opportunities**: ranked pairs. Each shows a tier badge, both project names, the distance, "in service N days apart", the top reasons, and a confidence badge.
- **Timeline matches**: pairs that are far apart but scheduled close together, clearly marked "timing only".
- **Zones**: clusters of linked projects, such as the Savannah River / McIntosh area and the Thurmond Lake area.

A stat strip (`N projects · M located · K nearby pairs · Z zones`) links to the Data Quality page.
The "Ask the grid" box ("230 kV work near Savannah in 2027") filters and highlights the map.

**Pair page:** both projects, a mini map, the signals table, reasons, the editable impact scenario, a Gemini
brief with open questions for planners, and a **Print memo** button that turns it into a one-page memo for a planning meeting.

**Zone page:** a Gantt chart of the zone's projects, red bands for years where they compete for crews, and a
suggested sequence ("a crew could move from X to Y, 152 days apart").

**Data Quality page:** sources with hashes and filing dates, coverage counts, check results, unlocated projects,
and the extraction accuracy.

---

## 4. Rules

**Sponsor rules (exact):**
- Project center = midpoint of its two endpoints, or the one located endpoint.
- **Nearby = under 25 miles** (haversine).
- Time gap = difference between in-service dates, in days.
- Distance is the main signal. Time is secondary.

**Our additions:**

| Signal | Meaning |
|---|---|
| Shared facility | Both projects name the same substation, and the matched points are within 2 mi |
| Work-window overlap | Dominion's first budget year → in-service date, compared where both windows are known; otherwise "unknown" |
| Confidence | Worst location confidence of the two projects |

**Ranking:**
- **Tier 1:** shared facility, or both nearby and timely.
- **Tier 2:** nearby only.
- **Tier 3:** low confidence ("needs review").
- Timeline-only pairs appear only in their own tab.
- A score orders pairs within a tier. The raw signals are always shown next to it.

**Honesty rules:**
- An in-service date is a milestone, not a construction period.
- Estimates are "modeled potential", not savings.
- Unknown stays unknown.

**Sponsor sample result:** the rules reproduce OVL_1–6 exactly, and OVL_2 (5.65 mi, 152 days) comes out as the only Tier 1 pair.

---

## 5. Architecture

```
public filings ─► pipeline/ (Python, pandas)
                   sources → extract → geocode (OSM + Gemini) → overlaps/zones → quality → briefs (Gemini)
                   └─► data/*.json (committed) ─► load_mongo.py ─► MongoDB Atlas
web/ (Next.js on Vercel) ─► API routes ─► Atlas ($geoNear, Atlas Search, $lookup, $facet)
                          └► /api/ask ─► Gemini function call ─► whitelisted query
.github/workflows: ci.yml (golden test) · source-watch.yml (weekly filing-change check)
```

| Part | Choice | Why |
|---|---|---|
| Pipeline | Python 3.12, uv, pandas, pdfplumber | Sperry's listed skills; best PDF tooling |
| App | Next.js (App Router, TypeScript), one deploy | UI and API in one place, preview URL per PR |
| Map | MapLibre GL + OpenFreeMap tiles | No map key |
| DB | MongoDB Atlas M0 | Atlas track; GeoJSON and geo queries are native |
| AI | Gemini (newest stable Flash, pinned) | Gemini track; JSON-schema output |
| Hosting | Vercel + GoDaddy Registry domain | Git-push deploys; domain track |

---

## 6. The agent team (Paperclip)

```
Board (humans): mentor check-ins, domain purchase, prod approval, Devpost submit
└── CEO (Opus) ─ scope, issues, schedule, cut decisions, Devpost draft
    └── CTO (Opus) ─ architecture, contracts, reviews and merges every PR, deploy
        ├── Utility Data Researcher ─ source manifest, owner codes, version links, unit costs
        ├── Data Engineer ─ PDF extraction, quality checks, source watcher
        ├── Geospatial Engineer ─ OSM matching, signals, tiers, zones, estimate
        ├── Backend Engineer ─ Atlas + API                (Atlas prize owner)
        ├── AI Engineer ─ every Gemini feature + eval     (Gemini prize owner)
        ├── Frontend Engineer ─ map, pages, evidence UI
        └── QA & Data Verifier ─ golden test, source checks, live QA
```

Everyone below the CTO runs on Sonnet. At most 4 agents run at once. The CEO releases the next issue when one merges.

## 7. Skills per agent

| Agent | Skills |
|---|---|
| CEO | gridlock-domain, hackathon-submission |
| CTO | gridlock-domain, git-pr-workflow, deploy-and-domain |
| Researcher | gridlock-domain, git-pr-workflow, source-audit |
| Data Engineer | gridlock-domain, git-pr-workflow, pdf-project-extraction, gemini-api |
| Geospatial Engineer | gridlock-domain, git-pr-workflow, osm-geocoding, overlap-scoring, gemini-api |
| Backend Engineer | gridlock-domain, git-pr-workflow, mongodb-atlas |
| AI Engineer | gridlock-domain, git-pr-workflow, gemini-api, mongodb-atlas |
| Frontend Engineer | gridlock-domain, git-pr-workflow, map-ui, frontend-design |
| QA & Data Verifier | gridlock-domain, git-pr-workflow, data-verification, source-audit, webapp-testing |

All 12 custom skills are written and live in `paperclip/skills/`. `frontend-design` and `webapp-testing` are copied
from anthropics/skills (Apache-2.0, licenses kept). Paperclip's built-in `paperclip` skill is attached to every agent automatically; check after import.

---

## 8. API keys and accounts

| Secret | Where | Who uses it | Needed? |
|---|---|---|---|
| `GH_TOKEN` | GitHub fine-grained token on `fradicus/Shellhacks-2026`: Contents, Pull requests, Workflows (read/write) | all agents | **Yes.** Created by `fradicus` or a collaborator with write access |
| `GEMINI_API_KEY` | aistudio.google.com/apikey | pipeline, app | **Yes** |
| `GEMINI_MODEL` | newest stable Flash model in AI Studio (plain setting) | pipeline, app | **Yes** |
| `MONGODB_URI` | Atlas M0. Two users: `loader` (read/write) for the pipeline, `web` (read) for Vercel. Network `0.0.0.0/0` | pipeline, app | **Yes** |
| `NOMINATIM_EMAIL` | any team email (plain setting) | Geospatial Engineer | **Yes** |
| `ANTHROPIC_API_KEY` | console.anthropic.com | all agents | Only if not using a Claude subscription login |
| `VERCEL_TOKEN` | vercel.com → Tokens | CTO | Optional |

No key needed: OpenStreetMap / Overpass / Nominatim, OpenFreeMap, MapLibre, GoDaddy DNS (set by hand).

---

## 9. Setup (about 25 minutes, humans)

1. Create the accounts and keys above. Import the repo into Vercel with root `web` once the CTO has scaffolded it.
2. Install and start Paperclip (Node 24.11+):
   ```bash
   npx paperclipai onboard --yes
   npx paperclipai run          # http://localhost:3100
   ```
3. Clone and make the first commit (the repo has no commits yet):
   ```bash
   git clone https://github.com/fradicus/Shellhacks-2026.git ~/gridlock && cd ~/gridlock
   # copy docs/ and plans/ in, commit, push
   ```
4. Import the company, previewing first:
   ```bash
   npx paperclipai company import ./plans/plan-D/paperclip --target new --dry-run
   npx paperclipai company import ./plans/plan-D/paperclip --target new --yes
   ```
5. **Company → Secrets:** add everything from section 8.
6. **Project "Gridlock" → Configuration:**
   - working folder `~/gridlock` (absolute path)
   - repo URL
   - turn on **Instance settings → Experimental → Isolated Workspaces**
   - default mode **Isolated**, base ref `origin/main`
   - provision command `uv sync --project pipeline || true; (cd web && npm ci) || true`
7. **Budgets:**

   | Agent | Budget |
   |---|---|
   | CEO | $12 |
   | CTO | $25 |
   | Researcher | $12 |
   | Data Engineer | $20 |
   | Geospatial Engineer | $25 |
   | Backend Engineer | $15 |
   | AI Engineer | $20 |
   | Frontend Engineer | $30 |
   | QA | $15 |
   | **Total** | **$174** (hard stops) |

8. Run **Test environment** on each agent. The Researcher, Frontend and QA agents use Chrome, so the Claude in Chrome extension must be installed.
9. Open the seeded **Kickoff** task, which is assigned to the CEO, and wake it. The status sweep runs every 2 hours.

Paperclip doesn't push code itself. Agents push branches and open PRs with `gh`, and the CTO merges.

---

## 10. 36-hour timeline

| Hours | Milestone |
|---|---|
| 0–2 | Source manifest, scaffold, CI. **Board: Sperry mentor check #1** |
| 2–9 | Golden test; Dominion extraction (both lists); Georgia Power extraction (border zones first) |
| 9–17 | Geocoding with confidence; signals, tiers, zones, estimate |
| 12–22 | Map and Opportunities UI on fixtures, then real data; Atlas load and API |
| 17–23 | Verification of every Tier 1–2 pair; Gemini briefs and Ask |
| 20 | **Board: Sperry mentor check #2**, show the ranked list and a zone |
| 22–27 | Zone page, pair memo, Data Quality page, source watcher |
| 28 | Deploy on the GoDaddy domain |
| **30** | **Feature freeze** |
| 30–34 | Live QA, Gemini-down drill, pitch rehearsal, Devpost draft |
| 34–36 | Buffer, submit |

**If late, cut in this order:**
1. Ask the grid
2. Sequence text
3. Right-of-way acres
4. Georgia Power zones away from the border

**Never cut:** the golden test, the evidence links, verification.

---

## 11. Board-only tasks

- Mentor check-ins at hours 1 and 20. Hour-1 questions:
  1. Can we use the Georgia Power table fields, given the CEII banner?
  2. What makes an opportunity useful to you?
  3. Is 180 days a reasonable timing window?
- Register the domain through the MLH GoDaddy Registry offer. **Only GoDaddy Registry TLDs qualify**, so check the offer page. Pick something short that fits the product.
- Approve production deploys, record the demo, and submit on Devpost with all four tracks selected.

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| Georgia Power PDF carries a CEII banner | Use only the table fields the sponsor points to; no page images; mentor confirms in hour 1 |
| Similar substation names in the wrong county | Confidence grades, QA re-check of every high/medium match, "needs review" tier |
| In-service date mistaken for construction time | Separate window signal; the wording rule ("in service N days apart") is enforced in briefs and UI |
| Made-up savings | Editable low/base/high scenario, cited inputs, low case = $0, "modeled potential" label |
| Gemini outage or quota | Deterministic results never depend on it; cached pipeline outputs; UI fallbacks, drilled by QA |
| Agent cost runaway | Hard budgets; at most 4 running at once; CEO pauses agents that spend without merging |
| Running out of time | Freeze at hour 30, cut order above, fixtures let the UI start before the data is ready |

---

## 13. Two-minute pitch

1. **Problem:** a contractor pays $1.5M in freight on a $5M job because utilities don't coordinate.
2. **Scale:** every project in both utilities' public filings, every number traceable.
3. **Best lead:** the top verified Tier 1 pair (the Okatie–McIntosh tie, if confirmed).
4. **Counterexample:** the 4.09 mi pair is 3,074 days apart. We rank evidence, not just proximity.
5. **Zone view:** where crews could be shared, and where they'll be fought over.
6. **Trust:** click any number to see its page. Data Quality page. Golden test in CI.
7. **Close:** "Gridlock finds the leads; planners make the call." Then the domain.

---

## 14. Files

```
plans/plan-D/
├── PLAN.md                          ← this file
└── paperclip/                       ← import this into Paperclip
    ├── COMPANY.md, .paperclip.yaml
    ├── agents/<9 roles>/AGENTS.md
    ├── skills/<14 skills>/SKILL.md
    └── projects/gridlock/PROJECT.md (+ tasks/kickoff, tasks/status-sweep)
```
