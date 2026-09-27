"""Exact terminal-name + county candidate references; no fuzzy or centroid matches."""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from common import validate
from texas.tpit import SOURCE_ID, _facility

NOTE = ('OSM facility reference point matched by exact name + county; '
        'not independently reviewed; not survey-grade.')
ATTRIBUTION = '© OpenStreetMap contributors; ODbL 1.0'
LICENSE_URL = 'https://opendatacommons.org/licenses/odbl/1-0/'
DUPLICATES = {'102795', '110733', '110749', '110751', '110753'}


def county_key(value):
    return re.sub(r'\s+county$', '', (value or '').strip(), flags=re.I).casefold()


def ring_location(x, y, ring):
    """0 outside, 1 inside, 2 on boundary (never an accepted county match)."""
    inside = False
    for (a, b), (c, d) in zip(ring, ring[1:] + ring[:1], strict=True):
        cross = (x - a) * (d - b) - (y - b) * (c - a)
        if abs(cross) < 1e-10 and min(a, c) <= x <= max(a, c) and min(b, d) <= y <= max(b, d):
            return 2
        if (b > y) != (d > y) and x < (c - a) * (y - b) / (d - b) + a:
            inside = not inside
    return int(inside)


def inside_geometry(lon, lat, geometry):
    if geometry['type'] not in {'Polygon', 'MultiPolygon'}:
        raise ValueError('county geometry must be Polygon or MultiPolygon')
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    for polygon in polygons:
        outer = ring_location(lon, lat, polygon[0])
        holes = [ring_location(lon, lat, ring) for ring in polygon[1:]]
        if outer == 1 and not any(holes):
            return True
    return False


def derive_facilities(osm, counties):
    if osm.get('remark') or counties.get('exceededTransferLimit'):
        raise ValueError('incomplete geography input')
    prepared, county_names = [], {}
    for feature in counties['features']:
        props, geometry = feature['properties'], feature['geometry']
        if not props['GEOID'].startswith('48'):
            raise ValueError('non-Texas county')
        key = county_key(props['NAME'])
        if key in county_names:
            raise ValueError('duplicate county name')
        county_names[key] = {'geoid': props['GEOID'], 'name': props['NAME']}
        polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        points = [p for polygon in polygons for ring in polygon for p in ring]
        bounds = (min(p[0] for p in points), min(p[1] for p in points),
                  max(p[0] for p in points), max(p[1] for p in points))
        prepared.append((key, geometry, bounds))
    facilities, seen = [], set()
    for element in osm['elements']:
        identity = f"{element['type']}/{element['id']}"
        if identity in seen:
            raise ValueError('duplicate OSM element')
        seen.add(identity)
        tags = element.get('tags', {})
        if tags.get('power') != 'substation':
            raise ValueError('OSM input includes non-substation')
        point = element.get('center', element)
        lat, lon = point.get('lat'), point.get('lon')
        if not all(isinstance(v, (float, int)) and math.isfinite(v) for v in (lat, lon)):
            raise ValueError('invalid OSM coordinates')
        if not (-107 < lon < -93 and 25 < lat < 37):
            raise ValueError('OSM reference point outside Texas bounding range')
        hits = [key for key, geometry, (w, s, e, n) in prepared
                if w <= lon <= e and s <= lat <= n and inside_geometry(lon, lat, geometry)]
        facilities.append({'osm_id': identity, 'url': f'https://www.openstreetmap.org/{identity}',
                           'lat': lat, 'lon': lon,
                           'reference_kind': 'node' if element['type'] == 'node' else 'Overpass bounding-box center',
                           'names': {k: tags[k] for k in ('name', 'alt_name', 'old_name') if tags.get(k)},
                           'operator': tags.get('operator'), 'voltage': tags.get('voltage'),
                           'county': hits[0] if len(hits) == 1 else None,
                           'county_disposition': 'inside_one' if len(hits) == 1 else 'outside_or_boundary' if not hits
                           else 'ambiguous_county'})
    return {'crs': 'EPSG:4326', 'attribution': ATTRIBUTION, 'license_url': LICENSE_URL,
            'counties': county_names, 'facilities': sorted(facilities, key=lambda p: p['osm_id'])}


def facility_index(ledger):
    result = defaultdict(dict)
    seen = set()
    for point in ledger['facilities']:
        if point['osm_id'] in seen:
            raise ValueError('duplicate OSM ledger element')
        seen.add(point['osm_id'])
        if point['county'] is None:
            continue
        for value in point['names'].values():
            name = _facility(value)
            if name:
                result[(name, point['county'])][point['osm_id']] = point
    return result


