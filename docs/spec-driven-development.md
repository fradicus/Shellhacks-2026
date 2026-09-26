# Spec-Driven Development (SDD): Agent Operating Guide

Condensed from the DeepLearning.AI × JetBrains course "Spec-Driven Development" (Andrew Ng, Paul Everitt). Written for a coding agent to load as working context.

---

## 1. Core Principle

The spec is the brain; the agent is the muscle. The human defines **what** and **why** in markdown specs; the agent implements the **how**. Specs are durable, versioned artifacts that persist across sessions and agents. Chat history is not.

**Why SDD beats vibe coding:**

1. **Leverage.** One spec sentence ("Use SQLite with Prisma ORM") controls hundreds of lines of code. Changing the spec is cheaper than changing code.
2. **No context decay.** Agents are stateless and degrade as context fills. Specs reload high-quality context at every session start and preserve non-negotiables.
3. **Intent fidelity.** Specs force the problem, success criteria, constraints and user flows to be defined before code is generated, so output matches goals.

Without a spec, architectural decisions are left to chance, producing unmaintainable code and contradictory implementations across developers and agents.

**Right level of detail:** Treat the agent as a highly capable pair programmer. Specs carry rich context about goals, mission, audience and constraints — the things the agent cannot know. Specs omit low-level decisions the agent can make itself (variable names, CSS class choices). Architect analogy: give builders detailed drawings, supervise, review, accept or request changes — don't tell them how to do their jobs.

---

## 2. Workflow Overview

```
CONSTITUTION (once per project, living document)
   mission.md · tech-stack.md · roadmap.md
        │
        ▼
FEATURE LOOP (repeat per roadmap item, each on its own branch)
   1. Plan (feature spec)  →  2. Implement  →  3. Validate  →  merge
        │
        ▼
REPLAN (between features)
   revise constitution · update roadmap · improve the process/skills
```

Works for both **greenfield** (constitution built through conversation) and **brownfield** (constitution reverse-engineered from the existing codebase).

---

## 3. The Constitution

Location: `specs/` directory. Three files:

| File | Purpose | Contents |
|---|---|---|
| `mission.md` | The *why* | Vision, target audience, scope, tone |
| `tech-stack.md` | Shared engineering understanding | Languages, frameworks, versions, database, testing framework, deployment constraints |
| `roadmap.md` | Living plan | Sequence of small phases, each implemented via its own feature spec; checkboxes for completion |

A constitution is agent-agnostic and more structured than a single `AGENTS.md`. It records agreements between human and agent, and among humans.

