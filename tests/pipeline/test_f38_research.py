"""Protect the research/publication boundary and the actual 300-row worklist."""

from copy import deepcopy
from pathlib import Path

import pytest

from common import REPO_ROOT, load_json
from expansion.new_england import BATCH, SOURCE_ID, artifacts, facts_hash, replay
from national.registry import entries


def source_records():
    return [p for p in load_json(REPO_ROOT / 'data/national/projects.json') if p['source_id'] == SOURCE_ID]


def test_research_selection_reconciliation_and_no_publication():
    projects = source_records()
    outputs = artifacts(projects, entries()[SOURCE_ID])
    for relative, content in outputs.items():
        assert (REPO_ROOT / relative).read_text() == content
    cohort = load_json(REPO_ROOT / BATCH / 'research-cohort.json')
    selected = cohort['projects']
    assert len(selected) == len({p['_id'] for p in selected}) == 300
    assert sum(p['status_group'] == 'in_service' for p in selected) == 254
    assert {p['_id'] for p in selected[:46]} == {
        p['_id'] for p in projects if p['status_group'] in {'planned', 'proposed', 'under_construction'}
    }
    assert all(p['center'] is None for p in selected)
    assert not cohort['summary']['publication_eligible']
    assert cohort['summary']['confirmed_location_count'] == 0
    ledger = load_json(REPO_ROOT / BATCH / 'dispositions.json')
    assert len(ledger) == 1024
    assert {p['project_id'] for p in ledger} == {p['_id'] for p in projects}
    assert sum(p['disposition'] == 'selected_for_research' for p in ledger) == 300


@pytest.mark.parametrize('mutation', ['coordinate', 'duplicate', 'source_hash', 'status', 'state'])
def test_unreviewed_changes_fail_closed(mutation):
    projects = deepcopy(source_records())
    if mutation == 'coordinate':
        projects[0]['center'] = {'type': 'Point', 'coordinates': [-71, 42]}
    elif mutation == 'duplicate':
        projects.append(projects[0])
    elif mutation == 'source_hash':
        projects[0]['evidence']['source_sha256'] = '0' * 64
    elif mutation == 'status':
        projects[0]['status_group'] = 'unknown'
    else:
        projects[0]['states'] = ['12']
    with pytest.raises(ValueError):
        artifacts(projects, entries()[SOURCE_ID])


def test_changed_evidence_changes_facts_binding():
    project = source_records()[0]
    changed = deepcopy(project)
    changed['evidence']['row'] += 1
    assert facts_hash(project) != facts_hash(changed)


def test_changed_workbook_is_rejected_before_parsing(tmp_path: Path):
    path = tmp_path / 'changed.xlsx'
    path.write_bytes(b'not the pinned public workbook')
    with pytest.raises(ValueError, match='SHA-256'):
        replay(path)
