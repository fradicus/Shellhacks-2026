"""BPA categorical exclusion (CX) determinations, 2025-2026: current transmission construction with named counties.

Each CX memo states its title, BPA project number, "Location: <counties>, <state>" and the exclusion classes applied.
Only memos applying a transmission construction class (B4.6 additions/modifications, B4.11 substations, B4.12
new lines, B4.13 upgrades/rebuilds) become projects; the rest are excluded with that reason. Rows use the same shape
as data/pnw/transcriptions, so build.py locates them identically.
"""

from __future__ import annotations

import re

from greatlakes.match import facilities_named, voltages_kv

BASE = "https://www.bpa.gov/-/media/Aep/environmental-initiatives/categorical-exclusions/"
# Filtered by title from the 2024-2026 listing at
# https://www.bpa.gov/learn-and-participate/public-involvement-decisions/categorical-exclusions
# (telecom, fish/wildlife, land, vegetation, security, fence and pole-replacement memos left out).
MEMOS = """
cx-2024/20240122-bellingham-substation-maintenance-and-disconnect-switch-replacements.pdf
cx-2024/20240123-hood-river-electric-co-op-interconnection.pdf
cx-2024/20240123-northern-wasco-county-pud-service-line-replace.pdf
cx-2024/20240201-P-12-Water-Source-Switch-Project.pdf
cx-2024/20240205-cascade-locks-substation-sale.pdf
cx-2024/20240206-leslie-rd-reata-transmission-line-interconnection.pdf
cx-2024/20240207-stjohns-substation-transformer-and-tie-line-conductor-replacement.pdf
cx-2024/20240207-tillamook-substation-disconnect-switches-and-maintenance.pdf
cx-2024/20240220-rogue-substation-communications-site-beam-path-maintenance.pdf
cx-2024/20240220-ross-calibration-chemistry-mangan-pcb-labs-and-surveyor-garage-upgrade-cx-update-02-2023.pdf
cx-2024/20240226-columbia-substation-transformer-bank-1.pdf
cx-2024/20240401-walla-walla-service-lighting-upgrade-project.pdf
cx-2024/20240411_lane-wendson_no2_structures_213_to_223_line_repair_project.pdf
cx-2024/20240419-santiam-sub-equipment-upgrade-and-santiam-albany-no-1-transmission-line-modification.pdf
cx-2024/20240429-bell-addy-no1-transmission-line-switch-replacements-and-structure.pdf
cx-2024/20240514_ostrea_sola_interconnection_project.pdf
cx-2024/20240521-lapine-substation-shunt-capacitor-expansion.pdf
cx-2024/20240529-snohomish-pud-battery-energy-storage-system-interconnection.pdf
cx-2024/20240529-uec-transmission-lines-longhorn-substation.pdf
cx-2024/20240611-hood-river-electric-coop-interconnection-update-on-jan-2024-cx.pdf
cx-2024/20240614-richland-substation-to-stevens-dr-transmission-line-rebuild.pdf
cx-2024/20240625-umatilla-electric-cooperative-mcnary-rockpile-transmission-line-upgrade.pdf
cx-2024/20240702-northwest-pipeline-installation-at-north-bonneville-midway-no1-transmission-line-row.pdf
cx-2024/20240711-snohomish-pud-battery-energy-storage-system-interconnection-may292024-cx-update.pdf
cx-2024/20240716-chief-joe-substation-upgrade-and-4160v-chief-joe-dam-line-replacement-and-reroute.pdf
cx-2024/20240719-rocky-reach-substation-transformer-and-disconnect-switch-replacements.pdf
cx-2024/20240724-snohomish-substation-maintenance-project.pdf
cx-2024/20240729-glade-tap-reconductor.pdf
cx-2024/20240730-hot-springs-substation-equipment-replacements-and-upgrades.pdf
cx-2024/20240801-mcnary-badger-canyon-no1-line-relocation.pdf
cx-2024/20240809-ice-age-dr-extension-xing-keeler-oregon-city-no2-transmission-line-corridor.pdf
cx-2024/20240809-nwnatural-gas-lines-xing-keeler-oregon-city-no2.pdf
cx-2024/20240829-lund-hill-battery-energy-storage-system-interconnection.pdf
cx-2024/20240918-keller-tap-grand-coulee-okanogan-no2-structures-204-and-212-urgent-replacement.pdf
cx-2024/20240920-or-trail-solar-facility-battery-energy-storage-system-interconnection.pdf
cx-2024/20241003-john-day-grizzly-500kv-no2-38-1-impairments.pdf
cx-2024/20241016-shelton-fairmount-no2-line-miles-49-and-50-structure-relocation.pdf
cx-2024/20241022-laclede-sub-transformer-replacement-and-metering-upgrade.pdf
cx-2024/20241028-red-mountain-horn-rapids-rebuild-update-to-previous-cx-01-23.pdf
cx-2024/20241031-bridge-substation-upgrade-and-expansion.pdf
cx-2024/20241101-columbia-generating-station-500kV-motor-operated-disconnect-switch-replacement.pdf
cx-2024/20241126-wheatridge-east-interconnection-project.pdf
cx-2024/20241219-biglow-canyon-wind-generation-interconnection-project.pdf
cx-2025/20250115-lapine-substation-shunt-capacitor-expansion.pdf
cx-2025/20250115-pge-reconductor-project-crossing-bpa-keeler-oregon-city-2-on-bpa-fee-owned-row.pdf
cx-2025/20250221-heyburn-minico-reconductor.pdf
cx-2025/20250221-pearl-sherwood-no-1-and-no-2-transmission-line-and-pearl-substation.pdf
cx-2025/20250224-targhee-substation.pdf
cx-2025/20250228-cx-bluebird-solar-generation-interconnection-project-g0586.pdf
cx-2025/20250303-harrisburg-substation-battery-replacement.pdf
cx-2025/20250314-communication-system-upgrade-port-angeles-and-sappho-substations.pdf
cx-2025/20250423-morrow-solar-generation-interconnection.pdf
cx-2025/20250424-silver-creek-sub-and-silver-creekmayfield-no1-230kv-upgrade.pdf
cx-2025/20250501-the-dalles-substation-expansion-and-updates.pdf
cx-2025/20250609-ccx-transmission-line-and-communication-tower-safety-upgrades-fall-protection-2030.pdf
cx-2025/20250610-wautoma-rock-creek-transmission-line-miles-37-to-43-reconductor.pdf
cx-2025/20250623-city-of-forest-grove-powerline-upgrades.pdf
cx-2025/20250722-chief-joseph-monroe-no1-681-ransmission-line-veg-mgmt.pdf
cx-2025/20250728-vhf-radio-system-upgrades-at-noxon-and-miller-peak-radio.pdf
cx-2025/20250729-winnemucca-sub-equipment-removal.pdf
cx-2025/20250729ccxtransmissionlinestructurehardwareandequipmentmaintenancereplacementandinstallthrough2030.pdf
cx-2025/20250731-urgent-response-on-hatton-tap-disconnect-switch-replacement.pdf
cx-2025/20250811-pacificorp-lyons-loop-upgrade.pdf
cx-2025/20250813-canyon-creek-pivot-pipeline-repair.pdf
cx-2025/20250819-douglas-county-pud-line-upgrade-at--valhalla-substation.pdf
cx-2025/20250821-chie-joseph-substation-property-transfer.pdf
cx-2025/20250826-ross-cold-creek-yard-expansion-project.pdf
cx-2025/20250930-driveway-improvements-and-solar-array-on-nbonneville-troutdale-no1-230kV-row.pdf
cx-2025/20251006-maple-valley-substation-transformer-installation-and-yard-expansion.pdf
cx-2025/20251009-chenowith-goldendale-line-mile-7-impairment-remediation.pdf
cx-2025/20251009-surprise-lake-substation-trenching-and-cable-replacement.pdf
cx-2025/20251020-avista-bluebird-substation-interconnection-to-grand-coulee-bell-no5.pdf
cx-2025/20251021-broadview-garrison-no2-transmission-line-impairments-164_4-to-165_2.pdf
cx-2025/20251023-troutdale-substation-terminal-expansion.pdf
cx-2025/20251028-monroe-substation-maintenance-project.pdf
cx-2025/20251118-morrow-solar-generation-interconnect-project-previous-cx-updated-20250423.pdf
cx-2025/20251121-sound-transit-line-raises.pdf
cx-2025/20251216-ringold-springs-hatchery-electrical-upgrades-project.pdf
cx-2026/20260105-lapine-fort-rock-access-road-upgrades.pdf
cx-2026/20260106-lapine-substation-shunt-capacitor-expansion-update-to-cx-issued-01152025.pdf
cx-2026/20260112-physical-security-system-upgrade-at-midway-substation.pdf
cx-2026/20260115-wheatridge-surplus-generation-interconnection-projects.pdf
cx-2026/20260126-rocky-reach-maple-valley-rebuild-miles-99-103.pdf
cx-2026/20260202-filbert-tap-forest-grov-mcminnville-no1-structure-relocation.pdf
cx-2026/20260226-jones-canyon-santiam-no1-access-rd-improvement-project-ph2-line-miles-109-and-115-132.pdf
cx-2026/20260226toledowendsonno1linemiles1516accessrdimprovementprojectph2.pdf
cx-2026/20260309-filbert-tap-to-forest-grove-mcminnville-no1-danger-tree-removal-project.pdf
cx-2026/20260312-port-angeles-sappho-no1-access-rd-upgrade-phase-1.pdf
cx-2026/20260316-sacheen-alternate-station-service-transformer-move-project-update-cx-issued-20211101.pdf
cx-2026/20260319accessrdbridgereplacementsnearstructures963and973onthechiefjosephmonroeno1transmissionline.pdf
cx-2026/20260319richlandsubstationtostevensdrivetransmissionlinerebuildprojectupdatetopreviouscx.pdf
cx-2026/20260323underwoodtaptobonnevilleph1alcoano12insulatorreplacementreconductor.pdf
cx-2026/20260325-125vdc-station-service-battery-purchase-at-connell-substation.pdf
cx-2026/20260325-john-day-grizzly-500kv-no2-impairment-and-access-road-improvement-project.pdf
cx-2026/20260330accessrdbridgereplacementsnearstructures963and973onthechiefjoemonroeno1txlineupdate20260319.pdf
cx-2026/20260406targheesubbreakerinstallationandtransfertripupgradesupdate-to-previous-CX-issued-20250224.pdf
cx-2026/20260413-palouse-junction-solar-facility-and-battery-storage-interconnection-projects.pdf
cx-2026/20260501-security-system-upgrade-at-monroe-substation.pdf
cx-2026/20260512-troy-sub-city-of-troy-public-utility-district-distribution-corridor-danger-tree-removal.pdf
cx-2026/20260527-mcnary-roundup-no1-transmission-line-rebuild-project.pdf
cx-2026/20260529-nez-perce-tribal-hatchery-chilled-water-system-upgrade.pdf
cx-2026/20260529-tillamook-substation-line-terminal-swap-project.pdf
cx-2026/20260617-pge-carty-solar-interconnection.pdf
cx-2026/20260622-benton-franklin-no1-transmission-line-switch-installation-and-structure-reconfig.pdf
cx-2026/20260708-eugene-alderwood-no1-115kV-rebuild-and-upgrades-cx.pdf
cx-2026/20260709-physical-security-system-upgrade-at-olympia-substation.pdf
cx-2026/20260715-actions-to-accommodate-construction-of-idaho-power-cos-boardman-to-hemingway-tx-line.pdf
cx-2026/20260727-carriger-solar-interconnection-project.pdf
cx-2026/20260803-fy26-westside-substation-defensible-space-veg-mgmt.pdf
cx-2026/20260810-chief-joseph-sickler-no1-transmission-line-insulator-replacement.pdf
cx-2026/20260915-chief-joseph-substation-transformer-maintenance-project.pdf
cx-2026/20260915-ross-substation-and-complex-station-service-upgrade-project-updated-cx-from-20230104.pdf
cx-2026/20260924-warner-substation-and-happy-camp-radio-site-alignment-project.pdf
""".split()
CONSTRUCTION = {"B4.6", "B4.11", "B4.12", "B4.13"}
STATE_NAMES = {"Washington": "WA", "WA": "WA", "Oregon": "OR", "OR": "OR", "Idaho": "ID", "ID": "ID", "Montana": "MT",
               "MT": "MT", "California": "CA", "Nevada": "NV", "NV": "NV", "Utah": "UT", "Wyoming": "WY"}
