# C12: connect the national delivery

This shared integration completes C11/F30/F31 under the user's national follow-on request. It is not a database migration or an activation of the optional AI branch.

- Add `/explore` to shared navigation after its route is present. F07's navigation suite exercises every displayed route.
- Trace only the national JSON directory for the national server routes, using the repository as the tracing boundary. This includes Census reference/catalog files in production while F31 still rejects production project snapshot mode. No raw source PDFs, downloads or cache directory are included by this glob. The optional `/assistant` trace entry has no effect until that route exists on its separate branch.
- Run F31's focused Node checks in required CI and its browser tests against the existing CI server with an explicit local snapshot mode. Optional F32 checks run only when the branch actually contains them. Neither Playwright configuration starts a local server on the worker's machine.
- Keep the existing legacy database helper, loader, search, embeddings, original map and time implementation under their existing owners. The national loader remains in the existing sole-writer Action.

The file tracing configuration follows [Next.js output tracing](https://nextjs.org/docs/app/api-reference/config/next-config-js/output): includes resolve from `web/`, while `outputFileTracingRoot` includes the parent repository. Acceptance must inspect generated server traces for the required reference files and run the integrated snapshot browser checks.

Undo by removing the added navigation/configuration entries; the separate national routes and namespaces retain their own owners. F32 remains a draft potential feature and must not be merged as part of this integration.

Acceptance: the integrated build passed ruff, 342 pipeline tests, web lint/typecheck/build, nine focused national tests, spec/ownership/whitespace checks and independent review. Generated traces package all four required JSON files for all four national routes. GitHub run 36265064703 passed all four national browser cases, including synchronized Reset/Back, API counts, geographic cascading and mobile overflow. The existing legacy Time-view mobile heading failure remains separately tracked in issue #88; 17 of 18 legacy smoke cases pass. Live Atlas/Gemini/domain verification remains deferred by the user.
