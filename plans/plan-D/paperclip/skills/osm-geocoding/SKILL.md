---
name: osm-geocoding
description: Find real coordinates (and line geometry) for substations and lines named in utility project lists using OpenStreetMap Overpass and Nominatim, with confidence grading and Gemini adjudication. Use for geocoding Gridlock endpoints.
---

# OSM geocoding

## 1. Bulk pull (Overpass, no key). Cache everything in `data/osm/`
POST `https://overpass-api.de/api/interpreter`:
```
[out:json][timeout:120];
(
  nwr["power"~"substation|switch|plant"](30.3,-85.7,35.3,-78.5);
);
out center tags;
```
Pull **all** power substations in GA+SC, not only operator-tagged ones: many border substations have no operator tag.
Filter by operator afterwards when choosing between candidates. For line geometry:
`way["power"="line"](bbox of the two endpoints + 5 mi); out geom tags;`, once per two-endpoint project, cached.

## 2. Normalize names (used everywhere, including `shared_facility`)
Uppercase; remove `SUBSTATION|SUB|PRIMARY|SWITCHING STATION|SS|TS|PLANT|DAM|#\d+|\(.*?\)`; replace `FT` with `FORT`
and `ST` with `SAINT` at the start; collapse spaces. Store it as `endpoint.norm`.

## 3. Match
Exact norm match -> candidates. Else `difflib.get_close_matches(norm, names, n=5, cutoff=0.85)`.
Filter candidates to the project's state (a GPC endpoint may legitimately sit in SC, e.g. tie lines: allow within 10 mi of the border).

## 4. Leftovers: Nominatim
`https://nominatim.openstreetmap.org/search?q=<name> substation, <county/city>, <state>&format=jsonv2&limit=5`
Header `User-Agent: gridlock-shellhacks/1.0 ($NOMINATIM_EMAIL)`. At most 1 request per second, cached, only a few hundred calls total.

## 5. Grade
- `high`: one candidate in the right state, consistent with the PDF zone/description (and operator tag if present).
- `medium`: several candidates -> Gemini adjudication picked one, with a stated reason; or one candidate with no corroboration.
- `low`: town centroid or fuzzy-only match.
- `unlocated`: no coordinates, ever.
Store `osm_id` (`node/123`, `way/456`) and a one-line `match_note`. Project confidence = worst endpoint used in the center.

## 6. Line geometry for ROW
If an OSM line way connects (within 0.3 mi) both endpoint substations and its voltage tag matches, store it as the project geometry. Otherwise the geometry is a straight dashed segment in the UI and isn't used for acres.

Sanity: sponsor sample coordinates (Thurmond 33.6601,-82.1959; McIntosh 32.3521,-81.1751; Okatie 32.3338,-81.0325) must be matched within 1 mi. Quick visual check: https://openinframap.org.
