"""F50: Wyoming TPPL endpoints and ProjectName fallback, and the committed release appended to the base snapshot."""

from common import REPO_ROOT, load_json
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
    added = [p for p in snapshot["projects"] if p["_id"].startswith("westconnect-tppl-2026-02-wy:")]
    assert len(added) == release["expected_counts"]["projects"]
    assert all(set(p["states"]) <= {"56", "32", "49", "16", "30"} for p in added)
    assert all(p["location_review"] == ("unreviewed" if p["center"] else "unlocated") for p in added)
    assert snapshot["coverage"]["interiorwest"]["independently_confirmed_projects"] == 0
