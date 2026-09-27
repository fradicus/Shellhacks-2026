# F44: Endpoint names with attached work text

**Context.** The user named California as sparse. 214 of 360 F44 projects are unlocated; some because the shared
parser returns an endpoint with work text attached: "Re-conductor Fulton", "Wilson Sub: Convert", "TL692: Japanese
Mesa", bank codes "Windhub AA" / "Serrano 4AA", "Mesa Spare".

**Choice.** `caiso.locate` strips that text from each parsed endpoint (`endpoint_name`). `caiso.named` is unchanged
because F39's dense Southeast imports it. Single-letter suffixes are kept ("Receiving Station B"). Result: 10 projects
gain a candidate point (146 → 156) and 3 partial lines gain their second endpoint; none is lost. The re-fetched
workbooks have the same hashes (only `retrieved_at` changes); the OSM extract is newer and moved no other center.

**Undo.** Remove `endpoint_name` from `caiso.locate` and rebuild.
