"""FIX-F45: 2026 WECC Annual Progress Reports of the Southwest utilities, through F50's page-verifying reader.

The WestConnect TPPL (F45's main source) is each sponsor's own list; their WECC progress reports also name projects the
TPPL does not. Rows are transcribed with a page and verbatim quote into data/southwest/transcriptions/ and read by
`interiorwest.apr`, which re-verifies them against the pinned PDFs, excludes rows another rollout publishes and places
the rest under C33/C38; a row whose text names no state is placed only by a corroborated facility in the owner's
territory within F45's states.
"""

from __future__ import annotations

from pathlib import Path

from common import REPO_ROOT, load_json
from interiorwest import apr

TRANSCRIPTIONS = REPO_ROOT / "data" / "southwest" / "transcriptions"
ORGS = {"PSCo": "Public Service Company of Colorado", "TSGT": "Tri-State Generation and Transmission Association",
        "APS": "Arizona Public Service", "TEP": "Tucson Electric Power", "AEPCO": "Arizona Electric Power Cooperative",
        "PNM": "Public Service Company of New Mexico", "EPE": "El Paso Electric Company",
        "WAPA": "Western Area Power Administration"}
REPORTS = {f"apr_{org.lower()}_2026": (f"{org}_2026_APR.pdf", f"{apr.BASE}{org}%202026%20APR.pdf",
                                       f"wecc-apr-2026-{org.lower()}", name) for org, name in ORGS.items()}
TERRITORY = {ORGS["PSCo"]: ["CO"], ORGS["TSGT"]: ["CO", "NM"], ORGS["APS"]: ["AZ"], ORGS["TEP"]: ["AZ"],
             "Unisource Electric": ["AZ"], ORGS["AEPCO"]: ["AZ"], ORGS["PNM"]: ["NM"], ORGS["EPE"]: ["NM"],
             ORGS["WAPA"]: ["AZ", "CO", "NV", "UT"]}
OPERATOR_KEYS = {ORGS["PSCo"]: ["XCEL", "PUBLIC SERVICE COMPANY OF COLORADO"], ORGS["TSGT"]: ["TRI-STATE", "TRI STATE"],
                 ORGS["APS"]: ["ARIZONA PUBLIC SERVICE", "APS"], ORGS["TEP"]: ["TUCSON ELECTRIC"],
                 "Unisource Electric": ["UNISOURCE", "UNS "], ORGS["AEPCO"]: ["ARIZONA ELECTRIC POWER COOP", "AEPCO"],
                 ORGS["PNM"]: ["PUBLIC SERVICE COMPANY OF NEW MEXICO", "PNM"], ORGS["EPE"]: ["EL PASO ELECTRIC"],
                 ORGS["WAPA"]: ["WESTERN AREA", "WAPA"]}
# Rollouts whose records a transcribed row may name as the same project.
PUBLISHED = ("data/sppsouth/projects.json", "data/interiorwest/projects.json", "data/pnw/projects.json",
             "data/midwest/projects.json")


def published_ids(root: Path = REPO_ROOT) -> set[str]:
    return {p["_id"] for path in PUBLISHED for p in load_json(root / path)}
