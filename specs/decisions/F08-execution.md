# F08 release readiness

Windows Codex claims F08 after F04 merged. The release engineer uses GPT-5.6 Sol with high reasoning;
root integration and independent review use GPT-6 Astra. Other workers retain their assigned app/contracts.

The user explicitly deferred Gemini, Atlas and domain setup because those resources are not available now.
Implement and verify the health route, local-run documentation and explicit deployment-verification tooling.
Record unavailable production checks as deferred, not passed; use existing issue 10 for the missing resources.

Local MongoDB may be used for bounded QA and must be distinguished from Atlas. Automatic approval review
blocked an earlier local web-preview launch without a specific reason; do not repeat or bypass that action.
Direct health-module checks, ordinary fixture builds and existing CI evidence remain available.

## Technical choices

1. Ship the health route, release verifier and operating documentation without inventing a deployment URL or a
   production result. `release/deploys.md` records the acceptance checks as deferred, not passed.
2. Treat the database as healthy only when both a ping succeeds and `meta._id = "active"` contains a non-empty
   dataset. A reachable database with no active dataset returns `db: "up"`, `ok: false` and HTTP 503 so operators
   can distinguish missing data from a network failure.
3. Bound the complete health probe, including the ping and active-dataset lookup, to two seconds. Return only
   `{ok, commit, db, active_dataset}` with `Cache-Control: no-store`; database exceptions and connection details are
   never returned or logged.
4. Require explicit credential-free HTTPS origins and a full commit SHA in the deployment verifier. A missing
   JavaScript bundle, an unscanned/oversized bundle, a fetch timeout or an unavailable active dataset is a failure.
5. Use the local MongoDB instance only to verify route behavior. It is labelled local QA and provides no Atlas,
   Vercel, DNS or track evidence.

## Completion

After Vercel, Atlas and the domain are configured, run the verifier against both real origins and append its actual
result to `release/deploys.md`. Close issue #10 only after the production health response identifies the expected
commit and active Atlas dataset. No code rollback is required.
