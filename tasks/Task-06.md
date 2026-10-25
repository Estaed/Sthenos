# Task-06: Muscle map: which muscles the week works, by day, with muscles picked per exercise
**Status: DONE** — verified 2026-10-26 (23c0b31), eye check pending: 1
> **Execution:** agent `ultracode`
> *Why:* product code with one owner and no parallel partner: one Opus agent builds it end to end, the main loop gates it.

**Lane**
- OWNS: `app/muscles.js`, `app/muscles.css`, `app/muscles-data.js`, `tests/test_muscles.py`, `app/registry.js` (append only), `app/core.js` (only: the exercise check accepting `muscles`, a read-only `Cali.muscles` list of the muscle keys, and its header lines), `app/program.js`, `app/program.css` and `tests/test_program.py` (only the Muscles field and its cases), `app/default-program.js` (only adding `muscles` to each exercise)
- MUST NOT TOUCH: `app/workout.js`, `app/summary.js` (Task-01), `app/timer.js`, `app/alert.js` (Task-02), `app/settings.js`, `app/sync.js` (Task-03), `app/week.js`, `app/progress.js` (Task-04), `sw.js` (orchestrator bumps the cache)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-05

## Goal
Tarık opens a muscle icon beside the hourglass on the day screen and sees, on a front and back body, which muscles the
week in view works and how much, and with one tap which day works what (chips Week, then the week's days by the
program's current names, else the day id, as the day screen names them). He changes the program (Task-05) and the map
follows the week built from it. A stranger with their own program gets the same, because each exercise carries the
muscles it works, picked in the program editor.

The look is `design/muscles.html` (shot `design/shots/09-muscles-proto.png`), with Tarık's changes already in it: a
muscle's colour runs from pale orange through orange to red with its fractional sets for the selection (none: the body
grey; 10 and up: full red; one absolute scale for Week and for a day), a scale under the bodies says so, and the day
chips filter it. Below the bodies: one box naming the least worked main muscle for the selection and the muscles not
worked at all, then one row per muscle (not-worked ones included, at the end) with a bar: sets planned in grey, sets
done this week filling orange (orange means done, as on the workout screen), and on Week only a tick at 4 sets (the
floor, Iversen 2021). Tapping a muscle on the body or its row puts that muscle in the box with the exercises that give
its sets ("Seated Leg Curl 2 (A)"). Small muscles on the body (forearm, tibialis) need not be tappable there; every
muscle is reachable from its row.

Counting is fractional (Pelland 2026): an exercise's sets count 1 for each muscle it is for and 0.5 for each helper.
Sets come from the week in view (the week copies the program, so a past week shows what it was), done sets from its
logged sets (a set at 0 does not count). `check` rows (stretch, walk, warm-up) are neither counted nor listed.

Each exercise gets an optional `muscles: { <muscle>: 1 | 0.5 }` (Blueprint → Data). No key: one name table guesses
them. `{}`: the user chose "counts nothing". The program editor shows a Muscles field: the muscle names as chips, a
tap cycling off → main → helper → off; the first time an exercise without `muscles` gets its name saved, the guess is
written into it (never over a pick, never re-guessed on a rename). An edit while the current week has sets shows from
the next week, and the field says so in one line, as the editor's other lines do. A reps or time row that neither
carries nor guesses is listed once under the box ("Not counted: <name>") with a way to its program editor. The
built-in program's exercises carry `muscles` written out, equal to what the table guesses for them, so Tarık's stored
program and weeks, built before this field existed, count the same through the guess.

## Why
Tarık 2026-10-26: "hangi kaslar çalışıyor hangileri eksik falan kas mapi olarak gözüksün", "o haftanın programına göre
olsun", "gün gün filtre", colour "az yoğun ise turuncu çok yoğun ise kırmızı". His answer on how custom exercises get
their muscles: "önerini yap" (picked per exercise). Program choices so far rested on hand-counted sets.

## Acceptance
- [ ] `tests/test_muscles.py` (its own server and console-error collection through `acceptance.py`'s helpers) checks on
  a fixture week: the fractional totals per muscle for Week and for each day; done sets counted from logged sets only; a
  past week opened from its read-only day screen shows that week's copy after the program changed; the least-worked
  box and the not-worked list; a tap on a body muscle and on a row selects it and lists its exercises; `{}` counts
  nothing and is not listed; check rows are ignored; bad `muscles` values in a pulled week are ignored, never thrown.
- [ ] The name table: for every built-in exercise the guess equals its written `muscles`; a fixture document stored
  without any `muscles` gives the same totals as the built-in one; and each of these names guesses its main muscle:
  Lat Pulldown (upper-back), Squat and Hack Squat (quadriceps), Deadlift and Romanian Deadlift (hamstring), Push-up and
  Bench Press (chest), Hip Thrust (gluteal), Overhead Press (deltoids), Upright Row (deltoids, not upper-back),
  Close-grip Bench Press (triceps), Bench Dip (triceps), Hammer Curl (biceps), Face Pull
  (deltoids), Lunge (quadriceps), Hanging Leg Raise (abs), Shrug (trapezius).
- [ ] Colour runs one way with sets, measured on the fills the screen paints, in both themes: hue moves from orange
  toward red and the distance from the body grey grows; 0 sets paints the body grey.
- [ ] The program editor's Muscles chips save `muscles` (main 1, helper 0.5, all off stores `{}`), the guess is written
  once as described, the week built afterwards carries it, and `Cali.change` refuses a value other than 1 or 0.5 or a
  key not in `Cali.muscles` (core's check).
- [ ] The icon sits in the day screen's top bar beside the hourglass; the day screen still fits at 360 px (the workout
  test's whole-day check stays green); the muscle screen opens with the week the day screen shows and Back returns there.
- [ ] The body paths come from react-native-body-highlighter, its MIT licence text in the header comment of
  `app/muscles-data.js`; no other outside asset.
- [ ] The page loads with no console errors at 360 px in both themes.
- [ ] (eye) the muscle screen at 360 px, both themes, against `design/muscles.html`; the Muscles field in the program
  editor in the look of its other fields; every control a 44 px target. Red here is a recorded break
  (`design/deviations.md`, 2026-10-26).

## Out of scope
- Separate front, side and rear deltoid regions (the body paths have one deltoid); a muscle history over weeks.
- Changing the built-in program's exercises or sets.

Fixed: muscle keys are the body paths' slugs (`chest`, `deltoids`, `biceps`, `triceps`, `forearm`, `abs`, `obliques`,
`upper-back`, `trapezius`, `lower-back`, `gluteal`, `quadriceps`, `hamstring`, `adductors`, `calves`, `tibialis`), kept
once in core as `Cali.muscles`; routes through `Cali.route` / `Cali.go`, the icon through `Cali.slot('topbar')`; UI text
in English; every visual change follows `D:/TarikOS/.brain/skills/tasarim/SKILL.md`.
