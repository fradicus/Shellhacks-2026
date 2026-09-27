# Mid-Atlantic public construction records

The C28 release covers a selected cohort in NY, NJ, PA, DE, MD and DC. The only activation file is
`releases/active.json`. Research manifests and candidate files cannot publish points. Existing New England and
Southeast releases remain separate inputs to the national assembly.

## Evidence and limits

PJM's public XML export supplies native upgrade/component IDs and all original fields. The release reconciles
all 15,662 acquired rows while admitting only the reviewed cohort. This is complete acquisition of that pinned
export, not complete project coverage in each state. Distinct upgrades can share a facility or parent program.
Unknown owner names remain the original PJM owner codes. Actual, projected, revised, required and ISA service
dates remain distinct, including when source status and date fields appear inconsistent.

New York uses original public NYPSC case documents and docket identities. The September 2025 statewide register
was available only as a web text capture, so its 44 rows are research evidence only. Current construction status
and service dates for the five admitted New York cases remain unknown. LIPA ownership is separate from PSEG Long
Island's role as agent.

Historical NOAA/BOEM facility points have 2017 source vintage and a maximum intended scale of 1:80,000. The
MassCZM OMP2021 reference has older underlying observations. Numerical positional uncertainty is unknown.
Neither reference establishes construction, current asset conditions, route geometry or complete state coverage.
They may share HIFLD ancestry and are not independent corroboration of one another. Independent project-to-asset
review, including identity conflicts and whole-project versus component scope, is required for every point.

A single known endpoint is partial coverage. Two endpoints produce an arithmetic center. A standalone site is
one facility position. None represents a surveyed construction footprint. Rejected, insufficient or stale review
leaves the center null. Review history is retained when project facts change.

## Reproduce

Acquire the exact publicly offered XML export at the source URL in `active.json`; its SHA-256 must match. From
`pipeline`, run:

```sh
uv run python -m expansion.pjm_mid_atlantic --source /path/to/projectCostUpgrades.xml
uv run python -m national.load --help
```

The first command compares every admitted PJM project's normalized fields and typed events and reconciles every
source row. It performs no network or database writes. The national assembly validates all previous producers,
then C28, before any staging. The existing GitHub load Action is the sole database writer; local verification uses
read-only API/export access. Missing active.json is a no-op; any invalid review or cross-reference fails closed.

Original downloads stay outside Git. The release carries exact source URLs, original artifact hashes, locators,
original CRS and point coordinates, retrieval times and independent approvals. Audit reports under
`reports/expansion/mid-atlantic/` retain enumeration, source limitations and independent checks. Acquisition time
never substitutes for publication or construction time. The EPSG:3395 ellipsoidal inverse and EPSG:3857 spherical
inverse are checked separately; all 1,813 acquired NOAA regional points were independently recomputed.
