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

## Open decisions for Blueprint (round 1, for Tarık in the morning; "evet" takes the recommendation)
1. **Stack:** PWA like Pantry (vanilla JS, `app/` one script per feature, GitHub Pages, data repo
   sync) — recommended: the Monday deadline, the sync and v4 data already exist, his phone runs
   Pantry the same way. Rejected for v1: Flutter/Kotlin native (the blueprint skill notes Pantry's
   web build fell short in scrolling and feel, 2026-10-21; if the workout app feels the same, native
   goes to *After v1* with the measured complaint).
2. **Design:** a style from round 4 (`design/r4/index.html`, ten static directions on the Day
   sheet's working core); round 3's prototypes were deleted 2026-10-24 (Tarık: none sat right, Day
   sheet closest), git keeps them.
3. **Data:** same private repo `Estaed/Calisthenics-Data`, schema v5 (per-set reps, workout
   start/finish) migrated from v4 — recommended (git history stays one time series). Rejected: a new repo.
4. **Old app:** the new one takes the same URL (his home-screen icon keeps working), the old
   `index.html` moves to `legacy/` until v1 has run a week — recommended. Rejected: a second URL.
- **Look:** round 1 of `design/yonler.html` kept P3 Focus (one exercise big, thumb buttons) and
  P4 Sets (each set its own cell); round 2 in `design/yonler-2.html`. Taste record in `design/DESIGN.md`.

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
  history, rest timer, sync, JSON backup (`design/brief-r3.md`).
- Sync pushes when a day or week is finished, not after every change (already live in the old app,
  `b47cf0c`); Pantry keeps its own policy (Tarık: "pantry kalsın aynen").
- Deadline: gym reopens Monday 2026-10-26; the app should be ready for that day.

## Ideas
- Set-by-set logging (P4) with a focus view for the current exercise (P3).
- Rest timer between alternated pairs (~90 s).
- Last week's value under every exercise; "+2.5 kg next" when the range top is reached.
- Round 3 (clickable; deleted, in git before this commit): Day sheet, Program + dock, Notebook. Day sheet liked best, "fena değil ama yeterli değil".

## Screens
<Eko fills it by asking before the Blueprint: v1 main flow, screen list, states>

## After v1
- 2026-10-24: link with Pantry (body weight, calories beside training) — Tarık kept the apps separate.
