# National/Southeast/3D requirements

| ID | Requirement | Priority |
|---|---|---|
| GEO-01 | U.S. discovery frame includes navigation for 50 states and DC, with explicit Alaska/Hawaii views. No inference of complete data coverage from the map extent. | R1 |
| GEO-02 | Southeast lens is GA/SC/NC/FL/AL/MS/TN/KY; reviewed GA/SC is the first comparison. State/planning boundaries are not eligibility gates. | R1 |
| DATA-01 | Display Not inventoried, Source found, Approved/extracted and Reviewed projects separately; show source scope, versions, freshness and exact counts. Blank coverage cannot read zero opportunities. | R1 |
| DATA-02 | Preserve legal owner separately from publisher/parent company; quarantine ambiguous CEII/public pages; resolve repeated project versions across filings. | R1 |
| VIS-01 | Three.js runs as a MapLibre custom layer with fixed ground anchors and a labeled vertical in-service-date axis. No implied grid route, energy flow, elevation or construction duration. | R1 |
| VIS-02 | Render exact dates using z_visual = 1000 × calendar-day offset from scene_epoch / 365.25. Units are exaggerated display meters. Sample epoch 2023-01-01; production uses a declared fixed scene epoch. | R1 |
| VIS-03 | Unknown/month/year-only dates use an exact-date-unknown tray. Source date precision is preserved. Hypothetical exact dates, if entered, remain assumptions. | R1 |
| VIS-04 | Toggle 2D/3D without changing pair eligibility, numerical distance, day gap, IDs or source version. Geographic facts never derive from screen/inset positions. | R1 |
| UX-01 | National → Southeast → reviewed pair → Reveal time → evidence → export works by keyboard; reduced-motion and WebGL failure preserve useful table/2D access. | R1 |
| UX-02 | Date drag has equivalent date-input controls, published ghost, explicit assumed value, safe reset and no mutation of stored facts. Changing date alone never creates/removes geographic overlap. | R2 |
| UX-03 | Filing playback names both versions/pages and shows a verified change; unknown disappearance is not cancellation. | R2 |
| PERF-01 | Test up to 300 records, explicitly labeling synthetic performance fixtures; target >=30 FPS over a 10-second orbit and <=250 ms local selection response after load on the recorded demo device/browser. | Future runtime check |
| SCALE-01 | National ingestion admits one reviewed source family at a time. Candidate acceleration must preserve reference recall at region seams and distance boundaries. | R4 |
| SCALE-02 | Retain actual Alaska/Hawaii geography and flag antimeridian midpoint cases for rule review; inset placement is presentation only. | R4 data / R1 navigation |

Existing sponsor rules, Atlas/Gemini/domain tracks, source/cost limitations and golden outputs remain binding. A 3D fallback does not count as passing VIS-01. No new account or API key is required by Three.js. The selected degree of regional ingestion must be visible in the pitch.
