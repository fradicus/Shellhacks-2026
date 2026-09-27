"""New York: NYISO 2026 Gold Book Table VII (Proposed Transmission Facilities) -> national-project records.

NYISO serves its documents behind a browser challenge, so the user downloaded the public PDF; this adapter takes that
local file, checks its pinned hash and records the publisher URL. From pipeline/:
  uv run python -m greatlakes.nyiso build --source ~/Downloads/2026-Gold-Book-Public.pdf [--check]
Each table row is one component (a line segment or station job) of a queue-numbered project; the From/To terminal
columns are the facility names used for C26 candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import pdfplumber

from common import validate

from . import osm as osm_data
from .match import NOT_AN_ENDPOINT, voltages_kv
from .shared import locate_named, write_outputs

SOURCE_ID = "nyiso-gold-book-2026"
URL = "https://www.nyiso.com/documents/20142/2226333/2026-Gold-Book-Public.pdf/a8fd42fe-5a8c-88cb-5052-f93dfd6423b8"
SHA256 = "43865c1cbe38ca2ef4c8319d11454881de2b9dde3e48867dbbd2e94855b908bf"
RETRIEVED = "2026-09-27T02:53:05Z"  # the user's browser download (file mtime); NYISO challenges scripts
TITLE = "Table VII: Proposed Transmission Facilities"
DATASET = "OpenStreetMap (ODbL), data/greatlakes/osm/ny-substations.json"
# Column left edges (PDF points) measured from the table header; each word belongs to the last edge at or before it.
COLUMNS = [("queue", 0), ("owner", 80), ("from", 122), ("to", 200), ("length", 282), ("prior", 322), ("year", 345),
           ("kv_operating", 362), ("kv_design", 390), ("circuits", 418), ("summer", 432), ("winter", 458),
           ("description", 480), ("class_type", 715)]
SECTIONS = {"Class Year Transmission Projects": "planned", "TIP Projects": "planned", "Firm Plans": "planned",
            "Non-Firm Plans": "proposed"}
OPERATOR_KEYS = {
    "NGRID": ["NATIONAL GRID", "NIAGARA MOHAWK"], "NYSEG": ["NYSEG", "NEW YORK STATE ELECTRIC"],
    "LIPA": ["LIPA", "LONG ISLAND", "PSEG"], "NYPA": ["NYPA", "NEW YORK POWER AUTHORITY"],
    "CONED": ["CON EDISON", "CONSOLIDATED EDISON", "CONED"], "TRANSCO": ["TRANSCO"], "CHGE": ["CENTRAL HUDSON"],
    "RGE": ["ROCHESTER GAS"], "O&R": ["ORANGE AND ROCKLAND", "ORANGE & ROCKLAND"], "LSP": ["LS POWER"],
}


def column(x0: float) -> str:
    return [name for name, edge in COLUMNS if x0 >= edge][-1]


def parse(path: Path) -> list[dict]:
    """Anchor rows carry a season/In-Service mark and a year; wrapped description lines join the nearest anchor."""
    rows: list[dict] = []
    section = None
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if TITLE not in text or "Project Queue" not in text:
                continue
            lines: dict[int, list[dict]] = {}
            for word in page.extract_words():
                if 115 < word["top"] < 570:
                    lines.setdefault(round(word["top"]), []).append(word)
            anchors, loose = [], []
            for top in sorted(lines):
                words = sorted(lines[top], key=lambda w: w["x0"])
                cells: dict[str, list[str]] = {}
                for word in words:
                    cells.setdefault(column(word["x0"]), []).append(word["text"])
                joined = {k: " ".join(v) for k, v in cells.items()}
                heading = " ".join(w["text"] for w in words)
                if found := next((s for s in SECTIONS if heading.startswith(s)), None):
                    section = found
                elif re.fullmatch(r"20\d\d", joined.get("year", "")) and joined.get("prior") in {"S", "W", "In-Service"}:
                    anchors.append({"page": page_number, "top": top, "section": section, "cells": joined})
                elif "description" in joined:
                    loose.append((top, joined["description"]))
            for top, text_part in loose:
                if anchors:
                    nearest = min(anchors, key=lambda a: abs(a["top"] - top))
                    if abs(nearest["top"] - top) <= 12:
                        nearest.setdefault("wrapped", []).append((top, text_part))
            for anchor in anchors:
                parts = sorted([*anchor.pop("wrapped", []), (anchor["top"], anchor["cells"].get("description", ""))])
                anchor["cells"]["description"] = " ".join(p for _, p in parts if p).strip() or None
                rows.append(anchor)
    return rows


def terminal(name: str | None, in_service: bool) -> str | None:
    """A terminal usable as a facility name: not a state line or tap, and not a not-yet-built new station."""
    if not name or name.upper() == "TBD" or "state line" in name.lower() or NOT_AN_ENDPOINT.search(name):
        return None
    if re.search(r"\(New\b", name) and not in_service:
        return None
    return re.sub(r"\([^)]*\)", " ", name).strip() or None


def operator_keys(owner: str) -> list[str]:
    return [k for part in re.split(r"[/,]", owner.upper().replace(" ", "")) for k in OPERATOR_KEYS.get(part, [])]


def build(source: Path) -> dict:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"{source}: sha256 {digest} does not match the reviewed Gold Book")
    facilities = osm_data.load(["NY"])
    projects, dispositions = [], []
    counters: dict[str, int] = {}
    for row in parse(source):
        c = row["cells"]
        # "[631],15,21" / "1125, 3": queue position then note numbers; a lone short number is only a note (1-25).
        queue = re.match(r"\[(\d+)\]|(\d{3,})\b", c.get("queue", ""))
        queue_id = queue and (queue[1] or queue[2])
        key = queue_id or re.sub(r"\W+", "", c.get("owner", "none")).lower()
        counters[key] = counters.get(key, 0) + 1
        native = f"{key}-{counters[key]}"
        locator = f"2026-Gold-Book-Public.pdf#page-{row['page']}-y{row['top']}"
        done = c["prior"] == "In-Service"
        group = "in_service" if done else SECTIONS.get(row["section"] or "", "unknown")
        # Same, blank or same-named ("Willis (Existing)" / "Willis (New)") To terminal: work at one station.
        bare = [re.sub(r"\([^)]*\)", "", c.get(k) or "").strip() for k in ("from", "to")]
        single = c.get("to") in {None, "-"} or bare[0] == bare[1]
        name = c.get("from", "?") if single else f"{c.get('from', '?')} – {c.get('to', '?')}"
        ends = [terminal(c.get("from"), done), terminal(c.get("to"), done)]
        kind = "site" if single else "line"
        names = ends[:1] if kind == "site" else ends
        named = {"kind": kind if any(names) else None, "names": [n for n in names] if any(names) else [],
                 "from": "terminal columns", "reason": None if any(names) else "terminals_not_facilities"}
        kv = voltages_kv(f"{c.get('kv_operating', '')} kV", f"{c.get('kv_design', '')} kV")
        center, candidate = locate_named(named, facilities, operator_keys(c.get("owner", "")), kv, DATASET)
        owners = [o.strip() for o in c.get("owner", "").split("/") if o.strip()]
        project = {
            "_id": f"{SOURCE_ID}:{native}", "source_id": SOURCE_ID, "native_id": native, "name": name,
            "description": c.get("description"), "owner": owners[0] if len(owners) == 1 else None,
            "other_owners": owners if len(owners) > 1 else [], "planning_region": "nyiso", "states": ["36"],
            "counties": [], "geography_basis": "source_state",
            "status": f"{row['section']}; {c['prior']} {c['year']}", "status_group": group,
            "in_service": {"raw": f"{c['prior']} {c['year']}", "value": c["year"], "precision": "year"},
            "center": center, "location_review": "unreviewed" if center else "unlocated",
            "location_candidate": candidate, "parent_project": f"queue {queue_id}" if queue_id else None,
            "evidence": {"page": row["page"], "sheet": TITLE, "row": None,
                         "raw": c | {"section": row["section"], "source_url": URL, "source_sha256": SHA256}},
        }
        validate(project, "national-project")
        projects.append(project)
        dispositions.append({"native_id": native, "locator": locator, "disposition": "accepted",
                             "reason": "row of Table VII with a season/in-service mark and year"})
    projects.sort(key=lambda p: p["_id"])
    sources = [{"_id": SOURCE_ID, "publisher": "New York Independent System Operator (NYISO)",
                "title": "2026 Load & Capacity Data Report (Gold Book), Table VII", "vintage": "as of 2026-03-15",
                "rights": "Public report; retrieved by the user in a browser because NYISO challenges scripts",
                "artifacts": [{"url": URL, "sha256": SHA256, "retrieved_at": RETRIEVED, "bytes": source.stat().st_size}]}]
    return {"projects": projects, "dispositions": dispositions, "sources": sources}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build"])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return write_outputs("ny", build(args.source.expanduser()), args.check)


if __name__ == "__main__":
    sys.exit(main())
