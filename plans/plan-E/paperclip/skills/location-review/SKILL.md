---
name: "location-review"
description: "Resolve endpoint candidates from public evidence and retain uncertainty before computing sponsor centers."
---

# Endpoint location review

## Inputs
Approved project records with raw endpoint names, verified owner evidence, voltage/county clues and permitted public map sources.

## Procedure
1. Search official public maps and public OSM features using multiple contextual clues. Name similarity alone is insufficient. Do not ask a model to supply authoritative coordinates.
2. Save each candidate's feature ID/source, retrieval date, coordinates, name/owner/voltage/county evidence and reason to accept or reject. Respect source usage policies and cache permitted queries; avoid a production dependency on public Nominatim.
3. For ambiguous homonyms or conflicting coordinates, keep candidates separate and request review. Never average competing candidates. A whole project's center is not an invented endpoint.
4. Mark a located endpoint only when both latitude and longitude pass review. With two located endpoints use arithmetic mean coordinates; with one use that endpoint and label the limitation; with none retain the project without geometry.
5. Store GeoJSON as longitude then latitude and omit unknown geometry. Keep original coordinates and source precision. A project center is a sponsor approximation and does not prove corridor intersection.
6. Hand off accepted endpoints, computed center, evidence and reviewer state to the matcher. QA independently reviews every pair featured in the pitch. Track unlocated records in coverage, not as hidden deletions.

## Output and checks
Location decisions with accepted and rejected evidence; tests for two endpoints, one endpoint, no endpoints and swapped axes. Fixture coordinates remain the untouched sponsor regression input; they are not automatically promoted to production-reviewed locations.
