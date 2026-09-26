# Optional app controls

This branch is separate from the delivered national explorer. `/assistant` will embed the same explorer with a side button; it is not a new project database or search implementation.

The offline preview supports explicit commands, labels itself as offline, and sends only validated actions to the same filter/selection controller used by manual controls. Unknown places ask for clarification; stale project IDs fail. Changing a map viewport cannot create a project location. Counts remain the explorer's measured counts and unavailable data stays unavailable.

A future provider adapter may return one `AssistantActionSchema` value after a bounded server-side model request. Run `validateAssistantAction` again against current reference and visible IDs before applying it. The adapter must not gain direct access to the database, URLs, JavaScript execution or writes. Retrieved text is evidence, not instructions. Credentials stay server-side; no provider is configured or called by this prototype.

Examples: `show projects in Massachusetts`, `show planned projects in Connecticut`, `show projects in Orange County in California`, `focus Alaska`, `find "transformer"`, `select project <visible ID>`, `go to time`, `reset`.
