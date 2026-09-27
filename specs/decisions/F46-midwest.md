# F46 decisions

## Part 1: SPP (2026-09-27)

**Count correction.** C43 reported 481 in-scope SPP rows in 128 projects. That count kept only rows with an NTC ID.
The record unit is the upgrade (`UID`), and 107 in-scope upgrades have no NTC ID yet (in service, identified or on
schedule). They are real rows and are kept: 587 accepted upgrades in 193 SPP projects. All 1,422 workbook rows carry a
disposition (835 excluded, by state).

**Operator guard.** C38's guard rejected 44 endpoints. The operator keys are spelled as OSM tags them (spot-checked);
the named substation is tagged with another utility. In the Dakotas and Nebraska, one utility's terminal work often
sits at a substation another utility operates (MRES at WAPA's Watertown, OPPD at NPPD's Tekamah), so some of these are
likely true sites. The guard stays as C38/C43 specify; relaxing it would need a contract change.

**Known gaps.** F40's parser strips a leading `S1234` as a queue ID, so "Raun - S3452 345 kV New Line" stays
unlocated instead of a partial point at Raun (3 rows). Names with "&" ("53rd & Mund") are treated as lists by F40's
parser (6 rows). Iowa has 7 SPP rows and none located; Iowa is MISO territory (part 2).

**Spot check** (10 random located records, seed 46): all 10 match the upgrade's named facility in its state, with an
operator consistent with the SPP owner; coordinates fall at the named towns. No errors found.
