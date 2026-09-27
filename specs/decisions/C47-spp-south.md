# C47: SPP South rollout (Oklahoma, eastern New Mexico, non-ERCOT Texas)

## Authority

On 2026-09-27 the user told this Claude local session to find sparse areas of the map and fill them with sourced data
as a continuous goal, naming Oklahoma first ("I don't see anything in Oklahoma"). Claude local adopts the
technical-lead contract role for this change only; no existing ownership changes.

## Findings (origin/main `ac0b4ee`)

- Oklahoma has 4 national records, all multi-state AR/KS/OK SPP rows from F39's dense release.
- SPP's public **Q3 2026 Quarterly Project Tracking Report** appendix (the artifact F46 pins, sha256 identical, no
  login) has 1,422 upgrade rows. Rows listing only OK: 327 (OGE 178, AEP 75, WFEC 38, GRDA 16, other 20). Only NM:
  126 (SPS 122). Only TX: 269 (ETEC 147, SPS 78, AEP 39, other 5).
- No rollout publishes these rows. F46 kept IA/MO/KS/NE/ND/SD; F39 kept rows listing AR or LA. F45's New Mexico
  records come from WestConnect (EPE, PNM, Tri-State) and name no SPS project. F41's Texas release is ERCOT's TPIT
  only; SPP's Texas rows (panhandle, South Plains, East Texas) are outside ERCOT and are different projects.

## Decision

1. **F47 (claude-local)** takes every SPP Q3 2026 row whose listed states are all among OK, NM and TX. Any other row,
   and any UID another rollout already publishes, is excluded with the reason.
2. Records follow C43 part 1 exactly (status groups, owner-indicated in-service date, in-service dating rule), reusing
   F46's parser by import. Source `spp-qpt-2026q3-south` cites the same artifact and hash as F46's
   `spp-qpt-2026q3`, so F46's source and counts are untouched. IDs are `spp-qpt-2026q3-south:<UID>`.
3. **Locations follow C33's tiers with C38's operator guard**, matched against OpenStreetMap substations in the
   row's own states, as C43 item 4. Every point stays `unreviewed`; no county-reference points.
4. **Publication:** fixed release `data/sppsouth/releases/active.json`. F30's `load_snapshot` appends
   `("sppsouth", "sppsouth.publish")` after the Midwest under a separate `[FIX-F30]` claim.
5. F41 keeps Texas's ERCOT scope; F47 does not edit F41's artifacts or release.

No point quota: reported counts are the counts found.

## Undo

Delete `data/sppsouth/releases/active.json` (the hook becomes a no-op) or `data/sppsouth/`.
