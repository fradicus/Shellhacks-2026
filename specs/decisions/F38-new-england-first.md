# F38: Start with the existing New England corpus

## Authority and scope

The user asked this session to start F38 on the New England data and target roughly 250–500 verified points.
This supersedes C22/F38's Florida-first ordering for this checkpoint; it does not waive source, identity,
location, independent-review or publication gates. No other feature ownership changes.

## Baseline and choice

At origin/main `84de54ee2209507f1816124a13b80dc18fb8516f`, F30 contains 1,024 ISO-NE June 2026 RSP rows:
46 planned/proposed/under construction, 643 in service and 335 cancelled. None has a located center.
These are committed-snapshot counts, not a fresh Atlas query or a claim of current construction.

Use a deterministic 300-project research cohort: all 46 nonhistorical-status records, then in-service
records ordered by descending native project ID until 300. This is a reproducible research priority,
not a chronology or a completeness claim. Keep cancelled and remaining in-service rows in the disposition ledger.
Historical records remain explicitly historical; multiple component projects can share one physical site.
If the 300-point target requires new sources, assess the Asset Condition List separately before importing it.
Do not increase counts with utility offices, towns, inventory-only substations or unsupported geocodes.

Replay the pinned public workbook through the existing F30 parser, compare every imported record, and produce
F38-owned research JSON and a readable bullet list with row-level citations. This is source verification,
not location confirmation. Research outputs have null coordinates and cannot activate in the loader.
An independent reviewer checks the original workbook and cohort without relying on the producer parser.
Subsequent acquisition should focus on regulator/utility project documents and official facility GIS that
can establish explicit identity and actual site/endpoints. Location proposals still require individual review.

## Prerequisites and undo

The additive loader/API/map contract remains pending and must land before production implementation.
Existing Florida pilot validation becomes a New England pilot for the authorized cohort; no pilot is passed
by this checkpoint. Broader stages remain deferred. No completion marker until geographic publication acceptance.
Undo by removing this research cohort; F30 records and production behavior are untouched.
