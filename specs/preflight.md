# Pre-flight: what humans do before launching the overnight run (about 45 minutes)

Agents can't do anything on this list. Skip a step and something blocks at 3 a.m. Work top to bottom; items marked
**[fradicus]** need repo admin (`fradicus` owns the repo; other accounts only have push).

## 1. Get the spec onto `main`
1. Review `specs/decisions/000-overnight-defaults.md`, especially **D2** (Georgia data) and **D4** (Atlas network). Change anything you disagree with now; agents will follow it literally.
2. Merge the branch holding `specs/`, `AGENTS.md`, `CLAUDE.md` into `main` (a PR is fine). This must happen **before** step 2 turns on protection.

## 2. Branch protection and auto-merge **[fradicus]**
```bash
gh api -X PATCH repos/fradicus/Shellhacks-2026 \
  -F allow_auto_merge=true -F delete_branch_on_merge=true \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false

gh api -X PUT repos/fradicus/Shellhacks-2026/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["ci"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```
`ci` doesn't exist until F00 creates it. That's fine: F00's own PR runs it. `enforce_admins: false` lets a human bypass in an emergency.
GitHub's merge queue needs an organization-owned repo, so it isn't available here. The strict check plus the agents' rebase loop (`overnight.md` §3.8) does the same job.

## 3. Accounts and secrets
| Item | Where it goes |
|---|---|
| Atlas M0 cluster, database `gridbridge`. Two DB users with random passwords: `loader` (readWrite on gridbridge), `web` (read). Network access `0.0.0.0/0` (decision D4) | none |
| `MONGODB_URI_RW` (loader user) + `MONGODB_DB=gridbridge` | **GitHub → repo → Settings → Secrets → Actions** **[fradicus]** |
| `MONGODB_URI_RO` (web user) | Vercel env (Production + Preview); lane B and C machines |
| `GEMINI_API_KEY` (aistudio.google.com/apikey), `GEMINI_MODEL` (a current stable model from AI Studio; test one call) | lane A machine only |
| GitHub fine-grained token, repo `fradicus/Shellhacks-2026`: Contents RW, Pull requests RW, Issues RW. **Plus Workflows RW on the lane B machine only** (F00 writes `.github/workflows`) | each machine as `GH_TOKEN` (or `gh auth login`) |
| Claude Code auth (subscription login or `ANTHROPIC_API_KEY`) | each machine |

## 4. Vercel + domain
1. Vercel → Add Project → import `fradicus/Shellhacks-2026`, **Root Directory `web`**, framework Next.js. Env: `MONGODB_URI_RO`, `MONGODB_DB=gridbridge`, `ANALYSIS_DATE=<launch date>`. The first builds fail until F00 merges; that's expected.
2. Register the domain through the MLH GoDaddy Registry offer (only GoDaddy Registry TLDs qualify; check the offer page). Add it in Vercel → Domains, and set the DNS records Vercel shows at the registrar. If you skip this, F08 files a `human-morning` issue and the app runs on `*.vercel.app`.

## 5. Each machine
```bash
git clone https://github.com/fradicus/Shellhacks-2026.git ~/gridbridge && cd ~/gridbridge
# tooling: Node 24.11+, Python 3.12, uv, gh, claude
node -v && python3 --version && uv --version && gh auth status && claude --version
npx paperclipai onboard --yes   # once per machine; then `npx paperclipai run`
```
Import **only this machine's lane agents and the skills**. No seeded tasks, because they'd duplicate across machines:
```bash
# Lane A machine
npx paperclipai company import ./plans/plan-E/paperclip --target new --include company,agents,skills \
  --agents data-researcher,gemini-engineer,geo-engineer --dry-run      # inspect, then rerun with --yes
# Lane B machine:  --agents technical-lead,frontend-engineer
# Lane C machine:  --agents qa-verifier,release-engineer,ceo
# One machine running everything: omit --agents
```
In the Paperclip UI:
- **Project workspace:** `~/gridbridge`. Enable isolated workspaces (Instance settings → Experimental), base ref `origin/main`, so each feature gets its own worktree.
- **Secrets:** bind this machine's rows from section 3.
- **Budgets:** CEO $10, technical-lead $25, others $20 each (hard stop). Adjust to taste.
- **Heartbeats:** turn timer heartbeats **on** for every agent, every 10 minutes, with max 1 concurrent run per agent and a 20-minute run timeout. This is the opposite of Plan E's setting: overnight, nobody is there to wake the agents.
- **Instructions override:** Plan E's `git-delivery` skill says "no commits". The root `AGENTS.md` and `specs/overnight.md` override it. Put this line at the top of each agent's instructions: *"Follow AGENTS.md and specs/overnight.md in the repo; they override any conflicting skill."*

## 6. Launch
1. Final commit on `main`: set `run_start` and `analysis_date` in `specs/roadmap.md` front matter. For a run shorter than 8 hours, scale the `gates` times. Fill in the machine mapping below.
2. Create one task per agent, assigned to that agent, with this body:

   > Autonomous overnight run. Read AGENTS.md and specs/overnight.md from origin/main and follow them exactly. Your agent slug is `<slug>`, your lane is `<A|B|C>`. Each run: check STOP, then your open PRs, then pick your next ready feature from specs/roadmap.md. Never wait for a human.

3. Wake the lane B `technical-lead` first (F00) and the `ceo` (F18). The others can wake too; they'll idle until `changes/F00.md` lands.

| Lane | Machine |
|---|---|
| A · data | |
| B · app | |
| C · quality | |

## 7. Emergency stop (from a phone)
GitHub web → `main` → Add file → create `STOP` (any content) → commit. Every agent stops at its next heartbeat.
To hard-stop a machine, pause its agents in Paperclip or quit `paperclipai run`.

## 8. Morning
Read `reports/final.md`, then open the `human-morning` issues, then read `specs/decisions/`. Check the live domain.
Delete `STOP` only if you want agents to continue.
