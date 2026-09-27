"""Read-only generation/coverage report: python -m national_pairs."""
import json
from time import perf_counter

from national.build import load_snapshot
from national_pairs.build import generate

snapshot = load_snapshot()
start = perf_counter()
result = generate(snapshot)
print(json.dumps({**result["coverage"], "generation_seconds": round(perf_counter() - start, 3)}, indent=2))
