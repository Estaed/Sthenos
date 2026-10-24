# Blueprint — Sthenos

The plan v1 is built from. Binding until changed on purpose (PRINCIPLES #5); the `blueprint`
skill writes and amends it. Constraints live in `AGENTS.md`, because every session must see them.
About 100 lines; a line that steers no decision is cut. An amendment rewrites the line it changes
and drops what the code now answers; it never appends a dated note (`blueprint` skill).

## What v1 is
A workout log for the gym on an Android phone, between sets, one hand: the whole day's program on
one screen, a set logged by tapping its cell, workout start and finish, a rest timer and an
independent timer, weeks with double progression, program editing, history, body weight. A public
site: anyone uses it without sync (data on their phone); Tarık adds his GitHub key and syncs to
his private data repo. English UI. Ships Tarık's current A/B/C program as the built-in default
program (week 1 is built from it on first open); no old logs come in.

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
Tested 2026-10-24 on Tarık's phone (Samsung Internet, test page in git at 0d1332d): once site
notifications were allowed (the first request returned `denied`), vibration and sound arrived with
the screen off and on. Both paths stay; without permission the app says the alert needs keep-awake.

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
- **document:** `{ _version: 5, updatedAt, programs, activeProgram, nextProgram, weeks, body, settings }`.
- **programs:** `{ id, name, days: [{ id, name, exercises: [{ id, name, kind: reps|time|check, sets,
  repMin, repMax, target, load, loadStep, bodyweight?, pair?, note?, duration? }] }] }`; `activeProgram`,
  `nextProgram` (used from the next week built). Pairs are adjacent exercises with the same `pair`.
- **weeks:** `{ n, program, startedAt, finishedAt?, days: { <dayId>: { startedAt?, finishedAt?,
  exercises: { <exId>: { name, kind, repMin, repMax, loadStep, …, load, target, sets: [{ r, at, pain? }] } } } } }`.
  A week copies its program's exercise (rules, load, target) when built, so editing a program never
  rewrites history.
- **body:** `[{ date, kg }]`. **settings:** rest (between sets 120 s, pair 90 s), alternate pairs
  (off), start rest after a log, heads-up 10 s, vibration (off, short, long, pulse), sound (off, beep,
  bell, chirp) and volume, keep awake, default load step 2.5, theme.
- `calisthenics-data.json` with `_version: 5` in the private repo; the v4 file moves to `archive/` untouched. The
  phone keeps a copy in localStorage (`cali.v5`) and works offline; the token and sync marks stay on the phone under
  `cali.sync`, running timers under `cali.timers` (start timestamps), none of them in the document.

## Rules
- **Logging:** tap a cell = target; tap again = one less (down to 0, then empty); hold = one more.
  `time` steps by 5 s, `check` toggles. The one way to enter reps (Tarık: "1 özellik 2 farklı şekilde
  yapılmasın"). A set at 0 counts as not done (no rest, can be the set in hand); a day with no set done
  goes back to not started. A tap on an exercise's name opens its editor in the card (load, target,
  sets, rep range, load step, name), written to this week and the program, never to reps.
- **Next set:** each exercise runs through its sets before the next (A1 A2 A3, then B; Tarık
  2026-10-24: "önce pull up bitireyim sonra dip geçerim"); Settings → Alternate paired exercises gives
  A1 → B1 → A2 with the pair rest inside the pair. After a log the rest timer starts.
- **Finish week** (manual) builds the next week from `nextProgram`, as the old app did: every set at
  target → target + 1; past `repMax` → load + `loadStep` and target back to `repMin`; any short set →
  no change; short at the same load three weeks running → load −10 % rounded to `loadStep` (no change
  at 0 added load). A day not done carries over unchanged and does not count toward the stall.
  Bodyweight lifts progress on the added load. A `time` row with every set at target → target + 5 s,
  any short set → no change (Tarık 2026-10-24); `check` rows copy. The rules live in `app/progress.js`
  as `Cali.progress`.
- **Timers** are computed from start timestamps, never from counted ticks; the rest timer and the
  independent timer run at once.
- **Sync:** a day's edits push at Done; Finish week, an edit to a finished day or to a program push at once;
  a change older than 12 h goes on the next open. Pull on open, last-write-wins per document with
  the remote `sha` checked. A remote document without `_version: 5` is never adopted.
- **Pantry kcal:** read only, from `pantry-data.json` in the private repo `Estaed/Pantry-Data` through the
  sync token (which then also needs read access to that repo): weekly average kcal beside body weight;
  absent or unreadable → the line is hidden. Not from `pantry.v1`: on the phone the two apps sit in
  different browsers, so that key is not visible (checked 2026-10-24; Tarık chose the repo read, 2026-10-24).

## Layout
- `index.html` shell; `app/core.js` (data, state, routing, rules above), one `app/<feature>.js` per
  feature (`workout`, `summary`, `timer`, `alert`, `settings`, `sync`, `week`, `progress`; wave 2:
  `program`, `history`, `body`),
  listed once each in the append-only `app/registry.js`; `app/base.css` for shared classes, each
  feature's classes carry its prefix. `tokens.css`, `fonts/`, `sw.js`, `manifest.json`, icons at the root.
- `legacy/`: the old app (`index.html`, its `tests/`) until v1 has run a week; then deleted.
- `tests/acceptance.py` (Playwright, 360 px, mocked GitHub API, served under `/Sthenos/`)
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
