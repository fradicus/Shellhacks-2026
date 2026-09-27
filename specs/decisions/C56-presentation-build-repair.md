# C56: preserve merged configuration while repairing the presentation build

The user authorized only safe fixes before the judge presentation and excluded deployment work (R1).
Main `9410954` fails web CI because committed conflict markers make `web/next.config.ts` invalid;
the same marker set remains in the shared navigation CSS. This is the build failure tracked in issue #313.

The technical-lead lane resolves these two frozen files without changing application contracts or providers:

- retain the current navigation declarations and remove only the three conflict-marker lines;
- retain the weather station-index route and both supported station formats (`.json` and `.json.gz`);
- preserve health, operations, national and verified-artifact tracing;
- leave data, map controllers, routes and all active worker files unchanged.

Acceptance requires lint, TypeScript, the production build, the existing national/operations trace checks,
verification that the built weather route includes all indexed station files, and desktop/mobile navigation
and existing-page checks. Required CI must pass for the exact repair revision before merging. No new UI feature,
dependency upgrade, database migration, provider call or deployment is part of this repair.
