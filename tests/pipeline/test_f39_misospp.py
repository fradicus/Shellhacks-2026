"""F39/C45 MISO South + SPP batch: parser and rule checks on small invented fixtures, plus the committed batch."""

from datetime import datetime

from common import REPO_ROOT, load_json
from national.build import OUTPUTS
from southeast import dense
from southeast.misospp import (
    bus_names,
    day,
    facility_names,
    history,
    locate_names,
    mtep_id,
    parse_text,
    spp_group,
    spp_rule,
    spp_states,
)


def test_spp_status_states_and_dates():
    assert spp_group("Delay - \nMitigation") == spp_group("NTC-C Project \nEstimate Window") == "planned"
    assert spp_group("CLOSED OUT") == spp_group("In Service") == spp_group("Complete") == "in_service"
    assert (spp_group("Withdrawn"), spp_group("Identified"), spp_group("Re-evaluation")) == \
        ("cancelled", "proposed", "unknown")
    assert spp_states("KS/AR/AR") == ["KS", "AR"] and spp_states("OK/") == ["OK"] and spp_states("NA") == []
    assert day(datetime(2025, 12, 29)) == "2025-12-29" and day("11/28/2025") == "2025-11-28"
    assert day(datetime(1933, 1, 1)) is None and day("TBD") is None and day(None) is None
    # A date-formatted numeric ID cell decodes back to its serial.
    assert mtep_id(datetime(2037, 12, 22)) == "50396" and mtep_id("50350") == "50350"


def test_spp_owner_rule():
    assert spp_rule("AEP", ["LA"]) == ("core", None)
    assert spp_rule("AEP", ["TX", "AR"]) == ("core", None)
    assert spp_rule("NWE", ["AR"])[0] == "excluded" and spp_rule("SPS", ["KS", "AR"])[0] == "excluded"
    # A border owner (or an unassigned one) must be corroborated by a facility in the tagged state.
    assert spp_rule("OGE", ["AR"]) == ("border", None) and spp_rule("OGE", ["LA"]) == ("border", None)
    assert spp_rule("TBD", ["AR", "KS", "OK"]) == ("border", None)


def test_name_rewrites_and_bus_agreement():
    assert parse_text("Alpha Creek 161kV: Build new substation") == "Alpha Creek 161kV Build new substation"
    assert parse_text("J1234 & J1235 Bravo 500-230 kV Station") == "Bravo 500/230 kV Station"
    assert parse_text("Ft. Charlie 345 kV Terminal Equipment") == "Fort Charlie 345 kV Terminal Equipment"
    assert parse_text("Delta Load Interconnection - Phase 2") == "Delta Load Interconnection"
    assert bus_names("Echo - Foxtrot Lake 138 kV Ckt 1", ["ECHO 138KV", "FOXTROT LAKE 138KV"]) == ["ECHO", "FOXTROT LAKE"]
    # Model bus names the upgrade name does not repeat are not location evidence.
    assert bus_names("Golf - Hotel 765 kV New Line", ["INDIA T", "JULIET  138"]) == []


def facility(name, sub_from, sub_to=None, kind="Substation"):
    return {"Name": name, "From Sub": sub_from, "To Sub": sub_to, "Facility Type": kind}


def test_miso_facility_names():
    assert facility_names([facility("x", "Kilo 500kV")]) == ("site", ["Kilo 500kV"])
    assert facility_names([facility("x", "Lima", None, "Line New")]) == ("line", ["Lima"])
    line = [facility("x", "Mike", "November", "Line New"), facility("y", "Mike")]
    assert facility_names(line) == ("line", ["Mike", "November"])
    # A new station cut into an existing line names three substations: not one site or line.
    cut_in = [facility("x", "Oscar", "Papa"), facility("y", "Quebec")]
    assert facility_names(cut_in) is None
    assert facility_names([facility("x", "Oscar", "Papa")]) is None  # two subs, but no line facility joins them
    assert facility_names([facility("x", "Multiple")]) is None


OSM = [
    {"id": "way/1", "name": "Romeo Substation", "operator": "Test Power Co", "voltage": "138000", "lat": 32.0,
     "lon": -93.0},
    {"id": "way/2", "name": "Sierra Substation", "operator": "Other Utility", "voltage": "138000", "lat": 32.5,
     "lon": -93.5},
    {"id": "way/3", "name": "Tango Substation", "operator": None, "voltage": None, "lat": 33.0, "lon": -92.0},
]


def test_locate_names_tiers_and_operator_guard():
    center, got = locate_names("line", ["Romeo", "Tango"], {138}, OSM, ["TEST POWER"], "from_to_bus_names")
    assert (center["basis"], center["lat"], center["lon"]) == ("two", 32.5, -92.5)
    assert got["tier"] == "candidate_unique_name" and got["independent_review"] is False
    center, got = locate_names("site", ["Romeo"], {138}, OSM, ["TEST POWER"], "facility_from_to")
    assert got["tier"] == "candidate" and center["basis"] == "source_point"
    # C38: the only same-name facility belongs to another utility.
    center, got = locate_names("site", ["Sierra"], {138}, OSM, ["TEST POWER"], "facility_from_to")
    assert center is None and got["endpoints"][0]["status"] == "operator_conflict"


def observation(edition, date, status, group, row=1):
    return {"edition": edition, "row": row, "title": f"Edition {edition}", "date": date, "status": status,
            "group": group, "date_field": "ISD",
            "evidence": {"publisher": "p", "url": "https://example.org/x", "artifact_sha256": "0" * 64,
                         "locator": "l", "source_date": None, "retrieved_at": "2026-09-27T00:00:00Z",
                         "access_review": "a", "facts": "-"}}


def test_history_changed_dates_then_in_service():
    events = history("p", "n", [observation("e1", "2024-06-01", "On Schedule", "planned"),
                                observation("e2", "2024-06-01", "On Schedule", "planned"),
                                observation("e3", "2025-03-20", "Delay", "planned"),
                                observation("e4", "2025-12-29", "Complete", "in_service")])
    assert [(e["type"], e["date"]) for e in events] == [
        ("planned_milestone", "2024-06-01"), ("planned_milestone", "2025-03-20"), ("in_service", "2025-12-29")]
    # An in-service status with a future or missing date is an undated in_service event.
    events = history("p", "n", [observation("e1", "2027-01-01", "In Service", "in_service")])
    assert [(e["type"], e["date"], e["precision"]) for e in events] == [("in_service", None, "unknown")]


def test_committed_misospp_batch_applies():
    snapshot = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    applied = dense.apply_release(snapshot, REPO_ROOT)
    entry = load_json(REPO_ROOT / dense.ACTIVE)["batches"]["misospp"]
    ids = {p["_id"] for p in load_json(REPO_ROOT / dense.FOLDER / "misospp" / "projects.json")}
    added = [p for p in applied["projects"] if p["_id"] in ids]
    assert len(added) == entry["expected_counts"]["projects"] > 0
    assert applied["coverage"]["southeast_dense"]["batches"]["misospp"] == entry["expected_counts"]
    for project in added:
        assert project["planning_region"] in ("miso", "spp")
        if project["center"]:
            assert project["location_candidate"]["tier"] in ("candidate", "candidate_unique_name")
            assert project["location_review"] == "unreviewed"
        else:
            assert project["location_review"] == "unlocated"
