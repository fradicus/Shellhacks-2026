"""Rebuild the Florida DEP candidate from pinned public bytes and separate reviews.

Writes only the candidate path. Activation is a separate integrator action after review.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import datetime
from html import unescape
from pathlib import Path

from common import REPO_ROOT, load_json, validate, write_json
from expansion.new_england import facts_hash
from southeast.florida import Tables, parse_index
from southeast.florida_crs import TRANSFORM
from southeast.publish import check_location, release_hash

MANIFEST = Path("data/southeast/manifests/florida-release-sources.json")
CANDIDATE = Path("data/southeast/batches/florida-tlsa/release-candidate.json")
REVIEWS = Path("data/southeast/reviews")
SOURCE = "southeast:fl-dep:conditions-index"
PRODUCER = "codex-local-f39-producer"


def detail_fields(html: str) -> dict:
    parser = Tables()
    parser.feed(html)
    fields = {}
    wanted = {"Licensee", "Certification #", "Date Certified", "Description", "Line Length", "Voltage", "Counties Crossed"}
    for row in parser.rows:
        if len(row) == 2 and row[0]["text"].rstrip(":") in wanted:
            key = row[0]["text"].rstrip(":")
            if key in fields:
                raise ValueError("duplicate detail field")
            fields[key] = row[1]["text"]
    if not wanted <= fields.keys():
        raise ValueError("incomplete General Information table")
    return fields


def deland_fields(html: str) -> dict:
    match = re.search(r'<div property="schema:text"[^>]*>.*?<p>(.*?)</p>', html, re.S)
    if not match:
        raise ValueError("DeLand narrative layout changed")
    text = " ".join(unescape(re.sub(r"<[^>]+>", " ", match[1])).split())
    required = ["TA25-20", "26.26", "DeLand West Substation in Volusia County", "Dona Vista Substation in Lake County"]
    if not all(value in text for value in required):
        raise ValueError("DeLand narrative facts changed")
    return {
        "Certification #": "TA25-20",
        "Licensee": None,
        "Description": text,
        "Counties Crossed": "Volusia and Lake",
        "Line Length": "approximately 26.26 miles",
        "Voltage": "230 kV",
        "Date Certified": None,
    }


def evidence(artifact: dict, locator: str, facts: str) -> dict:
    return {
        "publisher": artifact["publisher"],
        "url": artifact["url"],
        "artifact_sha256": artifact["sha256"],
        "locator": locator,
        "source_date": artifact["publication_date"],
        "retrieved_at": artifact["retrieved_at"],
        "access_review": artifact["access_review"],
        "facts": facts,
    }


def build(cache: Path, root: Path = REPO_ROOT) -> dict:
    manifest = load_json(root / MANIFEST)
    artifacts, payloads = {}, {}
    for artifact in manifest["artifacts"]:
        key = artifact["key"]
        if key in artifacts:
            raise ValueError("duplicate source artifact")
        raw = (cache / artifact["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
            raise ValueError(f"source bytes changed: {key}")
        artifacts[key], payloads[key] = artifact, raw
    index = parse_index(payloads["index"].decode())
    if len(index) != manifest["expected_index_rows"]:
        raise ValueError("index enumeration changed")
    geography_path = root / "data/national/geography.json"
    geography = load_json(geography_path)
    counties = {c["name"]: c["county_geoid"] for c in geography["counties"] if c["state_fips"] == "12"}
    county_reference = {"path": "data/national/geography.json", "sha256": hashlib.sha256(geography_path.read_bytes()).hexdigest()}
    projects, histories, dispositions = [], [], []
    for number, row in enumerate(index, 1):
        native = row["certification_raw"]
        pid = "southeast:fl-dep:" + native.lower()
        slug = row["project_urls"][0].rstrip("/").rsplit("/", 1)[-1]
        is_deland = native == "TA25-20"
        key = ("narrative:" if is_deland else "detail:") + slug
        fields = deland_fields(payloads[key].decode()) if is_deland else detail_fields(payloads[key].decode())
        detail_id = fields["Certification #"].replace(" ", "")
        if detail_id != ("TA06-14" if native == "TA07-14" else native):
            raise ValueError("project detail identity changed")
        county_names = re.split(r",\s*|\s+and\s+", fields["Counties Crossed"])
        if any(name not in counties for name in county_names):
            raise ValueError("unmapped county name")
        source_evidence = [
            evidence(artifacts["index"], native, "Transmission certification index row: name, native ID and licensee."),
            evidence(
                artifacts[key],
                "Opening project paragraph" if is_deland else "General Information table",
                "Project description, reported counties and certification observations; current service status not established.",
            ),
        ]
        raw = {
            "index": row,
            "detail": fields,
            "source_evidence": source_evidence,
            "county_reference": county_reference,
            "normalization": "Counties are the detail page's reported counties, not an exhaustive independently mapped route. "
            "Licensee is not silently treated as equipment owner. Current status and service date remain unknown.",
        }
        description = fields["Description"]
        if native == "TA07-14":
            raw["identity_aliases"] = ["TA07-14", "TA06-14"]
            raw["identity_resolution"] = (
                "Primary Conditions of Certification identifies TA07-14; retain TA06-14 as "
                "conflicting detail/GIS/register observation."
            )
            source_evidence.append(
                evidence(
                    artifacts["bobwhite-decision"],
                    "PDF pages 1 and 4 (printed page 1 footer)",
                    "Bobwhite-Manatee; TA07-14; certification dated 2008-11-06. Conflicting TA06-14 remains an alias.",
                )
            )
        if native == "TA81-03":
            description = (
                "Duval-to-Poinsett transmission corridor; primary certification Figure 1 names Duval and Poinsett endpoints."
            )
            raw["description_resolution"] = (
                "Detail's Kathleen endpoint statement conflicts with the primary corridor map and is not used for location."
            )
            source_evidence.append(
                evidence(
                    artifacts["duval-decision"],
                    "PDF page 33, Composite Attachment I, Figure 1",
                    "Duval and Poinsett are named endpoints; Rice and approximate Rima are intermediate. "
                    "No coordinates inferred.",
                )
            )
        if native == "TA81-01":
            raw["limitations"] = [
                "Hopkins detail Voltage is 2,200 MW, a unit error; no voltage normalized from that cell.",
                "Florida certification membership is supported; full interstate extent and Georgia membership remain unverified.",
            ]
        if native == "TA22-19":
            raw["voltage_note"] = "Raw Voltage cell lacks units; page title says 230kV. No unit inferred from the number alone."
        if native == "TA83-04":
            raw["topology_note"] = "Detail and GIS differ on branch topology; no route geometry or endpoint pairing inferred."
        if is_deland:
            source_evidence.append(
                evidence(
                    artifacts["deland-decision"],
                    "PDF page 1 cover and page 6 (printed 1), Section A.I",
                    "Conditions dated 2026-01-20; DEF identified as owner/operator and licensee as of "
                    "this document. No construction completion established.",
                )
            )
            raw["owner_observation"] = {
                "owner": "Duke Energy Florida",
                "as_of_document_date": "2026-01-20",
                "role": "owner/operator and licensee",
                "current_ownership_independently_confirmed": False,
            }
        project = {
            "_id": pid,
            "source_id": SOURCE,
            "native_id": native,
            "name": row["name"],
            "description": description,
            "owner": "Duke Energy Florida" if is_deland else None,
            "other_owners": [],
            "planning_region": None,
            "states": ["12"],
            "counties": sorted(counties[name] for name in county_names),
            "geography_basis": "Florida DEP certification scope and detail-reported counties; county list may be incomplete. "
            "Cross-border extent is not fully assessed; membership does not mean the whole line is in Florida.",
            "status": None,
            "status_group": "unknown",
            "in_service": {"raw": None, "value": None, "precision": "unknown"},
            "center": None,
            "location_review": "unlocated",
            "evidence": {"page": None, "sheet": None, "row": number, "source_sha256": artifacts["index"]["sha256"], "raw": raw},
        }
        validate(project, "national-project")
        projects.append(project)
        date = "2026-01-20" if is_deland else datetime.strptime(fields["Date Certified"], "%m/%d/%Y").date().isoformat()
        event_evidence = (
            [source_evidence[-1]]
            if is_deland
            else [
                evidence(
                    artifacts[key],
                    "General Information / Date Certified",
                    "Date Certified " + fields["Date Certified"] + "; raw Certification # " + fields["Certification #"],
                )
            ]
        )
        if native == "TA07-14":
            event_evidence.append(source_evidence[-1])
        histories.append(
            {
                "project_id": pid,
                "events": [
                    {
                        "id": pid + ":certification:" + date,
                        "type": "certification",
                        "date": date,
                        "precision": "day",
                        "native_project_link": native,
                        "description": (
                            "Conditions of Certification document dated 2026-01-20; official page lists "
                            "final-order filing on that date. "
                            "A separate legal effective date is not established."
                            if is_deland
                            else "DEP Date Certified; not a construction or in-service date."
                        ),
                        "evidence": event_evidence,
                    }
                ],
            }
        )
        dispositions.append(
            {
                "source_id": SOURCE,
                "locator": native,
                "disposition": "accepted",
                "project_id": pid,
                "reason": "One construction/certification project from the current DEP transmission table, with "
                "linked project evidence.",
            }
        )
    index_artifact = artifacts["index"]
    source = {
        "_id": SOURCE,
        "title": "Florida DEP current transmission Conditions of Certification index",
        "publisher": index_artifact["publisher"],
        "authority": "state_government",
        "role": "project_plan",
        "landing_url": index_artifact["url"],
        "download_url": index_artifact["url"],
        "publication_date": None,
        "vintage": None,
        "retrieved_at": index_artifact["retrieved_at"],
        "sha256": index_artifact["sha256"],
        "public_status": "verified_public",
        "import_status": "imported",
        "access_policy": "public_document",
        "planning_region": None,
        "states": ["12"],
        "project_count": len(projects),
        "notes": [
            "Complete 17-row current transmission index only. Not all Florida transmission construction.",
            "Historical relinquished Lake Tarpon-Kathleen and other providers remain outside this batch.",
            "Certification history does not establish current construction or operation.",
        ],
    }
    hopkins = next(p for p in projects if p["native_id"] == "TA81-01")
    native_payload = load_json(cache / artifacts["hopkins-native"]["file"])
    output_payload = load_json(cache / artifacts["hopkins-wgs84"]["file"])
    feature = native_payload["features"][0]
    output = output_payload["features"][0]["geometry"]
    if (
        native_payload["spatialReference"].get("latestWkid") != 6439
        or len(native_payload["features"]) != 1
        or feature["attributes"]["OBJECTID"] != 15
        or feature["attributes"]["SCO_NUMBER"] != "PA 74-03"
    ):
        raise ValueError("Hopkins feature identity or CRS changed")
    record = {
        "project_id": hopkins["_id"],
        "project_facts_sha256": facts_hash(hopkins),
        "producer": PRODUCER,
        "location_kind": "line",
        "reviews": [],
        "events": [],
        "points": [
            {
                "role": "a",
                "facility_id": "fl-dep:PA74-03",
                "facility_name": feature["attributes"]["PLANT_NAME"],
                "lon": output["x"],
                "lat": output["y"],
                "original_geometry": {
                    "crs": "EPSG:6439",
                    "type": "Point",
                    "coordinates": [feature["geometry"]["x"], feature["geometry"]["y"]],
                    "transform": TRANSFORM,
                },
                "precision": "Official DEP generating-station facility reference; exact terminal position, "
                "measurement date and source accuracy unknown.",
                "uncertainty_m": None,
                "geometry_evidence": [
                    evidence(
                        artifacts["hopkins-native"],
                        "OBJECTID=15; geometry; spatialReference",
                        "DEP certified generating-station point PA74-03 in native EPSG6439. Not a surveyed line terminal.",
                    ),
                    evidence(
                        artifacts["plant-layer"],
                        "Layer 2 geometryType, spatialReference, description",
                        "Official Certified Power Plants point layer. Storage precision is not positional accuracy.",
                    ),
                    evidence(
                        artifacts["hopkins-wgs84"],
                        "OBJECTID=15 geometry; explicit inverse ESRI108354 query",
                        "Explicit ArcGIS output independently reproduced by the committed Florida transformation.",
                    ),
                    evidence(
                        artifacts["esri-transform"],
                        "PDF page 1841, operation 108354",
                        "Coordinate_Frame parameters; inverse WGS84(ITRF00)-to-NAD83(2011). Operation "
                        "accuracy is not facility accuracy.",
                    ),
                ],
                "identity_evidence": [
                    evidence(
                        artifacts["detail:city-tallahassee-hopkins-bainbridge-line"],
                        "General Information / Description",
                        "TA81-01 names Arvah B. Hopkins Generating Station as a line endpoint.",
                    ),
                    evidence(
                        artifacts["hopkins-facility"],
                        "General Information / Certification #, Licensee, Location",
                        "Named City of Tallahassee generating station PA74-03; matches official point facility identity.",
                    ),
                ],
                "identity_rationale": "Project explicitly names the generating station; DEP point identifies that facility "
                "as PA74-03. "
                "This is a disclosed facility reference for one endpoint, not exact equipment position. "
                "South Bainbridge geometry is unverified; no midpoint or full route inferred.",
            }
        ],
    }
    location_review = root / REVIEWS / "florida-hopkins-location.json"
    if location_review.exists():
        record["reviews"] = load_json(location_review)
    decision = check_location(record, hopkins)
    release = {
        "schema_version": "southeast-release-v1",
        "release_id": "f39-florida-dep-17-v1",
        "created_at": manifest["created_at"],
        "producer": PRODUCER,
        "sources": [source],
        "projects": projects,
        "location_verifications": [record],
        "project_events": histories,
        "dispositions": dispositions,
        "acquisition": [
            {
                "source_id": SOURCE,
                "scope": "Current transmission table only; excludes plant/gas tables and historical relinquished entries.",
                "row_locators": [r["certification_raw"] for r in index],
                "expected_source_rows": 17,
                "completeness": "complete",
                "enumeration_evidence": [
                    evidence(
                        index_artifact,
                        "Transmission Lines table; all 17 certification rows from TA81-01 through TA25-20",
                        "Complete current transmission table independently enumerated; source-wide/statewide "
                        "construction denominator unknown.",
                    )
                ],
            }
        ],
        "expected_counts": {
            "new_sources": 1,
            "new_projects": len(projects),
            "confirmed_projects": int(decision == "confirmed"),
            "source_rows": len(dispositions),
        },
        "coverage_notes": source["notes"]
        + [
            "One candidate facility-reference endpoint at Hopkins; other project geometry remains unlocated.",
            "County assignments preserve reported scope and may omit counties; interstate extent remains partially assessed.",
            "All current lifecycle statuses remain unknown. Certification events preserve distinct dates and source semantics.",
        ],
    }
    identity_review = root / REVIEWS / "florida-identity.json"
    if identity_review.exists():
        release["identity_review"] = load_json(identity_review)
        if release["identity_review"]["facts_sha256"] != release_hash(release):
            raise ValueError("release review does not bind current facts")
        validate(release, "southeast-release")
    return release


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build(args.cache)
    if args.check:
        if result != load_json(REPO_ROOT / CANDIDATE):
            raise ValueError("candidate differs from pinned source replay")
    else:
        write_json(REPO_ROOT / CANDIDATE, result)
    print(result["expected_counts"], "identity reviewed:", "identity_review" in result)
