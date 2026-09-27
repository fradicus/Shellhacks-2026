"""F51: LADWP OSM aliases, the shared progress-report rules, and the committed release on the base snapshot."""

from camunis.build import LADWP, aliases, published_ids, with_aliases
from camunis.publish import apply_release
from common import REPO_ROOT, load_json
from interiorwest import apr
from national.build import OUTPUTS, _coverage, validate_snapshot_values

OPERATOR = "Los Angeles Department of Water and Power"


def test_aliases_come_only_from_ladwp_osm_names():
    assert aliases({"name": "Rinaldi Receiving Station", "operator": OPERATOR}) == ["Rinaldi"]
    assert aliases({"name": "Receiving Station E - Toluca", "operator": OPERATOR}) == ["RS-E", "Toluca"]
    assert aliases({"name": "Barren Ridge Switching Station", "operator": OPERATOR}) == ["Barren Ridge"]
    assert aliases({"name": "Kifer Receiving Station", "operator": "Silicon Valley Power"}) == []
    assert aliases({"name": "Rinaldi Receiving Station", "operator": None}) == []


def test_alias_places_a_territory_row_with_operator_corroboration():
    site = {"id": "way/1", "name": "Receiving Station E - Toluca", "norm": "RECEIVING STATION E TOLUCA",
            "operator": OPERATOR, "voltage": None, "state": "CA", "lat": 34.18, "lon": -118.36}
    row = {"owner": LADWP, "voltages_kv": [], "kind": "site", "facilities": ["RS-E"], "states": []}
    from camunis.build import OPERATOR_KEYS
    center, block = apr.locate(row, ["CA"], {"CA": with_aliases([site])}, OPERATOR_KEYS)
    assert center["basis"] == "source_point" and block["endpoints"][0]["corroboration"] == ["operator"]
    assert apr.locate(row, ["CA"], {"CA": [site]}, OPERATOR_KEYS)[0] is None  # no alias, no match


def test_committed_release_appends_unreviewed_candidates_in_their_states():
    base = {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    snapshot = apply_release(base, REPO_ROOT)
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "camunis" / "releases" / "active.json")
    released = {s["_id"] for s in load_json(REPO_ROOT / "data" / "camunis" / "sources.json")}
    added = [p for p in snapshot["projects"] if p["source_id"] in released]
    assert len(added) == release["expected_counts"]["projects"]
    assert all(set(p["states"]) <= {"06", "49", "32"} for p in added)
    assert all(p["location_review"] == ("unreviewed" if p["center"] else "unlocated") for p in added)
    assert not {p["_id"] for p in added} & published_ids()
    assert snapshot["coverage"]["camunis"]["independently_confirmed_projects"] == 0
