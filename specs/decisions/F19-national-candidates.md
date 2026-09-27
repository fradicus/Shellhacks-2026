# F19 scoped national candidates

This Codex local session owns the C48 frontend integration after F48 #256 and
F30 #265. The small F48 source-code correction is frozen in CI; only F19 is being
implemented now. Activate the UI after its corrected dataset is published.

Keep the existing scope, map, project drawer and comparison. Default to Nearby
candidates; a Legacy pairs switch retains the old views. Read 50 rows at a time
from the dataset-pinned API. Scope changes clear selection and restart paging;
requests are abortable and old responses never replace the new scope. Shared
candidate links retrieve their pair even outside page one. Evidence remains lazy.
Only selected/hovered national connections draw. Label every candidate provisional,
straight-line and not checked against routes or construction schedules. Once F48's
pairs carry stored routes (C46), a connection follows the road and the labels read
"within 25 miles by road"; construction schedules remain unchecked.

Validation: desktop/mobile list, state/pin scopes, load more, pair selection,
source evidence, share/reload, 2D/3D, legacy switch, failed and stale responses,
plus map/scope tests and exact-revision CI. Preserve unknown dates and location
labels; no new point coordinates, route calls, eligibility math or dependencies.

Committed snapshot mode has no published pair collection (F48 explicitly refuses
it). Show that limitation without making a request known to fail; keep Legacy
pairs available. Real Atlas failures still use retry/refresh and never an empty
success. CI navigation checks caught the unnecessary snapshot request.
