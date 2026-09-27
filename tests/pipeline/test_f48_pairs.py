import copy
import math
import random
from itertools import combinations

import pytest

from matches.core import EARTH_RADIUS_MI, haversine_mi
from national_pairs.build import exclusion, generate, identities, owner_index

LEDGER = {"version": "test-only", "entries": [
    {"identities": ["a"], "aliases": ["Alpha", "A Inc"], "evidence": ["test fixture"]},
    {"identities": ["b"], "aliases": ["Beta"], "evidence": ["test fixture"]},
    {"identities": ["c"], "aliases": ["Gamma"], "evidence": ["test fixture"]},
]}


def project(key, lat=30, lon=-95, owner="Alpha", **patch):
    return {"_id": key, "owner": owner, "other_owners": [], "states": ["48"],
            "planning_region": "ERCOT", "status_group": "planned", "location_review": "confirmed",
            "center": {"lat": lat, "lon": lon, "basis": "source_point"},
            "in_service": {"value": "2028-01-01", "precision": "day"}, **patch}


def run(rows):
    return generate({"projects": rows, "geography": {"states": [
        {"state_fips": "48", "census_region_code": "3"}, {"state_fips": "40", "census_region_code": "3"},
    ]}}, LEDGER)


def test_exact_cutoff_and_bands_are_unrounded():
    delta = math.degrees(25 / EARTH_RADIUS_MI)
    assert not run([project("a", 0, 0), project("b", delta, 0, "Beta")])["pairs"]
    assert run([project("a", 0, 0), project("b", delta - 1e-8, 0, "Beta")])["pairs"][0]["band"] == 1
    assert run([project("a"), project("b", owner="Beta")])["pairs"][0]["band"] == 0


def test_aliases_joint_owners_unknowns_and_ambiguous_ledger():
    assert not run([project("a"), project("b", owner=" a INC ")])["pairs"]
    assert not run([project("a"), project("b", owner="Beta", other_owners=["Alpha"])])["pairs"]
    assert run([project("a", owner=None)])["coverage"]["excluded"] == {"unresolved_owner": 1}
    assert identities(project("a", other_owners=["Unknown"]), owner_index(LEDGER)) is None
    ledger = copy.deepcopy(LEDGER)
    ledger["entries"][1]["aliases"].append("Alpha")
    with pytest.raises(ValueError, match="ambiguous"):
        owner_index(ledger)


def test_eligibility_and_duplicate_ids():
    for patch in ({"center": None}, {"location_review": "rejected"}, {"location_review": "needs_review"},
                  {"status_group": "in_service"}, {"status_group": "cancelled"},
                  {"location_candidate": {"tier": "county_reference"}},
                  {"center": {"lat": math.nan, "lon": 0}}, {"center": {"lat": 95, "lon": 0}}):
        assert exclusion(project("a", **patch))
    assert exclusion(project("legacy:a")) == "legacy"
    with pytest.raises(ValueError, match="duplicate"):
        run([project("a"), project("a")])


def test_dates_tiers_scope_and_stable_ids_without_mutation():
    a = project("a", states=["48", "40"])
    b = project("b", owner="Beta", states=["40"], location_review="unreviewed",
                in_service={"value": "2028-01", "precision": "month"})
    rows = [a, b]
    before = copy.deepcopy(rows)
    result = run(rows)["pairs"][0]
    assert result["time_gap_days"] is None and result["tier"] == "tentative"
    assert result["shared_states"] == ["40"] and result["shared_regions"] == ["3"]
    assert result["shared_plans"] == ["ercot"]
    assert run(list(reversed(rows)))["pairs"][0] == result
    assert rows == before
    b["in_service"] = {"value": "2028-01-03", "precision": "day"}
    assert run(rows)["pairs"][0]["time_gap_days"] == 2


def test_grid_equals_brute_force_including_poles_and_date_line():
    rng = random.Random(48)
    rows = [project(str(i), rng.uniform(-89, 89), rng.uniform(-180, 180),
                    ["Alpha", "Beta", "Gamma"][i % 3]) for i in range(500)]
    # Dense random neighborhoods plus pole/date-line cases exercise bucket boundaries.
    rows += [project(f"dense{i}", 30 + rng.uniform(-1, 1), -95 + rng.uniform(-1, 1),
                     ["Alpha", "Beta"][i % 2]) for i in range(200)]
    rows += [project("pole-a", 89.99, 0), project("pole-b", 89.99, 179, "Beta"),
             project("date-a", 0, 179.99), project("date-b", 0, -179.99, "Beta")]
    expected = {tuple(sorted((a["_id"], b["_id"]))) for a, b in combinations(rows, 2)
                if a["owner"] != b["owner"] and haversine_mi(
                    a["center"]["lat"], a["center"]["lon"], b["center"]["lat"], b["center"]["lon"]) < 25}
    actual = run(rows)
    assert {(p["a"], p["b"]) for p in actual["pairs"]} == expected
    assert actual["coverage"]["distance_comparisons"] < len(rows) * (len(rows) - 1) / 4
    assert [p["rank"] for p in actual["pairs"]] == list(range(1, len(expected) + 1))
