# F47: Xcel "Interchange" aliases

**Context.** F47 placed 29 of 269 SPP Texas rows. Most SPS rows name Xcel sites ("Potter County", "TUCO", "Lubbock
South") that OpenStreetMap names "Potter County Interchange", "TUCO Interchange", which the shared exact-name rule
(`facility_key`) does not equate.

**Options.** Change the shared key (affects every rollout); loosen matching to prefixes (reaches other utilities'
sites); or add aliases derived from the OSM name only for facilities OSM says SPS/Xcel operates.

**Choice.** The last, inside `sppsouth`: an Xcel-operated OSM facility named "X Interchange", "X Switching Station" or
"X Switchyard" also answers to "X". Matching, corroboration and the operator guard are unchanged; each match records
`osm_name` and the center evidence names both. Result: TX 29 → 50 located, 274 in total. Spot check of all 25 alias
matches: every one is the named Xcel site (Amarillo, Lubbock, Pampa, Abernathy, Hereford areas).

**Undo.** Remove `with_aliases` from `sppsouth.build` and rebuild.
