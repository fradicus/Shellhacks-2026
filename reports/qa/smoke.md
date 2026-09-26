# F07 browser verification

The suite runs against a production build with `DATA_MODE=fixture`. It covers:

- Every main navigation route returns HTTP 200, renders a main heading and has one active navigation link.
- All six sponsor pairs appear in priority order in the historical view, with the sample-data label visible.
- Selecting the first pair updates its pressed state and displays the 5.65 mi map popup. Its Evidence link opens the matching pair URL with HTTP 200.
- An injected basemap HTTP 503 leaves all six overlaps usable, displays the failure message and preserves the accessible ten-project table and attribution.
- Each check runs at 1440×1000 and 390×844. Uncaught exceptions and console errors fail the test; only the precise injected style-request 503 is exempt in the failure test.

Result on the initial QA base `b99f3cb`: **6 passed (8.0s)**, Chromium 153.0.8010.12, Playwright 1.63.0, Node 24.13.0.

## Run locally

From the repository root, install the pinned dependencies and browser:

```sh
(cd web && npm ci && npx playwright install chromium)
ln -s web/node_modules node_modules
(cd web && DATA_MODE=fixture npm run build)
```

Start the server in a separate terminal:

```sh
cd web
DATA_MODE=fixture npm start -- -p 3000
```

Run the browser suite from the root:

```sh
BASE_URL=http://localhost:3000 web/node_modules/.bin/playwright test -c tests/e2e
```

The existing non-required CI `e2e` job detects `tests/e2e/playwright.config.ts`, starts the fixture production server and runs this command automatically. No workflow or package changes are needed.

## Independent workbook check

```sh
cd pipeline
uv run python ../tests/e2e/golden_independent.py
uv run pytest -q --import-mode=prepend ../tests/e2e/test_golden_independent.py
```

The verifier prints all six pairs and exits nonzero on a mismatch. Nine verifier tests include deliberately changed distances, date gaps, missing pairs, ordering, centers, fixture dates and workbook distances. A tiny floating-point difference must remain visible in the report even when within tolerance. These Python QA checks are run explicitly; the existing pipeline pytest discovery does not include `tests/e2e`.

## Limits

The smoke suite serves a local empty MapLibre style and the installed worker, exercising real map rendering and selection without depending on tile-provider uptime. It does not verify live basemap content, Atlas credentials, a deployed domain, or Gemini integration. Placeholder pages are checked for reachability and errors; their unfinished feature content is not claimed complete.
