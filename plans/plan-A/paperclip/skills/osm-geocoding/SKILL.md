---
name: osm-geocoding
description: Find real coordinates for substations and lines named in utility project lists using OpenStreetMap Overpass and Nominatim, with confidence levels. Use for geocoding Gridlock endpoints.
---

# OSM geocoding

## 1. Bulk pull per operator (Overpass, no key)
POST to `https://overpass-api.de/api/interpreter`, one query per utility, cache the JSON in `data/osm/`:
```
[out:json][timeout:90];
(
  nwr["power"="substation"]["operator"~"Dominion|SCE&G|South Carolina Electric",i](31.9,-83.4,35.3,-78.5);
  nwr["power"="substation"]["operator"~"Georgia Power|Southern Company|Georgia Transmission|MEAG",i](30.3,-85.7,35.1,-80.8);
);
out center tags;
```
Repeat with `"power"="line"` + `out geom tags;` if line geometry is wanted for ROW estimates.
Also pull substations with **no** operator tag in the border counties; many are untagged.

## 2. Match names
Normalize both sides: uppercase, drop `SUB|SUBSTATION|PRIMARY|SS|TS|#\d|(…)`, collapse spaces.
Exact normalized match -> candidate. Else fuzzy (`difflib.get_close_matches`, cutoff 0.85).

## 3. Leftovers: Nominatim
`https://nominatim.openstreetmap.org/search?q=<name> substation, <county/city>, <state>&format=jsonv2&limit=5`
Send `User-Agent: gridlock-shellhacks/1.0 ($NOMINATIM_EMAIL)`. Max 1 request/second. Cache every response.

## 4. Adjudicate and grade
- One candidate, right state, consistent with PDF zone/description -> `high`.
- Several candidates -> Gemini adjudication (`gemini-api` skill, AI Engineer's helper) with PDF context; pick -> `medium`, note reason.
- Town/city centroid only -> `low`.
- Nothing -> `unlocated`, no coordinates.
Record `osm_id` and a one-line `match_note` for every endpoint. Project `confidence` = worst of its endpoints used for the center.

Sanity check: the sponsor sample gives known coordinates (e.g. Thurmond Sub 33.6601,-82.1959; McIntosh 32.3521,-81.1751). Your matches must land within 1 mi of them.
Quick visual check: https://openinframap.org.
