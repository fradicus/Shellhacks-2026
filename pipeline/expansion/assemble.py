"""Build proposed records from the bounded NOAA and Vermont evidence reviews.

Reviewers must bind the resulting record hashes before active.json is written.
Sources and reviewed inputs are supplied explicitly; this command never fetches URLs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import REPO_ROOT, load_json, write_json
from expansion.new_england import facts_hash

ISO_ID = "iso-ne-rsp-2026-06"
BATCH = Path("data/expansion/batches/new-england-locations")


def evidence(manifest: dict, publisher: str, locator: str, facts: str, date: str | None, rights: str) -> dict:
    return {
        "publisher": publisher, "url": manifest["url"], "artifact_sha256": manifest["sha256"],
        "locator": locator, "source_date": date,
        "retrieved_at": manifest.get("retrieved_utc") or manifest.get("retrieved") or manifest.get("retrieved_at"),
        "access_review": rights, "facts": facts,
    }


def project_evidence(project: dict, source: dict) -> dict:
    return evidence(source, "ISO New England", f"RSP_sortable row {project['evidence']['row']}",
                    f"Project {project['native_id']}: {project['name']}; reported owner: {project['owner']}; "
                    f"source state: {project['evidence']['raw']['State']}. Source status unchanged.",
                    "2026-06", "Pinned F30 public workbook; ISO-NE Public marking independently inspected.")


def noaa_records(review: dict, manifest: dict, projects: dict, iso: dict) -> list[dict]:
    records = []
    for row in review["reviews"]:
        if row["decision"] != "confirmed_planning_site":
            continue
        project = projects[row["project_id"]]
        if row["project_facts_sha256"] != facts_hash(project):
            raise ValueError("NOAA review does not match current project facts")
        kind = "site" if row["coverage"] == "site" else "line"
        points = []
        for index, site in enumerate(row["accepted_facilities"]):
            geometry = site["geometry_3857"]
            points.append({
                "role": "site" if kind == "site" else ["a", "b"][index],
                "facility_id": f"noaa-ne-2013:{site['facility_id']}", "facility_name": site["name"],
                "lat": site["coordinate_wgs84"]["lat"], "lon": site["coordinate_wgs84"]["lon"],
                "original_geometry": {"crs": "EPSG:3857", "type": "Point",
                                      "coordinates": [geometry["x"], geometry["y"]],
                                      "transform": "Inverse spherical Web Mercator, R=6378137m; independently recomputed."},
                "precision": "Planning-scale point digitized at 1:40000; source vintage 2013-06-05.",
                "uncertainty_m": None,
                "geometry_evidence": [evidence(
                    manifest["czm-ne-features.json"], "NOAA Coastal Services Center / Massachusetts CZM",
                    f"FeatureServer layer 2 OBJECTID={site['facility_id']}",
                    f"{site['name']}, {site['state']}; {site['source_description']}; source status: {site['source_status']}. "
                    "A facility reference point, not an equipment position or a survey.", "2013-06-05",
                    "Public government-hosted planning data; as-is/no-warranty terms; attribution retained.")],
                "identity_evidence": [project_evidence(project, iso), evidence(
                    manifest["czm-ne-metadata.xml"], "NOAA Coastal Services Center / Massachusetts CZM",
                    "Lineage and attribute accuracy", "ISO-NE 2012 non-CEII map guided named transmission facility "
                    "identification; publisher digitized imagery/OSM at 1:40000 and cross-checked attributes. "
                    "No current owner or voltage field in this GIS; project owner remains the RSP observation.",
                    "2013-06-05", "Public metadata; planning-use limitation retained.")],
                "identity_rationale": row["reason"],
            })
        records.append({"project_id": project["_id"], "project_facts_sha256": facts_hash(project),
                        "producer": "f38_grid_research", "location_kind": kind, "points": points,
                        "reviews": [], "events": []})
    return records


def vermont_records(review: dict, proposals: list, manifest: dict, projects: dict, iso: dict) -> list[dict]:
    proposals = {p["project_id"]: p for p in proposals}
    records = []
    # The first publication includes the two fully documented standalone sites.
    # Tafts endpoint proposals require additional filings and remain in the review ledger.
    for row in review["records"]:
        if row["decision"] != "confirmed" or row["project_id"] not in {"iso-ne:1616", "iso-ne:1617"}:
            continue
        proposal = proposals[row["project_id"]]
        if row["candidate_sha256"] != facts_hash(proposal):
            raise ValueError("Vermont proposal changed after independent review")
        project = projects[row["project_id"]]
        site = proposal["candidate_site"]
        props = site["attributes"]
        point = {
            "role": "site", "facility_id": f"vt-psd-esite:{props['ESITEID']}", "facility_name": props["Sub_NAME"],
            "lat": site["geometry"]["y"], "lon": site["geometry"]["x"],
            "original_geometry": {"crs": "EPSG:32145", "type": "Point",
                                  "coordinates": [proposal["native_geometry"]["x"], proposal["native_geometry"]["y"]],
                                  "transform": "ArcGIS output independently reproduced with inverse Vermont SPCS83 "
                                  "to NAD83 and inverse ESRI:108190 WGS_1984_(ITRF00)_To_NAD_1983; error <5.6e-10 degrees."},
            "precision": None, "uncertainty_m": None,
            "geometry_evidence": [evidence(
                manifest[name], "Vermont Public Service Department / VCGI", proposal["geometry_locator"],
                f"Utility-submitted/E911 {props['Sub_NAME']} substation site at {props['PRIMARYADDRESS']}, "
                f"{props['TOWNNAME']}; source Utility={props['Utility']}. Not individual equipment geometry.",
                None, "Vermont Open Geodata Policy permits sharing/integration; attribution and unknown accuracy retained.")
                for name in ("vermont-open-native.json", "vermont-open-wgs84.json")],
            "identity_evidence": [project_evidence(project, iso)], "identity_rationale": row["reason"],
        }
        for item in proposal["project_link_evidence"]:
            point["identity_evidence"].append(evidence(
                manifest[item["file"]], ("Vermont Electric Power Company (VELCO)" if item["file"] == "velco-crvp.pdf"
                                         else "TRC Environmental Corporation for VELCO; hosted by Vermont DEC"),
                f"PDF page {item['page']}: {item['locator']}",
                ("2017 plan identifies the 115 kV Chelsea rebuild to a three-breaker ring; VELCO/GMP identified."
                 if item["file"] == "velco-crvp.pdf" and project["_id"] == "iso-ne:1617"
                 else item["facts"].replace("at45", "at 45")
                 .replace("approximately6.3m", "approximately 6.2 m (datum unknown)")),
                "2017-03-16" if item["file"] == "velco-crvp.pdf" else "2018-03",
                "Public utility/regulator project evidence; bounded factual extraction only, no full PDF redistribution."))
        records.append({"project_id": project["_id"], "project_facts_sha256": facts_hash(project),
                        "producer": "f38_other_research", "location_kind": "site", "points": [point],
                        "reviews": [], "events": []})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--noaa-review", type=Path, required=True)
    parser.add_argument("--noaa-manifest", type=Path, required=True)
    parser.add_argument("--vt-review", type=Path, required=True)
    parser.add_argument("--vt-manifest", type=Path, required=True)
    parser.add_argument("--vt-proposals", type=Path, required=True)
    args = parser.parse_args()
    projects = {p["_id"]: p for p in load_json(REPO_ROOT / "data/national/projects.json")}
    iso = next(x for x in load_json(REPO_ROOT / "data/national/source-manifest.json") if x["id"] == ISO_ID)
    noaa = {Path(x["file"]).name: x for x in load_json(args.noaa_manifest)}
    vt = {Path(x["file"]).name: x for x in load_json(args.vt_manifest)}
    records = noaa_records(load_json(args.noaa_review), noaa, projects, iso)
    vt_records = vermont_records(load_json(args.vt_review), load_json(args.vt_proposals), vt, projects, iso)
    preferred_ids = {p["project_id"] for p in vt_records}
    records = [p for p in records if p["project_id"] not in preferred_ids] + vt_records
    records.sort(key=lambda p: p["project_id"])
    write_json(REPO_ROOT / BATCH / "proposed-records.json", records)
    print(f"Prepared {len(records)} proposed publication records; final review hashes still required.")


if __name__ == "__main__":
    main()
