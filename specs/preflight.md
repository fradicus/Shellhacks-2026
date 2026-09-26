# Pre-flight: what humans do before launching the overnight run (about 45 minutes)

Choose Paperclip, local Claude Code + Codex, or hybrid before launch. Humans supply account access and secrets; agents can prepare and check configurations. Work top to bottom; items marked
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

**Needed tonight for a full run:** coding-runtime login, GitHub access, `GEMINI_API_KEY` + `GEMINI_MODEL`, and Atlas connection settings. Test one small real Gemini request before leaving the agents running. UI/schema/offline-test work can start without Gemini or Atlas, but those integrations must be reported incomplete. The custom domain can wait until morning; the domain track remains pending until it works.

Create the product Gemini key in [Google AI Studio](https://aistudio.google.com/apikey), following [Google's key guide](https://ai.google.dev/gemini-api/docs/api-key). Store it in the data agent's Paperclip environment or the local data worker's environment, according to mode. It is separate from Claude/Codex login. Do not paste keys into chat, specs, PRs or client code; ignored `.env` files, if used, must be loaded explicitly by the intended process.

| Item | Where it goes |
|---|---|
| Atlas M0 cluster, database `gridbridge`. Two DB users with random passwords: `loader` (readWrite on gridbridge), `web` (read). Network access `0.0.0.0/0` (decision D4) | none |
| `MONGODB_URI_RW` (loader user) + `MONGODB_DB=gridbridge` | **GitHub → repo → Settings → Secrets → Actions** **[fradicus]** |
| `MONGODB_URI_RO` (web user) | Vercel env (Production + Preview); lane B and C machines |
| `GEMINI_API_KEY`, `GEMINI_MODEL` (an available model tested for the pipeline) | Data runtime only: Paperclip secret/env binding OR the local process environment. Never frontend/Vercel for this batch-only design. |
| GitHub fine-grained token, repo `fradicus/Shellhacks-2026`: Contents RW, Pull requests RW, Issues RW. **Plus Workflows RW on the lane B machine only** (F00 writes `.github/workflows`) | each machine as `GH_TOKEN` (or `gh auth login`) |
| Coding authentication: Claude Code and/or Codex login; provider API key only if choosing API billing | Each selected local runtime or Paperclip adapter host. Existing supported subscription login is sufficient; the application itself does not need an OpenAI/Anthropic key. |

## 4. Vercel + domain
1. Vercel → Add Project → import `fradicus/Shellhacks-2026`, **Root Directory `web`**, framework Next.js. Env: `MONGODB_URI_RO`, `MONGODB_DB=gridbridge`, `ANALYSIS_DATE=<launch date>`. The first builds fail until F00 merges; that's expected.
2. Register the domain through the MLH GoDaddy Registry offer (only GoDaddy Registry TLDs qualify; check the offer page). Add it in Vercel → Domains, and set the DNS records Vercel shows at the registrar. If you skip this, F08 files a `human-morning` issue and the app runs on `*.vercel.app`.

Coding authentication references: [Claude Code](https://code.claude.com/docs/en/authentication) and [official OpenAI documentation for Codex](https://developers.openai.com/codex/auth/). Model access and quotas must be checked in your own accounts; this spec does not verify them.

## 5. Choose how to run
```bash
git clone https://github.com/fradicus/Shellhacks-2026.git ~/gridbridge && cd ~/gridbridge
# tooling: Node 24.11+, Python 3.12, uv, gh, claude
node -v && python3 --version && uv --version && gh auth status && claude --version
```

### Option A — Paperclip
Set `execution_mode: paperclip` in the roadmap.
```bash
npx paperclipai onboard --yes   # once per host; later restart with `npx paperclipai run`
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

### Option B — local Claude Code + Codex
Set `execution_mode: local`. The roadmap's `local_workers` gives a suggested disjoint feature split; roles/lanes and CI gates stay the same. Authenticate both tools, then open each in its own feature worktree. Example commands after the spec is on main (run only the commands for the feature you are claiming):

```bash
# Codex starts the bootstrap feature.
git worktree add ../gridbridge-f00 -b f00-bootstrap origin/main
cd ../gridbridge-f00
codex
```

```bash
# In another terminal, after F00 has merged, Claude starts its first feature.
git fetch origin
git worktree add ../gridbridge-f01 -b f01-desc-register origin/main
cd ../gridbridge-f01
claude
```

Use the same pattern for later features, with a fresh worktree based on updated main. Read the relevant written domain skills from `plans/plan-E/paperclip/skills/` as procedural references if useful; root specs override their old paths, task and runtime instructions. Local sessions coordinate through PRs; skip Paperclip checkout, import, token and heartbeat instructions. No new skill installation is required to read these Markdown procedures. Keep both tools open; an ended local session needs resume rather than an assumed automatic wake.

### Option C — both
Set `execution_mode: hybrid`. Keep only the locally assigned feature IDs in `local_workers`, and tell Paperclip agents to skip those IDs. Run Option A for the remaining roles and Option B for local features. Each feature still has exactly one runtime owner. Pause the old owner before handing work between modes.

## 6. Launch
1. Final commit on `main`: set `run_start` and `analysis_date` in `specs/roadmap.md` front matter. For a run shorter than 8 hours, scale the `gates` times. Select `execution_mode`, review `local_workers` if applicable, and fill in runtime/machine ownership below.
2. In Paperclip, create a task for each active agent. For local sessions, paste the equivalent prompt into Claude/Codex with worker ID `claude-local` or `codex-local`:

   > Autonomous overnight run. Read AGENTS.md and specs/overnight.md from origin/main and follow them exactly. Your runtime mode is `<paperclip|local|hybrid>` and identity is `<agent-slug|local-worker-id>`. Honor the roadmap mode/ownership rules, adopting the feature role/lane for local work. Each run: check STOP, then your open PRs, then pick your next ready feature from specs/roadmap.md. Never wait for a human.

3. Start the F00 owner first: technical-lead in Paperclip, or codex-local in the sample local split. The F18 owner handles reporting (a separate CEO agent or local reporting checkpoints). Other implementation waits until `changes/F00.md` lands.

| Lane | Runtime / machine or local worker |
|---|---|
| A · data | |
| B · app | |
| C · quality | |

## 7. Emergency stop (from a phone)
GitHub web → `main` → Add file → create `STOP` (any content) → commit. Every agent stops at its next heartbeat.
To stop immediately, pause the Paperclip agents/stop its server and interrupt any local Claude/Codex sessions. The STOP file is checked on the next heartbeat or local task checkpoint; it cannot interrupt an already-running tool call.

## 8. Morning
Read `reports/final.md`, then open the `human-morning` issues, then read `specs/decisions/`. Check the live domain.
Delete `STOP` only if you want agents to continue.
