# F05: Landing hero truck scroll (RTL)

## Context
The marketing `/` page already lives under F05's `web/app/page.tsx` and renders `web/components/landing/`. That directory had no `owns` entry after the human `LandingPage_Basic` commit. The user asked to merge the attached `GridBridge_24df.html` hero copy and its right-to-left truck scroll into the Next.js landing.

## Options
1. Leave landing unowned and skip the ownership gate (fails CI).
2. Claim `web/components/landing/` under F05 (home route owner) and ship the RTL truck motion there.
3. Open a new feature id for marketing-only work.

## Choice
Option 2. Extend F05 `owns` with `web/components/landing/` via `[C24]` (frozen golden ownership expectation updated in the same contract). Keep the existing hero strings because they already match the landing e2e contract and the prior GridBridge HTML adaptation in `road-scene.js`; the attached `GridBridge_24df.html` was not present on the agent VM. Implement continuous right-to-left truck travel on the road canvas in `[FIX-F05]`. `prefers-reduced-motion` parks the truck; Pause freezes mid-route.

## Undo
Revert the owns amendment, the golden expectation, and restore the fixed-`xf` road scene.
