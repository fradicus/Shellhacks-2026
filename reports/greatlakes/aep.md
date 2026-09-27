# F40 AEP Transmission projects (OH, IN, MI)

**127 projects, all 127 with an unverified candidate location from AEP's own project maps (124 distinct points), 0 verified.**

| | Count |
|---|---|
| Projects | 127 from the Ohio (87), Indiana (31) and Michigan (11) maps; 2 listed on two state maps are one record each with both states (South Bend–Niles: IN, MI; Fort Wayne–Hicksville: IN, OH) |
| Status | planned 89 and proposed 26 from the map legend (green "Regulatory Approved & Additional Projects", yellow "Pending Regulatory Approval"); under construction 9 and in service 3 where the newest dated project update plainly says so |
| Location | every project has AEP's marker coordinate (`basis: source_point`); 3 markers are shared by two projects |

## Source

- `https://www.aeptransmission.com/{ohio,indiana,michigan}/geojson/map-setup.json`: AEP's public project maps, each
  marker with coordinates and the project names/pages it represents. Plus one project page per project (description,
  dated "Project Updates", links to Ohio Power Siting Board filings). Hashes in `data/greatlakes/aep/sources.json`.
- Marker placement method is not stated; one marker can stand for a line or a multi-part program. The point is AEP's
  published location for the project, labeled unverified. It is a stronger basis than an OSM name match.
- Status from text only when a sentence plainly states it (construction underway / completed and in service); a
  completion sentence is ignored if it is future tense or the update also mentions construction not yet begun (Niles).
- These are PJM-area projects; PJM's own list is unreachable from this network, so no PJM cross-links were checked.

## Spot check

Producer review of all 12 status changes against their update text, and of every point against its state's bounds:
one marker (Fort Wayne–Hicksville) lies in Ohio while listed on the Indiana map. The Ohio map lists the same project
page, so the record carries both states. Not an independent review.

Replay: from `pipeline/`, `uv run python -m greatlakes.aep fetch --cache DIR` then `build --cache DIR --check`.
