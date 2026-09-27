"""Fail closed before assembly, including repinned but unreconciled edits."""
import json
import shutil
from pathlib import Path

import pytest

from texas.statewide_publish import ACTIVE, FILES, apply_release, sha

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def release_root(tmp_path):
    paths = [ACTIVE, *[Path('data/texas') / p for p in FILES.values()],
             Path('data/national/geography.json'), Path('data/national/source-manifest.json')]
    for path in paths:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, tmp_path / path)
    return tmp_path


def empty_snapshot():
    return {'sources': [], 'projects': [], 'coverage': {}}


def repin(root, key, value):
    path = root / 'data/texas' / FILES[key]
    path.write_text(json.dumps(value))
    release = json.loads((root / ACTIVE).read_text())
    release['files'][key] = sha(path)
    (root / ACTIVE).write_text(json.dumps(release))


def test_statewide_release_preserves_input_and_rejects_double_publication():
    original = empty_snapshot()
    result = apply_release(original, ROOT)
    assert original == empty_snapshot()
    assert len(result['projects']) == 2044
    assert result['coverage']['texas']['county_reference_projects'] == 1218
    assert result['coverage']['texas']['county_reference_anchors'] == 1407
    with pytest.raises(ValueError, match='already present'):
        apply_release(result, ROOT)


def test_missing_is_noop_and_changed_hash_fails(release_root):
    original = empty_snapshot()
    (release_root / 'data/texas/statewide/projects.json').write_text('[]')
    with pytest.raises(ValueError, match='file hash changed: projects'):
        apply_release(original, release_root)
    (release_root / ACTIVE).unlink()
    assert apply_release(original, release_root) is original


def test_repinning_a_county_anchor_as_exact_geometry_fails(release_root):
    projects = json.loads((release_root / 'data/texas/statewide/projects.json').read_text())
    project = next(p for p in projects if 'approximate_location' in p)
    anchor = project['approximate_location']['anchors'][0]
    project['center'] = {'lat': anchor['lat'], 'lon': anchor['lon'], 'basis': 'one', 'evidence': 'county'}
    repin(release_root, 'projects', projects)
    with pytest.raises(ValueError, match='replay'):
        apply_release(empty_snapshot(), release_root)


def test_repinning_an_unattributed_county_reference_fails(release_root):
    ledger = json.loads((release_root / 'data/texas/statewide/facilities.json').read_text())
    next(iter(ledger['counties'].values()))['representative_point'][0] += 0.1
    repin(release_root, 'facilities', ledger)
    with pytest.raises(ValueError, match='county display reference'):
        apply_release(empty_snapshot(), release_root)
