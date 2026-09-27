# Shared product vocabulary

Use these meanings in the UI, APIs, exports, reports and presentations. This documents the existing data rules;
it does not rename stored fields or authorize schema changes.

| Term | Meaning and limit |
|---|---|
| Project | An identified project within its source/owner namespace. Similar names alone do not establish identical projects. |
| Filing version | One source's statement about a project at a particular revision. Multiple versions can describe one project. |
| Current filing version | The version selected by the pipeline's documented rule. It is not proof that the project is under construction or that the source was recently updated. |
| Filed in-service milestone | The source's stated service date, preserving exact/month/year/unknown precision. It is not a construction window, contract completion, equipment availability, or notice to proceed. |
| Located endpoint | A candidate location with source identity, evidence and confidence. Pipeline acceptance does not mean independent confirmation. |
| Project center | The canonical endpoint arithmetic approximation defined in the mission. It is not a surveyed job site or route/corridor. |
| Geographic overlap / candidate pair | Different eligible utilities with evidenced centers strictly less than 25 miles apart under the canonical rule. It is a lead for investigation. |
| Effective review state | The current valid review result after source/fact bindings are checked. A producer's older state must not override a later valid rejection. |
| Confirmed review | Confirmation of the stated subject under the review criteria. It does not certify that two jobs can share crews, equipment or schedules, or guarantee savings. |
| Parsed coverage | Records extracted relative to the documented source denominator. It does not measure field accuracy. |
| Measured accuracy / agreement | Results of a named evaluation with sample, fields and denominator. A spot check does not establish corpus or model accuracy. |
| Imported coverage | Records actually ingested from identified sources, with statuses and missingness visible. A national basemap or source catalogue does not establish national project completeness. |
| Source publication / vintage | When the publisher issued the document or the period it describes. Keep unknown if unsupported. |
| Retrieval / check time | When our process obtained or checked a source. Successful retrieval does not establish that its contents changed. |
| Observed change | A difference between comparable source versions, with old/new evidence. The observation date is not automatically the real-world event date. |
| Live integration verified | A named deployed revision and active dataset/provider path were actually exercised, with dated evidence. A green offline test or configured account is insufficient. |

For [F38 expansion](features/F38-verified-geographic-data/spec.md), **verified project location** means a current
independent review establishes the exact project-to-location link and its stated precision. It does not prove the
project is currently under construction or that a canonical center is a surveyed job site. **Location unresolved**
means that evidence is missing, ambiguous, conflicting or not yet reviewed; include the specific reason and next
check. A rejected candidate does not mean the project itself is false. Existing `needs_review`/`rejected` fields
retain their current semantics; F38's richer reason/evidence fields require its additive implementation contract.

**Source-complete** describes all eligible records in named source artifacts, vintages and scopes having a reconciled
disposition. It is not statewide or nationwide real-world completeness. **Visible verified coverage** counts accepted
project locations actually served and accessible in the existing map, with active dataset and evidence references;
source catalogues, geometry vertices, duplicate observations and unconfirmed candidates do not increase that count.

Unknown fields remain unknown. Preserve differing source statements and their dates instead of forcing agreement.
See the [mission](mission.md), [C11](decisions/C11-national-follow-on.md) and [context index](context/README.md).
