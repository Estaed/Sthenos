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
- **Built the way Pantry was:** same stack (PWA, vanilla JS, no build step, one script per feature
  under `app/`, GitHub Pages, private data repo sync), same process (notes → Blueprint → waves with
  `plan-wave` and `otopilot`), same design language (Tarik Base v6 + Pantry layer).
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

## Ideas
- Set-by-set logging (P4) with a focus view for the current exercise (P3).
- Rest timer between alternated pairs (~90 s).
- Last week's value under every exercise; "+2.5 kg next" when the range top is reached.

## Screens
<Eko fills it by asking before the Blueprint: v1 main flow, screen list, states>

## After v1
- 2026-10-24: link with Pantry (body weight, calories beside training) — Tarık kept the apps separate.