def match_terminal(name, county, index):
    normalized = _facility(name)
    if not normalized:
        return {'status': 'unnamed', 'matches': []}
    matches = list(index.get((normalized, county_key(county)), {}).values())
    return {'status': 'unique' if len(matches) == 1 else 'ambiguous' if matches else 'no_match',
            'matches': sorted(matches, key=lambda p: p['osm_id'])}


def locate(row, ledger, index):
    terminals, points, areas = {}, [], set()
    for side in ('from', 'to'):
        raw_county = row[f'county_{side}_raw']
        result = match_terminal(row[f'terminal_{side}'], raw_county, index)
        terminals[side] = {'status': result['status'], 'osm_ids': [p['osm_id'] for p in result['matches']]}
        if result['status'] == 'unique':
            points.append({'side': side, **result['matches'][0]})
        for name in re.split(r'[,;/&]|\band\b', raw_county or '', flags=re.I):
            key = county_key(name)
            if key in ledger['counties']:
                areas.add(ledger['counties'][key]['geoid'])
    center = None
    if points:
        center = {'lat': sum(p['lat'] for p in points) / len(points),
                  'lon': sum(p['lon'] for p in points) / len(points),
                  'basis': 'two' if len(points) == 2 else 'one', 'evidence': NOTE}
    anchors = []
    if not points:
        for county in ledger['counties'].values():
            if county['geoid'] in areas and county.get('representative_point'):
                lon, lat = county['representative_point']
                anchors.append({'county_geoid': county['geoid'], 'county_name': county['name'],
                                'lat': lat, 'lon': lon, 'method': 'Census Gazetteer representative point',
                                'source_id': 'census-2026-gaz-counties-national'})
    return {'tier': 'candidate' if points else 'area_only' if areas else 'unlocated',
            'center': center, 'endpoints': points, 'terminals': terminals, 'counties': sorted(areas),
            'display_anchors': sorted(anchors, key=lambda a: a['county_geoid']),
            'note': (NOTE if points else 'County reference — exact site unknown.' if areas
                     else 'No matched terminal or named Texas county.'),
            'location_meaning': 'terminal reference; does not establish a new substation site or line route'}


def canonical_rows(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['native_id']].append(row)
    output = []
    for native, observations in sorted(groups.items()):
        facts = [{k: v for k, v in row.items() if k != 'row'} for row in observations]
        if any(f != facts[0] for f in facts[1:]):
            raise ValueError(f'conflicting duplicate native ID: {native}')
        output.append((observations[0], [{'sheet': r['sheet'], 'row': r['row']} for r in observations]))
    return output


