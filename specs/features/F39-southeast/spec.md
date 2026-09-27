---
id: F39
name: Verified Southeast project coverage
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/southeast/, data/southeast/, reports/southeast/, tests/pipeline/test_f39_]
cut: never
---

# F39: Southeast geographic delivery

## Authority and scope

The user's instruction is to continue until the entire Southeast is done. This feature owns FL, GA, AL, MS,
SC, NC, TN, KY, VA, WV, AR and LA delivery, separate from the existing F38 New England worker. Do not edit F38
artifacts or its active release. Nationwide expansion outside these states remains with its existing specification.

The evidence, location, history, source-safety and visible-publication requirements in
[F38](../F38-verified-geographic-data/spec.md) apply in full to this geographic scope. That reference does not
transfer F38 ownership, its New England cohort, or its bounded-run deadline. This user requested no deadline or
budget: checkpoint and resume until the full Southeast acceptance criteria hold. Root STOP and main-red gates apply.

## Plan

1. Record source/provider coverage for every state, including investor-owned, municipal, cooperative and federal
   transmission planning where relevant. Name exact sources, scope, vintages, accessible archives, access restrictions
   and missing providers. A list of discovered links is not an acquired dataset or statewide completion.
2. Complete one Florida source batch with an independently verified project-location link, then publish and verify
   it through the existing Action, Atlas RO read and existing maps. Continue independent source research during this
   pilot, but do not scale an unproven location method.
3. Process the reviewed Florida source universe, repair/expand Georgia with canonical legacy IDs preserved, then
   reconcile remaining Southeast source/provider matrices. Ingest cross-state sources once and count projects once
   nationally. State totals may overlap and must say so.
4. Use sequential source/state/shard PRs with bounded acquisition, deterministic replay, exact row dispositions,
   field evidence, source-time precision, source-bound reviews and actual activation counts. Aim for reviewable
   checkpoints every 30–60 minutes; readiness decides when a PR ships.
5. Keep historical observations and events separate from current status. Prior accessible comparable vintages must
   be assessed. Permitting is not completion; old planned dates do not establish in-service status.

## Requirements

- Project identity must describe a construction or upgrade effort. Asset inventories, towers, generation queues and
  utility service areas cannot become project dots by relabeling them.
- Unknown coordinates/dates/owners/costs/contractors remain null. Source-backed unlocated rows remain searchable.
- New centers require independently reviewed exact project-to-location evidence, original CRS/geometry, precision,
  transformation method, source hash/locator and a current facts hash. Reviewer and producer must differ.
- Lines use the arithmetic mean of two supported endpoints or the sole supported endpoint, labeled partial. Sites
  use an authoritative site location. Route vertices, centroids and service-area centers are not endpoint evidence.
- Retain append-only rejected/stale/conflicting reviews and exact reasons. Numerical tests and model agreement do
  not replace source inspection. Review each promoted location; independently sample other fields across each source,
  parser/status/date variant. Quarantine systematic errors and inspect the affected full batch.
- Reuse national IDs for existing projects and preserve original observations. Explicit evidence establishes aliases,
  parent/component relationships and cross-source duplicates. Same-name projects are not automatically duplicates.
- Preserve Georgia D2 table-only and SERTP D15 exclusion. Review source content and access/rights before acquisition;
  public-looking filenames do not override restrictions. Raw downloads stay outside the checkout.
- Only approved fixed-path releases may activate, using accepted shared schemas and the sole existing Atlas load
  Action. No folder discovery, direct MongoDB write, additional service or new database writer.
- C23 currently covers location updates to existing national IDs. New Southeast project/source insertion requires an
  additive reviewed contract before activation. Do not disguise new projects as existing IDs or edit F38's release.
  F30/F31/F19 owners implement their respective loader, evidence/API and existing-map hooks under separate claims.
- Emit coverage and review ledgers under data/southeast/ and reports/southeast/. Candidate artifacts are explicitly
  non-publishable. The integrator alone writes the accepted release. Independent reviewers may operate in disjoint
  sessions, reading source evidence and recording decisions without modifying producer facts or release activation.

## Validation and acceptance

Run all tech-stack checks and the F38 validation cases relevant to this scope. In addition:

- Every eligible row of every approved source has accepted/duplicate/excluded/rejected disposition and reason.
  Every named provider/planning-process source is processed or has an evidenced access/scope gap. Do not quietly
  drop inaccessible or difficult sources from the denominator to claim completion.
- Report per-state/source/provider project totals, current/historical/unknown status, source freshness, confirmed
  locations, complete/partial endpoints, distinct physical sites, unknown geometry and rejected reasons.
- Every accepted field has a source locator or explicit null. Source publication, retrieval and observed-change
  timestamps remain distinct. Acquisition/pagination/truncation and parser drift fail closed.
- Test stale/self/rejected reviews, wrong CRS and axes, conflicting identity, duplicates, repeated releases,
  unchanged legacy facts/matching, failed activation and rollback. Tests use explicit fixtures, never synthetic
  records labeled as real public projects.
- Confirm each release's dataset/IDs/counts through Atlas RO after the Action. Verify at least one newly covered
  point in each state on the existing maps, with matching source/review evidence and accurate lifecycle filters.
  Verify unlocated records remain accessible. A database row count alone does not prove geographic delivery.
- The Florida pilot, all twelve state source ledgers, accepted release activation, existing-map visibility and
  remaining evidence gaps must be audited before changes/F39.md is written. Research-only checkpoints never write
  that marker. Unresolved geographic or source-coverage requirements mean the objective remains incomplete.

## Defaults

Use the existing Python stack and national projection. Transmission and associated substations only; current work
first, documented history retained. Frontend redesign is deferred; required existing-map integration is included.
No density quota, guessed geometry, private data, paid subscription or new credential is required. Report actual
source-bounded completeness; the unknown denominator of all real-world projects must never become an invented total.
