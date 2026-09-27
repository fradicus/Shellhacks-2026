"""F39/C45 CTPC batch: listing-row parser, name cleaning, location guards and dated events.

Fixture rows and facilities are explicit test inputs (IDs X000001.., places Alpha/Beta/...), not real projects.
"""

from common import REPO_ROOT, load_json
from southeast import ctpc, dense

MANIFEST = {ctpc.artifact(e): {"url": f"https://example.test/{e}.pdf", "sha256": "0" * 64,
                               "retrieved_at": "2026-09-27T00:00:00Z"} for e in ctpc.EDITIONS}


def row(edition, status, date, rid="X000001"):
    return (edition, {"id": rid, "name": "Alpha – Beta 115 kV Line, Rebuild", "owner": "DEP", "status": status,
                      "date": date, "cost_musd": "10", "page": 1, "raw": []})


def test_parse_row_reads_fields_by_value_across_layouts():
    plan = ["X000001", "Alpha – Beta 230 kV Line,\nReconductor", "DEP", "Underway", "12/1/2026", "31", "AS"]
    assert ctpc.parse_row(plan) == {"id": "X000001", "name": "Alpha – Beta 230 kV Line, Reconductor", "owner": "DEP",
                                    "status": "Underway", "date": "12/1/2026", "cost_musd": "31"}
    # Mid-year layout: an "issue resolved" column sits between name and status, the owner after the status.
    update = ["X000002", None, "Gamma 100 kV Line, Upgrade", "Mitigate contingency loading", "In-Service", "DEC",
              None, "11/7/2024", None, "11", None]
    got = ctpc.parse_row(update)
    assert (got["name"], got["status"], got["owner"], got["date"], got["cost_musd"]) == (
        "Gamma 100 kV Line, Upgrade", "In-Service", "DEC", "11/7/2024", "11")
    assert ctpc.parse_row(["X000003", "Delta, Construct", "Project status changed to In-Service"]) is None
    assert ctpc.parse_row(["Project ID", "Name", "DEC", "Planned", "TBD"]) is None


def test_dates_keep_the_printed_day_and_two_digit_years():
    assert ctpc.day("6/1/2026") == "2026-06-01"
    assert ctpc.day("12/1/26") == "2026-12-01"
    assert ctpc.day("TBD") is None and ctpc.day(None) is None


def test_clean_name_keeps_facilities_the_source_states():
    assert ctpc.clean_name("Alpha 100 kV Line (Beta–Gamma), Upgrade") == "Beta – Gamma 100 kV Line"
    assert ctpc.clean_name("Alpha – Beta 115 kV Line (Gamma – Delta – Eps), Reconductor") == "Alpha – Beta 115 kV Line"
    assert ctpc.clean_name("Alpha 230/115 kV Banks #1 & #2, Upgrade CT Ratios") == "Alpha 230/115 kV Bank"
    assert ctpc.clean_name("Alpha–Beta115 kV Line, Rebuild") == "Alpha–Beta 115 kV Line"
    assert ctpc.clean_name("Alpha 100 kV Switching Station, Construct") == "Alpha 100 kV Station"
    assert ctpc.clean_name("Alpha Tie, Upgrade") == "Alpha Tie Station"
    assert ctpc.clean_name("Alpha 230/100/44 kV Tie, Upgrade") == "Alpha 230/100/44 kV Tie Station"
    assert ctpc.clean_name("Alpha 230/100/44 kV Tie, Upgrade", tie=True) == "Alpha Tie 230/100/44 kV"


def facility(fid, name, operator, voltage, state="NC", lat=35.0, lon=-79.0):
    return {"id": fid, "name": name, "norm": name.upper(), "operator": operator, "voltage": voltage, "state": state,
            "lat": lat, "lon": lon}


def test_place_guards_foreign_sister_and_voltage_conflicts():
    facilities = [facility("node/1", "Alpha", "Duke Energy Progress", "230000"),
                  facility("node/2", "Beta", "Dominion Energy", "230000", lat=35.5),
                  facility("node/3", "Gamma", None, "230000", state="SC", lat=34.0, lon=-81.0),
                  facility("node/4", "Delta", "Duke Energy Progress", "100000", lat=36.0)]
    state_of = {f["id"]: f["state"] for f in facilities}
    # Another utility's terminal matches only with its own operator; the line then has both endpoints.
    center, candidate, states = ctpc.place("Alpha-VEPCO Beta 230 kV Line, Reconductor", "DEP", facilities, state_of)
    assert center["basis"] == "two" and candidate["endpoints"][1]["utility"] == "VEPCO" and states == ["37"]
    # DEC's "DUKE" key must not accept a Progress-operated facility.
    center, candidate, _ = ctpc.place("Delta 100 kV Substation, Upgrade", "DEC", facilities, state_of)
    assert center is None and candidate["endpoints"][0]["status"] == "operator_conflict"
    # A name-only match tagged 230 kV cannot be the terminal of a 100 kV line.
    center, candidate, states = ctpc.place("Delta – Gamma 100 kV Line, Upgrade", "DEP", facilities, state_of)
    assert [e["status"] for e in candidate["endpoints"]] == ["matched", "voltage_conflict"]
    assert center["basis"] == "one" and states == ["37"]


def test_events_one_per_changed_date_and_newest_in_service_date():
    listings = [row("2024", "Underway", "6/1/2025"), row("2024-myu", "Underway", "6/1/2025"),
                row("2025", "In-Service", "7/1/2025"), row("2025-myu", "In-Service", "6/20/2025")]
    events = ctpc.events("p", listings, MANIFEST)
    assert [(e["type"], e["date"]) for e in events] == [("planned_milestone", "2025-06-01"),
                                                        ("in_service", "2025-06-20")]
    assert "Unchanged through the 2024-myu edition" in events[0]["description"]
    assert events[1]["evidence"][0]["source_date"] == ctpc.EDITIONS["2025-myu"][0]


def test_in_service_without_a_usable_date_stays_undated():
    events = ctpc.events("p", [row("2025", "Planned", "TBD"), row("2025-myu", "In-Service", "-")], MANIFEST)
    assert [(e["type"], e["date"], e["precision"]) for e in events] == [("in_service", None, "unknown")]


def test_committed_batch_applies_through_the_dense_release():
    from national.build import OUTPUTS

    snapshot = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    applied = dense.apply_release(snapshot, REPO_ROOT)
    batch = load_json(REPO_ROOT / dense.FOLDER / "ctpc" / "projects.json")
    ids = {p["_id"] for p in batch}
    added = [p for p in applied["projects"] if p["_id"] in ids]
    assert len(added) == len(batch) == applied["coverage"]["southeast_dense"]["batches"]["ctpc"]["projects"]
    for project in added:
        assert project["location_review"] == ("unreviewed" if project["center"] else "unlocated")
        assert project["center"] is None or project["location_candidate"]["tier"] in dense.TIERS
    dispositions = load_json(REPO_ROOT / dense.FOLDER / "ctpc" / "dispositions.json")
    assert sum(d["disposition"] == "accepted" for d in dispositions) == len(batch)
