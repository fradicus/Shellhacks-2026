"""F49: the quote check, date precision, the antimeridian center check, and the committed Alaska/Hawaii release."""

import pytest

from akhi.build import check_event, check_quotes, norm, with_aliases
from akhi.publish import apply_release, inside_bounds
from common import REPO_ROOT, load_json
from national.build import OUTPUTS, _coverage, validate_snapshot_values


def test_a_quote_must_be_on_its_cited_page():
    docs = {"doc": [norm("Page one says nothing."), norm("Waipiʻo  Tsf 3 (Docket No.\n2023-0303)")]}
    check_quotes("x", {"source": "doc", "page": 2, "quotes": ["waipi'o tsf 3 (docket no. 2023-0303)"]}, docs)
    check_quotes("x", {"source": "doc", "page": None, "quotes": ["Page one says"]}, docs)
    with pytest.raises(ValueError, match="quote not in doc p.1"):
        check_quotes("x", {"source": "doc", "page": 1, "quotes": ["Tsf 3"]}, docs)
    with pytest.raises(ValueError, match="quote not in doc"):
        check_quotes("x", {"source": "doc", "quotes": ["in service 2027"]}, docs)


def test_event_dates_keep_the_stated_precision():
    check_event("p", {"type": "planned_milestone", "date": "2027-04", "precision": "month"})
    check_event("p", {"type": "in_service", "date": None, "precision": "unknown"})
    for bad in ({"type": "completion", "date": "2023", "precision": "day"},
                {"type": "completion", "date": "2023-12-15", "precision": "year"},
                {"type": "award", "date": "2024", "precision": "year"}):
        with pytest.raises(ValueError):
            check_event("p", bad)


def test_osm_parenthetical_abbreviation_is_an_alias():
    ceip = {"id": "way/1", "name": "Campbell Estate Industrial Park (CEIP) Substation", "lat": 21.3, "lon": -158.1}
    names = [f["name"] for f in with_aliases([ceip])]
    assert names == [ceip["name"], "CEIP Substation"]


def test_alaska_bounds_cross_the_antimeridian():
    states = {s["usps"]: s["bounds"] for s in load_json(REPO_ROOT / "data" / "national" / "geography.json")["states"]}
    alaska, hawaii = states["AK"], states["HI"]
    assert alaska["west"] > alaska["east"]  # why the CONUS-style check rejects every Alaska point
    assert inside_bounds(60.47, -149.75, alaska)  # Quartz Creek
    assert inside_bounds(52.9, 173.2, alaska)  # Attu, west of 180
    assert not inside_bounds(60.47, 150.0, alaska)
    assert not inside_bounds(21.3, -157.9, alaska)
    assert inside_bounds(21.3, -157.9, hawaii) and not inside_bounds(60.47, -149.75, hawaii)


def test_committed_release_appends_unreviewed_points_only():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = apply_release(base, REPO_ROOT)
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    assert validate_snapshot_values(snapshot) == []
    ours = {s["_id"] for s in load_json(REPO_ROOT / "data" / "akhi" / "sources.json")}
    added = [p for p in snapshot["projects"] if p["source_id"] in ours]
    release = load_json(REPO_ROOT / "data" / "akhi" / "releases" / "active.json")
    assert len(added) == release["expected_counts"]["projects"]
    located = [p for p in added if p["center"]]
    assert all(p["location_review"] == "unreviewed" for p in located)
    assert all(p["location_review"] == "unlocated" for p in added if not p["center"])
    assert {p["states"][0] for p in located} == {"02", "15"}
    assert snapshot["coverage"]["akhi"]["independently_confirmed_projects"] == 0
