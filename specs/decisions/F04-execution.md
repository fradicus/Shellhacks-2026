# F04 public OSM inventory

Windows Codex claims F04 after FIX-F01 merged. The geospatial role runs GPT-5.6 Sol with high reasoning;
the root coordinator and independent review use GPT-6 Astra. No other worker owns F04.

Fetch only the public regional infrastructure and border-line queries specified in F04. Start with each full
bounding box and split only when needed. Keep one request in flight, bounded retry/backoff, raw response bytes,
query text, retrieval timestamps, hashes and OSM/ODbL attribution. Unavailable or incomplete coverage stays explicit.

This inventory supplies location candidates, not approved project endpoints. Missing names/operators stay missing.
Way/relation centers retain their Overpass provenance. F09 reviews each candidate against project evidence;
workbook coordinates remain regression fixtures and are not copied into production locations.
