# Florida DEP pilot: published and locally verified

PR 161 merged at `748f56a34073c417ce1662431c0d12ca72489eb3`. The sole Atlas load Action 36291780624 and
main CI 36291780644 succeeded. Local read-only verification on 2026-09-27 found 1,303 national projects and 415
located records. Every live national source/project exactly matches the reviewed assembly, including prior records.

Florida adds 17 projects, 17 certification/document events,one independently confirmed partial endpoint and 16 unlocated
records. All 17 current lifecycle statuses remain unknown. The source scope is DEP's current transmission index;
Florida/statewide and the whole Southeast are incomplete.

The local app at `http://localhost:3101` reads actual Atlas dataset 748f56a. Florida's JSON export matches every
reviewed project field and event; its additional GeoJSON equals the supported center. `/explore?state=12` displays
17 records / one point / 16 unknown locations. Hopkins is selectable and discloses its exact review and partial endpoint.

The merged F19 `/time` implementation displays 425 points: 79 legacy and 346 confirmed national, with explicit legacy
mirror handling. This exceeds the national located count of 415 because the legacy display retains its existing 79 points,
whereas the national projection has 69 legacy centers. These counts measure different projections; no 10 new Florida
points are implied. Hopkins remains visible without an in-service date. Selection shows its source, unknown status,
partial facility-reference meaning, matching dataset and exact review hash. No new overlap pair is claimed.

Screenshots and machine-readable Atlas/export/browser receipts accompany this report. This is local app/live Atlas
acceptance, not a production-host/browser acceptance claim. Source accuracy and exact equipment position remain
unknown. The explorer legend is abbreviated and omits an explicit unknown-status legend item; selected evidence
correctly distinguishes confirmed location from unknown construction status. Main-map idle presentation resumed
during inspection; reselection exposed the unchanged facts-bound review.

Continue broader Florida provider coverage and historical comparisons, Georgia reconciliation, and AL/MS/SC/NC/TN/
KY/VA/WV/AR/LA. No F39 completion marker is created.
