# Hopkins–Bainbridge candidate location review

Reviewer: `/root/f39_florida_review`; UTC reviewed 2026-09-27 01:32:57.
Decision: **needs review; do not promote this candidate yet.** Identity linkage is strong. Exact endpoint-point meaning and reproducible datum operation are insufficiently documented in the supplied evidence. This is not a rejection of the facility or a finding that its coordinates are false.

## What is established

The official TA81-01 project page explicitly identifies Arvah B. Hopkins Generating Station as one terminus, the City of Tallahassee as licensee, and South Bainbridge as the other terminus. The official generating-station page identifies PA74-03, City of Tallahassee, Leon County, address 1125 Geddie Road. DEP Certified Power Plants layer feature OBJECTID 15 identifies the same generating station, owner, PA74-03 and county, and links the exact facility page. This is more than a name-only match. A parent power-plant inventory row must remain endpoint evidence for TA81-01; it is not an additional transmission project.

Official pages:
- https://floridadep.gov/water/siting-coordination-office/content/city-tallahassee-hopkins-bainbridge-line — General Information, Description / Licensee / Certification.
- https://floridadep.gov/water/siting-coordination-office/content/arvah-b-hopkins-gnerating-station — General Information, certification, address and county. Note source URL spelling `gnerating`.
- https://cadev.dep.state.fl.us/arcgis/rest/services/OpenData/ARMS/MapServer/2 — Certified Power Plants metadata and feature OBJECTID 15, SCO_NUMBER PA 74-03.

## Why not confirm yet

F38 Location evidence (inherited by F39) allows official facility coordinates linked to a project and explicitly permits unknown uncertainty as null. Thus neither lack of survey accuracy nor use of a facility reference is automatically disqualifying. The spec does not demand invented precision or an arbitrary extra source.

However, this layer describes only power-plant locations. It does not identify whether its point represents a plant label, building, site representative point, switchyard or line termination. Unknown positional uncertainty is different from unknown feature meaning. If publishing this as an exact transmission endpoint, the supplied evidence is insufficient. At most it supports a **facility-level candidate for the named endpoint**. Preserve that meaning and null uncertainty; do not call it a located switchyard or terminal. Obtain feature-method metadata or an official endpoint/site plan that establishes what this marker represents and whether facility-level representation is explicitly acceptable for this endpoint. Do not invent a switchyard point from visual imagery or use an arbitrary line vertex.

The candidate has only one linked endpoint. South Bainbridge has no reviewed geometry here. Any subsequent approval must be explicitly partial, with one endpoint and no inferred midpoint.

## CRS and arithmetic check

Native response declares ESRI WKID102967 / latest EPSG6439. Layer metadata supplies xyTolerance0.001 and xyUnits10000; these are storage settings, not positional accuracy. EPSG6439 is NAD83(2011) / Florida GDL Albers in metres; Esri official projected-coordinate table identifies the corresponding system: https://doc.arcgis.com/es/allsource/1.2/visualization/pdf/projected_coordinate_systems.pdf .

Native coordinate: x361673.80200000107, y716135.95380000025.
ArcGIS outSR4326 output: longitude -84.399465330026601, latitude30.452223774750653.
Attribute values: LONG_ -84.399461, LAT30.452218 (attribute datum not declared separately).

No installed pyproj/proj executable was available. Independently inverted the Albers projection using Python stdlib math, GRS80 ellipsoid a6378137, inverse flattening298.257222101, standard parallels24/31.5, origin24/-84, false easting400000, northing0. Result in **NAD83(2011) geographic coordinates**, without a datum shift:
longitude -84.39946127898251, latitude30.452218069491423.
This agrees with the stored LAT/LONG_ fields to their six decimal places. The ArcGIS WGS84 output differs by -0.00000405104408685 degrees longitude and +0.00000570525923038 degrees latitude (roughly0.74m horizontally at this latitude). That is consistent with an additional datum operation, but this review has not independently established which operation ArcGIS selected. Do not call the projection-only result WGS84 or silently discard the difference. Record an explicit ArcGIS datumTransformation identifier/parameters, pin the transformation response, then independently reproduce/verify it. Request-only outSR4326 is not a complete durable specification of the datum operation.

No actual geographic accuracy bound is supplied. Preserve uncertainty null and facility-level precision; number of decimal places is not survey precision.

## Factual discrepancy

TA81-01 project page Voltage field says `2,200 MW`, which is power capacity units, not voltage. The raw GIS/PDF say230kV. Preserve the erroneous source field and competing evidence; do not normalize 2,200MW to a voltage. This does not erase the explicit endpoint identity link, but precludes saying all corroborating fields agree.

## SHA256 of inspected raw bytes

| File | SHA256 |
| --- | --- |
| hopkins-project.html | fdf4c8fe388998adb491ca392e6e057c62c5ff7033591915e5e8d676b789f0ac |
| hopkins-facility.html | 66fd61179902fd4e1b22e1d5973fb42a5124f1c346478efd3f59c19b332062a1 |
| hopkins-native-point.json | be6e2e39bbb9d8c16716314707535e143da5ed836b8c54a0bde9ae0e911e17b9 |
| hopkins-point.json | c3d3fe0abd766f78b620dfa16857061c2f8fb2fc7b64c3c3e49d98152c141eb9 |
| power-plants-metadata.json | 55d7df530addd0f7d781ab18103cf7e67f55af3aaa3c7bf6116789e1b4ddba56 |

These hashes identify inspected bytes; no separate producer manifest was supplied for equality checking. No coordinates approved and no repository files changed.
