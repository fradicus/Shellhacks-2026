# F39 part 13: HIFLD fallback for SERTP

## Decision

SERTP already uses C33 name candidates, C38's operator guard, voltage counter-evidence and uniqueness across
an entire balancing-authority footprint. Keep that behavior and every successful OSM match. Only an endpoint
with `no_facility` may try public HIFLD substations in the same footprint. OSM ambiguity, operator conflicts,
name truncation and voltage conflicts are not rescued by the fallback. Multiple distant HIFLD sites sharing
a name stay ambiguous even if voltage would select one. States come from matched source geometry, never place
knowledge. HIFLD points remain explicitly unreviewed candidates and never create project rows by themselves.

The geometry source is the same public February 2021 HIFLD copy used by F42 (`pnw.build.HIFLD`). Paged downloads
are pinned in `data/southeast/hifld/sources.json`; repeated IDs, wrong-state records and pagination exhaustion fail
closed. Extracts preserve the source ID, name, state, voltage and point. HIFLD supplies no operator field here.
The existing dense `sertp` batch and fixed release remain the publication path; no new loader folder is added.

The initial fresh SERTP fetch failed on Kentucky OSM with HTTP 504. A complete earlier cache was found under the
previous session's `41c0fc00-966a-40ab-91ee-9d371fdff8ab/scratchpad/cache/sertp` and is replayed with its existing
hash manifest. Fetch now saves a manifest after each completed source and verifies cached bytes before reuse.
Only the allowed 2023/2024/2025 preliminary PDFs are ingested; D15 and the 2025 final exclusion remain intact.

## Undo

Restore the previous SERTP locator and batch/release entry, then remove the Southeast HIFLD extracts and module.
The deferred one-endpoint line-policy tightening is not part of this change.

## Measured result and source check

The 331 project IDs and four project sources are unchanged. Centers rise from 117 to 120: three gained,
zero lost, zero moved existing centers. Two gains are Kentucky and one Mississippi. All remain unreviewed.
All three gained names and voltages were checked against the 2025 preliminary PDF and the pinned HIFLD records:

| Project | PDF page | HIFLD ID | Match | Limitation |
|---|---:|---|---|---|
| Cane Run 345/138 kV transformer | 32 | 130528 | Exact normalized name and voltage | Facility candidate, no independent review |
| Middletown–Buckner 345 kV line | 31 | 130652 | Middletown name and 345 kV | One endpoint only; Buckner remains unresolved |
| Philadelphia 161 kV reactors | 122 | 149765 | Exact name and 161 kV | Report additionally names TVA's Mississippi area |

The footprint and counter-evidence checks reject other apparent HIFLD-only possibilities. This increment does
not add Tennessee points or establish full Southeast coverage. The 211 unlocated rows remain visible as unknowns.
