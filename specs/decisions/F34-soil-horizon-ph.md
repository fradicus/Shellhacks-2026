# FIX-F34: soil horizon pH with depth and units

Additive SSURGO `chorizon` join on the existing USDA Soil Data Access query.
Each component may carry horizons with `ph_h2o_1_to_1` (1:1 soil-water method),
`depth_top_cm` / `depth_bottom_cm`, and fixed `depth_unit: "cm"`.
Null pH remains visible; reversed depths and out-of-range pH fail closed.
Does not treat the board "Ph Area" note as a confirmed requirement (C15).
Site/route/conditions HTTP contracts are unchanged; only soil envelope data grows.
