"""F50: TPPL endpoints, progress-report verification and dates, and the committed release on the base snapshot."""

import pytest

from common import REPO_ROOT, load_json
from interiorwest import apr
from interiorwest.build import endpoints, locate
from interiorwest.publish import apply_release
from national.build import OUTPUTS, _coverage, validate_snapshot_values


def row(**cells):
    return {"projectid": 1, "Sponsor": "Cheyenne Light Fuel and Power", "ProjectName": "Orchard Valley 115 kV Substation",
            "Origin": "Cheyenne, WY", "Termination": "Cheyenne, WY", "Voltage": "115", "StateTraversed": "Wyoming",
            "_row": 2} | cells


def test_endpoints_prefer_origin_termination_then_project_name():
    assert endpoints(row()) == ("site", ["Orchard Valley"], "project_name")
    assert endpoints(row(ProjectName="Bison - Orchard Valley 115 kV Line", Origin="Bison 115 kV Substation",
                         Termination="Orchard Valley 115 kV Substation")) == (
        "line", ["Bison", "Orchard Valley"], "origin_termination")
    # A generator tied into a line names no facility of its own.
    assert endpoints(row(ProjectName="CLPT G20 365 MW Solar/BESS", Origin="Sweetgrass – Bluffs 230 kV Line",
                         Termination="NA"))[0] is None


def test_cheyenne_light_operator_corroborates_and_guards():
    site = {"id": "way/1", "name": "Orchard Valley Substation", "norm": "ORCHARD VALLEY", "voltage": None,
            "lat": 41.1, "lon": -104.8}
    center, block = locate(row(), "WY", [site | {"operator": "Cheyenne Light Fuel and Power"}])
    assert center["basis"] == "source_point" and block["endpoints"][0]["corroboration"] == ["operator"]
    assert locate(row(), "WY", [site | {"operator": "Western Area Power Administration"}])[0] is None


def test_committed_release_appends_unreviewed_candidates_in_their_states():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = apply_release(base, REPO_ROOT)
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "interiorwest" / "releases" / "active.json")
    released = {s["_id"] for s in load_json(REPO_ROOT / "data" / "interiorwest" / "sources.json")}
    added = [p for p in snapshot["projects"] if p["source_id"] in released]
    assert len(added) == release["expected_counts"]["projects"]
    assert all(set(p["states"]) <= {"56", "32", "49", "16", "30"} for p in added)
    assert all(p["location_review"] == ("unreviewed" if p["center"] else "unlocated") for p in added)
    assert snapshot["coverage"]["interiorwest"]["independently_confirmed_projects"] == 0
    assert not {p["_id"] for p in added} & apr.published_ids()


def test_report_dates_keep_their_precision():
    assert apr.in_service("June 30, 2028")["value"] == "2028-06-30"
    assert apr.in_service("December 2026") == {"raw": "December 2026", "value": "2026-12", "precision": "month"}
    assert apr.in_service("Q4 2032")["value"] == "2032" and apr.in_service("end of 2027")["precision"] == "year"
    for hedged in ("2036 (earliest)", "no earlier than 2027", "2028 or later", "12/2027 January 2028", None):
        assert apr.in_service(hedged)["value"] is None
    assert apr.status_group("placed in service", apr.in_service("December 2024"), "2026-09-27") == "in_service"
    assert apr.status_group("energized", apr.in_service("December 2035"), "2026-09-27") == "planned"


def test_rows_must_be_on_their_cited_page():
    row = {"page": 1, "quote": "Lazy 5 120 kV Substation", "name": "Lazy 5", "facilities": ["Lazy 5"],
           "in_service_raw": "January 2029", "status_raw": None}
    apr.verify("f", 1, row, {1: "the Lazy 5 120 kV Substation is new", 2: "ISD January 2029"})
    with pytest.raises(SystemExit):
        apr.verify("f", 1, row | {"quote": "Lazy 6 120 kV Substation"}, {1: "the Lazy 5 120 kV Substation"})


def test_territory_search_needs_corroboration():
    row = {"owner": "NV Energy", "voltages_kv": [120], "kind": "site", "facilities": ["Peavine"], "states": []}
    bare = {"id": "way/1", "name": "Peavine Substation", "norm": "PEAVINE", "voltage": None, "operator": None,
            "state": "NV", "lat": 39.6, "lon": -119.9}
    assert apr.locate(row, ["NV"], {"NV": [bare]})[0] is None
    assert apr.locate(row, ["NV"], {"NV": [bare | {"operator": "NV Energy"}]})[0]["basis"] == "source_point"
    assert apr.locate(row | {"states": ["NV"]}, ["NV"], {"NV": [bare]})[0] is not None  # stated state: C33 name-only
