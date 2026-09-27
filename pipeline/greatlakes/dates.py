"""In-service dates for Great Lakes projects that were published without one; publish.py overlays them.

From pipeline/:
  uv run python -m greatlakes.dates aep --pages <aep cache> --cache <dir> [--check]
      AEP project-page timeline graphics. The SVGs hold outlined glyphs, not text, so each is rendered (macOS
      qlmanage) and read with tesseract; the date is the season/month + year printed directly under the label.
  uv run python -m greatlakes.dates firstenergy --cache <dir> [--check]
      FirstEnergy's 2026 Long-Term Forecast Report (PUCO 26-0504-EL-FOR), Form FE3-T9 "Operation" year, joined by the
      project's Ohio Power Siting Board case number or by the same two line terminals.
Writes data/greatlakes/dates/<source>.json keyed by project _id. A date is the utility's stated plan, not completion.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin

import pdfplumber

from common import REPO_ROOT, load_json, write_json

from .match import facilities_named, facility_key
from .shared import fetch_into, verify_cache

OUT = REPO_ROOT / "data" / "greatlakes" / "dates"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
TIMELINE_LINK = re.compile(r"images/timeline[^\"' )]*\.(?:svg|jpg|png)", re.I)
LTFR_URL = "https://dis.puc.state.oh.us/ViewImage.aspx?CMID=A1001001A26F02B44352J03794"
CASE = re.compile(r"\b\d{2}-\d{4}-EL-[A-Z]{3}\b")


def in_service(when: str, year: str, label: str, source: str) -> dict:
    month = next((i for i, m in enumerate(MONTHS, 1) if when.lower() == m.lower()), None)
    value, precision = (f"{year}-{month:02d}", "month") if month else (year, "year")
    return {"raw": f"{when} {year} ({source}: {label})", "value": value, "precision": precision}


def read_timeline(path: Path) -> list[dict]:
    """OCR words with boxes (tesseract TSV) of a timeline image; SVGs are rendered to PNG first."""
    image = path
    if path.suffix == ".svg":
        subprocess.run(["qlmanage", "-t", "-s", "2400", "-o", str(path.parent), str(path)], check=True,
                       capture_output=True)
        image = path.with_name(path.name + ".png")
    out = subprocess.run(["tesseract", str(image), "-", "--psm", "11", "tsv"], check=True, capture_output=True,
                         text=True).stdout
    rows = [line.split("\t") for line in out.splitlines()[1:]]
    return [{"text": r[11], "left": int(r[6]), "top": int(r[7]), "width": int(r[8]), "height": int(r[9])}
            for r in rows if len(r) == 12 and r[11].strip()]


QUALIFIER = re.compile(r"^(?:Ongoing-)?(Early|Mid|Late|End|Spring|Summer|Fall|Autumn|Winter|" + "|".join(MONTHS) + r")$",
                       re.I)
ANCHORS = [("SERVICE", "Placed In Service"), ("IN-SERVICE", "In-Service"), ("COMPLETE", "Complete"),
           ("COMPLETION", "Completion")]


def timeline_date(words: list[dict]) -> tuple[str, str, str, dict] | None:
    """The qualified date printed directly under an in-service/complete label: the next line down (within three line
    heights), starting at or left of the label's right edge. OCR reading order is not trusted: axis years interleave."""
    dates = []
    for i, w in enumerate(words[:-1]):
        nxt = words[i + 1]
        if (QUALIFIER.match(w["text"]) and re.fullmatch(r"20[1-3]\d[.,]?", nxt["text"])
                and abs(nxt["top"] - w["top"]) < w["height"]):
            dates.append((w, nxt["text"][:4]))
    for anchor, label in ANCHORS:
        for w in words:
            if w["text"].strip(".,:*").upper() != anchor:
                continue
            below = [(d, year) for d, year in dates if 0 < d["top"] - w["top"] <= 3 * w["height"]
                     and d["left"] <= w["left"] + w["width"]]
            if below:
                d, year = min(below, key=lambda b: b[0]["top"])
                return QUALIFIER.match(d["text"])[1].title(), year, label, {"label_box": w, "date_box": d}
    return None


