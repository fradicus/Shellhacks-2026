# F36 browser evidence

The Playwright suite intercepts every operations API. Its screenshots are clearly named `mocked-*` and exercise
synthetic test-only responses; they are layout and interaction evidence, not live provider evidence. The production
page contains no fixture fallback. Unmocked initial-state capture may be added by the integration owner after the
route is deployed and must retain the provider states actually returned.
