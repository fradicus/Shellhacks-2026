# Independent golden verification

Source: `docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx` (`projects!A1:Q11`, `overlaps!A1:I7`).
SHA-256: `fe01df4ed0691d55fd565784a7510ddfe4682316ff63fb70b963b934c5974f24`.

Reference reads original endpoints and mixed Excel/text dates with openpyxl, then computes arithmetic centers,
haversine with R=3958.8 mi (atan2 form), strict distance <25 mi, exact date gaps and priority independently.
Live production core is called in a separate process using the same workbook inputs. Committed golden
fixture endpoints and dates are checked against those inputs. No production math is used by the reference.

Workbook distances are published to two decimals; raw rounding deltas below are expected, not hidden.
Every nonzero core/center delta is listed. Absolute tolerance for floating-point comparison is 1e-10;
pair membership, gaps, bands, ranks and workbook two-decimal distances must agree exactly.

| Pair | Projects | Reference mi | Workbook mi | Raw minus workbook | Core minus reference | Gap days |
|---|---|---:|---:|---:|---:|---:|
| OVL_1 | DESC:DESC_2__GPC:GPC_1 | 4.088086278374062 | 4.09 | -0.0019137216259377254 | 0.0 | 3074 |
| OVL_2 | DESC:DESC_3__GPC:GPC_2 | 5.650181138667416 | 5.65 | 0.0001811386674157589 | 0.0 | 152 |
| OVL_3 | DESC:DESC_3__GPC:GPC_3 | 7.5481645003824145 | 7.55 | -0.0018354996175853344 | 0.0 | 517 |
| OVL_4 | DESC:DESC_1__GPC:GPC_1 | 8.014463286708528 | 8.01 | 0.004463286708528358 | 0.0 | 3074 |
| OVL_5 | DESC:DESC_5__GPC:GPC_2 | 14.34158427301774 | 14.34 | 0.001584273017739335 | 0.0 | 365 |
| OVL_6 | DESC:DESC_5__GPC:GPC_3 | 14.809675845040983 | 14.81 | -0.0003241549590171644 | 0.0 | 730 |

Priority: OVL_2, OVL_3, OVL_1, OVL_4, OVL_5, OVL_6.
Checked 10 projects and 25 cross-utility pairs; expected six overlaps and nineteen exclusions.

## Nonzero center/core differences

None.

## Result

PASS: workbook, independent calculation, fixtures and live core agree within the stated precision.
