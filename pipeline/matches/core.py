"""Canonical overlap rules (specs/mission.md). The ONLY implementation; every feature imports it. Pure, no I/O.

A project dict, as consumed here:
    {"project_key": "DESC:6807B", "utility": "DESC" | "GPC" | "unknown",
     "center": {"lat": float, "lon": float, "basis": "two" | "one"} | None,
     "in_service": {"raw": str, "date": "YYYY-MM-DD" | None, "precision": "day" | "month" | "year" | "unknown"},
     "location_confidence": "high" | "medium" | "low" | None}   # weakest endpoint used for the center

Two rules (C46). The product rule is the DRIVE rule: a comparable pair overlaps when its stored driving route between
the two centers is <= 25 mi. A road is never shorter than the great-circle line, so only pairs within 25 straight-line
mi (inclusive) are candidates worth routing. Pass `drives` (match _id -> unrounded drive miles, None = unknown) to
`overlaps` to apply it; an unknown drive is never an overlap. Without `drives`, `overlaps` applies the sponsor's
straight-line example rule (< 25 mi), kept for the workbook check and for records produced before routes existed.
"""

from collections.abc import Container, Iterable, Mapping
from datetime import date
from math import asin, cos, radians, sin, sqrt
from typing import Any

from common.ids import match_id

EARTH_RADIUS_MI = 3958.8
OVERLAP_MI = 25.0
NEAR_BAND_MI = 10.0
RULE_VERSION = "overlap-25mi-v1"
RANK_VERSION = "nearby-band-v1"
DRIVE_RULE_VERSION = "overlap-25mi-drive-v1"
DRIVE_RANK_VERSION = "nearby-band-drive-v1"
KNOWN_UTILITIES = ("DESC", "GPC")


def center(endpoints: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """Mean lat/lon of the located endpoints; one located -> that point; none -> None. Rejected endpoints never count."""
    pts = [
        (e["lat"], e["lon"])
        for e in endpoints
        if e.get("lat") is not None and e.get("lon") is not None and e.get("confidence") != "rejected"
    ]
    if not pts:
        return None
    return {
        "lat": sum(p[0] for p in pts) / len(pts),
        "lon": sum(p[1] for p in pts) / len(pts),
        "basis": "one" if len(pts) == 1 else "two",
    }


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    h = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lon2 - lon1) / 2) ** 2
    h = min(1.0, max(0.0, h))  # float error can push h just outside [0, 1]
    return 2 * EARTH_RADIUS_MI * asin(sqrt(h))


def exact_date(in_service: dict[str, Any] | None) -> date | None:
    """Only day-precision dates count. Never impute Jan 1 / Dec 31 for month or year precision."""
    if not in_service or in_service.get("precision") != "day" or not in_service.get("date"):
        return None
    return date.fromisoformat(in_service["date"])


def time_gap_days(a: dict[str, Any] | None, b: dict[str, Any] | None) -> int | None:
    da, db = exact_date(a), exact_date(b)
    return None if da is None or db is None else abs((da - db).days)


def comparable(pa: dict[str, Any], pb: dict[str, Any], known: Container[str] | None = KNOWN_UTILITIES) -> bool:
    """Different utilities, both known. `known=None` accepts any named utility (the national corpus), never "unknown"."""
    ua, ub = pa.get("utility"), pb.get("utility")
    if known is None:
        named = all(isinstance(u, str) and u and u != "unknown" for u in (ua, ub))
        return named and ua != ub
    return ua in known and ub in known and ua != ub


def straight_line_mi(
    pa: dict[str, Any], pb: dict[str, Any], known: Container[str] | None = KNOWN_UTILITIES
) -> float | None:
    """Unrounded center-to-center great-circle miles for a comparable pair with both centers, else None."""
    if not comparable(pa, pb, known):
        return None
    ca, cb = pa.get("center"), pb.get("center")
    if not ca or not cb:
        return None
    return haversine_mi(ca["lat"], ca["lon"], cb["lat"], cb["lon"])


def is_overlap(pa: dict[str, Any], pb: dict[str, Any]) -> tuple[bool, float | None]:
    """Straight-line example rule: (overlap?, unrounded distance). Comparable pair AND distance < 25 mi (25.0 is out)."""
    d = straight_line_mi(pa, pb)
    return (False, None) if d is None else (d < OVERLAP_MI, d)


def is_drive_overlap(
    pa: dict[str, Any], pb: dict[str, Any], drive_mi: float | None, known: Container[str] | None = KNOWN_UTILITIES
) -> tuple[bool, float | None]:
    """Drive rule: (overlap?, unrounded straight-line distance). Comparable pair within the straight-line pre-filter
    AND a known drive <= 25 mi (25.0 is in). An unknown drive (no route, never fetched, stale) is never an overlap."""
    d = straight_line_mi(pa, pb, known)
    if d is None or d > OVERLAP_MI or drive_mi is None:
        return False, d
    return drive_mi <= OVERLAP_MI, d


def route_candidates(
    projects: Iterable[dict[str, Any]], known: Container[str] | None = KNOWN_UTILITIES
) -> list[tuple[dict[str, Any], dict[str, Any], float]]:
    """(a, b, straight-line mi) for every comparable pair within 25 straight-line mi (inclusive), a/b by project_key."""
    items = list(projects)
    out = []
    for i, j in candidate_pairs(items, known):
        d = straight_line_mi(items[i], items[j], known)
        if d is not None and d <= OVERLAP_MI:
            pa, pb = sorted((items[i], items[j]), key=lambda x: x["project_key"])
            out.append((pa, pb, d))
    return out


