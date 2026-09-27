# F30: assemble reviewed F38 locations before national activation

Codex-local, delegated data-researcher session `f38_grid_research`, claims the F30 integration required by
[C23](C23-f38-location-publication.md). F38 owns its producer and active release in PR #142; F30 owns only
national assembly and loader validation. Base committed snapshots stay unchanged. The fixed reviewed release
is applied in memory after base validation and before staging, then coverage is recomputed and validated.

No direct Atlas writes are authorized. The existing load Action remains the sole writer. This claim cannot
merge before F38 PR #142 and green current-main CI. The root coordinator handles the final merge.
