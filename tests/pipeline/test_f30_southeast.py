"""C27 assembly integration with explicitly synthetic additions and real committed base."""
import shutil
from copy import deepcopy

import pytest

from common import REPO_ROOT, write_json
from national.build import OUTPUTS, load_snapshot, validate_snapshot_values
from national.load import stage
from southeast.publish import ACTIVE_RELEASE, release_hash


def synthetic_release():
    evidence = {"publisher": "Synthetic fixture", "url": "https://example.com/synthetic", "artifact_sha256": "0" * 64,
                "locator": "row1", "source_date": None, "retrieved_at": "2025-01-01T00:00:00Z",
                "access_review": "Synthetic test input", "facts": "Synthetic construction project"}
    project = {"_id": "southeast:synthetic:1", "source_id": "synthetic-source", "native_id": "synthetic1",
               "name": "Synthetic project", "owner": None, "other_owners": [], "planning_region": None,
               "states": ["12"], "counties": [], "geography_basis": "Synthetic fixture", "status": None,
               "status_group": "unknown", "center": None, "location_review": "unlocated",
               "in_service": {"raw": None, "value": None, "precision": "unknown"},
               "evidence": {"page": None, "sheet": None, "row": 1, "source_sha256": "0" * 64,
                            "raw": {"source_evidence": [evidence]}}}
    source = {"_id": "synthetic-source", "title": "Synthetic plan", "publisher": "Synthetic fixture",
              "authority": "state_government", "role": "project_plan", "landing_url": evidence["url"],
              "download_url": evidence["url"], "publication_date": None, "vintage": None,
              "retrieved_at": evidence["retrieved_at"], "sha256": "0" * 64, "public_status": "verified_public",
              "import_status": "imported", "access_policy": "public_document", "planning_region": None,
              "states": ["12"], "notes": ["Synthetic test"], "project_count": 1}
    release = {"schema_version": "southeast-release-v1", "release_id": "synthetic-only", "producer": "fixture-producer",
               "created_at": "2025-02-01T00:00:00Z", "sources": [source], "projects": [project],
               "location_verifications": [], "project_events": [{"project_id": project["_id"], "events": [{
                   "id": "synthetic-event", "type": "certification", "date": "2025", "precision": "year",
                   "native_project_link": "synthetic1", "evidence": [evidence], "description": "Synthetic certification"}]}],
               "dispositions": [{"source_id": source["_id"], "locator": "row1", "disposition": "accepted",
                                 "project_id": project["_id"], "reason": "Synthetic test"}],
               "acquisition": [{"source_id": source["_id"], "scope": "Synthetic source", "row_locators": ["row1"],
                                "expected_source_rows": 1, "completeness": "complete", "enumeration_evidence": [evidence]}],
               "expected_counts": {"new_sources": 1, "new_projects": 1, "confirmed_projects": 0, "source_rows": 1},
               "coverage_notes": ["Synthetic test"], "identity_review": {
                   "reviewer": "fixture-reviewer", "reviewed_at": "2025-02-02T00:00:00Z", "decision": "approved",
                   "facts_sha256": "", "evidence": "Synthetic review"}}
    release["identity_review"]["facts_sha256"] = release_hash(release)
    return release


@pytest.fixture
def root(tmp_path):
    target = tmp_path / "data/national"
    target.mkdir(parents=True)
    for name in OUTPUTS:
        shutil.copyfile(REPO_ROOT / "data/national" / f"{name}.json", target / f"{name}.json")
    return tmp_path


@pytest.mark.parametrize("with_expansion", [False, True])
def test_southeast_assembles_after_existing_overlay_without_changing_legacy(root, with_expansion):
    if with_expansion:
        target = root / "data/expansion/releases/active.json"
        target.parent.mkdir(parents=True)
        shutil.copyfile(REPO_ROOT / "data/expansion/releases/active.json", target)
    baseline = load_snapshot(root)
    before = {p: p.read_bytes() for p in (root / "data/national").iterdir()}
    write_json(root / ACTIVE_RELEASE, synthetic_release())
    result = load_snapshot(root)
    assert load_snapshot(root) == result
    assert validate_snapshot_values(result) == []
    assert result["projects"][:-1] == baseline["projects"]
    assert result["sources"][:-1] == baseline["sources"]
    assert result["coverage"]["projects_total"] == baseline["coverage"]["projects_total"] + 1
    assert result["coverage"]["located_count"] == baseline["coverage"]["located_count"]
    assert result["coverage"]["southeast"]["new_projects"] == 1
    if with_expansion:
        assert result["coverage"]["expansion"] == baseline["coverage"]["expansion"]
    source = next(s for s in result["coverage"]["sources"] if s["source_id"] == "synthetic-source")
    assert source["project_count"] == 1 and source["located_count"] == 0
    staged = stage(result, "synthetic-dataset")["national_projects"][-1]
    assert staged["project_events"][0]["precision"] == "year" and staged["geo"] is None
    assert before == {p: p.read_bytes() for p in before}


def test_candidate_isolation_and_invalid_release_or_final_snapshot_fails(root):
    baseline = load_snapshot(root)
    write_json(root / "data/southeast/batches/active.json", {"invalid": "candidate"})
    assert load_snapshot(root) == baseline
    release = synthetic_release()
    broken = deepcopy(release)
    broken["projects"][0]["name"] = "Changed after review"
    write_json(root / ACTIVE_RELEASE, broken)
    with pytest.raises(ValueError, match="identity review"):
        load_snapshot(root)
    # Producer-valid evidence still must meet the final national source-hash contract.
    broken = deepcopy(release)
    broken["projects"][0]["evidence"]["source_sha256"] = "1" * 64
    broken["identity_review"]["facts_sha256"] = release_hash(broken)
    write_json(root / ACTIVE_RELEASE, broken)
    with pytest.raises(ValueError, match="assembled national snapshot validation failed"):
        load_snapshot(root)
