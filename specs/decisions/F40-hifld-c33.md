# F40 part 4: HIFLD fallback and C33's unique-name tier

**Context.** The user asked this session to adopt F40 and fill sparse Great Lakes states (MN 64 points of 303
projects, IL 39 of 180). 480 endpoint names had no OSM facility (OSM leaves many substations unnamed) and ~90 were
uncorroborated. Every rollout after C26 uses C33's labeled unique-name tier with C38's operator guard; F42 already
reads HIFLD's public substation layer.

**Options.** (a) Switch F40 wholesale to C33/C38: +116 points, but C38's guard dropped 20 existing points and cut 26
lines to one endpoint, mostly NY tie lines that correctly end at another utility's substation. (b) Keep every C26
match unchanged and loosen only what C26 could not place.

**Choice.** (b). `shared.locate_named` keeps a C26 match (operator/voltage) as it was. An uncorroborated name goes
through C33's matcher (unique in the pool → `candidate_unique_name`, another utility's facility → rejected). A name
OSM lacks is tried against committed HIFLD extracts (`data/greatlakes/hifld/`) with the same C33/C38 rules; the
center evidence names the HIFLD substation. Publish labels the tier; the release rule is C33.

**Result.** 663 → 799 centers: 136 projects gain a point (WI 72, IL 40, NY 38, MN 21, IN 4, MI 1), 41 partial lines
gain their second endpoint, 0 lost or moved elsewhere. Spot check of 10 gained: 9 at the named site; "Danz Ave SW STA
– University (WPS)" matched the state's only "University" substation, at Whitewater, likely not WPS's (C33 looseness).
Source workbooks were re-fetched; only `retrieved_at` changed. AEP (official tier) was not rebuilt.

**Undo.** Restore the C26 `locate_named` and `publish` tier, delete `data/greatlakes/hifld/`, rebuild.
