---
id: F33
name: Verified EIA directory and source reconciliation
lane: A
agent: data-researcher
phase: 6
depends_on: [F00]
owns: [pipeline/verified/, data/verified/, web/lib/verified/, web/app/api/verified/, tests/pipeline/test_f33_, tests/web/verified/]
cut: never
---

# F33 Verified reference directory

Implement C15's actual EIA-861 final archive import, evidence/lineage validation and strict read-only directory APIs. Use the reviewed 2024 archive and member hashes; 2025 early unvalidated data is not accepted. Join by vintage + EIA utility number only. Preserve utility/state/activity rows and distribution-equipment county semantics. Cross-check names/GEOIDs/state parent against Census while recording that this does not corroborate utility service membership. Ambiguous counties stay unresolved. No project-owner fuzzy match can become confirmed without independent evidence.

Add domain-owned versioned JSON schemas, deterministic output manifest, row-level provenance, duplicate/foreign-key/count validations and source-aware claim reconciliation. Same-lineage mirrors do not count twice; conflicting comparable claims go to quarantine and cannot feed operational/model results. Expose counts/status honestly. Raw downloads go to an ignored cache; commit only reviewed public normalized artifacts. No Mongo writer or edit to F30/legacy data.

Validate real-source replay, member hashes, exact denominators, county ambiguity, duplicate IDs, false lineage independence, conflicts/vintage mismatch, missing artifacts, strict API queries and bounded pagination. Run all repository checks and independent source review before marker/merge.
