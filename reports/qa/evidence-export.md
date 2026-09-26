# Evidence, export and filing-history QA

Verified against `bd01ad6` (the F18 report update after `ef6110c`), including F11 evidence/export, F14 filing history, F02 Georgia data and the loader/pair-page fixes. Runtime: Mac Codex, F07 independent QA. Original fixture data is unchanged.

## Browser coverage

The production-fixture Playwright suite contains **18 checks** across desktop (1440×1000) and mobile (390×844):

- Navigation routes return 200 without console errors. Six historical pairs rank correctly, select on the map and open an actual coordination-card region. A failed basemap preserves the accessible table and selection.
- The OVL_2 card shows 5.65 mi, a 152-day gap, exact filed dates, one/two-endpoint center bases, sponsor workbook citations, unknown owner codes and Needs review. An absent Gemini brief remains unavailable.
- Print calls `window.print`; print CSS hides navigation/actions while keeping the card and both evidence panels/citations visible. A separate Chromium Letter-size print of OVL_2 produced one page with both panels.
- CSV responses preserve source/precision/confidence columns and attachment headers. Fixtures export six historical pairs and ten projects; future pairs export only the header. Invalid queries return 400. Formula-like text receives an apostrophe, quotes/newlines escape correctly, and negative numeric longitude remains numeric.
- Filing history shows the verified 0139 M,N date change, both public PDF page links, historical labeling, field filtering and an honest empty state.

## Independent defect verification

[F11 issue #28](https://github.com/fradicus/Shellhacks-2026/issues/28) originally reproduced an HTTP-200 server-error screen and React error #441 using a temporary fixture with match ID `QA:SYNTHETIC%zz__PAIR`. On fix `5354acf`, the same encoded URL returns 200, renders one Coordination card, preserves the exact identifier in the title and produces no browser page errors. The reproduction is resolved.

[F06 issue #17](https://github.com/fradicus/Shellhacks-2026/issues/17): independent in-memory failure injection against `684e270` confirms that retrying the active revision leaves its records unchanged. A failed new revision preserves the active pointer/data and records a failed run.

The synthetic fixture remained under `/private/tmp` with `FIXTURE_DIR`; it was never committed as project data or loaded into Atlas. Product fixes were made by their owners.

## Integration audit

Reviewed F02's parser, owner mappings, summary and decision: cost fields remain null, redacted costs are not retained, unverified owner codes remain unknown, endpoint ambiguities and the conflicting status of TEAMS 20482 remain flagged for later review. This is a code/data review, not an independent recount of all PDF rows.

Repo checks pass on the integrated code from `ef6110c`: **107 pipeline tests**, Ruff, web lint, TypeScript and fixture production build. Spec lint and F07 ownership pass. The QA TypeScript check also passes.

## Production failure state

A separate production build and server with `DATA_MODE` and Atlas credentials unset renders Data unavailable on home, filing history and the pair page. No sample match/card appears and no browser page error occurs. Projects, matches and CSV APIs return 503. Health still returns the explicit F08 placeholder (501); release work is unfinished.

## Limits

This does not certify Gemini output, full real-corpus extraction/matches, live Atlas, a deployed domain or live basemap content. Browser coverage verifies citation links and fixture behavior; it does not independently validate every linked source or pagination for arbitrary future content.
