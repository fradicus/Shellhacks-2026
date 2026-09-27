"""Re-bind the F13 audit to the C46 drive-rule matches. Run from pipeline/: uv run python ../reports/audit/rebind_c46.py

The oracle below uses its own center, atan2 haversine, date and ordering arithmetic; it imports no production
matching code. The loader helpers are used only to project and hash review subjects, as in the original audit.
A pair downgrade is carried to the changed pair only when that pair had one and every supporting endpoint verdict is
still current. Nothing is promoted; any other pair has no verdict and stays needs_review.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, date, datetime
from itertools import combinations

from common import REPO_ROOT, load_json, write_json
from load.build import collect, join_projects, stage
from load.review_subjects import FINGERPRINT_VERSION, current_subjects, subject_hash, supporting_endpoints

LIMIT_MI, NEAR_MI, TOP = 25.0, 10.0, 15
AUDIT = REPO_ROOT / "data/review/audit/audit.json"
EVIDENCE = REPO_ROOT / "reports/audit/evidence.json"
REVIEWER = "cursor-agent re-binding under C46 (carries the original downgrade; not a new source review)"


def canonical(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    la, lb = math.radians(a[0]), math.radians(b[0])
    h = math.sin((lb - la) / 2) ** 2 + math.cos(la) * math.cos(lb) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 7917.6 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def oracle(projects: list[dict], locations: list[dict], routes: dict[str, dict], matches: list[dict]) -> list[dict]:
    centered = {}
    for p in projects:
        if not p["active"] or p["utility"] not in ("DESC", "GPC"):
            continue
        eps = [e for e in locations if e["project_id"] == p["_id"] and e["confidence"] != "rejected"]
        if eps:
            centered[p["project_key"]] = (p, tuple(sum(e[k] for e in eps) / len(eps) for k in ("lat", "lon")))
    expected = []
    for (ka, (pa, ca)), (kb, (pb, cb)) in combinations(sorted(centered.items()), 2):
        if pa["utility"] == pb["utility"]:
            continue
        if pa["utility"] != "DESC":
            (ka, pa, ca), (kb, pb, cb) = (kb, pb, cb), (ka, pa, ca)
        straight = miles(ca, cb)
        if straight > LIMIT_MI:
            continue
        mid = f"{ka}__{kb}"
        route = routes[mid]
        assert route["status"] == "ok", mid
        assert all(math.isclose(route[end][k], c[i], abs_tol=1e-9) for end, c in (("origin", ca), ("destination", cb))
                   for i, k in enumerate(("lat", "lon"))), f"{mid}: route not bound to the current centers"
        if route["drive_mi"] > LIMIT_MI:
            continue
        days = [date.fromisoformat(p["in_service"]["date"]) if p["in_service"]["precision"] == "day" else None
                for p in (pa, pb)]
        gap = abs((days[0] - days[1]).days) if all(days) else None
        band = 0 if route["drive_mi"] < NEAR_MI else 1
        expected.append({"_id": mid, "distance_mi": straight, "drive_mi": route["drive_mi"], "time_gap_days": gap,
                         "band": band})
    expected.sort(key=lambda m: (m["band"], m["time_gap_days"] is None, m["time_gap_days"] or 0, m["drive_mi"],
                                 m["distance_mi"], m["_id"]))
    by_id = {m["_id"]: m for m in matches}
    checks = [{"case": "complete_pair_ID_set", "passed": {m["_id"] for m in expected} == set(by_id)},
              {"case": "unique_pair_IDs", "passed": len(by_id) == len(matches)}]
    for rank, m in enumerate(expected, 1):
        m["rank"] = rank
        actual = by_id.get(m["_id"], {})
        passed = (math.isclose(actual.get("distance_mi", math.inf), m["distance_mi"], rel_tol=0, abs_tol=1e-10)
                  and all(actual.get(k) == m[k] for k in ("drive_mi", "time_gap_days", "band", "rank")))
        checks.append({"case": m["_id"], "passed": passed, "expected": m})
    return checks


def main() -> None:
    records, errors, _ = collect(REPO_ROOT)
    assert not errors, errors
    projects = load_json(REPO_ROOT / "data/projects/desc.json") + load_json(REPO_ROOT / "data/projects/gpc.json")
    locations = load_json(REPO_ROOT / "data/locations/locations.json")
    matches = load_json(REPO_ROOT / "data/matches/matches.json")
    routes = {r["_id"]: r for r in load_json(REPO_ROOT / "data/routes/routes.json")}
    checks = oracle(projects, locations, routes, matches)
    assert all(c["passed"] for c in checks), [c["case"] for c in checks if not c["passed"]]

    ready = {**records, "projects": join_projects(records["projects"], records["locations"])}
    subjects = current_subjects(ready)
    reviews = load_json(AUDIT)
    endpoints = {r["record_id"]: r for r in reviews if r["subject_type"] == "endpoint"}
    assert all(r["subject_hash"] == subject_hash(subjects[("endpoint", k)]) for k, r in endpoints.items())
    old_pairs = {r["record_id"]: r for r in reviews if r["subject_type"] == "pair"}
    now = datetime.now(UTC).isoformat()
    rebound, unaudited = [], []
    for m in sorted(matches, key=lambda m: m["rank"])[:TOP]:
        subject = subjects[("pair", m["_id"])]
        old = old_pairs.get(m["_id"])
        if old is None or not set(supporting_endpoints(subject)) <= set(endpoints):
            unaudited.append({"record_id": m["_id"], "reason": "no prior pair verdict" if old is None
                              else "a supporting endpoint has no current verdict"})
            continue
        rebound.append({**old, "reviewer": REVIEWER, "at": now, "fingerprint_version": FINGERPRINT_VERSION,
                        "subject_hash": subject_hash(subject), "subject_snapshot": subject,
                        "reason": old["reason"] + " Re-bound under C46: the pair's drive, band and rule version "
                                  "changed; its endpoint facts and verdicts did not.",
                        "rebound_from": old["subject_hash"]})
    dropped = sorted(set(old_pairs) - {r["record_id"] for r in rebound})
    write_json(AUDIT, [*rebound, *endpoints.values()])

    evidence = load_json(EVIDENCE)
    evidence["input_hashes"] = {"projects": canonical(projects), "locations": canonical(locations),
                                "matches": canonical(matches)}
    evidence["math_checks"] = checks
    top = sorted(matches, key=lambda m: m["rank"])[:TOP]
    evidence |= {"selected_pairs": top, "selected_count": len(top), "total_matches": len(matches),
                 "review_counts": {"pairs": len(rebound), "endpoints": len(endpoints), "confirmed": 0,
                                   "downgraded": len(rebound) + len(endpoints)}}
    evidence["rebinding"] = {
        "contract": "C46", "at": now, "rule": "drive route <= 25 mi after a 25 mi straight-line prefilter",
        "routes_sha256": canonical(load_json(REPO_ROOT / "data/routes/routes.json")),
        "rebound_pairs": [r["record_id"] for r in rebound], "unaudited_top_pairs": unaudited,
        "retired_pair_verdicts": dropped, "endpoint_verdicts_unchanged": len(endpoints),
    }
    write_json(EVIDENCE, evidence)
    staged = stage(records | {"reviews": load_json(AUDIT)}, "rebind-check")
    states: dict[str, int] = {}
    for m in staged["matches"]:
        states[m["review_state"]] = states.get(m["review_state"], 0) + 1
    print(json.dumps({"checks": len(checks), "rebound": len(rebound), "unaudited": len(unaudited),
                      "retired": len(dropped), "states": states}, sort_keys=True))


if __name__ == "__main__":
    main()
