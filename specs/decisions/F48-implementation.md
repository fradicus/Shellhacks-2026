# F48 implementation

Codex local / technical-lead owns this backend part of C48. Generate pairs at
publication, keep per-dataset reads bounded, and reuse the existing canonical
haversine, date-gap and ranking helpers. Use a versioned explicit owner ledger;
missing aliases exclude the project and appear in generation coverage.

A 3D Cartesian grid on the Earth sphere supplies a conservative neighbor search,
including across the date line and near the poles. Exact haversine decides <25 mi.
No new dependency or route-service call is needed. F30 stages pair records before
activation; F19 consumes their paged API in its subsequent owned PR.

## Initial measured snapshot
On parent `3606762`, assembled snapshot: 8,058 records; 2,019 eligible projects;
1,874 in-service/cancelled, 262 legacy, 3,479 unusable location/review and 424
unresolved-owner exclusions. Result: 1,240 provisional pairs (2 with both locations
confirmed, 1,238 tentative), 3,947 exact distance comparisons, generation 0.082 s
excluding snapshot loading on the local Mac. These are source-bounded counts,
not a nationwide completeness claim or a page-load benchmark.

The generator refuses more than 100,000 pairs instead of silently truncating;
publication must preserve the previous dataset on that failure. The read API caps
pages at 50 and pins all joins to the requested active dataset.
