"""C26 candidate locations: facility names a project's source text states, matched to public facility points.

Exact normalized-name equality plus operator or voltage corroboration; ambiguity and anything else stays unlocated.
"""

from __future__ import annotations

import math
import re

from common.names import norm_name

# Words that describe work, not a facility name.
DESCRIPTORS = {
    "LINE", "LINES", "REBUILD", "PROJECT", "PROJECTS", "UPGRADE", "UPGRADES", "INSTALL", "STORM", "STRUCTURE",
    "STRUCTURES", "TEMPERATURE", "TERMINAL", "RELOCATION", "REFURB", "CONVERSION", "EXPANSION", "MODERNIZATION",
    "TRANSMISSION", "SUBSTATION", "SUB", "ADDITION", "REPLACEMENT", "CIRCUIT", "CIRCUITS", "SEGMENT", "AND", "TO",
    "DOUBLE", "RECONDUCTOR", "SWAP", "ELR", "DISTRIBUTION", "BREAKER", "BREAKERS", "RING", "BUS", "CAP", "BANK",
    "CAPACITOR", "TRANSFORMER", "TRANSFORMERS", "THIRD", "SECOND", "STATCOM", "REACTOR", "SINGLE", "ASSET", "RENEWAL",
    "INTERCONNECTION", "DELIVERY", "RETIREMENT", "RELAY", "RELAYS", "SS", "SWT", "STA", "SW", "DIC", "GENERATOR",
    "NETWORK", "OPGW", "CONTROL", "POWER", "HOUSE", "NEW", "PARTIAL", "SVC", "STATION", "SWITCHYARD", "AUTOTRANSFORMER",
    "SWITCH", "CBS", "EQUIPMENT", "POINT", "LOAD", "DC", "REDUNDANCY",
}
NUMERIC = re.compile(r"T\d+|TR\d+|[\d./]+(KV)?")
QUEUE_ID = re.compile(r"[JSR]\d+(/[JSR]\d+)*")
PARTICLES = {"du", "de", "la", "le"}
ABBREVIATIONS = {"RD": "ROAD", "CO": "COUNTY", "SAINT": "ST", "JCT": "JUNCTION", "AVE": "AVENUE", "MT": "MOUNT"}
TRAILING_CODE = re.compile(r"\s*[–—-]\s*[A-Z]+\d+$")
LEADING = {"LINE", "REBUILD", "INSTALL", "REINFORCE", "JTIQ", "REPLACE", "UPGRADE", "RECONDUCTOR", "CONSTRUCT", "BUILD",
           "ADD", "EXPAND", "RETIRE", "UPRATE", "CONVERT", "RELOCATE", "REROUTE", "NEW"}
# A site project must name facility equipment after the facility name.
SITE_EQUIPMENT = re.compile(
    r"\b(Substations?|Sub|Transformers?|TR\d+|STATCOM|Ring Bus|Breakers?|Capacitors?|Cap Bank|Reactor|"
    r"Switching Station|Single Point of Failure|SS|Swt St|SW STA|DIC|SVC|Station|Switchyard|Autotransformers?|Bank|"
    r"Switch|CBs|Delivery Point)\b",
    re.I,
)
# Names that are not a single facility: programs, areas, multi-line lists. Taps/structures are not endpoints.
NOT_A_FACILITY = re.compile(r"\bArea\b|,|&")
NOT_AN_ENDPOINT = re.compile(r"\b(tap|str)\b", re.I)
SEPARATOR = re.compile(r"\s+[–—-]\s+|(?<=[A-Za-z])[–—-](?=\s?[A-Z])|\s+to\s+")
KV = re.compile(r"([\d.]+(?:\s*/\s*[\d.]+)*)\s*-?\s*kV", re.I)
DESCRIPTION_ENDPOINTS = re.compile(
    r"\b(?:between|from) (?:the )?([A-Z][\w.'’]*(?: [A-Z][\w.'’]*){0,3}) [Ss]ubstation (?:and|to) (?:the )?"
    r"([A-Z][\w.'’]*(?: [A-Z][\w.'’]*){0,3}) [Ss]ubstation"
)
DUPLICATE_METERS = 1000.0


def _facility_name(text: str) -> str | None:
    """Leading run of capitalized name tokens, dropping work descriptors; None if nothing name-like remains."""
    tokens = text.split()
    # Line numbers ("0754", "5400") lead some names; short numbers ("9 Mile") are part of the name.
    while tokens and (tokens[0].upper() in LEADING or (tokens[0].isdigit() and len(tokens[0]) >= 3)
                      or QUEUE_ID.fullmatch(tokens[0])):
        tokens = tokens[1:]
    name: list[str] = []
    for token in tokens:
        up = token.upper()
        if not name and token.isdigit():  # "9 Mile", "7 Mile Creek"
            name.append(token)
            continue
        if token in PARTICLES and name:
            name.append(token)
            continue
        if up in DESCRIPTORS or NUMERIC.fullmatch(up) or not (token[0].isupper() or token[0].isdigit()):
            break
        name.append(token)
    return " ".join(name) or None