def trusted_center(p: dict[str, Any]) -> bool:
    """A center good enough for `future`: high/medium confidence, and high if it rests on one endpoint (F10)."""
    conf = p.get("location_confidence")
    basis = (p.get("center") or {}).get("basis")
    return conf == "high" or (conf == "medium" and basis != "one")


def view(pa: dict[str, Any], pb: dict[str, Any], analysis_date: date) -> str:
    """historical: an exact date before analysis_date. future: both exact dates on/after it and both centers trusted
    (see trusted_center). tentative: everything else (unknown date, low/unknown confidence, one-endpoint medium)."""
    da, db = exact_date(pa.get("in_service")), exact_date(pb.get("in_service"))
    if (da and da < analysis_date) or (db and db < analysis_date):
        return "historical"
    if da and db and trusted_center(pa) and trusted_center(pb):
        return "future"
    return "tentative"


# Great-circle distance is never shorter than the latitude arc between two points, so a pair whose latitudes alone are
# 25 mi apart cannot overlap. The margin keeps float error from ever pruning a pair the exact predicate would keep.
_LAT_WINDOW_RAD = OVERLAP_MI / EARTH_RADIUS_MI + 1e-9


def candidate_pairs(
    projects: list[dict[str, Any]], known: Container[str] | None = KNOWN_UTILITIES
) -> list[tuple[int, int]]:
    """Index pairs (i < j, input order) that could overlap: both located, comparable utilities, latitudes within
    25 mi. A superset of the overlapping pairs; the distance predicates stay the only test."""
    located = [
        (radians(p["center"]["lat"]), i, p.get("utility"))
        for i, p in enumerate(projects)
        if p.get("center") and (p.get("utility") in known if known is not None else True)
    ]
    located.sort(key=lambda row: (row[0], row[1]))
    out: list[tuple[int, int]] = []
    lo = 0
    for hi, (lat, i, utility) in enumerate(located):
        while located[lo][0] < lat - _LAT_WINDOW_RAD:
            lo += 1
        for _, j, utility2 in located[lo:hi]:
            if utility2 != utility:
                out.append((min(i, j), max(i, j)))
    out.sort()
    return out


def overlaps(
    projects: Iterable[dict[str, Any]],
    analysis_date: date | str,
    drives: Mapping[str, float | None] | None = None,
    *,
    known: Container[str] | None = KNOWN_UTILITIES,
) -> list[dict[str, Any]]:
    """Every overlapping pair as a match dict (unsorted; see priority_sort). Distances stay unrounded.
    Pairs come out in the same order as a scan of every combination of the input.

    With `drives` (match _id -> drive miles; None or absent = unknown) this is the drive rule and each match carries
    `drive_mi`, its band taken from the drive. Without it, the straight-line example rule."""
    if isinstance(analysis_date, str):
        analysis_date = date.fromisoformat(analysis_date)
    out = []
    for pa, pb, d in route_candidates(projects, known):
        if drives is None:
            if d < OVERLAP_MI:
                out.append(match_record(pa, pb, d, analysis_date))
            continue
        drive = drives.get(match_id(pa["project_key"], pb["project_key"]))
        if is_drive_overlap(pa, pb, drive, known)[0]:
            out.append(match_record(pa, pb, d, analysis_date, drive=drive))
    return out


def match_record(
    p: dict[str, Any], q: dict[str, Any], d: float, analysis_date: date, *, drive: float | None = None
) -> dict[str, Any]:
    """The stored match for an overlapping pair at unrounded straight-line distance `d`; `drive` only under the drive
    rule, which then sets the band and rule versions."""
    pa, pb = sorted((p, q), key=lambda x: x["project_key"])
    if drive is None:
        rule = {"band": 0 if d < NEAR_BAND_MI else 1, "rule_version": RULE_VERSION, "rank_version": RANK_VERSION}
    else:
        rule = {"drive_mi": drive, "band": 0 if drive < NEAR_BAND_MI else 1,
                "rule_version": DRIVE_RULE_VERSION, "rank_version": DRIVE_RANK_VERSION}
    return {
        "_id": match_id(pa["project_key"], pb["project_key"]),
        "a": pa["project_key"],
        "b": pb["project_key"],
        "distance_mi": d,
        "time_gap_days": time_gap_days(pa.get("in_service"), pb.get("in_service")),
        **rule,
        "analysis_date": analysis_date.isoformat(),
        "view": view(pa, pb, analysis_date),
    }

def priority_key(m: dict[str, Any]) -> tuple:
    gap, drive = m["time_gap_days"], m.get("drive_mi")
    return (m["band"], gap is None, gap if gap is not None else 0,
            m["distance_mi"] if drive is None else drive, m["distance_mi"], m["_id"])


def priority_sort(matches: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """nearby-band-v1 / nearby-band-drive-v1: band 0 before 1, exact gap ascending (unknown last), unrounded drive
    distance (straight-line when there is no drive), then straight-line distance, then pair id. Adds `rank`."""
    return [{**m, "rank": i} for i, m in enumerate(sorted(matches, key=priority_key), start=1)]
