# F40 part 5: Pennsylvania PJM construction-register rows

The user handed F40 to Codex local and requested browser acquisition of PJM's blocked XML, starting with
Pennsylvania. The public register was saved from Brave on 2026-09-27; its pinned source hash is recorded in
the adapter. Reuse F38's strict XML reader and date/status semantics, but edit no F38 files or records.

This part takes only rows explicitly reporting State=PA. Exclude native upgrade IDs already published in any
PJM corpus and retain a disposition for every XML row. Owner codes remain verbatim. Facility candidates must
come from the explicit Location/Description fields and the PA OSM/HIFLD inventories under the existing F40
rules; inventories never become projects. Unknown dates and locations stay unknown. Planned and actual dates
remain distinct events. No inference from a past planned date establishes completion.

Append this producer inside the existing Great Lakes fixed release; there is no new national release folder.
The previous F40 increment (#309) is merged and loaded. F39 #319 implementation is complete, CI green and
waiting for the unrelated main-red repair; this is the only new implementation in this session.

Undo: remove the PJM producer, adapter and its data, rebuild the Great Lakes release. No other feature changes.

## Final audit

The final adapter adds 2,966 PA upgrade/component records, 1,203 candidate centers and 503 distinct coordinates.
It preserves all 1,475 existing F40 projects and their centers. There are 106 partial line candidates,
211 two-endpoint means and 886 site points; all new locations remain unreviewed. Raw status and separate
actual/projected/revised dates remain visible. The source has no reliable publication date, so it stays null.

An explicit single `at … substation/station` description overrides a circuit Location for site equipment.
If site equipment still parses as a circuit, the work site is unresolved and the center stays null (98 records).
This rule applies only to the new PJM adapter; the deferred shared one-endpoint policy is unchanged.
Three source-described distribution-only rows are excluded. See the committed summary for all status cohorts
and unresolved reasons, and [the ten-record source/geometry sample](../../reports/greatlakes/pjm-pa-sample.md).

F39 #319 subsequently merged and its Atlas readback succeeded. This supersedes the waiting status above.
