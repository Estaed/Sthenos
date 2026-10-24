# Task-04: Weeks and double progression
> **Execution:** agent `ultracode`
> *Why:* the numbers that drive Tarık's training decisions; a wrong load next week is the costliest bug.

**Lane**
- OWNS: `app/week.js`, `tests/test_week.py`
- MUST NOT TOUCH: `app/core.js` (Task-00), `app/workout.js` (Task-01), `app/timer.js` (Task-02), `app/settings.js`, `app/sync.js` (Task-03)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
Finish week builds the next week from `nextProgram` with Blueprint → Rules applied, and the week menu
(Week 1 ⌄) opens any past week read-only. Tarık sees on the summary what moves up and trusts it.

## Why
Double progression is the point of the log; it must be right on his real numbers.

## Acceptance
- [ ] Rules as Blueprint → Rules: every set at `repMax` → load + `loadStep`, target `repMin`; any short
  set → no change; short at the same load three weeks running → −10 % rounded to `loadStep`; a day not
  done carries over unchanged; bodyweight lifts progress on the added load; `time` and `check` rows copy.
- [ ] A week copies program values when built; editing the program afterwards changes no past week.
- [ ] Tests on a fixture of Tarık's program covering each rule, including the three-week stall and a
  missed day; the tests are written from the rules above, not from the implementation.
- [ ] Finish week asks for confirmation and is undoable until the next set is logged.
- [ ] (eye) the week menu and a past week shown read-only in the day sheet's look.

## Out of scope
- Programs list, editor, import (wave 2), deload settings (*After v1*).
