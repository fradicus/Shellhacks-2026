# Mid-Atlantic release: 275 project records, 266 confirmed locations

Publication status: approved and validated locally; PR157 and the sole-writer load Action must complete before these are live.

## Counts

| State | New records | Confirmed locations | Unlocated |
|---|---:|---:|---:|
| New York | 5 | 3 | 2 |
| New Jersey | 105 | 101 | 4 |
| Pennsylvania | 94 | 94 | 0 |
| Delaware | 5 | 5 | 0 |
| Maryland | 66 | 63 | 3 |
| District of Columbia | 0 | 0 | 0 |

These are 275 native construction upgrade/case identities, with 266 reviewed locations occupying **65 distinct canonical map positions** and referencing **62 facilities**. Multiple separately documented upgrades can share a site. Location coverage is 255 standalone sites, three complete endpoint pairs and eight partial endpoints. Nine valid project records remain unlocated.

Lifecycle groups for all new records: {'in_service': 237, 'planned': 24, 'proposed': 6, 'under_construction': 3, 'unknown': 5}. Confirmed-location groups: {'planned': 19, 'proposed': 6, 'in_service': 237, 'under_construction': 1, 'unknown': 3}. Most records are historical upgrades; five New York cases retain unknown current construction status.

## Source coverage and review

PJM public XML: SHA-256 `5aa1fbc06e26e8f3a6c366d29302fb60fb3a1cbb66d9d239c4b26a4d4dce2a67`; 15,662 unique native rows acquired and independently reconciled. The first assignment screen found 5,749 eligible research rows, 80 explicitly withheld-location rows, 17 cross-assignment rows, 574 missing-state rows and 9,242 outside-assignment rows. The reviewed cohort admits 270 projects; other eligible rows remain deferred, not rejected as invalid. Publication is not complete PJM/state coverage.

Five NYPSC native cases use original public project-description PDFs plus docket identity pages. Each has a bounded-partial acquisition entry and null wider denominator. The September 2025 register web capture reconciles 44 rows but is not misrepresented as original PDF bytes or fresh construction status. Three gas cases and an unresolved native-ID conflict remain outside publication.

All 275 admitted native identities, all 15,667 release dispositions, all 270 × 31 raw PJM fields, all 768 typed events and every confirmed location were independently checked. No field sampling substituted for this census. The six original primary artifacts are pinned. Every source owner code, unknown date and actual-versus-planned service field remains visible. LIPA ownership and PSEG Long Island agency are separate.

The reviewer freshly extracted the original NOAA GDB and checked all 1,813 regional reference points. The implementation inverse matches independent pyproj values within 2.14e-14 degrees. NOAA 2017 historical coastal points retain original EPSG:3395 geometry, unknown numerical uncertainty and maximum intended scale 1:80,000. OMP2021 carries older observations in EPSG:3857. Shared HIFLD ancestry does not count as independent corroboration.

Independent reviewers corrected endpoint order and misleading NOAA city labels using original PJM filings, rejected same-name ambiguity, and added NYPSC Oakwood glossary evidence. Unsupported name-only matches and inferred alternate terminals never became centers. Authentication-required PJM geometry and restrictive PSEG MPRP map content were excluded.

Unlocated PJM identities: b3855.1, b3855.2, b4053.29, s3532.1, s3533.1, s3615.1 and s3272.1. Reasons are retained in the per-candidate decision ledger: ambiguous same-name/locality identities or multisite semantics. NY Clay and STAR East remain insufficient because a component terminal cannot be used to imply whole-project coverage.

## Integration and verification

C28 contract: PR159. F30 assembly hook: PR162. F38 implementation/data: PR157. The approved release hash, excluding only identity_review, is `4d62455a61f698eda04fce8bf25ec18cb4886a8030a3c7445f8b1c43f651871b`. Superseded approvals are retained in review-history.

Production schema, source/review hash binding, fixed activation, deterministic assembly, independent location and whole-release approval, duplicate identity checks and full national validation pass. Assembly changes the checked baseline from 1,286 to 1,561 projects and from 414 to 680 located. All prior project facts and coordinates, including the 345 New England confirmations, remain identical. No legacy ID, status, owner, date, match or existing source record was rewritten.

The source replay command is documented in data/expansion/mid-atlantic/README.md. Raw downloads stay outside Git. Source access details, original/rebound review receipts, current-versus-historical status mapping, state gaps and unknown denominators are in adjacent JSON files.

Repo-wide final checks are recorded in PR157. An initial test run had three temporary-directory errors from a full local disk; disposable outputs were removed and checks rerun. An initial sandboxed web build could not fetch existing Google Fonts; the network-enabled build passed. No product code or evidence was weakened for either environment issue.

After the merged load Action, verify every new Atlas/export record against the reviewed projection and preserve the active dataset ID and browser evidence in the live receipt. Until then, offline counts are not a claim of publication. F38 remains incomplete nationally; DC, inland coverage, prior comparable source vintages and unresolved projects remain gaps.
