---
name: hackathon-submission
description: ShellHacks 2026 judging criteria and track requirements for Gridlock, and how to write the Devpost submission. Use for scope decisions and the final write-up.
---

# Hackathon submission

## General judging
Completion, Originality, Design, Technology, Practicality. Every scope call serves one of these.

## Tracks entered and what proves each
| Track | Proof a judge must see |
|-------|------------------------|
| Sperry Tech - Gridlock | Interactive map of both utilities, highlighted overlaps (< 25 mi), ranked opportunity list, cost/impact estimate, sponsor golden sample reproduced |
| MLH Best Use of Gemini API | Gemini parses GPC tables, adjudicates geocode matches, writes coordination briefs, answers natural-language questions that drive the map |
| MLH Best Use of MongoDB Atlas | Atlas stores projects as GeoJSON with 2dsphere, `$geoNear` powers the radius tool, Atlas Search powers text lookup |
| MLH Best Domain Name (GoDaddy Registry) | App live on the registered domain; domain named in the submission |

## Devpost write-up
Sections: Inspiration (FERC Order 1920, $1.5M-of-$5M freight quote) - What it does - How we built it
(pipeline diagram, stack per track) - Challenges (redacted GPC costs, ambiguous substation names, how we verify) -
Accomplishments (golden sample matched, N projects located, top opportunity with numbers) - What's next (more
utility pairs, SERTP data, line-geometry ROW overlap). Include the live URL, repo URL, and screenshots of map + ranked list + detail panel.
Select all four tracks on Devpost. A human submits; you draft.
