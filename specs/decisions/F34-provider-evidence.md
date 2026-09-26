# F34 implementation claim

Runtime: Codex Astra high; logical role: geo-engineer. Exclusive F34 implementation,
based on reviewed C15 commit 12802fb. Public provider requests remain bounded and
independent; no paid Google verification or credentials are used. The public route
response is an attributed textual summary. Annual satellite embeddings and survey
soil context cannot certify present conditions or engineering suitability.

Implemented a bounded public COG sampler using Rasterio's custom opener.
The real Seattle point (47.6062, -122.3321), year 2025, required 31,820,382 bytes
and 77 requests with object, range, index and pixel identity. The original 8 MB
official index range produced nine matching rows; only 2025 is sampled.
The CLI caps COG reads at 32 MiB, 80 requests and 45 seconds, with a 50-second
watchdog. Index discovery allows 8,008,192 bytes and two requests with a 35-second
watchdog. Every accepted AEF sample retains its own
retrieval/range evidence on append; the web checks snapshot and per-record binding.

Independent review corrections: dimensions now require exact whole millimetres and
weight whole kilograms. This avoids silent understatement while respecting Google's
integer-unit contract. Soil TOP1001 is a sentinel after 1,000 public rows.
Washington requests use a pinned 2026 Census polygon
after coarse bounding prefilter. Route evidence binds transport hash, retrieval,
geometry digest, sampled points/statuses/requests and departure. Road snapping is
limited to 100 m and disclosed. Route environmental context is explicitly not resolved
to per-point arrival times, so route assessments always remain incomplete. Google
warnings and ignored restrictions remain partial. Public reference rejects queries.

Live public verification reached NWS and USDA successfully; WSDOT was stale under
the 15-minute policy. Forecast age policy is six hours. These are visible application
thresholds, not provider accuracy guarantees. Google remains unverified with0paid
calls. No credentials, server preview or Atlas writes were used.

Post-review checks: 354 pytest tests, 13 Node provider tests, 12 focused Python
tests, Ruff, web lint/typecheck/fixture build, spec lint and ownership passed.
Independent review accepted a3f4992; subsequent rebase onto b9968b5 preserves
the accepted feature code. Full Python checks preceded that visual-token-only
rebase; focused and web checks were repeated afterward. Exact-head CI is required.
Undo by removing the F34 owned modules/artifacts and optional Rasterio extra via
the contract owner. No existing data or MongoDB writer is changed.
`/api/operations/conditions` is an additive point-only current-conditions endpoint for F36 polling. It uses the existing weather/roadwork adapters exclusively, preserving independent status/time/evidence and 60-second reference cadence without repeating USDA, AEF or Google. The focused regression checks both allowed provider calls and strict malformed/unknown/duplicate query rejection at the actual route handler. Site and route APIs are unchanged. This extension was rebased onto main 62cf6c85 before implementation; its final checks and exact-head CI supersede the earlier marker.
The NWS default identifies the public project issue URL; a nonblank `NWS_USER_AGENT` overrides it. Missing credentials no longer disable this free provider. Focused tests verify default/override/blank fallback and reference readiness without making any live request.
Final extension validation on main 7e1d3fd: 379 full pytest tests, 15 Node provider tests, Ruff, web lint/typecheck/fixture build, spec lint, ownership and Graphify AST update passed. Root accepted the narrow conditions endpoint; the NWS public contact default and override have dedicated tests. No additional live requests were made.
