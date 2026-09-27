# C26: Great Lakes rollout with a labeled candidate-location tier

## Authority

On 2026-09-26 the user instructed this Claude local session to fill the map state by state across the Great Lakes,
starting with Minnesota, targeting roughly 5,000 points, following the F38 source rules. Asked directly whether the
F38 independent-review bar or the point target should win, the user chose to **add a labeled candidate tier**.
Claude local adopts the technical-lead contract role for this isolated spec only; no existing ownership changes.

## Findings that forced the choice

- The national corpus has no MISO or PJM projects; no Great Lakes project can use C23, which updates existing IDs only.
- Minnesota withdrew its statewide transmission/substation GIS in July 2022 as inaccurate. The 2025 Minnesota Biennial
  Transmission Projects Report is public and names ~239 tracking IDs, with facility names but no coordinates.
- MISO's site and CDN return HTTP 403 to scripted requests. The user chose to skip MISO rather than hand-download it.
- The first F38 hour confirmed zero locations. At that bar, ~5,000 points is not reachable in this rollout.

## Decision

Assign [F40](../features/F40-great-lakes/spec.md) to claude-local: MN, WI, MI, IL, IN, OH, PA, NY in that order.
The 5,000 figure is a target, not a quota; the counts reported are the counts found.

A **candidate location** reuses the existing national `location_review: "unreviewed"` state, which `/explore` already
labels. It is published only when all of these hold, and is never counted as a verified location:

1. The project comes from a reviewed public register row with a source locator (page/row/section).
2. The facility is named explicitly in that project's source text as its site or a line endpoint.
3. The geometry comes from a public facility dataset with recorded attribution (OSM under ODbL, or official GIS),
   in the project's reported state.
4. The normalized facility name equals the source name exactly (no substring or fuzzy match), and at least one
   corroboration holds: the facility operator matches a project utility, its voltage includes a voltage the project
   names, or it lies in a county the source names. Ambiguous matches (more than one surviving facility) stay unlocated.
5. The center follows the mission rule: two endpoints give the mean (`basis: two`), one endpoint is partial
   (`basis: one`), a site is `source_point`. `center.evidence` begins `Unverified candidate:` and names the facility
   ID, dataset and matched fields. The full match rationale stays in an additive `location_candidate` field.

Utility offices, towns, county/state centroids and route vertices still cannot be candidates. Reports keep
verified, candidate and unlocated counts separate. A later independent review can promote a candidate to `confirmed`
under F38/C23; a rejection returns it to unlocated with the reason retained.

## Integration and undo

Publication follows the fixed-release pattern of [C29](C29-texas-candidate-publication.md) under the
[C25](C25-main-demo-map.md) display tiers, which already name this rule as its candidate tier. F40 owns
`data/greatlakes/releases/active.json` and `pipeline/greatlakes/publish.py` (`apply_release`); the release pins the
exact `data/greatlakes/projects.json` hash, per-source hashes and expected counts, and adds new IDs only. F30's owner
appends that call to the national build under a separate claim; a missing or invalid file changes nothing. A
transmission owner's own published project-map coordinate (e.g. AEP) is C25's Official tier, not a candidate.
Undo by deleting the active release or `data/greatlakes/`; verified data is untouched.
