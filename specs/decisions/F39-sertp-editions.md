# F39: which SERTP editions may be ingested

## Authority

F39 owns Southeast delivery and must "preserve … SERTP D15 exclusion" and review source content before acquisition.
[D15](000-overnight-defaults.md) excludes the 2026 SERTP preliminary expansion report because its text carries CEII
headings. This records the content check for the other editions on the public
[SERTP archive](https://www.southeasternrtp.com/archive.cshtml), as used by the C40 dense batch `sertp`.

## Check

`pdftotext -layout`, then every line naming "CEII". A line is a **marking** when it has no lower-case prose (a page
heading such as `TRANSMISSION PROJECTS (CEII)`) or ends with `(CEII)`. Any marking excludes the edition; disclaimer
sentences ("…does not include Critical Energy Infrastructure Information (CEII) materials") do not.
`southeast.sertp.build` repeats the check on every ingested file and refuses to build on a marking.

| Edition (file) | sha256 | CEII lines | Markings | Verdict |
|---|---|---:|---:|---|
| 2025 Preliminary Expansion Plan Report (Non-CEII) | `462f9f3dee796a9c010d31581eca3402f8b93be625af68cc73b2bdba81bed0ae` | 0 | 0 | **pass — current edition** |
| 2025 Regional Transmission Plan and Input Assumptions (final) | `9183e3ffcb4fc06e46db2afc50510948b6c0f950312440b6272aaa862bc9da6b` | 319 | 194 | **fail** — `TRANSMISSION PROJECTS (CEII)` page headings; not used |
| 2024 Regional Transmission Plan and Input Assumptions (final) | `fa960646893d376d93fe1c75d9f4ff242618f4f5dd0da5c539581209a6f56236` | 5 | 0 | pass — history |
| 2024 Preliminary Expansion Plan Report (Non-CEII) | `4ea25c3db5dba8859f66a94cf81ed852e16bd01a74b45a0ce81c8ff94919276a` | 0 | 0 | pass — history |
| 2023 Regional Transmission Plan and Input Assumptions (final) | `32350b2b7dc953b71174d7491487dd47036d0824a414aa7f5da699ca20adfd02` | 5 | 0 | pass — history |
| 2022 Regional Transmission Plan and Input Assumptions (Final, Non-CEII) | `bf4fbdfbb9d8f98143aab1882c8c6c7cf24873c9db62940bcf06c64564bcd80f` | 5 | 0 | pass — not used (different page layout) |
| 2021 Regional Transmission Plan and Input Assumptions (Non-CEII) | `679d4f16333ebfbc3d4563edb4b3a4730c41c5aeec5d333687c19c6a7611af85` | 5 | 0 | pass — not used (older than the linked history) |
| 2026 Preliminary Expansion Plan Report | not downloaded | — | — | **excluded by D15** |

Retrieved 2026-09-27. The 2025 final was downloaded only to run this check; nothing from it is ingested.

## Decision

1. The 2025 preliminary report (Non-CEII) is the current SERTP edition for F39. D15's 2026 exclusion stands
   unchanged; it is revisited only after the sponsor clarifies.
2. The 2023 final, 2024 preliminary and 2024 final add history only: a `planned_milestone` event (year precision)
   where a row's In-Service Year differs from the previous edition's, linked to a current project only by the same
   Balancing Authority Area and the same name up to punctuation (or the current name without its trailing
   ", ACTION" phrase), one-to-one and unique in both editions.
3. The 2025 report renamed most projects (only 35/50/78 of 244/301/364 older rows link). A row that no longer
   appears cannot be told apart from a rename, and dropping out never establishes completion, so older unlinked rows
   are excluded with that reason rather than kept as projects of unknown status.

## Undo

Delete `data/southeast/dense/sertp/` and its entry in `data/southeast/dense/releases/active.json`.
