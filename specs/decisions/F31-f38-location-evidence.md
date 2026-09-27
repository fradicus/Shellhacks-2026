# F31: Display and export reviewed expansion locations

C23 assigns the national explorer's additive evidence display and JSON export to F31. This isolated
Codex-local delegated session adopts F31's frontend-engineer role. F38 produces reviewed records;
F30 validates and activates them. The explorer displays the accepted projection without repeating
publication logic or modifying project status.

Preserve the existing CSV export default. Add an explicit `format=json` option to the same bounded,
read-only export endpoint, including the active dataset and embedded location evidence. Selected projects
show site versus complete/partial endpoint meaning, source precision/date, citations and the latest review.
Unknown precision and source dates remain visible. No renderer or style redesign is included.

Validation and live acceptance are recorded in the PR. Data release and loader integration must be active
before a deployed-map verification can establish delivery; local implementation alone does not establish it.
