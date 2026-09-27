# F05: Landing hero truck scroll (RTL)

## Context
The marketing `/` page already lives under F05's `web/app/page.tsx` and renders `web/components/landing/`. That directory had no `owns` entry after the human `LandingPage_Basic` commit. The user asked to merge the attached `GridBridge_24df.html` hero copy and its right-to-left truck scroll into the Next.js landing.

## Options
1. Leave landing unowned and skip the ownership gate (fails CI).
2. Claim `web/components/landing/` under F05 (home route owner) and ship the RTL truck motion there.
3. Open a new feature id for marketing-only work.

## Choice
Option 2. Extend F05 `owns` with `web/components/landing/` via `[C24]` (frozen golden ownership expectation updated in the same contract). Hero copy comes from the reference HTML (`docs/GridBridge-reference.html` in the Project store): final overlay brand `GridBridge`, tag `Every mile. Connected.`, primary CTA `See how it works`, scroll hint `Scroll`; scroll-story beats `Same roads.` / `One network.` (with their reference subs) surface as road/network scene captions. How / corridor / finale section copy also follows the reference. The HTML ghost CTA `Replay` is omitted (no replayable scroll-story on the Next landing). Continuous right-to-left truck travel stays on the road canvas. Entrance sequence: truck-only first (~1.6s, brand/tag/CTA/chrome at opacity 0), then `GridBridge` rises in (blur + translate + tracking settle, warm/black system — no purple glow), then tag + CTA, then scroll hint and scene chrome. `prefers-reduced-motion` skips the hold and shows the full overlay. Pause freezes mid-route. Landing e2e caption expectations in `tests/e2e/` are F07-owned and need a follow-up `[FIX-F07]`.

## Undo
Revert the owns amendment, the golden expectation, and restore the fixed-`xf` road scene.
