# Florida DEP current-index release checkpoint

## Scope

This batch covers the 17 projects in the Florida DEP current transmission certification index. It preserves
17 certification/document events and all 17 source-row dispositions. It does not establish all Florida project
coverage. Lake Tarpon–Kathleen's historical relinquished certification and other providers remain pending.
All twelve Southeast states remain incomplete; no F39 completion marker is appropriate.

The source manifest pins 28 public artifacts. Replay from `pipeline/`:

```sh
uv run python -m southeast.florida_release --cache /private/tmp/gridbridge-southeast-sources --check
```

Raw downloads remain outside Git. The builder writes only the candidate. The integrator separately selects the
reviewed candidate for the fixed release path after identity approval and semantic validation.

## Evidence and limitations

- One independently confirmed location: Hopkins–Bainbridge TA81-01, at the official DEP PA74-03 generating-station
  reference point. It represents one named endpoint and is partial. Exact terminal position, source accuracy,
  measurement date and the South Bainbridge endpoint remain unknown.
- Native EPSG:6439 geometry is retained. The explicit inverse ESRI:108354 transformation was independently
  reproduced; coordinate digits do not imply surveyed accuracy.
- Sixteen projects remain unlocated. Every current lifecycle status is unknown. Past certification dates do not
  imply completion, current construction, or an in-service date.
- DeLand's January 20, 2026 Conditions document supports dated owner/operator identification and a qualified
  certification-document event; it does not establish legal effective date or current operational status.
- Bobwhite uses primary-document TA07-14 while preserving the conflicting TA06-14 alias. Duval–Poinsett retains
  erroneous Kathleen detail text in raw evidence and cites the primary map for the normalized endpoint name.
- Reported Florida counties are source-reported partial geography, not exhaustive route intersections. Hopkins's
  entire interstate extent remains unassessed; no Georgia membership is inferred from a utility name.

Independent source, discrepancy, coordinate and candidate reviews accompany this batch. Final identity approval
binds exact release facts, including the location review and expected counts. C25's newer official/candidate display
policy does not change this batch's stronger confirmed-location evidence or bypass the existing C27 loader contract.

## Publication acceptance still required

Record checks, merged revision, successful sole-writer Action, Atlas read-only dataset/IDs/counts, JSON export,
and visible point/evidence on the existing maps. Prepared or validated artifacts are not live publication evidence.
Continue Florida provider coverage, Georgia reconciliation and the remaining ten states after the pilot journey.
