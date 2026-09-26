# F14 decisions (filing-change view)

1. **Wording.** An in-service change reads "filed date moved N days later/earlier between filings". It's a fact about
   two filings, never "delayed". When both dates are before the analysis date the change is labelled `historical`.
2. **Cost deltas** show the percentage change between the filed amounts ("+4.6% as filed"). No dollars are derived
   beyond the two filed values.
3. **Grouping and order.** Changes are grouped by `project_key`. The verified example `DESC:0139 M,N` is pinned first
   and outlined; other groups sort by key. The display name comes from the active filing's project record; without a
   project record only the key is shown.
4. **"In any overlap"** is computed from `getMatches` (all views, limit 500): a link to the first pair, or "no overlap".
5. **Limit**: first 200 changes after the field filter, with a "showing 200 of N" note.
6. **Filing names and links** come from `getSources` (C3 + FIX-F06 `/api/sources`) through the same citation helper as
   F11: DESC links to the public PDF `#page=N`; Georgia would show page numbers only (D2).
