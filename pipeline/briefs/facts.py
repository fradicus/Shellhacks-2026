"""Pure current-fact projection shared with F06, before dataset-prefixing IDs."""

import hashlib
import json
import math
import re
from typing import Any

from locations.core import SOURCE_BLOCKING_FLAGS
from matches import core

INPUT_VERSION = "brief-facts-v1"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def unique(records: list[dict], field: str = "_id") -> dict[str, dict]:
    out = {}
    for record in records:
        key = record[field]
        if not isinstance(key, str) or key in out:
            raise ValueError("duplicate_or_invalid_identity")
        out[key] = record
    return out


def build_match_input(match: dict, projects_by_id: dict, locations_by_id: dict, sources_by_id: dict) -> dict:
    """Return {facts, input_hash, binding}. Only `facts` may be transported to Gemini.

    Georgia contributes names, dates and codes only. Internal binding covers source/version/endpoint
    provenance without putting coordinates, descriptions, raw excerpts or audit state in the prompt.
    """
    facts, bindings, prepared = [], {}, []
    for side in ("a", "b"):
        binding = match["bindings"][side]
        project = projects_by_id[binding["project_id"]]
        sid = project["source"]["source_id"]
        source = sources_by_id[sid]
        if (project.get("active") is not True or project["project_key"] != match[side]
                or project["_id"] != f"{match[side]}@{sid}" or sid != binding["source_id"]
                or source["_id"] != sid or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
                or project["utility"] not in ("DESC", "GPC")):
            raise ValueError("invalid_project_source_binding")
        if SOURCE_BLOCKING_FLAGS & set(project.get("quality_flags", [])):
            raise ValueError("source_gated_project")
        locids = binding["location_ids"]
        if not 1 <= len(locids) <= 2 or len(set(locids)) != len(locids):
            raise ValueError("invalid_supporting_endpoints")
        eps = [locations_by_id[key] for key in locids]
        current_ids = {e["_id"] for e in locations_by_id.values()
                       if e.get("project_id") == project["_id"] and e.get("confidence") != "rejected"}
        if set(locids) != current_ids:
            raise ValueError("stale_supporting_endpoint_set")
        if len({e["endpoint_index"] for e in eps}) != len(eps):
            raise ValueError("duplicate_endpoint_slot")
        filed = project.get("filed_endpoints", project.get("endpoints", []))
        for e in eps:
            if (e.get("project_id") != project["_id"] or e.get("source_id") != sid
                    or e["project_key"] != match[side] or e["confidence"] not in ("high", "medium", "low")
                    or isinstance(e["endpoint_index"], bool)
                    or e["endpoint_index"] not in (0, 1) or e["endpoint_index"] >= len(filed)
                    or e.get("norm") != filed[e["endpoint_index"]].get("norm")):
                raise ValueError("invalid_endpoint_binding")
            if e.get("project_source") != project["source"] or e.get("source_quality_flags") != project.get("quality_flags", []):
                raise ValueError("stale_endpoint_source_evidence")
            for field, maximum in (("lat", 90), ("lon", 180)):
                value = e[field]
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or abs(value) > maximum):
                    raise ValueError("invalid_coordinate")
        center = core.center(eps)
        confidence = max((e["confidence"] for e in eps), key={"high": 0, "medium": 1, "low": 2}.__getitem__)
        if center != binding["center"] or confidence != match["location_confidence"][side]:
            raise ValueError("stale_center_or_confidence")
        prepared.append({"project_key": project["project_key"], "utility": project["utility"], "center": center,
                         "in_service": project["in_service"], "location_confidence": confidence})
        fields = {"name": project["name"], "native_id": project["native_id"], "utility": project["utility"],
                  "owner_code": project.get("owner_code"), "in_service": project["in_service"]}
        if project["utility"] == "DESC":
            fields.update(status=project.get("status"), description=project.get("description"))
        for name, value in fields.items():
            facts.append({"id": f"{side}.{name}", "value": value,
                          "source": {"source_id": sid, "page": project["source"]["page"]}})
        bindings[side] = {"project_id": project["_id"], "source": project["source"], "source_sha256": source["sha256"],
                          "endpoints": [{k: e.get(k) for k in ("_id", "project_id", "source_id", "endpoint_index", "norm",
                                       "lat", "lon", "confidence", "evidence", "osm_id", "osm_url")} for e in eps]}
    computed = core.overlaps(prepared, match["analysis_date"])
    if len(computed) != 1 or any(match.get(k) != value for k, value in computed[0].items()):
        raise ValueError("stale_match_facts")
    for name in ("distance_mi", "time_gap_days", "band", "view", "analysis_date"):
        facts.append({"id": f"match.{name}", "value": match[name]})
    facts.append({"id": "match.distance_display_mi", "value": f"{match['distance_mi']:.2f}"})
    binding = {"version": INPUT_VERSION, "match_id": match["_id"],
               "rule_version": match["rule_version"], "projects": bindings}
    return {"facts": facts, "binding": binding, "input_hash": canonical_hash({"facts": facts, "binding": binding})}


def current_input_hash(match_id: str, ready: dict[str, list[dict]]) -> str | None:
    """F06 BriefHash callback. Raw or joined records, BEFORE dataset prefixes; malformed/stale -> None."""
    try:
        matches = unique(ready.get("matches", []))
        projects = unique(ready.get("projects", []))
        active = [p for p in projects.values() if p.get("active") is True]
        unique(active, "project_key")
        locations = ready.get("locations")
        if locations is None:
            locations = [e for p in projects.values() for e in p.get("endpoints", []) if "confidence" in e]
        return build_match_input(matches[match_id], projects, unique(locations), unique(ready.get("sources", [])))["input_hash"]
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        return None
