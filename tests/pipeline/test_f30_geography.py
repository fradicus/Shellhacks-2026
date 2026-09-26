from common import REPO_ROOT, load_json


def test_complete_census_reference_keeps_leading_zeroes_and_antimeridian():
    geography = load_json(REPO_ROOT / "data" / "national" / "geography.json")
    assert geography["counts"] == {
        "regions": 4,
        "divisions": 9,
        "states_and_dc": 51,
        "states_only": 50,
        "districts": 1,
        "territories": 5,
        "counties_primary": 3_144,
        "territory_county_equivalents": 91,
        "counties_total": 3_235,
        "gazetteer_2026_counties": 3_222,
    }
    states = {state["state_fips"]: state for state in geography["states"]}
    counties = {county["county_geoid"]: county for county in geography["counties"]}
    assert states["01"]["usps"] == "AL"
    assert counties["01001"]["county_fips"] == "001"
    assert states["02"]["bounds"]["crosses_antimeridian"] is True
    assert states["02"]["bounds"]["fit_east_unwrapped"] > 180
    territories = [state for state in states.values() if state["scope"] == "territory"]
    assert all(state["census_region_code"] is None and state["census_division_code"] is None for state in territories)


def test_reference_points_are_labeled_as_census_reference_only():
    geography = load_json(REPO_ROOT / "data" / "national" / "geography.json")
    assert geography["states"][0]["representative_point"]
    notes = " ".join(geography["provenance"]["notes"])
    assert "not project geometry" in notes
