# Evidence and export QA

Base: `33a493b`, after F11, C3 and the sources API merged. Runtime: Mac Codex, F07 independent QA. Original fixture data is unchanged.

## Passing checks

The production-fixture Playwright suite now has **16 passing checks** across desktop (1440×1000) and mobile (390×844). It retains all six previous navigation/map checks and adds:

- The OVL_2 card shows 5.65 mi, a 152-day gap, the exact filed dates, one/two-endpoint center bases, sponsor workbook citations, unknown owner codes and Needs review.
- No absent Gemini brief or unconfirmed review is presented as completed work.
- Print calls `window.print`; print CSS hides navigation/actions while keeping the card and both evidence panels/citations visible. This checks print behavior, not pagination for arbitrary future content.
- CSV headers preserve source/precision/confidence fields; the fixture exports six historical pairs and ten projects. Future pairs export only the header. Response content type and attachment name are checked.
- Invalid export query parameters return 400. Formula-like text receives an apostrophe; quotes/newlines escape correctly and negative numeric longitude remains numeric.

Local result: **16 passed (4.8s)** on Node 24.13.0 / Playwright 1.63.0. Existing pipeline: **98 passed (13.30s)**. Web lint, typecheck and fixture production build pass.

Rebase checkpoint `c8a8902`: C4 aligns fixture filing source IDs with F01's manifest and includes the two cited public DESC sources. Reviewed those changes and reran all repo checks (98 pipeline tests), the test-file TypeScript check, and all 16 browser checks successfully.

Checkpoint `39cd085`: F14 now renders filing history. Added desktop/mobile checks for the verified 0139 M,N date change, both public PDF page links, historical labeling, field filtering and the empty state. The suite now contains 18 checks. A separate Chromium Letter-size print of the sponsor OVL_2 card produced one page with both evidence panels; arbitrary future content pagination remains unverified.

Checkpoint `684e270`: verified the F06 loader fix with independent in-memory failure injection. Reloading the active revision leaves its documents unchanged, and a failed new revision preserves the active pointer/data and records a failed run. Repo checks pass with **101 pipeline tests**; all **18 browser checks pass (4.7s)** on the rebased branch. The URL-page finding #28 remains separate.

## Confirmed defect outside F07 ownership

[F11 issue #28](https://github.com/fradicus/Shellhacks-2026/issues/28): metadata/page code decodes the route ID again. A temporary copy of the sponsor fixtures with only a synthetic match identifier (`QA:SYNTHETIC%zz__PAIR`) renders a server-error screen and React error #441. The response can be HTTP 200, so checking status alone misses the failure. The regular pair tests now assert the actual coordination-card region.

This synthetic fixture was used only under `/private/tmp` with `FIXTURE_DIR`; it was neither committed as project data nor loaded into Atlas. The issue records a reproduction. Product fixes remain with F11's owner.

## Integration limits

This does not certify Gemini output, real-corpus matches, live Atlas, a deployed domain, or restricted Georgia source handling on real records. The golden sample contains workbook citations only; public PDF citation links and future real-record field evidence need validation as those records reach the pair view. Existing open loader/API findings remain tracked in #17.
