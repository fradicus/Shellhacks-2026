"""Exclusive C32/C29 Texas assembly, rollback and fail-closed loader boundary."""

import shutil

import pytest

from common import REPO_ROOT
from national import load as loader
from national.build import OUTPUTS, load_snapshot, validate_snapshot_values
from texas.publish import ACTIVE, FILES
from texas.statewide_publish import ACTIVE as STATEWIDE_ACTIVE
from texas.statewide_publish import FILES as STATEWIDE_FILES


@pytest.fixture
def root(tmp_path):
    national = tmp_path / "data" / "national"
    national.mkdir(parents=True)
    for name in OUTPUTS:
        shutil.copyfile(REPO_ROOT / "data" / "national" / f"{name}.json", national / f"{name}.json")
    shutil.copyfile(REPO_ROOT / "data/national/source-manifest.json", national / "source-manifest.json")
    texas = tmp_path / "data" / "texas"
    texas.mkdir(parents=True)
    for filename in set(FILES.values()) | set(STATEWIDE_FILES.values()):
        (texas / filename).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / "data" / "texas" / filename, texas / filename)
    return tmp_path


def test_only_fixed_active_file_assembles_texas_and_preserves_base(root):
    baseline = load_snapshot(root)
    original = {path.name: path.read_bytes() for path in (root / "data" / "national").iterdir()}
    assert "texas" not in baseline["coverage"]
    assert load_snapshot(root) == baseline  # research files cannot activate on their own

    active = root / ACTIVE
    active.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / ACTIVE, active)
    result = load_snapshot(root)
    assert validate_snapshot_values(result) == []
    assert result["projects"][:-8] == baseline["projects"]
    assert result["sources"][:-1] == baseline["sources"]
    assert result["coverage"]["projects_total"] == baseline["coverage"]["projects_total"] + 8
    assert result["coverage"]["located_count"] == baseline["coverage"]["located_count"] + 8
    assert result["coverage"]["texas"]["candidate_projects"] == 8
    texas_source = next(s for s in result["coverage"]["sources"] if s["source_id"] == "ercot-tpit-2026-07")
    assert texas_source["project_count"] == texas_source["located_count"] == 8
    assert {p["location_review"] for p in result["projects"][-8:]} == {"unreviewed"}
    assert original == {path.name: path.read_bytes() for path in (root / "data" / "national").iterdir()}


def test_invalid_texas_file_fails_before_database_staging(root, monkeypatch):
    active = root / ACTIVE
    active.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / ACTIVE, active)
    with (root / "data" / "texas" / "publication-candidates.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="Texas release file hash changed"):
        load_snapshot(root)
    monkeypatch.setattr(loader, "REPO_ROOT", root)
    monkeypatch.setattr(loader, "dataset_id", lambda: pytest.fail("invalid Texas release reached staging"))
    assert loader.main() == 1


def test_statewide_replaces_fallback_and_keeps_county_anchors_out_of_geo(root):
    baseline = load_snapshot(root)
    for path in (ACTIVE, STATEWIDE_ACTIVE):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / path, root / path)
    result = load_snapshot(root)
    assert validate_snapshot_values(result) == []
    assert result['projects'][:-2044] == baseline['projects']
    assert result['sources'][:-1] == baseline['sources']
    assert result['coverage']['projects_total'] == baseline['coverage']['projects_total'] + 2044
    assert result['coverage']['located_count'] == baseline['coverage']['located_count'] + 635
    projects = [p for p in result['projects'] if p['source_id'] == 'ercot-tpit-2026-07']
    assert len(projects) == len({p['_id'] for p in projects}) == 2044
    staged = loader.stage(result, 'test-statewide')['national_projects']
    county = [p for p in staged if 'approximate_location' in p]
    assert len(county) == 1218
    assert all(p['geo'] is None and p['center'] is None for p in county)
    assert all(p['approximate_location']['eligible_for_matching'] is False for p in county)
    (root / STATEWIDE_ACTIVE).unlink()
    assert load_snapshot(root)['coverage']['texas']['candidate_projects'] == 8


def test_invalid_statewide_never_falls_back_or_reaches_staging(root, monkeypatch):
    for path in (ACTIVE, STATEWIDE_ACTIVE):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / path, root / path)
    (root / 'data/texas/statewide/projects.json').write_text('[]')
    with pytest.raises(ValueError, match='statewide release file hash changed'):
        load_snapshot(root)
    monkeypatch.setattr(loader, 'REPO_ROOT', root)
    monkeypatch.setattr(loader, 'dataset_id', lambda: pytest.fail('invalid statewide release reached staging'))
    assert loader.main() == 1


def test_real_earlier_overlays_remain_when_texas_is_assembled():
    result = load_snapshot(REPO_ROOT)
    assert validate_snapshot_values(result) == []
    assert result["coverage"]["texas"]["project_tiers"]["candidate"] == 635
    for name in ("expansion", "southeast", "mid_atlantic"):
        assert name in result["coverage"]
    assert len([p for p in result["projects"] if p["source_id"] == "ercot-tpit-2026-07"]) == 2044
