# F33: source-bound utility directory

F33 joins the 2024 final EIA-861 workbooks only by data vintage and EIA utility number. It preserves all source rows, rejects activity foreign keys absent from Frame, and quarantines county names that do not resolve uniquely against the committed Census reference. County identity checks never count as independent corroboration of EIA service membership.

The builder requires the reviewed archive/member hashes, explicit `generated_at`, deterministic normalized content and exact recomputed denominators. Dataset hashes exclude envelope time and dataset fields; artifact hashes bind the published bytes. Same-lineage EIA rows remain one lineage, while unresolved/conflicting claims cannot populate public utility geography.

The read-only API serves only bounded public utility fields. It validates strict query keys, Census state/county parentage, literal utility ID/name search and pagination. Missing or corrupt artifacts fail closed as unavailable; no sample rows, workbook evidence, Mongo writer or fuzzy owner/project joins are introduced.

Undo by removing the F33-owned pipeline, artifacts, read-only API, tests and marker. F30 national projects and all existing Mongo/search paths remain unchanged.
