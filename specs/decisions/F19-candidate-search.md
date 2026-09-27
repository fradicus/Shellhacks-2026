# F19 candidate search

Codex local / frontend-engineer owns the C55 interface increment. Backend #317
is complete and awaiting the shared C56 build repair and CI; this branch stacks
on it and merges after it. Parked C46 driving-rule drafts remain untouched.

Use one native submitted search form. Keep draft text separate from the applied
query; include the applied query in the existing request key and URL. Reset
selection and pagination on search, preserve search on scope changes, and keep
shared-pair lookup independent. Display each endpoint's filed owner, source and
native ID without fetching full evidence. Unknown owner remains explicit.

Validate desktop/mobile search, clear, URL reload, scope, literal empty results,
stale requests and readable identity labels alongside existing map tests.
Rollback removes only the form, labels and optional query wiring.
