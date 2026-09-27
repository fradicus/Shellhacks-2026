# C24: Claim marketing landing under F05

## Context
`web/components/landing/` shipped on `main` without an `owns` entry. FIX work on the hero truck scroll needs a home, and `tests/golden/test_ownership.py` hardcodes F05's owns list (frozen).

## Choice
Add `web/components/landing/` to F05 owns and update the golden expectation to match. Implementation of the RTL truck scroll stays in `[FIX-F05]`.

## Undo
Revert this contract and the FIX that depends on it.
