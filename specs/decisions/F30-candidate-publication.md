# F30 candidate publication (C48)

This Codex local session adopts F30's data-researcher role for C48 integration.
F48 is merged in #256. Generate provisional pairs from the assembled national
snapshot and stage them under the same dataset before activation. Pair generation,
write, count verification or ready-run failure must preserve the previous pointer.
Record pair coverage with the run; retain pairs for the same two datasets as projects.

The existing load Action remains the sole writer. Dispatch that Action on main
after merge and verify its stored pair count and a dataset-pinned read. No manual
Atlas writes, producer snapshot edits or project-coordinate changes.
