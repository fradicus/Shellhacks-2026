# Deployment verification

The Vercel origin is live, but it reports a different, unmapped revision from the reviewed `main`. The passing row below proves
the listed deployed commit and infrastructure checks only. It does not prove that later fixes, every application
workflow, Google integrations, or contract upload are live. No qualifying custom domain has been verified.

| Recorded | Target | Revision | Health / Atlas | HTTPS + `/` | JS secret scan | Result |
|---|---|---|---|---|---|---|
| 2026-09-27T12:00:13Z | `https://shellhacks2026-mu.vercel.app` | `4b30678aadee6f96c25a19d17d94179f23256b36` | 200; database up; dataset `9548c28191b2ac4eb703ec9283c31e364a911bce` | HTTPS; home 200 | 8 bundles; no configured markers found | **PASSED** |
| 2026-09-27T11:59:39Z | `https://shellhacks2026-mu.vercel.app` | target `1fbcb5d97369a651d8853753aca4caeda1b4638f` | health reported deployed commit `4b30678aadee6f96c25a19d17d94179f23256b36` | live origin; revision not accepted | not release-accepting | **FAILED** — deployed commit mismatch |
| 2026-09-26 | Vercel URL and custom domain | not available | not run | not run | not run | **DEFERRED** — no live targets |

The 2026-09-26 row is retained as dated context from before the Vercel origin was supplied. The authenticated
Vercel account available during the 2026-09-27 review could not manage this exact host, and its alias lookup returned
404. The deployment owner must redeploy the intended `main` revision after its exact-revision required CI passes,
in the existing Vercel project with `web` as the
project root, then rerun the verifier against the full deployed commit. Infrastructure is alive; current fixes are
not live until that check passes.

Passing command for the currently deployed revision:

```bash
node release/verify-deployment.mjs \
  --commit 4b30678aadee6f96c25a19d17d94179f23256b36 \
  --url https://shellhacks2026-mu.vercel.app
```

## Local implementation evidence

These direct module checks used Node 24 and did not launch a web server. They are implementation evidence only.

| Case | Observed response | Elapsed |
|---|---|---:|
| `MONGODB_URI_RO` absent | 503, `db: "not_configured"`, no active dataset | 22 ms |
| Unreachable loopback URI | 503, `db: "down"`, no active dataset | 1,922 ms |
| Reachable local MongoDB without `meta.active` | 503, `db: "up"`, no active dataset | 37 ms |
| Local `meta.active.dataset` set to empty, whitespace, or an object | 503, `db: "up"`, no active dataset for all three cases | not timed |
| Local QA MongoDB `gridbridge_local_review` | 200, `db: "up"`, dataset `74dfa796b4c6777ce7146c3b0a12ee7511a7ea2e` | 16 ms |

Every response used `Cache-Control: no-store` and contained only the documented health fields. The loopback
database is not MongoDB Atlas and the elapsed times are one local run, not service-level measurements.
The malformed-metadata cases used and then dropped the temporary loopback database
`gridbridge_f08_health_metadata_check`; the same direct check preserved the valid dataset ID exactly.

## Run a genuine check

Set `COMMIT` to the full revision deployed from `main`, and set `VERCEL_URL` and `DOMAIN_URL` to the real public
HTTPS origins. The verifier rejects credentials, paths, query strings and fragments in those values.
It follows at most five redirects and rejects any redirect hop that leaves credential-free HTTPS.

```bash
node release/verify-deployment.mjs --commit "$COMMIT" --url "$VERCEL_URL" --url "$DOMAIN_URL"
```

For each supplied origin the command requires:

- valid HTTPS and a `200` home page;
- a `200` health response whose commit exactly matches `COMMIT`, whose database is up, and whose active dataset is present;
- at least one discoverable JavaScript bundle, with every discovered bundle fetched under fixed time and size limits; and
- no `mongodb+srv`, `GEMINI` or `AIza` marker in any fetched client bundle.

The command prints timestamped JSON and exits non-zero on any incomplete or failed check. Add a new table row only
from that real output; a local build, local MongoDB response or proposed domain is not deployment evidence.
