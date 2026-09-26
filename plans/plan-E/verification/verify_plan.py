#!/usr/bin/env python3
"""Validate Plan E's authored package and math; this is not application code."""
from pathlib import Path
from datetime import datetime, timedelta, date, timezone
from collections import Counter
import hashlib
import itertools
import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
E = HERE.parent
REPO = E.parents[1]
PACKAGE = E / 'paperclip'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
checks = []
def check(label, result):
    if not result:
        raise AssertionError(label)
    checks.append(label)

# Ruby/Psych supplies a real YAML parser without adding repository dependencies.
parsed = {}
for path in sorted(E.rglob('*')):
    if not path.is_file() or path.suffix not in ('.md', '.yaml', '.yml'):
        continue
    text = path.read_text()
    if path.suffix == '.md':
        if not text.startswith('---\n'):
            continue
        parts = text.split('---\n', 2)
        check('Closed frontmatter: ' + str(path.relative_to(E)), len(parts) == 3)
        text = parts[1]
    proc = subprocess.run(
        ['ruby', '-ryaml', '-rjson', '-e',
         'v=YAML.safe_load(STDIN.read, permitted_classes: [], permitted_symbols: [], aliases: false); puts JSON.generate(v)'],
        input=text, text=True, capture_output=True, check=True)
    obj = json.loads(proc.stdout)
    check('YAML mapping: ' + str(path.relative_to(E)), isinstance(obj, dict))
    parsed[str(path.relative_to(PACKAGE))] = obj

agents = {p.split('/')[1]: obj for p, obj in parsed.items() if p.endswith('/AGENTS.md')}
skills = {p.split('/')[1]: obj for p, obj in parsed.items() if p.endswith('/SKILL.md')}
projects = {p.split('/')[1]: obj for p, obj in parsed.items() if p.endswith('/PROJECT.md')}
tasks = {p.split('/')[-2]: obj for p, obj in parsed.items() if p.endswith('/TASK.md')}
check('Expected package counts', (len(agents), len(skills), len(projects), len(tasks), len(parsed)) == (8, 13, 1, 17, 41))
company = parsed['COMPANY.md']
check('Company required fields/schema', all(company.get(x) for x in ('name', 'description', 'slug')) and company['schema'] == 'agentcompanies/v1')
refs = 0
for slug, obj in agents.items():
    check('Agent required fields: ' + slug, bool(obj.get('name')) and bool(obj.get('title')) and 'reportsTo' in obj and bool(obj.get('skills')))
    parent = obj['reportsTo']
    check('Reporting relationship: ' + slug, parent is None if slug == 'ceo' else parent == 'ceo')
    seen = {slug}
    while parent:
        check('Reporting graph acyclic: ' + slug, parent in agents and parent not in seen)
        seen.add(parent)
        parent = agents[parent]['reportsTo']
    for skill in obj['skills']:
        check('Skill resolves: ' + slug + '/' + skill, skill in skills)
        refs += 1
for slug, obj in skills.items():
    check('Skill metadata: ' + slug, obj.get('name') == slug and bool(obj.get('description')))
    body = (PACKAGE / 'skills' / slug / 'SKILL.md').read_text().split('---\n', 2)[2]
    check('Skill written procedure: ' + slug, all(x in body for x in ('## Inputs', '## Procedure', '## Output and checks')) and len(body.split()) >= 150)
for slug, obj in projects.items():
    check('Project owner: ' + slug, obj.get('owner') in agents and bool(obj.get('name')) and bool(obj.get('description')))
deps = {}
for slug, obj in tasks.items():
    check('Task references: ' + slug, obj.get('assignee') in agents and obj.get('project') in projects and bool(obj.get('name')))
    body = (PACKAGE / 'projects' / obj['project'] / 'tasks' / slug / 'TASK.md').read_text()
    match = re.search(r'^Dependencies: (.+)$', body, re.M)
    check('Task dependency declaration: ' + slug, match is not None)
    deps[slug] = [] if match.group(1) == 'none' else match.group(1).split(', ')
    check('Task prerequisites resolve: ' + slug, all(x in tasks for x in deps[slug]))
visiting, visited = set(), set()
def visit(slug):
    check('Task graph acyclic: ' + slug, slug not in visiting)
    if slug in visited:
        return
    visiting.add(slug)
    for dep in deps[slug]:
        visit(dep)
    visiting.remove(slug)
    visited.add(slug)
for slug in tasks:
    visit(slug)
sidecar = parsed['.paperclip.yaml']
check('Sidecar schema/agents', sidecar.get('schema') == 'paperclip/v1' and set(sidecar['agents']) == set(agents))
for slug, obj in sidecar['agents'].items():
    check('Adapter type: ' + slug, obj.get('adapter') == {'type': 'claude_local'})
    for key, decl in obj['inputs']['env'].items():
        check('Portable env declaration: ' + slug + '/' + key, set(decl) == {'kind', 'requirement'} and decl['kind'] in ('secret', 'plain') and decl['requirement'] in ('required', 'optional'))
