"""F10: the spatial candidate search returns exactly what a scan of every pair returns, in the same order."""

from __future__ import annotations

import random
from datetime import date
from itertools import combinations
from math import degrees

from matches import core
from matches.benchmark import synthetic_projects

ANALYSIS_DATE = "2026-09-26"


def brute_force(projects: list[dict], analysis_date: str) -> list[dict]:
    """The pre-index reference: every combination through the canonical predicate."""
    out = []
    for p, q in combinations(projects, 2):
        hit, d = core.is_overlap(p, q)
        if hit:
            out.append(core.match_record(p, q, d, date.fromisoformat(analysis_date)))
    return out


def _project(key: str, utility: str, lat: float | None, lon: float | None) -> dict:
    return {
        "project_key": key,
        "utility": utility,
        "center": None if lat is None else {"lat": lat, "lon": lon, "basis": "two"},
        "in_service": {"raw": "1/1/2027", "date": "2027-01-01", "precision": "day"},
        "location_confidence": "high",
    }


def test_random_corpora_match_the_full_scan_exactly():
    for seed in range(8):
        projects = synthetic_projects(400, seed=seed, spread_deg=3.0)
        assert core.overlaps(projects, ANALYSIS_DATE) == brute_force(projects, ANALYSIS_DATE)


def test_boundaries_poles_and_ineligible_records():
    step = degrees(core.OVERLAP_MI / core.EARTH_RADIUS_MI)
    projects = [
        _project("A:on-rule", "DESC", 33.0, -81.0),
        _project("B:on-rule", "GPC", 33.0 + step, -81.0),  # on the rule: whichever side float error puts it, both agree
        _project("K:outside", "GPC", 33.0 + step * 1.001, -81.0),
        _project("C:inside", "GPC", 33.0 + step * 0.999, -81.0),
        _project("D:same-utility", "DESC", 33.0, -81.0001),
        _project("E:unknown", "unknown", 33.0, -81.0),
        _project("F:unlocated", "GPC", None, None),
        _project("G:pole", "DESC", 89.99, 0.0),
        _project("H:pole", "GPC", 89.99, 179.0),  # across the pole: near in miles, far in longitude
        _project("I:dateline", "DESC", 10.0, 179.99),
        _project("J:dateline", "GPC", 10.0, -179.99),
    ]
    found = core.overlaps(projects, ANALYSIS_DATE)
    assert found == brute_force(projects, ANALYSIS_DATE)
    pairs = {(m["a"], m["b"]) for m in found}
    assert ("A:on-rule", "C:inside") in pairs
    assert ("A:on-rule", "K:outside") not in pairs
    assert ("G:pole", "H:pole") in pairs and ("I:dateline", "J:dateline") in pairs
    assert not any("E:unknown" in pair or "F:unlocated" in pair for pair in pairs)


def test_candidates_are_a_superset_in_input_order():
    projects = synthetic_projects(300, seed=11, spread_deg=2.0)
    candidates = core.candidate_pairs(projects)
    assert candidates == sorted(candidates)
    hits = {(i, j) for i, j in combinations(range(len(projects)), 2) if core.is_overlap(projects[i], projects[j])[0]}
    assert hits <= set(candidates)
    assert len(candidates) < len(projects) * (len(projects) - 1) // 2


def test_input_order_is_preserved_after_shuffling():
    projects = synthetic_projects(200, seed=5, spread_deg=1.5)
    random.Random(3).shuffle(projects)
    assert core.overlaps(projects, ANALYSIS_DATE) == brute_force(projects, ANALYSIS_DATE)
