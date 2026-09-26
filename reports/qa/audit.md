# F07 merge audit

Initial audit base: `b99f3cb` (F00, F05, F06, C1 and the F05/F06 fixes).

| Area | Evidence | Result |
|---|---|---|
| Sponsor overlap math | Original workbook, independent computation, live core subprocess and golden fixture comparison | Six overlaps, nineteen exclusions; exact gaps and rank agree. Raw deltas are in `golden.md`. |
| One-endpoint confidence | C1 diff and existing regression cases in `tests/golden/test_golden.py` | Medium-confidence one-endpoint pairs remain tentative; high-confidence pairs can be future. Issue #7 has a merged fix. |
| Matching ownership | F05 reads stored ranks/distances; loader imports core for centers; read API queries stored matches | No competing production overlap formula found in these changes. Independent QA math is confined to this test harness. |
| Production data separation | `web/lib/data.ts`, API handlers and loader `SOURCES` | API failures return unavailable; loader excludes `data/fixtures`. Fixture mode remains an explicit local/CI setting. Live Atlas is unverified. |
| Evidence and unknowns | F05 list/table and loader staging | Sample label, filed dates, source IDs and confidence are shown. F11 evidence contents are outside this initial checkpoint. |
| Secrets and scope | Changed paths and server environment-variable access reviewed | No literal credential or browser-exposed server credential observed in the reviewed changes. No read-only sponsor input was edited. |
| Loader retry safety | mongomock failure injected during a second load of the active revision | Confirmed existing issue #17: active pointer stays at the same revision while project records drop from 1 to 0 after delete/failed insert. |

## Open finding

[Issue #17: preserve active data on reload and validate malformed inputs](https://github.com/fradicus/Shellhacks-2026/issues/17) already tracks the loader retry defect. No duplicate issue was opened. The reproduction used only an in-memory mongomock database and synthetic test records; no Atlas writes occurred. The fix belongs to F06.

Reproduction: call `load(db, records, [], "same-revision")` successfully; replace `db.projects.insert_many` with a function raising `RuntimeError`; repeat the same load. `db.meta.active.dataset` remains `same-revision`, but its previously published project documents have been deleted. Readers can observe incomplete data on an active-revision retry.

Continue this audit at checkpoints as later features merge. This report is evidence for the revisions named above, not a release-wide sign-off.
