"""F45: TPPL endpoint cells, year/status mapping, the C38 operator guard, and the committed Southwest release."""

from common import REPO_ROOT, load_json
from national.build import OUTPUTS, _coverage, validate_snapshot_values
from southwest.build import STATUS, endpoint, in_service, locate
from southwest.publish import apply_release


def facility(fid, name, lat, lon, operator=None, voltage=None):
    return {"id": fid, "name": name, "norm": name.upper(), "operator": operator, "voltage": voltage, "lat": lat, "lon": lon}


def test_endpoint_cells_name_a_facility_or_nothing():
    assert endpoint("Harris Substation 230 kV Substation") == "Harris"
    assert endpoint("North Loop 138-kV bus") == "North Loop"
    assert endpoint("Santa Rita (formerly Hartt) 138 kV Substation") == "Santa Rita"
    assert endpoint("New Copper World 138 kV Substation") == "Copper World"
    assert endpoint("Vail 345 kV Bus") == "Vail"
    assert endpoint("Orchard Susbtation") == "Orchard"  # the source's spelling
    for description in ("TBD", "N/A", None, "Freedom-Panda 230kV line near the existing Jojoba 500kV switchyard",
                        "A new or existing substation in or around the Phoenix Metropolitan area"):
        assert endpoint(description) is None


def test_year_and_status_are_as_entered():
    assert in_service(2028) == {"raw": "2028", "value": "2028", "precision": "year"}
    assert in_service("TBD") == {"raw": "TBD", "value": None, "precision": "unknown"}
    assert in_service("In-service") == {"raw": "In-service", "value": None, "precision": "unknown"}
    assert STATUS["withdrawn"] == "cancelled" and STATUS["conceptual"] == "proposed"


def test_endpoints_locate_with_the_operator_guard():
    row = {"Sponsor": "Tucson Electric Power", "Voltage": "138 kV", "_usps": "AZ",
           "Origin": "Vail 345 kV Bus", "Termination": "Vail 138 kV Bus"}
    vail = [facility("way/1", "Vail Substation", 32.05, -110.7, "Tucson Electric Power")]
    center, candidate = locate(row, vail)
    assert candidate["kind"] == "site" and center["basis"] == "source_point" and candidate["tier"] == "candidate"
    # Another utility's same-name facility is rejected even when it is the only one in the state.
    aps = [facility("way/2", "Vail Substation", 32.05, -110.7, "Arizona Public Service")]
    center, candidate = locate(row, aps)
    assert center is None and candidate["endpoints"][0]["status"] == "operator_conflict"
    line = row | {"Origin": "Irvington 138 kV Substation", "Termination": "Sonoran 138 kV Substation"}
    two = [facility("way/3", "Irvington", 32.16, -110.9), facility("way/4", "Sonoran", 32.0, -110.9)]
    center, candidate = locate(line, two)
    assert center["basis"] == "two" and candidate["tier"] == "candidate_unique_name"
    assert abs(center["lat"] - 32.08) < 1e-6
    center, candidate = locate(line, two[:1])
    assert center["basis"] == "one"  # the mission's partial: one located endpoint


def test_committed_release_appends_unreviewed_points_only():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = apply_release(base, REPO_ROOT)
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "southwest" / "releases" / "active.json")
    added = [p for p in snapshot["projects"] if p["source_id"] in {s["_id"] for s in load_json(
        REPO_ROOT / "data" / "southwest" / "sources.json")}]
    assert len(added) == release["expected_counts"]["projects"]
    located = [p for p in added if p["center"]]
    assert all(p["location_review"] == "unreviewed" for p in located)
    assert all(p["location_review"] == "unlocated" for p in added if not p["center"])
    assert snapshot["coverage"]["southwest"]["independently_confirmed_projects"] == 0
    # C42's ask: History draws located projects with a dated event, Overlaps the located unbuilt ones.
    assert sum(any(e["date"] for e in p["project_events"]) for p in located) >= 100
    assert sum(p["status_group"] not in {"in_service", "cancelled"} for p in located) >= 100
    assert {p["states"][0] for p in located} >= {"04", "08", "35", "32", "49"}
