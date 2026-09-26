# F01 reviewed endpoint scope corrections

Independent QA compared 15 active records with the public source pages and found multi-asset or section-scope ambiguities. These records must retain source evidence and candidate labels without an automatically accepted endpoint pair.

Implement explicit source/page overrides inside parse_card, assert the expected project key, and pin both source PDF hashes. This makes the deterministic register and F03 source validation agree. Preserve all existing names, raw text, costs, dates, active flags and filing-change records. F09 must skip endpoint-ambiguous projects until a reviewer resolves the actual work scope.

Runtime: Windows Codex / data researcher GPT-5.6 Sol high. Independent QA: GPT-6 Astra xhigh. Root integration: GPT-6 Astra. Issue 34 records the source-specific findings.
