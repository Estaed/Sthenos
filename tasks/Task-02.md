# Task-02: Independent timer and alerts
> **Execution:** agent `ultracode`
> *Why:* a rest or a timed stretch that ends unnoticed wastes the session; the alert path is v1's riskiest assumption.

**Lane**
- OWNS: `app/timer.js`, `app/timer.css`, `app/alert.js`, `sw-alert.js`, `tests/test_timer.py`, `tests/test_alert.py`
- MUST NOT TOUCH: `app/core.js` (Task-00), `app/workout.js` (Task-01), `app/settings.js`, `app/sync.js` (Task-03), `app/week.js`, `app/progress.js` (Task-04), `sw.js` (Task-00; the orchestrator adds one `importScripts('sw-alert.js')` line at integration)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
A timer screen (screen 4) separate from the rest timer: a countdown with presets (30 s, 1, 2, 4 min,
custom) and a stopwatch with laps, both running while Tarık is back on the workout, shown as a pill in
the top bar (`Cali.slot('topbar')`) that opens the screen. This task fills `Cali.alert`, which the rest
timer uses too: beep, vibration and the visual change while the page is visible; a notification from
the service worker as the fallback when it is not.

## Why
Blueprint → Riskiest assumption: keep-awake is the main path, the service-worker notification the fallback.

## Acceptance
- [ ] Countdown, stopwatch, laps, pause, reset, +1 min through `Cali.timers`; correct after the page was
  hidden for minutes (tests jump `Cali.now()`).
- [ ] `Cali.go('timer', { countdown })` starts a countdown with that duration.
- [ ] `Cali.alert(kind)` plays a beep (Web Audio, unlocked on the first tap) and vibrates when the
  settings allow, for kinds `rest`, `headsup`, `timer`, `test`.
- [ ] `Cali.alert.schedule(kind, endAt, tag)` posts `{ endAt, tag, kind }` to the service worker
  (`sw-alert.js`: waits with `event.waitUntil`, shows a `requireInteraction` notification with that tag);
  the page shows the same tag itself when it is awake at the end, so only one appears; `cancel(tag)`
  stops both. Design from `reports/2026-10-24-rest-alert-screen-off.md` → Recommended design.
- [ ] A Playwright test registers the real service worker, schedules a 2 s alert, and sees the
  notification with its tag; `cancel` before the end shows none.
- [ ] `Cali.alert.requestPermission()` asks once; never on load (Task-03 puts the button in Settings).
- [ ] (eye) screen 4 and the top-bar pill (screen 2) of `design/r6/screens.html`, both modes.

## Out of scope
- Push servers, Notification Triggers, periodic sync, the silent-audio keep-alive (it pauses music).
