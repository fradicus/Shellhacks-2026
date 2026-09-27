"""Invented PJM fixtures check source precision and location semantics, never public-data stand-ins."""
from greatlakes.pjm import SHA256, SOURCE_ID, URL, project


def test_pjm_component_preserves_unknowns_and_separate_actual_and_planned_events():
    from expansion.pjm_mid_atlantic import FIELDS

    raw = dict.fromkeys(FIELDS, "")
    raw.update(UpgradeId="fixture-1", State="PA", Location="Fixture Alpha", Equipment="Substation",
               Description="Invented fixture substation rebuild", Voltage="230", TransmissionOwner="RAW-CODE",
               Status="IS", ActualInServiceDate="3/4/2025", ProjectedInServiceDate="2024")
    row = {"raw": raw, "native_id": raw["UpgradeId"], "row": 1, "locator": "/Upgrades/Upgrade[1]"}
    source = {"_id": SOURCE_ID, "sha256": SHA256, "download_url": URL, "retrieved_at": "2026-09-27T00:00:00Z"}
    facilities = [{"id": "node/fixture", "name": "Fixture Alpha", "state": "PA", "operator": None,
                   "voltage": "230000", "lat": 40.0, "lon": -77.0}]
    p = project(row, source, facilities)
    assert p["_id"] == f"{SOURCE_ID}:fixture-1"
    assert p["states"] == ["42"] and p["owner"] == "RAW-CODE"
    assert p["center"]["basis"] == "source_point" and p["location_review"] == "unreviewed"
    assert p["in_service"]["value"] == "2025-03-04"
    assert [e["type"] for e in p["project_events"]] == ["in_service"]
    assert p["evidence"]["raw"]["ProjectedInServiceDate"] == "2024"
    # A past projected date alone is never completion; no date becomes an invented day.
    raw.update(ActualInServiceDate="", Status="On Hold")
    p = project(row, source, facilities)
    assert p["status_group"] == "unknown" and p["in_service"]["value"] is None
    assert not p["project_events"]


def test_explicit_work_site_wins_over_circuit_location():
    from expansion.pjm_mid_atlantic import FIELDS

    raw = dict.fromkeys(FIELDS, "")
    raw.update(UpgradeId="fixture-2", State="PA", Location="Fixture Alpha - Fixture Bravo",
               Equipment="Circuit Breaker", Voltage="230",
               Description="Replace a circuit breaker at Fixture Alpha substation on the Alpha - Bravo line.")
    row = {"raw": raw, "native_id": raw["UpgradeId"], "row": 2, "locator": "/Upgrades/Upgrade[2]"}
    source = {"_id": SOURCE_ID, "sha256": SHA256, "download_url": URL, "retrieved_at": "2026-09-27T00:00:00Z"}
    facilities = [{"id": "node/fixture1", "name": "Fixture Alpha", "state": "PA", "operator": None,
                   "voltage": "230000", "lat": 40.0, "lon": -77.0},
                  {"id": "node/fixture2", "name": "Fixture Bravo", "state": "PA", "operator": None,
                   "voltage": "230000", "lat": 41.0, "lon": -78.0}]
    p = project(row, source, facilities)
    assert p["center"]["basis"] == "source_point"
    assert p["center"]["lat"] == 40.0 and p["center"]["lon"] == -77.0
