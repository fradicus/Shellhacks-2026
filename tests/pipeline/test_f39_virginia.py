"""F39/C45 Virginia batch: Dominion page schedules, SCC case-list parsing, and the committed batch applying."""

from common import REPO_ROOT, load_json
from national.build import OUTPUTS
from southeast import dense
from southeast.virginia import locate_text, page_url, schedule, scc_cases, split_case


def test_schedule_reads_one_in_service_or_completion_date():
    got = schedule("was energized on February 26, 2019. Timeline 2016 Project announced")
    assert (got["kind"], got["value"], got["precision"]) == ("in_service", "2019-02-26", "day")
    got = schedule("Timeline 2031 – In-service 2028 Construction begins")
    assert (got["kind"], got["value"], got["precision"]) == ("planned_milestone", "2031", "year")
    got = schedule("June 2028 - SCC approved in service date ... expected to be in service by 2028")
    assert (got["value"], got["precision"]) == ("2028-06", "month")
    # A part of the work is not the project: "Completion of boardwalk", "completion of the final phase".
    assert schedule("February 2023 Completion of boardwalk for the diversion") is None
    # Phases with different years stay unknown rather than picking one.
    assert schedule("Late Summer 2024 – Complete construction ... Late 2024 Construction complete "
                    "Late 2026 Construction complete") is None
    assert schedule("Construction begins in 2027.") is None


CASE_LIST = """
<div class="panel--header_title"> EASTERN VIRGINIA </div>
<ul>
<li>Dominion Energy Virginia&nbsp;
<ul>
<li><a href="/docketsearch#caseDetails/1">PUR-2024-00105</a> - City of Chesapeake - Fentress-Yadkin 500 kV Line #588
Rebuild
<ul><li><a href="/media/map.pdf">Overview Map</a></li></ul>
</li>
</ul>
</li>
<li>Non-Utility Projects
<ul><li><a href="/docketsearch">PUR-2020-00235</a> - Surry County - Example Solar generating facility</li></ul>
</li>
</ul>
"""


def test_scc_case_list_keeps_region_utility_and_case_text():
    cases = scc_cases(CASE_LIST)
    assert [(c["region"], c["utility"]) for c in cases] == [("EASTERN VIRGINIA", "Dominion Energy Virginia"),
                                                           ("EASTERN VIRGINIA", "Non-Utility Projects")]
    parts = split_case(cases[0]["text"])
    assert parts == {"case": "PUR-2024-00105", "area": "City of Chesapeake",
                     "work": "Fentress-Yadkin 500 kV Line #588 Rebuild"}
    # A line between two substations is not an area: "Chesterfield - Lanexa Corridor".
    assert split_case("PUR-2025-00154 - Chesterfield - Lanexa Corridor Lines #92")["area"] is None
    assert locate_text("500 kV Doubs-Goose Creek Line #514") == "Doubs-Goose Creek Line #514 (500 kV)"


def test_only_dominion_pages_are_fetched():
    assert page_url("http://www.dominionenergy.com/en/X/Allman-Substation") == \
        "https://www.dominionenergy.com/en/X/Allman-Substation"
    assert page_url("https://coastalvawind.com") is None and page_url(None) is None


def test_committed_virginia_batch_applies_unreviewed():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = dense.apply_release(base, REPO_ROOT)
    ids = {p["_id"] for p in load_json(REPO_ROOT / dense.FOLDER / "virginia" / "projects.json")}
    added = [p for p in snapshot["projects"] if p["_id"] in ids]
    assert added and len(added) == snapshot["coverage"]["southeast_dense"]["batches"]["virginia"]["projects"]
    for project in added:
        assert project["location_review"] == ("unreviewed" if project["center"] else "unlocated")
        assert project["location_candidate"]["tier"] in (dense.TIERS if project["center"] else (None,))
        assert all(e["type"] != "in_service" or e["date"] for e in project["project_events"])
