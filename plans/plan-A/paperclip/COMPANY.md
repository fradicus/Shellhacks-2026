---
name: Gridlock
description: AI company that builds a tool flagging overlapping utility construction plans (Sperry Tech, ShellHacks 2026) with Gemini, MongoDB Atlas, and a GoDaddy Registry domain
slug: gridlock
schema: agentcompanies/v1
version: 1.0.0
license: MIT
authors:
  - name: Eric Zhang
goals:
  - Win Sperry Tech "Gridlock" - compare Dominion Energy South Carolina and Georgia Power planned transmission projects, flag pairs within 25 miles, weigh in-service-date gaps, rank the top coordination opportunities, estimate cost/impact
  - Win MLH Best Use of Gemini API - Gemini does real work in the pipeline and in the product, not a bolted-on chat box
  - Win MLH Best Use of MongoDB Atlas - geospatial ($geoNear, 2dsphere) and search features power the app
  - Win MLH Best Domain Name from GoDaddy Registry - app is live on a memorable GoDaddy Registry domain
requirements:
  secrets:
    - GH_TOKEN
    - GEMINI_API_KEY
    - MONGODB_URI
---

Gridlock is a small AI engineering company with one product: a web app that shows two
neighboring utilities' planned transmission work on one map, flags where it overlaps in
space (primary signal, < 25 mi) and time (secondary signal, in-service date gap in days),
and ranks the pairs most worth coordinating on (shared crews, equipment, freight,
right-of-way).

Work flows:

1. **CEO** owns goals, turns `projects/gridlock/PROJECT.md` into issues, unblocks, writes the Devpost submission.
2. **CTO** owns architecture, reviews and merges every PR, runs deploys.
3. **Data Engineer** turns the two utility PDFs into clean project tables.
4. **Geospatial Engineer** finds coordinates, computes overlaps, ranks, estimates savings.
5. **Backend Engineer** owns MongoDB Atlas and the API.
6. **AI Engineer** owns every Gemini feature.
7. **Frontend Engineer** owns the map UI and ranked list.
8. **QA & Data Verifier** confirms every location match and every overlap against the source PDFs and the sponsor's golden sample.

Hard rule for everyone: public filings only. Anything marked CEII and not published as a
public disclosure is off-limits.
