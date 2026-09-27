"""Synthetic fixture checks for evidence gates; these locations are never published."""

import json
import math
from copy import deepcopy

import pytest
from common import REPO_ROOT, load_json
from expansion.new_england import facts_hash
from expansion.publish import ACTIVE_RELEASE, apply_release, record_hash


@pytest.fixture
def case(tmp_path):
    project = next(p for p in load_json(REPO_ROOT / 'data/national/projects.json') if p['_id'] == 'iso-ne:1617')
    e = {'publisher': 'Synthetic test publisher', 'url': 'https://example.test/fixture',
         'artifact_sha256': 'a' * 64, 'locator': 'synthetic fixture only', 'source_date': None,
         'retrieved_at': '2026-09-26T00:00:00Z', 'access_review': 'synthetic fixture', 'facts': 'synthetic fixture'}
    point = {'role': 'site', 'facility_id': 'fixture:1', 'facility_name': 'Synthetic site',
             'lat': 44.0, 'lon': -72.0, 'original_geometry': {'crs': 'EPSG:4326', 'type': 'Point',
                                                         'coordinates': [-72.0, 44.0], 'transform': 'none'},
             'precision': None, 'uncertainty_m': None, 'geometry_evidence': [e], 'identity_evidence': [e],
             'identity_rationale': 'Synthetic test linkage'}
    record = {'project_id': project['_id'], 'project_facts_sha256': facts_hash(project), 'producer': 'test-producer',
              'location_kind': 'site', 'points': [point], 'reviews': [], 'events': []}
    review = {'id': 'fixture-review', 'reviewer': 'independent-test-reviewer', 'reviewed_at': '2026-09-26T01:00:00Z',
              'decision': 'confirmed', 'facts_sha256': record_hash(record), 'reason': 'Synthetic fixture verification'}
    record['reviews'].append(review)
    release = {'schema_version': 'expansion-release-v1', 'release_id': 'synthetic-fixture',
               'created_at': '2026-09-26T02:00:00Z', 'scope': 'synthetic test only',
               'records': [record], 'coverage_notes': ['Synthetic fixture, not real geography']}
    snapshot = {'projects': [project], 'coverage': {'located_count': 0}}
    path = tmp_path / ACTIVE_RELEASE
    path.parent.mkdir(parents=True)
    return snapshot, release, path, tmp_path


def run(case):
    snapshot, release, path, root = case
    path.write_text(json.dumps(release))
    return apply_release(snapshot, root)


def test_confirmed_record_projects_without_mutating_original_and_is_repeatable(case):
    original = deepcopy(case[0])
    result = run(case)
    assert case[0] == original
    assert result == run(case)
    p = result['projects'][0]
    assert p['center']['basis'] == 'source_point'
    assert p['location_review'] == 'confirmed'
    assert p['name'] == original['projects'][0]['name']
    assert result['coverage']['expansion']['confirmed_projects'] == 1


@pytest.mark.parametrize('decision', ['insufficient', 'conflicting', 'rejected', 'no_review', 'stale'])
def test_unconfirmed_coordinates_cannot_activate(case, decision):
    record = case[1]['records'][0]
    if decision == 'no_review':
        record['reviews'] = []
    elif decision == 'stale':
        record['points'][0]['identity_rationale'] = 'changed after review'
    else:
        record['reviews'][0]['decision'] = decision
    result = run(case)
    assert result['projects'][0]['center'] is None
    assert result['coverage']['expansion']['confirmed_projects'] == 0


@pytest.mark.parametrize('problem', ['project_changed', 'self_review', 'duplicate', 'wrong_crs', 'reversed_axes',
                                     'duplicate_endpoint', 'wrong_role', 'unknown_id', 'future_review'])
def test_invalid_release_fails_before_original_data_is_modified(case, problem):
    record = case[1]['records'][0]
    if problem == 'project_changed':
        case[0]['projects'][0]['name'] = 'Changed original source fact'
    elif problem == 'self_review':
        record['reviews'][0]['reviewer'] = record['producer']
    elif problem == 'duplicate':
        case[1]['records'].append(deepcopy(record))
    elif problem == 'wrong_crs':
        record['points'][0]['original_geometry']['crs'] = 'EPSG:99999'
    elif problem == 'reversed_axes':
        record['points'][0]['lat'], record['points'][0]['lon'] = -72.0, 44.0
    elif problem == 'duplicate_endpoint':
        record['location_kind'] = 'line'
        record['points'][0]['role'] = 'a'
        record['points'].append(deepcopy(record['points'][0]))
    elif problem == 'wrong_role':
        record['points'][0]['role'] = 'a'
    elif problem == 'unknown_id':
        record['project_id'] = 'unknown-fixture'
    else:
        record['reviews'][0]['reviewed_at'] = '2200-01-01T00:00:00Z'
    before = deepcopy(case[0])
    with pytest.raises(ValueError):
        run(case)
    assert case[0] == before


