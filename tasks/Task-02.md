# Task-02: Independent timer and alerts
> **Execution:** agent `ultracode`
> *Why:* a rest or a timed stretch that ends unnoticed wastes the session; the alert path is v1's riskiest assumption.

**Lane**
- OWNS: `app/timer.js`, `app/timer.css`, `app/alert.js`, `tests/test_timer.py`, `tests/test_alert.py`
- MUST NOT TOUCH: `app/core.js` (Task-00), `app/workout.js` (Task-01), `app/settings.js`, `app/sync.js` (Task-03), `app/week.js` (Task-04), `sw.js` (Task-00; the orchestrator merges the notification handler you specify)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
A timer screen (screen 4) separate from the rest timer: a countdown with presets (30 s, 1, 2, 4 min,
custom) and a stopwatch with laps, both running while Tarık is back on the workout, shown as a pill in
the top bar that opens the screen. `Cali.alert(kind)` is implemented here and used by the rest timer
too: beep, vibration, the visual change, and a notification as the fallback when the page is hidden.

## Why
Blueprint → Riskiest assumption: keep-awake is the main path, the service-worker notification the fallback.

## Acceptance
- [ ] Countdown, stopwatch, laps, pause, reset, +1 min; both computed from timestamps through `Cali.timers`;
  correct after the page was hidden for minutes (test with `Cali.now()` jumps).
- [ ] `Cali.go('timer', { countdown })` starts a countdown with that duration (the stretch and walk rows).
- [ ] `Cali.alert`: in-page beep (Web Audio, unlocked on the first tap) and `navigator.vibrate` when the
  settings allow; when the page is hidden at the end time, a notification (`requireInteraction`, one tag
  per timer so the page and the service worker never show two). Follow
  `reports/2026-10-24-rest-alert-screen-off.md` → Recommended design; specify the `sw.js` handler for the
  orchestrator (end time sent from the page, `event.waitUntil`).
- [ ] Notification permission is asked once, from Settings or the first timer start, never on load.
- [ ] Tests drive `Cali.now()`; real waits are not used.
- [ ] (eye) screen 4 and the top-bar pill (screen 2) of `design/r6/screens.html`, both modes.

## Out of scope
- Push servers, Notification Triggers, periodic sync, the silent-audio keep-alive (it pauses music).
