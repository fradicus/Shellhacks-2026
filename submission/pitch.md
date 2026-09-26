# Planner workflow pitch — draft

Target length: about two minutes [unverified until rehearsed]. Use explicit fixture mode for a demo until a real database-backed deployment is configured. Do not imply this script has been recorded or presented.

“Neighboring utilities publish construction plans separately. A planner needs a way to find nearby work and inspect the evidence before contacting another utility.

GridBridge reads the public DESC filings and the permitted Georgia planning-table fields. It preserves source versions, original owner codes and uncertainty. Our current register covers 262 active projects and 400 filed endpoints. Only 89 endpoints have medium-confidence locations; we show the unresolved records instead of inventing coordinates.

Here is the ranked list. Geography decides whether a pair overlaps; exact in-service dates determine its place within a distance band. A milestone is not a construction window. The current run finds 19 candidates: 16 historical, three tentative and no qualifying future pairs. Every candidate still needs review.

Open a coordination card to inspect both filed milestones, source pages and location evidence. The center is an endpoint approximation, not a corridor intersection. The audit calls out insufficient county evidence, so a similar substation name does not become a confirmed opportunity.

The sample demonstrates why the closest pair need not be the top-ranked pair. Then the filing-change view shows how the same project's milestone changed between documents. Both original sources remain available, and the card can be exported or printed.

The Gemini workbench currently shows that live outputs are unavailable. Its pipeline and validation are testable, but we are not claiming real model accuracy, Atlas hosting or an HTTPS domain before those integrations run.

Our next step is planner-reviewed location evidence and a configured live deployment. GridBridge makes a lead inspectable; it does not promise savings.”

## Number sources

Corpus/location counts: [committed F09 coverage](../data/locations/coverage.json). Match counts and ranking: [committed F10 summary](../data/matches/summary.json). Sample counterexample: [untouched golden overlaps](../data/fixtures/golden/overlaps.json). Gemini status: [committed evaluation](../data/extraction/eval.json). Audit wording remains subject to final F13 artifacts.
