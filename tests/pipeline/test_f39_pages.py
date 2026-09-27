"""F39/C40 pages batch: schedule wording, page parsing, legacy-duplicate rule, committed batch."""

from common import REPO_ROOT, load_json
from national.build import OUTPUTS
from southeast import dense
from southeast.pages import ekpc_blocks, endpoints, fe_schedule, ga_schedule, gtc_items, legacy_twin, named_states


def test_firstenergy_planned_date_is_read_even_when_past_and_only_once():
    got = fe_schedule("expected to commence on or about April 2, 2024, and be complete on or about October 18, 2024.")
    assert got == {"value": "2024-10-18", "precision": "day", "phrase": "be complete on or about October 18, 2024"}
    assert fe_schedule("be completed on or about May 1, 2024. Phase 2 will be completed on or about June 3, 2025.") \
        is None
    assert fe_schedule("construction was completed in 2024") is None


def test_georgia_quarter_is_year_precision_and_component_rows_are_ignored():
    got = ga_schedule("Q1 2027 Line Construction begins Q2 2028 Project complete Note:")
    assert got == {"value": "2028", "precision": "year", "quarter": "Q2 2028", "phrase": "Q2 2028 Project complete"}
    assert ga_schedule("we expect all projects to be ready for service Q2 2027.")["quarter"] == "Q2 2027"
    assert ga_schedule("Q2 2028 Substation Complete Q4 2028 Line Construction Complete") is None
    assert ga_schedule("Q4 2027 Project Completion Target")["value"] == "2027"


def test_named_states_come_only_from_county_state_phrases():
    text = "16.4 miles in Allegany County, Maryland and 10.9 miles in Morgan County, West Virginia."
    assert named_states(text) == {"24", "54"}
    assert named_states("between the Page Substation in Luray, Virginia") == set()


def test_legacy_twin_needs_the_same_endpoints_and_voltage():
    legacy = [{"_id": "legacy:GPC:1", "name": "GTC: DRESDEN - TALBOT 500KV LINE"},
              {"_id": "legacy:GPC:2", "name": "FARLEY (APC)-TAZEWELL 500KV"}]
    assert endpoints("Dresden – Talbot 500 kV Transmission Line") == (frozenset({"DRESDEN", "TALBOT"}),
                                                                     frozenset({500}))
    assert legacy_twin("Dresden – Talbot 500 kV Transmission Line", legacy) == "legacy:GPC:1"
    assert legacy_twin("Dresden – Talbot 230 kV Transmission Line", legacy) is None
    assert legacy_twin("Big Tazewell - Farley 500kv Transmission Project", legacy) is None
    assert legacy_twin("Effingham County Transmission Project", legacy) is None


def test_page_blocks_parse():
    ekpc = ('<section><article data-x class="c-accordion"><h3><button aria-label="Expand A-B line">'
            '<span class="text">A-B line</span></button></h3><div><p>Hart County</p>'
            '<a href="/files/a.pdf">Document</a></div></article></section>')
    assert ekpc_blocks(ekpc) == [{"title": "A-B line", "text": "Hart County Document", "links": ["/files/a.pdf"]}]
    gtc = ('<h4 class="item-title">X 230 kV Switching Station (Y County)</h4>\n<div class="item-content">'
           '<p>Parcel acquired in 2009.</p></div>')
    assert gtc_items(gtc) == [{"title": "X 230 kV Switching Station (Y County)", "text": "Parcel acquired in 2009."}]


def test_committed_pages_batch_applies_unreviewed():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = dense.apply_release(base, REPO_ROOT)
    ids = {p["_id"] for p in load_json(REPO_ROOT / dense.FOLDER / "pages" / "projects.json")}
    added = [p for p in snapshot["projects"] if p["_id"] in ids]
    assert added and len(added) == snapshot["coverage"]["southeast_dense"]["batches"]["pages"]["projects"]
    for project in added:
        assert project["location_review"] == ("unreviewed" if project["center"] else "unlocated")
        assert project["location_candidate"]["tier"] in (dense.TIERS if project["center"] else (None,))
        assert all(e["type"] == "planned_milestone" for e in project["project_events"])
