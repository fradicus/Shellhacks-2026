# Grounded brief artifacts and F06 integration

Run from `pipeline/`: `uv run python -m briefs`. This default is offline even when Gemini credentials exist.
It selects at most 15 canonical F10 matches, future first then historical in stored priority order; tentative is excluded.
It writes `summary.json` with `status: unavailable`, `model: null`, `calls: 0`, and current input hashes.
On a fresh checkout `briefs.json` is `[]`. Existing brief bytes are preserved by offline or unconfigured runs.
No response/model/timestamp is fabricated. Offline test responses are explicitly synthetic.

Optional real execution: set `GEMINI_API_KEY` and `GEMINI_MODEL`, then run `uv run python -m briefs --live`.
The user has deferred this live execution. `--repo-root PATH` selects an existing canonical input tree.
Live execution verifies pinned source PDFs and deterministic permitted fields locally before any cache reuse or call.
Only fact objects are sent: DESC names/dates/codes/status/descriptions; Georgia names/dates/codes only; deterministic
match distance/gap/band/view/date. No Georgia PDF, page text, description, coordinates, tools or uploads are sent.
Source content is untrusted prompt data. Transient calls retry at most twice; invalid output regenerates once.
Persistent transport failures preserve prior evidence. Rejected responses have reasons; cached responses are revalidated.

## Exact pure helper contract (issue #43)

```python
from briefs.facts import current_input_hash
current_input_hash(match_id: str, ready: dict[str, list[dict]]) -> str | None
```

F06 calls this **before dataset-prefixing IDs**, after joining locations into projects. It also accepts raw records.
`ready` contains `matches`, `projects`, `sources`, and optionally `locations`. Without `locations`, it gathers located
records from joined `projects[].endpoints`; joined filed names must remain in `filed_endpoints`. Inputs are not mutated.
No I/O, environment values, model configuration or F06 imports occur. Missing, ambiguous or stale bindings return `None`.

The helper requires F10 `match.bindings.a/b.{project_id,source_id,location_ids,center}`, per-side
`location_confidence`, exact active project/source IDs, valid source SHA256, complete accepted endpoint sets and current
filed endpoint/source identities. It recomputes center/match facts through frozen `matches.core`, never separate math.
The hash includes the selected permitted facts, source page/version/SHA, endpoint identity/coordinates/confidence/evidence
and spatial rule version. It excludes dataset, review state and rank. JSON is canonical UTF-8: sorted keys, compact
separators, non-ASCII preserved, no NaN/Infinity. Source PDFs use their separately pinned binary SHA256.

Lower-level API: `build_match_input(match, projects_by_id, locations_by_id, sources_by_id)` returns
`{facts, input_hash, binding}` or raises for invalid input. Only `facts` goes to Gemini; `binding` stays local.

F06 wiring is owned by F06: pass this function as `stage(..., brief_hash=current_input_hash)` or use it as that
callback's default. Merely comparing match IDs is insufficient. Preserve source artifacts; reject stale/unverifiable
passed briefs in the staged dataset. Until wired, F06's existing default deliberately rejects them as unverified.

Cache identity combines `input_hash`, exact model, prompt version and response-schema version. Cache files contain
response bytes/hash and original successful-call timestamp. A cache hit retains that timestamp, requires exact metadata,
and reruns shape/citation/numeric/claim validation. `summary.json` and cache envelopes have no `_id`, so the loader skips them.
