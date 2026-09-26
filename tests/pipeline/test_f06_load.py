"""F06 loader: validation, locations->projects join, dataset staging, pointer flip, idempotence (mongomock)."""

import hashlib
import json
from pathlib import Path

import mongomock
import pytest

from common import REPO_ROOT, load_json
from load.__main__ import load
from load.build import collect, join_projects, stage
from load.review_subjects import FINGERPRINT_VERSION, current_subjects, subject_hash, supporting_endpoints

FIX = REPO_ROOT / "data/fixtures"


def write(root: Path, rel: str, obj) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


@pytest.fixture
def data_root(tmp_path):
    """A data/ tree built from the golden fixtures, in the folders the producing features own."""
    projects = [{k: v for k, v in p.items() if k not in ("center", "geo", "location_confidence")}
                for p in load_json(FIX / "projects.json")]
    write(tmp_path, "data/sources/sources.json", load_json(FIX / "sources.json"))
    write(tmp_path, "data/projects/desc.json", [p for p in projects if p["utility"] == "DESC"])
    write(tmp_path, "data/projects/gpc.json", [p for p in projects if p["utility"] == "GPC"])
    write(tmp_path, "data/locations/locations.json", [{k: v for k, v in loc.items() if k != "_id"}
                                                      for loc in load_json(FIX / "locations.json")])
    write(tmp_path, "data/matches/matches.json", load_json(FIX / "matches.json"))
    write(tmp_path, "data/matches/summary.json", {"pairs_evaluated": 25})
    write(tmp_path, "data/versions/versions.json", load_json(FIX / "version_changes.json"))
    write(tmp_path, "data/fixtures/matches.json", [{"not": "loaded"}])
    write(tmp_path, "data/osm/substations.json", [{"not": "loaded"}])
    return tmp_path


def test_collect_reads_owned_folders_only(data_root):
    records, errors, skipped = collect(data_root)
    assert errors == []
    assert skipped == ["data/matches/summary.json"]
    assert len(records["projects"]) == 10 and len(records["locations"]) == 20  # 2 endpoints x 10, incl. 4 unlocated
    assert len(records["matches"]) == 6 and len(records["version_changes"]) == 1


def test_join_recomputes_fixture_centers(data_root):
    records, _, _ = collect(data_root)
    joined = {p["project_key"]: p for p in join_projects(records["projects"], records["locations"])}
    for p in load_json(FIX / "projects.json"):
        j = joined[p["project_key"]]
        assert j["center"] == pytest.approx(p["center"]) if p["center"] else j["center"] is None
        assert j["geo"] == p["geo"]
        assert j["location_confidence"] == p["location_confidence"]
    one = joined["DESC:DESC_1"]  # Hooks Sub has no coordinates in the sample
    assert one["center"]["basis"] == "one" and len(one["endpoints"]) == 2


def test_invalid_record_reported(data_root):
    write(data_root, "data/matches/bad.json", [{"_id": "x", "a": "A", "b": "B", "distance_mi": 30}])
    _, errors, _ = collect(data_root)
    assert any("data/matches/bad.json[0]" in e for e in errors)


def test_duplicate_ids_reported(data_root):
    write(data_root, "data/versions/dup.json", load_json(FIX / "version_changes.json"))
    _, errors, _ = collect(data_root)
    assert any("duplicate _id" in e for e in errors)


def test_stage_namespaces_ids(data_root):
    records, _, _ = collect(data_root)
    staged = stage(records, "abc")
    m = staged["matches"][0]
    assert m["_id"].startswith("abc:") and m["id"] == m["_id"][4:] and m["dataset"] == "abc"
    assert "locations" not in staged


def test_load_flips_pointer_and_is_idempotent(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "sha1") == 0
    snapshot = {c: sorted(d["_id"] for d in db[c].find()) for c in ("projects", "matches", "version_changes")}
    assert db.meta.find_one({"_id": "active"})["dataset"] == "sha1"
    assert load(db, records, errors, "sha1") == 0
    assert {c: sorted(d["_id"] for d in db[c].find()) for c in snapshot} == snapshot
    assert db.meta.find_one({"_id": "active"})["previous"] is None
    assert db.runs.find_one({"_id": "load:sha1"})["status"] == "ok"


