"""FIX-F46: MISO LRTP Tranche 2.1 eligible facilities in IA, MO, ND and SD.

MISO's public workbook lists every facility of the Long Range Transmission Planning Tranche 2.1 portfolio, one
sheet per LRTP project, with its MTEP project and facility IDs, the transmission owners' member systems, state and
scope. Each facility in F46's states is one record; the workbook gives no status or date, so none is stated. Facilities
are located with F46's name parser under C33/C38; "State Line" ends and new substations stay unlocated.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import openpyxl

SOURCE_ID = "miso-lrtp-tr21-midwest"
FILE = "miso-lrtp-tr21-eligible.xlsx"
URL = "https://cdn.misoenergy.org/20250306%20LRTP%20TR2.1%20Eligible%20Projects671260.xlsx"
HEADER_ROW = 3  # rows 1-2 are the title and the ROFR note
# OSM operator fragments for the member-system codes the workbook uses in F46's states.
TO_KEYS = {"MEC": ["MIDAMERICAN"], "ITCM": ["ITC"], "ATXI": ["AMEREN"], "AMMO": ["AMEREN"], "OTP": ["OTTER TAIL"],
           "MDU": ["MONTANA-DAKOTA", "MDU"], "XEL": ["XCEL", "NORTHERN STATES"], "GRE": ["GREAT RIVER"],
           "MRES": ["MISSOURI RIVER"], "MP": ["MINNESOTA POWER"], "DPC": ["DAIRYLAND"], "CIPCO": ["CENTRAL IOWA"],
           "Ameren": ["AMEREN"], "AmerenMO": ["AMEREN"], "AmerenIL": ["AMEREN"], "WAPA": ["WESTERN AREA", "WAPA"]}


def rows(path: Path) -> list[dict]:
    """Facility rows of the per-project sheets (the summary sheet has no State column), with their locators."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in book.worksheets[1:]:
        table = list(ws.iter_rows(values_only=True))
        header = [" ".join(str(h).split()) if h is not None else "" for h in table[HEADER_ROW - 1]]
        for n, r in enumerate(table[HEADER_ROW:], start=HEADER_ROW + 1):
            if r[0] is not None:
                out.append(dict(zip(header, r, strict=False)) | {"_sheet": ws.title, "_row": n})
    return out


def owners(cell) -> list[str]:
    """Member-system codes; "To Be Determined …" (a competitive or undecided owner) names no one."""
    codes = [o.strip() for o in str(cell or "").replace("\n", " ").split(",") if o.strip()]
    return [c for c in codes if not c.lower().startswith("to be determined")]


def keys(codes: list[str]) -> list[str]:
    return [k for c in codes for k in TO_KEYS.get(c, [])]
