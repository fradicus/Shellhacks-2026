# C34: California rollout, and the labeled candidate tier on Overlaps and History

## Authority

On 2026-09-27 the user told this Claude local session to look at California's pins and get about 100 History pins
and 100 Overlaps pins there. Claude local adopts the technical-lead contract role for this change only.

## Findings

- The assembled national snapshot had **0** California records.
- `/time` (Overlaps) and `/history` drew national records only when `location_review === "confirmed"`. No rollout since
  C25 had activated its Official/Candidate display tiers there, so the Texas, Great Lakes and any California candidates
  were visible only in `/explore`.
- The official California facility layer (CEC substations) now requires an ArcGIS token and its hub download is
  disabled; it is not used. Third-party re-uploads of it are not an official source. OSM (ODbL) is used, as in C26.

## Decision

1. **F43 (claude-local): California from CAISO.** The Transmission Development Forum workbooks list every
   CAISO-approved transmission project and interconnection network upgrade, with each forum's expected in-service
   date. Sources: approved projects July 2026 (current), July 2025 and January 2025 (only in-service projects the
   newer edition dropped), and network upgrades July 2025 (the newest public edition; removed, replaced and
   not-triggered rows excluded). Each forum's *changed* expected date is a `planned_milestone` event; an in-service
   status is an `in_service` event dated only when the workbook's current column still lists a date. Pre-2000 cells
   (e.g. 1933 for 2033) are source typos and stay unknown.
2. **Locations follow C33's loosened tiers** with one added guard: a same-name facility whose OSM operator is a
   different utility is rejected (`operator_conflict`), even when voltage corroborates. A spot check found PG&E
   Estrella/Camden/Mariposa/Santa Rosa and SDG&E Las Pulgas matching other utilities' same-name substations.
   Every located record stays `location_review: "unreviewed"`; none is counted as verified.
3. **Activate C25's labeled tier on `/time` and `/history`.** Both draw `confirmed` and `unreviewed` national points.
   Unreviewed points get their own marker colour, a legend entry, a selection label ("Candidate location, not
   independently reviewed"; official and name-only variants) and separate counts. They create no pairs, rings, ranks
   or savings: national points are never matched. This applies to every region's unreviewed points, not only
   California; a California-only rule would be arbitrary.
4. **Map cap 2,000 → 3,000** (`MAX_MAP_POINTS`, F31). With California the located national total is 2,125; at 2,000
   the id-sorted cut would silently drop about 125 New York points.
5. The fixed-release hook: `("california", "california.publish")` after Great Lakes in `load_snapshot` (F30), as in
   [F30-great-lakes-hook](F30-great-lakes-hook.md).

## Result (from the committed release)

360 projects, 146 located (139 corroborated candidates, 7 name-only), 0 verified. All 146 carry dated events, so
History draws 146; 109 are not in service (107 excluding 2 cancelled), so Overlaps draws 109.

## Undo

Delete `data/california/releases/active.json` (the hook becomes a no-op). Revert the `DRAWN` set in
`web/components/time/nationalProjects.ts` to `confirmed` only to hide every candidate tier again.
