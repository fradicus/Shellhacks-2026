"""Pinned candidate integrity and explicit parser-layout failure cases."""
import pytest

from common import REPO_ROOT, load_json, validate
from expansion.new_england import facts_hash
from southeast.florida_release import CANDIDATE, deland_fields, detail_fields


def test_detail_parser_preserves_units_and_rejects_missing_or_duplicate_fields():
    fields = {"Licensee": "Synthetic utility", "Certification #": "TA00-00", "Date Certified": "1/2/2000",
              "Description": "Synthetic line", "Line Length": "Unknown", "Voltage": "230", "Counties Crossed:": "Leon"}
    rows = [f"<tr><td>{name}</td><td>{value}</td></tr>" for name, value in fields.items()]
    result = detail_fields("<table>" + "".join(rows) + "</table>")
    assert result["Voltage"] == "230" and result["Date Certified"] == "1/2/2000"
    with pytest.raises(ValueError, match="incomplete"):
        detail_fields("<table>" + "".join(rows[:-1]) + "</table>")
    with pytest.raises(ValueError, match="duplicate"):
        detail_fields("<table>" + "".join(rows + [rows[0]]) + "</table>")


def test_deland_requires_explicit_narrative_layout_and_does_not_invent_certification_date():
    # Synthetic reduced layout reproduces the required public-source identity anchors.
    html = ('<div property="schema:text"><p>TA25-20 26.26 miles, DeLand West Substation in Volusia County '
            'to Dona Vista Substation in Lake County</p></div>')
    result = deland_fields(html)
    assert result["Date Certified"] is None and result["Licensee"] is None
    with pytest.raises(ValueError, match="layout"):
        deland_fields("<p>Missing required container</p>")
    with pytest.raises(ValueError, match="facts changed"):
        deland_fields(html.replace("26.26", "99"))


def test_committed_candidate_preserves_unknown_status_history_and_exact_project_hash():
    release = load_json(REPO_ROOT / CANDIDATE)
    assert len(release["projects"]) == len(release["project_events"]) == len(release["dispositions"]) == 17
    assert len({p["native_id"] for p in release["projects"]}) == 17
    for project in release["projects"]:
        validate(project, "national-project")
        assert project["status_group"] == "unknown" and project["in_service"]["value"] is None
        assert project["center"] is None
        assert project["evidence"]["source_sha256"] == release["sources"][0]["sha256"]
    record = release["location_verifications"][0]
    hopkins = next(p for p in release["projects"] if p["_id"] == record["project_id"])
    assert record["project_facts_sha256"] == facts_hash(hopkins)
    assert record["points"][0]["uncertainty_m"] is None
    bobwhite = next(p for p in release["projects"] if p["native_id"] == "TA07-14")
    assert bobwhite["evidence"]["raw"]["identity_aliases"] == ["TA07-14", "TA06-14"]
    duval = next(p for p in release["projects"] if p["native_id"] == "TA81-03")
    assert "Kathleen" not in duval["description"]
    assert "Kathleen" in duval["evidence"]["raw"]["detail"]["Description"]
    deland = next(row for row in release["project_events"] if row["project_id"].endswith("ta25-20"))
    assert "legal effective date is not established" in deland["events"][0]["description"]


def test_reviewed_release_integrates_without_changing_prior_corpus(tmp_path):
    """Exercise real publication, retained unknowns and loader projection together."""
    import shutil

    from national.build import load_snapshot
    from national.load import stage
    from southeast.publish import ACTIVE_RELEASE

    shutil.copytree(REPO_ROOT / 'data/national', tmp_path / 'data/national')
    shutil.copytree(REPO_ROOT / 'data/expansion', tmp_path / 'data/expansion')
    baseline = load_snapshot(tmp_path)
    target = tmp_path / ACTIVE_RELEASE
    target.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / ACTIVE_RELEASE, target)
    assembled = load_snapshot(tmp_path)
    prior = {p['_id']: p for p in baseline['projects']}
    actual = {p['_id']: p for p in assembled['projects']}
    assert all(actual[key] == value for key, value in prior.items())
    added = [p for key, p in actual.items() if key not in prior]
    assert len(added) == 17
    assert sum(p['center'] is not None for p in added) == 1
    assert sum(len(p['project_events']) for p in added) == 17
    hopkins = actual['southeast:fl-dep:ta81-01']
    assert hopkins['location_review'] == 'confirmed'
    assert hopkins['status_group'] == 'unknown'
    assert hopkins['center']['lat'] == 30.452223774750653
    assert hopkins['center']['lon'] == -84.3994653300266
    assert hopkins['center']['basis'] == 'one'
    assert 'partial location' in hopkins['center']['evidence']
    records = stage(assembled, 'synthetic-test-dataset')['national_projects']
    loaded = next(p for p in records if p['id'] == hopkins['_id'])
    assert loaded['project_events'] == hopkins['project_events']
    assert loaded['geo']['coordinates'] == [hopkins['center']['lon'], hopkins['center']['lat']]
    assert assembled == load_snapshot(tmp_path)
