# GridBridge

GridBridge is a coordination-discovery tool for transmission planners. It compares public planned-project records
from Dominion Energy South Carolina and Georgia utilities, identifies projects whose known centers are less than
25 miles apart, ranks those leads deterministically, and keeps the source evidence and uncertainty visible. It is
not a compliance tool and does not promise savings.

## Deployment status

No production URL or qualifying custom domain has been verified. Atlas, Vercel and domain configuration remain
pending in [issue #10](https://github.com/fradicus/Shellhacks-2026/issues/10). Local fixture and local MongoDB checks
do not count as production or MongoDB Atlas evidence.

When a deployment is configured, `GET /api/health` reports the deployed Git commit, database state and active
dataset without returning connection details. `release/verify-deployment.mjs` checks the real HTTPS origins,
revision, home page and browser bundles; see `release/deploys.md` for the procedure and current evidence.

## Run the web app locally

Node 24 is required. Install the pinned dependencies from `web/`:

```bash
cd web
npm ci
```

Fixture mode uses the committed sponsor sample and never contacts MongoDB:

```bash
# macOS/Linux
DATA_MODE=fixture npm run dev

# PowerShell
$env:DATA_MODE="fixture"; npm run dev
```

The page labels this mode as sample data. Never set `DATA_MODE=fixture` in production.

For read-only MongoDB mode, set `MONGODB_URI_RO` in the process environment and optionally set `MONGODB_DB`
(default `gridbridge`), make sure `DATA_MODE` is unset, then run `npm run dev` from `web/`. Keep the URI out of
shell history, logs and repository files. The application returns an explicit unavailable state when MongoDB
cannot be reached; it does not fall back to fixtures.

## Run the data pipeline

Python 3.12 and `uv` are required. The deterministic parsers and cached OSM normalization run without service
credentials:

```bash
cd pipeline
uv sync --locked
uv run python -m extract_desc
uv run python -m extract_gpc
uv run python -m osm
```

`uv run python -m gemini_extract` exercises the no-call path. A real batch request requires the separately
authorized `--live` flag plus `GEMINI_API_KEY` and `GEMINI_MODEL`; no live Gemini run is claimed in the current
release. Generated records are validated against the schemas before they are accepted.

The `load` GitHub Action is the only writer to MongoDB Atlas. It validates committed data, stages it under the Git
revision, and changes the active-dataset pointer only after the complete load succeeds. Local application runs use
the read-only MongoDB identity.

Run the repository checks from their respective directories:

```bash
cd pipeline
uv run ruff check .
uv run pytest -q

cd ../web
npm run lint
npm run typecheck
DATA_MODE=fixture npm run build
```

## Architecture

```text
Public filings ──> deterministic Python parsers ──> versioned JSON ──> JSON Schema validation
      │                                                        │
      ├──> cached OSM inventory ──> reviewed location evidence │
      │                                                        v
      └──> optional Gemini batch extraction ─────────> GitHub load action (only Atlas writer)
                                                               │
                                                               v
                                             MongoDB Atlas versioned datasets
                                                               │ read-only
                                                               v
                                              Next.js route handlers and health
                                                               │
                                                               v
                                  Map/list, evidence, changes, coverage and exports

Local/CI fixture mode ──> committed sponsor sample ──> Next.js UI
                         (visibly labelled; never a production fallback)
```

The canonical matching code computes project centers, haversine distance, the strict under-25-mile rule, exact
date gaps and `nearby-band-v1` priority. The UI reads those facts; it does not recalculate or reinterpret them.
