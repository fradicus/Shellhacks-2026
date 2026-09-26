---
name: "qa-acceptance"
description: "Independently verify golden math, public evidence and the deployed judge workflow with explicit limits."
---

# QA acceptance

## Inputs
Original untouched workbook, approved source pages, build revision, dataset version, contracts and proposed featured claims.

## Procedure
1. Independently recompute workbook centers and all 25 cross-utility pairs. Expect six exact OVL IDs, 19 exclusions, distances 4.09/5.65/7.55/8.01/14.34/14.81 and gaps 3074/152/517/3074/365/730. Do not obtain expected values from the implementation under test.
2. Test strict 25-mile boundary, one/no endpoint, unknown and partial dates, leap-day arithmetic, reverse pairs, duplicate input versions, invalid GeoJSON and display rounding. Check the documented ranking and null impact behavior.
3. Inspect every featured production pair against source pages, owner mapping, location decisions and date precision. Revisit CEII/public classifications. The immutable sample regression and corrected production attribution have different purposes.
4. Audit Gemini's reference-set outcomes and all featured briefs. Check cited fact IDs, unsupported numbers, malicious input handling and service-failure states. Keep failures in the report.
5. Test Atlas idempotency, active-run promotion, version references, bounded routes, protected generation, CSV formula escaping and absence of client secrets. Inspect evidence of live database use.
6. Run the full map/list/detail/export flow, historical/future filters, keyboard route and empty states. For R2 compare published and hypothetical views then reset; inspect original records for accidental mutation.
7. Re-run the critical path against the actual deployed revision after release. Record host/domain/TLS outcomes, Gemini metadata and Atlas query evidence. Mark unresolved core requirements as blockers, not implied passes.

## National and 3D acceptance
Verify the date-height formula on all golden records; toggle 2D/3D without changing any match facts. Check unknown-date tray, scenario ghost/reset, reduced motion, region-seam pair selection and WebGL fallback. Reconcile region/utility counts to actual reviewed source scope; inspect duplicates and missing-coverage labels. Measure the declared rendering/feedback targets on the real demo device. No planning-only test proves graphics performance or national data coverage.

## Output and checks
Acceptance matrix with case, expected/observed outcome, command or steps, revision/dataset and evidence path. State what was not exercised. QA signs off independently; authors do not approve their own featured evidence. After freezes, widen testing only for changes or unresolved failures.
