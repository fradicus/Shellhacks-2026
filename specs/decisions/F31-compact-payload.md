# F31: compact project summaries and selected evidence

The user assigned the spec and implementation to this Codex local session on
2026-09-27. This is a bounded follow-up under the existing F31 frontend-engineer
assignment; original run gates are historical. F31 ships the summary/detail
contract and Explorer integration, then this session adopts it in an F19 PR.
No overlapping F31/F19 implementation claim was open when this work began.

## Contract

- Add an explicit summary DTO with only map/list/filter fields and source locators.
  Initial summaries omit raw source fields, verification ledgers, facility evidence
  and descriptions. Full records remain available through detail and export reads.
- Project IDs, coordinates, date precision, tiers, count/truncation semantics and
  county display rules stay unchanged. Source catalog data stays available.
- The existing full loader remains available for History's server-side event
  derivation and existing API consumers. History already sends derived events;
  do not delete their meaning, dates or citations to reduce bytes.
- Compact loader output uses the existing dataset cache, then projects summaries
  before the server/client boundary. Never mutate cached full records.
- A bounded read-only `/api/national/project?id=...&dataset=...` returns one full
  project and its source from the exact requested active dataset. Reject invalid,
  duplicate or unknown parameters. A changed dataset returns an explicit refresh
  response instead of silently mixing versions. Missing records and DB failures
  have distinct responses. Snapshot mode remains explicit and production-disabled.
- Fetch details only for a selected project, with loading, error and retry states.
  Abort outdated requests and prevent a prior project's evidence flashing under
  a new selection. Preserve the existing evidence contents once loaded.
- Exports retain full evidence. No new dependency, credentials, writer, raw source
  edits, geographic inference, animation or visual-design changes.

## Validation

Verify summary projection removes heavy fields without changing map/list facts;
full records/cache remain unchanged; detail queries are dataset/ID scoped; invalid
parameters, absent records, unavailable DB, snapshot restrictions and dataset
changes are handled. Browser checks cover selection, rapid selection changes,
retry and existing evidence. Run required CI and measure serialized full vs summary
payload sizes from the same read-only dataset. Report local measurements honestly.

## Local payload measurement

Read-only Atlas dataset `b73dc34bb745f79f494504b8ac25553b8aa2b59d`, 2026-09-27,
3,648 map records, page 1 / 25: full explorer JSON 14,631,749 bytes; summary JSON
4,841,341 bytes (66.9% smaller). Map-project arrays alone: 12,788,053 to 3,055,038
bytes. Counts, geometry, labels and date precision are preserved. These are
uncompressed serialized loader payloads, not measured HTTP transfer or page timings.
