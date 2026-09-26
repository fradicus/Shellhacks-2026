---
id: F34
name: Environmental evidence and truck-aware conditions
lane: A
agent: geo-engineer
phase: 6
depends_on: [F00]
owns: [pipeline/environment/, data/environment/, web/lib/operations/, web/app/api/operations/, tests/pipeline/test_f34_, tests/web/operations-providers/]
cut: never
---

# F34 Operational evidence

Implement C15 provider contracts and Zod types. Add a bounded actual AEF GCS COG point sampler with the optional Rasterio extra, pinned index/object identity, nonlinear int8 decode, nodata/CRS/pixel/year checks, attribution, byte/request/time limits and replayable sample evidence. Domain-owned schemas validate artifacts. Annual embeddings cannot yield soil strength or a categorical environmental assessment without an independently validated downstream model. The web reads only matching evidenced point/year artifacts; a missing point returns unavailable.

Implement fixed-host server-side NWS forecast/alerts, USDA mapped soil context, an actually validated official WZDx feed with explicit jurisdiction coverage, and configured Google TRUCK route adapter. No paid calls during worker verification. Require server credentials and explicit LVR-enabled setting; no DRIVE fallback. Bind truck, departure and geometry; request and disclose ignored restriction flags. Route content uses Google's attribution/retention requirements and is never overlaid on MapLibre. Route/site sampled weather, roadworks and annual evidence remain distinct. Missing coverage does not imply no hazard. Worksite/route assessment stays incomplete when required evidence is unavailable.

Use independent result envelopes, strict bounded inputs, timeouts and response-size budgets, typed parse validation, source times and stated freshness limits. Do not retain stale observations as live or fill missing severity/date/units with benign values. Never fetch arbitrary client-supplied URLs or pass arbitrary SQL; USDA query coordinates must be validated numbers embedded only in a fixed query. No provider secret or raw Google response in git/browser output.

Test HTTP failures, stale/future/missing times, null alert geometry, route sampling gaps, unknown jurisdictions, incomplete vehicle profiles, ignored restrictions, malformed provider output, cache binding and unavailable AEF. Verify at least one permitted real public sample/feed where reachable, record failures honestly, and preserve unit fixtures as test-only. Full checks and independent review required.
