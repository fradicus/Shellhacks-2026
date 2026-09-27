"""F46: SPP and MISO name forms, status and date mapping, the operator guard, and the committed Midwest release."""

from datetime import datetime

from california.caiso import match
from common import REPO_ROOT, load_json
from midwest.build import OPERATOR_KEYS, miso_keys, named, project, status_group
from midwest.publish import apply_release
from national.build import OUTPUTS, _coverage, validate_snapshot_values

ARTIFACT = {"url": "https://www.spp.org/x.zip", "sha256": "0" * 64, "retrieved_at": "2026-09-27T08:00:00Z"}


def facility(fid, name, lat, lon, operator=None, voltage=None, state="NE"):
    return {"id": fid, "name": name, "norm": name.upper(), "operator": operator, "voltage": voltage, "state": state,
            "lat": lat, "lon": lon}


def row(**cells):
    base = {"UID": 1, "PID": 2, "NTC ID": 3, "ProjectOwner": "NPPD", "State(s)": "NE", "Project Name": "P",
            "Upgrade Name": "Tekamah 161 kV Substation", "Project Type": "Regional Reliability",
            "Project Owner Indicated In-Service Date": datetime(2028, 9, 30), "Project Status": "On Schedule < 4",
            "Current Cost Estimate": None, "Voltages (kV)": "161", "From Bus Name": None, "To Bus Name": None,
            "Project Description/ Comments": None, "_sheet": "S", "_row": 9}
    return base | cells


def test_spp_upgrade_name_forms():
    assert named("Lake County - Howard 115 kV Ckt 1 New Line")["names"] == ["Lake County", "Howard"]
    # Terminal work is at the named site; "toward" names the far end, never a second endpoint.
    assert named("Craig 161 kV Ckt 2 Terminal Upgrade toward Midway 161 kV") == {
        "kind": "site", "names": ["Craig"], "from": "name", "reason": None}
    assert named("Wolf Creek 345kV Terminal Equipment")["names"] == ["Wolf Creek"]
    assert named("Sweetwater 345kV GEN-2016-074 Interconnection (TOIF) (NPPD)")["names"] == ["Sweetwater"]
    assert named("Leland Olds - Finstad - 345 kV New Line")["names"] == ["Leland Olds", "Finstad"]
    # Generator queue positions, bus numbers and border points are not facilities.
    assert named("Holt County 345kV (Tap Grand Prairie - Grand Island 345kV) - GEN-2015-023 Addition (TOIF)") == {
        "kind": "site", "names": ["Holt County"], "from": "name", "reason": None}
    assert named("S3454 - S3740 345 kV New Line")["kind"] is None
    assert named("North Dakota/Saskatchewan Border (Tableland) - Tande 230 kV Ckt 1")["names"] == [None, "Tande"]


def test_miso_name_forms_and_submitters():
    assert named("Replace Labadie 345 kV 3-4 bus tie switches")["names"] == ["Labadie"]
    assert named("Booneville: Retire 13 kV Reactors") == {"kind": "site", "names": ["Booneville"], "from": "name",
                                                          "reason": None}
    assert named("Leland to Forest City N43 69 kV Rebuild")["names"] == ["Leland", "Forest City"]
    assert named("Upgrade Baumgartner-Watson-1 138 kV Line")["names"] == ["Baumgartner", "Watson"]
    assert named("Plymouth 161-69 kV Transformer Replacement")["names"] == ["Plymouth"]
    assert miso_keys("MIDAMERICAN ENERGY CO. MEC") == ["MIDAMERICAN"]
    assert miso_keys("MONTANA-DAKOTA UTILITIES CO.MDU") == ["MONTANA-DAKOTA", "MDU"]
    assert miso_keys("AMEREN MISSOURI") == ["AMEREN"]  # F40's list still answers what it knows


def test_statuses_and_dates():
    assert status_group("Delay - \nMitigation") == status_group("On Schedule > 4") == "planned"
    assert status_group("NTC-C Project Estimate Window") == "proposed"
    assert status_group("Closed Out") == "in_service" and status_group("Withdrawn") == "cancelled"
    assert status_group("Suspended") == "unknown"
    planned = project(row(), ARTIFACT, {})
    assert [(e["type"], e["date"], e["precision"]) for e in planned["project_events"]] == [
        ("planned_milestone", "2028-09-30", "day")]
    assert planned["states"] == ["31"] and planned["in_service"]["value"] == "2028-09-30"
    # An in-service status is dated only by a date on or before retrieval; nothing is inferred.
    done = project(row(**{"Project Status": "Complete", "Project Owner Indicated In-Service Date": datetime(2025, 5, 1)}),
                   ARTIFACT, {})
    assert [(e["type"], e["date"]) for e in done["project_events"]] == [("in_service", "2025-05-01")]
    late = project(row(**{"Project Status": "In Service", "Project Owner Indicated In-Service Date": datetime(2027, 1, 1)}),
                   ARTIFACT, {})
    assert [(e["type"], e["date"]) for e in late["project_events"]] == [("in_service", None)]
    blank = project(row(**{"Project Owner Indicated In-Service Date": None}), ARTIFACT, {})
    assert blank["project_events"] == [] and blank["in_service"]["precision"] == "unknown"


def test_operator_guard_uses_spp_owner_codes():
    keys = OPERATOR_KEYS["NPPD"]
    assert match("Tekamah", [facility("way/1", "Tekamah Substation", 41.8, -96.2, "Nebraska Public Power District")],
                 keys, set())["corroboration"] == ["operator"]
    assert match("Tekamah", [facility("way/2", "Tekamah Substation", 41.8, -96.2, "Omaha Public Power District")],
                 keys, set())["status"] == "operator_conflict"
    located = project(row(), ARTIFACT, {"NE": [facility("way/1", "Tekamah Substation", 41.8, -96.2, "NPPD")]})
    assert located["center"]["basis"] == "source_point" and located["location_review"] == "unreviewed"
    # Facilities are searched only in the row's own states.
    assert project(row(), ARTIFACT, {"KS": [facility("way/3", "Tekamah Substation", 38.0, -98.0, state="KS")]}
                   )["center"] is None


def test_committed_release_appends_unreviewed_candidates_in_their_states():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = apply_release(base, REPO_ROOT)
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "midwest" / "releases" / "active.json")
    added = [p for p in snapshot["projects"]
             if p["source_id"] in {"spp-qpt-2026q3", "miso-mtep26-eval-midwest", "miso-mtep25-appendix-a-midwest"}]
    assert len(added) == release["expected_counts"]["projects"]
    assert all(set(p["states"]) <= {"19", "29", "20", "31", "38", "46"} for p in added)
    assert all(p["location_review"] == ("unreviewed" if p["center"] else "unlocated") for p in added)
    assert snapshot["coverage"]["midwest"]["independently_confirmed_projects"] == 0


def test_appendix_a_rows_are_new_mtep_ids_in_f46_states():
    projects = load_json(REPO_ROOT / "data" / "midwest" / "projects.json")
    appendix = [p for p in projects if p["source_id"] == "miso-mtep25-appendix-a-midwest"]
    assert appendix and all(set(p["states"]) <= {"19", "29", "38", "46"} for p in appendix)
    earlier = {p["native_id"] for p in projects if p["source_id"] == "miso-mtep26-eval-midwest"}
    assert not {p["native_id"] for p in appendix} & earlier
