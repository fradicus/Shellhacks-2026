# F49 decisions: Alaska and Hawaii

Choices made while transcribing under [C49](C49-alaska-hawaii.md), each smaller and reversible.

1. **Alaska Energy Authority projects carry no operator keys.** AEA owns lines that end at other utilities'
   substations; OSM tags Quartz Creek as Chugach's. C38's guard would treat that as counter-evidence, but a
   transmission owner's line ending at a utility substation is not. The Sterling–Quartz Creek endpoint is therefore
   C33's name-only tier (`candidate_unique_name`), labeled as such. Undo: give the row `["ALASKA ENERGY AUTHORITY"]`.
2. **An OSM parenthetical abbreviation is an alias.** OSM names the CEIP substation
   "Campbell Estate Industrial Park (CEIP) Substation"; the source says "CEIP Substation". Only an all-caps
   abbreviation OSM itself states in parentheses is added. Undo: drop `with_aliases`.
3. **F49 fetches documents itself with a 64 MB cap.** The PUC FY2025 annual report (31 MB) and the USFWS EA
   (19 MB) exceed F40's 16 MB helper. A PDF without `%%EOF` near its end is refetched and never pinned: AEA's
   server sometimes ends a download early without an error.
4. **Sources left out:** the Alaska OMB FY2027 budget component (its server sends an incomplete certificate chain;
   verification is not disabled), ARCTEC's project pages (mod_security rejects non-browser clients; not worked
   around), and AEA's GRIP kickoff deck (always truncated). Their facts are either covered by the AEA update and
   the USFWS EA or deferred.
5. **Status wording.** A PUC hearing notice proves an application existed, not what happened next; those rows are
   `unknown` with the notice date in `status`. The hearing date is a `source_status` event, not a milestone.
6. **Undated facts stay undated.** "A new substation was energized" (Kulanihakoi) is an `in_service` event with
   `unknown` precision; the West Maui release date is recorded as the date Hawaiian Electric reported the line
   online, not as its in-service date.
7. **Excluded** rows of the PUC capital table (generation overhauls, storage, EV charging, demand response,
   program-level resilience and wildfire spending) are listed in `dispositions.json` with their quotes.
