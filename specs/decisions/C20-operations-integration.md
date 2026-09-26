# C20: publish the operations modules as one reviewed workflow

Issue #97 coordinates C15/F33–F36. This shared integration belongs to the Windows root technical lead. It preserves the other computers' C14 search, C18 visual system, F19 time view and F37 historical-page work.

Delivery is staged: package and validate the eight merged backend APIs first, so F36's own PR can run its UI checks through the shared workflow. Add the navigation entry in a C20 follow-on after the F36 page exists. The first integration PR does not claim the estimator screen is delivered.

After the owned modules and page exist, add `/operations` navigation using the current shared visual system; trace the exact public verified-directory and environmental artifacts required by the deployed route handlers. Never package private actual-job histories, model candidates or synthetic test fixtures into public deployment assets. Outcome models remain explicitly configured external private files.

Run verified-directory, operational-provider and outcome Node tests in the required CI check when their modules exist. Run F36 browser tests in the existing GitHub CI browser job, retaining the national, optional assistant and legacy tests. Check deployment traces after building. Local server launch remains prohibited by the earlier approval review; no alternate launcher is used.

F35 deployment additionally requires `OUTCOMES_APPROVED_AT` (UTC timestamp), alongside `OUTCOMES_MODEL_PATH` and `OUTCOMES_APPROVED_SHA256`. It is an external approval record: requests earlier than this timestamp cannot use the newly approved model. The model itself binds path-free import/source/authorization/review provenance; it cannot self-activate. The hash and timestamp are deployment configuration, not browser inputs. Missing actual records, approval or a passing evaluated cohort means no prediction.

No live Google truck-route access, private histories, model accuracy, national work-zone coverage or production deployment is claimed by integration checks. Each provider's actual coverage and current status remain visible. F32's optional assistant stays on its separate branch.

## Additive current-conditions contract

F34 adds `GET /api/operations/conditions?lat=<number>&lon=<number>` with exactly one of each required parameter, finite latitude/longitude bounds matching its point schema, and rejection of extra parameters. `ConditionsResponse` is `{ request: { lat, lon }, weather: Envelope<WeatherData>, roadwork: Envelope<RoadworkData> }`, using the existing provider contracts and independent failure states. It never calls soil, AEF or paid routing. This root-reviewed addition preserves the existing site and route contracts.

F36 performs a full site request initially, then refreshes only these current conditions every 60 seconds while visible and bound to the active point. It retains the original soil/annual AEF evidence timestamps and stops polling on changed inputs, hidden pages and unmount. Refresh failures must remain visible and cannot make older evidence appear current. This avoids turning USDA's 24-hour reference interval into a 24-hour delay for weather updates.

NWS uses the public project issues URL as its default identifying contact, with `NWS_USER_AGENT` as a deployment override. No API credential is needed for the NWS adapter. This default does not bypass freshness or response validation, and does not imply coverage or availability when provider checks fail.

## Dated adapter verification

On 2026-09-26 at 22:40 UTC, the root independently called the F34 conditions service for the previously evidenced public Seattle point (47.6062, -122.3321), using the default identifying contact and no Google credentials. NWS returned `available`, 156 forecast periods, zero active point alerts, and a source update of 18:26:46 UTC. WSDOT was reachable but correctly returned `stale` because its source update was 00:00:14.8388927 UTC. These are observations of that adapter call, not a production deployment, a future forecast guarantee or a corridor-wide all-clear. No source file, private history or model was changed by this check.
