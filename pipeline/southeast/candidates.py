"""Normalize the pinned Florida observations for independent review, without activation."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from common import REPO_ROOT, load_json, write_json

OBSERVATIONS = Path("data/southeast/batches/florida-tlsa/observations.json")
OUTPUT = Path("data/southeast/batches/florida-tlsa/project-candidates.json")
SOURCE_ID = "southeast:fl-dep:conditions-index"
# The linked individual project page resolves this index transcription discrepancy.
ALIASES = {"TA07-14": "TA06-14"}


def build(batch: dict) -> dict:
    artifacts = {source["key"]: source for source in batch["sources"]}
    details = {row["source_id"]: row for row in batch["observations"]
               if row["source_id"].startswith("detail:")}
    projects, events, dispositions = [], [], []
    used_details = set()
    for row in batch["observations"]:
        if row["source_id"] != "dep-conditions-index":
            continue
        facts = row["facts"]
        raw_id = facts["certification_raw"]
        native_id = ALIASES.get(raw_id, raw_id)
        project_id = "southeast:fl-dep:" + native_id.lower()
        linked_details = [key for key in details if any(
            url.rstrip("/").endswith("/" + key.removeprefix("detail:"))
            for url in facts["project_urls"])]
        if len(linked_details) > 1:
            raise ValueError("ambiguous linked project detail")
        detail = details[linked_details[0]] if linked_details else None
        if raw_id in ALIASES and detail is None:
            raise ValueError("index alias requires linked individual project evidence")
        if detail and detail["facts"]["Certification #"].replace(" ", "") != native_id:
            raise ValueError("linked project certification conflicts with canonical identity")
        evidence = {"index": row, "index_artifact": artifacts["index"],
                    "normalization": "Licensee retained as licensee; equipment owner and current status unknown."}
        if detail:
            used_details.add(detail["source_id"])
            evidence["detail"] = detail
            evidence["detail_artifact"] = artifacts[detail["source_id"]]
        if raw_id != native_id:
            evidence["identity_resolution"] = (
                "Index TA07-14 links to the Bobwhite-Manatee individual page whose certification is TA06-14. "
                "Retain both observations; use the individual page certification as the proposed native ID.")
        projects.append({
            "_id": project_id, "source_id": SOURCE_ID, "native_id": native_id,
            "name": facts["name"], "owner": None, "other_owners": [], "planning_region": None,
            "states": ["12"], "counties": [],
            "geography_basis": "Florida DEP transmission certification index; cross-border extent not fully assessed.",
            "status": None, "status_group": "unknown",
            "in_service": {"raw": None, "value": None, "precision": "unknown"},
            "center": None, "location_review": "unlocated",
            "description": detail["facts"]["Description"] if detail else None,
            "evidence": {"page": None, "sheet": None, "row": len(projects) + 1, "raw": evidence},
        })
        dispositions.append({"source_id": SOURCE_ID, "locator": raw_id, "project_id": project_id,
                             "disposition": "accepted",
                             "reason": "Proposed identity from transmission certification index; pending independent review."})
        if detail and detail["facts"].get("Date Certified"):
            source = artifacts[detail["source_id"]]
            date = datetime.strptime(detail["facts"]["Date Certified"], "%m/%d/%Y").date().isoformat()
            events.append({"project_id": project_id, "events": [{
                "id": project_id + ":certification:" + date, "type": "certification", "date": date,
                "precision": "day", "native_project_link": native_id,
                "description": "DEP Date Certified; does not establish construction or in-service date.",
                "evidence": [{"publisher": source["publisher"], "url": source["url"],
                              "artifact_sha256": source["sha256"], "locator": "General Information / Date Certified",
                              "source_date": source["publication_date"], "retrieved_at": source["retrieved_at"],
                              "access_review": source["access_review"],
                              "facts": "Certification # " + native_id + "; Date Certified " + detail["facts"]["Date Certified"]}],
            }]})
    if used_details != set(details):
        raise ValueError("unreconciled individual project detail")
    if len({project["_id"] for project in projects}) != len(projects):
        raise ValueError("canonical project identity collision")
    return {"publication_eligible": False, "projects": projects, "project_events": events,
            "proposed_dispositions": dispositions, "new_confirmed_points": 0,
            "limitations": ["Independent identity review and release assembly remain required.",
                            "Current index scope only; historical relinquished entries and other providers remain pending.",
                            "GIS observations remain in the source batch; they do not establish project endpoints.",
                            "Florida membership does not exclude unassessed cross-border states."]}


if __name__ == "__main__":
    result = build(load_json(REPO_ROOT / OBSERVATIONS))
    write_json(REPO_ROOT / OUTPUT, result)
    print(f"{len(result['projects'])} proposed projects; {len(result['project_events'])} certification events; not publishable")
