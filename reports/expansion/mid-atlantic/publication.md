# Mid-Atlantic publication checkpoint

The 275-record release is published in Atlas and visible in the local app reading Atlas. This receipt does not assert a separate production-host deployment.

- Data PR: [157](https://github.com/fradicus/Shellhacks-2026/pull/157), merged `19fa5a17045455ac71f4f3316caaab6b3ed911b1` at 2026-09-27T03:58:26Z.
- Required CI: [36292642654](https://github.com/fradicus/Shellhacks-2026/actions/runs/36292642654), passed on final PR head `4c0977ccf74cf0692316e49e61ed10d8c404e0f5`: ruff, 563 tests passed / 1 skipped, web lint/typecheck/build, spec lint and ownership.
- Sole-writer load: [36292952034](https://github.com/fradicus/Shellhacks-2026/actions/runs/36292952034), succeeded. Active dataset equals the merged SHA above.
- [Live API receipt](live-api-receipt.json), checked 2026-09-27T04:00:28.260887+00:00: all 275 IDs and all projected fields, coordinates, reviews and 768 events match the reviewed release. Every confirming review binds the exact published location inputs. Whole-release hash remains `4d62455a61f698eda04fce8bf25ec18cb4886a8030a3c7445f8b1c43f651871b`.
- All 1,303 immediately prior API records are exactly preserved, including Florida's concurrently published 17 records and New England's 345 confirmed locations.
- National totals: 1,578 records, 681 located, 897 unlocated. This batch adds 266 located and nine unlocated records, at 65 distinct canonical map positions. Most additions are historical; see [release](release.md) for lifecycle cohorts and coverage gaps.

## Browser observations

[Browser receipt](live-browser-receipt.json) records actual localhost:3000 UI observations against the active Atlas dataset. All six state filters match the API counts in the release table.

- [Mickleton site](live-mickleton-map.png): b3867.1 is a planned circuit-switcher upgrade with its map point, ACE owner code, 2029 milestone and original PJM source hash visible.
- [North Philadelphia–Master pair](live-complete-pair.png): b3907.1 retains complete endpoint coverage and explains the canonical mean point. Both endpoint identities are visible in the evidence panel.
- [Pannell review](live-pannell-review.png): 23-T-0660 retains unknown current status and explicitly partial endpoint coverage. Expanded evidence shows original EPSG:3857 geometry, source hashes and exact confirming review.
- [Existing time map](live-time-map.png): 691 total located projects drawn, including 612 confirmed national projects, with 897 national records unlocated. The concurrent F19 integration supplies this view; F38 does not invent overlap pairs.
- The responsive override requested 390 × 844, but the observed explorer viewport stayed 839 pixels wide. It had no horizontal overflow at that width. Mobile verification is **not claimed**; the override was reset.

## Validation and remaining scope

The final isolated local pipeline run also passed: 563 tests / 1 skipped in 943.83 seconds. Earlier local runs hit disk exhaustion and a shared pytest temporary-directory failure; those are failures, not passing evidence. Only disposable outputs in completed F38 worktrees were removed. Source downloads and reviews were preserved. A reviewer found no validation algorithm change in the concurrent rebase; local resource pressure and repeated full-dataset assembly explain the longer runs.

Optional legacy e2e and Azure testgen failed on the data PR. Required CI passed. These optional outcomes do not justify a claim that all checks were green.

No nationwide F38 completion marker is added. DC remains zero in this batch, nine admitted records remain unlocated, many eligible PJM rows remain deferred, and NY acquisition is bounded rather than statewide-complete. Resume by selecting another bounded primary-source cohort, preserving these reviewed active records, and repeating independent review before publication.
