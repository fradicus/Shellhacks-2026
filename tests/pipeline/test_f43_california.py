"""F43: California name rules, the C33 loosening with its operator guard, and the committed CAISO release."""

from datetime import datetime

from california.caiso import date_of, match, named, status_group
from california.publish import apply_release
from common import REPO_ROOT, load_json
from national.build import OUTPUTS, _coverage, validate_snapshot_values


def facility(fid, name, lat, lon, operator=None, voltage=None):
    return {"id": fid, "name": name, "norm": name.upper(), "operator": operator, "voltage": voltage, "lat": lat, "lon": lon}


def test_california_name_forms():
    assert named("Ames 115 kV Short Circuit Mitigation")["names"] == ["Ames"]
    assert named("Gates 500 kV Dynamic Voltage Support (Orchard Substation)")["names"] == ["Orchard"]
    assert named("San Jose Area HVDC 500 kV Line (Metcalf – San Jose)") == {
        "kind": "line", "names": ["Metcalf", "San Jose"], "from": "name", "reason": None}
    assert named("TL695B Japanese Mesa-Talega Tap Reconductor")["names"] == ["Japanese Mesa", None]
    assert named("Santa Rosa 115 kV lines Reconductoring project")["kind"] is None  # lines, not a site
    assert "North" not in named("IV-North of Songs 500 kV line")["names"]


def test_unique_name_needs_no_conflicting_operator():
    keys = ["PACIFIC GAS"]
    lone = [facility("way/1", "Clear Lake Substation", 39.0, -122.8)]
    assert match("Clear Lake", lone, keys, set())["corroboration"] == ["unique_in_state"]
    other = [facility("way/2", "Estrella Substation", 34.0, -117.0, "Southern California Edison")]
    assert match("Estrella", other, keys, set())["status"] == "operator_conflict"
    twice = lone + [facility("way/3", "Clear Lake Substation", 37.0, -120.0)]
    assert match("Clear Lake", twice, keys, set())["status"] == "ambiguous"
    # Voltage alone does not outweigh another utility's name on the facility.
    sce = [facility("way/4", "Santa Rosa Substation", 33.9, -117.3, "Southern California Edison", "115000")]
    assert match("Santa Rosa", sce, keys, {115})["status"] == "operator_conflict"


def test_workbook_cells_and_statuses():
    assert date_of(datetime(2028, 2, 28)) == ("2028-02-28", "day")
    assert date_of(datetime(1933, 12, 1)) == (None, "unknown")  # source typo for 2033 stays unknown
    assert date_of(2027) == ("2027", "year")
    assert date_of("Earliest June-27; latest Dec-27") == (None, "unknown")
    assert status_group("In-Service") == status_group("Operational") == "in_service"
    assert status_group("In-Flight") == "planned" and status_group("Execution") == "under_construction"
    assert status_group("On Hold") == "unknown"


def test_committed_release_appends_unreviewed_candidates_only():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = apply_release(base, REPO_ROOT)
    # load_snapshot recounts coverage after each release; do the same before validating.
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "california" / "releases" / "active.json")
    added = [p for p in snapshot["projects"] if p["source_id"].startswith("caiso-")]
    assert len(added) == release["expected_counts"]["projects"]
    located = [p for p in added if p["center"]]
    assert all(p["location_review"] == "unreviewed" and p["states"] == ["06"] for p in located)
    assert all(p["location_review"] == "unlocated" for p in added if not p["center"])
    assert snapshot["coverage"]["california"]["independently_confirmed_projects"] == 0
    # The pins this rollout was asked for: History draws every located project with an event, Overlaps the unbuilt.
    assert sum(bool(p["project_events"]) for p in located) >= 100
    assert sum(p["status_group"] not in {"in_service", "cancelled"} for p in located) >= 100
