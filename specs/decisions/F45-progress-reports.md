# F45: Southwest utilities' 2026 WECC progress reports

**Context.** Arizona and Colorado stay thin for their size. The TPPL is each sponsor's own list; the same utilities'
public 2026 WECC Annual Progress Reports (wecc.org, no login) sometimes name projects the TPPL does not.

**Choice.** Transcribe the eight reports (PSCo, Tri-State, APS, TEP, AEPCO, PNM, EPE, WAPA) with page and verbatim
quote into `data/southwest/transcriptions/`, read through `interiorwest.apr` (F50) by import: every quote, title and
facility is re-found in the pinned PDF; a row naming a TPPL record (or another rollout's) as the same project is
excluded; a row whose text names no state is placed only by an operator- or voltage-corroborated facility in the
owner's territory within F45's states. Result: 8 new projects, all located; the 272 earlier records keep their
centers (the fresh cache changes only `retrieved_at`).

**Undo.** Drop the progress-report block from `southwest.build` and rebuild.
