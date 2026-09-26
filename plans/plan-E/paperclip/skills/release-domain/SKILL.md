---
name: "release-domain"
description: "Prepare and validate deployment, scoped secrets, eligible domain handoff and rollback."
---

# Release and domain

## Inputs
Accepted build revision, dataset version, hosting account, authorized deployment scope and human-confirmed domain eligibility.

## Procedure
1. During hours 0–4, verify chosen host can reach Atlas with a permitted network route. Vercel is the default Next.js target; if the selected plan cannot meet network needs, document a fixed-egress alternative and have the operator choose it. Do not default to an unrestricted Atlas access list.
2. Set the deployment root to the implementation web directory. Bind server-only Gemini/Atlas values in host settings, separate from Paperclip's agent inputs. Record plain model/database/analysis configuration without secret values.
3. Produce a concrete release candidate and checks before requesting any missing deployment authorization. This plan does not itself authorize deploying, purchasing a domain or accepting terms.
4. Human obtains the eligible GoDaddy Registry domain and controls registrar access. Prepare the exact DNS records from the host dashboard. Do not guess that any GoDaddy-purchased name qualifies; verify the event offer and suffix rules.
5. Deploy the accepted revision, verify domain resolution and HTTPS, check Atlas-backed reads and protected Gemini behavior, and hand the deployed URL/revision to QA. Capture redacted evidence, not provider keys.
6. Keep previous deployment/dataset pointers and document rollback. Restore them on release-blocking regressions; do not overwrite approved source history.
7. Prepare release notes, track evidence and the final short video with CEO. Keep feature/data/release freeze checkpoints. Human makes the actual submission and accepts platform terms.

## Output and checks
Release checklist with actual outcomes, domain eligibility evidence, revision/dataset mapping, DNS/TLS checks and rollback procedure. Mark live checks pending until performed. A proposed domain or local screenshot is not evidence of a published qualifying app.
