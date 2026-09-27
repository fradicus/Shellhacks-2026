# F37: part 1 over documented events already in the active datasets

Date: 2026-09-27. Requested by the user in a local Claude Code session ("implement the frontend redesign for
history ... improve the spec ... keep to the core idea").

## Context

F37 was specified (C19) with contract/award discovery as the first step. Measuring the assembled national snapshot
showed the active dataset already documents planned and actual events for located projects (PJM register date
fields, ISO-NE register status, Florida DEP certifications), while no public award/contract record with an
evidenced project link exists yet.

## Options

1. Wait for award/contract sourcing before building the page.
2. Build the page over the documented events already published, and keep award discovery as a visible, unmet part 2.
3. Build over a new committed history corpus under `data/history/`.

## Choice

Option 2. It keeps C19's core idea (a 3D sibling of `/time` with a scrubbable year plane and sourced events), adds no
storage or writer, and does not duplicate records. Option 3 would copy published records into a second place.

F19's layer draws pillars/beads/pairs; History needs event glyphs, plan→actual threads, a movable plane and ground
ripples. F37 imports F19's pure time math and keeps a small history layer inside its own paths instead of editing or
forking F19's renderer.

## Undo

Delete `web/app/history/`, `web/components/history/`, `web/lib/history/`. No data, schema or other route changes.
