# F05: Common Ground story attribute and retired map controls

## Context
The sticky truck scroll used `data-gridbridge-story` after the rename to Common
Ground. Hidden "01 The road / 02 The network" controls remained in the hero even
though the map toggle was retired.

## Options
1. Leave the old attribute and hidden controls.
2. Rename the story hook to `data-common-ground-story` and drop the dead map
   toggle markup.

## Choice
Option 2 for the controls. Keep both `data-common-ground-story` and
`data-gridbridge-story` on the story root so the standalone HTML exporter
(`web/scripts/export-landing.cjs`, outside F05 owns) still finds the node.

## Undo
Restore the hidden `sceneControls` block in `HeroScene.tsx` and drop
`data-common-ground-story`.
