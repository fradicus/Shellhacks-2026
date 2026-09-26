"""Deterministic search texts for matches, projects and briefs. Pure functions; no I/O.

The embedded text is stored verbatim on every embedding record (`text` + `text_hash`), so any
vector can be traced back to exactly the facts that produced it. Unknowns stay visible as
"unknown" — never filled in (specs/mission.md).
"""

from __future__ import annotations


def _endpoints(project: dict) -> str:
    names = [e["name"] for e in project.get("endpoints", []) if e.get("name")]
    return ", ".join(names) if names else "unknown endpoints"


def _voltages(project: dict) -> str:
    values = project.get("voltages_kv") or []
    return ", ".join(str(v) for v in values) + " kV" if values else "unknown voltage"


def _in_service(project: dict) -> str:
    date = (project.get("in_service") or {}).get("date")
    return date if date else "unknown in-service date"


def project_text(project: dict) -> str:
    """One active filing version of one project."""
    description = (project.get("description") or "").strip()
    text = (
        f"{project['project_key']} ({project['utility']}): {project.get('name') or 'unnamed project'}. "
        f"Endpoints: {_endpoints(project)}. Voltage: {_voltages(project)}. "
        f"In service: {_in_service(project)}."
    )
    return f"{text} {description}".strip()


def match_text(match: dict, projects_by_key: dict[str, dict]) -> str:
    """One coordination pair, with the filed names of both sides for semantic context."""
    a = projects_by_key.get(match["a"], {})
    b = projects_by_key.get(match["b"], {})
    gap = match.get("time_gap_days")
    gap_text = f"in-service dates {gap} days apart" if gap is not None else "in-service gap unknown"
    return (
        f"Coordination pair {match['a']} ({a.get('utility', 'unknown utility')}) and "
        f"{match['b']} ({b.get('utility', 'unknown utility')}). "
        f"{match['distance_mi']:.2f} miles apart, priority band {match['band']}; {gap_text}. "
        f"A: {a.get('project_key', match['a'])} — {a.get('name') or 'unnamed project'}; {_endpoints(a)}; "
        f"{_voltages(a)}; {_in_service(a)}. "
        f"B: {b.get('project_key', match['b'])} — {b.get('name') or 'unnamed project'}; {_endpoints(b)}; "
        f"{_voltages(b)}; {_in_service(b)}."
    )


def brief_text(brief: dict) -> str:
    """A passed coordination brief: its grounded facts, activities and open questions."""
    sections = [
        *(f["text"] for f in brief.get("supported_facts", []) if f.get("text")),
        *(a["text"] for a in brief.get("possible_shared_activities", []) if a.get("text")),
        *(q for q in brief.get("questions", []) if q),
    ]
    return f"Coordination brief for pair {brief['match_id']}. " + " ".join(sections)
