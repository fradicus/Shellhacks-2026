# F46: MISO LRTP Tranche 2.1 facilities

**Context.** Iowa remained the emptiest Midwest state (15 points). MISO's public "LRTP TR2.1 Eligible Projects"
workbook (`cdn.misoenergy.org/20250306 LRTP TR2.1 Eligible Projects671260.xlsx`, no login) lists each Tranche 2.1
facility with MTEP project and facility IDs, member-system owners, state and scope. No rollout publishes it.

**Choice.** One record per facility in IA, MO, ND or SD (`miso-lrtp-tr21-midwest:<MTEP Facility ID>`), located
with F46's name parser under C33/C38 (member-system codes mapped to OSM operator fragments). The workbook states no
status or in-service date, so the status is "LRTP Tranche 2.1 eligible project (no status stated)", group unknown,
with no events. "To Be Determined" owners are recorded as none. Result: 72 facilities, 35 located; earlier records
unchanged.

**Known limit.** New substations named with an existing place in parentheses ("Marshalltown (Twinkle)") match the
existing substation of that name, an approximate candidate.

**Undo.** Drop the LRTP block from `midwest.build` and rebuild.
