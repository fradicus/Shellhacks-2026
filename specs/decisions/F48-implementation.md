# F48 implementation

Codex local / technical-lead owns this backend part of C48. Generate pairs at
publication, keep per-dataset reads bounded, and reuse the existing canonical
haversine, date-gap and ranking helpers. Use a versioned explicit owner ledger;
missing aliases exclude the project and appear in generation coverage.

A 3D Cartesian grid on the Earth sphere supplies a conservative neighbor search,
including across the date line and near the poles. Exact haversine decides <25 mi.
No new dependency or route-service call is needed. F30 stages pair records before
activation; F19 consumes their paged API in its subsequent owned PR.
