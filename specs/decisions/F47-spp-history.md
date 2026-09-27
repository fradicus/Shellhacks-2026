# F47: Completed upgrades from older SPP tracking editions

**Context.** The user asked for sparse areas to be filled with present and past projects. SPP drops an upgrade from
its Quarterly Project Tracking workbook some time after completion, so the 2026 Q3 edition misses most finished work
in OK, NM and TX. F39 already pins the Q4 2017–2025 editions (public, no login).

**Choice.** For each UID in F47's states absent from 2026 Q3 and not published by F46 or F39, read the newest older
edition that lists it; keep it only if that edition calls it complete, closed out or in service. Its status reads
"<status> (last listed in <edition>)" and its in-service event follows C43's dating rule. Upgrades dropped while
planned or delayed are excluded: no edition records their outcome. One source per edition
(`spp-qpt-<edition>-south`). Locations use F47's rules unchanged. Result: +299 projects, +147 points.

**Known limit.** C33's loose tier places some one-endpoint lines on a same-named substation elsewhere in the state
(2 of 10 in the spot check, e.g. "Stonewall - Wapanucka" at an Oklahoma City "Stonewall"). The same rule governs the
2026 Q3 records; tightening it is a policy change for C33, not this fix.

**Undo.** Drop `history` from `sppsouth.build` and rebuild.
