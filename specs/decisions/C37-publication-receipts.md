# C37 Publication receipts in the load Action

User direction on 2026-09-27: verify a data release once, as part of shipping it, instead of a later PR
that only commits receipts. Applies to every feature that publishes through the national snapshot
(F30, F38–F42 and later geographic work).

## Problem
Only the load Action writes Atlas, and it runs after merge. Live checks therefore came after the data PR,
and workers committed Atlas/browser/export receipts (JSON and screenshots) in separate PRs. Each receipt
needed a branch, claim, CI run and review, and it held the feature's single open-PR slot.

## Accepted contract
- **Before merge:** `cd pipeline && uv run python -m common.publication` prints the expected per-state
  projects, drawn points (confirmed / tentative / county) and ID digest from the assembled snapshot. Paste the
  table, or the rows for your states, into the data PR. It uses no database.
- **After merge:** the load Action runs the same module with Atlas access. It reads the active dataset back and
  fails if the dataset is not the merge commit, or if the project IDs or any per-state count differ. Its step
  summary is the Atlas receipt. Link the run in a comment on the merged PR.
- **Browser spot check** (optional, when UI behavior is in question): open the map filtered to the state and
  describe the result in a comment on the merged PR, not in a committed file.
- Do not open PRs whose only content is receipts. Receipt JSON and screenshots stay out of the repository.
  Existing committed receipts remain as history.
- "Drawn" follows `displayPoints()` in `web/lib/national/locations.ts`. `common.publication.display_kind`
  mirrors it; change both together.

This satisfies the "confirm through Atlas RO after the Action" and "visible on the existing maps" criteria
in F38/F39 and later geographic specs. Map rendering itself is covered by the web tests of those rules.
Merges that do not touch `data/**` do not trigger a load; run `load` with `workflow_dispatch` when a
receipt is needed for them.

## Delivery
`pipeline/common/publication.py`, a verification step in `.github/workflows/load.yml` and
`tests/golden/test_publication_receipt.py`. Complements C36 (CI scope and rebase churn); it does not change
`ci.yml`.
