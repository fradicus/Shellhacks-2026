# F30: Assemble the reviewed Mid-Atlantic release

C28 authorizes F30 to consume F38's fixed Mid-Atlantic release after the existing New England and Southeast producers. The delegated Codex session `f38_grid_research` adopts the F30 data-researcher role in a separate worktree; source production and independent reviews remain separate assignments.

Use the existing fixed-path assembly loop. Import `expansion.mid_atlantic` only when `data/expansion/mid-atlantic/releases/active.json` exists, so this consumer can land before the producer. Missing releases preserve the baseline; producer or assembled-snapshot validation errors prevent staging. Recompute final national and per-source coverage while preserving every producer summary and project evidence. Original snapshot generation remains unchanged.

Undo through a reviewed F30 revert; activation and rollback remain with the existing national loader and load Action.
