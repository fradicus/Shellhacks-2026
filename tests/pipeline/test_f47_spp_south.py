"""F47: SPP South scope, owner operator keys, and the committed release appended to the base snapshot."""

from datetime import datetime

from california.caiso import match
from common import REPO_ROOT, load_json
from national.build import OUTPUTS, _coverage, validate_snapshot_values
from sppsouth.build import OPERATOR_KEYS, project, published_uids, with_aliases
from sppsouth.publish import apply_release

ARTIFACT = {"url": "https://www.spp.org/x.zip", "sha256": "0" * 64, "retrieved_at": "2026-09-27T08:00:00Z"}


def facility(fid, name, lat, lon, operator=None, state="OK"):
    return {"id": fid, "name": name, "norm": name.upper(), "operator": operator, "voltage": None, "state": state,
            "lat": lat, "lon": lon}


def row(**cells):
    base = {"UID": 1, "PID": 2, "NTC ID": 3, "ProjectOwner": "OGE", "State(s)": "OK", "Project Name": "P",
            "Upgrade Name": "Calumet 138 kV Substation", "Project Type": "Regional Reliability",
            "Project Owner Indicated In-Service Date": datetime(2028, 6, 1), "Project Status": "On Schedule < 4",
            "Current Cost Estimate": None, "Voltages (kV)": "138", "From Bus Name": None, "To Bus Name": None,
            "Project Description/ Comments": None, "_sheet": "S", "_row": 9}
    return base | cells


def test_records_use_the_south_source_and_state_codes():
    record = project(row(**{"State(s)": "TX, NM"}), ARTIFACT, {})
    assert record["_id"] == "spp-qpt-2026q3-south:1" and record["states"] == ["35", "48"]
    assert [(e["type"], e["date"]) for e in record["project_events"]] == [("planned_milestone", "2028-06-01")]


def test_new_owner_keys_corroborate_and_guard():
    keys = OPERATOR_KEYS["OGE"]
    assert match("Calumet", [facility("way/1", "Calumet Substation", 35.6, -98.1, "OG&E")], keys, set()
                 )["corroboration"] == ["operator"]
    assert match("Calumet", [facility("way/2", "Calumet Substation", 35.6, -98.1, "Western Farmers Electric Coop")],
                 keys, set())["status"] == "operator_conflict"
    located = project(row(), ARTIFACT, {"OK": [facility("way/1", "Calumet Substation", 35.6, -98.1, "OG&E")]})
    assert located["center"]["basis"] == "source_point" and located["location_review"] == "unreviewed"
    assert OPERATOR_KEYS["NPPD"]  # F46's codes still answer


def test_committed_release_appends_unreviewed_candidates_in_their_states():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = apply_release(base, REPO_ROOT)
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "sppsouth" / "releases" / "active.json")
    released = {s["_id"] for s in load_json(REPO_ROOT / "data" / "sppsouth" / "sources.json")}
    added = [p for p in snapshot["projects"] if p["source_id"] in released]
    assert len(added) == release["expected_counts"]["projects"]
    assert all(set(p["states"]) <= {"40", "35", "48"} for p in added)
    assert all(p["location_review"] == ("unreviewed" if p["center"] else "unlocated") for p in added)
    assert not {p["native_id"] for p in added} & published_uids()
    assert snapshot["coverage"]["sppsouth"]["independently_confirmed_projects"] == 0


def test_xcel_interchange_aliases_come_only_from_sps_osm_names():
    site = facility("way/9", "Potter County Interchange", 35.31, -101.92, "Xcel Energy", state="TX")
    named = {f["name"] for f in with_aliases([site])}
    assert named == {"Potter County Interchange", "Potter County"}
    assert with_aliases([site | {"operator": "Golden Spread Electric Cooperative"}]) == [
        site | {"operator": "Golden Spread Electric Cooperative"}]
    located = project(row(**{"ProjectOwner": "SPS", "State(s)": "TX", "Upgrade Name": "Potter County 345 kV Line Reactor"}),
                      ARTIFACT, {"TX": with_aliases([site])})
    assert located["center"]["basis"] == "source_point"


def test_older_editions_add_only_completed_upgrades_the_current_edition_dropped():
    projects = load_json(REPO_ROOT / "data" / "sppsouth" / "projects.json")
    current = {p["native_id"] for p in projects if p["source_id"] == "spp-qpt-2026q3-south"}
    past = [p for p in projects if p["source_id"] != "spp-qpt-2026q3-south"]
    assert past and all(p["status_group"] == "in_service" and "last listed in" in p["status"] for p in past)
    assert not {p["native_id"] for p in past} & current
    assert len({p["native_id"] for p in projects}) == len(projects)  # one record per UID across editions
    assert all(e["type"] == "in_service" for p in past for e in p["project_events"])
