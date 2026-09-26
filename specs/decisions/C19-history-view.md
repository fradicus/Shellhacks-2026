# C19: a 3D History sibling to the main time view

Status: specification approved by the user on 2026-09-26; implementation pending.
Tracking: [issue 104](https://github.com/fradicus/Shellhacks-2026/issues/104).

## Decision

The user selected a separate, visually rich Three.js History page that remains very similar to the main time
view. `/time` stays the primary planning surface, as specified by F21. `/history` will share its map controls,
vertical time direction, utility colors, selection behavior and evidence presentation. Historical framing,
a scrubbable year plane and documented event markers provide the distinction.

This replaces the earlier proposal for a mode switch within `/time` and the alternative horizontal-timeline
page. Neither alternative is the requested design. The existing Historical pair filter remains available and
does not become a claim that those projects completed or received contracts.

## Scope and ownership

This C19 PR delivers specifications only, under the user's explicit request to create an issue, isolated
worktree and PR and merge it. The first-run gates are historical for this bounded task. Codex local acts as
the lane B technical-lead / contract owner. It does not resume an autonomous build, reassign an active feature,
or add a completion marker for F37.

[F37](../features/F37-history-view/spec.md) defines the future page, evidence adapter and acceptance criteria.
It is assigned to codex-local for a later explicit implementation start. F19 owns the existing time scene;
F21 owns the visual direction. Shared scene extraction and navigation need a separate contract change with
an agreed file-ownership boundary before F37 starts. Do not duplicate the renderer or edit another owner's
route as a shortcut.

C15 / PR102 proposes F33–F36 operations evidence and actual outcomes. Those contracts remain pending until
merged. F37 must use compatible accepted outcome types if available and keep any contract-award evidence
additive. It does not take over operations ingestion, outcome estimation or the planning desk.

## Evidence and delivery

The first implementation step is to verify a small public source set for actual historical records and
project-to-contract links. The current project milestone data does not establish award or completion.
Report partial coverage and missing contract evidence explicitly. Keep estimates, awards and actual spend
separate; no inferred contractor, date, location, completion or savings.

The intended demonstration starts at a planned project, opens History with supported context, scrubs a past
period and opens a documented event and its original source. Contract-discovery acceptance requires a real,
verified award/contract example; a working history scene alone cannot satisfy that requirement.

## Reversibility

The proposal adds a separate route and retains `/time`. A later spec change can defer F37 without changing
existing matching, ranking or project records. No application behavior or schema is changed by this PR.
