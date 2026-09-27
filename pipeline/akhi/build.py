"""F49 Alaska and Hawaii: projects hand-transcribed from public documents, every fact quote-checked (C49).

Neither state publishes a machine-readable project list, so `data/akhi/transcribed.json` names each project and
cites short verbatim quotes. The build fetches every cited document, and refuses to write anything when a quote is
not in that document's text (on the cited page for a PDF). Endpoints are matched by exact name to OSM substations in
the project's state, as the other rollouts do (C33 tiers, C38 operator guard).

From pipeline/:
  uv run python -m akhi.build fetch --cache /tmp/akhi-f49
  uv run python -m akhi.build build --cache /tmp/akhi-f49 [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

import pdfplumber

from california.caiso import match
from common import REPO_ROOT, load_json, write_json
from greatlakes.match import candidate_center
from greatlakes.shared import USER_AGENT, fetch_osm, osm_extract, utc_now, verify_cache

OUT = REPO_ROOT / "data" / "akhi"
TRANSCRIBED = OUT / "transcribed.json"
STATES = {"AK": "02", "HI": "15"}
EVENT_TYPES = {"source_status", "planned_milestone", "certification", "construction_start", "completion", "in_service"}
PRECISION = {"day": r"\d{4}-\d{2}-\d{2}", "month": r"\d{4}-\d{2}", "year": r"\d{4}"}
MAX_BYTES = 64 * 1024 * 1024  # the PUC's FY2025 annual report is past F40's 16 MB cap
GROUPS = {"planned", "under_construction", "proposed", "in_service", "cancelled", "unknown"}


def norm(text: str) -> str:
    """Case, whitespace and quote-mark insensitive, so a quote survives HTML/PDF layout differences."""
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'").replace("ʻ", "'")
    return " ".join(text.replace("“", '"').replace("”", '"').split()).lower()


def html_text(body: bytes) -> str:
    text = body.decode("utf-8", "replace")
    text = re.sub(r"(?s)<!--.*?-->", " ", text)  # commented-out markup is not what the page says
    text = re.sub(r"(?s)<(script|style|noscript)\b.*?</\1>", " ", text)
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


def pdf_pages(body: bytes) -> list[str]:
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def document(path: Path, fmt: str) -> list[str]:
    """Normalized text per page; an HTML page is one page."""
    body = path.read_bytes()
    return [norm(t) for t in (pdf_pages(body) if fmt == "pdf" else [html_text(body)])]


def check_quotes(where: str, cite: dict, docs: dict[str, list[str]]) -> None:
    pages = docs[cite["source"]]
    page = cite.get("page")
    text = pages[page - 1] if page else " ".join(pages)
    for quote in cite["quotes"]:
        if norm(quote) not in text:
            raise ValueError(f"{where}: quote not in {cite['source']}" + (f" p.{page}" if page else "") + f": {quote!r}")


def with_aliases(facilities: list[dict]) -> list[dict]:
    """OSM's own parenthetical abbreviation is a name it states: 'Campbell Estate Industrial Park (CEIP) Substation'."""
    extra = []
    for f in facilities:
        short = re.search(r"\(([A-Z]{2,})\)", f["name"])
        if short:
            extra.append(f | {"name": f"{short.group(1)} Substation", "osm_name": f["name"]})
    return facilities + extra


def locate(project: dict, facilities: list[dict]) -> tuple[dict | None, dict]:
    names, kind = project["endpoints"], project["kind"]
    keys = project["operator_keys"]
    matches = [match(n, facilities, keys, set()) for n in names]
    center = candidate_center(kind, matches) if kind and names else None
    tier = None
    if center:
        found = [m for m in matches if m["status"] == "matched"]
        tier = "candidate" if all(m["corroboration"] != ["unique_in_state"] for m in found) else "candidate_unique_name"
        center["evidence"] = center["evidence"].replace("corroborated by unique_in_state",
                                                        "the only facility with that name in the state (C33 name-only)")
    fields = ("id", "name", "osm_name", "operator", "voltage", "lat", "lon")
    endpoints = [{k: v for k, v in m.items() if k not in ("facility", "facility_ids")}
                 | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
                 for m in matches]
    reason = None if center else ("no_named_endpoint" if not names else "endpoints_not_in_osm")
    return center, {"rule": "C33", "tier": tier, "independent_review": False, "kind": kind if names else None,
                    "reason": reason, "voltages_kv": [], "operator_keys": keys, "endpoints": endpoints,
                    "dataset": f"OpenStreetMap power=substation, {project['state']} (ODbL)"}


