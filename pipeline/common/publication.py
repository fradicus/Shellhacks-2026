"""C37 publication receipt: what the national snapshot should draw, and whether Atlas serves exactly that.

    uv run python -m common.publication     # before merge: expected per-state table (no database)
    # in the load Action, after national.load: MONGODB_URI_RW set -> read back the active dataset and fail on drift

The drawn/tentative/county split mirrors displayPoints() in web/lib/national/locations.ts; keep them in step.
"""
from __future__ import annotations

import hashlib
import os
import sys
from collections import Counter, defaultdict

FIELDS = ('id', 'states', 'counties', 'center', 'location_review', 'approximate_location')


def display_kind(project: dict) -> str | None:
    """How the existing maps draw a project: confirmed, tentative, county, or not at all (None)."""
    review = project.get('location_review')
    if review == 'rejected':
        return None
    center = project.get('center')
    if center and review != 'unlocated':
        return 'confirmed' if review == 'confirmed' else 'tentative'
    area = project.get('approximate_location') or {}
    if (center is None and area.get('precision') == 'county' and area.get('eligible_for_matching') is False
            and (area.get('reference_source') or {}).get('url')
            and any(a.get('county_geoid') in project.get('counties', []) for a in area.get('anchors') or [])):
        return 'county'
    return None


def summarize(projects) -> dict:
    """Per-state counts plus an ID digest. A multi-state project counts once in each of its states."""
    states, ids = defaultdict(Counter), []
    for project in projects:
        ids.append(project['id'])
        kind = display_kind(project)
        for state in project.get('states') or ['unknown']:
            states[state]['projects'] += 1
            states[state]['drawn'] += kind is not None
            if kind:
                states[state][kind] += 1
    return {'projects': len(ids), 'ids_sha256': hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest(),
            'states': {s: dict(sorted(c.items())) for s, c in sorted(states.items())}}


def expected(root=None) -> dict:
    from common import REPO_ROOT
    from national.build import load_snapshot
    snapshot = load_snapshot(root or REPO_ROOT)
    return summarize({**p, 'id': p['_id']} for p in snapshot['projects'])


def served(db) -> tuple[str | None, dict]:
    dataset = (db.meta.find_one({'_id': 'national_active'}) or {}).get('dataset')
    rows = db.national_projects.find({'dataset': dataset}, {k: 1 for k in FIELDS})
    return dataset, summarize(rows)


def differences(want: dict, got: dict) -> list[str]:
    errors = [f'{k}: expected {want[k]}, Atlas {got[k]}' for k in ('projects', 'ids_sha256') if want[k] != got[k]]
    for state in sorted(set(want['states']) | set(got['states'])):
        a, b = want['states'].get(state, {}), got['states'].get(state, {})
        if a != b:
            errors.append(f'state {state}: expected {a}, Atlas {b}')
    return errors


def table(summary: dict) -> str:
    kinds = ('projects', 'drawn', 'confirmed', 'tentative', 'county')
    lines = ['| state | ' + ' | '.join(kinds) + ' |', '|---' * (len(kinds) + 1) + '|']
    lines += [f'| {s} | ' + ' | '.join(str(c.get(k, 0)) for k in kinds) + ' |' for s, c in summary['states'].items()]
    return '\n'.join(lines) + f"\n\n{summary['projects']} projects; ID digest `{summary['ids_sha256'][:16]}`\n"


def main() -> int:
    want = expected()
    report = '## Expected national publication\n\n' + table(want)
    uri, status = os.environ.get('MONGODB_URI_RW'), 0
    if uri:
        from pymongo import MongoClient
        client = MongoClient(uri, serverSelectionTimeoutMS=20_000, appname='gridbridge-publication-receipt')
        try:
            dataset, got = served(client[os.environ.get('MONGODB_DB', 'gridbridge')])
        finally:
            client.close()
        errors = differences(want, got)
        sha = os.environ.get('GIT_SHA')
        if sha and dataset != sha:
            errors.insert(0, f'active dataset {dataset} is not this commit {sha}')
        status = 1 if errors else 0
        report += (f'\n## Atlas readback: active dataset `{dataset}`\n\n'
                   + ('**Matches the expected publication.**\n' if not errors
                      else '**MISMATCH**\n\n' + '\n'.join(f'- {e}' for e in errors) + '\n'))
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write(report)
    return status


if __name__ == '__main__':
    sys.exit(main())
