# F37: Fit the History overview to the lower 48

**Context.** C49/F49 adds located Alaska and Hawaii projects. The History overview fits the min/max of every drawn
point, so a Honolulu or Kenai Peninsula point would shrink the contiguous US to a corner of the default view.

**Choice.** The fit uses points inside a lower-48 coordinate box whenever any exist, and all points otherwise, so a
query or origin that leaves only Alaska or Hawaii still fits them. Every point is still drawn. On the national
snapshot with F49 applied, exactly the 9 Alaska/Hawaii centers fall outside the box.

**Undo.** Fit `all` again in `HistoryView`'s `bbox`.
