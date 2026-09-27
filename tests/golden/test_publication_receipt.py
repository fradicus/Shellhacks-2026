"""C37: the load Action's readback catches Atlas serving something other than the committed snapshot."""
import mongomock

from common.publication import differences, display_kind, served, summarize

POINT = {'lat': 27.0, 'lon': -81.0, 'basis': 'one', 'evidence': 'fixture'}
COUNTY = {'precision': 'county', 'eligible_for_matching': False, 'reference_source': {'url': 'https://example.test'},
          'anchors': [{'county_geoid': '12001', 'lat': 29.6, 'lon': -82.3}]}
# Explicit fixtures, not real public projects.
PROJECTS = [
    {'id': 'fx:confirmed', 'states': ['12'], 'counties': [], 'center': POINT, 'location_review': 'confirmed'},
    {'id': 'fx:tentative', 'states': ['12'], 'counties': [], 'center': POINT, 'location_review': 'unreviewed'},
    {'id': 'fx:county', 'states': ['12'], 'counties': ['12001'], 'center': None, 'location_review': 'unlocated',
     'approximate_location': COUNTY},
    {'id': 'fx:unlocated', 'states': ['12', '13'], 'counties': [], 'center': None, 'location_review': 'unlocated'},
    {'id': 'fx:rejected', 'states': ['13'], 'counties': [], 'center': POINT, 'location_review': 'rejected'},
]


def test_display_kind_matches_map_rules():
    assert [display_kind(p) for p in PROJECTS] == ['confirmed', 'tentative', 'county', None, None]
    summary = summarize(PROJECTS)
    assert summary['states']['12'] == {'projects': 4, 'drawn': 3, 'confirmed': 1, 'tentative': 1, 'county': 1}
    assert summary['states']['13'] == {'projects': 2, 'drawn': 0}


def test_readback_flags_missing_or_stale_projects():
    db = mongomock.MongoClient().db
    db.meta.insert_one({'_id': 'national_active', 'dataset': 'sha1'})
    db.national_projects.insert_many([{**p, 'dataset': 'sha1'} for p in PROJECTS])
    db.national_projects.insert_one({**PROJECTS[0], 'id': 'fx:old', 'dataset': 'sha0'})  # retained previous dataset
    dataset, got = served(db)
    assert dataset == 'sha1' and differences(summarize(PROJECTS), got) == []
    db.national_projects.delete_one({'id': 'fx:tentative', 'dataset': 'sha1'})
    errors = differences(summarize(PROJECTS), served(db)[1])
    assert any(e.startswith('projects:') for e in errors) and any(e.startswith('state 12:') for e in errors)