def build(rows, ledger, source_hash):
    index = facility_index(ledger)
    located = [dict(native_id=r['native_id'], sheet=r['sheet'], row=r['row'], **locate(r, ledger, index)) for r in rows]
    by_locator = {(r['sheet'], r['row']): r for r in located}
    if len(by_locator) != len(rows):
        raise ValueError('duplicate source locator')
    projects = []
    for row, citations in canonical_rows(rows):
        if row['source_sha256'] != source_hash:
            raise ValueError('TPIT source hash changed')
        loc = by_locator[(row['sheet'], row['row'])]
        conflict = row['sheet_cohort'] == 'completed' and row['status_raw'] != 'In-Service'
        status = {'Planned': 'planned', 'Conceptual': 'proposed', 'Under Construction': 'under_construction',
                  'In-Service': 'in_service'}.get(row['status_raw'], 'unknown')
        p = {'_id': f"ercot-tpit:{row['native_id']}", 'native_id': row['native_id'], 'source_id': SOURCE_ID,
             'name': row['title'] or f"ERCOT project {row['native_id']} (title unknown)", 'description': None,
             'owner': row['owner_raw'], 'other_owners': [], 'planning_region': 'ercot', 'states': ['48'],
             'counties': loc['counties'], 'geography_basis': 'TPIT named county; Census TIGERweb county containment',
             'status': row['status_raw'], 'status_group': 'unknown' if conflict else status,
             'in_service': row['projected_in_service'], 'center': loc['center'],
             'location_review': 'unreviewed' if loc['center'] else 'unlocated',
             'location_evidence': {k: v for k, v in loc.items() if k not in {'native_id', 'sheet', 'row', 'center'}},
             'evidence': {'page': None, 'sheet': row['sheet'], 'row': row['row'], 'source_sha256': source_hash,
                          'raw': {k: row[k] for k in ('title', 'terminal_from', 'terminal_to', 'county_from_raw',
                                   'county_to_raw', 'status_raw', 'sheet_cohort', 'owner_raw', 'voltage_kv_raw',
                                   'actual_in_service', 'projected_in_service')},
                          'source_rows': citations, 'lifecycle_conflict': conflict}}
        if loc['center']:
            p['location_candidate'] = {'tier': 'candidate', 'label': 'Tentative', 'note': NOTE,
                                       'independent_review': False, 'attribution': ATTRIBUTION,
                                       'license_url': LICENSE_URL, 'endpoints': loc['endpoints']}
        elif loc['display_anchors']:
            p['approximate_location'] = {
                'precision': 'county', 'label': 'County reference — exact site unknown.',
                'anchors': loc['display_anchors'], 'reference_source': ledger['county_reference_provenance'],
                'eligible_for_matching': False,
            }
        validate(p, 'national-project')
        projects.append(p)
    def counts(items):
        tiers = Counter(x.get('tier', x.get('location_evidence', {}).get('tier')) for x in items)
        centers = [x['center'] for x in items if x['center']]
        return {'candidate': tiers['candidate'], 'full': sum(c['basis'] == 'two' for c in centers),
                'partial': sum(c['basis'] == 'one' for c in centers), 'area_only': tiers['area_only'],
                'unlocated': tiers['unlocated']}
    terminal_counts = Counter(t['status'] for x in located for t in x['terminals'].values())
    return projects, located, {'observations': len(rows), 'canonical_projects': len(projects),
                              'observation_tiers': counts(located), 'project_tiers': counts(projects),
                              'terminals': dict(terminal_counts),
                              'ambiguous_observations': sum(any(t['status'] == 'ambiguous' for t in x['terminals'].values())
                                                            for x in located),
                              'duplicate_ids': sorted(k for k, n in Counter(r['native_id'] for r in rows).items() if n > 1)}


def main():
    root = Path(__file__).resolve().parents[2]
    raw = Path(sys.argv[1])
    receipts = json.loads((raw / 'acquisition.json').read_text())
    for key in ('osm', 'counties'):
        if hashlib.sha256((raw / f'{key}.json').read_bytes()).hexdigest() != receipts[key]['sha256']:
            raise ValueError('raw geography hash mismatch')
    osm, counties = [json.loads((raw / f'{key}.json').read_text()) for key in ('osm', 'counties')]
    if len(counties['features']) != 254:
        raise ValueError('Texas county enumeration incomplete')
    ledger = derive_facilities(osm, counties)
    ledger['provenance'] = receipts
    ledger['osm_base_timestamp'] = osm['osm3s']['timestamp_osm_base']
    geography = json.loads((root / 'data/national/geography.json').read_text())
    references = {c['county_geoid']: c for c in geography['counties'] if c['state_fips'] == '48'}
    for county in ledger['counties'].values():
        county['representative_point'] = references[county['geoid']]['representative_point']
    manifest = json.loads((root / 'data/national/source-manifest.json').read_text())
    reference = next(s for s in manifest if s['id'] == 'census-2026-gaz-counties-national')
    ledger['county_reference_provenance'] = {
        k: reference[k] for k in ('id', 'url', 'sha256', 'retrieved_at')
    }
    rows = sum([json.loads((root / 'data/texas' / f'{s}-observations.json').read_text())
                for s in ('planned', 'future', 'completed')], [])
    source = json.loads((root / 'data/texas/publication-source.json').read_text())
    projects, observations, summary = build(rows, ledger, source['sha256'])
    if len(rows) != 2049 or set(summary['duplicate_ids']) != DUPLICATES:
        raise ValueError('TPIT enumeration changed')
    source['project_count'] = len(projects)
    source['notes'] = ['Statewide exact-name plus county OSM candidate references; no independently confirmed locations.',
                       NOTE, 'County-only projects have labeled display anchors and null exact centers. '
                       'Sheet and lifecycle conflicts remain explicit.']
    out = root / 'data/texas/statewide'
    out.mkdir(exist_ok=True)
    for name, value in [('facilities', ledger), ('projects', projects), ('observations', observations),
                        ('summary', summary), ('source', source)]:
        (out / f'{name}.json').write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
