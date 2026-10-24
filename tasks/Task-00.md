# Task-00: Shell, data core and the thinnest path
**Status: DONE** — verified 2026-10-24, eye check pending: 1
> **Execution:** agent `ultracode`
> *Why:* every wave-1 feature builds against the core, the routes, the events and the gate laid here.

**Lane**
- OWNS: `index.html`, `app/core.js`, `app/registry.js`, `app/base.css`, `app/default-program.js`, `app/workout.js` (thin version, replaced by Task-01), `app/progress.js` (stub, replaced by Task-04), `tokens.css`, `fonts/`, `sw.js`, `manifest.json`, `tests/acceptance.py`, `tests/test_core.py`, `tests/fixtures/`, `tools/default_program.py`, `legacy/`
- MUST NOT TOUCH: `design/`, `docs/`, `notes.md`, `spikes/`
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: none

## Goal
The new app replaces the old one at the same URL: Tarık opens his home-screen icon and sees week 1,
day A of his program as the round-6 day sheet (no polish yet), taps a set, reloads, and the set is
still there. The old app keeps working at `legacy/` without harming the new one. Built for Tarık on
his Samsung phone, and for the four parallel builders who come next: every seam they need is named
under Fixed, so none of them edits another's file.

## Why
Retires the plumbing risk (shell, storage, routes, service worker on a GitHub Pages sub-path) and
gives the wave one green gate to build against.

## Acceptance
- [x] Old app moved with history (`git mv`) to `legacy/` (its `index.html`, `tests/`). Its block that
  unregisters every service worker and deletes every cache on load (old `index.html` ~4068-4074) is
  removed, its own `sw.js` registration points inside `legacy/`, and a test opens `/legacy/` and then
  checks the new app still loads offline. Legacy refuses a document with `_version > 4` (it already does;
  a test proves it on a v5 fixture).
- [x] `app/core.js`: schema v5 with `_version: 5` (Blueprint → Data); defaults for every setting;
  first open builds week 1 from `activeProgram`; storage key `cali.v5`; nothing writes `cali4_*` or
  `pantry.*`. Everything under Fixed exists and is documented in a header comment.
- [x] `app/default-program.js`: Tarık's current A/B/C program as the built-in default, generated once by
  `tools/default_program.py` from the v4 file's plans (days, exercises, pairs, ranges, loads, steps,
  notes; kinds reps/time/check); no logs.
- [x] Logging rule in `Cali.log`'s caller helper `Cali.tap(dayId, exId, i)` / `Cali.hold(...)`: tap =
  target, again = one less down to 0 then empty, hold = one more; `time` ±5 s; `check` toggles.
- [x] `app/registry.js` lists each feature's script and stylesheet (append-only); `index.html` loads
  them; the top bar and the day header take slot items from features.
- [x] Service worker caches the shell with a versioned cache name and deletes only its own old caches
  (`knowledge/concepts/pwa-service-worker-onbellek-guncelleme.md`); manifest `start_url` relative.
- [x] `tests/acceptance.py`: serves `D:/Projects`, opens `/Calisthenics-App/` at 360×740 with
  `hasTouch`, a mocked GitHub API, runs every `tests/test_*.py`, non-zero on any failure; tests drive
  `Cali.now()`, never real time, and write only to `.tmp/`. Here: no console errors; touch-tap Pull-up
  set 1 → 6 stored; reload → 6; tap again → 5; hold → 6; first open builds week 1.
- [ ] (eye) day A renders in the round-6 structure (`design/r6/screens.html` screen 7) at 360 px.

## Out of scope
- Look polish, rest timer, start/finish, summary (Task-01); timer and alerts (Task-02); settings and
  sync (Task-03); weeks and progression rules (Task-04).

Fixed: `Cali.go(route, args)` with routes `day {week, dayId, readOnly}`, `timer {countdown}`, `settings`,
`summary {dayId}`; `Cali.log(dayId, exId, i, value)` (the only writer of a set); `Cali.tap`/`Cali.hold`;
`Cali.on(event, fn)` / `Cali.emit` with events `log`, `change`, `dayDone`, `weekFinished`;
`Cali.settings.get(key)` / `set(key, value)`; `Cali.timers` (start timestamps, several at once);
`Cali.alert(kind)` with kinds `rest`, `headsup`, `timer`, `test`, plus `Cali.alert.schedule(kind, endAt, tag)`,
`Cali.alert.cancel(tag)`, `Cali.alert.requestPermission()` (no-op stubs here, Task-02 fills them);
`Cali.progress(weekExercise, history)` returning `{ load, target, reason }` (stub "no change" here,
Task-04 fills it); `Cali.slot('topbar' | 'dayheader', node)`; `Cali.now()`; set cells carry
`data-set="<dayId>:<exId>:<i>"`; storage keys `cali.v5` / `cali.sync`.
