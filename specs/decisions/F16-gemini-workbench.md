# F16 decisions (Gemini workbench)

1. **Unavailable is the product tonight.** F03 committed no model output (live Gemini deferred; `eval.json` status
   unavailable). The page says "Gemini extraction unavailable" with the denominator (0 of N DESC cards) and never
   presents anything as a Gemini result. It still shows each DESC card's real page text and F01's deterministic parse,
   with the Gemini column reading "Not extracted".
2. **Denominator** = DESC project records with a source page (one per card: 91 on the committed corpus), not a
   hard-coded 91. `eval.json` isn't served (it's a non-record envelope the loader skips), so the summary is computed from
   the extraction records themselves.
3. **Agreement** counts a field only when the comparison is `match` *and* its citation is valid; a match with an invalid
   citation shows as "match, invalid cite" and counts as invalid. The caption says "validated field agreement with the
   deterministic parse (not independent human accuracy)", matching F03's measurement label.
4. **Page text** comes from the extraction record's `source_text` when present ("exactly the text Gemini was given"),
   otherwise F01's `raw_text`. DESC only; Georgia cards are filtered out (D2).
5. **Briefs tab** lists every stored brief, passed and rejected, with the rejection reason and a link to `/pair/[id]`
   (via `getBriefs`, C5). Empty until F12 runs.
6. **Layout test.** The Gemini column was checked with one synthetic record labelled `LAYOUT-TEST` everywhere (model
   `LAYOUT-TEST-NOT-GEMINI`), in a throwaway directory. Never committed.
