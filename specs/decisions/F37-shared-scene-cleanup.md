# F37: shared scene cleanup (#190)

C34 authorizes this bounded adoption after F19 extracts the shared primitives. History now
imports scoped layout styles, dimension controls, bearing/projection math and buffer/lifecycle
helpers from F19. Its shaders, event meanings, dash spacing, palette, date precision, picking
and responsive/reduced-motion rules remain local and unchanged.

This completes only the cleanup of the delivered F37 part 1. Contract/award discovery
remains deferred and unmet; no `changes/F37.md` completion marker is added.

Validation: History event tests (5), shared graphics checks (2), lint, typecheck and fixture
build pass. Browser and final repository CI receipts are recorded on the PR. No throughput
or frame-rate improvement is claimed. Revert this adoption before reverting F19's exports.
