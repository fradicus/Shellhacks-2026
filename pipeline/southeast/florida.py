"""Replay pinned DEP index/GIS observations; never approve project coordinates.

uv run python -m southeast.florida --cache /path/to/public/downloads [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from common import REPO_ROOT, load_json, write_json

INDEX_URL = "https://floridadep.gov/water/siting-coordination-office/content/conditions-certification"
MANIFEST = Path("data/southeast/manifests/florida-sources.json")
OUTPUT = Path("data/southeast/batches/florida-tlsa/observations.json")


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {"text": "", "links": []}
        elif self.cell is not None:
            if tag == "a":
                href = dict(attrs).get("href")
                if href:
                    self.cell["links"].append(urljoin(INDEX_URL, href))
            elif tag == "br":
                self.cell["text"] += " "

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.cell["text"] = " ".join(self.cell["text"].split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def parse_index(html: str) -> list[dict]:
    parser = Tables()
    parser.feed(html)
    rows = []
    for row in parser.rows:
        if len(row) != 3 or not re.search(r"\bTA\d{2}-\d{2}\b", row[1]["text"]):
            continue
        ids = set(re.findall(r"\bTA\d{2}-\d{2}\b", row[1]["text"]))
        if len(ids) != 1 or not row[0]["text"] or not row[2]["text"]:
            raise ValueError("ambiguous transmission index row")
        rows.append({"certification_raw": ids.pop(), "name": row[0]["text"],
                     "licensee_raw": row[2]["text"], "project_urls": row[0]["links"],
                     "document_urls": row[1]["links"]})
    if not rows or len({r["certification_raw"] for r in rows}) != len(rows):
        raise ValueError("missing or duplicate certification index records")
    return rows


def reconcile(index: list[dict], gis: dict, ids: dict) -> dict:
    if gis.get("error") or ids.get("error") or gis.get("exceededTransferLimit"):
        raise ValueError("failed or truncated GIS response")
    features = gis["features"]
    object_ids = [f["attributes"]["OBJECTID"] for f in features]
    expected = ids["objectIds"]
    if (not expected or len(set(expected)) != len(expected) or len(set(object_ids)) != len(object_ids)
            or set(object_ids) != set(expected) or ids.get("objectIdFieldName") != "OBJECTID"):
        raise ValueError("GIS ID reconciliation failed")
    observations = []
    for row in index:
        observations.append({"observation_id": "dep-index:" + row["certification_raw"],
                             "source_id": "dep-conditions-index", "locator": row["certification_raw"],
                             "facts": row, "center": None, "location_review": "unlocated",
                             "disposition": "pending_project_reconciliation"})
    for feature in sorted(features, key=lambda f: f["attributes"]["OBJECTID"]):
        attrs = feature["attributes"]
        observations.append({"observation_id": f"dep-gis:{attrs['OBJECTID']}",
                             "source_id": "dep-transmission-gis", "locator": f"OBJECTID={attrs['OBJECTID']}",
                             "facts": attrs, "center": None, "location_review": "unlocated",
                             "disposition": "pending_project_reconciliation"})
    index_ids = {r["certification_raw"] for r in index}
    gis_ids = {f["attributes"]["CERTIFICATION"] for f in features}
    return {"publication_eligible": False, "index_rows": len(index), "gis_rows": len(features),
            "gis_unique_certification_ids": len(gis_ids), "gis_acquisition_reconciled": True,
            "index_ids_missing_from_gis": sorted(index_ids - gis_ids),
            "gis_ids_missing_from_index": sorted(gis_ids - index_ids),
            "observations": observations, "new_confirmed_points": 0,
            "limitations": ["Observations are not canonical projects or verified current construction.",
                            "Certification ID discrepancies require explicit source reconciliation.",
                            "Linked documents are references, not automatic acquisition approval.",
                            "This source does not cover every Florida transmission construction project."]}


def build(cache: Path, manifest: dict) -> dict:
    payloads = {}
    for source in manifest["artifacts"]:
        raw = (cache / source["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"source hash changed: {source['file']}")
        payloads[source["key"]] = raw
    index = parse_index(payloads["index"].decode())
    if len(index) != manifest["expected_index_rows"]:
        raise ValueError("index row count changed")
    result = reconcile(index, json.loads(payloads["gis"]), json.loads(payloads["ids"]))
    for source in manifest["artifacts"]:
        if not source["key"].startswith("detail:"):
            continue
        parser = Tables()
        parser.feed(payloads[source["key"]].decode())
        fields = {}
        wanted = {"Licensee", "Certification #", "Date Certified", "Description", "Line Length", "Voltage",
                  "Counties Crossed", "Counties Crossed:"}
        for row in parser.rows:
            if len(row) == 2 and row[0]["text"] in wanted:
                key = row[0]["text"].rstrip(":")
                if key in fields:
                    raise ValueError("duplicate project detail field")
                fields[key] = row[1]["text"]
        if not {"Licensee", "Certification #", "Description"} <= fields.keys():
            raise ValueError("project detail fields missing")
        result["observations"].append({"observation_id": source["key"], "source_id": source["key"],
                                       "locator": "General Information table", "facts": fields,
                                       "center": None, "location_review": "unlocated",
                                       "disposition": "pending_project_reconciliation"})
    result["sources"] = manifest["artifacts"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build(args.cache, load_json(REPO_ROOT / MANIFEST))
    if args.check:
        if result != load_json(REPO_ROOT / OUTPUT):
            raise ValueError("committed observations differ from pinned source replay")
    else:
        write_json(REPO_ROOT / OUTPUT, result)
    print(f"{result['index_rows']} index rows; {result['gis_rows']} GIS observations; 0 approved points")


if __name__ == "__main__":
    main()
