# F38 initial source research

Checked during C22 specification work on 2026-09-26 (session date). These are candidate source entry points.
An inspected landing page or service description is not a reviewed ingestion artifact, verified coordinate, license
approval or coverage claim. Pin bytes/metadata and inspect relevant content before enabling an adapter.

## Florida pilot

| Source | What was inspected / potential use | Limit and next check |
|---|---|---|
| [FPL Andytown–Oasis](https://www.fpl.com/reliability/andytown-oasis-project.html) | Official page names a proposed four-line program, substations, counties, a corridor PDF and planned timeline; useful identity and scope evidence | Program vs component identities need reconciliation. A preferred corridor is not an exact built route or proven endpoint coordinate. Verify the linked permit/GIS records before locating |
| [FPL ten-year plan](https://www.fpl.com/content/dam/fplgp/us/en/about/pdf/ten-year-site-plan.pdf) | Indexed transmission section/table names proposed bulk lines, terminals and month/year milestones | Candidate artifact; full PDF content/access review and byte pinning pending. Its stated table scope excludes other work, so it cannot establish statewide completeness. Compare source-specific schedules rather than silently replacing one with another |
| [Florida DEP certified-line GIS](https://cadev.dep.state.fl.us/arcgis/rest/services/OpenData/ARMS/MapServer/5) | Inspected service metadata: polyline geometry; name, licensee, certification/date, voltage, counties and website fields; paginated JSON/GeoJSON support | Metadata only; feature extraction, canonical service provenance, license and CRS transformation validation pending. Certification is not completion or current construction. A line must be explicitly linked to a project |
| [Florida DEP certified facilities](https://floridadep.gov/water/siting-coordination-office/documents/certified-facilities-list) | Official landing page links a list and related applications/certified-facility information | Contains multiple facility types; filter transmission scope and retain certification meaning. Archived and current records need source-time checks |
| [Florida PSC docket example](https://www.psc.state.fl.us/commission-conferences-of-the-fpsc?agendadate=September+10+2026) | Search result identifies docket 20260020 for the Andytown–Oasis need proceeding | Discovery lead only. Inspect docket documents, status and public exhibits; a docket listing does not establish an outcome |
| [Duke Central Park](https://www.duke-energy.com/Our-Company/Future/Central-Park) | Official project page discovered for Orlando grid improvements | Discovery lead only; inspect transmission scope and the project's own evidence before import |
| [Duke Polk County announcement](https://news.duke-energy.com/releases/duke-energy-announces-final-routes-substation-location-for-polk-county-reliability-enhancement-project) | Official historical route/substation announcement discovered | Discovery lead only; proposal/selection is not actual completion. Find linked records and applicable later status |

Florida inventory must also check the PSC's current utility filings and relevant public material for Tampa Electric,
Seminole Electric, municipal utilities such as JEA/OUC, and other evidenced transmission providers. These are discovery
targets, not claims that an ingestible project register or exact geometry has already been found for each.

## Georgia and Southeast

- Reuse the current Georgia register and its native IDs before acquiring duplicate observations. Investigate the
  unresolved linkage issues in [the existing audit](../../../reports/audit/summary.md) and preserve its decisions.
- [Georgia Power Grassy Hollow–Great Valley](https://www.georgiapower.com/about/grid-reliability/grid-improvements/grid-projects/transmission-projects/grassy-hollow-great-valley.html)
  is an official project-page discovery lead naming the project and Bartow County; inspect primary maps/documents.
- [Georgia Transmission ECRP](https://www.gatransmission.com/ecrp/) is an official project-page discovery lead;
  inspect project identity, county-specific route evidence and status. Do not treat a county meeting as geometry.
- [SERTP archive](https://www.southeasternrtp.com/archive.cshtml) was inspected and provides annual document discovery.
  Existing D15 restrictions still apply; this spec does not authorize the previously excluded report. Content-level
  restriction checks precede acquisition/extraction. Use eligible utility/regulator sources when a regional file is blocked.
- Extend the source matrix to SCRTP, FRCC and relevant regional/local plans from the existing national directory.
  Exact URLs, accessible artifacts and project coverage must be established during discovery; listing a region is not import.

## Nationwide discovery

Reuse `data/national/sources.json` for already catalogued planning entry points: ISO-NE, NYISO, PJM, MISO, SPP,
ERCOT, CAISO, NorthernGrid, WestConnect, FRCC, SERTP and SCRTP. Check the current
[FERC planning-region explainer](https://ferc.gov/explainer-transmission-planning-and-cost-allocation-final-rule)
and relevant public provider/state records for omissions. These regions have different scopes and reporting formats;
a planning-directory entry is not an acquired project corpus, and a regional register alone may omit local projects.

Prioritize public machine-readable project registers, then primary permit/project evidence that can establish location.
Utility directories, EIA plants and infrastructure inventories may support entity/location reconciliation but must not
be relabeled as a national construction-project database. Include non-ISO utility, cooperative, municipal and federal
planning sources where relevant. Alaska/Hawaii need their own discovery and remain stretch work.

## New England checkpoint (2026-09-27 UTC)

The user's later launch changes the initial priority to CT, ME, MA, NH, RI and VT; see
[F38-new-england-first](../../decisions/F38-new-england-first.md). The existing approved June 2026 RSP workbook
was downloaded again and matched its F30 hash. Its current rows were replayed against the committed snapshot.
This confirms extraction reproducibility, not precise location or freshness on the day of download.

| Source inspected | Supported discovery facts | Next check before location promotion |
|---|---|---|
| [ISO-NE RSP and Asset Condition List](https://www.iso-ne.com/system-planning/system-plans-studies/rsp) | Distinguishes regional RSP projects from owner-identified asset-condition work; points to list updates | The directory warns that some linked material is restricted. Review each exact public artifact; latest/prior vintages remain pending. Do not infer acquisition permission for all links |
| [Connecticut Docket 490](https://portal.ct.gov/CSC/1_Applications-and-Other-Pending-Matters/Applications/3_DocketNos400s/Docket-No-490---UI_Bridgeport) | United Illuminating's Old Town 115/13.8 kV rebuild; project parcels at 282, 312 and 330 Kaechele Place, Bridgeport; public project maps and construction updates are linked | Candidate link to `iso-ne:1618`. Establish the final replacement site versus existing equipment, source geometry and exact project relationship; a street address is not a coordinate |
| [Old Town application, June 2020](https://portal.ct.gov/-/media/csc/1_dockets-medialibrary/media_do400-499/do490/applicantsubmissions/application/002---united-illuminating-re-old-town-substation---csc-application---final---061120.pdf) | Page FR-1 (PDF page 9) identifies UI, Fairfield County, 115/13.8 kV and the adjoining rebuild site; useful corroboration | Searched document has no `1618` or `latitude` match. The utility's office address is separate. Application proposes work and does not prove completion. Full artifact pin/restriction review pending |
| [National Grid Massachusetts substation layer](https://systemdataportal.nationalgrid.com/arcgis/rest/services/MASDP/MASDP_Substations/MapServer/0) | Utility-hosted point layer, CRS 4326, facility name/number, address and voltage fields; supports pagination | Metadata inspected only, no geometry imported. Item metadata has blank license information. Review portal use terms, field meaning/accuracy and explicit project-to-facility identities before acquisition |
| [Acushnet–Fall River](https://www.mass.gov/info-details/acushnet-to-fall-river-reliability-project) | Official siting page describes line and associated substation work | Review petitions/appendices and explicit links to RSP component IDs before accepting endpoints; landing-page search discovery only |
| [Greater Cambridge](https://www.mass.gov/info-details/greater-cambridge-energy-program) | Official siting page describes a multi-line program and proposed underground substation | Separate program from component IDs; a program is not several independently located sites. Landing-page search discovery only |
| [MassGIS transmission layer](https://www.mass.gov/info-details/massgis-data-transmission-lines) | Search discovery identifies an asset inventory | Direct page read returned 403. Do not bypass; asset routes alone cannot establish RSP project endpoints |

NH, ME, RI and VT regulator/utility location sources remain to be reviewed. No state is geographically complete.
No newly discovered source above is enabled for bulk ingestion by this checkpoint.
