# F19: Fit the Time overview to the lower 48

**Context.** C49/F49 adds located Alaska and Hawaii projects. The Time overview fits the min/max of every located
project, so a Honolulu or Kenai Peninsula point would shrink the contiguous US to a corner of the default view.
History made the same change in `F37-overview-fit.md` (#280).

**Choice.** The overview fits located projects inside a lower-48 coordinate box whenever any exist, and all of them
otherwise. Every point is still drawn; a scope (for example the state of Alaska) still fits its own points through
`scopeBox`. On the national snapshot with F49 applied, exactly the 9 Alaska/Hawaii centers fall outside the box.

**Undo.** Fit `located` again in `TimeView`'s `bbox`.