STATE = re.compile(r",?\s*\b(" + "|".join(STATE_NAMES) + r")\b(?!\s+[Cc]ount)\.?")  # not "Washington County"
FIELD = re.compile(r"(Proposed Action|Project No\.|Project Manager|Location|Categorical Exclusions? Applied)\s*:?\s*")


def files() -> dict[str, str]:
    """Cache file name -> URL."""
    return {"cx_" + path.rsplit("/", 1)[1]: BASE + path for path in MEMOS}


def fields(text: str) -> dict[str, str]:
    """The labeled header fields of a CX memo's first page, whitespace-collapsed."""
    parts = FIELD.split(text, maxsplit=10)
    out: dict[str, str] = {}
    for label, value in zip(parts[1::2], parts[2::2], strict=True):
        out.setdefault(label.replace("Exclusions", "Exclusion"), value.strip())
    return out


def counties(location: str) -> list[tuple[str, str]]:
    """(state, county name) pairs: 'Bonneville, Fremont, and Teton counties, Idaho and Teton County, Wyoming'."""
    pairs, start = [], 0
    for m in STATE.finditer(location):
        chunk = re.sub(r"\b(counties|county)\b", " ", location[start:m.start()], flags=re.I)
        for name in re.split(r",|\band\b", chunk):
            name = name.strip(" .")
            if name and name[0].isupper() and not name.lower().startswith(("multiple", "city of")):
                pairs.append((STATE_NAMES[m[1]], name))
        start = m.end()
    return pairs


