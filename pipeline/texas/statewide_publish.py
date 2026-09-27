"""Replay the fixed C32 statewide release before national assembly."""
from __future__ import annotations

import hashlib
import math
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlencode

from common import load_json, validate
from osm.fetch import OVERPASS_URL, USER_AGENT
from texas.publish import _time
from texas.statewide import ATTRIBUTION, DUPLICATES, LICENSE_URL, build
from texas.statewide_acquire import COUNTY_PARAMS, COUNTY_URL, QUERY
from texas.tpit import SOURCE_ID

ACTIVE = Path('data/texas/statewide/releases/active.json')
FILES = {name: f'statewide/{name}.json'
         for name in ('facilities', 'projects', 'observations', 'summary', 'source')}
FILES.update({name: f'{name}-observations.json' for name in ('planned', 'future', 'completed')})
FILES['source_audit'] = 'source-audit.json'
RELEASE_ID = 'texas-ercot-2026-07-statewide-1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_ledger(ledger, root):
    if (ledger['crs'] != 'EPSG:4326' or ledger['attribution'] != ATTRIBUTION
            or ledger['license_url'] != LICENSE_URL or len(ledger['facilities']) != 3303
            or len(ledger['counties']) != 254):
        raise ValueError('Texas facility enumeration or attribution changed')
    _time(ledger['osm_base_timestamp'])
    for key, url, query in [('osm', OVERPASS_URL, QUERY),
                            ('counties', COUNTY_URL + '?' + urlencode(COUNTY_PARAMS), COUNTY_PARAMS)]:
        receipt = ledger['provenance'][key]
        _time(receipt['retrieved_at'])
        if (receipt['url'] != url or receipt['query'] != query or receipt['user_agent'] != USER_AGENT
                or not re.fullmatch('[a-f0-9]{64}', receipt['sha256']) or receipt['bytes'] <= 0):
            raise ValueError('Texas geography acquisition receipt changed')
    geography = load_json(root / 'data/national/geography.json')
    counties = {c['county_geoid']: c for c in geography['counties'] if c['state_fips'] == '48'}
    if {c['geoid'] for c in ledger['counties'].values()} != set(counties):
        raise ValueError('Texas county identity changed')
    for county in ledger['counties'].values():
        if county['representative_point'] != counties[county['geoid']]['representative_point']:
            raise ValueError('Texas county display reference changed')
    manifest = load_json(root / 'data/national/source-manifest.json')
    reference = next(s for s in manifest if s['id'] == 'census-2026-gaz-counties-national')
    if ledger['county_reference_provenance'] != {
        k: reference[k] for k in ('id', 'url', 'sha256', 'retrieved_at')
    }:
        raise ValueError('Texas county reference provenance changed')
    for point in ledger['facilities']:
        if (not re.fullmatch(r'(node|way|relation)/[1-9][0-9]*', point['osm_id'])
                or point['url'] != f"https://www.openstreetmap.org/{point['osm_id']}"
                or not point['names'].get('name')
                or set(point['names']) - {'name', 'alt_name', 'old_name'}
                or not all(isinstance(point[k], (int, float)) and math.isfinite(point[k]) for k in ('lat', 'lon'))
                or not (-107 < point['lon'] < -93 and 25 < point['lat'] < 37)):
            raise ValueError('invalid Texas facility reference')
        if point['county'] is not None and (
            point['county'] not in ledger['counties'] or point['county_disposition'] != 'inside_one'
        ):
            raise ValueError('invalid Texas facility county assignment')


def apply_release(snapshot: dict, root: Path) -> dict:
    if not (root / ACTIVE).exists():
        return snapshot
    release = load_json(root / ACTIVE)
    if (release['policy'] != 'C32' or release['release_id'] != RELEASE_ID
            or release['source_id'] != SOURCE_ID or set(release['files']) != set(FILES)):
        raise ValueError('Texas statewide release manifest changed')
    folder = root / 'data/texas'
    for key, filename in FILES.items():
        if sha(folder / filename) != release['files'][key]:
            raise ValueError(f'Texas statewide release file hash changed: {key}')
    data = {k: load_json(folder / name) for k, name in FILES.items()}
    source, audit, ledger = data['source'], data['source_audit'], data['facilities']
    validate(source, 'national-source')
    _time(source['retrieved_at'])
    if (source['_id'] != SOURCE_ID or source['sha256'] != audit['sha256']
            or source['sha256'] != audit['reacquired_sha256']
            or source['retrieved_at'] != audit['reacquired_at']
            or source['download_url'] != audit['url'] or source['publication_date'] != audit['publication_date']
            or source['vintage'] != audit['source_as_of'] or source['project_count'] != 2044
            or source['role'] != 'project_plan' or source['import_status'] != 'imported'
            or release['source_sha256'] != source['sha256']
            or release['geography_provenance'] != ledger['provenance']):
        raise ValueError('Texas statewide source identity or acquisition changed')
    check_ledger(ledger, root)
    if [len(data[k]) for k in ('planned', 'future', 'completed')] != [358, 1429, 262]:
        raise ValueError('Texas statewide source enumeration changed')
    rows = data['planned'] + data['future'] + data['completed']
    projects, observations, summary = build(rows, ledger, source['sha256'])
    if (projects != data['projects'] or observations != data['observations'] or summary != data['summary']
            or summary != release['expected_counts'] or summary['canonical_projects'] != 2044
            or set(summary['duplicate_ids']) != DUPLICATES
            or [p['_id'] for p in projects] != release['project_ids']):
        raise ValueError('Texas statewide replay or identity reconciliation failed')
    existing = {p['_id'] for p in snapshot['projects']}
    if (existing.intersection(release['project_ids'])
            or any(p['source_id'] == SOURCE_ID for p in snapshot['projects'])
            or any(s['_id'] == SOURCE_ID for s in snapshot['sources'])):
        raise ValueError('Texas statewide source already present')
    result = deepcopy(snapshot)
    result['sources'].append(source)
    result['projects'].extend(projects)
    result['coverage']['texas'] = {
        'release_id': RELEASE_ID, 'source_id': SOURCE_ID, **summary,
        'independently_confirmed_projects': 0,
        'county_reference_projects': sum('approximate_location' in p for p in projects),
        'county_reference_anchors': sum(len(p.get('approximate_location', {}).get('anchors', [])) for p in projects),
        'distinct_candidate_centers': len({(p['center']['lat'], p['center']['lon']) for p in projects if p['center']}),
        'attribution': ATTRIBUTION, 'license_url': LICENSE_URL,
        'notes': 'ERCOT TPIT source coverage; county dots are display references, not project sites.',
    }
    return result
