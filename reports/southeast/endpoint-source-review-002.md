# Florida endpoint source follow-up

Independent reviewer `/root/f39_florida_review`. No repository writes, geometry acquisition or activation. Assessment uses official Duke announcement, ArcGIS layer metadata and supplied TVA metadata. No coordinate approval.

## Florida verdict: reject RPS_VOH as endpoint confirmation at this stage

The official Duke announcement (2018-12-13) establishes two construction components and their named termini: Kathleen line to Kathleen substation, Haines City line to Haines City East, both associated with the proposed Osprey substation. It is valid historical project-link evidence. Its projected 2024 in-service statement is not proof of completion.

Source: https://news.duke-energy.com/releases/duke-energy-announces-final-routes-substation-location-for-polk-county-reliability-enhancement-project , route bullets and Next Steps. The linked Duke map failed to open in this review; no access restriction was bypassed and no alternative private endpoint was queried.

RPS_VOH_Features is not established as Duke-authored project geometry. Service metadata says layers for a public open house but gives no named Polk project or accountable publisher. The existing-substations layer explicitly describes a general substations/taps inventory and credits ORNL/LANL/INL/NGA HSIP, not a Duke project survey. Its legend includes Ocala Electric, suggesting a different study area; this is a warning, not proof of geography. No reviewed record links Kathleen, Haines City East or Osprey to this layer. A service name containing Duke in another layer is insufficient authority or project provenance.

Exact metadata:
- https://services.arcgis.com/DN2fPfpggEPlLhP6/ArcGIS/rest/services/RPS_VOH_Features/FeatureServer — service item368663c0ee5e4ab5b719d752b682f377; description public-OH layers, blank copyright.
- https://services.arcgis.com/DN2fPfpggEPlLhP6/ArcGIS/rest/services/RPS_VOH_Features/FeatureServer/0 — Existing Substations, point geometry, NAME/ID/TYPE/STATUS/Owner/GlobalID; inventory/taps meaning; original spatial reference102659/latest2237 and service units feet. Accuracy unspecified.
- https://services.arcgis.com/DN2fPfpggEPlLhP6/ArcGIS/rest/services/RPS_VOH_Features/FeatureServer/getEstimates — indexed estimate25 substations. Estimate is not a complete acquired row-ID response.

Public retrieval does not establish reuse rights. Because underlying HSIP inventory provenance is credited but license/origin edition is not explained, do not bulk acquire features as approved project geometry. First obtain item license/access/publisher metadata and an official utility page linking this exact service/project. No positive restriction was fabricated: license is unresolved, not known prohibited. Metadata can remain discovery evidence.

## Next Florida evidence

The announcement itself is the exact usable source for historical component identity and source-time semantics. For geometry, obtain its official route map or publicly accessible project siting/parcel document that directly identifies the named substation footprint/point with a stable ID. Then inspect geometry meaning and CRS; don't substitute the Osprey plant marker or a route vertex.

A search found Florida Polytechnic's 2022-09-28 board book, whose indexed appraisal passage links the Polk project/Kathleen line to a specific address (12347 US Hwy98 N, Lakeland). URL https://floridapoly.edu/board-of-trustees/assets/agendas/2022/09/09.28.22_board_of_trustees_board_book.pdf now returned404. Treat it as discovery only, not verified address/geometry; find an accessible official board archive copy before using its facts. A geocode alone would still require parcel/site corroboration.

## TVA secondary assessment

Supplied webmap metadata names ownerTVA-GIS and item97b88516802c4c0b9cc064c59711e49f. Root reports official Jones Chapel page links that map; preserve the source page/link bytes as the authority chain. Cached map data directly references:
https://services.arcgis.com/w8auYAijfGK1Mydj/arcgis/rest/services/TSSProjects_Hosted/FeatureServer/3

This substation layer is **polygon geometry**, with NAME, DESCRIPTION, SOURCE, PROJECT_ID, STATUS, GlobalID. It is a stronger next research source than RPS_VOH because it offers project-specific identifiers and a utility-page link chain. Still inspect exact feature attributes against official project text and retain proposed/alternative status. An independently verified site polygon is useful location evidence, but current point contract does not automatically authorize replacing a line terminal with polygon centroid or an arbitrary vertex. Seek a published site/terminal point or an explicitly reviewed polygon-to-site representation method under the applicable contract before promotion. Route layers0/5 remain route/corridor evidence only.

No source files from this follow-up were downloaded or hashed by this reviewer. Prior supplied metadata inspection is not approval of any unseen feature geometry. No new confirmed endpoint was established.
