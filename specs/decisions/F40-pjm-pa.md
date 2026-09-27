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