def facilities_named(project_name: str, description: str | None) -> dict:
    """Return {'kind': 'site'|'line'|None, 'names': [...], 'from': 'name'|'description', 'reason': str|None}."""
    name = TRAILING_CODE.sub("", re.sub(r"\([^)]*\)|\[[^\]]*(\]|$)", " ", project_name).strip())
    name = re.sub(r"^[A-Z][\w ]*?\bon\s+(?=[A-Z])", "", name)  # "Remediate Sag on Delhi - Green"
    second = re.search(r"\band\s+(\S+)", name)
    if NOT_A_FACILITY.search(name) or (second and second[1][0].isupper() and second[1].upper() not in DESCRIPTORS):
        return {"kind": None, "names": [], "from": "name", "reason": "program_area_or_multi_facility"}
    parts = [p for p in SEPARATOR.split(name) if p.strip()]
    if len(parts) > 2:
        return {"kind": None, "names": [], "from": "name", "reason": "multi_terminal_line"}
    if len(parts) == 2:
        names = [None if NOT_AN_ENDPOINT.search(p) else _facility_name(p) for p in parts]
        work_only = [n is None and not NOT_AN_ENDPOINT.search(p) for n, p in zip(names, parts, strict=True)]
        if any(work_only) and not all(work_only):
            # "North Lake SS – Transformer Asset Renewal": the dash introduces work, not a second endpoint.
            name = parts[work_only.index(False)] + " " + parts[work_only.index(True)]
        elif any(names) and names[0] != names[1]:
            return {"kind": "line", "names": names, "from": "name", "reason": None}
        else:
            return {"kind": None, "names": [], "from": "name", "reason": "endpoint_not_named"}
    if at := re.search(r"\bat (?:the )?([A-Z][\w.'’]*(?: [A-Z][\w.'’]*){0,3}) (?:Substation|Station|Sub)\b", name):
        return {"kind": "site", "names": [at[1]], "from": "name", "reason": None}
    if SITE_EQUIPMENT.search(name) and not NOT_AN_ENDPOINT.search(name) and (site := _facility_name(name)):
        return {"kind": "site", "names": [site], "from": "name", "reason": None}
    if description and (m := DESCRIPTION_ENDPOINTS.search(description)):
        return {"kind": "line", "names": [m.group(1), m.group(2)], "from": "description", "reason": None}
    return {"kind": None, "names": [], "from": "name", "reason": "no_named_facility"}


def facility_key(name: str) -> str:
    """Shared name normalization for both sides: common noise words, voltage suffixes, abbreviations."""
    key = re.sub(r"\b[\d./]+\s*KV\b", " ", norm_name(name).replace(".", ""))
    return " ".join(ABBREVIATIONS.get(token, token) for token in key.split() if token not in {"STATION", "SWITCHYARD"})


def voltages_kv(*texts: str | None) -> set[int]:
    out: set[int] = set()
    for text in texts:
        for group in KV.findall(text or ""):
            for value in group.split("/"):
                try:
                    out.add(round(float(value.strip())))
                except ValueError:
                    continue
    return out


def _meters(a: dict, b: dict) -> float:
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat, dlon = lat2 - lat1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def match_facility(name: str | None, facilities: list[dict], operator_keys: list[str], kv: set[int]) -> dict:
    """Exact normalized name, then operator or voltage corroboration, then a single physical site."""
    if name is None:
        return {"status": "not_a_facility", "name": None}
    key = facility_key(name)
    hits = [f for f in facilities if facility_key(f["name"]) == key]
    if not hits:
        return {"status": "no_facility", "name": name, "norm": key}
    corroborated = []
    for f in hits:
        why = []
        operator = (f.get("operator") or "").upper()
        if operator and any(k in operator for k in operator_keys):
            why.append("operator")
        tagged = {round(int(v) / 1000) for v in re.findall(r"\d+", f.get("voltage") or "") if int(v) >= 1000}
        if kv & tagged:
            why.append("voltage")
        if why:
            corroborated.append((f, why))
    if not corroborated:
        return {"status": "not_corroborated", "name": name, "norm": key, "facility_ids": [f["id"] for f in hits]}
    # One site mapped twice (node + area) is one facility; anything farther apart is ambiguous.
    if any(_meters(a[0], b[0]) > DUPLICATE_METERS for a in corroborated for b in corroborated):
        return {"status": "ambiguous", "name": name, "norm": key, "facility_ids": [f["id"] for f, _ in corroborated]}
    facility, why = sorted(corroborated, key=lambda c: (c[0]["id"].startswith("node"), c[0]["id"]))[0]
    return {"status": "matched", "name": name, "norm": key, "facility": facility, "corroboration": why}


def candidate_center(kind: str, matches: list[dict]) -> dict | None:
    """Mission rule: a site point, the mean of two endpoints, or the single endpoint (partial)."""
    found = [m for m in matches if m["status"] == "matched"]
    if not found:
        return None
    points = [m["facility"] for m in found]
    if kind == "site":
        basis = "source_point"
    else:
        basis = "two" if len(points) == 2 else "one"
    lat = round(sum(p["lat"] for p in points) / len(points), 6)
    lon = round(sum(p["lon"] for p in points) / len(points), 6)
    ids = ", ".join(f"OSM {p['id']} ({p['name']})" for p in points)
    partial = " Partial: one of two endpoints." if basis == "one" else ""
    why = ", ".join(sorted({w for m in found for w in m["corroboration"]}))
    evidence = f"Unverified candidate: exact-name match to {ids}, corroborated by {why}.{partial}"
    return {"lat": lat, "lon": lon, "basis": basis, "evidence": evidence}
