# C34: Shared Time and History presentation helpers

The user explicitly launched issue #190 on 2026-09-27. This bounded cleanup supersedes
F37's deferral of shared presentation helpers. It preserves both scenes and their data semantics.

## Ownership and delivery

Codex local takes the frontend-engineer role for this F19/F37 cleanup. No F19 or F37 PR
was open when the claim was recorded on #190. Other sessions must not start these
features until the sequential cleanup claims finish. Existing F30/F31 and data claims
are unchanged. Original overnight elapsed gates are historical for this explicit request.

1. F19 extracts reusable rendering primitives, matching styles and small shared controls
   under its existing `web/components/time/` ownership, and adopts them in Time.
2. F37 imports those helpers and removes matching implementations from History.
3. Each step uses its own feature worktree and PR, with the repository checks. Close
   #190 only when both consumers are validated. Historical contract/award research
   remains deferred; this cleanup does not satisfy that separate F37 requirement.

## Shared interface

- Pure color/easing/projection helpers and point/line buffer setup and disposal may be
  shared. Shader code, dash/opacity choices and scene-specific events stay explicit.
- Shared CSS must preserve selector specificity, cascade order, breakpoints, palettes,
  reduced motion and accessible focus. Use scoped CSS modules; no global map reset.
- Small identical controls and DOM helpers may be shared when that removes actual
  duplication. Keep planning milestones and historical events in their existing views.
- History already imports F19's time math. This extends that same dependency direction;
  no reverse import, new dependency, universal scene framework or new owned path is needed.
- Stored pairs, source evidence, eligibility, date precision and unknowns are unchanged.
  Performance work and data loading are outside this refactor.

## Acceptance and rollback

Run every repository check and focused helper checks. Compare desktop and 390px views,
selection, 2D/3D, keyboard access, reduced motion, fallback states and navigation re-entry.
Report actual code reduction and observed checks; no unmeasured frame-rate claim.
Revert F37 adoption before reverting F19's shared exports to avoid breaking imports.