**How to build it (greenfield):**
- Read stakeholder input (e.g., `README.md`).
- Interview the human (use `AskUserQuestion` or equivalent) about mission, stack and roadmap. Ask good questions: unconsidered architecture patterns, existing packages that already solve the problem, tradeoffs (e.g., speed vs. data fidelity), tone, roadmap granularity.
- Organize the roadmap into **small steps** to support human-in-the-loop review.
- Write the three files, then let the human review. Expect gaps (e.g., missing target audience — the agent can't know the business).
- Apply revisions through the agent, not by manual edits, so related documents stay consistent.
- Commit the constitution.

**How to build it (brownfield / legacy):**
- Explore the codebase, commits, `README.md`, `TODO.md`, and any other planning artifacts (issue trackers, docs).
- Reverse-engineer mission (audience, idea), tech stack (file structure, framework versions) and roadmap (phases derived from existing TODOs).
- Ask clarifying questions; incorporate extra context the human provides (e.g., "improve efficiency while shipping requested features").
- Commit. From here the workflow is identical to greenfield.

---

## 4. Feature Loop

### 4.0 Pre-flight checklist (start of every feature)
- No unfinished work; previous feature branch merged to main.
- Next roadmap item is still the right one.
- **Context cleared** (`/clear`) so the agent relies on specs, not stale memory, and has full context budget.
- Create a new feature branch.

### 4.1 Plan: the feature spec
Start from fresh context; read the constitution. Interview the human on key decisions (scope, versions, strictness, validation method). Surface conflicts and problems; the human need not accept proposed solutions.

Write a feature spec directory containing three files:
- **plan** — approach, sequence of work, organized as numbered **task groups**.
- **requirements** — important technical needs and constraints (e.g., pin library versions, strict TypeScript, CSS framework choice). Not minor details like variable names.
- **validation** — how the agent and human confirm success (tests, manual curl checks, running the app).

Human reviews all three. Changes go through the agent so plan, requirements and validation stay in sync. Commit the feature spec before implementing. Time spent here is well spent: spec changes expand into hundreds of lines of code.

### 4.2 Implement
- Clear context, then implement task groups from the plan.
- Default: all task groups at once. For risky areas (security, database, anything where small mistakes compound) or large features, implement **one task group at a time** with commits in between.
- Report a summary of work done per task group.
- Keep changes manageable in size to reduce human **cognitive debt** (the load of tracking what code does and how it evolved) and **AI fatigue**.

### 4.3 Validate
Human reviews diffs at a **high level**: does the feature work and match the spec? Avoid nitpicks. Standard: code the human is willing to commit under their own name.

Rules during validation:
- If a code problem stems from a spec omission, **fix both spec and code** (e.g., add a new task group to the plan). Omissions are not failures; the spec evolves as details are discovered.
- **Prevent drift.** Even trivial IDE refactors (moving files) must be followed by asking the agent to update all references in specs, READMEs and other artifacts.
- Apply cross-cutting preferences everywhere (e.g., "extract prop types into standalone TypeScript types across the codebase").
- Human runs the app and reads/steps through tests under the debugger to *understand* changes, not just confirm they pass.
- **Deep review:** spawn several sub-agents to review the entire project with the feature change. This gives more thinking space and preserves the main agent's context. Apply accepted recommendations, run tests. A second look usually finds important issues.
- Run the changelog skill (if defined), commit, merge the branch.

**Spec versioning on feature branches:** Small constitution changes (e.g., checking off a roadmap item) may ride on the feature branch. Larger constitution changes belong on their own branch so it's traceable which spec version produced which code.

---

## 5. Replanning (Between Features)

"Run slow to run fast." Do this on a dedicated replanning branch.

- **Update the constitution** with missing preferences (e.g., add a testing framework to `tech-stack.md`), then propagate: update existing feature specs and implementation to match, and write the missing tests.
- **Absorb product changes** (e.g., "40% of users are mobile → responsive design"). Update product specs, feature specs and code together. Small changes: implement during replanning. Large changes: schedule as a new roadmap phase.
- **Revisit the roadmap.** Is the next item still correct? Merge related phases if they belong together.
- **Improve the process.** Package repeatable workflows as skills (see §7).
- Specs capture *decisions*, not just code. Keep specs and code in sync for team communication.
- Commit in small steps; merge.

---

## 6. Large Batches / MVP

Implementing the rest of the roadmap in one step is acceptable only when the constitution and existing feature specs are high quality and the human can handle review. Treat it as a stress test of the specs:
- Interview, write MVP feature specs, human reviews for incorrect gap-filling assumptions, commit.
- Implement, run the app.
- Ask the agent to **validate against the specs** and report where the MVP exposes holes in planning.
- If results diverge from intent, run a replanning phase to eliminate whatever led the agent astray. Share the evaluation with stakeholders; merge or archive the branch.

---

## 7. Automating the Workflow with Skills

**Skills** are packages of instructions and resources giving the agent repeatable capabilities with project/org-specific context. Use them for any prompt the human keeps retyping.

Recommended skills:
- **feature-spec** — the standard "start a feature: branch, interview, write plan/requirements/validation" prompt.
- **changelog** — update a changelog on each merge to main for non-technical stakeholders. (Changelogs also communicate with future agents.)
- **validation** — README updates, linting, formatting, test running, other quality checks.
- **research** — capture side investigations (see below).

Skill guidelines:
- Create skills via the agent's skill-creator (interview the human, then write). Restart the agent to load new skills.
- Decide scope: **per-project** vs. **global** (usable across all projects).
- Agents select skills by description (progressive disclosure), but judgment degrades as context grows. **If a skill is wanted, name it explicitly.**
- Skills can call other skills. Many agents are moving from custom slash commands to skills.

**Research backlog:** When an idea arises mid-feature (e.g., database choice) that shouldn't interrupt branch work or enter the roadmap yet, research it with the agent and write a report to a well-known backlog location. Later, schedule it on the roadmap with a link to the backlog file.

**External tools:**
- **MCP** (Model Context Protocol) has been the universal extension mechanism (APIs, knowledge bases, databases).
- Trend: **skill + CLI** is replacing many MCP servers — less setup, less context usage. Example: Context7 (current package documentation, e.g., React 19.2+) offers a CLI + skill option; prefer it.
- **Plugins** bundle agent extensions for sharing across machines/teams. Not a cross-agent standard. They execute code — trust them before install/update.

**Existing SDD frameworks** (adopt, then customize with skills):
- **GitHub Spec Kit** — `speckit.constitution`, `plan`, `tasks`, `implement`.
- **OpenSpec (Fission AI)** — propose/explore (= plan), apply (= implement), archive (= replan); includes quick-feature patterns.
Both provide branch management, verification scripts and opinionated spec formats.

---

## 8. Agent Replaceability

Keep the workflow independent of any one agent or IDE. Relevant standards:
- **MCP** — external tools.
- **`AGENTS.md`** — rules.
- **Agent Skills** — repeatable workflows with context; portable across agents (e.g., the feature-spec skill runs in Codex after copying to its skills path).
- **ACP (Agent Client Protocol)** — connects agents to editors, modeled on LSP; covers features like next-edit suggestion and plan mode. The **ACP registry** automates finding, installing and connecting agents (e.g., OpenCode in JetBrains IDEs).

Choose agents on criteria that matter to the project; leaderboards change fast.

---

## 9. Operating Rules for the Agent (Checklist)

1. Load the constitution (`specs/mission.md`, `tech-stack.md`, `roadmap.md`) at session start.
2. Work one roadmap feature per branch. Never start a feature with unmerged prior work.
3. Plan before code: interview the human, write plan/requirements/validation, wait for review and commit.
4. Ask clarifying questions on key decisions; surface conflicts, tradeoffs and existing packages.
5. Implement task groups from the plan; go group-by-group for risky areas.
6. Keep diffs small and reviewable. Commit frequently.
7. When the human requests a change, update **every** affected artifact — specs, README, changelog, code, tests — to prevent drift.
8. If implementation reveals a spec gap, amend the spec, don't just patch code.
9. Validate: run tests, run the app, offer a sub-agent deep review.
10. Update the roadmap checkbox, changelog, then merge.
11. Between features, propose replanning: constitution updates, roadmap adjustments, new skills.
12. Constitution changes of substance go on their own branch.
13. Never rely on chat memory for decisions — if it matters, it belongs in a spec.
14. The human is responsible for the code; request permission for commands and respect their review.
