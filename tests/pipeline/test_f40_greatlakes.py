"""F40: C26 candidate matching rules and the committed Minnesota output."""

from common import REPO_ROOT, load_json, validate
from greatlakes.match import candidate_center, facilities_named, match_facility
from greatlakes.minnesota import completed_status, planned_in_service


def facility(fid, name, lat, lon, operator=None, voltage=None):
    return {"id": fid, "name": name, "norm": name.upper(), "operator": operator, "voltage": voltage, "lat": lat, "lon": lon}


def test_names_sites_lines_and_non_facilities():
    assert facilities_named("Hibbing Substation Modernization", None)["names"] == ["Hibbing"]
    assert facilities_named("Lake Pulaski TR05 ELR", None)["names"] == ["Lake Pulaski"]
    assert facilities_named("Wilmarth Substation - FRM13", None)["names"] == ["Wilmarth"]
    line = facilities_named("0754 Buffalo - Maple Lake Rebuild", None)
    assert (line["kind"], line["names"]) == ("line", ["Buffalo", "Maple Lake"])
    assert facilities_named("Summit to Dovray 69 kV Rebuild", None)["names"] == ["Summit", "Dovray"]
    assert facilities_named("Duluth Area 230 kV", None)["kind"] is None
    assert facilities_named("Fargo-St. Cloud- Monticello 345kV", None)["reason"] == "multi_terminal_line"
    assert facilities_named("Priam Second Transformer and St John's Lake Breaker Station", None)["kind"] is None
    assert facilities_named("25 Line Rebuild", None)["kind"] is None
    described = facilities_named("25 Line Rebuild", "It runs from the Arrowhead Substation to the Hibbing Substation.")
    assert (described["from"], described["names"]) == ("description", ["Arrowhead", "Hibbing"])


def test_match_requires_exact_name_and_corroboration():
    osm = [facility("way/1", "Coon Creek Substation", 45.1, -93.3, "Xcel Energy", "345000;115000"),
           facility("way/2", "Coon Rapids Substation", 45.2, -93.3, "Xcel Energy", "115000")]
    assert match_facility("Coon", osm, ["XCEL"], set())["status"] == "no_facility"
    assert match_facility("Coon Creek", osm, ["GREAT RIVER"], set())["status"] == "not_corroborated"
    hit = match_facility("Coon Creek", osm, ["GREAT RIVER"], {345})
    assert (hit["status"], hit["corroboration"]) == ("matched", ["voltage"])
    assert match_facility("Haines Rd", [facility("way/3", "Haines Road Substation", 46, -92, "Minnesota Power")],
                          ["MINNESOTA POWER"], set())["status"] == "matched"


def test_same_name_far_apart_is_ambiguous_but_node_and_area_collapse():
    far = [facility("way/1", "Benson", 45.3, -95.6, "Xcel Energy"), facility("way/2", "Benson", 47.0, -92.0, "Xcel Energy")]
    assert match_facility("Benson", far, ["XCEL"], set())["status"] == "ambiguous"
    near = [facility("node/9", "Benson", 45.3000, -95.6000, "Xcel Energy"), facility("way/1", "Benson", 45.3005, -95.6005)]
    near[1]["voltage"] = "115000"
    hit = match_facility("Benson", near, ["XCEL"], {115})
    assert hit["status"] == "matched" and hit["facility"]["id"] == "way/1"


def test_center_rule_mean_partial_and_site():
    a = {"status": "matched", "facility": facility("way/1", "A", 45.0, -93.0), "corroboration": ["operator"]}
    b = {"status": "matched", "facility": facility("way/2", "B", 46.0, -94.0), "corroboration": ["voltage"]}
    missing = {"status": "no_facility"}
    two = candidate_center("line", [a, b])
    assert (two["lat"], two["lon"], two["basis"]) == (45.5, -93.5, "two")
    one = candidate_center("line", [a, missing])
    assert one["basis"] == "one" and "Partial" in one["evidence"]
    assert candidate_center("site", [a])["basis"] == "source_point"
    assert candidate_center("line", [missing, missing]) is None


def test_dates_keep_their_precision():
    assert completed_status("7/11/2024")[1]["value"] == "2024-07-11"
    assert completed_status("July, 2022")[1]["value"] == "2022-07"
    assert completed_status("Completed in 2024") == ("in_service", {"raw": "Completed in 2024", "value": "2024", "precision": "year"})
    assert completed_status("Withdrawn: replaced")[0] == "cancelled"
    assert completed_status("Moved to study")[0] == "unknown"
    assert planned_in_service("The projected in-service date is December 2027.")["value"] == "2027-12"
    assert planned_in_service("Phase 1 in-service 2026; phase 2 in-service 2028.")["precision"] == "unknown"


def test_committed_minnesota_records_are_candidates_never_verified():
    projects = load_json(REPO_ROOT / "data" / "greatlakes" / "mn" / "projects.json")
    assert len({p["_id"] for p in projects}) == len(projects)
    for project in projects:
        validate(project, "national-project")
        assert project["location_review"] in {"unreviewed", "unlocated"}
        if project["center"]:
            assert project["location_review"] == "unreviewed"
            assert project["center"]["evidence"].startswith("Unverified candidate:")
        else:
            assert project["location_review"] == "unlocated"
    summary = load_json(REPO_ROOT / "data" / "greatlakes" / "mn" / "summary.json")
    assert summary["candidate_located"] == sum(1 for p in projects if p["center"]) and summary["verified"] == 0


def test_atc_names_ordinals_particles_queue_ids_and_brackets():
    assert facilities_named("Menominee – 30th Ave. 69 kV (Y-199)", None)["names"] == ["Menominee", "30th Ave."]
    assert facilities_named("South Fond du Lac - Forward Energy Center 138 kV", None)["names"][0] == "South Fond du Lac"
    assert facilities_named("R1049/R5061 Edgewater SS", None)["names"] == ["Edgewater"]
    assert facilities_named("J1316 Paris SS Network Upgrades [North Appleton - Fox River]", None)["names"] == ["Paris"]
    assert facilities_named("Range Line Dist (WE) – Range Line Switchyard 138 kV", None)["kind"] is None
    partial = facilities_named("Harrison Tap – Iola 69kV (Y-70)", None)
    assert (partial["kind"], partial["names"]) == ("line", [None, "Iola"])


def test_atc_zone_states_and_cost():
    from greatlakes.wisconsin import cost, zone_states

    page = "<p>Zone 3 includes the counties of:</p><ul><li>Dane, Wis.</li><li>Winnebago (N), Ill.</li></ul>" \
           "<h2>Zone 3 Planned Projects</h2><p>Mich.</p>"
    assert zone_states(page) == ["IL", "WI"]
    assert cost("$ 1 3,857,000") == {"raw": "$ 1 3,857,000", "usd": 13857000}
    assert cost("$ -")["usd"] is None


def test_short_leading_numbers_and_work_after_a_dash():
    assert facilities_named("9 Mile SW STA – Pine River 69kV", None)["names"] == ["9 Mile", "Pine River"]
    site = facilities_named("North Lake SS – Transformer Asset Renewal", None)
    assert (site["kind"], site["names"]) == ("site", ["North Lake"])
    assert facilities_named("0754 Buffalo - Maple Lake Rebuild", None)["names"] == ["Buffalo", "Maple Lake"]
