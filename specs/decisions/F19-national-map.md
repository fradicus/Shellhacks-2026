# F19 national points on the existing time map

The user explicitly asked this Codex session to finish issue #139. No open F19 implementation PR
was present at claim time. This bounded follow-up owns only F19 paths and supersedes the original
F19 exclusion of national display; other regional producer and shared-loader assignments stay intact.

Reuse F31's active national reader and F19's renderer. Display confirmed nonlegacy national centers
alongside legacy projects, preserving canonical IDs, owners, source statuses, date precision and
location evidence. Keep stored legacy pairs unchanged. National records are discovery points and
are not newly computed overlap pairs. Exclude national legacy projections to prevent duplication.

Use the national reader's existing map bound and disclose truncation or unavailability. National
unlocated records remain accessible through the explorer; the time drawer does not claim to contain
all national records. Do not convert month/year milestones into exact dates or inferred completion.

Undo by reverting this follow-up; no database or source data changes are required.

C25 merged during this implementation. This increment delivers issue #139's accepted confirmed
projection, including independent legacy/national failure states. C25's new official/candidate tiers
await additive shared producer/loader/read contracts; no unpublished tier is inferred here. Its broader
state filters and unified unlocated search remain a separate follow-up; the existing explorer provides
those controls now. This PR does not claim full C25 acceptance or regional data completion.

## Verification receipt — 2026-09-27 UTC

- Final API read: Atlas dataset `d4e5855c29a113ed36e4e743fb2c86d6d513d8ae`, 1,286 national
  records, 414 located, 872 unlocated, no map truncation. The main view draws 424 records:
  345 confirmed nonlegacy national points plus 79 legacy points, with 183 legacy records unlocated.
  Legacy current-version selection differs from the national legacy projection; the two located totals
  are not interchangeable. National points retain the native ID and source/review evidence.
- Representative point: `iso-ne:1617`, Chelsea, Vermont Electric Power Company, latitude
  43.96074042841999 / longitude -72.47113915797026, confirmed source site; milestone `2018-01`
  remains month precision and raw text `2018-01-01T00:00:00` is separately displayed.
- Local Atlas-backed app: `http://localhost:3019/time`; Playwright Chromium at 1440×1000 and
  390×844 verified the overview, Chelsea selection/owner/month interval/source links, 2D, and
  Home → Overlaps → National explorer → Overlaps. Main interaction run had zero page errors.
  Disabled WebGL and blocked basemap requests both retain mobile project selection and evidence.
  Screenshots were visually inspected. This is local integration evidence, not hosted deployment.
- Headless Chromium requestAnimationFrame averaged approximately 53 fps over five seconds at
  1440×1000. Headed demo-laptop performance remains unmeasured for this batch.
- Explicit mocked page probes pass independent legacy, national and pair outages, both-unavailable
  and valid-empty states. Two committed Node 24 adapter tests cover legacy mirror exclusion,
  unapproved/null/invalid centers and exact/month/year/unknown milestone semantics.
- Final required commands: `uv run ruff check .` passed; `uv run pytest -q` passed with 490 passed,
  1 skipped; `npm run lint`, `npm run typecheck`, `DATA_MODE=fixture npm run build` passed.
  Existing Big Shoulders fallback-font warning remains. Spec lint (32 features), F19 ownership,
  whitespace and diff scope/secrets review passed. No source data, secrets or read-only paths changed.