def test_line_endpoints_use_arithmetic_mean_and_partial_is_explicit(case):
    record = case[1]['records'][0]
    record['location_kind'] = 'line'
    record['points'][0]['role'] = 'a'
    record['reviews'][0]['facts_sha256'] = record_hash(record)
    partial = run(case)
    assert partial['projects'][0]['center']['basis'] == 'one'
    assert partial['coverage']['expansion']['partial_endpoint_projects'] == 1
    other = deepcopy(record['points'][0])
    other.update(role='b', facility_id='fixture:2', lon=-70, lat=42)
    other['original_geometry']['coordinates'] = [-70, 42]
    record['points'].append(other)
    record['reviews'][0]['facts_sha256'] = record_hash(record)
    full = run(case)
    assert full['projects'][0]['center']['lon'] == -71
    assert full['projects'][0]['center']['lat'] == 43
    assert full['coverage']['expansion']['complete_endpoint_projects'] == 1


def test_web_mercator_recomputation_and_mutation_detection(case):
    record = case[1]['records'][0]
    point = record['points'][0]
    point['original_geometry'].update(crs='EPSG:3857', coordinates=[
        math.radians(-72) * 6378137, math.log(math.tan(math.pi / 4 + math.radians(44) / 2)) * 6378137])
    record['reviews'][0]['facts_sha256'] = record_hash(record)
    assert run(case)['coverage']['expansion']['confirmed_projects'] == 1
    point['original_geometry']['coordinates'][0] += 500
    record['reviews'][0]['facts_sha256'] = record_hash(record)
    with pytest.raises(ValueError, match='transformation'):
        run(case)


def test_missing_release_preserves_snapshot(case):
    assert apply_release(case[0], case[3]) is case[0]


def test_last_appended_review_controls_instead_of_an_earlier_confirmation(case):
    record = case[1]['records'][0]
    later = dict(record['reviews'][0], id='correction', decision='conflicting', reviewed_at='2026-09-26T01:01:00Z')
    record['reviews'].append(later)
    assert run(case)['projects'][0]['center'] is None


@pytest.mark.parametrize('problem', ['week_date', 'future_retrieval', 'blank_fact'])
def test_event_evidence_and_date_precision_cannot_bypass_review_gate(case, problem):
    record = case[1]['records'][0]
    event = {'id': 'synthetic-event', 'type': 'planned_milestone', 'date': '2026-10-01', 'precision': 'day',
             'native_project_link': '1617', 'evidence': deepcopy(record['points'][0]['identity_evidence']),
             'description': 'Synthetic fixture event, not a real milestone'}
    if problem == 'week_date':
        event['date'] = '2026-W39-1'
    elif problem == 'future_retrieval':
        event['evidence'][0]['retrieved_at'] = '2200-01-01T00:00:00Z'
    else:
        event['evidence'][0]['facts'] = ' '
    record['events'].append(event)
    record['reviews'][0]['facts_sha256'] = record_hash(record)
    with pytest.raises(ValueError):
        run(case)


def test_final_approval_requires_exact_set_and_current_facts(case):
    from expansion.finalize import approved_release
    record = deepcopy(case[1]['records'][0])
    approval = {'project_id': record['project_id'], 'review': record['reviews'].pop()}
    projects = case[0]['projects']
    release = approved_release([record], [approval], projects, 'synthetic-fixture')
    assert release['records'][0]['reviews'] == [approval['review']]
    assert record['reviews'] == []
    for bad in ([], [approval, approval]):
        with pytest.raises(ValueError):
            approved_release([record], bad, projects, 'synthetic-fixture')
    record['points'][0]['identity_rationale'] = 'changed after approval'
    with pytest.raises(ValueError, match='exact current'):
        approved_release([record], [approval], projects, 'synthetic-fixture')


def test_committed_release_reconciles_every_project_and_preserves_baseline():
    projects = load_json(REPO_ROOT / 'data/national/projects.json')
    original = deepcopy(projects)
    release = load_json(REPO_ROOT / ACTIVE_RELEASE)
    result = apply_release({'projects': projects, 'coverage': {}}, REPO_ROOT)
    assert projects == original
    assert len(result['projects']) == len(original) == 1286
    accepted = {r['project_id'] for r in release['records']}
    assert len(accepted) == 345
    assert sum(p['center'] is not None for p in result['projects']) == 414
    for before, after in zip(original, result['projects'], strict=True):
        if before['_id'] not in accepted:
            assert before == after
        else:
            assert after['location_review'] == 'confirmed'
            assert {k: v for k, v in after.items() if k not in {'center', 'location_review', 'location_verification'}} == {
                k: v for k, v in before.items() if k not in {'center', 'location_review', 'location_verification'}}
    ledger = load_json(REPO_ROOT / 'data/expansion/batches/new-england-locations/dispositions.json')
    assert len(ledger['records']) == len({r['project_id'] for r in ledger['records']}) == 1024
    assert sum(ledger['counts'].values()) == 1024
    assert {r['project_id'] for r in ledger['records'] if r['disposition'] == 'confirmed'} == accepted