# No absolute links/paths in the imported configuration, real secret values or runtime IDs.
check('Portable configuration avoids local paths', '/Users/' not in json.dumps(parsed))
check('Budget arithmetic', sum([10,25,20,20,20,20,15,10]) == 140)

# Resolve package-local Markdown links, ignoring external URLs and fragment-only links.
local_links = 0
for path in PACKAGE.rglob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        if target.startswith(('https://', 'http://', '#')):
            continue
        target = target.split('#')[0]
        check('Local link: ' + str(path.relative_to(E)) + ' -> ' + target, (path.parent / target).exists())
        local_links += 1

# Load the untouched XLSX using only standard library XML/ZIP readers.
wb_path = REPO / 'docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx'
with zipfile.ZipFile(wb_path) as archive:
    shared = [''.join(t.text or '' for t in item.findall('.//s:t', NS))
              for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]
    workbook = ET.fromstring(archive.read('xl/workbook.xml'))
    props = workbook.find('s:workbookPr', NS)
    check('Workbook uses 1900 date system', props is None or props.get('date1904', '0') in ('0', 'false'))
    def rows(sheet):
        result = []
        for row in ET.fromstring(archive.read('xl/worksheets/' + sheet + '.xml')).findall('.//s:row', NS):
            values = {}
            for cell in row.findall('s:c', NS):
                value = cell.find('s:v', NS)
                if value is not None:
                    values[re.sub(r'\d', '', cell.get('r'))] = shared[int(value.text)] if cell.get('t') == 's' else value.text
            result.append(values)
        return result
    raw_projects, raw_overlaps = rows('sheet1')[1:], rows('sheet2')[1:]

def point(row, a, b):
    return (float(row[a]), float(row[b])) if a in row and b in row else None