def aep(pages: Path, cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    dates = {}
    for project in load_json(REPO_ROOT / "data" / "greatlakes" / "aep" / "projects.json"):
        url = project["evidence"]["raw"]["project_url"]
        state = url.split("/")[3]
        page = pages / f"{state}--{url.strip('/').rsplit('/', 1)[1]}.html"
        link = TIMELINE_LINK.search(page.read_text(errors="replace")) if page.exists() else None
        if not link:
            continue
        image_url = urljoin(url.rstrip("/") + "/", link[0])
        name = re.sub(r"[^A-Za-z0-9._-]", "_", image_url.split("aeptransmission.com/")[1])
        if name not in manifest:
            try:
                fetch_into(cache, name, image_url, manifest)
            except HTTPError as error:  # a page can link a timeline file the site no longer serves
                print(f"skip {image_url}: HTTP {error.code}")
                continue
            write_json(cache / "manifest.json", manifest)
        words_path = cache / f"{name}.words.json"
        if not words_path.exists():
            write_json(words_path, read_timeline(cache / name))
        found = timeline_date(load_json(words_path))
        if not found:
            continue
        when, year, label, boxes = found
        dates[project["_id"]] = {
            "in_service": in_service(when, year, label, "AEP project timeline"),
            "evidence": {"image_url": image_url, "image_sha256": manifest[name]["sha256"],
                         "retrieved_at": manifest[name]["retrieved_at"], "ocr_boxes": boxes,
                         "note": "Read by OCR from AEP's timeline graphic: the date printed under the label. AEP marks "
                                 "timelines subject to change."}}
    return dates


def ltfr_forms(path: Path) -> list[dict]:
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    forms = []
    for i, form in enumerate(text.split("FORM FE3-T9")[1:], start=1):
        name = re.search(r"Line Name and Number\s+(.+)", form)
        operation = re.search(r"Operation:\s*(20\d\d)", form)
        ends = re.findall(r"\b[OT]:\s*(.+?)\s*$", form, re.M)
        if name and operation:
            forms.append({"form": i, "name": name[1].strip(), "year": operation[1], "cases": sorted(set(CASE.findall(form))),
                          "terminals": sorted({facility_key(e) for e in ends})})
    return forms


def firstenergy(cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    if "fe-ltfr-2026.pdf" not in manifest:
        fetch_into(cache, "fe-ltfr-2026.pdf", LTFR_URL, manifest)
        write_json(cache / "manifest.json", manifest)
    verify_cache(cache, ["fe-ltfr-2026.pdf"])
    forms = ltfr_forms(cache / "fe-ltfr-2026.pdf")
    dates = {}
    for project in load_json(REPO_ROOT / "data" / "greatlakes" / "firstenergy" / "projects.json"):
        case = project.get("siting_case")
        hits, how = [f for f in forms if case and case in f["cases"]], "siting case"
        named = facilities_named(project["name"], None)
        pair = {facility_key(n) for n in named["names"] if n} if named["kind"] == "line" else set()
        if not hits and len(pair) == 2:
            hits, how = [f for f in forms if pair <= set(f["terminals"])], "same two terminals"
        if len({f["year"] for f in hits}) != 1:
            continue  # none, or forms that disagree: leave the date unknown
        form = hits[0]
        dates[project["_id"]] = {
            "in_service": {"raw": f"Operation: {form['year']} (FirstEnergy 2026 LTFR Form FE3-T9: {form['name']})",
                           "value": form["year"], "precision": "year"},
            "evidence": {"url": LTFR_URL, "sha256": manifest["fe-ltfr-2026.pdf"]["sha256"],
                         "retrieved_at": manifest["fe-ltfr-2026.pdf"]["retrieved_at"], "form": form["form"],
                         "joined_by": how, "docket": "PUCO 26-0504-EL-FOR"}}
    return dates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=["aep", "firstenergy"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--pages", type=Path, help="aep: cache of AEP project pages from greatlakes.aep fetch")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    dates = aep(args.pages, args.cache) if args.source == "aep" else firstenergy(args.cache)
    path = OUT / f"{args.source}.json"
    if args.check:
        ok = path.exists() and load_json(path) == dates
        print("ok" if ok else f"stale: {path}")
        return 0 if ok else 1
    write_json(path, dates)
    print(f"{len(dates)} dated -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
