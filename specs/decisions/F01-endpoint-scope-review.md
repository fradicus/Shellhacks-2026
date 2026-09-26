# F01 reviewed endpoint scope

## Context

The DESC cards describe assets, corridors, sections, and work scopes in the same title. Generic splitting can turn a
multi-asset project or a corridor label into an unsupported two-endpoint pair. Independent review identified 17
source rows where this would create false location certainty: seven multi-asset rows and ten corridor, section, or
landmark-scope rows.

## Choice

- Keep all 91 filed cards and their version evidence. Do not change names, descriptions, active status, dates, costs,
  or source pages.
- Apply reviewed exceptions by pinned source ID and physical page inside `parse_card`. Each exception asserts its
  expected project key. Both DESC PDF hashes are pinned, so a decision cannot silently move to different source
  bytes or a different card.
- For the 17 reviewed rows, leave `endpoints` empty. Preserve ordered source-derived labels in
  `endpoint_candidates`, including normalized and exact raw forms.
- Mark every reviewed row `endpoint_ambiguous`. Use `endpoint_multi_asset` for the seven records whose source fields
  identify more than two assets, and `endpoint_scope_ambiguous` for the ten rows where titles and descriptions refer
  to different corridor sections or to crossing, loop, or landmark scope.
- Apply the same three-candidate treatment to both filed versions of `DESC:0139 M,N`. For `DESC:6238 H`, preserve
  Fairfax, Yemassee, and DESCSQ #1151 as candidates because the title names the Fairfax-Yemassee line while the
  description limits the work to the DESCSQ #1151-Yemassee portion. The latter exception also asserts that exact
  description evidence before suppressing the generic title-derived pair.
- Keep generic parsing for every other card. Ampersands, parallel circuit numbers, and voltage pairs do not by
  themselves make a record ambiguous.
- F09 must not accept, geocode, center, or feature an endpoint-ambiguous DESC record until a reviewer resolves its
  scope. Candidate labels are review evidence, not accepted locations.

## Undo

Remove or revise a page-scoped exception only after reviewing the same pinned public PDF bytes. Regenerate the DESC
outputs and rerun the 91-card, 54-active, 58-version-change, counterexample, schema, and deterministic-output tests.
