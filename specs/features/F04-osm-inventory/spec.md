---
id: F04
name: OSM power-infrastructure inventory (GA + SC)
lane: A
agent: geo-engineer
phase: 1
depends_on: [F00]
owns: [pipeline/osm/, tests/pipeline/test_f04_, data/osm/]
cut: allowed
---

# F04 OSM inventory

Starts right after F00, so geo isn't idle while the registers are parsed.

## Plan
1. Overpass (`https://overpass-api.de/api/interpreter`, no key) bulk pulls, cached as raw JSON in `data/osm/raw/`. Split into tiles if one times out.
   - `nwr["power"~"substation|switch|plant"](30.3,-85.7,35.3,-78.5); out center tags;`
   - `way["power"="line"](...)` **for the border bbox only** (31.8,-82.6,33.9,-80.6); `out tags center;`
   Pull **all** substations, including those with no `operator` tag.
2. Normalize to `data/osm/substations.json`: `{osm_id, name, norm, lat, lon, operator, voltage, county?}`, with `norm` from `pipeline.common.norm_name`.
3. Save the query text and the retrieval timestamp. Credit OSM (ODbL) in the output metadata.

## Requirements
- At most 1 request at a time, and sleep 10 s between tiles. Handle 429/504 by backing off and retrying up to 3 times.

## Validation
- `tests/pipeline/test_f04_*.py`: the normalizer on a recorded sample. Plus a sanity check: for the sample coordinates (Thurmond 33.6601,-82.1959; McIntosh 32.3521,-81.1751; Okatie 32.3338,-81.0325), verify and report whether a feature whose `norm` contains THURMOND, MCINTOSH or OKATIE is within 1 mi (skip, with a message, if the raw data is missing). A nearby unnamed OSM feature remains unnamed and is reported as a gap; never assign the sample name to make this check pass.
- PR body: counts, bbox, and how many substations have operator tags.

## Defaults
- If Overpass is down, record `status: unavailable`. F09 then uses only sample coordinates, which leaves most projects unlocated. Log it.
