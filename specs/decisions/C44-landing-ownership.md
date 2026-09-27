# C44: landing ownership under F05

Context: `web/components/landing/` already ships on `main` for the marketing home, but F05
`owns` did not list it after the map-retirement rename. FIX work for the truck scroll and
Common Ground brand reveal needs an explicit prefix.

Options: leave landing unowned (ownership CI blocks FIX-F05), or add
`web/components/landing/` to F05 and update the frozen golden expectation.

Choice: add `web/components/landing/` to F05 `owns` and the golden owns assertion. Keep
existing `web/app/map/`, map, and list prefixes for the retirement track.

Undo: remove the landing owns entry and restore the prior golden assertion.
