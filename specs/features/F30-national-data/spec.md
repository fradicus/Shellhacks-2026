---
id: F30
name: Trusted national source registry, geography and ingestion
lane: A
agent: data-researcher
phase: 5
depends_on: [F00]
owns: [pipeline/national/, data/national/, tests/pipeline/test_f30_]
cut: never
---

# F30 National public data

Follow Plans B and D's source, provenance, uncertainty and sponsor-rule requirements and C11's follow-on boundary. The scope is an extensible verified-source registry, complete federal state/county reference geography, and a real first regional project import; it is not a claim that every US project is already available.

## Requirements

1. Obtain authoritative Census state/county identifiers and label Census regions separately from transmission planning regions. Retain exact original URLs, SHA-256, retrieval timestamps, data vintage and field meanings. Leading zeroes are significant.
2. Catalogue verified FERC/EIA and official regional/state/utility sources by their actual roles, authority and retrieval status. Do not copy unverified project counts from the user's research. Existing infrastructure geometry and distribution-service counties cannot establish future project sites.
3. Implement a bounded download/cache and adapter interface with an explicit reviewed-source allowlist; no arbitrary URL ingestion from a user or extracted document. Fail on unexpected source format, duplicate identities, invalid geography, oversized/archive payloads or changed required columns. Keep original rows/pages and raw milestone text for traceability.
4. Import at least one verified current public machine-readable regional project source into a separate national snapshot. Preserve source/project identity, owner-as-published, status, planning region, stated states/counties, exact or partial milestone precision and missing coordinates. Do not fabricate an EIA match, source publication date, project center, cost or confidence probability.
5. Reuse sponsor arithmetic and strict <25-mile semantics if producing candidate pairs from verified owners and evidenced centers. No center means no spatial candidate. Exact day differences require two exact dates. Never replace canonical legacy matches with a new ranking.
6. Validate all records and produce ingestion coverage/failures with explicit source-level counts. Repeat offline parsing is deterministic; retrieval time belongs to source evidence, not invented record events. Expose a CLI for intentional refresh and cached replay.
7. Provide an isolated namespace loader for national snapshots as described in C11. Validate-only without RW; atomic national activation; idempotent dataset imports; never touch legacy datasets or the other worker's search/embedding collections.

## Validation

Meaningful tests cover source-row parsing and page/row citations, changed headers, uncertain dates, unknown/ambiguous owner and geography, leading-zero codes, duplicate IDs, missing geometry, unsafe downloads, deterministic replay, failed-load activation and idempotency. Validate a real retrieved snapshot and inspect representative rows against the official file. Run repo-wide checks. Document actual coverage and unimplemented adapters in `data/national/README.md`.

## Reviewed location publication (C23)

Validate the committed base, apply F38's fixed `data/expansion/releases/active.json` in memory, recompute national
and per-source coverage, and validate the assembled result before staging. Missing releases preserve the base;
invalid releases fail closed. Preserve F38's expansion summary and embed its evidence under the same national
dataset pointer. `build_snapshot` continues to emit only original base observations, never an applied overlay.

## Southeast additions (C27)

After the validated base and optional C23 overlay, invoke F39's fixed-path assembler for
`data/southeast/releases/active.json`. Recompute national and per-source coverage and validate
the combined snapshot before staging. Preserve both producer summaries, project events and
location evidence. Missing active releases leave the original base behavior intact; invalid
Southeast releases must prevent activation. The existing load Action remains the sole writer.

## Mid-Atlantic additions (C28)

After C23 and C27, invoke F38’s `expansion.mid_atlantic.apply_release` only when
`data/expansion/mid-atlantic/releases/active.json` exists. Pass the full assembled snapshot,
preserve all producer summaries and evidence, recompute national and per-source coverage,
and validate before staging. Missing releases preserve prior behavior; invalid releases
prevent activation. Original snapshot generation and the sole load Action writer are unchanged.

## Texas candidate release (C29)

After the existing overlays, invoke F41's `texas.publish.apply_release` only when
`data/texas/releases/active.json` exists. Its fixed eight-project candidate release must pass producer checks
and final national snapshot validation before database staging. Recompute aggregate and per-source coverage
under the same dataset pointer. The candidates remain `unreviewed` and generate no national overlap pairs.
Missing input preserves previous behavior; invalid input fails before the sole load Action writes Atlas.
