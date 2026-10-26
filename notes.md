# Notes

The first file of the project and the one place for ideas. Nothing here is binding; what holds
becomes Blueprint. Dump freely, then sort: v1 is the simplest complete version, and everything it
doesn't need moves to *After v1*. Eko points out when the v1 list grows past that.

Restarted 2026-10-24 from a TarikOS session (Tarık back at the gym after a month off). The old app
(`index.html`, one 4,000-line file, `tests/acceptance.py`) stays live until the rebuild replaces it.

## Goal
Tarık's own workout log for the gym, on his phone between sets: today's exercises with sets, reps
and load, done/partial per set, last week beside each, double progression that raises the load at
the top of the rep range. For Tarık only (2026-09-15: "bu sadece benim için yapıldı").

## Decided (Tarık, 2026-10-24)
- **Separate app**, not a tab inside Pantry ("antreman uygulaması ayrı kalsın"); Pantry's notes
  planned a v1.2 merge, which is now *After v1* at most.
- **Built the way Pantry was** ("pantryde yaptığımız development ile ilerleyeceğiz"): same process
  (notes → Blueprint → waves with `plan-wave` and `otopilot`) and design language (Tarik Base v6 +
  Pantry layer). The stack is still a decision (round below): he named the process, not the stack.

## Blueprint decisions, round 1 (Tarık "evet" to the recommendations, 2026-10-24)
1. **Stack:** PWA like Pantry (vanilla JS, `app/` one script per feature, GitHub Pages, data repo
   sync) — recommended: the Monday deadline, the sync and v4 data already exist, his phone runs
   Pantry the same way. Rejected for v1: Flutter/Kotlin native (the blueprint skill notes Pantry's
   web build fell short in scrolling and feel, 2026-10-21; if the workout app feels the same, native
   goes to *After v1* with the measured complaint).
