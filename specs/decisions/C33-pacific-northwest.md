# C33: Pacific Northwest rollout with loose, labeled locations

## Authority

On 2026-09-27 the user instructed this Claude local session to work on the Pacific Northwest — Washington, Oregon,
Idaho and Montana — and said independent verification is too hard for a hackathon: "let's be more loose" for pins.
Claude local adopts the technical-lead contract role for this isolated spec only; no existing ownership changes.

## Decision

Assign [F42](../features/F42-pacific-northwest/spec.md) to claude-local: WA, OR, ID, MT. No point quota; counts
reported are the counts found. Independent review is not required for any tier below. Every tier stays
`location_review: "unreviewed"` and is never counted as verified or `confirmed`.

| Tier | Evidence | `center` | Label |
|---|---|---|---|
| Official | The project source itself supplies coordinates or a marker for the project | source point, `basis: source_point` | Official source; not independently reviewed |
| Candidate | C26: facility named in the project's source text; exact normalized name match to public facility geometry in the reported state; one corroboration (operator, voltage, or named county); one surviving facility | site, endpoint mean, or partial | Candidate; not independently reviewed |
| Candidate (unique name) | **Loosened by this decision:** same as above without corroboration, when exactly one facility in the reported state carries that normalized name | same | Candidate (name only); not independently reviewed |
| County reference | Source names the county (or a city the source names resolves to one county) | null | Approximate — county; exact site unknown |
| Unlocated | none of the above | null | searchable row with reason |

County references follow [C32](C32-texas-statewide.md)'s additive `approximate_location` field: `precision`,
`label`, `anchors` (county GEOID/name, lat/lon, method, source ID), `reference_source` and
`eligible_for_matching: false`. Anchors come from Census county internal points. Multi-county projects keep all
anchors under one ID. The exact `center` stays null.

Still forbidden: fuzzy or substring names, a same-name facility in another state, more than one surviving facility,
utility offices, state centroids, route vertices, model-guessed coordinates, invented dates or owners. Candidate and
county points never enter overlap, pair ranking or savings.

## Integration and undo

Publication follows the fixed-release pattern of C29/C26: F42 owns `data/pnw/releases/active.json` and
`pipeline/pnw/publish.py` (`apply_release`), pinning file hashes and expected counts and adding new IDs only.
F30's owner appends the call to the national build under a separate claim; a missing file changes nothing.
Undo by deleting the active release or `data/pnw/`; other producers' data is untouched.
