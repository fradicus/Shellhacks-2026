# Pennsylvania PJM source and geometry sample

Source: browser-saved [PJM construction XML](https://www.pjm.com/pjmfiles/media/planning/projectConstruction-data/projectCostUpgrades.xml), SHA-256 `cb96605a3dd65cc62111df5ef58ba54075116e53b60b965b198d4b86d764f002`. Ten candidates below were checked against their raw descriptions and the pinned PA OSM/HIFLD facility geometry. This is a source/geometry consistency check; no candidate is promoted to independently reviewed. Map links expose the selected facilities for review.

| Native ID | Source description | Candidate geometry | Coordinates |
|---|---|---|---|
| b0001 | Seven 230 kV breakers at Shawville | source_point: [Shawville Substation (way/181047002)](https://www.openstreetmap.org/way/181047002) | 41.066575, -78.366811 |
| b0007 | Addition of third Lewistown 230/115 kV transformer | source_point: [Lewistown Substation (way/181134948)](https://www.openstreetmap.org/way/181134948) | 40.580374, -77.590308 |
| b0171.1 | Replace two 500 kV circuit breakers and two wave traps at Elroy substation to increase rating of Elroy - Hosensack 500kV | source_point: [ELROY (hifld/144020)](https://www.openstreetmap.org/?mlat=40.278339&mlon=-75.3262568#map=14/40.278339/-75.3262568) | 40.278339, -75.326257 |
| b0284.4 | Changes at Juniata 500 kV substation | source_point: [Juniata Substation (way/125107942)](https://www.openstreetmap.org/way/125107942) | 40.429229, -77.170986 |
| b0287 | Install 600 MVAR Automatically switched capacitor banks at Elroy 500 kV substation (Two 300 MVAR cap banks) | source_point: [ELROY (hifld/144020)](https://www.openstreetmap.org/?mlat=40.278339&mlon=-75.3262568#map=14/40.278339/-75.3262568) | 40.278339, -75.326257 |
| b0293.2 | Raise the operating temperature of the 2-1590 ACSR to 140C for the Martins Creek - Portland 230 kV circuit | two: [Martins Creek Substation (way/95656880)](https://www.openstreetmap.org/way/95656880); [Portland Substation (way/183679569)](https://www.openstreetmap.org/way/183679569) | 40.854773, -75.094962 |
| b0359 | North Philadelphia - Waneeta 230kV reconductor same impedance as existing line; ratings of 760 MVA normal/882 MVA emergency | one: [Waneeta Substation (way/785215536)](https://www.openstreetmap.org/way/785215536) | 40.008553, -75.114627 |
| b0507 | Reconductor the Jarrett - Whitpain 230 kV circuit | two: [JARRETT (hifld/144012)](https://www.openstreetmap.org/?mlat=40.1890022&mlon=-75.1636865#map=14/40.1890022/-75.1636865); [Whitpain Substation (way/41742985)](https://www.openstreetmap.org/way/41742985) | 40.180238, -75.236876 |
| b1156.11 | Replace Croydon 230 kV breaker '115' | source_point: [CROYDON (hifld/143957)](https://www.openstreetmap.org/?mlat=40.0807053&mlon=-74.8913397#map=14/40.0807053/-74.8913397) | 40.080705, -74.89134 |
| TOI437 | Install a 3rd 230-69kV autotransformer at Schuylkill substation | source_point: [SCHUYLKILL (hifld/144039)](https://www.openstreetmap.org/?mlat=39.9420335&mlon=-75.1865543#map=14/39.9420335/-75.1865543) | 39.942034, -75.186554 |

## Findings and corrections

- `b0171.1`: Location names Elroy–Hosensack, but Description places the breaker work at Elroy substation. The adapter uses the explicit work site, not the circuit midpoint.
- `TOI428`: a circuit label for breaker work does not establish which site contains the breaker. Such unresolved site-equipment records now retain null centers, even if both circuit terminals match.
- `b0013`: combined line/substation construction stays unlocated under that conservative rule. This sacrifices coverage rather than infer which geometry represents the work.
- `b0359`: the source Location misspells North Philadelphia; that endpoint stays unresolved. Waneeta is explicitly a partial candidate, not a line route.
- `b0284.4`: the cancelled cohort remains cancelled. A location does not establish current construction.
- `b0012`, `n6890`, `n8207.1`: explicit distribution-only records are excluded with reasons.

No existing F40 point or record is altered. The shared one-endpoint line policy is unchanged. Multiple upgrade IDs can refer to the same site; candidate component counts are not unique-site counts.
