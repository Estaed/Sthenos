# Task-00: Shell, data core and the thinnest path
> **Execution:** agent `ultracode`
> *Why:* every wave-1 feature builds against the core, the routes and the gate laid here.

**Lane**
- OWNS: `index.html`, `app/core.js`, `app/registry.js`, `app/base.css`, `app/workout.js` (thin version), `tokens.css`, `fonts/`, `sw.js`, `manifest.json`, `tests/acceptance.py`, `tests/test_core.py`, `tests/fixtures/`, `tools/seed_program.py`, `legacy/`
- MUST NOT TOUCH: `design/`, `docs/`, `notes.md`
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: none

## Goal
The new app replaces the old one at the same URL: Tarık opens his home-screen icon and sees day A
of his program as the round-6 day sheet (cells only, no styling polish needed yet), taps a set,
reloads, and the set is still there. The old app keeps working at `legacy/`. Built for Tarık on
his Samsung phone, and for the four parallel builders who come next: the seams below must let each
of them add a feature without editing another's file.

## Why
Retires the plumbing risk (shell, storage, routes, service worker on a GitHub Pages sub-path) and
gives the wave one green gate to build against.

## Acceptance
- [ ] Old app moved with history (`git mv`) to `legacy/` (its `index.html`, `tests/`); it still loads
  at `/Calisthenics-App/legacy/` with its `cali4_*` data untouched.
- [ ] `app/core.js` holds schema v5 (Blueprint → Data), defaults for every setting, routes
  (`Cali.go`), `Cali.log(dayId, exId, setIndex, value)` as the only writer of a set, the logging rule
  (tap = target, again = one less down to 0 then empty, hold = one more; `time` ±5 s; `check` toggles),
  the pair alternation for "next set", `Cali.timers` (start timestamps, both timers at once,
  `Cali.now()` injectable for tests), and a no-op `Cali.alert(kind)` hook that Task-02 fills.
  Storage key `cali.v5`, token key `cali.sync`; nothing writes `cali4_*` or `pantry.*`.
- [ ] `app/registry.js` lists one script per feature (append-only); `index.html` loads them; a top-bar
  slot API lets the timer pill and the settings button be added by their own features.
- [ ] `tools/seed_program.py` converts the v4 file's current program (plans → days → exercises,
  pairs, ranges, loads, steps, notes) into a v5 document with that program and no weeks, written to
  `.tmp/`; it never pushes. Tests use a fixture built the same way, not personal data.
- [ ] Service worker caches the shell with a versioned cache name and deletes old caches on activate
  (`knowledge/concepts/pwa-service-worker-onbellek-guncelleme.md`); manifest `start_url` relative.
- [ ] `tests/acceptance.py`: serves `D:/Projects` and opens `/Calisthenics-App/` at 360 px with a mocked
  GitHub API, runs every `tests/test_*.py`, exits non-zero on any failure; tests drive `Cali.now()`,
  never real time; tests write only to `.tmp/`. Checks here: no console errors; tap Pull-up set 1 →
  6 stored; reload → still 6; tap again → 5; hold → 6.
- [ ] (eye) day A renders in the round-6 structure (`design/r6/screens.html` screen 7) on a 360 px screen.

## Out of scope
- Look polish, rest timer, start/finish, summary (Task-01); timer (Task-02); settings and sync
  (Task-03); weeks and progression (Task-04).

Fixed: `Cali.go`, `Cali.log`, `Cali.timers`, `Cali.alert`, `Cali.now`, storage keys `cali.v5` / `cali.sync`, `app/registry.js`.
