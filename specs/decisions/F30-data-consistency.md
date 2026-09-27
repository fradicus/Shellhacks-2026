# F30 national data consistency

The user assigned this worker state-filter repair, reconciliation of legacy/national location differences, shared coverage counts, and live verification. Work starts from main 5effc22.

The first trace shows that ten locations absent from the national projection have rejected endpoint reviews. Preserve those rejections; matching display totals cannot justify reintroducing rejected coordinates. Any legacy renderer/loader change stays with its feature owner.

Repair supported state assignments with explicit provenance, retain unknowns, and measure location tiers without silently changing review status. Reuse existing contracts and load Action. Coordinate with the existing location-precision and time-view work; no competing color scheme or marker contract is introduced.

## Implemented choice and reversal

Reuse `locations.boundaries.StateBoundaries` and its pinned Census cache. Derive states from eligible
individual endpoints, retaining candidate review status. This yields 55 Georgia and 14 South Carolina
records with state membership; no coordinate or review status changes. Ten rejected projects retain null
centers and unknown states. The exact endpoint decisions are preserved in raw evidence for consumers.
The alternative of utility-based assignment would assert unsupported project geography and is rejected.

Add a base-only `national rebuild-legacy` command and measured optional coverage counts. Existing schemas
permit the evidence and coverage additions; no contract or dependency changes are needed. Removing this
projection enrichment and rebuilding the base reverses the change. No national overlap pairs are introduced.

The read-only baseline advanced to dataset 5effc228a094d2ac383a49d9af82feaa2d355160 during the audit:
3,622 records and 1,316 centers after statewide Texas activation. Preserve that release and its county
references. Local assembled counts are recorded in `data/national/consistency-audit.json`; those are distinct
from a future successful load receipt. The ten-center renderer discrepancy was reported to F19 in PR 184.
