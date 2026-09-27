"""Generate dataset-scoped nearby candidates before publication, using only stored facts."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from itertools import product
from math import cos, floor, isfinite, radians, sin
from pathlib import Path
from typing import Any

from common import REPO_ROOT, load_json, match_id
from matches.core import EARTH_RADIUS_MI, NEAR_BAND_MI, haversine_mi, priority_sort, time_gap_days
from matches.routes import Candidate, drives_for, load_routes, route_summary

RULE = "national-drive-25mi-v1"
ROUTES = Path("data/national_pairs/routes.json")
LIMIT_MI = 25.0
COLLECTION = "national_candidate_pairs"
MAX_PAIRS = 100_000  # fail publication explicitly rather than truncate the candidate universe
CELL = 2 * EARTH_RADIUS_MI * sin(LIMIT_MI / (2 * EARTH_RADIUS_MI)) * (1 + 1e-12)
OFFSETS = tuple(product((-1, 0, 1), repeat=3))


def owner_key(value: str) -> str:
    return " ".join(value.casefold().split())


def owner_index(ledger: dict) -> dict[tuple[str, str], frozenset[str]]:
    """Only explicit aliases. A conflicting alias fails the release, never picks a winner."""
    result = {}
    for entry in ledger["entries"]:
        identities = frozenset(entry["identities"])
        if not identities or not entry["evidence"]:
            raise ValueError("owner identity and evidence are required")
        for source in entry.get("source_ids", ["*"]):
            for alias in entry["aliases"]:
                key = (source, owner_key(alias))
                if not key[1] or key in result and result[key] != identities:
                    raise ValueError(f"ambiguous owner alias: {source}: {alias}")
                result[key] = identities
    return result


def resolve_owner(name: str | None, source: str, owners: dict) -> frozenset[str] | None:
    if not isinstance(name, str):
        return None
    key = owner_key(name)
    return owners.get((source, key), owners.get(("*", key)))


def identities(p: dict, owners: dict) -> frozenset[str] | None:
    matches = [resolve_owner(name, p.get("source_id", ""), owners)
               for name in [p.get("owner"), *p.get("other_owners", [])]]
    if any(match is None for match in matches):
        return None
    return frozenset().union(*matches)


def exclusion(p: dict) -> str | None:
    if p["_id"].startswith("legacy:"):
        return "legacy"
    if p.get("status_group") in {"in_service", "cancelled"}:
        return "inactive_status"
    if p.get("location_review") not in {"confirmed", "unreviewed"}:
        return "location_review"
    tier = str((p.get("location_candidate") or {}).get("tier", "")).lower()
    if "county" in tier or "area" in tier:
        return "area_only"
    c = p.get("center")
    if not c or any(type(c.get(k)) not in (int, float) or not isfinite(c[k]) or abs(c[k]) > bound
                    for k, bound in (("lat", 90), ("lon", 180))):
        return "no_usable_center"
    return None


def tier(p: dict) -> str:
    if p["location_review"] == "confirmed":
        return "confirmed"
    return "official" if (p.get("location_candidate") or {}).get("tier") == "official" else "tentative"


def cell(p: dict) -> tuple[int, int, int]:
    lat, lon = radians(p["center"]["lat"]), radians(p["center"]["lon"])
    xyz = (cos(lat) * cos(lon), cos(lat) * sin(lon), sin(lat))
    return tuple(floor(EARTH_RADIUS_MI * v / CELL) for v in xyz)


def candidates(snapshot: dict, ledger: dict | None = None, root: Path = REPO_ROOT) -> dict[str, Any]:
    """Straight-line prefilter: every cross-owner pair within 25 straight-line miles (inclusive), straight-line ranked."""
    ledger = ledger if ledger is not None else load_json(root / "data/national_pairs/owners.json")
    owners = owner_index(ledger)
    regions = {s["state_fips"]: s.get("census_region_code") for s in snapshot.get("geography", {}).get("states", [])}
    excluded, unknown = Counter(), Counter()
    accepted, seen = [], set()
    for p in sorted(snapshot["projects"], key=lambda row: row["_id"]):
        if p["_id"] in seen:
            raise ValueError(f"duplicate project ID: {p['_id']}")
        seen.add(p["_id"])
        reason = exclusion(p)
        if reason:
            excluded[reason] += 1
            continue
        ids = identities(p, owners)
        if not ids:
            excluded["unresolved_owner"] += 1
            for name in [p.get("owner"), *p.get("other_owners", [])]:
                if resolve_owner(name, p.get("source_id", ""), owners) is None:
                    unknown[str(name)] += 1
            continue
        accepted.append((p, ids))
    buckets = defaultdict(list)
    pairs, comparisons = [], 0
    for p, pids in accepted:
        pos = cell(p)
        for offset in OFFSETS:
            for q, qids in buckets[tuple(a + b for a, b in zip(pos, offset, strict=True))]:
                if pids & qids:
                    continue
                comparisons += 1
                a, b = q, p  # input is sorted by ID; earlier records are canonical first
                ca, cb = a["center"], b["center"]
                distance = haversine_mi(ca["lat"], ca["lon"], cb["lat"], cb["lon"])
                if distance > LIMIT_MI:
                    continue
                milestones = [{"date": x.get("in_service", {}).get("value"),
                               "precision": x.get("in_service", {}).get("precision")} for x in (a, b)]
                states = [set(x.get("states", [])) for x in (a, b)]
                region_sets = [{regions[s] for s in st if regions.get(s)} for st in states]
                plans = [(x.get("planning_region") or "").strip().lower() for x in (a, b)]
                worst = max((tier(a), tier(b)), key={"confirmed": 0, "official": 1, "tentative": 2}.__getitem__)
                pair_id = "npc:" + hashlib.sha256(json.dumps([a["_id"], b["_id"]]).encode()).hexdigest()[:32]
                if len(pairs) >= MAX_PAIRS:
                    raise ValueError("national candidate safety limit exceeded; previous dataset must remain active")
                pairs.append({
                    "_id": pair_id, "a": a["_id"], "b": b["_id"], "distance_mi": distance,
                    "time_gap_days": time_gap_days(*milestones), "band": 0 if distance < 10 else 1,
                    "tier": worst, "rule_version": RULE, "identity_version": ledger["version"],
                    "shared_states": sorted(states[0] & states[1]),
                    "shared_regions": sorted(region_sets[0] & region_sets[1]),
                    "shared_plans": [plans[0]] if plans[0] and plans[0] == plans[1] else [],
                    "geo_a": {"type": "Point", "coordinates": [ca["lon"], ca["lat"]]},
                    "geo_b": {"type": "Point", "coordinates": [cb["lon"], cb["lat"]]},
                    "owners_a": sorted(qids), "owners_b": sorted(pids),
                })
        buckets[pos].append((p, pids))
    pairs = priority_sort(pairs)
    return {"pairs": pairs, "coverage": {
        "rule_version": RULE, "identity_version": ledger["version"],
        "input_projects": len(seen), "eligible_projects": len(accepted), "excluded": dict(sorted(excluded.items())),
        "unresolved_owners": dict(sorted(unknown.items())), "distance_comparisons": comparisons,
        "pairs": len(pairs), "tiers": dict(sorted(Counter(p["tier"] for p in pairs).items())),
    }}


def route_candidates(pairs: list[dict[str, Any]]) -> list[Candidate]:
    """Prefilter pairs in the shape matches.routes binds and fetches: centers taken from the pair's stored points."""
    def end(key: str, geo: dict[str, Any]) -> dict[str, Any]:
        lon, lat = geo["coordinates"]
        return {"project_key": key, "center": {"lat": lat, "lon": lon}}
    return [(end(p["a"], p["geo_a"]), end(p["b"], p["geo_b"]), p["distance_mi"]) for p in pairs]


