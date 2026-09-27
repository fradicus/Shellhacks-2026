"""F39/C40 SERTP batch: block parser, CEII marking check, cross-edition links, name guard, committed release."""

from common import REPO_ROOT, load_json
from southeast import dense
from southeast.sertp import ceii_markings, links, locate_name, parse, segment_start

# Invented fixture in the report's pdftotext -layout shape (not real projects).
FIXTURE = """                         SERTP TRANSMISSION PROJECTS
                         ALPHA Balancing Authority Area

   In-Service    2027
        Year:
Project Name:    NORTH FOO - SOUTH BAR 115 KV TRANSMISSION LINE,
                 REBUILD
  Description:   Rebuild 3 miles of the North Foo - South Bar 115 kV transmission line with
                 795 ACSR at 100°C.
  Supporting     The line overloads under contingency.
  Statement:     Revised 06/24/2024                                        Page 1 of 2
\f                         SERTP TRANSMISSION PROJECTS
                         BETA Planning Authority Area

    In-Service   2029
         Year:
Project Name:    GTC: QUUX 230 KV, SWITCH REPLACEMENT
  Description:   Replace switches.
  Supporting     Aging equipment.
  Statement:

                                                  2
"""


def test_parse_reads_blocks_pages_and_sections():
    rows = parse(FIXTURE)
    assert [(r["baa"], r["page"], r["year"]) for r in rows] == [("ALPHA", 1, "2027"), ("BETA", 2, "2029")]
    assert rows[0]["name"] == "NORTH FOO - SOUTH BAR 115 KV TRANSMISSION LINE, REBUILD"
    assert rows[0]["description"].endswith("795 ACSR at 100°C.")
    assert rows[0]["support"] == "The line overloads under contingency."  # footer stripped
    assert rows[1]["support"] == "Aging equipment."  # bare page number is not text


def test_ceii_disclaimers_pass_and_headings_fail():
    prose = ("stakeholder, as it does not include Critical Energy Infrastructure Information (CEII) materials.\n"
             "     (CEII) materials. Materials which include CEII are also available, subject to completion of the\n")
    assert ceii_markings(prose) == (2, [])
    assert ceii_markings("       TRANSMISSION PROJECTS (CEII)\n")[1] == ["TRANSMISSION PROJECTS (CEII)"]
    assert ceii_markings("   TVA  Balancing   Authority    Area(CEII)\n")[1]


def row(name, baa="ALPHA"):
    return {"baa": baa, "name": name}


def test_links_are_exact_or_action_stripped_and_one_to_one():
    new = [row("NORTH FOO - SOUTH BAR 115 KV TRANSMISSION LINE, REBUILD"), row("QUUX 230 KV, UPGRADE"),
           row("ZED 115 KV, REBUILD"), row("ZED 115 KV, RECONDUCTOR")]
    old = [row("NORTH FOO - SOUTH BAR 115KV TRANSMISSION LINE REBUILD"), row("QUUX 230 KV"), row("ZED 115 KV"),
           row("QUUX 230 KV", baa="BETA")]
    # Spacing/punctuation-only difference, then the name without its ", ACTION" phrase; "ZED" is ambiguous and
    # another Balancing Authority Area never links.
    assert links(old, new) == {0: 0, 1: 1}


def test_locate_name_and_segment_guard():
    assert locate_name("GTC: NORTH FOO - SOUTH BAR 115 KV TRANSMISSION LINE, REBUILD") == \
        "North Foo - South Bar 115 kV Transmission Line"
    assert locate_name("CC - QUUX 230 KV, SWITCH REPLACEMENT") == "Quux 230 kV"
    text = "Yates - Line Creek 230 kV (Green) Transmission Line"
    assert segment_start("Yates", text) and not segment_start("Creek", text)
    assert not segment_start("Customer", "Parkwood Tie - Customer Station 100 kV")


def test_committed_sertp_batch_applies():
    from national.build import OUTPUTS

    snapshot = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    result = dense.apply_release(snapshot, REPO_ROOT)
    added = [p for p in result["projects"] if p["_id"].startswith("southeast:sertp:")]
    expected = load_json(REPO_ROOT / dense.ACTIVE)["batches"]["sertp"]["expected_counts"]
    assert len(added) == expected["projects"] > 0
    assert all(p["location_review"] == ("unreviewed" if p["center"] else "unlocated") for p in added)
    assert all(p["status_group"] == "planned" and p["in_service"]["precision"] == "year" for p in added)
    assert all(e["type"] == "planned_milestone" for p in added for e in p["project_events"])


def test_name_only_match_with_other_voltages_is_rejected():
    from southeast.sertp import rejected

    def endpoint(name, voltage, why):
        return {"name": name, "facility": {"voltage": voltage}, "corroboration": why}

    text = "Foo - Bar 115 kV Transmission Line"
    assert rejected(endpoint("Foo", "161000", ["unique_in_state"]), text, {115}, True) == "voltage_conflict"
    assert rejected(endpoint("Foo", "230000;115000", ["unique_in_state"]), text, {115}, True) is None
    assert rejected(endpoint("Foo", None, ["unique_in_state"]), text, {115}, True) is None
    assert rejected(endpoint("Foo", "161000", ["operator"]), text, {115}, True) is None  # operator corroborates
    assert rejected(endpoint("Bar", "115000", ["voltage"]), text, {115}, True) is None


def test_one_sided_dash_separates_terminals():
    assert locate_name("GTC: FOO - BAR CREEK -BAZ 500 KV NEW TRANSMISSION LINES, CONSTRUCT") == \
        "Foo - Bar Creek - Baz 500 kV New Transmission Lines"


def test_legacy_duplicates_need_exactly_one_legacy_project_and_one_claimant():
    from southeast.sertp import legacy_duplicates

    def rows(*names, baa="SOUTHERN"):
        return [{"baa": baa, "name": n} for n in names]

    legacy = [{"_id": "legacy:GPC:1", "name": "FOO - BAR 115KV REBUILD"},
              {"_id": "legacy:GPC:2", "name": "ZED - QUUX 230KV LINE"},
              {"_id": "legacy:GPC:3", "name": "QUUX - ZED 230KV RECONDUCTOR"},
              {"_id": "legacy:GPC:4", "name": "ALPHA 230/115KV BANK REPLACEMENT"},
              {"_id": "legacy:GPC:5", "name": "BRAVO - CHARLIE 115KV REBUILD"}]
    current = rows("BAR - FOO 115 KV TRANSMISSION LINE, REBUILD",       # reversed pair, one legacy match
                   "ZED - QUUX 230 KV TRANSMISSION LINE, UPGRADE",      # two legacy matches: stays new
                   "ALPHA 230/115 KV BANK, REPLACE",                    # same site and kV
                   "ALPHA 500 KV BUS, EXPANSION",                       # same site, other kV: stays new
                   "BRAVO - CHARLIE 115 KV (BLACK), REBUILD",           # two SERTP rows claim one legacy
                   "BRAVO - CHARLIE 115 KV (WHITE), REBUILD")
    matched, kept = legacy_duplicates(current + rows("FOO - BAR 115 KV, REBUILD", baa="TVA"), legacy)
    assert {j: p["_id"] for j, p in matched.items()} == {0: "legacy:GPC:1", 2: "legacy:GPC:4"}
    assert sorted(kept) == [1, 4, 5]
