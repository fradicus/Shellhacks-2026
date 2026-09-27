# C31: Publish useful project locations at their supported precision

## Authority and precedence

The user explicitly requested this shared spec amendment on 2026-09-27: agents are being too strict for the hackathon; county-level locations are acceptable when the data says so. This is the governing location-publication policy for all geographic producers, including F38, F39, F40 and F41, and their F30/F31/F19 consumers.

This supersedes conflicting mandatory independent identity/location review, exact-location-only publication, centroid-display bans and geographic acceptance wording in C22, C23, C25, C27, C28, C29 and associated feature specs. Existing independent reviews remain valid evidence. Feature ownership, source-access restrictions and the sole Atlas load Action remain in force. Earlier strict requirements must not be used to block records meeting this policy.

## Delivery rule

Publish documented transmission construction/upgrade projects in small useful batches at the best supported precision. Do not wait for complete provider coverage, a previous-year comparison, or independent review of every record before publishing a valid current batch. Retain coverage gaps and improve records incrementally. A source-backed county location is a successful approximate geographic delivery, with refinement tracked separately.

| Location | Minimum evidence | Display |
|---|---|---|
| Official site or endpoint | Project source supplies coordinates or explicitly links an official facility/GIS feature | Official source; site or endpoint precision |
| Candidate facility | Named project facility has a unique public geometry match using normalized name and supporting owner, voltage or county | Candidate; not independently reviewed |
| County / municipality / documented area | Project source explicitly names the area; resolve its administrative ID against public reference geography | Approximate — county/municipality/area; exact site unknown |
| State only | Source identifies only a state | State summary or boundary; no project point |
| Unknown | No defensible geographic link | Searchable record with unknown location |

Independent review is optional for routine source extraction, identities and official/candidate/area locations. Use producer validation and source citations as the publication gate. Seek additional review for unresolved conflicts or prominent precise claims; a conflict at facility precision may fall back to an unambiguous sourced county. Never fabricate a reviewer or upgrade an unreviewed record to independently confirmed.

## County markers are permitted

County boundaries are preferred when readily available. A sourced administrative representative point (or a reproducibly derived point-on-surface of its public boundary) may serve as an approximate display marker. This is explicitly allowed even though it is not the project site. Save the reference source, administrative identifier, method and source geometry reference. Do not invent an offset or jitter coincident records to suggest separate sites.

Keep the actual project center null when only an area is known. Store the approximate display anchor separately. Do not put a county anchor into an endpoint, site coordinate, or canonical project center. Existing exact line centers continue to use the endpoint mean rule. Multi-county projects keep all documented counties and render an area or linked approximate anchors under one project ID; they count as one project nationally. Never silently choose the first county as the project's precise location.

## Required data semantics

The additive shared schema and API must carry these semantics using a single agreed representation:

- Location precision: site, endpoint, county, municipality, area, state, or unknown.
- Evidence basis: official, candidate match, or source-reported area.
- Independent review state as a separate field; absent review means not reviewed.
- Source URL, document/page/row locator, retrieval time and raw location wording.
- Administrative names and stable IDs, with explicit nulls when unresolved.
- Exact project geometry/center separately from optional approximate display geometry/anchor.
- Display method and reference-geography provenance for every derived area anchor.

For example, a project reported only in Leon County stores county precision and its source citation, null exact center, and an optional separately attributed county display anchor. Selection and export say “Approximate — Leon County; exact site unknown.” County precision is categorical; do not manufacture meter-level uncertainty or confidence percentages.

## Map, search and export acceptance

Default maps include official, candidate and approximate locations. Approximate markers must differ visibly in shape/style and say “Approximate — county” in the legend and selection. Search, API, download and detail views preserve the same precision and source evidence. Several projects sharing a county anchor remain individually accessible through a list or cluster.

Counts distinguish unique projects, official/candidate facility locations, approximate area locations and unlocated records. Reviewed status is an additional badge, not an extra project count. County markers are not distinct physical sites. Report improved geographic coverage without claiming exact-site verification or exhaustive statewide coverage.

Candidate and approximate anchors do not enter distance-based overlap, routing, pair ranking or savings calculations. This policy does not authorize new national pair calculations. Legacy golden matching remains unchanged. Unknown dates, status, ownership and costs remain unknown; a past planned date is not completion. A project still needs evidence of construction/upgrade work; asset inventories alone do not qualify.

## Implementation sequence and ownership

1. Contract owner adds compatible schema fields for these semantics, preserving existing records and review history. Producers can immediately collect county-qualified records in their own batches.
2. F30 and producer owners remove mandatory second-review gates for the allowed tiers and validate provenance, unique IDs, coordinate/CRS sanity, area resolution and duplicate/conflict handling. Known ambiguous facility matches fall back to their supported area or unknown.
3. F31 exposes precision, separate display geometry and evidence consistently in API/search/export. F19 renders these tiers in the existing map. Owners retain their paths; no renderer fork or new database writer.
4. Activate a Florida batch through the existing Action and verify a county-only project end to end: source -> stored precision -> RO API/export -> visibly approximate marker. Confirm its exact center stays null and it is excluded from matching.
5. Apply the same policy to each regional batch. Independent audits and precise-location improvements can follow publication without withholding the already useful records.

Until additive consumers support a tier, keep its records in the producer batch and deliver the missing compatibility work as the next task. Do not relabel an approximate anchor as confirmed to bypass a validator, and do not treat outdated validator restrictions as a reason to abandon this policy.

## Validation

Run repository checks for each implementation PR. Verify a county-only record can publish without an independent reviewer, reference geometry resolves to its stated county, exact center remains null, exports preserve precision, and the map visibly labels approximation. Verify duplicate county anchors do not inflate project/site counts, multi-county IDs count once, ambiguous areas remain unresolved, unsupported exact coordinates fail, and previous exact projects and golden pairs remain unchanged.

This specification does not claim schema implementation, new Atlas records or newly rendered points. Completion of the change requires the real Florida journey above, followed by the same contract in all active geographic producers.
