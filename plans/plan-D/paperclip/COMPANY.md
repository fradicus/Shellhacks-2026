---
name: Gridlock
description: AI company building a cross-utility transmission coordination finder for ShellHacks 2026 (Sperry Tech track) with Gemini, MongoDB Atlas and a GoDaddy Registry domain
slug: gridlock
schema: agentcompanies/v1
version: 2.0.0
license: MIT
authors:
  - name: Eric Zhang
goals:
  - Win Sperry Tech "Gridlock" - full public project lists for Dominion Energy SC and Georgia Power, sponsor overlap rules reproduced exactly, ranked coordination opportunities with evidence on every number, cost/impact scenario
  - Win MLH Best Use of Gemini API - Gemini extracts, adjudicates, explains, and answers questions that drive the map
  - Win MLH Best Use of MongoDB Atlas - GeoJSON + 2dsphere, $geoNear, Atlas Search and aggregation power the product
  - Win MLH Best Domain Name from GoDaddy Registry - live on a memorable qualifying domain
requirements:
  secrets:
    - GH_TOKEN
    - GEMINI_API_KEY
    - MONGODB_URI
---

Gridlock builds one product: a web app that puts two neighboring utilities' planned transmission
work on one map, flags pairs that are close in space (< 25 mi, primary) or time (secondary), detects
shared facilities and coordination zones, and ranks what's worth a planner's phone call. Every number links to its evidence.

The product spec is `projects/gridlock/PROJECT.md`. Everything else serves it.

Company rules:
- Public filings only. Nothing CEII beyond the table fields the sponsor directs teams to use.
- Never invent a coordinate, date, cost, or owner. Unknown stays unknown and visible.
- Deterministic code decides overlaps. Gemini extracts, adjudicates, and explains; it never computes a distance or a date gap.
- Judges are Sperry's AI team: data quality and traceability are features, not chores.