def evidence(cite: dict, source: dict, artifact: dict) -> dict:
    page = f"page {cite['page']}" if cite.get("page") else "page text"
    return {"publisher": source["publisher"], "url": source["url"], "artifact_sha256": artifact["sha256"],
            "locator": f"{source['title']}, {page}", "source_date": source["publication_date"],
            "retrieved_at": artifact["retrieved_at"], "access_review": "Public document; no login.",
            "facts": " … ".join(cite["quotes"])}


def check_event(pid: str, event: dict) -> None:
    if event["type"] not in EVENT_TYPES:
        raise ValueError(f"{pid}: event type {event['type']}")
    if event["precision"] == "unknown" and event["date"] is None:
        return  # a stated fact with no stated date ("was energized") stays undated
    pattern = PRECISION.get(event["precision"])
    if pattern is None or not re.fullmatch(pattern, event["date"] or ""):
        raise ValueError(f"{pid}: {event['type']} date {event['date']!r} is not {event['precision']} precision")


def project_record(row: dict, sources: dict, manifest: dict, facilities: list[dict]) -> dict:
    source = sources[row["source"]]
    pid = f"{row['source']}:{row['native_id']}"
    if row["state"] not in STATES or row["status_group"] not in GROUPS:
        raise ValueError(f"{pid}: state or status group")
    center, candidate = locate(row, facilities)
    events = []
    for n, e in enumerate(row["events"], start=1):
        check_event(pid, e)
        cited = sources[e["source"]]
        events.append({"id": f"{pid}:{e['type']}:{n}", "type": e["type"], "date": e["date"],
                       "precision": e["precision"], "native_project_link": row["native_id"],
                       "description": e["description"],
                       "evidence": [evidence(e, cited, manifest[cited["file"]])]})
    # The transcription names which event, if any, states the (planned or actual) in-service date.
    chosen = events[row["in_service_event"] - 1] if row.get("in_service_event") else None
    in_service = ({"raw": chosen["evidence"][0]["facts"], "value": chosen["date"], "precision": chosen["precision"]}
                  if chosen else {"raw": None, "value": None, "precision": "unknown"})
    return {
        "_id": pid, "source_id": row["source"], "native_id": row["native_id"], "name": row["name"],
        "description": row["description"], "owner": row["owner"], "other_owners": [],
        "planning_region": None, "states": [STATES[row["state"]]], "counties": [],
        "geography_basis": "source_state", "status": row["status"], "status_group": row["status_group"],
        "in_service": in_service, "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events,
        "evidence": {"page": row["facts"][0].get("page"), "sheet": None, "row": None,
                     "source_sha256": manifest[source["file"]]["sha256"],
                     "raw": {"cited": [{"source": c["source"], "page": c.get("page"), "quotes": c["quotes"]}
                                       for c in row["facts"]]}},
    }


def fetch_document(cache: Path, name: str, url: str, manifest: dict, attempts: int = 5) -> None:
    for attempt in range(1, attempts + 1):
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=300) as response:  # noqa: S310
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise RuntimeError(f"{url}: exceeds {MAX_BYTES} bytes")
        # AEA's server sometimes ends a PDF early without an error; a cut-off body is never pinned.
        if not name.endswith(".pdf") or b"%%EOF" in body[-2048:]:
            break
        if attempt == attempts:
            raise RuntimeError(f"{url}: truncated PDF ({len(body)} bytes) after {attempts} attempts")
    (cache / name).write_bytes(body)
    manifest[name] = {"url": url, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                      "retrieved_at": utc_now()}


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    for source in load_json(TRANSCRIBED)["sources"]:
        if source["file"] not in manifest:
            fetch_document(cache, source["file"], source["url"], manifest)
            write_json(cache / "manifest.json", manifest)
    for usps in STATES:
        if f"osm-{usps.lower()}.json" not in manifest:
            fetch_osm(cache, usps, manifest)
            write_json(cache / "manifest.json", manifest)


