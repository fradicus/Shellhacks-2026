# F40 publication release (part 2)

**Release `great-lakes-2026-09-candidates-1`: 1,475 projects from 54 source artifacts; 663 drawable points
(536 C26 candidates, 127 C25 official owner-map points), 527 distinct coordinates; 0 independently confirmed.**

| | Count |
|---|---|
| National snapshot before (committed, `national.build.load_snapshot`) | 1,578 projects, 681 with a center |
| After `greatlakes.publish.apply_release` | 3,053 projects, 1,344 with a center; `validate_snapshot_values`: 0 errors |
| Sources | 54 national-source records, one per hashed artifact (6 MN report pages, ATC PDF, MISO workbook, NYISO PDF, 3 AEP state maps, 42 FirstEnergy pages) |

## How it reaches the map

Following [C29](../../specs/decisions/C29-texas-candidate-publication.md) and [C26](../../specs/decisions/C26-great-lakes-candidates.md):
`data/greatlakes/releases/active.json` pins the SHA-256 of `data/greatlakes/projects.json` and `sources.json` and
the expected counts. `apply_release(snapshot, root)` refuses changed hashes, duplicate or colliding IDs, schema
failures, project/source hash mismatches, source project counts, any reviewed state other than `unreviewed`, points
outside their source states, candidate centers that are not the site point or mean of their matched facilities, and
official points that differ from the owner's marker. A missing active file changes nothing.

**Not yet live.** F30's owner must add `("greatlakes", "greatlakes.publish")` to the fixed producer list in
`national.build.load_snapshot` (issue #153); the existing load Action then writes Atlas. `/explore` already draws
`unreviewed` centers with their label; `/time` (F19) currently draws confirmed points only.

Replay: from `pipeline/`, run each adapter's `build --check`, then `uv run python -m greatlakes.publish --check`.
