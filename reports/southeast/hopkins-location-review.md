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

## Clarification: explicitly limited facility-reference meaning

Follow-up read-only inspection: `origin/main:pipeline/expansion/assemble.py` now represents independently reviewed NOAA/VCGI facility reference points without claiming equipment or survey positions. Also inspected `power-plants-metadata-detail.txt`, whose official layer metadata identifies Certified Power Plants, describes PPSA-certified plant locations, and credits FDEP Siting Coordination Office. It does not provide an accuracy estimate or acquisition/positioning method; its Esri metadata creation date is not proof of coordinate measurement date.

**Semantic eligibility is conditional YES for the expressly limited claim proposed here.** The exact project identity link is to the named generating station; the stable PA74-03 feature describes that same facility and owner/county. Calling its point an official DEP generating-station reference for one named line endpoint, explicitly partial with unknown accuracy, does not assert a switchyard, physical termination, surveyed location or site centroid. The layer title/abstract is sufficient to identify this limited facility-reference meaning. The earlier concern remains applicable to an exact-terminal claim, but should not prohibit this narrower, disclosed representation. No additional equipment-position evidence is required solely to allow the facility-reference semantics permitted by the spec. This clarification follows the source evidence and stated meaning, not numerical agreement or pressure to add a dot.

Remaining requirements before any coordinate approval:

1. Document and independently reproduce the exact NAD83(2011)/EPSG6439 to WGS84 datum operation behind the proposed output. The previous projection-only check still leaves the approximately0.74m offset unexplained by a specified transformation.
2. Bind the final candidate to the pinned project, facility, native/output geometry and layer-method evidence, with stable feature/certification IDs and current project/record hashes. Submit that final record for independent approval; this memo is not a confirmed decision for unseen release bytes.
3. Preserve precision as an official facility reference with source accuracy/measurement date unknown; uncertainty_m null. Metadata creation/retrieval timestamps must not become measurement/status freshness. Geometry metadata tolerance must not become survey accuracy.
4. Preserve the voltage discrepancy and one-endpoint partial coverage; no South Bainbridge geometry, midpoint, line route or current operational status is established by this candidate.

No coordinates approved in this clarification. The semantic obstacle is resolved for the limited facility-reference claim; datum reproduction and final facts-bound review remain outstanding.

## Independent datum reproduction — 2026-09-27T01:58:36.483780+00:00

**Transformation discrepancy resolved.** Independently visually inspected PDF page1841 of the official Esri12.1 geographic-transformation reference, row108354. Verified Coordinate_Frame convention, WGS84-to-NAD83(2011) direction, translations(0.9956,-1.9013,-0.5215)m, rotations(0.025915,0.009426,0.011599)arcsec and scale0.00062ppm. Source URL: https://developers.arcgis.com/rest/services-reference/enterprise/d1865ecb5d1b957bb92e4444f93d769c/gtf_pdf_12.1.pdf . Render inspected at /private/tmp/hopkins-108354-review.png.

Independent reproducible script: `/private/tmp/gridbridge-hopkins-independent-transform.py`. Uses only stdlib; imports no producer code. It inverts EPSG6439 Albers on GRS80, converts NAD83 geographic coordinates to geocentric coordinates with computational height0, solves the inverse of the stated forward seven-parameter coordinate-frame transform, and converts to WGS84 geographic coordinates. Zero height is a2D transformation convention, not a source elevation claim.

Computed WGS84 longitude -84.39946533002666, latitude30.452223774750678. Explicit ArcGIS108354 inverse result is longitude -84.3994653300266, latitude30.452223774750653. Residuals are -5.684341886080802e-14 and2.4868995751603507e-14 degrees respectively. This explains the previous approximately0.74m projection-only discrepancy. The explicit query records transformForward:false, consistent with inverse WGS84-to-NAD83 direction; cached findTransformations response recommends the same operation first.

The reference operation accuracy0.1m is NOT facility-coordinate accuracy and must not populate uncertainty_m. Original source positioning accuracy/date remain unknown. The transformation reproduces the selected service representation; it does not establish survey precision, a current geodetic epoch, exact line terminal, or actual in-service status. All prior limited facility-reference/partial-endpoint semantics remain required.

Hashes of inspected new evidence:

- esri-transformations-12.1.pdf: `928f623f5832d40c6e691924e83881ffbcf4445ead2d95fbc719c3101df94a73`
- hopkins-explicit-wgs84.json: `c3d3fe0abd766f78b620dfa16857061c2f8fb2fc7b64c3c3e49d98152c141eb9`
- hopkins-explicit-query-url.txt: `c06cce04f6d321eb28556e91b9f6793055845bb037a456c5b2fa8a4c37963781`
- florida-datum-transforms.json: `05c50ae0dbe92d5959b8152256b18dbf2249a966bb112189fb4e3ac8406c7618`

The datum-method prerequisite is satisfied for these pinned native/output bytes and this explicit operation. Final project/record hash-bound location approval remains outstanding; this transformation review does not activate or confirm an unseen release.
