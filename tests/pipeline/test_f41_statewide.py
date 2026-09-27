"""Statewide matching must require exact name, named county and one OSM identity."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from texas.statewide import (DUPLICATES, build, canonical_rows, derive_facilities, facility_index,
                            inside_geometry, locate, match_terminal)

ROOT = Path(__file__).resolve().parents[2]


def ledger():
    return {'counties': {'alpha': {'geoid': '48001', 'name': 'Alpha County'},
                         'beta': {'geoid': '48003', 'name': 'Beta County'}},
            'facilities': [
                {'osm_id': 'way/1', 'names': {'name': 'First Substation', 'alt_name': 'Old First',
                                            'old_name': 'First Substation'},
                 'county': 'alpha', 'lat': 30.0, 'lon': -100.0},
                {'osm_id': 'way/2', 'names': {'name': 'Second'}, 'county': 'beta', 'lat': 32.0, 'lon': -98.0},
            ]}


def row():
    return {'terminal_from': 'FIRST', 'county_from_raw': 'Alpha County',
            'terminal_to': 'Second station', 'county_to_raw': 'Beta'}


def test_aliases_are_exact_and_same_osm_element_is_counted_once():
    index = facility_index(ledger())
    assert match_terminal('old first', 'Alpha', index)['status'] == 'unique'
    assert match_terminal('First', 'Alpha', index)['status'] == 'unique'
    assert match_terminal('Frist', 'Alpha', index)['status'] == 'no_match'
    assert match_terminal('First', 'Beta', index)['status'] == 'no_match'


def test_two_surviving_osm_identities_are_ambiguous():
    data = ledger()
    data['facilities'].append({**data['facilities'][0], 'osm_id': 'node/3'})
    result = match_terminal('First', 'Alpha', facility_index(data))
    assert result['status'] == 'ambiguous'
    assert len(result['matches']) == 2
    location = locate(row(), data, facility_index(data))
    assert location['center']['basis'] == 'one'
    assert location['center']['lat'] == 32.0


def test_full_partial_area_only_and_unlocated_have_distinct_geometry():
    data, source = ledger(), row()
    index = facility_index(data)
    full = locate(source, data, index)
    assert full['center']['basis'] == 'two'
    assert (full['center']['lat'], full['center']['lon']) == (31.0, -99.0)
    source['terminal_to'] = 'Unknown'
    partial = locate(source, data, index)
    assert partial['center']['basis'] == 'one'
    assert (partial['center']['lat'], partial['center']['lon']) == (30.0, -100.0)
    source['terminal_from'] = 'Unknown'
    area = locate(source, data, index)
    assert area['tier'] == 'area_only' and area['center'] is None
    source.update(county_from_raw='Typo', county_to_raw=None)
    missing = locate(source, data, index)
    assert missing['tier'] == 'unlocated' and missing['center'] is None


def test_county_dots_preserve_all_named_counties_without_exact_center():
    data = ledger()
    data['counties']['alpha']['representative_point'] = [-100.5, 30.5]
    data['counties']['beta']['representative_point'] = [-98.5, 32.5]
    source = {**row(), 'terminal_from': 'Unknown', 'terminal_to': None,
              'county_from_raw': 'Alpha and Beta', 'county_to_raw': 'Alpha'}
    result = locate(source, data, facility_index(data))
    assert result['center'] is None
    assert result['tier'] == 'area_only'
    assert [a['county_geoid'] for a in result['display_anchors']] == ['48001', '48003']
    assert result['display_anchors'][0]['lon'] == -100.5
    assert locate(row(), data, facility_index(data))['display_anchors'] == []


def test_polygon_holes_boundaries_and_multipolygons():
    outer = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    hole = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]
    geom = {'type': 'Polygon', 'coordinates': [outer, hole]}
    assert inside_geometry(1, 1, geom)
    assert not inside_geometry(5, 5, geom)
    assert not inside_geometry(0, 1, geom)
    assert not inside_geometry(4, 5, geom)
    assert inside_geometry(1, 1, {'type': 'MultiPolygon', 'coordinates': [[outer, hole]]})


def test_facility_county_requires_containment_and_unique_county():
    ring = [[-101, 29], [-99, 29], [-99, 31], [-101, 31], [-101, 29]]
    feature = {'properties': {'NAME': 'Alpha County', 'GEOID': '48001'},
               'geometry': {'type': 'Polygon', 'coordinates': [ring]}}
    osm = {'elements': [{'type': 'node', 'id': 1, 'lat': 30, 'lon': -100,
                         'tags': {'power': 'substation', 'name': 'First'}}]}
    result = derive_facilities(osm, {'features': [feature]})
    assert result['facilities'][0]['county'] == 'alpha'
    other = deepcopy(feature)
    other['properties'] = {'NAME': 'Beta County', 'GEOID': '48003'}
    result = derive_facilities(osm, {'features': [feature, other]})
    assert result['facilities'][0]['county'] is None
    assert result['facilities'][0]['county_disposition'] == 'ambiguous_county'


def test_all_five_future_duplicates_retain_both_citations_once():
    rows = json.loads((ROOT / 'data/texas/future-observations.json').read_text())
    canonical = canonical_rows(rows)
    duplicates = {r['native_id']: citations for r, citations in canonical if len(citations) > 1}
    assert set(duplicates) == DUPLICATES
    assert all(len(citations) == 2 for citations in duplicates.values())
    assert len(canonical) == 1424
    changed = deepcopy(rows)
    second = next(r for r in changed if r['native_id'] == '110733' and r['row'] == 364)
    second['terminal_from'] = 'Conflicting terminal'
    with pytest.raises(ValueError, match='conflicting duplicate'):
        canonical_rows(changed)


def test_committed_statewide_projects_replay_and_preserve_unknowns():
    folder = ROOT / 'data/texas'
    rows = sum([json.loads((folder / f'{s}-observations.json').read_text())
                for s in ('planned', 'future', 'completed')], [])
    facilities = json.loads((folder / 'statewide/facilities.json').read_text())
    source_hash = json.loads((folder / 'publication-source.json').read_text())['sha256']
    projects, observations, summary = build(rows, facilities, source_hash)
    assert projects == json.loads((folder / 'statewide/projects.json').read_text())
    assert len(projects) == 2044 and len(observations) == 2049
    assert summary['terminals']['unique'] == 821 and summary['terminals']['ambiguous'] == 80
    assert summary['project_tiers'] == {'candidate': 635, 'full': 183, 'partial': 452,
                                       'area_only': 1218, 'unlocated': 191}
    assert all(p['center'] is None for p in projects if p['location_evidence']['tier'] != 'candidate')
    assert not any(p['location_review'] == 'confirmed' for p in projects)
    county_projects = [p for p in projects if 'approximate_location' in p]
    assert len(county_projects) == 1218
    assert sum(len(p['approximate_location']['anchors']) for p in county_projects) == 1407
    assert all(p['approximate_location']['eligible_for_matching'] is False for p in county_projects)
    typo = next(p for p in projects if p['native_id'] == '105424')
    assert typo['counties'] == [] and typo['center'] is None
    assert typo['evidence']['raw']['county_from_raw'] == 'Stonwall'
