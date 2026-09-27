"""Synthetic response fixtures; no recorded or live Gemini outputs are represented here."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from briefs import runner
from briefs.facts import build_match_input, canonical_hash, current_input_hash, unique
from briefs.validation import validate_response
from common import REPO_ROOT, load_json, write_json
from gemini_extract.transport import TransportFailure
from load.build import join_projects
from matches import core


@pytest.fixture
def inputs():
    return runner.load_inputs(REPO_ROOT)


@pytest.fixture
def bundle(inputs):
    return build_match_input(inputs["matches"][0], *(unique(inputs[k]) for k in ("projects", "locations", "sources")))


def clean(bundle):
    value = next(f["value"] for f in bundle["facts"] if f["id"] == "match.distance_display_mi")
    return {"supported_facts": [{"text": f"The project centers are {value} miles apart.",
                                 "fact_ids": ["match.distance_display_mi"]}],
            "possible_shared_activities": [{"text": "Possible crews planning.", "fact_ids": ["a.name", "b.name"]}],
            "questions": ["Which milestones remain current?", "Who should validate the endpoints?", "Could planners compare scope?"],
            "limitations": ["County identity and construction schedules remain unverified."]}


def test_clean_explicitly_synthetic_response(bundle):
    assert validate_response(json.dumps(clean(bundle)), bundle["facts"])[1] == []


@pytest.mark.parametrize("text", ["The distance is 999999 miles.", "The distance is one million miles.", "The gap is 1e99 days."])
def test_unsupported_numbers_rejected(bundle, text):
    response = clean(bundle)
    response["supported_facts"][0]["text"] = text
    assert "number_not_in_cited_facts" in validate_response(json.dumps(response), bundle["facts"])[1]


def test_cross_fact_number_and_unknown_id(bundle):
    response = clean(bundle)
    response["supported_facts"][0]["fact_ids"] = ["match.band"]
    assert "number_not_in_cited_facts" in validate_response(json.dumps(response), bundle["facts"])[1]
    response["supported_facts"][0]["fact_ids"] = ["invented.fact"]
    assert "unknown_fact_id" in validate_response(json.dumps(response), bundle["facts"])[1]


@pytest.mark.parametrize("group,text", [("supported_facts", "The centers are 20277 miles apart."),
                                       ("supported_facts", "The in-service gap is 20277 days."),
                                       ("questions", "Could the 20277 mile distance support equipment planning?"),
                                       ("limitations", "The distance is 20277 miles.")])
def test_identifier_cannot_authorize_measurement(bundle, group, text):
    response = clean(bundle)
    if group == "supported_facts":
        response[group][0] = {"text": text, "fact_ids": ["b.native_id"]}
    else:
        response[group][0] = text
    assert "numeric_fact_type_mismatch" in validate_response(json.dumps(response), bundle["facts"])[1]


@pytest.mark.parametrize("group", ["supported_facts", "possible_shared_activities", "questions", "limitations"])
@pytest.mark.parametrize("quantity", ["two", "forty"])
def test_spelled_measurements_cannot_borrow_description_numbers(bundle, group, quantity):
    response = clean(bundle)
    next(f for f in bundle["facts"] if f["id"] == "a.description")["value"] = "Two transformers will be installed."
    text = f"Possible crews planning for centers {quantity} miles apart."
    if group in ("supported_facts", "possible_shared_activities"):
        response[group][0] = {"text": text, "fact_ids": ["a.description"]}
    else:
        response[group][0] = text
    assert "numeric_fact_type_mismatch" in validate_response(json.dumps(response), bundle["facts"])[1]


def _straight_match(match: dict) -> dict:
    base = {k: v for k, v in match.items() if k not in ("drive_mi", "route")}
    return {**base, "band": 0 if match["distance_mi"] < core.NEAR_BAND_MI else 1,
            "rule_version": core.RULE_VERSION, "rank_version": core.RANK_VERSION}


def _drive_match(match: dict, drive: float) -> dict:
    return {**_straight_match(match), "drive_mi": drive, "band": 0 if drive < core.NEAR_BAND_MI else 1,
            "rule_version": core.DRIVE_RULE_VERSION, "rank_version": core.DRIVE_RANK_VERSION}


def test_drive_match_cites_stored_drive_and_straight_line_match_is_unchanged(inputs):
    tables = [unique(inputs[k]) for k in ("projects", "locations", "sources")]
    legacy = _straight_match(inputs["matches"][0])
    straight = build_match_input(legacy, *tables)
    assert not {"match.drive_mi", "match.drive_display_mi"} & {f["id"] for f in straight["facts"]}
    drive = min(legacy["distance_mi"] + 1.5, core.OVERLAP_MI)
    driven = build_match_input(_drive_match(legacy, drive), *tables)
    facts = {f["id"]: f["value"] for f in driven["facts"]}
    assert facts["match.drive_mi"] == drive and facts["match.drive_display_mi"] == f"{drive:.2f}"
    assert driven["input_hash"] != straight["input_hash"]
    text = f"The driving route between the centers is {facts['match.drive_display_mi']} miles."
    response = {**clean(straight), "supported_facts": [{"text": text, "fact_ids": ["match.drive_display_mi"]}]}
    assert validate_response(json.dumps(response), driven["facts"])[1] == []
    with pytest.raises(ValueError, match="stale_match_facts"):
        build_match_input({**legacy, "drive_mi": drive}, *tables)
    with pytest.raises(ValueError, match="stale_match_facts"):
        build_match_input(_drive_match(legacy, core.OVERLAP_MI + 0.01), *tables)


def test_bool_endpoint_index_is_not_integer_slot(inputs):
    match = inputs["matches"][0]
    lid = match["bindings"]["a"]["location_ids"][0]
    next(e for e in inputs["locations"] if e["_id"] == lid)["endpoint_index"] = False
    assert current_input_hash(match["_id"], inputs) is None


@pytest.mark.parametrize("text", ["There will be savings.", "Built at the same time.", "Simultaneous construction.",
                                  "These projects will be built together.", "Their construction windows overlap."])
def test_prohibited_claims_in_any_output(bundle, text):
    response = clean(bundle)
    response["questions"][0] = text
    assert "prohibited_claim" in validate_response(json.dumps(response), bundle["facts"])[1]


def test_strict_shape_and_possible_activity(bundle):
    response = clean(bundle)
    response["possible_shared_activities"][0]["text"] = "Crews will be shared."
    assert "activity_not_allowed_or_not_tentative" in validate_response(json.dumps(response), bundle["facts"])[1]
    response["validation"] = "passed"
    assert validate_response(json.dumps(response), bundle["facts"])[1] == ["invalid_response_shape"]
    assert validate_response("{", bundle["facts"])[1] == ["invalid_json"]


def test_only_permitted_georgia_facts_and_raw_joined_hash_agree(inputs, bundle):
    bfields = {f["id"] for f in bundle["facts"] if f["id"].startswith("b.")}
    assert bfields == {"b.name", "b.native_id", "b.utility", "b.owner_code", "b.in_service"}
    mid = inputs["matches"][0]["_id"]
    assert current_input_hash(mid, inputs) == bundle["input_hash"]
    joined = {**inputs, "projects": join_projects(inputs["projects"], inputs["locations"])}
    assert current_input_hash(mid, joined) == bundle["input_hash"]
    del joined["locations"]
    assert current_input_hash(mid, joined) == bundle["input_hash"]
    altered = copy.deepcopy(inputs)
    for m in altered["matches"]:
        m.update(rank=1234, review_state="confirmed", dataset="another")
    assert current_input_hash(mid, altered) == bundle["input_hash"]


@pytest.mark.parametrize("field,value", [("source_id", "wrong"), ("project_id", "wrong"), ("lat", 44),
                                        ("confidence", "rejected"), ("norm", "wrong")])
def test_changed_endpoint_fails_closed(inputs, field, value):
    match = inputs["matches"][0]
    lid = match["bindings"]["a"]["location_ids"][0]
    next(l for l in inputs["locations"] if l["_id"] == lid)[field] = value
    assert current_input_hash(match["_id"], inputs) is None


def test_changed_source_hash_invalidates_brief(inputs, bundle):
    inputs["sources"][0]["sha256"] = "a" * 64
    # Alter the source actually selected, regardless of manifest ordering.
    sid = inputs["matches"][0]["bindings"]["a"]["source_id"]
    next(s for s in inputs["sources"] if s["_id"] == sid)["sha256"] = "b" * 64
    assert current_input_hash(inputs["matches"][0]["_id"], inputs) != bundle["input_hash"]


def test_duplicate_active_or_endpoint_identity_fails_closed(inputs):
    mid = inputs["matches"][0]["_id"]
    inputs["projects"].append(copy.deepcopy(next(p for p in inputs["projects"] if p["active"])))
    assert current_input_hash(mid, inputs) is None


@pytest.fixture
def batch(tmp_path, inputs, monkeypatch):
    inputs["matches"] = inputs["matches"][:1]
    for name, path in (("projects", "data/projects/desc.json"), ("locations", "data/locations/locations.json"),
                       ("sources", "data/sources/sources.json"), ("matches", "data/matches/matches.json")):
        write_json(tmp_path / path, inputs[name])
    write_json(tmp_path / "data/projects/gpc.json", [])
    monkeypatch.setattr(runner, "verify_sources", lambda *_: None)
    return tmp_path


class Fake:
    def __init__(self, actions):
        self.actions = list(actions)
        self.calls = []

    def generate(self, bundle, repair):
        self.calls.append(copy.deepcopy(repair))
        action = self.actions.pop(0) if self.actions else json.dumps(clean(bundle))
        if isinstance(action, Exception):
            raise action
        return action


def run_live(root, fake):
    return runner.run_batch(repo_root=root, live=True, model="gemini-synthetic-test", transport=fake, sleep=lambda _: None)


def test_offline_preserves_passed_bytes_and_never_calls(batch, monkeypatch):
    artifact = batch / "data/briefs/briefs.json"
    write_json(artifact, [{"_id": "historical-evidence", "validation": "passed", "input_hash": "old"}])
    original = artifact.read_bytes()
    fake = Fake([])
    monkeypatch.setenv("GEMINI_MODEL", "gemini-present")
    monkeypatch.setenv("GEMINI_API_KEY", "not-used")
    result = runner.run_batch(repo_root=batch, transport=fake)
    assert result["calls"] == 0 and result["model"] is None and result["status"] == "unavailable"
    assert artifact.read_bytes() == original and fake.calls == []


def test_unconfigured_live_stays_unavailable(batch, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert runner.run_batch(repo_root=batch, live=True)["model"] is None


def test_one_regeneration_then_rejected_with_actual_metadata(batch):
    fake = Fake(["{}", "{}"])
    result = run_live(batch, fake)
    assert result["calls"] == 2 and result["rejected"] == 1
    [record] = load_json(batch / "data/briefs/briefs.json")
    assert record["validation"] == "rejected" and record["model"] == "gemini-synthetic-test"
    assert record["schema_version"] == runner.SCHEMA_VERSION
    assert record["generated_at"].endswith("Z") and fake.calls[1] == ["invalid_response_shape"]


def test_clean_regeneration_and_revalidated_cache(batch):
    result = run_live(batch, Fake(["{}"]))
    assert result["calls"] == 2 and result["passed"] == 1
    original = (batch / "data/briefs/briefs.json").read_bytes()
    fake = Fake([])
    cached = run_live(batch, fake)
    assert cached["calls"] == 0 and cached["cache_hits"] == 1 and not fake.calls
    assert (batch / "data/briefs/briefs.json").read_bytes() == original
    cache_path = next((batch / "data/briefs/cache").glob("*.json"))
    cache = load_json(cache_path)
    response = json.loads(cache["response"])
    response["supported_facts"][0]["text"] = "Unsupported 999999 miles."
    cache["response"] = json.dumps(response)
    cache["response_sha256"] = hashlib.sha256(cache["response"].encode()).hexdigest()
    write_json(cache_path, cache)
    assert run_live(batch, Fake([]))["calls"] == 1  # Even self-consistent forged cache is revalidated.


@pytest.mark.parametrize("failure,expected", [(TransportFailure("rate_limit", True), 3),
                                             (TransportFailure("permission_denied", False), 1)])
def test_bounded_retry_and_failure_preserves_artifact(batch, failure, expected):
    path = batch / "data/briefs/briefs.json"
    write_json(path, [{"_id": "old", "validation": "passed"}])
    original = path.read_bytes()
    result = run_live(batch, Fake([failure] * 3))
    assert result["calls"] == expected and result["status"] == "partial"
    assert path.read_bytes() == original


def test_cache_metadata_binds_model_prompt_schema_and_hash(bundle):
    meta = runner.metadata(bundle, "gemini-a")
    for field in meta:
        assert canonical_hash(meta) != canonical_hash({**meta, field: "changed"})


def test_selection_excludes_tentative_and_prefers_future(inputs):
    selected = runner.select_matches(inputs["matches"])
    eligible = [m for m in inputs["matches"] if m["view"] != "tentative"]
    assert len(selected) == min(15, len(eligible)) > 0
    assert all(m["view"] != "tentative" for m in selected)
    other = copy.deepcopy(inputs["matches"][-1])
    other.update(_id="synthetic-future", view="future", rank=999)
    assert runner.select_matches([*inputs["matches"], other])[0]["_id"] == "synthetic-future"


def test_sources_are_checked_before_cache_or_network(batch, monkeypatch):
    def bad(*_):
        raise ValueError("source_hash_changed")
    monkeypatch.setattr(runner, "verify_sources", bad)
    fake = Fake([])
    with pytest.raises(ValueError, match="source_hash_changed"):
        run_live(batch, fake)
    assert not fake.calls
