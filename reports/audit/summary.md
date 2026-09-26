# Independent data audit

The top 15 ranked pairs and their 14 supporting endpoint records receive **29 confidence downgrades and zero confirmations**. Source dates and independently recomputed geometry agree. County/project-area correspondence does not yet establish that these cached OSM features are the intended filing locations; a downgrade is not proof of a wrong coordinate.

Evidence was selected against canonical F10 data at `de43141fa00de6d906f3d4b1e5fd9303600a3632` and bound to current facts at `5fb62b98c0ce06245ff090f0535c3726e8778388` on 2026-09-26T14:22:53.856128+00:00. Canonical JSON input hashes, source byte hashes, observed fields and all verdict bindings are in [evidence.json](evidence.json) and [audit.json](../../data/review/audit/audit.json).

| Check | Observed |
|---|---|
| Full pair set, unique IDs and independent distance/gap/band/rank | 21/21 checks pass across all 19 pairs |
| Selected scope | 15 historical pairs, 10 distinct projects |
| Supporting locations | 14 endpoint records, 9 distinct OSM features |
| Cached raw coordinates and independent state checks | 14/14 agree; all are medium-confidence bounding-box centers |
| Supporting operator tags | 13 present and consistent; Jasper absent |
| Independently established county/project-area identity | 0/14 |
| Source cards / table rows | 2 DESC cards and 8 Georgia rows checked |
| Effective loader review state after this audit | 15 rejected, 4 needs review, 0 confirmed |

The source review read public DESC cards on pages 8 and 18 and independently recovered the eight Georgia rows by native-ID anchored columns on pages 178, 180, 183, 184 and 186. Georgia evidence is limited to permitted table fields under D2; no page images or broad excerpts are published or sent to Gemini. Cached OSM features and their SHA-verified raw records were inspected, without a live OSM page fetch. The source cards do not establish county identity.

The independent oracle uses its own arithmetic means, atan2 haversine and date arithmetic, without production matching or parser imports. The safe loader helper is reused only for subject projection/hash. Each decision includes its current subject snapshot and `audit-subject-v1` fingerprint. Changes to reviewed source, filing or endpoint facts invalidate the decision. Loader corrections for issues [66](https://github.com/fradicus/Shellhacks-2026/issues/66) and [43](https://github.com/fradicus/Shellhacks-2026/issues/43) were required before binding this audit.

The twelve-card extraction check is documented separately in [extraction_check.md](extraction_check.md). Live Gemini, Atlas and domain verification remain user-deferred. No new coordinate or source mismatch was found that would justify inventing a replacement; the remaining location uncertainty is recorded per endpoint and pair.
