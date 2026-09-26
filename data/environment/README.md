# Environmental evidence (F34)

The committed AEF sample covers **only latitude 47.6062, longitude -122.3321,
calendar year 2025** (Seattle). It is a real public pixel, not a project location
or an assessment of current site conditions. Other exact point/year requests
return unavailable. There is no interpolation, geocoding or nearest-pixel fallback.

`aef-samples.json` contains 64 signed raw values and their nonlinear decoding.
`aef-samples.evidence.json` v2 retains per-sample retrieval time, object ETag, HTTP
ranges and hashes of the bytes actually read. The object was 3,380,177,694 bytes;
the sampler read 31,820,382 bytes in 77 requests. A whole-object hash is **unknown**.
The snapshot binds each native pixel locator. Its hash covers UTF-8 JSON after CRLF-to-LF normalization; the reader
checks it and each record's object/index/sample/range binding before accepting a point.
Appending another sample preserves the older sample's evidence and retrieval time.
This is a reviewed static annual
artifact, not a live Earth Engine call or a validated downstream classifier.

`seattle-index.csv` is a reviewed nine-row subset of the official index, selected
using the stated Seattle point and actual source row bounds. The accompanying
evidence identifies the upstream ETag and an 8,000,000-byte range (18,000,000 through
25,999,999). Its hash is a partial-read hash. It is not a hash of the 797,849,869-byte
whole index. CSV exact bytes are retained for its pinned input hash.

Reproduce from the repository's `pipeline/` directory (explicit public requests):

```powershell
uv run python -m environment.index_subset --offset 18000000 --bytes 8000000 --lat 47.6062 --lon -122.3321 --output "$env:TEMP/aef-seattle.csv" --allow-public-network
$indexHash = (Get-FileHash "$env:TEMP/aef-seattle.csv" -Algorithm SHA256).Hash.ToLower()
uv run --extra environment python -m environment --index "$env:TEMP/aef-seattle.csv" --index-sha256 $indexHash --lat 47.6062 --lon -122.3321 --year 2025 --output "$env:TEMP/aef-seattle.json" --allow-public-network
```

The offset is a discovery hint for this reviewed subset, not a spatial index rule.
If upstream index ordering or identity changes, no matching row must remain
unavailable until a new subset is reviewed. The extractor reads at most 8,008,192
bytes in two requests with a 35-second process watchdog. The sampler permits at most 32 MiB and 80 HTTP requests,
with a 45-second budget and a 50-second parent-process watchdog. Every range uses
the same ETag. Errors preserve existing accepted artifacts. Rasterio uses a custom
opener: ordinary file-like input would copy a whole COG and is deliberately avoided.

AEF attribution: The AlphaEarth Foundations Satellite Embedding dataset is produced
by Google and Google DeepMind. Dataset license: CC-BY 4.0.
Official specification: https://developers.google.com/earth-engine/guides/aef_on_gcs_readme

`public-probe.json` is a historical verification report, never runtime fallback
weather. The actual public probe reached NWS, USDA SDA and WSDOT. NWS and mapped
soil context were available; the WSDOT feed was **stale** under the 15-minute
policy. No paid Google requests were made. Its API still needs a key and actual
LVR provisioning; a configuration flag cannot prove provisioning.

Runtime API contracts are exported from `web/lib/operations/contracts.ts`:

- `/api/operations/reference`: supported providers, exact available AEF years,
  readiness, refresh policy and restrictions. Readiness is configuration readiness,
  not an upstream health guarantee.
- `/api/operations/site?lat=...&lon=...&year=...`: independent weather, soil, AEF and
  work-zone envelopes. Malformed, unknown or duplicate parameters return 400.
- `POST /api/operations/route`: explicit origin/destination, departure and actual
  truck dimensions/weight/axles/trailers/hazmat. Dimensions must be exact whole
  millimetres and weight whole kilograms; unsupported fractions are rejected,
  never silently rounded. Only attributed textual Google
  summary is public; no geometry, token or raw response is retained or exported.

NWS requests use the public project issue URL as identifying contact, with an optional
`NWS_USER_AGENT` override. Forecasts older than
six hours or without future periods are stale; future source timestamps fail.
Point alerts retain null-geometry county/zone warnings. Poll no faster than 60s.
USDA supplies map-unit/component survey context and source vintage, never measured
soil strength or present moisture. WSDOT is the sole work-zone adapter; its broad
WA bounding box is only a request prefilter. A hash-bound 2026 Census Washington
polygon then verifies jurisdiction, with boundary uncertainty failing closed.
This does not assert complete road coverage. Work zones within the 0.05-degree point vicinity can be
planned or active; dates, verification and vehicle impact remain explicit.

Route context samples at most five points of actual returned truck geometry. Its
maximum along-route gap and failed samples are displayed; it always remains a
partial/incomplete corridor assessment. Even short gaps can miss hazards. Future
arrival conditions are not guaranteed: this version explicitly does not resolve
weather/work-zone samples to per-point ETAs. Snapping over 100m is rejected;
accepted snapping distances are disclosed. Google response hash/retrieval, geometry
hash, exact sample points, child request/hash/status and departure bind aggregate
evidence without publishing the route geometry. Unavailable AEF remains visible. No
passenger-car or straight-line route substitutes are generated.

Provider transport rejects redirects and arbitrary hosts, limits bodies and
deadlines, makes no retries, and uses no persistent response cache. Forecast/soil
failures do not erase other provider results. Raw Google responses and credentials
are neither committed nor sent to the browser. Google content is not drawn on
MapLibre; the public response is intended for an attributed textual-only panel.

Focused checks from repository root:

```powershell
node --import ./tests/web/operations-providers/loader.mjs --test tests/web/operations-providers/*.test.ts
cd pipeline
uv run pytest -c pyproject.toml -q ../tests/pipeline/test_f34_environment.py
```

An optional public-only probe is `node --import ./tests/web/operations-providers/loader.mjs tests/web/operations-providers/public-probe.ts --allow-public-network`
from repository root. It writes the historical verification report and does not
read credentials or call Google routing. It is not part of offline CI.
`GET /api/operations/conditions?lat=47.6062&lon=-122.3321` refreshes only weather and roadwork, at the published 60-second cadence. It does not repeat soil or annual AEF queries. NWS identifies this public project by default as `GridBridge (https://github.com/fradicus/Shellhacks-2026/issues)`; deployments may override the contact using `NWS_USER_AGENT`. No NWS secret is required.
