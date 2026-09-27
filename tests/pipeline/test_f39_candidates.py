from copy import deepcopy

import pytest

from common import REPO_ROOT, load_json, validate
from southeast.candidates import OBSERVATIONS, build


def test_pinned_candidates_preserve_identity_and_unknowns():
    batch = load_json(REPO_ROOT / OBSERVATIONS)
    result = build(batch)
    assert len(result["projects"]) == 17
    assert len(result["project_events"]) == 5
    for project in result["projects"]:
        validate(project, "national-project")
        assert project["center"] is None and project["owner"] is None
        assert project["status_group"] == "unknown"
        assert project["in_service"]["value"] is None
    bobwhite = next(p for p in result["projects"] if p["native_id"] == "TA07-14")
    assert bobwhite["evidence"]["raw"]["index"]["facts"]["certification_raw"] == "TA07-14"
    assert bobwhite["evidence"]["raw"]["identity_aliases"] == ["TA07-14", "TA06-14"]
    assert not result["publication_eligible"]
    altered = deepcopy(batch)
    detail = next(row for row in altered["observations"] if row["source_id"].endswith("bobwhite-manatee-line"))
    detail["facts"]["Certification #"] = "TA00-00"
    with pytest.raises(ValueError, match="conflicts"):
        build(altered)
