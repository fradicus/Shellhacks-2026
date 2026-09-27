"""Tentative Florida locations from FRCC Form 13 (2012-2026) and FPL Schedule 10 (2024-2026).

Nothing here is independently reviewed. Locations are exact-name references to OSM substations/plants or
EIA-860M plant coordinates, labeled "Tentative" on the existing maps. County centers are never used.

    uv run python -m southeast.florida_tentative acquire /private/tmp/f39-fl-raw   # network, outside the repo
    uv run python -m southeast.florida_tentative build /private/tmp/f39-fl-raw     # writes data/southeast/tentative
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common import REPO_ROOT, load_json

OUT = Path('data/southeast/tentative')
ACTIVE = OUT / 'releases/active.json'
RELEASE_ID = 'southeast-florida-tentative-1'
FILES = ('observations', 'ledger', 'projects', 'sources', 'dispositions', 'summary')
PSC = 'https://www.floridapsc.com/pscfiles/website-files/PDF/Utilities/Electricgas/TenYearSitePlans'
FRCC = {2012: f'{PSC}/2012/FRCC_2012_Load_Resource_Plan.pdf', 2013: f'{PSC}/2013/FRCC_2013_Load_Resource_Plan.pdf',
        2014: f'{PSC}/2014/FRCC_2014_Load_Resource_Plan.pdf',
        **{y: f'{PSC}/{y}/FRCC.pdf' for y in (2015, 2016, 2017)},
        **{y: f'{PSC}/{y}/FRCC_RLRP.pdf' for y in range(2018, 2027)}}
# FPL Ten Year Power Plant Site Plans. 2024/2025 are the PSC docket copies; 2026 is FPL's published copy.
FPL = {2024: 'https://www.floridapsc.com/pscfiles/library/filings/2024/01428-2024/01428-2024.pdf',
       2025: 'https://www.floridapsc.com/library/FILINGS/2025/02502-2025/02502-2025.pdf',
       2026: 'https://www.fpl.com/content/dam/fplgp/us/en/about/pdf/ten-year-site-plan.pdf'}
EIA_URL = 'https://www.eia.gov/electricity/data/eia860m/xls/august_generator2026.xlsx'
OSM_QUERY = ('[out:json][timeout:90][maxsize:67108864];\narea["ISO3166-2"="US-FL"]->.fl;\n'
             'nwr["power"~"^(substation|plant)$"]["name"](area.fl);\nout center tags;\n')
OSM_ATTRIBUTION = '© OpenStreetMap contributors; ODbL 1.0'
OSM_LICENSE = 'https://opendatacommons.org/licenses/odbl/1-0/'
LABEL = 'Tentative'
# Expansions come from each FRCC plan's own abbreviations page.
OWNERS = {'DEF': 'Duke Energy Florida', 'PEF': 'Progress Energy Florida', 'TEC': 'Tampa Electric Company',
          'FPL': 'Florida Power & Light', 'GPC': 'Gulf Power Company', 'APC': 'Alabama Power Company',
          'PEC': 'PowerSouth Energy Cooperative', 'JEA': 'JEA', 'LAK': 'Lakeland, City of',
          'TAL': 'Tallahassee, City of', 'SEC': 'Seminole Electric Cooperative, Inc.',
          'OUC': 'Orlando Utilities Commission', 'KUA': 'Kissimmee Utility Authority',
          'GRU': 'Gainesville Regional Utilities', 'FMPA': 'Florida Municipal Power Agency'}
# OSM operator substrings compatible with a reported owner code; a conflicting operator rejects the match.
OPERATORS = {'DEF': ('DUKE', 'PROGRESS'), 'PEF': ('DUKE', 'PROGRESS'), 'TEC': ('TAMPA', 'TECO'),
             'FPL': ('FLORIDA POWER', 'FPL', 'NEXTERA'), 'GPC': ('GULF', 'FLORIDA POWER', 'FPL'),
             'APC': ('ALABAMA',), 'PEC': ('POWERSOUTH', 'POWER SOUTH'), 'JEA': ('JEA',), 'LAK': ('LAKELAND',),
             'TAL': ('TALLAHASSEE',), 'SEC': ('SEMINOLE',), 'OUC': ('ORLANDO',), 'KUA': ('KISSIMMEE',),
             'GRU': ('GAINESVILLE',), 'FMPA': ('FLORIDA MUNICIPAL',)}
STRIP = (r'\b(SUBSTATION|SUBSTA|SUB|SWITCHING STATION|SWITCHING STA|SWITCH STATION|SWITCHYARD|SWITCHING|TRAN|'
         r'TRANSMISSION|POWER STATION|POWER PLANT|GENERATING STATION|PLANT|ENERGY CENTER|ENERGY CTR|STATION|TAP)\b')
PLANT_WORDS = r'\b(SOLAR|ENERGY|CENTER|CENTRE|BATTERY|STORAGE|SYSTEM|BESS|PV|PLANT|FACILITY|ACES|PILOT)\b'
FRCC_FIELDS = ('vintage', 'page', 'text_line', 'raw', 'owner', 'in_service')
MIN_ENDPOINT_KM = 40  # endpoints farther apart than max(3x reported length, 40 km) are a name collision


def norm(name: str) -> str:
    s = re.sub(r'\(.*?\)', '', name.upper().replace('&', ' AND '))
    s = re.sub(r'\bST\.?\s', 'SAINT ', s)
    s = re.sub(r'\bFT\.?\s', 'FORT ', s)
    s = re.sub(STRIP, '', s)
    s = re.sub(r'\b\d+\s*KV\b', '', s)
    return ' '.join(re.sub(r'[^A-Z0-9 ]', ' ', s).split())


def plant_key(name: str) -> str:
    return ' '.join(re.sub(PLANT_WORDS, '', norm(name)).split())


def owner_codes(raw: str) -> list[str]:
    return [c for c in re.split(r'[-/ ]+', raw.upper().replace('PEF', 'DEF')) if c]


def km(a: dict, b: dict) -> float:
    p = math.pi / 180
    h = (math.sin((b['lat'] - a['lat']) * p / 2) ** 2
         + math.cos(a['lat'] * p) * math.cos(b['lat'] * p) * math.sin((b['lon'] - a['lon']) * p / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(h))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------- acquisition (network; raw files stay outside the checkout) ----------

def acquire(target: Path) -> None:
    from osm.fetch import OVERPASS_URL, USER_AGENT
    target = target.resolve()
    if target.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError('raw downloads must stay outside the repo')
    target.mkdir(parents=True, exist_ok=True)
    jobs = [(f'frcc-{y}.pdf', url, None) for y, url in FRCC.items()]
    jobs += [(f'fpl-tysp-{y}.pdf', url, None) for y, url in FPL.items()]
    jobs += [('eia860m.xlsx', EIA_URL, None),
             ('osm.json', OVERPASS_URL, urlencode({'data': OSM_QUERY}).encode())]
    receipts = {}
    for name, url, body in jobs:
        with urlopen(Request(url, data=body, headers={'User-Agent': USER_AGENT}), timeout=180) as response:
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError(f'{name} exceeds size limit')
        if name.endswith('.pdf') and not data.startswith(b'%PDF'):
            raise ValueError(f'{name} is not a PDF')
        if name == 'osm.json' and 'remark' in json.loads(data):
            raise ValueError('Overpass response is incomplete')
        (target / name).write_bytes(data)
        receipts[name] = {'url': url, 'retrieved_at': datetime.now(UTC).isoformat(), 'sha256': sha(data),
                          'bytes': len(data), 'user_agent': USER_AGENT, **({'query': OSM_QUERY} if body else {})}
        print(name, receipts[name]['sha256'], len(data))
    (target / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')


# ---------- extraction (pdftotext -layout; observations are committed and replayed) ----------

def pdf_text(path: Path) -> str:
    return subprocess.run(['pdftotext', '-layout', str(path), '-'], check=True, capture_output=True, text=True).stdout


def frcc_rows(text: str, vintage: int) -> list[dict]:
    rows, on, page = [], False, 1
    for number, line in enumerate(text.split('\n'), 1):
        page += line.count('\f')
        upper = line.upper()
        if 'SPECIFICATIONS OF PROPOSED TRANSMISSION LINES' in upper and '...' not in line:
            on = True
            continue
        if on and (line.strip().startswith('* TLSA') or 'MERCHANT' in upper or 'ABBREVIATIONS' in upper):
            on = False
        if not on or not line.strip():
            continue
        parts = re.split(r'\s{2,}', re.sub(r'(\d{1,2})\s*/\s*(\d{4})', r'\1/\2', line).strip())
        dates = [i for i, p in enumerate(parts) if re.fullmatch(r'\d{1,2}/\d{4}', p)]
        if not dates or dates[0] < 3 or parts[0][0].isdigit():
            continue
        i = dates[0]
        rest = parts[i + 1:]
        rows.append({'kind': 'frcc', 'vintage': vintage, 'page': page,
                     'text_line': number, 'raw': line.strip(), 'owner': parts[0], 'from': parts[1], 'to': parts[2],
                     'length_mi': parts[3] if i == 4 else None, 'in_service': parts[i],
                     'kv': rest[0] if rest else None, 'mva': rest[1] if len(rest) > 1 else None,
                     'sited_under': rest[2] if len(rest) > 2 else None})
    return rows


def fpl_rows(text: str, vintage: int) -> list[dict]:
    rows = []
    for page_no, page in enumerate(text.split('\f'), 1):
        m = re.search(r'Page (\d+) of (\d+)\s*\n\s*Schedule 10\s*\n\s*Status Report and Specifications of Proposed '
                      r'Transmission Lines\s*\n\s*\n\s*(.+?)\s*\(([^)]*)\)', page)
        if not m:
            continue

        def field(n: int, page: str = page) -> str | None:
            f = re.search(rf'\({n}\)[^:\n]*:\s*(.+?)\n\s*\n', page, re.S)
            return ' '.join(f.group(1).split()) if f else None
        rows.append({'kind': 'fpl', 'vintage': vintage, 'schedule_page': int(m.group(1)), 'schedule_pages': int(m.group(2)),
                     'page': page_no, 'center': ' '.join(m.group(3).split()), 'county': m.group(4).strip(),
                     'origin': field(1), 'lines': field(2), 'length': field(4), 'voltage': field(5),
                     'timing': field(6), 'substations': field(8), 'participation': field(9)})
    return rows


# ---------- reference ledger (every candidate for every referenced name, so ambiguity replays) ----------

def osm_entries(osm: dict) -> list[dict]:
    out = []
    for e in osm['elements']:
        t = e['tags']
        c = e.get('center') or {'lat': e.get('lat'), 'lon': e.get('lon')}
        names = {k: t[k] for k in ('name', 'alt_name', 'official_name', 'short_name') if t.get(k)}
        out.append({'id': f"{e['type']}/{e['id']}", 'url': f"https://www.openstreetmap.org/{e['type']}/{e['id']}",
                    'power': t['power'], 'names': names, 'operator': t.get('operator'),
                    'lat': c['lat'], 'lon': c['lon']})
    return out


def eia_entries(path: Path) -> list[dict]:
    import openpyxl
    out, seen = [], set()
    workbook = openpyxl.load_workbook(path, read_only=True)
    for sheet in ('Operating', 'Planned', 'Retired', 'Canceled or Postponed'):
        rows = workbook[sheet].iter_rows(values_only=True)
        header = next(r for r in rows if r and 'Plant Name' in r)
        for row in rows:
            d = dict(zip(header, row, strict=False))
            if d.get('Plant State') != 'FL' or (d['Plant ID'], sheet) in seen:
                continue
            try:
                lat, lon = float(d['Latitude']), float(d['Longitude'])
            except (TypeError, ValueError):
                continue
            seen.add((d['Plant ID'], sheet))
            out.append({'plant_id': str(d['Plant ID']), 'plant_name': d['Plant Name'], 'entity': d['Entity Name'],
                        'county': d['County'], 'sheet': sheet, 'lat': lat, 'lon': lon})
    return out


def terminal_names(observations: list[dict]) -> tuple[set[str], set[str]]:
    subs, plants = set(), set()
    for o in observations:
        if o['kind'] == 'frcc':
            subs |= {norm(o['from']), norm(o['to'])}
        else:
            subs |= {norm(s) for s in fpl_substations(o)} | {norm(fpl_origin(o))}
            plants.add(plant_key(o['center']))
    return subs - {''}, plants - {''}


def build_ledger(observations: list[dict], osm: list[dict], eia: list[dict], receipts: dict) -> dict:
    subs, plants = terminal_names(observations)
    keep_osm = [e for e in osm if {norm(n) for n in e['names'].values()} & subs
                or (e['power'] == 'plant' and {plant_key(n) for n in e['names'].values()} & plants)]
    keep_eia = [e for e in eia if plant_key(e['plant_name']) in plants]
    return {'osm': sorted(keep_osm, key=lambda e: e['id']), 'eia': sorted(keep_eia, key=lambda e: (e['plant_id'], e['sheet'])),
            'osm_elements_total': len(osm), 'eia_florida_rows_total': len(eia),
            'provenance': {k: receipts[k] for k in ('osm.json', 'eia860m.xlsx')},
            'attribution': OSM_ATTRIBUTION, 'license_url': OSM_LICENSE}


# ---------- matching and project assembly (pure; replayed by apply_release) ----------

def osm_index(ledger: dict) -> dict[str, list[dict]]:
    index = defaultdict(dict)
    for e in ledger['osm']:
        for n in e['names'].values():
            if norm(n):
                index[norm(n)][e['id']] = e
    return {k: list(v.values()) for k, v in index.items()}


def match(name: str, owner: str, index: dict) -> tuple[dict | None, str]:
    key = norm(name)
    if not key or 'UNSITED' in key:
        return None, 'unnamed'
    found = index.get(key, [])
    if not found:
        return None, 'no_match'
    hints = [h for c in owner_codes(owner) for h in OPERATORS.get(c, ())]
    compatible = [e for e in found if not (e['operator'] and hints and not any(h in e['operator'].upper() for h in hints))]
    if not compatible:
        return None, 'operator_conflict'
    if len(compatible) == 1:
        return compatible[0], 'unique'
    by_operator = [e for e in compatible if e['operator'] and any(h in e['operator'].upper() for h in hints)]
    if len(by_operator) == 1:
        return by_operator[0], 'operator'
    return None, f'ambiguous:{len(compatible)}'


def endpoint(side: str, e: dict) -> dict:
    return {'side': side, 'osm_id': e['id'], 'url': e['url'], 'names': e['names'], 'operator': e['operator'],
            'lat': e['lat'], 'lon': e['lon'], 'reference_kind': 'Overpass element center'}


def candidate(note: str, endpoints: list[dict], osm: bool) -> dict:
    extra = {'attribution': OSM_ATTRIBUTION, 'license_url': OSM_LICENSE} if osm else {
        'attribution': 'U.S. Energy Information Administration, Form EIA-860M (public domain)', 'license_url': EIA_URL}
    return {'tier': 'candidate', 'label': LABEL, 'note': note, 'independent_review': False, **extra, 'endpoints': endpoints}


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def month(raw: str) -> str | None:
    m = re.fullmatch(r'(\d{1,2})/(\d{4})', raw)
    return f'{int(m.group(2)):04d}-{int(m.group(1)):02d}' if m and 1 <= int(m.group(1)) <= 12 else None


def dep_terminals(dep_projects: list[dict]) -> dict[str, set[str]]:
    return {p['_id']: {norm(t) for t in re.split(r'\s+-\s+|-', p['evidence']['raw']['index']['name'])}
            for p in dep_projects}


def frcc_projects(observations: list[dict], index: dict, dep: dict, sources: dict) -> tuple[list, list]:
    groups = defaultdict(list)
    for o in observations:
        if o['kind'] == 'frcc':
            kv = re.match(r'\d+', o['kv'] or '')
            # Owner labels change between editions (Gulf Power became FPL); terminals + voltage identify the line.
            key = (tuple(sorted({norm(o['from']), norm(o['to'])})), kv.group(0) if kv else '')
            groups[key].append(o)
    projects, dispositions = [], []
    for (terms, kv), obs in sorted(groups.items()):
        obs.sort(key=lambda o: (o['vintage'], o['page'], o['text_line']))
        last = obs[-1]
        native = slug(f"{' '.join(terms)} {kv}kv")
        pid = f'southeast:fl-frcc:{native}'
        locators = [f"{o['vintage']}:p{o['page']}:l{o['text_line']}" for o in obs]
        duplicate = next((d for d, names in dep.items() if set(terms) <= names and len(terms) == 2), None)
        if duplicate:
            dispositions += [{'source_id': f"frcc-lrp-{o['vintage']}", 'locator': loc, 'disposition': 'duplicate',
                              'project_id': duplicate, 'reason': 'Same terminals as the reviewed Florida DEP certification.'}
                             for o, loc in zip(obs, locators, strict=True)]
            continue
        a, sa = match(last['from'], last['owner'], index)
        b, sb = match(last['to'], last['owner'], index)
        same = len(terms) == 1
        center, cand, note = None, None, None
        if a and b and not same:
            length = float(last['length_mi']) if re.fullmatch(r'\d+(\.\d+)?', last['length_mi'] or '') else 0
            if km(a, b) <= max(3 * length * 1.609, MIN_ENDPOINT_KM):
                note = ('Midpoint of two OSM terminal references matched by exact name and owner-compatible operator; '
                        'not reviewed.')
                center = {'lat': round((a['lat'] + b['lat']) / 2, 7), 'lon': round((a['lon'] + b['lon']) / 2, 7), 'basis': 'two'}
                cand = candidate(note, [endpoint('from', a), endpoint('to', b)], True)
            else:
                sa = sb = 'endpoint_distance_conflict'
        elif (a or b) and (same or not (a and b)):
            x, side = (a, 'from') if a else (b, 'to')
            note = ('OSM substation reference matched by exact name; site of the reported work; not reviewed.' if same else
                    'One OSM terminal reference matched by exact name (partial); line route and other terminal unknown; '
                    'not reviewed.')
            center = {'lat': x['lat'], 'lon': x['lon'], 'basis': 'one'}
            cand = candidate(note, [endpoint(side, x)], True)
        current = last['vintage'] == max(FRCC)
        codes = owner_codes(last['owner'])
        project = {
            '_id': pid, 'source_id': f"frcc-lrp-{last['vintage']}", 'native_id': native,
            'name': (f"{last['from'].title()} {kv} kV work" if same else
                     f"{last['from'].title()} – {last['to'].title()} {kv} kV line"),
            'description': None, 'owner': OWNERS.get(codes[0], codes[0]),
            'other_owners': [OWNERS.get(c, c) for c in codes[1:]], 'planning_region': 'frcc', 'states': ['12'],
            'counties': [], 'geography_basis': 'FRCC Florida plan; no county reported',
            'status': ('Proposed as of January 1, 2026 (FRCC Form 13)' if current else
                       f"Last listed as proposed in the {last['vintage']} FRCC plan; later status unknown"),
            'status_group': 'planned' if current else 'unknown',
            'in_service': ({'raw': last['in_service'], 'value': month(last['in_service']), 'precision': 'month'}
                           if current and month(last['in_service']) else {'raw': None, 'value': None, 'precision': 'unknown'}),
            'center': {**center, 'evidence': note} if center else None,
            'location_review': 'unreviewed' if center else 'unlocated',
            'evidence': {'page': last['page'], 'sheet': 'FRCC Form 13', 'row': last['text_line'],
                         'source_sha256': sources[f"frcc-lrp-{last['vintage']}"]['sha256'],
                         'raw': {'observations': [{k: o[k] for k in FRCC_FIELDS}
                                                  for o in obs],
                                 'terminal_matches': {'from': sa, 'to': sb},
                                 'projected_in_service_is_not_completion': True}},
        }
        if cand:
            project['location_candidate'] = cand
        projects.append(project)
        dispositions += [{'source_id': f"frcc-lrp-{o['vintage']}", 'locator': loc, 'disposition': 'accepted',
                          'project_id': pid, 'reason': 'Form 13 proposed line row.'}
                         for o, loc in zip(obs, locators, strict=True)]
    return projects, dispositions


def fpl_substations(o: dict) -> list[str]:
    return [s.strip() for s in re.split(r',|\band\b', re.sub(r'(?i)\bnew\b', '', o['substations'] or '')) if s.strip()]


def fpl_origin(o: dict) -> str:
    return re.split(r'(?i)\s+to\s+|\s+-\s+', o['origin'] or '')[0]


def fpl_projects(observations: list[dict], index: dict, ledger: dict, counties: dict, sources: dict) -> tuple[list, list]:
    plants = defaultdict(dict)
    for e in ledger['eia']:
        if re.search('Florida Power|NextEra|Gulf Power', e['entity'] or ''):
            plants[plant_key(e['plant_name'])].setdefault(e['plant_id'], e)
    groups = defaultdict(list)
    for o in observations:
        if o['kind'] == 'fpl':
            groups[norm(o['center'])].append(o)
    projects, dispositions = [], []
    for key, obs in sorted(groups.items()):
        obs.sort(key=lambda o: (o['vintage'], o['schedule_page']))
        o = obs[-1]
        pid = f"southeast:fl-fpl-tysp:{slug(key)}"
        county_name = norm(o['county'].replace('County', ''))
        county = counties.get(county_name)
        center, cand, how = None, None, 'unlocated'
        new = next((x for s in fpl_substations(o) for x in [match(s, 'FPL', index)[0]] if x), None)
        eia = list(plants.get(plant_key(o['center']), {}).values())
        eia_ok = len(eia) == 1 and norm(eia[0]['county'] or '') == county_name
        origin = match(fpl_origin(o), 'FPL', index)[0]
        if new:
            how, x = 'new_substation', new
            note = 'OSM reference for the new substation named in Schedule 10, matched by exact name; not reviewed.'
            center, cand = {'lat': x['lat'], 'lon': x['lon'], 'basis': 'one'}, candidate(note, [endpoint('site', x)], True)
        elif eia_ok:
            how, x = 'eia_plant', eia[0]
            note = ('EIA-860M plant coordinates for the named energy center, where Schedule 10 places the new substation; '
                    'county agrees; not reviewed.')
            center = {'lat': x['lat'], 'lon': x['lon'], 'basis': 'source_point'}
            cand = candidate(note, [{'side': 'site', 'url': EIA_URL, 'names': {'name': x['plant_name']},
                                     'eia_plant_id': x['plant_id'], 'eia_sheet': x['sheet'],
                                     'lat': x['lat'], 'lon': x['lon']}], False)
        elif origin:
            how, x = 'origin_substation', origin
            note = 'OSM reference for the Schedule 10 point of origin (partial); new facility site unknown; not reviewed.'
            center, cand = {'lat': x['lat'], 'lon': x['lon'], 'basis': 'one'}, candidate(note, [endpoint('from', x)], True)
        current = o['vintage'] == max(FPL)
        year = re.search(r'End date:\s*(\d{4})', o['timing'] or '')
        source = f"fpl-tysp-{o['vintage']}"
        project = {
            '_id': pid, 'source_id': source, 'native_id': slug(key),
            'name': f"{o['center']} transmission interconnection", 'description': o['origin'],
            'owner': 'Florida Power & Light Company', 'other_owners': [], 'planning_region': 'frcc', 'states': ['12'],
            'counties': [county] if county else [], 'geography_basis': 'Schedule 10 reported county',
            'status': (f"Proposed in FPL {o['vintage']} Ten Year Site Plan" if current else
                       f"Last listed in FPL {o['vintage']} Schedule 10; later status unknown"),
            'status_group': 'planned' if current else 'unknown',
            'in_service': ({'raw': year.group(0), 'value': year.group(1), 'precision': 'year'} if year and current
                           else {'raw': None, 'value': None, 'precision': 'unknown'}),
            'center': {**center, 'evidence': note} if center else None,
            'location_review': 'unreviewed' if center else 'unlocated',
            'evidence': {'page': o['page'], 'sheet': 'Schedule 10', 'row': o['schedule_page'],
                         'source_sha256': sources[source]['sha256'],
                         'raw': {'observations': [{k: x[k] for k in ('vintage', 'page', 'schedule_page', 'timing')}
                                                  for x in obs]}
                         | {k: o[k] for k in ('center', 'county', 'origin', 'length', 'voltage', 'substations')}
                         | {'location_method': how, 'eia_candidates': [e['plant_id'] for e in eia],
                            'projected_end_is_not_completion': True}},
        }
        if cand:
            project['location_candidate'] = cand
        projects.append(project)
        dispositions += [{'source_id': f"fpl-tysp-{x['vintage']}", 'locator': f"schedule-10:{x['schedule_page']}",
                          'disposition': 'accepted', 'project_id': pid, 'reason': 'Schedule 10 proposed line.'} for x in obs]
    return projects, dispositions


def county_lookup(root: Path) -> dict[str, str]:
    geography = load_json(root / 'data/national/geography.json')
    return {norm(c['name']): c['county_geoid'] for c in geography['counties'] if c['state_fips'] == '12'}


def assemble(observations: list[dict], ledger: dict, sources: list[dict], root: Path) -> tuple[list, list, dict]:
    by_id = {s['_id']: s for s in sources}
    index = osm_index(ledger)
    dep = dep_terminals(load_json(root / 'data/southeast/releases/active.json')['projects'])
    frcc, frcc_rows_ = frcc_projects(observations, index, dep, by_id)
    fpl, fpl_rows_ = fpl_projects(observations, index, ledger, county_lookup(root), by_id)
    projects = sorted(frcc + fpl, key=lambda p: p['_id'])
    if len({p['_id'] for p in projects}) != len(projects):
        raise ValueError('duplicate Florida tentative project id')
    located = [p for p in projects if p['center']]
    summary = {'projects': len(projects), 'located_tentative': len(located),
               'distinct_centers': len({(p['center']['lat'], p['center']['lon']) for p in located}),
               'unlocated': len(projects) - len(located), 'county_centers_used': 0,
               'by_source': dict(sorted(Counter(p['source_id'].split('-')[0] for p in located).items())),
               'basis': dict(sorted(Counter(p['center']['basis'] for p in located).items())),
               'dep_duplicates': sorted({d['project_id'] for d in frcc_rows_ if d['disposition'] == 'duplicate'}),
               'independently_confirmed': 0}
    return projects, frcc_rows_ + fpl_rows_, summary


def source_records(receipts: dict) -> list[dict]:
    notes = ['Tentative exact-name locations only; no independent review. County centers are never used.']
    frcc = [{'_id': f'frcc-lrp-{y}', 'title': f'FRCC {y} Regional Load & Resource Plan, Form 13 proposed transmission lines',
             'publisher': 'Florida Reliability Coordinating Council', 'authority': 'regional_planning_organization',
             'role': 'project_plan', 'landing_url': 'https://www.psc.state.fl.us/ten-year-site-plans', 'download_url': url,
             'publication_date': None, 'vintage': f'{y}-01-01', 'retrieved_at': receipts[f'frcc-{y}.pdf']['retrieved_at'],
             'sha256': receipts[f'frcc-{y}.pdf']['sha256'], 'public_status': 'verified_public',
             'access_policy': 'public_document', 'import_status': 'imported', 'planning_region': 'frcc',
             'states': ['12'], 'notes': notes} for y, url in FRCC.items()]
    fpl = [{'_id': f'fpl-tysp-{y}', 'title': f'FPL Ten Year Power Plant Site Plan {y}-{y + 9}, Schedule 10',
            'publisher': 'Florida Power & Light Company', 'authority': 'utility', 'role': 'project_plan',
            'landing_url': 'https://www.fpl.com/about/10-year-site-plan.html', 'download_url': url,
            'publication_date': None, 'vintage': str(y), 'retrieved_at': receipts[f'fpl-tysp-{y}.pdf']['retrieved_at'],
            'sha256': receipts[f'fpl-tysp-{y}.pdf']['sha256'], 'public_status': 'verified_public',
            'access_policy': 'public_document', 'import_status': 'imported', 'planning_region': 'frcc',
            'states': ['12'], 'notes': notes} for y, url in FPL.items()]
    return [*frcc, *fpl]


def file_hash(root: Path, name: str) -> str:
    return sha((root / OUT / f'{name}.json').read_bytes())


def write(root: Path, name: str, value) -> None:
    path = root / OUT / f'{name}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + '\n')


def build(raw: Path, root: Path = REPO_ROOT) -> dict:
    receipts = json.loads((raw / 'receipts.json').read_text())
    for name, receipt in receipts.items():
        if sha((raw / name).read_bytes()) != receipt['sha256']:
            raise ValueError(f'{name} changed after acquisition')
    observations = [row for y in FRCC for row in frcc_rows(pdf_text(raw / f'frcc-{y}.pdf'), y)]
    if not all(Counter(o['vintage'] for o in observations).get(y) for y in FRCC):
        raise ValueError('an FRCC vintage produced no Form 13 rows; parser drift')
    for y in FPL:
        fpl = fpl_rows(pdf_text(raw / f'fpl-tysp-{y}.pdf'), y)
        if not fpl or [o['schedule_page'] for o in fpl] != list(range(1, fpl[0]['schedule_pages'] + 1)):
            raise ValueError(f'FPL {y} Schedule 10 pages missing or out of order; parser drift')
        observations += fpl
    ledger = build_ledger(observations, osm_entries(json.loads((raw / 'osm.json').read_text())),
                          eia_entries(raw / 'eia860m.xlsx'), receipts)
    sources = source_records(receipts)
    projects, dispositions, summary = assemble(observations, ledger, sources, root)
    counts = Counter(p['source_id'] for p in projects)
    sources = [{**source, 'project_count': counts[source['_id']]} for source in sources]
    for name, value in zip(FILES, (observations, ledger, projects, sources, dispositions, summary), strict=True):
        write(root, name, value)
    release = {'release_id': RELEASE_ID, 'policy': 'tentative-candidate', 'label': LABEL,
               'files': {name: file_hash(root, name) for name in FILES}, 'expected_counts': summary,
               'project_ids': [p['_id'] for p in projects]}
    (root / ACTIVE).parent.mkdir(parents=True, exist_ok=True)
    (root / ACTIVE).write_text(json.dumps(release, indent=1) + '\n')
    return summary


def apply_release(snapshot: dict, root: Path) -> dict:
    """Replay the committed tentative release and append it; any drift stops national assembly."""
    if not (root / ACTIVE).exists():
        return snapshot
    release = load_json(root / ACTIVE)
    if release['release_id'] != RELEASE_ID or set(release['files']) != set(FILES):
        raise ValueError('Florida tentative release manifest changed')
    for name in FILES:
        if file_hash(root, name) != release['files'][name]:
            raise ValueError(f'Florida tentative file hash changed: {name}')
    data = {name: load_json(root / OUT / f'{name}.json') for name in FILES}
    projects, dispositions, summary = assemble(data['observations'], data['ledger'], data['sources'], root)
    if (projects != data['projects'] or dispositions != data['dispositions'] or summary != data['summary']
            or summary != release['expected_counts'] or [p['_id'] for p in projects] != release['project_ids']
            or any(s['project_count'] != sum(p['source_id'] == s['_id'] for p in projects) for s in data['sources'])):
        raise ValueError('Florida tentative replay failed')
    if any(p['center'] and p['location_review'] != 'unreviewed' for p in projects):
        raise ValueError('tentative release cannot confirm locations')
    existing = {p['_id'] for p in snapshot['projects']} | {s['_id'] for s in snapshot['sources']}
    if existing & ({p['_id'] for p in projects} | {s['_id'] for s in data['sources']}):
        raise ValueError('Florida tentative release overlaps existing identities')
    result = deepcopy(snapshot)
    result['sources'].extend(data['sources'])
    result['projects'].extend(projects)
    result['coverage']['florida_tentative'] = {
        'release_id': RELEASE_ID, **summary, 'attribution': OSM_ATTRIBUTION, 'license_url': OSM_LICENSE,
        'notes': 'FRCC Form 13 (2012-2026) and FPL Schedule 10 (2024-2026); tentative exact-name locations, no county dots.'}
    return result


if __name__ == '__main__':
    command, raw = sys.argv[1], Path(sys.argv[2])
    if command == 'acquire':
        acquire(raw)
    elif command == 'build':
        print(json.dumps(build(raw), indent=1))
    else:
        raise SystemExit('usage: florida_tentative acquire|build RAW_DIR')
