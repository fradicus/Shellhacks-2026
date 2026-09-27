# F40 Minnesota (part 1)

**225 projects, 51 with an unverified candidate location (48 distinct points), 0 verified.** Rule: [C26](../../specs/decisions/C26-great-lakes-candidates.md).

| | Count |
|---|---|
| Projects (unique MPUC tracking numbers) | 225 (229 table rows; 4 duplicate rows) |
| Status | planned 158, in service 54, cancelled 10, unknown 3 |
| Candidate located | 51: 38 sites, 7 lines with both endpoints, 6 partial lines (one endpoint) |
| Candidate located by status | planned 41, in service 8, cancelled 2 |
| Unlocated | 174: no single facility named 62, no OSM facility with that exact name 58, area/program/multi-facility 24, name found but no operator/voltage corroboration 11, multi-terminal line 10, mixed endpoint reasons 9 |
| Counties from source text | 11 projects |

## Sources

- Project register: 2025 Minnesota Biennial Transmission Projects Report (MPUC Docket E999/M-25-99, filed 2025-10-31),
  Chapter 6 zone pages 6.3–6.8 on minnelectrans.com. Every "Needed Projects" and "Completed/withdrawn" table row
  has a disposition in `data/greatlakes/mn/dispositions.json`; page hashes in `data/greatlakes/mn/sources.json`.
  "Needed" rows are `planned` as the report frames them; that does not prove construction has started.
- Candidate geometry: OpenStreetMap `power=substation` in Minnesota (1,842 features, 593 named; ODbL,
  © OpenStreetMap contributors). The named subset is committed at `data/greatlakes/osm/mn-substations.json`.

## Gaps and next sources

- Minnesota's statewide transmission/substation GIS was withdrawn by the state in July 2022; no official substitute found.
- 11 exact-name matches (e.g. Hibbing, Coon Creek, Byron) lack OSM operator/voltage tags and stay unlocated under C26.
  Official utility GIS or siting dockets could corroborate them.
- Prior biennial reports (2023, 2021, …) would add historical projects; MISO MTEP Appendix A (MTEP numbers are kept in
  `evidence.raw`) is blocked by HTTP 403 to scripts and skipped at the user's direction.

## Spot check

All candidates were reviewed by hand: project name, extracted facility, matched OSM name/operator/voltage and
coordinates (e.g. Prairie Island 44.625, -92.634; Forbes 47.364, -92.691). One systematic error was found and fixed:
names joining two facilities with "and" (Priam … and St John's Lake …) had been placed at the first facility; they are
now unlocated as multi-facility. This check was done by the producer, not an independent reviewer.

## Publication

Records are national-schema valid and sit at the fixed path `data/greatlakes/projects.json`. They are **not yet in the
national snapshot or Atlas**: that needs the separately claimed F30 hook named in C26. No map change is claimed here.

Replay (offline after fetch): from `pipeline/`, `uv run python -m greatlakes.minnesota fetch --cache DIR`, then
`uv run python -m greatlakes.minnesota build --cache DIR --check`.
