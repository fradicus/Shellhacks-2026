"""F42: C33 loosened matching, county references and the committed Pacific Northwest output."""

from common import REPO_ROOT, load_json, validate
from pnw.shared import counties, county_geoids, locate, match


def facility(fid, name, lat, lon, operator=None, voltage=None):
    return {"id": fid, "name": name, "norm": name.upper(), "operator": operator, "voltage": voltage, "lat": lat, "lon": lon}


def test_unique_in_state_name_matches_without_corroboration():
    osm = [facility("way/1", "Hot Springs Substation", 47.6, -114.7, "Some Coop")]
    hit = match("Hot Springs", osm, ["BONNEVILLE"], set())
    assert (hit["status"], hit["corroboration"]) == ("matched", ["unique_in_state"])
    # A node + area of the same site still counts as one facility.
    osm.append(facility("node/2", "Hot Springs", 47.6003, -114.7003))
    assert match("Hot Springs", osm, ["BONNEVILLE"], set())["facility"]["id"] == "way/1"


def test_two_same_name_facilities_or_no_name_stay_unlocated():
    osm = [facility("way/1", "Midway", 46.0, -119.0), facility("way/2", "Midway", 47.5, -117.0)]
    assert match("Midway", osm, ["BONNEVILLE"], set())["status"] == "ambiguous"
    assert match("Mid", osm, ["BONNEVILLE"], set())["status"] == "no_facility"
    # Corroboration still picks the one C26 would pick.
    osm[0]["operator"] = "Bonneville Power Administration"
    assert match("Midway", osm, ["BONNEVILLE"], set())["corroboration"] == ["operator"]


def test_locate_labels_name_only_centers():
    osm = [facility("way/1", "Alpha", 45.0, -120.0), facility("way/2", "Beta", 46.0, -121.0)]
    center, block = locate("line", ["Alpha", "Beta"], osm, [], set(), "test")
    assert (center["lat"], center["lon"], center["basis"]) == (45.5, -120.5, "two")
    assert "name-only" in center["evidence"] and center["evidence"].startswith("Unverified candidate:")
    assert locate(None, [], osm, [], set(), "test")[0] is None


def test_named_counties_become_geoids_only():
    assert county_geoids([("WA", "Benton County"), ("WA", "Benton"), ("WA", "Nowhere")], counties()) == ["53005"]


def test_committed_projects_validate_and_never_claim_review():
    path = REPO_ROOT / "data" / "pnw" / "projects.json"
    if not path.exists():
        return
    projects = load_json(path)
    assert len({p["_id"] for p in projects}) == len(projects)
    for p in projects:
        validate(p, "national-project")
        assert p["location_review"] == ("unreviewed" if p["center"] else "unlocated")
        assert "approximate_location" not in p  # no county dots (user, 2026-09-27)
        if p["center"]:
            assert p["center"]["evidence"].startswith(("Unverified candidate:", "Official source"))


def test_voltage_or_county_contradiction_blocks_name_only():
    osm = [facility("hifld/1", "Mountain View", 47.2, -123.1, voltage="138000") | {"county": "MASON"}]
    assert match("Mountain View", osm, ["GRANT"], set(), {"GRANT"})["status"] == "county_conflict"
    assert match("Mountain View", osm, [], {500})["status"] == "voltage_conflict"
    assert match("Mountain View", osm, [], set())["status"] == "matched"


def test_cx_memo_fields_counties_and_window():
    from pnw.build import excluded
    from pnw.cx import counties as cx_counties
    from pnw.cx import rows

    assert cx_counties("Clackamas County and Washington County, Oregon") == [("OR", "Clackamas"), ("OR", "Washington")]
    assert cx_counties("Wasco County, Oregon and Klickitat County, Washington") == [("OR", "Wasco"), ("WA", "Klickitat")]
    page = ("Categorical Exclusion Determination Proposed Action: Heyburn-Minico No. 1 Reconductor Project No.: P04353 "
            "Project Manager: A B Location: Minidoka County, Idaho Categorical Exclusion Applied (from Subpart D, 10 "
            "C.F.R. Part 1021): B4.13 Upgrading and rebuilding existing powerlines Description")
    row = rows({1: page})
    assert (row["native_id"], row["kind"], row["facilities"], row["states"]) == ("P04353", "line", ["Heyburn", "Minico"],
                                                                                 ["ID"])
    assert excluded(row | {"memo_year": "2025"}) is None
    assert excluded(row | {"memo_year": "2024"}) == "2024 CX memo with no 2025-2035 year in its text"
    assert "B1.3" not in row["section"] and excluded(rows({1: page.replace("B4.13", "B1.3")})).startswith("other")
    assert excluded(row | {"status_raw": "Completed"}).startswith("historical")
    assert excluded(row | {"in_service_raw": "2024"}) == "in-service 2024 outside 2025-2035"


def test_release_applies_to_the_national_snapshot():
    from national.build import load_snapshot, validate_snapshot_values
    from pnw.publish import apply_release, release

    assert load_json(REPO_ROOT / "data" / "pnw" / "releases" / "active.json") == release()
    snapshot = load_snapshot()
    hooked = "pacific_northwest" in snapshot["coverage"]
    if not hooked:  # before F30's loader hook; the loader, not apply_release, recomputes coverage totals
        snapshot = apply_release(snapshot, REPO_ROOT)
    released = {p["_id"] for p in load_json(REPO_ROOT / "data" / "pnw" / "projects.json")}
    assert sum(p["_id"] in released for p in snapshot["projects"]) == len(released) > 0
    assert snapshot["coverage"]["pacific_northwest"]["independently_confirmed_projects"] == 0
    assert not hooked or validate_snapshot_values(snapshot) == []
