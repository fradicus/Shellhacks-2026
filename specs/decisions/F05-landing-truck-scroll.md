# F05: Landing hero truck scroll (RTL)

## Context
The marketing `/` page already lives under F05's `web/app/page.tsx` and renders `web/components/landing/`. That directory had no `owns` entry after the human `LandingPage_Basic` commit. The user asked to merge the attached `GridBridge_24df.html` hero copy and its right-to-left truck scroll into the Next.js landing.

## Options
1. Leave landing unowned and skip the ownership gate (fails CI).
2. Claim `web/components/landing/` under F05 (home route owner) and ship the RTL truck motion there.
3. Open a new feature id for marketing-only work.

## Choice
Option 2. Extend F05 `owns` with `web/components/landing/` via `[C24]` (frozen golden ownership expectation updated in the same contract). Hero copy comes from the reference HTML final overlay (`docs/GridBridge-reference.html` in the Project store): brand `GridBridge`, tag `Every mile. Connected.`, primary CTA `See how it works`, scroll hint `Scroll`. The HTML ghost CTA `Replay` is omitted (no replayable scroll-story on the Next landing). Continuous right-to-left truck travel stays on the road canvas. `prefers-reduced-motion` parks the truck; Pause freezes mid-route. Landing e2e heading expectations in `tests/e2e/` are F07-owned and need a follow-up `[FIX-F07]`.

## Undo
Revert the owns amendment, the golden expectation, and restore the fixed-`xf` road scene.
