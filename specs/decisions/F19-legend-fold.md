# F19: A collapsible legend in the scene dock

**Context.** The user asked for the legend card to be collapsible and graceful. The dock mixes reference content
read once (the legend and gesture hint) with controls used constantly (2D/3D, Overview, the sheet slider).

**Choice.** Only the reference half folds. `LegendFold` wraps the legend and hint in a native `<details>` (keyboard
and screen-reader behavior for free); the controls sit outside it. The dock is anchored at its foot, so folding
shrinks it from the top and the controls never move. Height animates through `::details-content` with
`interpolate-size` where supported, instantly elsewhere and under reduced motion. The choice is remembered in
`localStorage` (`gridbridge.legend`), written only on the reader's click; blocked storage leaves it open. It starts
open so a first-time reader learns the symbols. The existing narrow-screen and open-detail rules now hide the whole
fold. History can adopt the same component.

**Undo.** Remove `LegendFold` from the dock and restore `.legend`/`.hint` in the hide rules.
