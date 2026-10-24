# Task-01: The workout day
> **Execution:** agent `ultracode`
> *Why:* the screen Tarık uses three times a week between sets; Monday's session runs on it.

**Lane**
- OWNS: `app/workout.js`, `app/workout.css`, `app/summary.js`, `tests/test_workout.py`, `tests/test_summary.py`
- MUST NOT TOUCH: `app/core.js` (Task-00; ask the orchestrator for a core change), `app/timer.js` (Task-02), `app/settings.js`, `app/sync.js` (Task-03), `app/week.js` (Task-04)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
Tarık, sweaty, one hand, between sets: he sees the whole day (A/B/C tabs), last week's sets and the
4-week trend line beside each exercise, taps the set he just did, and the app moves to the next set
in the pair, starts the rest timer in the score bug and shows an Undo. Start begins the session clock;
Finish shows the summary (duration, sets, short sets, what moves up next week) and Done records the day.

## Why
This is v1's main task; everything else supports it.

## Acceptance
- [ ] Logging follows `Cali.log`'s rule; one tap logs the target, two taps log one short; hold adds one.
  Tap counts checked in a test.
- [ ] Done sets orange tint, short sets the partial orange ring at reps/target, the current set the
  ink ring; a set changed later stays editable by the same taps; Undo restores the previous value.
- [ ] Next set follows the pair alternation; the rest timer starts after a log (pair rest inside a
  pair, the other after the pair's last set) from settings defaults, computed from timestamps, and
  calls `Cali.alert('rest')` at zero; heads-up at 10 s when on.
- [ ] Start/Finish store `startedAt`/`finishedAt`; Finish → summary (screen 6) → Done marks the day
  finished (Task-03's sync pushes on that event). Wake Lock is held while a workout runs when the
  setting is on, and re-acquired on return to the page.
- [ ] Timed rows (stretch, walk) open `Cali.go('timer', { countdown: seconds })`.
- [ ] Tests drive `Cali.now()`; they read last week's values in both states (none yet, present).
- [ ] (eye) screens 1, 2, 6, 7, 8 of `design/r6/screens.html`, both modes, at 360 px; the whole day
  visible without scrolling on day A.

## Out of scope
- The timer screen and alerts' implementation (Task-02), settings (Task-03), week building (Task-04),
  notes, pain flag, body weight (wave 2).