def test_new_dataset_keeps_previous_and_drops_older(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    for sha in ("s1", "s2", "s3"):
        assert load(db, records, errors, sha) == 0
    meta = db.meta.find_one({"_id": "active"})
    assert (meta["dataset"], meta["previous"]) == ("s3", "s2")
    assert sorted(db.matches.distinct("dataset")) == ["s2", "s3"]


def test_failed_validation_does_not_flip(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    load(db, records, errors, "good")
    write(data_root, "data/matches/bad.json", [{"_id": "x"}])
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "bad") == 1
    assert db.meta.find_one({"_id": "active"})["dataset"] == "good"
    assert db.runs.find_one({"_id": "load:bad"})["status"] == "failed"
    assert db.matches.count_documents({"dataset": "bad"}) == 0


class FailingInserts:
    """Wraps a mongomock db; insert_many on `coll` raises, like a dropped connection mid-load."""

    def __init__(self, db, coll):
        self._db, self._coll = db, coll

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __getitem__(self, name):
        c = self._db[name]
        if name != self._coll:
            return c

        class Broken:
            def __getattr__(self, attr):
                if attr == "insert_many":
                    def boom(*a, **k):
                        raise ConnectionError("simulated")
                    return boom
                return getattr(c, attr)

        return Broken()


def test_reloading_active_sha_is_a_no_op_even_if_writes_would_fail(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "sha1") == 0
    before = db.sources.count_documents({"dataset": "sha1"})
    assert load(FailingInserts(db, "sources"), records, errors, "sha1") == 0
    assert db.sources.count_documents({"dataset": "sha1"}) == before > 0
    assert db.meta.find_one({"_id": "active"})["dataset"] == "sha1"


def test_write_failure_keeps_served_dataset(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "sha1") == 0
    served = db.matches.count_documents({"dataset": "sha1"})
    assert load(FailingInserts(db, "sources"), records, errors, "sha2") == 1
    assert db.meta.find_one({"_id": "active"})["dataset"] == "sha1"
    assert db.matches.count_documents({"dataset": "sha1"}) == served
    run = db.runs.find_one({"_id": "load:sha2"})
    assert run["status"] == "failed" and "ConnectionError" in run["errors"][0]
    assert load(db, records, errors, "sha2") == 0  # a later retry of the failed sha still loads


def test_non_object_entries_are_errors_and_block_activation(data_root):
    write(data_root, "data/projects/mixed.json", [load_json(FIX / "projects.json")[0] | {"_id": "X@y"}, None])
    records, errors, skipped = collect(data_root)
    assert any("data/projects/mixed.json[1]: not a JSON object" in e for e in errors)
    assert "data/projects/mixed.json" not in skipped
    db = mongomock.MongoClient().db
    assert load(db, records, errors, "sha1") == 1
    assert db.meta.find_one({"_id": "active"}) is None


def test_filed_endpoints_kept_apart_from_locations(data_root):
    records, _, _ = collect(data_root)
    p = dict(records["projects"][0])
    p["endpoints"] = [{"name": "Queensboro", "raw": "Queensboro", "norm": "QUEENSBORO"}]
    [joined] = join_projects([p], [])
    assert joined["filed_endpoints"] == p["endpoints"] and "endpoints" not in joined
    [joined] = join_projects([p], [loc for loc in records["locations"] if loc["project_key"] == p["project_key"]])
    assert joined["filed_endpoints"][0]["name"] == "Queensboro"
    assert all("confidence" in e for e in joined["endpoints"])


# --- #35: at most one accepted location per endpoint, endpoint_index 0 or 1 ------------------------------------------

def synth_loc(index, lon, confidence="high", n=0):
    """Clearly synthetic coordinates on the equator; never real endpoint data."""
    return {"_id": f"qa#{index}#{n}", "project_key": "DESC:DESC_3", "endpoint_index": index, "name": "Synthetic QA",
            "confidence": confidence, "evidence": "synthetic test coordinate", "lat": 0.0, "lon": lon}


@pytest.fixture
def qa_root(tmp_path):
    [p] = [p for p in load_json(FIX / "projects.json") if p["project_key"] == "DESC:DESC_3"]
    write(tmp_path, "data/projects/qa.json", [{k: v for k, v in p.items() if k not in ("center", "geo")}])
    return tmp_path


BASE = [synth_loc(0, 0.0), synth_loc(1, 2.0)]


@pytest.mark.parametrize("locs, error", [
    (BASE, None),
    (BASE + [synth_loc(0, 4.0, n=1)], "2 accepted candidates for 'DESC:DESC_3@sperry-sample' endpoint 0"),
    (BASE + [synth_loc(2, 4.0)], "endpoint_index 2"),
    (BASE + [synth_loc(0, 4.0, "rejected", n=1)], None),  # F09 keeps rejected alternatives as evidence
    (BASE + [synth_loc(2, 4.0, "rejected")], None),
    ([synth_loc(0, 0.0), synth_loc(0, 2.0, "low", n=1)], "2 accepted candidates"),
])
def test_accepted_endpoint_candidates_are_unambiguous(qa_root, locs, error):
    write(qa_root, "data/locations/qa.json", locs)
    records, errors, _ = collect(qa_root)
    if error is None:
        assert errors == []
        [p] = join_projects(records["projects"], records["locations"])
        assert p["center"] == {"lat": 0.0, "lon": 1.0, "basis": "two"} and len(p["endpoints"]) == len(locs)
    else:
        assert len(errors) == 1 and error in errors[0]


def test_ambiguous_endpoints_block_activation_and_keep_previous(qa_root):
    db = mongomock.MongoClient().db
    write(qa_root, "data/locations/qa.json", BASE)
    assert load(db, *collect(qa_root)[:2], "good") == 0
    write(qa_root, "data/locations/qa.json", BASE + [synth_loc(0, 4.0, n=1)])
    assert load(db, *collect(qa_root)[:2], "bad") == 1
    assert db.meta.find_one({"_id": "active"})["dataset"] == "good"
    assert db.projects.find_one({"dataset": "good"})["center"]["lon"] == 1.0


# --- #47: a location is evidence for one filing version, never for every version of its project_key ------------

def versions(active_source="v2"):
    """Two filing versions of one synthetic project; only `active_source` is active. Filed names stay on both."""
    [p] = [p for p in load_json(FIX / "projects.json") if p["project_key"] == "DESC:DESC_3"]
    base = {k: v for k, v in p.items() if k not in ("center", "geo", "location_confidence")}
    return [{**base, "_id": f"DESC:DESC_3@{sid}", "active": sid == active_source,
             "source": {**base["source"], "source_id": sid}, "endpoints": [{"name": "Filed", "norm": "FILED",
                                                                            "raw": "Filed Sub"}]}
            for sid in ("v1", "v2")]


def bound(index, lon, **fields):
    return {**synth_loc(index, lon), "_id": f"qa#{index}#{fields.get('project_id', fields.get('source_id', 'legacy'))}",
            **fields}


def test_location_joins_only_its_declared_filing_version():
    locs = [bound(0, 0.0, project_id="DESC:DESC_3@v2", source_id="v2"), bound(1, 2.0, project_id="DESC:DESC_3@v2")]
    for order in (versions(), versions()[::-1]):  # record order can't change the binding
        joined = {p["_id"]: p for p in join_projects(order, locs)}
        assert joined["DESC:DESC_3@v2"]["center"] == {"lat": 0.0, "lon": 1.0, "basis": "two"}
        old = joined["DESC:DESC_3@v1"]
        assert old["center"] is None and old["geo"] is None and "endpoints" not in old
        assert old["filed_endpoints"][0]["name"] == "Filed"


def test_source_id_alone_names_the_version_and_inactive_versions_can_hold_evidence():
    [old, new] = join_projects(versions(), [bound(0, 0.0, source_id="v1")])
    assert old["_id"] == "DESC:DESC_3@v1" and old["center"]["basis"] == "one" and new["center"] is None


def test_legacy_location_binds_to_the_only_active_version(tmp_path):
    write(tmp_path, "data/projects/qa.json", versions())
    write(tmp_path, "data/locations/qa.json", [synth_loc(0, 0.0)])  # no project_id / source_id, e.g. the fixtures
    records, errors, _ = collect(tmp_path)
    assert errors == [] and records["locations"][0]["project_id"] == "DESC:DESC_3@v2"
    joined = {p["_id"]: p for p in join_projects(records["projects"], records["locations"])}
    assert joined["DESC:DESC_3@v2"]["center"] is not None and joined["DESC:DESC_3@v1"]["center"] is None


@pytest.mark.parametrize("projects, loc, error", [
    (versions(), bound(0, 0.0, project_id="DESC:DESC_3@v9"), "unknown project 'DESC:DESC_3@v9'"),
    (versions(), bound(0, 0.0, project_id="DESC:DESC_3@v2", source_id="v1"), "contradicts project 'DESC:DESC_3@v2'"),
    (versions(), bound(0, 0.0, project_id="DESC:DESC_3@v2") | {"project_key": "DESC:OTHER"}, "contradicts project"),
    (versions(), bound(0, 0.0, source_id="v9"), "unknown project 'DESC:DESC_3@v9'"),
    ([{**v, "active": True} for v in versions()], synth_loc(0, 0.0), "has 2 active versions"),
    ([{**v, "active": False} for v in versions()], synth_loc(0, 0.0), "has 0 active versions"),
    ([], synth_loc(0, 0.0), "has 0 active versions"),
])
def test_inconsistent_or_unplaceable_binding_blocks_activation(tmp_path, projects, loc, error):
    write(tmp_path, "data/projects/qa.json", projects)
    write(tmp_path, "data/locations/qa.json", [loc])
    records, errors, _ = collect(tmp_path)
    assert len(errors) == 1 and error in errors[0] and records["locations"] == []
    assert all(p["center"] is None for p in join_projects(records["projects"], [loc]))
    assert load(mongomock.MongoClient().db, records, errors, "bad") == 1


def test_accepted_uniqueness_is_per_filing_version(tmp_path):
    write(tmp_path, "data/projects/qa.json", versions())
    write(tmp_path, "data/locations/qa.json", [bound(0, 0.0, source_id="v1"), bound(0, 2.0, source_id="v2")])
    assert collect(tmp_path)[1] == []


# --- #38 / #57: audit verdicts set match.review_state only while their fingerprint is current ----------------------

def subjects_of(records):
    return current_subjects({**records, "projects": join_projects(records["projects"], records["locations"])})


def review(verdict, at, record_id, subject_type="pair", subjects=None, stale=False):
    """A review bound to the current subject (or deliberately stale, or unbound when subjects is None)."""
    r = {"_id": f"r-{subject_type}-{record_id}-{verdict}-{at}-{stale}", "record_id": record_id, "verdict": verdict,
         "reason": "synthetic", "reviewer": "qa", "at": at}
    if subjects is not None:
        h = subject_hash(subjects[(subject_type, record_id)])
        r |= {"subject_type": subject_type, "fingerprint_version": FINGERPRINT_VERSION,
              "subject_hash": h[::-1] if stale else h}
    return r


def endpoint_confirmations(subjects, pair_id, at="2026-09-26T09:00:00Z", verdict="confirmed", skip=()):
    return [review(verdict, at, e, "endpoint", subjects) for e in supporting_endpoints(subjects[("pair", pair_id)])
            if e not in skip]


def staged_state(records, reviews):
    states = set()
    for order in (reviews, reviews[::-1]):  # append-only reviews: file order must not matter
        [m] = [m for m in stage({**records, "reviews": order}, "ds")["matches"] if m["id"] == records["matches"][0]["_id"]]
        states.add(m["review_state"])
    assert len(states) == 1
    return states.pop()


T1, T2 = "2026-09-26T10:00:00Z", "2026-09-26T11:00:00Z"


def test_pair_and_endpoint_subjects_exist_for_fixture_data(data_root):
    records, _, _ = collect(data_root)
    subs = subjects_of(records)
    pair = records["matches"][0]["_id"]
    assert len(supporting_endpoints(subs[("pair", pair)])) == 3  # GPC_2 has one located endpoint
    assert all(("endpoint", e) in subs for e in supporting_endpoints(subs[("pair", pair)]))
    # canonical JSON, so the hash is stable across machines and TypeScript/Python reimplementations
    assert subject_hash({"b": 1, "a": [1.5, None, "é"]}) == "10c71012fb391fead6e4d481b11c8b16696561c1fd93a68cca35fa194c3aa97d"


@pytest.mark.parametrize("build, state", [
    (lambda s, p: [], "needs_review"),
    (lambda s, p: [review("confirmed", T1, p, subjects=s)] + endpoint_confirmations(s, p), "confirmed"),
    (lambda s, p: [review("confirmed", T1, p, subjects=s)], "needs_review"),  # endpoints not yet reviewed
    (lambda s, p: [review("confirmed", T1, p, subjects=s)] + endpoint_confirmations(s, p, skip=[
        supporting_endpoints(s[("pair", p)])[0]]), "needs_review"),
    (lambda s, p: [review("confirmed", T1, p, subjects=s)] + endpoint_confirmations(s, p)
     + endpoint_confirmations(s, p, at=T2, verdict="downgraded")[:1], "needs_review"),  # an endpoint downgrade
    (lambda s, p: [review("confirmed", T1, p, subjects=s), review("downgraded", T2, p, subjects=s)]
     + endpoint_confirmations(s, p), "rejected"),
    (lambda s, p: [review("downgraded", T1, p, subjects=s), review("confirmed", T2, p, subjects=s)]
     + endpoint_confirmations(s, p), "confirmed"),
    (lambda s, p: [review("rejected", T1, p, subjects=s)], "rejected"),
    # the same instant written with different offsets: conflicting decisions stay conservative
    (lambda s, p: [review("confirmed", T1, p, subjects=s), review("downgraded", "2026-09-26T06:00:00-04:00", p,
                                                                   subjects=s)], "rejected"),
    # 10:00-04:00 is 14:00Z, later than 13:00Z
    (lambda s, p: [review("downgraded", "2026-09-26T13:00:00Z", p, subjects=s),
                   review("confirmed", "2026-09-26T10:00:00-04:00", p, subjects=s)] + endpoint_confirmations(s, p),
     "confirmed"),
    (lambda s, p: [review("confirmed", T1, p)] + endpoint_confirmations(s, p), "needs_review"),  # legacy: no binding
    (lambda s, p: [review("confirmed", T1, p, subjects=s, stale=True)] + endpoint_confirmations(s, p), "needs_review"),
    (lambda s, p: [review("rejected", T1, p, subjects=s, stale=True)], "needs_review"),
    # newest decision stale: no fallback to the older, still-valid confirmation
    (lambda s, p: [review("confirmed", T1, p, subjects=s), review("confirmed", T2, p, subjects=s, stale=True)]
     + endpoint_confirmations(s, p), "needs_review"),
    (lambda s, p: [review("confirmed", T1, "DESC:DESC_1__GPC:GPC_1", subjects=s)], "needs_review"),  # another pair
    (lambda s, p: [review("note", T1, p, subjects=s)] + endpoint_confirmations(s, p), "needs_review"),
    (lambda s, p: [review("confirmed", "2026-09-26T10:00:00", p, subjects=s)] + endpoint_confirmations(s, p),
     "needs_review"),  # no timezone: can't be ordered
])
def test_audit_verdicts_apply_to_review_state(data_root, build, state):
    records, _, _ = collect(data_root)
    subs = subjects_of(records)
    assert staged_state(records, build(subs, records["matches"][0]["_id"])) == state


@pytest.mark.parametrize("change", [
    lambda r: edit_first_project(r, lambda p: p | {"in_service": {**p["in_service"], "date": "2030-01-01"}}),
    lambda r: edit_first_match(r, distance_mi=7.5),
    lambda r: {**r, "locations": [loc | {"lon": loc["lon"] + 0.01} if loc.get("lon") is not None else loc
                                  for loc in r["locations"]]},
    lambda r: {**r, "sources": [s | {"sha256": "0" * 64} for s in r["sources"]]},
])
def test_confirmation_lapses_when_its_facts_change(data_root, change):
    records, _, _ = collect(data_root)
    subs, pair = subjects_of(records), records["matches"][0]["_id"]
    reviews = [review("confirmed", T1, pair, subjects=subs)] + endpoint_confirmations(subs, pair)
    assert staged_state(records, reviews) == "confirmed"
    assert staged_state(change(records), reviews) == "needs_review"
    unrelated = {**records, "matches": [records["matches"][0] | {"rank": 99, "review_state": "rejected"},
                                        *records["matches"][1:]]}
    assert staged_state(unrelated, reviews) == "confirmed"  # rank and producer state are not facts under review


def test_reviews_are_preserved_and_producer_records_untouched(data_root):
    records, _, _ = collect(data_root)
    match = records["matches"][0]
    reviews = [review("confirmed", T1, match["_id"]), review("note", "2026-09-26T09:00:00Z", match["_id"])]
    staged = stage({**records, "reviews": reviews}, "ds")
    assert [r["id"] for r in staged["reviews"]] == [r["_id"] for r in reviews]
    assert match["review_state"] == "needs_review"


# --- #43: a passed brief is served only while its input_hash matches the current facts -------------------------------

def fake_hash(match_id, ready):
    """Stand-in for F12's builder: hashes the match (minus review_state) and both joined projects."""
    [m] = [{k: v for k, v in m.items() if k != "review_state"} for m in ready["matches"] if m["_id"] == match_id]
    ps = sorted((p for p in ready["projects"] if p["project_key"] in (m["a"], m["b"])), key=lambda p: p["_id"])
    return hashlib.sha256(json.dumps([m, ps], sort_keys=True).encode()).hexdigest()


def make_brief(records, validation="passed"):
    mid = records["matches"][0]["_id"]
    ready = {"matches": records["matches"], "projects": join_projects(records["projects"], records["locations"])}
    return {"_id": f"brief-{validation}", "match_id": mid, "input_hash": fake_hash(mid, ready), "model": "m",
            "prompt_version": "p", "generated_at": "2026-09-26T10:00:00Z", "supported_facts": [],
            "possible_shared_activities": [], "questions": [], "limitations": [], "validation": validation}


def staged_brief(records, b, hash_fn=fake_hash):
    [out] = stage({**records, "briefs": [b]}, "ds", hash_fn)["briefs"]
    return out


def edit_first_project(records, fn):
    key = records["matches"][0]["a"]
    return {**records, "projects": [fn(p) if p["project_key"] == key else p for p in records["projects"]]}


def edit_first_match(records, **kw):
    return {**records, "matches": [records["matches"][0] | kw, *records["matches"][1:]]}


def test_unchanged_input_keeps_passed_brief(data_root):
    records, _, _ = collect(data_root)
    b = staged_brief(records, make_brief(records))
    assert b["validation"] == "passed" and "source_validation" not in b


@pytest.mark.parametrize("change", [
    lambda r: edit_first_project(r, lambda p: p | {"in_service": {**p["in_service"], "date": "2030-01-01"}}),
    lambda r: edit_first_project(r, lambda p: p | {"description": "changed description"}),
    lambda r: edit_first_match(r, distance_mi=7.5),  # location-derived distance
    lambda r: edit_first_match(r, time_gap_days=1, band=1),
    lambda r: {**r, "locations": [loc | {"lon": loc["lon"] + 0.01} if loc.get("lon") is not None else loc
                                  for loc in r["locations"]]},
])
def test_changed_input_makes_passed_brief_ineligible(data_root, change):
    records, _, _ = collect(data_root)
    b = staged_brief(change(records), make_brief(records))
    assert (b["validation"], b["source_validation"]) == ("rejected", "passed")
    assert b["rejection_reason"] == "stale: input facts changed since generation"


def test_unverifiable_or_orphaned_briefs_fail_closed(data_root):
    records, _, _ = collect(data_root)
    assert staged_brief(records, make_brief(records), None)["rejection_reason"].startswith("unverified")
    orphan = make_brief(records) | {"match_id": "X__Y"}
    assert staged_brief(records, orphan)["rejection_reason"] == "stale: match is not in this dataset"
    rejected = make_brief(records, "rejected") | {"rejection_reason": "number not in input"}
    assert staged_brief(records, rejected) == {**rejected, "_id": "ds:brief-rejected", "id": "brief-rejected",
                                               "dataset": "ds"}
