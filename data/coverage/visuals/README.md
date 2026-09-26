# F15 component screenshot evidence

These four captures render the real `CoverageView` TSX and feature CSS to standalone HTML, then open that file in
installed Chrome. No web server was launched.

| State | 1440 px | 390 px |
|---|---|---|
| Real committed corpus | `real-1440.png` | `real-390.png` |
| Coverage unavailable | `unavailable-1440.png` | `unavailable-390.png` |

The real render uses `data/coverage/coverage.json`, `data/sources/sources.json`, and `latestRun: null`; the last value
exercises the honest `N/A` state. The unavailable render passes an empty coverage array. All four captures had no page
or console errors and no horizontal overflow. They were visually inspected at their named viewport widths.

Component SHA-256: `1c25940f86322dc168a481ad72d11b6557edfd2af0def6c2fdf62b88f4e40983`
CSS SHA-256: `8cced0ba1dbb04dfa59401cd4eb59f775ff7494cb9cd4818de9520cfe1fe5d1f`

This is component-only visual evidence. CI exercises the actual Next route; these images do not establish a local
route preview, Atlas connectivity, or a deployed production page.
