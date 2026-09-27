# F46: MISO MTEP25 Appendix A rows for the Midwest states

**Context.** C43 left Iowa thin (40 projects, 8 points) pending state dockets. On 2026-09-27 the user asked this
session to keep filling sparse areas. MISO's MTEP25 Appendix A workbook
(`cdn.misoenergy.org/MTEP25 Appendix A - New Local Reliability Projects720399.xlsx`, public, no login) is already
pinned by F39 (`southeast.misospp`), which reads it only for LA, AR, MS and KY.

**Choice.** A third F46 source, `miso-mtep25-appendix-a-midwest`: App. A and App. B rows whose states are all among
IA, MO, ND and SD and whose MTEP ID neither F46's MTEP26 list, F40 nor F39 publishes. F39's workbook helpers are
imported, not copied. A row is placed from the Facility sheet's From/To substations when they name one site or one
line (F39's rule), else from its title with F46's parser; C33 tiers and C38's operator guard are unchanged. Result:
81 projects, 29 located; the 673 earlier records are unchanged (0 moved, re-built from fresh OSM extracts).

**Known limit.** A new substation whose facility rows name only its existing neighbour is placed at that neighbour
(e.g. "New 345 kV Lumberjack substation" at Montgomery); it stays an unreviewed candidate.

**Undo.** Drop the Appendix A block from `midwest.build` and rebuild.
