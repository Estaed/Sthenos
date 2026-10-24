# Blueprint — Calisthenics-App

The plan v1 is built from. Binding until changed on purpose (PRINCIPLES #5); the `blueprint`
skill writes and amends it. Constraints live in `AGENTS.md`, because every session must see them.
About 100 lines; a line that steers no decision is cut. An amendment rewrites the line it changes
and drops what the code now answers; it never appends a dated note (`blueprint` skill).

## What v1 is
A workout log for the gym on an Android phone, between sets, one hand: the whole day's program on
one screen, a set logged by tapping its cell, workout start and finish, a rest timer and an
independent timer, weeks with double progression, program editing, history, body weight. A public
site: anyone uses it without sync (data on their phone); Tarık adds his GitHub key and syncs to
his private data repo. English UI. Starts empty except for Tarık's current A/B/C program as the
seed program; no old logs come in.

Done when:
- wave 1 by Monday 2026-10-26: Tarık logs his first A Heavy session in the gym only in this app,
  start to Finish, and the day reaches `Calisthenics-Data`;
- a set at target is 1 tap, a set one short 2 taps;
- finishing week 1 builds week 2 with the progression rules below, right on his real numbers;
- (eye) on the phone the screens match `design/r6/screens.html` (screens 1, 2, 4-8).

## Not in v1
Swapping an exercise when a machine is busy; a starter template and sync without GitHub for other
people; native app; desktop layout; the old app's data. Full list: `notes.md` → *After v1*.

## Riskiest assumption
The rest timer reaches Tarık when it ends with the phone in his hand or on the bench. A PWA cannot
schedule a real alarm: Notification Triggers ended, a service worker lives ~5 min per event, page
vibration needs a visible page (`reports/2026-10-24-rest-alert-screen-off.md`, sources dated there).
So the main path is the screen kept awake (Wake Lock, re-acquired on return) with an in-page beep,
vibration and the visual change; the fallback is a service-worker notification at the end time.
Untested on his phone: `spikes/rest-alert/` (Pages) answers whether the fallback rings with the screen
off on Samsung Internet; if it does not, v1 says so in Settings and relies on keep-awake.

## Stack
Pantry's stack, so both apps share one style (they stay separate apps, Tarık 2026-10-24).

| Piece | Version | Why |
|---|---|---|
| Vanilla JS, HTML, CSS | — | no build step; one script per feature (Layout) |
| `tokens.css`, Archivo, Manrope | Tarik Base v6, copied unchanged | design language; fonts local, works offline |
| Service worker + manifest | — | installable PWA, offline in the gym |
| Wake Lock, Vibration, Web Audio, Notifications | built in | keep awake, rest and timer alerts (Riskiest assumption) |
| GitHub Contents API | REST, fine-grained token | sync to `Estaed/Calisthenics-Data`, the old app's sync carried over |
| Python + Playwright | 3.13.5 / 1.62.0 (this machine) | the acceptance test |

Rejected: native Kotlin or Flutter (Monday deadline; Pantry's PWA, sync and stack already exist; if
the phone feel falls short as in Pantry, native goes to *After v1* with the measured complaint); a
framework or bundler; IndexedDB (years of sets fit localStorage).

## Data (schema v5, one JSON document)
- **programs:** `{ id, name, days: [{ id, name, exercises: [{ id, name, kind: reps|time|check, sets,
  repMin, repMax, target, load, loadStep, bodyweight?, pair?, note? }] }] }`; `activeProgram`,
  `nextProgram` (used from the next week built). Pairs are adjacent exercises with the same `pair`.
- **weeks:** `{ n, program, startedAt, finishedAt?, days: { <dayId>: { startedAt?, finishedAt?,
  exercises: { <exId>: { load, target, sets: [{ r, at, pain? }] } } } } }`. A week copies its
  program's values when built, so editing a program never rewrites history.
- **body:** `[{ date, kg }]`. **settings:** rest (pair 90 s, between exercises 120 s), start rest
  after a log, heads-up 10 s, vibrate, sound, keep awake, default load step 2.5, theme.
- `calisthenics-data.json` v5 in the private repo; the v4 file moves to `archive/` untouched. The
  phone keeps a copy in localStorage and works offline; the token stays on the phone under its own key.

## Rules
- **Logging:** tap a cell = target; tap again = one less (down to 0, then empty); hold = one more.
  `time` steps by 5 s, `check` toggles. The one way to enter reps (Tarık: "1 özellik 2 farklı şekilde
  yapılmasın"); the pencil in the sheet edits load, never reps.
- **Next set** follows the pair alternation (A1 → B1 → A2 …); after a log the rest timer starts
  (pair rest inside a pair, the other after the pair's last set).
- **Finish week** (manual) builds the next week from `nextProgram`: every set at `repMax` → load +
  `loadStep`, target back to `repMin`; any short set → no change; short at the same load three weeks
  running → load −10 % rounded to `loadStep`. A day not done carries over with no progression.
  Bodyweight lifts progress on the added load.
- **Timers** are computed from start timestamps, never from counted ticks; the rest timer and the
  independent timer run at once.
- **Sync:** a day's edits push at Finish; an edit to a finished day or to a program pushes at once;
  a change older than 12 h goes on the next open. Pull on open, last-write-wins per document with
  the remote `sha` checked.
- **Pantry kcal:** read only from Pantry's `localStorage` key `pantry.v1` (same origin,
  `estaed.github.io`): weekly average kcal beside body weight; absent → the line is hidden.

## Layout
- `index.html` shell; `app/core.js` (data, state, routing, rules above), one `app/<feature>.js` per
  feature (`workout`, `timer`, `settings`, `sync`, `week`, `program`, `history`, `body`, `summary`),
  listed once each in the append-only `app/registry.js`; `app/base.css` for shared classes, each
  feature's classes carry its prefix. `tokens.css`, `fonts/`, `sw.js`, `manifest.json`, icons at the root.
- `legacy/`: the old app (`index.html`, its `tests/`) until v1 has run a week; then deleted.
- `tests/acceptance.py` (Playwright, 360 px, mocked GitHub API, served under `/Calisthenics-App/`)
  runs every `tests/test_<feature>.py`; a feature's tests reach its screen by route.
- `design/` source of truth; `reports/` research; `references/` inputs.
- Hermes' weekly summary is a Hermes skill in `D:/TarikOS/.brain/hermes-skills/`, reading the data
  repo after Finish week. No Hermes skill reads a data repo today; whether its GitHub access reaches
  `Calisthenics-Data` is not verified, so that task checks it first.
- Seams: routes `Cali.go(name, ...args)`; `Cali.log(day, ex, set, value)` is the only writer of a
  set; `Cali.timers` holds both timers; registry lines and the service worker cache name are bumped
  by the orchestrator at integration.

## Verification
- Gate: `python tests/acceptance.py` from the repo root; clean = every check PASS, exit 0. Written
  and first run in Task-00.
- Eye: Tarık on his phone (Samsung Internet, text size 1.0), or the emulator at 360 px, against
  `design/r6/screens.html`; intended breaks go to `design/deviations.md`.

## Decisions (2026-10-24, Tarık)
- PWA on Pantry's stack. Rejected: native now (above).
- Look: round 6 (02 result colour: done orange, short a partial ring, current an ink ring), tap-only
  logging. Rejected: the number strip, and both ways at once.
- Fresh data, same repo, v5 file. Rejected: migrating v4 ("eski verileri kullanmayacağız").
- The new app takes the old URL; the old one moves to `legacy/`. Rejected: a second URL.
- Public, sync optional per person. Rejected: Tarık-only with sync required.
- New programs: Settings → Programs (edit, duplicate, import a program JSON, use from next week).
  Rejected: editing only by Eko in the data repo (others could not).
- v1 includes body weight with a 7-day average, a note per exercise and a pain flag per set,
  Pantry's weekly kcal, and Hermes' weekly Discord summary. Rejected: exercise swap in v1.
