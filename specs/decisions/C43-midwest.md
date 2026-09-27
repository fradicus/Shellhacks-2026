# C43: Midwest rollout (IA, MO, KS, NE, ND, SD)

## Authority

On 2026-09-27 the user told this Claude local session to do the Midwest after reviewing the plan below ("let's do
this"). Claude local adopts the technical-lead contract role for this change only; no existing ownership changes.

## Findings (origin/main `b73dc34`)

- The Census Midwest is 12 states. [F40](../features/F40-great-lakes/spec.md) covers MN, WI, MI, IL, IN and OH. The
  other six have 0–2 national records each: Iowa, Missouri, Kansas, Nebraska, North Dakota, South Dakota.
- SPP's public **Q3 2026 Quarterly Project Tracking Report** ([page](https://www.spp.org/engineering/project-tracking-ntcs/),
  appendix zip `/Documents/77416`, no login) lists every SPP-approved (NTC) upgrade: state, owner, project and
  upgrade names, owner-indicated in-service date, status, cost. 481 upgrade rows (128 projects) list only these six
  states: SD 130, ND 100, KS 93, NE 87, MO 69, IA 3. One further row lists KS and AR.
- The From/To bus columns are empty on 385 of those rows. The upgrade name states the facilities
  ("Lake County - Howard 115 kV Ckt 1 New Line", "Tekamah 161 kV Substation").
- F40's pinned MISO workbook (`miso-mtep26-eval`, sha256 `40f325fe…`) holds 86 rows F40 excluded only as outside its
  states: MO 38, IA 33, ND 11, SD 4. MISO's site and Appendix A still return HTTP 403 to scripted requests.
- Iowa is MISO territory, so SPP covers it barely. State dockets (Iowa Utilities Commission franchise dockets, ND
  PSC and SD PUC siting cases) name Iowa and MISO long-range lines but need page-verified transcription.

## Decision

1. **F46 (claude-local)** covers the six states. Every row whose listed states are all among the six is in scope;
   any other row is excluded with the reason.
2. **Part 1: SPP.** One record per upgrade (`UID`), `_id` `spp-qpt-2026q3:<UID>`, `major_project` the SPP project
   name, `part` the upgrade name, `states` the row's states. Status groups:
   `planned` for On Schedule < 4, On Schedule > 4, Delay - Mitigation and Delay - Mitigation Window;
   `proposed` for NTC - Commitment Window, NTC-C Project Estimate Window, Re-evaluation and Identified;
   `in_service` for Complete, In Service and Closed Out; `cancelled` for Withdrawn; anything else `unknown`.
   The owner-indicated in-service date is a day-precision `planned_milestone` event. An in-service row instead gets
   an `in_service` event, dated only when that date is on or before retrieval. No other date is inferred.
3. **Part 2: MISO.** The 86 rows F40 excluded, from F40's pinned workbook, parsed with F40's reader by import. They
   use their own source record, `miso-mtep26-eval-midwest`, which cites the same artifact and hash, so F40's source
   and counts are untouched. IDs are `miso-mtep26-eval-midwest:<MTEP id>`.
4. **Locations follow C33's tiers with C38's operator guard** (`california.caiso.match`), matched against
   OpenStreetMap substations in the row's own states. Endpoints come from the upgrade name: two named facilities are
   a line, and one facility with site work (substation, terminal, transformer) is a site. A "toward X" clause names
   the far end of a terminal upgrade, not its site. Bus codes (`S3454`), taps and border points are not facilities.
   The bus columns are used only when the name gives no facility. Every point stays `unreviewed`.
   County-reference points are not used.
5. **Publication:** fixed release `data/midwest/releases/active.json`. F30's `load_snapshot` appends
   `("midwest", "midwest.publish")` after the Southwest under a separate `[FIX-F30]` claim.
6. **Deferred, not rejected:** Iowa Utilities Commission franchise dockets and ND PSC / SD PUC siting cases
   (JETx, Big Stone South–Hankinson–Bison). They need page-verified transcription; Iowa stays thin until then.

No point quota: reported counts are the counts found.

## Undo

Delete `data/midwest/releases/active.json` (the hook becomes a no-op) or `data/midwest/`.
