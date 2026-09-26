"""Every UI fixture validates against its schema, and the fixtures agree with the canonical matcher."""

import pytest

from common import REPO_ROOT, load_json, norm_name, validate
from matches.core import overlaps, priority_sort

FIX = REPO_ROOT / "data/fixtures"
SCHEMA_OF = {
    "sources": "source", "projects": "project", "locations": "location", "matches": "match", "version_changes": "version_change",
    "briefs": "brief", "extractions": "extraction", "reviews": "review", "runs": "run", "coverage": "coverage",
}


@pytest.mark.parametrize("name", sorted(SCHEMA_OF))
def test_fixture_validates(name):
    records = load_json(FIX / f"{name}.json")
    assert isinstance(records, list)
    for r in records:
        validate(r, SCHEMA_OF[name])


def test_match_fixture_is_core_output():
    projects = load_json(FIX / "projects.json")
    stored = load_json(FIX / "matches.json")
    fresh = priority_sort(overlaps(projects, stored[0]["analysis_date"]))
    assert [m["_id"] for m in stored] == [m["_id"] for m in fresh]
    assert all(m["view"] == "historical" for m in stored)


def test_version_change_fixture():
    [vc] = load_json(FIX / "version_changes.json")
    assert (vc["project_key"], vc["old"], vc["new"]) == ("DESC:0139 M,N", "2024-12-31", "2026-05-31")


def test_schema_rejects_bad_match():
    bad = {"_id": "x", "a": "DESC:A", "b": "GPC:B", "distance_mi": 25.0, "time_gap_days": None, "band": 1,
           "rule_version": "r", "rank_version": "r", "analysis_date": "2026-09-26", "view": "future"}
    with pytest.raises(ValueError):
        validate(bad, "match")


def test_location_needs_coords_unless_rejected():
    loc = {"project_key": "DESC:A", "endpoint_index": 0, "name": "X", "confidence": "high", "evidence": "e"}
    with pytest.raises(ValueError):
        validate(loc, "location")
    validate(loc | {"confidence": "rejected"}, "location")


@pytest.mark.parametrize("field,value", [
    ("center", {"lat": 100.0, "lon": -81.0, "basis": "two"}),
    ("center", {"lat": 33.0, "lon": -181.0, "basis": "two"}),
    ("geo", {"type": "Point", "coordinates": [-81.0, 100.0]}),
    ("geo", {"type": "Point", "coordinates": [-81.0, 33.0, 5.0]}),
])
def test_project_coordinates_bounded(field, value):
    p = load_json(FIX / "projects.json")[0]
    validate(p, "project")
    with pytest.raises(ValueError):
        validate(p | {field: value}, "project")


def test_norm_name():
    assert norm_name("Thurmond Dam (USA) #5 Sub") == "THURMOND DAM"
    assert norm_name("EVANS PRIMARY") == "EVANS"
    assert norm_name("  Okatie   Substation ") == "OKATIE"
