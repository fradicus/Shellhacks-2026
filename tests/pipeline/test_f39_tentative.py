"""F39 Florida tentative locations: name matching guards and committed-release replay."""
import pytest

from common import REPO_ROOT
from southeast import florida_tentative as ft


def facility(fid, name, operator, lat=28.0, lon=-82.0):
    # Explicit fixture facilities, not real public projects.
    return {'id': fid, 'url': f'https://www.openstreetmap.org/{fid}', 'power': 'substation',
            'names': {'name': name}, 'operator': operator, 'lat': lat, 'lon': lon}


def test_norm_strips_facility_words_and_expands_saint():
    assert ft.norm('ST. JOHNS SUBSTATION') == ft.norm('Saint Johns Substation') == 'SAINT JOHNS'
    assert ft.norm('ASPEN (CIRCUIT 2)') == 'ASPEN'


def test_match_rejects_other_utility_and_ambiguity():
    index = ft.osm_index({'osm': [facility('node/1', 'Fixture Substation', 'Florida Power & Light')]})
    assert ft.match('FIXTURE', 'TEC', index) == (None, 'operator_conflict')
    assert ft.match('FIXTURE', 'FPL', index)[1] == 'unique'
    two = ft.osm_index({'osm': [facility('node/1', 'Twin Substation', None), facility('node/2', 'Twin Substation', None)]})
    assert ft.match('TWIN', 'DEF', two) == (None, 'ambiguous:2')
    assert ft.match('UNSITED', 'TEC', two) == (None, 'unnamed')


def test_committed_release_replays_without_county_centers():
    result = ft.apply_release({'projects': [], 'sources': [], 'coverage': {}}, REPO_ROOT)
    summary = result['coverage']['florida_tentative']
    located = [p for p in result['projects'] if p['center']]
    assert summary['county_centers_used'] == 0 and summary['independently_confirmed'] == 0
    assert len(located) == summary['located_tentative'] >= 100
    assert all(p['location_review'] == 'unreviewed' and p['location_candidate']['label'] == 'Tentative' for p in located)
    assert all(24 < p['center']['lat'] < 31.1 and -87.7 < p['center']['lon'] < -79.9 for p in located)
    with pytest.raises(ValueError, match='overlaps existing identities'):
        ft.apply_release(result, REPO_ROOT)
