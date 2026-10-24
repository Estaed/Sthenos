# Task-01: The workout day
**Status: DONE** — verified 2026-10-24, eye check pending: 1
> **Execution:** agent `ultracode`
> *Why:* the screen Tarık uses three times a week between sets; Monday's session runs on it.

**Lane**
- OWNS: `app/workout.js` (replaces Task-00's thin version), `app/workout.css`, `app/summary.js`, `app/summary.css`, `tests/test_workout.py`, `tests/test_summary.py`
- MUST NOT TOUCH: `app/core.js`, `app/progress.js` (Task-00 / Task-04; ask the orchestrator for a core change), `app/timer.js`, `app/alert.js` (Task-02), `app/settings.js`, `app/sync.js` (Task-03), `app/week.js` (Task-04)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
Tarık, sweaty, one hand, between sets: he sees the whole day (A/B/C tabs), last week's sets and the
4-week trend line beside each exercise, taps the set he just did, and the app moves to the next set
in the pair, starts the rest timer in the score bug and shows Undo. Start begins the session clock;
Finish shows the summary (duration, sets, short sets, what moves up next week) and Done records the day.

## Why
This is v1's main task; everything else supports it.

## Acceptance
- [x] Touch tests (`hasTouch`): one tap logs the target, two taps one short, hold adds one; the hold never
  opens a context menu or selects text; a second touch within 150 ms of the first is ignored as a bounce.
- [x] Done sets orange tint, short sets the partial orange ring at reps/target, the current set the ink
  ring; a logged set stays editable by the same taps; Undo restores the previous value and stays until
  the next log or 8 s.
- [x] Next set follows the pair alternation. After a log the rest starts from `Cali.settings` (pair rest
  inside a pair, the other after the pair's last set), computed from timestamps, and is scheduled at
  once with `Cali.alert.schedule('rest', endAt, 'rest')` (plus `headsup` 10 s before when on); the next
  log cancels it.
- [x] Start/Finish store `startedAt`/`finishedAt`; Finish → summary (screen 6, "moves up" from
  `Cali.progress`, tested with the stub and with a real result) → Done marks the day and emits `dayDone`.
  Wake Lock is held while a workout runs when the setting is on and re-acquired on visibility.
- [x] `Cali.go('day', { week, dayId, readOnly: true })` renders a past week's day with no taps.
- [x] Timed rows (stretch, walk) open `Cali.go('timer', { countdown: seconds })`.
- [x] Tests drive `Cali.now()`; they read last week's values in both states (none yet, present).
- [ ] (eye) screens 1, 2, 6, 7, 8 of `design/screens.html`, both modes; at 360×740 the whole of day A
  is visible without scrolling.

## Out of scope
- The timer screen and alert delivery (Task-02), settings (Task-03), week building and its menu (Task-04),
  notes, pain flag, body weight (wave 2).
