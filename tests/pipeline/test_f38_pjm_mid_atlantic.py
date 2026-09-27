"""Pinned input changes and distinct date semantics fail safely."""
import hashlib
from xml.etree import ElementTree

import pytest

from expansion.pjm_mid_atlantic import FIELDS, events, normalize, read_registry, source_date


def registry(tmp_path, **overrides):
    raw = dict.fromkeys(FIELDS, "") | {"UpgradeId": "example-native", "State": "NJ", "Status": "EP",
        "Description": "Fixture transmission work", "Location": "Fixture", "Equipment": "Transformer",
        "ProjectedInServiceDate": "6/1/2028", "ActualInServiceDate": "5/13/2026"} | overrides
    tree = ElementTree.Element("Upgrades")
    row = ElementTree.SubElement(tree, "Upgrade")
    for k, v in raw.items():
        ElementTree.SubElement(row, k).text = v
    path = tmp_path / "register.xml"
    path.write_bytes(ElementTree.tostring(tree))
    source = {"_id": "mid-atlantic:test", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "download_url": "https://example.org/fixture.xml", "retrieved_at": "2026-09-27T00:00:00Z"}
    return path, source


def test_source_change_never_normalizes(tmp_path):
    path, source = registry(tmp_path)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash"):
        read_registry(path, source)


def test_project_and_event_dates_preserve_meaning(tmp_path):
    path, source = registry(tmp_path)
    project = normalize(read_registry(path, source)[0], source)
    assert project["center"] is None and project["location_review"] == "unlocated"
    assert project["owner"] is None and project["counties"] == []
    assert project["in_service"]["value"] == "2026-05-13"
    assert project["status_group"] == "planned"  # Date selection never overrides reported lifecycle status.
    observations = {e["type"]: e["date"] for e in events(project)}
    assert observations == {"in_service": "2026-05-13", "planned_milestone": "2028-06-01"}
    assert source_date("TBD") == {"raw": "TBD", "value": None, "precision": "unknown"}


@pytest.mark.parametrize("change", ["duplicate_id", "missing_field", "duplicate_field", "unknown_row"])
def test_xml_shape_and_identity_fail_closed(tmp_path, change):
    path, source = registry(tmp_path)
    tree = ElementTree.fromstring(path.read_bytes())
    if change == "duplicate_id":
        tree.append(ElementTree.fromstring(ElementTree.tostring(tree[0])))
    elif change == "missing_field":
        tree[0].remove(tree[0].find("Voltage"))
    elif change == "duplicate_field":
        ElementTree.SubElement(tree[0], "Voltage").text = "230"
    else:
        ElementTree.SubElement(tree, "Unexpected")
    path.write_bytes(ElementTree.tostring(tree))
    source["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        read_registry(path, source)


def test_cross_assignment_and_unknown_state_require_review(tmp_path):
    for state in ["VA", "", "MD,VA"]:
        path, source = registry(tmp_path, State=state)
        with pytest.raises(ValueError, match="state review"):
            normalize(read_registry(path, source)[0], source)
