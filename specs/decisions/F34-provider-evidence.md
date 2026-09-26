# F34 implementation claim

Runtime: Codex Astra high; logical role: geo-engineer. Exclusive F34 implementation,
based on reviewed C15 commit 12802fb. Public provider requests remain bounded and
independent; no paid Google verification or credentials are used. The public route
response is an attributed textual summary. Annual satellite embeddings and survey
soil context cannot certify present conditions or engineering suitability.

Implemented a public-only bounded COG sampler using Rasterio's custom opener,
never whole-file file-like reads. Actual Seattle (47.6062,-122.3321),2025 evidence
read 31,820,382 bytes/77requests with object/range/index/pixel identity. The original
8MB official index range produced nine real point-covering rows; only2025 is sampled.
The CLI caps COG reads32MiB/80requests/45s with50s watchdog, index discovery8,008,192
bytes/two requests with35s watchdog. Every accepted AEF sample retains its own
retrieval/range evidence on append; the web checks snapshot and per-record binding.

Independent review corrections: dimensions now require exact whole millimetres and
weight whole kilograms. This avoids silent understatement while respecting Google's
integer-unit contract; no unreviewed ceiling conversion is used. Soil TOP1001 is a
sentinel after1000public rows. Washington requests use a pinned2026Census polygon
after coarse bounding prefilter. Route evidence binds transport hash, retrieval,
geometry digest, sampled points/statuses/requests and departure. Road snapping is
limited100m and disclosed. Route environmental context is explicitly not resolved
to per-point arrival times, so route assessments always remain incomplete. Google
warnings and ignored restrictions remain partial. Public reference rejects queries.

Live public verification reached NWS and USDA successfully; WSDOT was stale under
the15minute policy. Forecast age policy is6hours. These are visible application
thresholds, not provider accuracy guarantees. Google remains unverified with0paid
calls. No real credentials, server preview or Atlas writes were used.

Pre-review baseline checks:353pytest,8Node provider tests,11focusedPython tests,
web lint/typecheck/fixturebuild passed. Post-review checks are recorded in the PR.
Undo by removing the F34 owned modules/artifacts and optional Rasterio extra via
the contract owner. No existing data or MongoDB writer is changed.