2. **Design:** a style from round 4 (`design/r4/`, deleted, in git; ten static directions on the Day
   sheet's working core); round 3's prototypes were deleted 2026-10-24 (Tarık: none sat right, Day
   sheet closest), git keeps them.
3. **Data:** same private repo `Estaed/Calisthenics-Data`, a fresh schema v5 file (per-set reps, workout
   start/finish, body weight); the v4 file moves to `archive/`, nothing is migrated (Tarık 2026-10-24).
4. **Old app:** the new one takes the same URL (his home-screen icon keeps working), the old
   `index.html` moves to `legacy/` until v1 has run a week — recommended. Rejected: a second URL.
- **Look:** round 1 of `design/yonler.html` (deleted, in git) kept P3 Focus (one exercise big, thumb buttons) and
  P4 Sets (each set its own cell); round 2 in `design/yonler-2.html` (deleted, in git). Taste record in `design/DESIGN.md`.

## Blueprint decisions, round 2 (Tarık "evet" to the recommendations, 2026-10-24)
5. **Edits and sync:** an edit during a workout goes with Finish; an edit to a finished day or to the
   program pushes at once (rare, and a lost program edit hurts); the 12 h fallback stays.
6. **New program (e.g. 4 days):** programs are their own objects (v4 already has `plans`). Settings →
   Programs: list, edit, duplicate, and "use from next week", so the running week never changes under
   you; the week generator takes the chosen program at Finish week. Two ways in: the in-app editor
   (days, exercises, sets, range, load, step, pairs, order) and importing a program file (JSON) that Eko
   or anyone writes. Tarık: "muhtemelen sana söylerim sen düzenle"; others use the editor or a file.
7. **Who it is for:** a public site; anyone who opens it uses it without sync, data on their phone
   (localStorage, JSON backup); Tarık adds his GitHub key in Settings and syncs (Tarık: "başkası senkronsuz
   çalışacak ... ben ise github key ile senkronlu"). A starter template for others goes to *After v1*.
8. **Missed day / week end:** Finish week is manual; a day not done carries its exercises over with no
   progression.
9. **Stalled lift:** the same load short three weeks running drops 10 % (StrongLifts' deload).
10. **Timed and bodyweight rows:** plank tap steps by 5 s; stretch and walk are done/not done; weighted
   pull-up and dip log the added load (BW + x kg) and progress on it.
11. **Rest alert with the screen off:** a web page cannot vibrate or beep reliably while the phone is
   locked in a pocket. This is the riskiest assumption; research before Blueprint (Notification API,
   Samsung Internet, keep-awake as the fallback).

## What we know (2026-10-24)
- Data lives in private `Estaed/Calisthenics-Data` → `calisthenics-data.json` (v4 schema: plans,
  weeks → days → exercises with sets, reps, weight, status, repMin/repMax/loadStep). Every sync is
  a commit, so git history is a free time series. Old weeks in `archive/`.
- Current program: one 3-day plan A Ağır / B Hacim / C Bacak (`D:/TarikOS/600-Life 🌿/Health/Antrenman.md`).
  Pairs are alternated (pull-up ↔ dip, row ↔ shoulder press); each day ends with a 4-minute
  hamstring stretch and a 22-minute incline walk (timed, not sets).
- Health limits that shape the exercise list: same note, *Sağlık kısıtları*.

## Riskiest assumption
<to fill with Tarık>

## Acceptance
- <to fill with Tarık>
- (eye) <to fill with Tarık>

## Must (Tarık, 2026-10-24 night)
- The whole day's program in one view; reps done entered fast; a short set entered just as fast,
  keeping its real number ("eksik sette kaç tekrar yaptığımı da kaydedelim ki ilerideki haftalarda
  ona göre programı düzenleriz, log tutalım her şeyin").
- Workout Start and Finish: start time, finish time, duration ("spora başla sporu bitir yapalım ne
  kadar süre geçirdiğimi de hesaplarız").
- What the old app provides: weeks with double progression on finish, days, program editing,
  history, rest timer, sync, JSON backup (`design/brief-r3.md`, deleted, in git).
- Sync pushes when a day or week is finished, not after every change (already live in the old app,
  `b47cf0c`); Pantry keeps its own policy (Tarık: "pantry kalsın aynen").
- Deadline: gym reopens Monday 2026-10-26; the app should be ready for that day.
- Look: round 6 (`design/screens.html`) approved 2026-10-24 ("güzel bence"). One way to change a set's reps, not
  two ("1 özellik 2 farklı şekilde yapılmasın"): tapping the cell, StrongLifts style (Tarık: "dokunarak yapalım"): tap =
  target, tap again = one less, hold = one more; no number strip (`design/screens.html` screens 7-8).
- Body weight is logged here, not in Pantry (Tarık 2026-10-24); Pantry's notes left it an open idea.
- v1 also has (Tarık 2026-10-24, from Eko's list): body weight with a 7-day average; a lasting note per exercise
  and a pain flag on a set; a weekly summary to Discord by Hermes; Pantry's weekly calories beside body weight
  (read only). After v1: swapping an exercise when the machine is busy.
- Old data is not used ("eski verileri kullanmayacağız"): v1 starts empty, no v4 migration.

## Ideas
- Set-by-set logging (P4) with a focus view for the current exercise (P3).
- Rest timer between alternated pairs (~90 s).
- Last week's value under every exercise; "+2.5 kg next" when the range top is reached.
- Round 3 (clickable; deleted, in git before this commit): Day sheet, Program + dock, Notebook. Day sheet liked best, "fena değil ama yeterli değil".

## Screens
<Eko fills it by asking before the Blueprint: v1 main flow, screen list, states>

## After v1
Items with a place sit under the version they aim at (`CHANGELOG.md`: one MINOR per wave).

### Later
- 2026-10-26: the walk's real minutes and distance from the gym's Technogym treadmill (Tarık opens a session by
  scanning its QR into Mywellness) instead of the tile's own timer: on day A he walked 23 min, the tile only says done.
  Not checked: the public API (apidocs.mywellness.com) is for partner platforms; a personal route would be Mywellness →
  Strava (reported unreliable for treadmill sessions) → Strava's API, since a web page cannot read Health Connect.
  First step: does one walk show up in Mywellness, and does Mywellness push it to Strava. Until then, a minutes
  field on the walk tile is the cheap fix.
- 2026-10-24: link with Pantry (body weight, calories beside training) — Tarık kept the apps separate.
- 2026-10-24: starting load for an exercise new to a program (Tarık: adding bench when moving to 4 days,
  with dips at 8 × +10 kg). Estimate from his own logged history of the closest movement (incline bench
  3×8 at 45 kg is in the current program), not from a dip→bench ratio (transfer varies person to person,
  `knowledge/concepts/calisthenics-kuvvet-profili-ve-arka-zincir.md`); start a step below the estimate and let
  week 1 calibrate it. Fits the wave 2 program editor.
