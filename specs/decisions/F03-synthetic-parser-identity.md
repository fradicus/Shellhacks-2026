# F03: keep the invented fixture clear of reviewed source-page overrides

The Alpha/Beta offline fixture claims DESC 2024 page 3 metadata to exercise forged-source
and forged-cache rejection. F01 now correctly binds that real page to project `0139 M,N`.
Parsing the invented fixture under the real identity therefore fails before its intended
validation test can run.

Move the normal fixture to claimed DESC 2024 page 5, updating its invented card header and
all ten response citations together. That page has no reviewed endpoint override in either
main or the pending F01 fix. The invented Alpha/Beta content remains explicitly synthetic;
it is not presented as actual page 5 evidence. The Page intentionally retains claimed real
metadata so actual-PDF and forged-cache tests continue to reject it before any network call.

This is a fixture-only compatibility repair: no parser adapter, production module, source
allowlist, or test assertion changes. If page 5 later receives a reviewed override, the
fixture will fail visibly rather than bypass that guard.

This tests local validation only; there are still no real Gemini calls or recorded responses.
Undo by replacing the invented fixture with separately labeled genuine recorded evidence,
while retaining an explicit invented-source adversary for provenance rejection.
