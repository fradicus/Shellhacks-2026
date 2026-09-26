# F08 release readiness

Windows Codex claims F08 after F04 merged. The release engineer uses GPT-5.6 Sol with high reasoning;
root integration and independent review use GPT-6 Astra. Other workers retain their assigned app/contracts.

The user explicitly deferred Gemini, Atlas and domain setup because those resources are not available now.
Implement and verify the health route, local-run documentation and explicit deployment-verification tooling.
Record unavailable production checks as deferred, not passed; use existing issue 10 for the missing resources.

Local MongoDB may be used for bounded QA and must be distinguished from Atlas. Automatic approval review
blocked an earlier local web-preview launch without a specific reason; do not repeat or bypass that action.
Direct health-module checks, ordinary fixture builds and existing CI evidence remain available.
