# C55 — Search scoped candidates and identify their projects

## Assignment
The user assigned this Codex local session specification and implementation on
2026-09-27 after the cleanup pass. Codex owns this bounded increment as
technical-lead (contract/F48) then frontend-engineer (F19). Original overnight
time gates are historical for this assignment; STOP, ownership and CI remain.
Ship the existing feature owners' changes sequentially. Preserve merged F52 and
quiet-overview changes. Parked C46 driving-rule drafts (#294, #281, #300) target
an unmerged contract and are not part of this current-main search increment;
leave those branches untouched and record the integration dependency in claims.

## Outcome and scope
A user can find a candidate by either project's filed name, utility name/code,
co-owner, source ID or project ID without paging through the national list.
Two rows with similar names remain distinguishable by filed owner, source and
native project ID. No inferred identities, renamed projects or duplicate merging.
This increment does not add shortlist storage, exports, accounts or dependencies.

## API (F48)
- Add optional `q` to `/api/national-pairs`, max 120 characters. Trim whitespace;
  blank means no search. Reject duplicate parameters, overlong input and `id`
  combined with nonempty `q`; the shared-pair lookup remains independent.
- Case-insensitive literal substring match on `name`, `owner`, `other_owners`,
  `native_id`, `id`, `source_id` of either endpoint. Spaces/underscores between
  words are equivalent so a displayed name can be searched. Regex punctuation
  is escaped, never treated as a user-provided pattern. No fuzzy matching.
- Search the current dataset's project records, then constrain the existing pair
  query to matching endpoint IDs. Apply existing scope and search BEFORE count,
  stored-rank sorting and 50-row pagination. Both endpoints still satisfy scope;
  only one endpoint needs to match the search phrase.
- Use existing MongoDB client and 5-second query limits; return only project IDs
  from the search read. Bound this read to 10,001 IDs and return explicit 422
  guidance to narrow the search above 10,000; never silently truncate results.
- Preserve the response schema, dataset checks, current matching rule, ranking,
  geometry and compact evidence payload. No data migration or publication needed.

## UI (F19)
- One labeled native search form in Nearby candidates: Search and Clear. Enter
  submits. Explicit submit avoids requests on every keystroke. Search is across
  all scoped results; typing alone does not alter the displayed result set.
- Submission/clear resets pagination, pair/project selection and hover. Scope
  changes preserve the submitted search and reset paging. Show total matches
  and explicit loading/empty/error states; retain existing retry/refresh behavior.
- Store submitted `q` in the URL with scope and selected pair. Reload restores
  search. Fetch a shared selected pair by ID even if outside the search page.
  Aborted or stale results must not replace a newer search/scope.
- Each candidate endpoint shows its name, filed owner (unknown stays unknown),
  source ID and native project ID as selectable text. Keep separate project
  identities even when names match. Preserve accessible row buttons, location
  tiers, provisional disclosure, map selection and lazy full evidence.
- Keep Legacy pairs' existing views and behavior. No global search or extra page.

## Validation and delivery
1. F48: literal/space normalization and bounds; project/owner/co-owner/ID matches;
   a result originally beyond page one; combined scope; stable pagination/counts;
   duplicate-looking identities; unknown fields; unchanged dataset/failure checks.
2. F19: desktop/mobile search, Enter, clear, scope+query, query+pair shared reload,
   empty state, stale requests and readable owner/source/native IDs. Preserve lazy
   evidence, map controls and prior clarity changes. Test real published data.
3. Exact-head CI, focused API/browser checks, measured search latency and payload
   size. Merge backend before frontend. No live speed claim from local timing.

Rollback: revert F19 search/labels, then remove the optional API parameter. Existing
clients without `q` continue unchanged throughout delivery.
