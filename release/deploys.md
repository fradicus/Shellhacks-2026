# Deployment verification

No production verification has been run. The Vercel project URL, MongoDB Atlas bindings and qualifying custom
domain were not configured or supplied for this release, so HTTPS, deployed-revision, Atlas-read and browser-bundle
checks remain pending in [issue #10](https://github.com/fradicus/Shellhacks-2026/issues/10). This is deliberately not
a passing production row.

| Recorded | Target | Revision | Health / Atlas | HTTPS + `/` | JS secret scan | Result |
|---|---|---|---|---|---|---|
| 2026-09-26 | Vercel URL and custom domain | not available | not run | not run | not run | **DEFERRED** — no live targets |

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
