---
name: deploy-and-domain
description: Deploy the Gridlock Next.js app to Vercel with env vars, and attach a qualifying GoDaddy Registry domain via DNS. Use for deploy, env, and domain issues.
---

# Deploy and domain

## Vercel
A human imports the GitHub repo in the Vercel dashboard once (root directory `web`, framework Next.js). After that:
every merge to `main` deploys to production and every PR gets a preview URL. Agents with `VERCEL_TOKEN` may run
`npx vercel --cwd web` for manual previews. Production promotion or rollback needs board approval.
Env vars (Production + Preview): `MONGODB_URI` (the read-only `web` user), `GEMINI_API_KEY`, `GEMINI_MODEL`, `ANALYSIS_DATE`.
Rollback: redeploy the previous production deployment from the Vercel dashboard. Data is versioned in `data/` and the loader is idempotent.

## GoDaddy Registry domain
- A board member registers it through the MLH "Best Domain Name from GoDaddy Registry" offer. **Only TLDs operated by GoDaddy Registry qualify**; a domain merely sold by the GoDaddy registrar may not. Confirm the eligible extensions on the MLH offer page before choosing.
- DNS at the registrar: apex `A @ 76.76.21.21`, `CNAME www cname.vercel-dns.com`. If Vercel shows different values under Project -> Domains, use Vercel's.
- Add both hostnames in Vercel. TLS is automatic. Verify with `dig +short <domain>` and load `https://<domain>` and `https://www.<domain>`.

## Pre-release checklist
CI green on `main`. `/api/projects`, `/api/pairs` and `/api/zones` return data in production. First paint under 3 s on
a phone. No secrets in the client bundle (`grep -r "GEMINI_API_KEY\|mongodb+srv" web/.next/static` finds nothing).
Open Graph image and title set, so the link previews well in Devpost and Slack.
