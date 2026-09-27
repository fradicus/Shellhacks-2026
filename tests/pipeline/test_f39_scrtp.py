"""F39/C40 SCRTP: DESC page blocks, Santee Cooper deck tables, dates and names."""

from southeast.dense import locate
from southeast.scrtp import desc_rows, santee_rows, site_name, when

DESC_PAGE = """                                               Project 3 of 54
                            Dominion Energy South Carolina
                   Planned Transmission Projects $2M and above Total
                                     5 Year Budget

Canadys-Ritter 115KV: Rebuild SPDC 230/115KV 1272 (Approx 18
Miles)

Project ID
06076 A

Project Description
Rebuild the line.

Project Status
In Progress

Planned In-Service Date
6/1/2028
"""


def test_desc_page_keeps_a_wrapped_title_and_labels():
    row = desc_rows(DESC_PAGE)[0]
    assert row["title"] == "Canadys-Ritter 115KV: Rebuild SPDC 230/115KV 1272 (Approx 18 Miles)"
    assert (row["id"], row["status"], row["date"]) == ("06076 A", "In Progress", "6/1/2028")
    assert site_name(row["title"]) == "Canadys-Ritter 115KV"


def test_santee_table_needs_its_heading_and_owner():
    deck = ("Santee Cooper\n\f   Committed Transmission Facilities\n   Project Title      In-service Date\n"
            "Indian Field-Wassamassaw 230 kV Line              12/1/2026\n\n24\n")
    assert santee_rows(deck) == [{"page": 2, "title": "Indian Field-Wassamassaw 230 kV Line", "date": "12/1/2026"}]
    assert santee_rows(deck.replace("Santee Cooper", "Other utility")) == []


def test_dates_keep_precision_and_reject_impossible_days():
    assert when("5/31/26") == {"raw": "5/31/26", "value": "2026-05-31", "precision": "day"}
    assert when("04/31/26")["value"] is None  # the source's impossible date stays unknown, raw kept
    assert when(None) == {"raw": None, "value": None, "precision": "unknown"}


def test_hyphenated_voltage_pair_does_not_hide_the_facility_name():
    bucksville = [{"id": "way/1", "name": "Bucksville Substation", "operator": "Santee Cooper", "voltage": "230000",
                   "lat": 33.72, "lon": -79.10}]
    center, candidate = locate("Bucksville 230-115 kV Substation", None, bucksville, ["SANTEE COOPER"])
    assert center and candidate["tier"] == "candidate"