def rows(pages: dict[int, str]) -> dict:
    """One transcription-shaped row from a memo's pages; a tap endpoint stays None (partial line).

    A 2024 memo counts only if its own text names a year in the user's 2025-2035 window (e.g. a construction date).
    """
    f = fields(pages[1])
    window = sorted({y for text in pages.values() for y in re.findall(r"\b(20(?:2[5-9]|3[0-5]))\b", text)})
    title = re.sub(r"\.$", "", f.get("Proposed Action", "")).strip()
    applied = set(re.findall(r"B\s?\.?\s?(\d+\.\d+)", f.get("Categorical Exclusion Applied", "")))
    applied = {f"B{c}" for c in applied}
    location = f.get("Location", "")
    pairs = counties(location)
    states = sorted({s for s, _ in pairs})
    named = facilities_named(title, None)
    row = {"native_id": f.get("Project No.") or None, "name": title, "page": 1,
           "quote": f"Location: {location}", "owner": "Bonneville Power Administration", "states": states,
           "state_basis": "source_text" if states else None, "counties": [c for _, c in pairs],
           "county_pairs": pairs, "kind": named["kind"], "facilities": named["names"],
           "voltages_kv": sorted(voltages_kv(title)), "in_service_raw": None,
           "status_raw": "Categorical exclusion determination (NEPA decision to proceed)", "cost_raw": None,
           "work_type": "transmission" if applied & CONSTRUCTION else "other",
           "section": "CX classes applied: " + ", ".join(sorted(applied)),
           "window_years": window}
    return row
