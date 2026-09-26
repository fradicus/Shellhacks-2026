---
id: F36
name: Field operations planning desk
lane: B
agent: frontend-engineer
phase: 6
depends_on: [F33, F34, F35]
owns: [web/app/operations/, web/components/operations/, tests/web/operations-ui/]
cut: never
---

# F36 One estimator workflow

Build `/operations` against C15's F33/F34/F35 APIs. Keep manual confirmed coordinate/label inputs, departure and explicit truck facts visible. No guessed truck dimensions or hidden default site. A compact responsive workflow presents directory/source validation, live forecast/alert/work-zone context, annual AEF/soil evidence, route summary/restrictions and outcome estimates independently. Status text distinguishes unavailable, stale, partial and insufficient evidence from zero/no hazard. Source times and coverage reasons are actionable. The side-panel AI prototype stays separate.

No Google route rendering on MapLibre: use an appropriately attributed route-only panel. Route duration is travel time, not construction duration. Weather hazards are observed/forecast facts, not a numerical project-delay probability. No duration/probability appears when F35 abstains. No location/forecast/provider credentials or fake result fixtures in production. Local presentation of explicit user input is not a verified source claim.

Use server APIs only. Poll visible-page current conditions at the declared bounded interval; cancel obsolete requests on input changes, prevent late responses overwriting newer assessments, and stop timers when hidden/unmounted. Keep success from one provider when another fails. Provide keyboard controls, mobile layout, evidence details and retry. Reuse existing tokens; do not edit shared navigation/config or other feature files.

Test validation, unavailable and mixed success, malformed/outdated responses, coordinate/request binding, stale-response races, no-model abstention, polling teardown, keyboard and 390px overflow. Browser tests use the existing GitHub CI server with explicitly mocked test endpoints when needed; identify mocks in test evidence and never call them live data. No local server launch. Full checks plus independent review required before done marker.