def build(cache: Path) -> dict[Path, object]:
    transcribed = load_json(TRANSCRIBED)
    sources = {s["id"]: s for s in transcribed["sources"]}
    osm_files = [f"osm-{u.lower()}.json" for u in STATES]
    manifest = verify_cache(cache, [s["file"] for s in sources.values()] + osm_files)
    docs = {sid: document(cache / s["file"], s["format"]) for sid, s in sources.items()}
    for s in sources.values():
        if s.get("date_quote"):
            check_quotes(s["id"], {"source": s["id"], "quotes": [s["date_quote"]]}, docs)
    facilities = {u: with_aliases(osm_extract(json.loads((cache / f"osm-{u.lower()}.json").read_bytes()), u))
                  for u in STATES}
    projects, dispositions = [], []
    for row in transcribed["projects"]:
        where = f"{row['source']}:{row['native_id']}"
        for cite in row["facts"] + row["events"]:
            check_quotes(where, cite, docs)
        project = project_record(row, sources, manifest, facilities[row["state"]])
        projects.append(project)
        dispositions.append({"source_id": row["source"], "locator": where, "name": row["name"],
                             "disposition": "accepted", "_id": project["_id"],
                             "location": project["location_candidate"]["tier"] or "unlocated"})
    for row in transcribed.get("excluded", []):
        check_quotes(row["name"], row, docs)
        dispositions.append({"source_id": row["source"], "locator": row["name"], "name": row["name"],
                             "disposition": "excluded", "reason": row["reason"]})
    ids = [p["_id"] for p in projects]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate project ids")
    projects.sort(key=lambda p: p["_id"])
    per_source = Counter(p["source_id"] for p in projects)
    note = "F49 Alaska and Hawaii release (C49). Hand-transcribed, quote-checked facts; pins are unreviewed."
    national_sources = [
        {"_id": s["id"], "publisher": s["publisher"], "title": s["title"], "authority": s["authority"],
         "role": "project_plan", "landing_url": s["url"], "download_url": s["url"],
         "publication_date": s["publication_date"], "vintage": None,
         "retrieved_at": manifest[s["file"]]["retrieved_at"], "sha256": manifest[s["file"]]["sha256"],
         "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
         "planning_region": None, "states": [STATES[u] for u in s["states"]], "project_count": per_source[s["id"]],
         "notes": [note]}
        for s in transcribed["sources"]]
    return {OUT / "projects.json": projects, OUT / "sources.json": national_sources,
            OUT / "dispositions.json": dispositions,
            OUT / "osm-sources.json": {"publisher": "OpenStreetMap contributors", "rights": "ODbL 1.0; attribution "
                                       "required", "role": "candidate facility geometry only (C33)",
                                       "named_substations": {u: len(f) for u, f in facilities.items()},
                                       **{name: manifest[name] for name in osm_files}},
            OUT / "summary.json": summary(projects)}


def summary(projects: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    return {"projects": len(projects), "located": len(located), "verified": 0,
            "by_state": dict(sorted(Counter(p["states"][0] for p in projects).items())),
            "located_by_state": dict(sorted(Counter(p["states"][0] for p in located).items())),
            "by_tier": dict(sorted(Counter(p["location_candidate"]["tier"] for p in located).items())),
            "by_status": dict(sorted(Counter(p["status_group"] for p in projects).items())),
            "with_dated_event": sum(any(e["date"] for e in p["project_events"]) for p in projects),
            "located_with_dated_event": sum(any(e["date"] for e in p["project_events"]) for p in located),
            "located_not_in_service": sum(p["status_group"] not in {"in_service", "cancelled"} for p in located)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch(args.cache)
        return 0
    from .publish import release

    outputs = build(args.cache)
    outputs |= release(outputs)
    if args.check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print(json.dumps(outputs[OUT / "summary.json"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