def generate(snapshot: dict, ledger: dict | None = None, root: Path = REPO_ROOT,
             routes: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """C46 drive rule: a prefilter pair is kept when its stored route to the current centers is <= 25 driving miles.

    A pair without a current route (missing, stale or no drivable road) is excluded and counted, never guessed."""
    found = candidates(snapshot, ledger, root)
    routes = load_routes(root / ROUTES) if routes is None else routes
    drives, states = drives_for(route_candidates(found["pairs"]), routes)
    pairs, over = [], 0
    for p in found["pairs"]:
        mid = match_id(p["a"], p["b"])
        drive = drives[mid]
        if drive is None:
            continue
        if drive > LIMIT_MI:
            over += 1
            continue
        rest = {k: v for k, v in p.items() if k != "rank"}
        pairs.append({**rest, "drive_mi": drive, "band": 0 if drive < NEAR_BAND_MI else 1,
                      "route": route_summary(routes[mid])})
    pairs = priority_sort(pairs)
    return {"pairs": pairs, "coverage": {
        **found["coverage"], "straight_line_candidates": len(found["pairs"]),
        "route_states": dict(sorted(Counter(states.values()).items())), "drive_over_limit": over,
        "pairs": len(pairs), "tiers": dict(sorted(Counter(p["tier"] for p in pairs).items())),
    }}
