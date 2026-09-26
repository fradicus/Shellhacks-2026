---
name: deploy-and-domain
description: Deploy the Gridlock Next.js app to Vercel with env vars and attach a GoDaddy Registry domain via DNS. Use for deploy, env, and domain issues.
---

# Deploy and domain

## Vercel
Humans connect the GitHub repo once in the Vercel dashboard (root directory `web`). After that every
merge to `main` deploys to production and every PR gets a preview URL. Agents with `VERCEL_TOKEN` may use
`npx vercel --cwd web` for manual previews; production changes need board approval.
Project env vars (Production + Preview): `MONGODB_URI`, `GEMINI_API_KEY`, `GEMINI_MODEL`.

## GoDaddy Registry domain (humans register it, agents configure)
Registration uses the MLH GoDaddy Registry offer code; a board member does it. Then in the domain's DNS:
- Apex: `A @ 76.76.21.21`
- www: `CNAME www cname.vercel-dns.com`
Add both hostnames in Vercel -> Project -> Domains; Vercel issues TLS automatically. If Vercel shows
different target values, use Vercel's. Verify with `dig +short <domain>` and loading `https://<domain>`.

## Pre-release checklist
CI green on `main`; `/api/projects` and `/api/overlaps` return data on prod; map loads under 3 s; no secrets in client bundle (`grep -r GEMINI_API_KEY web/.next/static` returns nothing).
