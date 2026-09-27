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

## Part 2: MISO (2026-09-27)

**Reuse.** F40's MISO adapter reads rows inside `build()`, so there is no reader to import. F46 imports its file,
sheet, URL, status codes, state list and operator keys, and reads the rows itself. MISO's CDN served the workbook
to the pipeline's fetcher with F40's pinned hash (`40f325fe…`); nothing was bypassed.

**Operator keys.** F40's list has no entry for MidAmerican (18 rows), Citizens Electric (9), Montana-Dakota (5) or
Cedar Falls (1), so those rows would get neither corroboration nor the guard. `MISO_KEYS` adds them ahead of F40's
list; OSM tags Montana-Dakota as both "Montana-Dakota Utilities" and "MDU".

**Events.** F40's MISO records carry no events. F46 applies part 1's rule to "Expected ISD": a day-precision
`planned_milestone`, or an `in_service` event dated only on or before retrieval.

**Name forms added** (every SPP record re-verified byte-identical after each): a leading work verb ("Replace
Labadie"), ITC Midwest line numbers ("Forest City N43"), circuit suffixes ("Watson-1"), "Site: work" colons and
"161-69 kV". Reusing F40's `_facility_name` for this was rejected: it cut "Gavins Point" to "Gavins" (POINT is a
descriptor) and lost a correct SPP point.

**Result.** 86 rows, 18 located (15%). Most misses are real: new substations and load additions not yet in OSM,
blankets and programs. Known approximation: "New Greenbrier 345 kV Ring Bus on Denny - Zachary line" is a new site
on that line and is drawn as a partial point at Zachary.

**Spot check** (all 18 located): each matched substation's operator is the submitting utility; coordinates fall at
the named places. No errors beyond the Greenbrier approximation.
