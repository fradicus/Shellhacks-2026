# F17: matting and mobilization scenario

## Authorization and context

On 2026-09-26 the user explicitly requested finishing F17, tailored to the sponsor conversations.
This bounded follow-on supersedes the original overnight elapsed-time gates for F17 only. Codex-local
adopts the feature's technical-lead role in its own worktree. Other feature assignments stay intact.

The [demo notes](../context/2026-09-26-demo-feedback.md) describe short-notice mobilization, scarce
equipment and rental idle time. The [panel notes](../context/2026-09-26-sponsor-panel.md) emphasize
access planning and estimator workflows before a site walk-down.

Public research checked 2026-09-26: [Dakota's services](https://dakotamats.com/about/) include access
planning, mat installation/removal and rentals; the company describes reducing freight cost and shipment
time through its supply relationships. This supports the workflow vocabulary, not any price or savings rate.

## Decision

Build a local, user-entered low/base/high worksheet for a PM considering moving mats or equipment
between two jobs. Preserve the original mobilization formula. Offer an optional holding-cost deduction
(idle days multiplied by a quoted daily total) so keeping a rented package between jobs has an explicit cost.
Coordination costs include inter-site freight, handling, inspection/cleaning and administration as applicable;
the worksheet asks for an aggregate incremental quote rather than inventing line-item rates.

Show published pair facts and review state separately from editable assumptions. Users can also work without
a pair when the database is unavailable. Keep all inputs empty initially, accept explicit zero, retain negative
results, and provide notes, a printable handoff and a reset. Date assumptions change only a displayed milestone
gap. They never establish an equipment-release date or a construction window.

No rental marketplace, automated dispatch, soil lookup, decay prediction, AI call or data mutation is part of F17.
The soil discussion informs a field-verification prompt only; there is no validated mat-lifetime model.

## Alternatives and reversal

A generic three-input calculator misses idle rental cost. A full estimate/marketplace needs rates, approvals and
operating data we do not have. The optional holding-cost deduction is a bounded extension using user inputs.
It can be removed within F17 without changing any shared data contract.
