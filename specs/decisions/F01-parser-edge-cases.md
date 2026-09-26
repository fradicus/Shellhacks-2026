# F01 parser edge cases

## Context

The public DESC cards contain cases that the F01 spec does not fully define: a malformed yearly amount on 2024
page 22, table cells without a dollar sign on 2025 pages 24 and 43, narrative-only costs on 2025 pages 44 and 45,
two phase dates on one card in each filing, and four printed totals that differ from the sum of their yearly cells.

## Choice

- Keep the malformed `$19,00,181` yearly amount as `null`, preserve the raw token, and add
  `cost_amount_invalid:2024` plus `yearly_spend_incomplete`. Do not infer a missing zero from the published total.
- Parse a correctly grouped numeric cell in its cost-table column when the printed dollar sign is absent, and add a
  `cost_currency_symbol_missing:<label>` flag.
- Parse an explicitly printed narrative total into `cost_usd`, leave `yearly_spend` empty, and add
  `yearly_spend_not_published`.
- Preserve both the printed yearly cells and total on the four inconsistent cards (2024 pages 3 and 26; 2025
  pages 27 and 29), and add `cost_consistency_mismatch` instead of changing either value.
- Preserve every phase date in `in_service.dates`, leave the singular canonical date null with precision `unknown`,
  and add `in_service_multiple_dates`.
- Store all voltages in `voltages_kv`; the schema's singular `voltage_kv` is the highest printed voltage for the
  project name.

The PDF-embedded font maps printed en dashes to U+FFFD. The parser normalizes that character to an en dash after
representative pages were visually verified. Endpoint splitting accepts the same delimiter without surrounding
spaces and an ASCII hyphen followed by an uppercase endpoint name because the cards use those typography variants
for the same relationship (for example, `Okatie-Bluffton`). Numeric voltage ranges and `Fold-in` remain intact.

## Undo

Change the pure parsing helpers and regenerate the four JSON outputs. No source document or frozen contract must
change.
