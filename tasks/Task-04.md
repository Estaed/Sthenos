# Task-04: Weeks and double progression
**Status: DONE** — verified 2026-10-24, eye check pending: 1
> **Execution:** agent `ultracode`
> *Why:* the numbers that drive Tarık's training decisions; a wrong load next week is the costliest bug.

**Lane**
- OWNS: `app/week.js`, `app/week.css`, `app/progress.js` (replaces Task-00's stub), `tests/test_week.py`, `tests/test_progress.py`
- MUST NOT TOUCH: `app/core.js` (Task-00), `app/workout.js`, `app/summary.js` (Task-01), `app/timer.js`, `app/alert.js` (Task-02), `app/settings.js`, `app/sync.js` (Task-03)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
`Cali.progress` applies Blueprint → Rules; Finish week builds the next week from `nextProgram` with it;
the week menu (Week 1 ⌄, added through `Cali.slot('dayheader')`) opens any past week read-only through
`Cali.go('day', { week, dayId, readOnly: true })`. Tarık sees on the summary what moves up and trusts it.

## Why
Double progression is the point of the log; it must be right on his real numbers.

## Acceptance
- [x] `tests/test_progress.py` is written from Blueprint → Rules before the code, one case per rule: all
  sets at target → target + 1; past `repMax` → load + `loadStep`, target `repMin`; a short set → no change;
  three short weeks at one load → −10 % rounded to `loadStep`, none at 0 added load; a day not done →
  unchanged and not counted toward the stall; bodyweight on added load; a `time` row all at target →
  target + 5 s, short → no change; `check` rows copy (Tarık 2026-10-24: Plank +5 s, as on screen 6).
- [x] A week copies program values when built; editing the program afterwards changes no past week.
- [x] Finish week asks for confirmation, emits `weekFinished`, and can be undone until the next `log` event.
- [x] Tests check routes and stored state, not Task-01's DOM.
- [ ] (eye) the week menu, and a past week shown read-only in the day sheet's look.

## Out of scope
- Programs list, editor, import (wave 2), deload settings (*After v1*).
