# Plan A: Gridlock on Paperclip

A Paperclip company package (Agent Companies spec, `agentcompanies/v1` + `.paperclip.yaml`) that builds
the Sperry Tech "Gridlock" overlap detector and covers the Gemini, MongoDB Atlas and GoDaddy Registry tracks.
Everything the agents need is in `paperclip/`. The product spec is `paperclip/projects/gridlock/PROJECT.md`.

## 1. Org chart

```
Board (you, humans) — approves spend, the domain purchase, prod deploys, the Devpost submit
└── CEO (Opus) ............ goals → issues, unblocking, scope, Devpost draft
    └── CTO (Opus) ........ architecture, scaffold, reviews + merges every PR, Vercel deploy, domain DNS
        ├── Data Engineer (Sonnet) ........ PDFs → project tables
        ├── Geospatial Engineer (Sonnet) .. OSM coordinates, overlaps, score, cost estimate
        ├── Backend Engineer (Sonnet) ..... MongoDB Atlas + API          (Atlas prize owner)
        ├── AI Engineer (Sonnet) .......... all Gemini features          (Gemini prize owner)
        ├── Frontend Engineer (Sonnet) .... map UI + ranked list
        └── QA & Data Verifier (Sonnet) ... golden test, PDF checks, live-site QA
```

## 2. Skills per agent

| Agent | Skills |
|-------|--------|
| CEO | gridlock-domain, hackathon-submission |
| CTO | gridlock-domain, git-pr-workflow, deploy-and-domain |
| Data Engineer | gridlock-domain, git-pr-workflow, pdf-project-extraction, gemini-api |
| Geospatial Engineer | gridlock-domain, git-pr-workflow, osm-geocoding, overlap-scoring, gemini-api |
| Backend Engineer | gridlock-domain, git-pr-workflow, mongodb-atlas |
| AI Engineer | gridlock-domain, git-pr-workflow, gemini-api, mongodb-atlas |
| Frontend Engineer | gridlock-domain, git-pr-workflow, map-ui, frontend-design* |
| QA & Data Verifier | gridlock-domain, git-pr-workflow, data-verification, webapp-testing* |

\* Vendored from [anthropics/skills](https://github.com/anthropics/skills) @ `33375500`, Apache-2.0, license file kept.
Every agent also gets Paperclip's bundled `paperclip` skill (the one that lets it read and update issues). Check it's attached after import.

## 3. API keys and accounts

| Secret | Where to get it | Used by | Required |
|--------|-----------------|---------|----------|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | all agents (Claude Code) | Only if you skip Claude subscription login |
| `GH_TOKEN` | GitHub → Settings → Developer settings → Fine-grained token, repo `fradicus/Shellhacks-2026`, **Contents: RW, Pull requests: RW, Workflows: RW** | all agents | Yes. The token owner must be `fradicus` or a collaborator with write access |
| `GEMINI_API_KEY` | aistudio.google.com/apikey | pipeline + app | Yes |
| `GEMINI_MODEL` (plain) | newest Flash model listed in AI Studio | pipeline + app | Yes |
| `MONGODB_URI` | Atlas → free M0 cluster → Database Access (user: readWrite on `gridlock`) → Network Access `0.0.0.0/0` → Connect → Drivers | pipeline + app | Yes |
| `NOMINATIM_EMAIL` (plain) | any team email (Nominatim usage policy wants a contact in the User-Agent) | Geospatial Engineer | Yes |
| `VERCEL_TOKEN` | vercel.com → Account → Tokens | CTO (manual previews only) | Optional. The GitHub integration deploys without it |

**No key needed:** OpenStreetMap Overpass, Nominatim, OpenFreeMap tiles, MapLibre, GoDaddy DNS (you set it by hand in the GoDaddy UI).

## 4. Setup (about 20 minutes, humans only)

1. **Accounts:** make the Atlas M0 cluster, Gemini key and GitHub token from the table. Register the domain with the MLH GoDaddy Registry code (see §5). Import the repo into Vercel with root directory `web`, after issue 1 creates `web/`.
2. **Install Paperclip** (needs Node 24.11+):
   ```bash
   npx paperclipai onboard --yes      # sets up the instance, embedded Postgres
   npx paperclipai run                # UI at http://localhost:3100
   ```
3. **Clone the repo** (Paperclip project workspace points here):
   ```bash
   git clone https://github.com/fradicus/Shellhacks-2026.git ~/gridlock && cd ~/gridlock
   ```
   `main` has no commits yet. Commit `docs/` + `plans/plan-A/` as the first commit and push it before step 4.
4. **Import the company:**
   ```bash
   npx paperclipai company import ./plans/plan-A/paperclip --target new --dry-run   # preview
   npx paperclipai company import ./plans/plan-A/paperclip --target new --yes
   ```
5. **Secrets:** Company → Secrets: add every row from §3. Each agent's env inputs (declared in `.paperclip.yaml`) bind to these.
6. **Project workspace:** Projects → Gridlock → Configuration:
   - Local folder `cwd` = `~/gridlock` (absolute path), Repo URL = `https://github.com/fradicus/Shellhacks-2026.git`
   - Instance settings → Experimental → Enable Isolated Workspaces. Then Default mode **Isolated (new workspace)**, base ref `origin/main`, provision command `uv sync --project pipeline || true; (cd web && npm ci) || true`
   - Paperclip doesn't push for you. Agents push branches and open PRs with `gh`, which is what `git-pr-workflow` tells them to do.
7. **Budgets** (Costs page): CEO $15, CTO $25, each engineer $20, QA $15. That's about $175 total with hard stops. Raise it only for agents that are shipping merged PRs.
8. **Adapter check:** each agent → Test environment. `claude_local` needs `claude` on PATH and either the API key or `claude login`. The Frontend and QA agents have `chrome: true` for browser checks, which needs the Claude in Chrome extension.
9. **Start:** open the seeded "Kickoff" task (assigned to CEO) and wake the CEO. The `status-sweep` routine runs every 2 hours.

## 5. Board-only actions (agents can't do these)

- Register the GoDaddy Registry domain. Pick something judges remember and check that it's available first. Candidates: `gridlock.us`, `sharethecrew.us`, `twogrids.co`. Then approve the CTO's DNS issue.
- Approve production deploys and merges the CTO flags as risky.
- Submit on Devpost and select all four tracks.

## 6. What gets built (for comparing plans)

Python pipeline (PDF → OSM geocode → overlaps → Atlas) plus a Next.js/MapLibre app on Vercel.
- **Gemini:** extraction assist, geocode adjudication, coordination briefs, and natural-language questions that drive the map.
- **Atlas:** GeoJSON + 2dsphere, `$geoNear` radius tool, Atlas Search.
- **Acceptance:** the sponsor's golden sample (OVL_1–6) is reproduced exactly. The haversine in `overlap-scoring` was checked against it: 6/6 pairs, distances and gaps exact, no false positives.
- **Not included:** auth, user accounts, Docker, a separate backend service, driving distances.
