# C46: Overlaps on the driving route (drive rule)

The user asked on 2026-09-27 that the Overlaps page keep its UI and replace the straight line between two related
centers with the actual most efficient driving route, with the distance to match; that a pair counts when that
distance is 25 miles or less; and that the same logic apply to every data point, including the national snapshot.
The user chose open road-network routing over Google so the existing MapLibre map stays unchanged (Google Routes
content may not be shown on a non-Google map; C15 already forbids it on MapLibre).

While this was in draft, C48/F48 shipped straight-line national pairs ("provisional, simple 25-mile circles for
now"). The user then chose to upgrade those pairs to this rule as a follow-up on F48's own files, not a new feature.

## Evidence

- Challenge brief (`docs/Sperry-Tech-Challenge/ShellHacks_Challenge_Gridlock.docx`): two projects overlap "if they
  are within 25 mi of each other. Closer than 25 mi, we flag it." No distance method is required.
- Companion guide (`Finding_Real_Locations_Guide.docx`, Part 3): "straight-line/haversine is fine — no need for
  driving distance". Straight-line is permitted, not mandated; road distance is a stricter reading of "within".
- The sponsor workbook is a straight-line worked example. By stored road routes, 3 of its 6 example pairs are within
  25 miles (13.03, 13.94, 23.19 drive mi); OVL_2 is 5.65 mi apart in a line but 31.24 by road.

## Options

1. Keep the straight-line rule and only draw roads: pairs could show road distances above 25 mi. Rejected by the user.
2. **Drive rule for every corpus, straight line as a pre-filter (chosen).**
3. Replace the canonical rule outright: breaks the sponsor workbook check and every caller in one step.

## Contract (additive only)

- `pipeline/matches/core.py`: `route_candidates`, `straight_line_mi`, `is_drive_overlap`, `comparable`, and
  `overlaps(projects, date, drives=None, *, known=KNOWN_UTILITIES)`. With `drives` it applies
  `overlap-25mi-drive-v1` / `nearby-band-drive-v1` and adds `drive_mi`; band follows the drive. Without `drives`,
  the unchanged straight-line example rule (`overlap-25mi-v1`), so existing callers keep working until they move.
  `known=None` compares any named utility (national owners). `priority_key` sorts on the drive when present.
- `pipeline/matches/routes.py` (store, staleness binding, polite fetch loop) and `pipeline/matches/osrm.py` (client).
  Shared because F10 routes now and F48's national pairs route next. A route is bound to the exact centers it was computed from.
- `schemas/route.schema.json` (new); `schemas/match.schema.json` gains optional `drive_mi` (≤ 25) and `route`;
  `distance_mi` becomes ≤ 25 (a candidate exactly 25 mi in a line can still drive exactly 25).
- `web/lib/types.ts`: `MatchRoute`, optional `Match.drive_mi` and `Match.route`.
- `data/fixtures/routes.json`, `data/fixtures/golden/routes.json`; `data/fixtures/matches.json` rebuilt on the drive
  rule (3 pairs, each with its route). Golden tests keep the workbook's straight-line check and add the drive rule.
- Specs: mission rule and priority, test conventions (no fixed corpus counts), F10 owns `data/routes/`, F19 steps
  22-24, F48's drive-rule follow-up, roadmap note.

## Router

Public OSRM (`https://router.project-osrm.org`, `OSRM_URL` overrides), driving profile, fastest route; the
usage policy allows at most one request per second, which the fetch loop honors. Routes are fetched once by a
person running a command and committed; the website and the match run never call a router. If the public server
throttles or changes, point `OSRM_URL` at a self-hosted OSRM (free Docker image with an OSM extract). Route data is
© OpenStreetMap contributors under the ODbL; the committed route files carry that attribution and stay ODbL.

## Merge order

1. `[FIX-F07]`, `[FIX-F06]`: smoke and loader tests read expected pairs and counts from the fixture files.
2. `[C46]` (this).
3. `[FIX-F12]` brief facts pass a match's stored drive to the matcher and cite drive miles when present. Works on
   both straight-line and drive matches.
4. One stack, merged back to back: `[FIX-F10]` routes the full corpus and rebuilds `data/matches/` on the drive rule,
   then the owners' refreshes of artifacts bound to exact match records: `[FIX-F12]` briefs, `[FIX-F13]` audit
   verdicts, `[FIX-F15]` coverage, each dropping fixed full-corpus pair counts. Each PR is based on the previous
   one; `main` is green only after the last. Merging publishes to Atlas.
5. `[FIX-F19]` draws routes and road miles. Tolerates records without routes, so it may land any time after C46.
6. `[FIX-F30]` first: F30's loader tests give their synthetic pair a stored route and the load summary names the
   rule the coverage reports (safe on either generator). Then `[FIX-F48]` national pairs on the drive rule: F48
   stores routes for its straight-line candidates in
   `data/national_pairs/routes.json` and keeps pairs whose drive is at most 25 mi; F19 then draws and labels them
   like filing pairs. Until then F48's pairs stay straight-line and labeled provisional (C48).

An F13 downgrade may be re-bound to a changed pair only when every supporting endpoint verdict is still current; a
pair that was never audited stays `needs_review`. Nothing is promoted.

## Undo

Revert F48's drive follow-up, then F10's data (restores the straight-line matches), then this PR. Because the contract is additive,
reverting only F10's data returns production to the straight-line rule with no code change.