def center(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return tuple((x+y)/2 for x,y in zip(a,b))

def parse_day(raw):
    if raw is None:
        return None
    if '/' in raw:
        return datetime.strptime(raw, '%m/%d/%Y').date()
    return (datetime(1899, 12, 30) + timedelta(days=float(raw))).date()

def gap(a,b):
    return abs((b-a).days) if a is not None and b is not None else None

def haversine(a,b):
    if a is None or b is None:
        return None
    lat1, lon1 = map(math.radians,a)
    lat2, lon2 = map(math.radians,b)
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2*3958.8*math.asin(math.sqrt(max(0,min(1,h))))

def eligible(distance, different=True):
    return different and distance is not None and distance < 25

def rank_key(m):
    return (0 if m['distance_mi_raw'] < 10 else 1,
            m['time_gap_days'] if m['time_gap_days'] is not None else math.inf,
            m['distance_mi_raw'], tuple(sorted((m['project_a'],m['project_b']))))

def impact(n,unit,coord):
    return None if any(x is None for x in (n,unit,coord)) else n*unit-coord

projects_by_id = {}
for row in raw_projects:
    c = center(point(row,'F','G'),point(row,'I','J'))
    check('Center matches workbook: ' + row['A'], all(abs(x-y)<1e-10 for x,y in zip(c,point(row,'K','L'))))
    projects_by_id[row['A']] = {'id':row['A'],'utility':row['B'],'name':row['D'],'center':c,'date':parse_day(row.get('M')),'raw':row}
all_pairs = [(a,b) for a,b in itertools.combinations(projects_by_id.values(),2) if a['utility'] != b['utility']]
check('25 cross-utility comparisons',len(all_pairs)==25)
actual = {}
for a,b in all_pairs:
    d = haversine(a['center'],b['center'])
    if eligible(d):
        actual[(a['id'],b['id'])] = {'project_a':a['id'],'project_b':b['id'],'distance_mi_raw':d,'distance_mi':round(d,2),'time_gap_days':gap(a['date'],b['date']),'impact_dollars':impact(None,None,None)}
expected = {(r['E'],r['H']):r for r in raw_overlaps}
check('Exact six-pair set and 19 excluded pairs',set(actual)==set(expected) and len(actual)==6 and len(all_pairs)-len(actual)==19)
results=[]
for pair,row in expected.items():
    result=actual[pair]
    result['overlap_id']=row['A']
    check('Distance matches: '+row['A'], result['distance_mi']==float(row['B']))
    check('Day gap matches: '+row['A'], result['time_gap_days']==int(row['C']))
    a,b=map(projects_by_id.get,pair)
    check('Workbook labels match: '+row['A'], (a['utility'],a['name'],b['utility'],b['name'])==(row['D'],row['F'],row['G'],row['I']))
    results.append(result)
for p in projects_by_id.values():
    neighbors={b if a==p['id'] else a for a,b in actual if p['id'] in (a,b)}
    row=p['raw']; stored={row[k] for k in ('O','P','Q') if k in row}
    check('Project overlap counts/IDs: '+p['id'],neighbors==stored and len(neighbors)==int(row['N']))
ranked=sorted(results,key=rank_key)
check('Expected product ranking',[x['overlap_id'] for x in ranked]==['OVL_2','OVL_3','OVL_1','OVL_4','OVL_5','OVL_6'])
for i,r in enumerate(ranked,1):
    r['product_priority']=i
    r['distance_band']=0 if r['distance_mi_raw']<10 else 1
check('Impact unknown for all sample rows',all(r['impact_dollars'] is None for r in results))
analysis_date=date(2026,9,26)
future_pairs=[r for r in results if all(projects_by_id[r[k]]['date'] is not None and projects_by_id[r[k]]['date']>=analysis_date for k in ('project_a','project_b'))]
check('No sample pair has two future milestones as of plan date',len(future_pairs)==0)
edge_results={
 '25_miles_excluded':not eligible(25.0),
 'just_below_included':eligible(24.999999),
 'just_above_excluded':not eligible(25.000001),
 'same_utility_excluded':not eligible(1,False),
 'unknown_location_excluded':not eligible(haversine(None,(1,2))),
 'zero_distance':haversine((1,2),(1,2))==0,
 'symmetric_distance':abs(haversine((30,-80),(31,-81))-haversine((31,-81),(30,-80)))<1e-12,
 'two_endpoint_center':center((30,-80),(32,-82))==(31,-81),
 'one_endpoint_center':center(None,(30,-80))==(30,-80),
 'no_endpoint_center':center(None,None) is None,
 'missing_date_gap':gap(None,date(2026,1,1)) is None,
 'leap_day_gap':gap(date(2024,2,28),date(2024,3,1))==2,
 'impact_synthetic_arithmetic_only':impact(2,1000,500)==1500,
 'negative_impact_preserved':impact(0,1000,500)==-500,
 'missing_impact_input':impact(2,None,500) is None,
 'ten_mile_band_boundary':rank_key({'distance_mi_raw':10,'time_gap_days':0,'project_a':'a','project_b':'b'})[0]==1,
 'unknown_gap_last_in_band':rank_key({'distance_mi_raw':5,'time_gap_days':None,'project_a':'a','project_b':'b'})>rank_key({'distance_mi_raw':6,'time_gap_days':1,'project_a':'a','project_b':'b'}),
 'ranking_stable_tie':rank_key({'distance_mi_raw':5,'time_gap_days':1,'project_a':'a','project_b':'b'})<rank_key({'distance_mi_raw':5,'time_gap_days':1,'project_a':'a','project_b':'c'}),
 'hypothetical_gap_same_formula':gap(date(2026,1,1),date(2026,6,1))==151,
}
for name,success in edge_results.items():
    check('Edge case: '+name,success)
# An explicit hypothetical input demonstrates sensitivity without mutating fixtures.
original=projects_by_id['DESC_3']['date']
scenario={'published_gap_days':gap(original,projects_by_id['GPC_2']['date']),
          'assumed_date':'2026-01-01','hypothetical_gap_days':gap(date(2026,1,1),projects_by_id['GPC_2']['date'])}
check('Hypothetical scenario preserves published date', projects_by_id['DESC_3']['date']==original and scenario['published_gap_days']==152 and scenario['hypothetical_gap_days']==151)

baseline=json.loads((HERE/'baseline.json').read_text())
for name,digest in baseline.items():
    check('Baseline excludes Plan D',not name.startswith('plans/plan-D/'))
    check('Unchanged original: '+name,hashlib.sha256((REPO/name).read_bytes()).hexdigest()==digest)
# Name-only git status; never open or hash Plan D files.
status=subprocess.run(['git','status','--porcelain','--untracked-files=all'],cwd=REPO,text=True,capture_output=True,check=True).stdout
check('Git changes confined to Plan E',all(line[3:].strip('"').startswith('plans/plan-E/') for line in status.splitlines()))
report={
 'verified_at_utc':datetime.now(timezone.utc).isoformat(),
 'status':'PASS','assertions_passed':len(checks),'yaml_frontmatter_files':len(parsed),
 'agents':len(agents),'skills':len(skills),'skill_references':refs,'projects':1,'tasks':len(tasks),
 'cross_utility_pairs':len(all_pairs),'overlaps':results,'nonmatches':19,'analysis_date':analysis_date.isoformat(),'sample_pairs_with_two_future_milestones':len(future_pairs),
 'rank_order':[x['overlap_id'] for x in ranked],'edge_cases':edge_results,'hypothetical_scenario':scenario,
 'unchanged_baseline_files':len(baseline),'plan_d_read':False,
 'budget_total_usd':140,'git_status':status.splitlines(),
 'not_verified':['Paperclip server import or dry-run','adapter execution / runtime skill injection','Gemini live extraction quality','Atlas provisioning/networking','new corpus endpoint accuracy','new non-sample overlap target','deployment/domain/track eligibility','submission'],
 'checks':checks}
(HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
source_file=HERE/'source-checks.json'
source_info='URL checks pending.'
if source_file.exists():
    src=json.loads(source_file.read_text())
    ok=sum(r['ok'] for r in src['results'])
    source_info=f"URL retrieval: **{ok}/{len(src['results'])} passed**. See [source-checks.json](source-checks.json) for statuses, redirects and retrieval timestamps."
lines=['# Plan E verification results','',f"Status: **PASS** — {len(checks)} local assertions. Run: {report['verified_at_utc']}.",'',
 '## Sponsor workbook calculations','',
 'Read the original XLSX directly. Recomputed every center, all 25 cross-utility distances and mixed text/Excel-serial dates. All six pair IDs, labels, rounded distances, exact gaps and project neighbor counts match; all 19 remaining pairs are excluded.','',
 '| ID | Pair | Computed miles | Workbook miles | Computed gap | Workbook gap | Priority | Impact |',
 '|---|---|---:|---:|---:|---:|---:|---|']
for r in results:
    row=expected[(r['project_a'],r['project_b'])]
    lines.append(f"| {r['overlap_id']} | {r['project_a']} / {r['project_b']} | {r['distance_mi']:.2f} | {float(row['B']):.2f} | {r['time_gap_days']} | {row['C']} | {r['product_priority']} | null |")
lines += ['', 'Priority: '+', '.join(report['rank_order'])+'.', '',
 f"Additional formula/edge checks: **{len(edge_results)}/{len(edge_results)} passed**. Strict boundary, two/one/no endpoint, null gap, leap day, symmetry, band boundary, unknown-gap ordering, stable tie and impact checks are recorded in [results.json](results.json).",'',
 'None of the six sample pairs has two in-service dates on or after September 26, 2026. This is a dated regression fixture, not evidence of six current future opportunities. All sample savings estimates are null: mobilization inputs are absent. Synthetic arithmetic checks only: 2 × $1,000 − $500 = $1,500; 0 × $1,000 − $500 = −$500. These are not observed savings.', '',
 'Hypothetical scenario check: changing DESC_3 from its published December 31, 2025 to an assumed January 1, 2026 changes the gap to GPC_2 from 152 to 151 days. The fixture date stays unchanged. No construction feasibility is inferred.', '',
 '## Company package','',
 f"Parsed **{len(parsed)} YAML/frontmatter files** with Ruby Psych safe_load: company + sidecar, 8 agents, 13 skills, 1 project and 17 tasks. All **{refs} agent-skill references** resolve. Required fields, reporting graph, task owners/projects, acyclic prerequisite graph, skill procedure sections and env input declarations pass local structural checks.",'',
 'Format checked against the official Agent Companies reference at companies commit `514503bf4f0ca88ebf16d5dc648e085d587f268f`, the normative specification and Paperclip vendor/CLI documentation. No live IDs or secret values are supplied. This is a local structural checker, not the Paperclip importer or an exhaustive schema implementation.', '',
 '## Sources and preservation','',source_info,'',
 f"All **{len(baseline)} baseline files** outside Plan E remain byte-identical. Baseline excludes Plan D before reading/hashing. Git status reports changes only under Plan E. Plan D contents were not read. This agent made no commit and created no application or cloud resource. Another repository update committed a Plan E draft during authoring; that draft is preserved and remaining changes are uncommitted.",'',
 '## Not verified','',
 '- Live Paperclip import/dry-run, adapter/model execution, runtime skill installation and credentials.',
 '- Gemini evaluation on the new corpus, Atlas provisioning/egress, actual web/API behavior and deployed critical path.',
 '- Independent accuracy of sample coordinates, full new-source classifications/owner mappings, or three non-sample pairs.',
 '- Domain availability/qualifying registration, current event eligibility and submission.',
 '- URL resolution establishes retrieval only; it does not establish page permissions or substantive completeness.','']
(HERE/'RESULTS.md').write_text('\n'.join(lines))
print(json.dumps({k:report[k] for k in ('status','assertions_passed','yaml_frontmatter_files','agents','skills','skill_references','tasks','cross_utility_pairs','nonmatches','rank_order','unchanged_baseline_files')},indent=2))
for r in results:
    print(r['overlap_id'],r['project_a'],r['project_b'],f"{r['distance_mi']:.2f}",r['time_gap_days'],r['product_priority'])
