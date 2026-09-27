# F17: Attach Field planning site evidence to Impact pairs

## Context
The site-api drop-in and F34 water/soil providers give survey pH and water
context at a point. Impact already asks PMs about soil conditions for mats but
had no link to that evidence.

## Options
1. Leave Impact cost-only.
2. When a pair has project centers, read existing
   `/api/operations/site` and `/api/operations/water` and link to `/operations`.

## Choice
Option 2. Show screening facts with honest no-data states. Do not infer soil
suitability, flood determination, or wetland delineation (F17 defaults).

## Undo
Remove `SiteEvidence.tsx`, its page mount, styles, and this note.
