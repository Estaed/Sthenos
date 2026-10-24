# Round 6 brief: the chosen design as one clickable prototype

Tarık picked round 5's **02 result colour** (`design/r5/02-result-colour.html`, built on `00-control.html`)
with two changes, and asked for settings and an independent timer (2026-10-24): "02 ama yeşil yerine
turuncu olur, sarı yerine de yarım olduğunu belli eden bir renk ... ayarlar falan da lazım, bir de timer
lazım, bağımsız timer app içinde ... prototip okeylersek diğer özellikleri de söyler başlarız."

If he approves this prototype, the real app is built from it, so it is the reference for the look and the
main flow. History, program editing and weeks come later; do not build them.

## Look (start from 02, change only this)

- **Hit set** (reps ≥ target): orange. A tinted orange fill with the number in orange (dark and light
  tokens from the base's signal orange, contrast AA).
- **Short set:** shows that it is partial by its shape, not by a second hue: the same orange tint
  fills the cell only up to reps/target from the bottom (9 of 12 → 75 % high), the rest stays neutral,
  and the number reads `9/12`.
- **Current set:** orange now means "done", so the current set moves to a thick neutral ink ring
  (white in dark, near-black in light) so it does not compete. If you find a better way to keep "now"
  and "done" apart at a glance, use it and say why.
- Orange will cover more than the base's ~2 % once many sets are done; that is Tarık's choice for
  this screen. Everything else orange (tags, rest digits) is kept only where it carries the one key
  number; drop orange elsewhere if the screen gets loud.
- Everything else as 02/00: M3 structure, 04's score bug in the docked sheet, 05's last week and
  trend line per exercise, Tarik Base v6 neutrals, Manrope + Archivo, both modes.

## What it must do (clickable, on real data)

Data: `C:/Users/TARIK/AppData/Local/Temp/claude/D--Projects-Calisthenics-App/5be50840-7a9a-4974-a907-dab39604bfb3/scratchpad/cali-data/calisthenics-data.json`
(plans → days A/B/C, week 1; embed what you need). Pairs are alternated: Pull-up 1 → Dip 1 → Pull-up 2 …

1. **Workout:** Start (clock starts) and Finish (a short summary: duration, sets done, short sets,
   exercises that reached the range top and get +load next week). Day tabs A/B/C switch days.
2. **Log a set:** one tap logs the target; one tap on 7/8/9/11/12 logs that number; any other number in
   two taps. After logging, the next set follows the pair alternation, the trend line's this-week point
   updates, and the rest timer starts by itself (pair rest 90 s, from settings).
3. **Fix a mistake:** an undo snackbar after each log; tapping any logged cell lets you change or clear it.
4. **Independent timer** inside the app, separate from the rest timer: a stopwatch and a countdown
   (presets like 30 s, 1, 2, 4 min and a custom value), start, pause, reset, lap for the stopwatch. It keeps
   running while you are back on the workout screen (a small pill in the top bar shows it; tap to open).
   At zero: vibration (`navigator.vibrate`) and a short beep (Web Audio). The timed rows (Hamstring stretch
   4 min, Incline walk 22 min) start the countdown with their duration.
5. **Settings** screen: default rest and pair rest, auto-start rest after a log, keep screen awake during
   a workout (real Wake Lock API), vibration and sound, default load step (2.5 kg), theme (system / light /
   dark), sync status (GitHub; shown, not wired), JSON backup download (real, from the prototype state)
   and upload, reset prototype data. Add only what a serious lifter would miss, and say why.
6. State in `localStorage` under a prototype-only key; never the real sync.

Timers must stay correct when the phone screen is off or the tab is in the background: compute from
start timestamps, never by counting ticks.

## Build and check

- One self-contained `D:/Projects/Calisthenics-App/design/r6/proto.html` (fonts as base64, no external
  requests), working by double-click over `file://` and from GitHub Pages on his Android phone (Samsung
  Internet): on a narrow screen it fills the phone (safe areas, no desktop frame); on a wide screen it
  shows a 360×780 phone frame with a theme toggle.
- Follow `D:/TarikOS/.brain/skills/tasarim/SKILL.md` (§3 checks) and `references/DESIGN.md`; project layer
  `design/DESIGN.md` (taste record, rounds 1-5).
- **Done means you used it like Tarık would**, with Playwright at 360×780: start the workout, log Pull-up 1
  at target, Dip 1 short (7), undo, relog, fix a logged cell, run the countdown from the stretch row and let
  a 5 s custom countdown finish, open settings and change rest to 60 s and see the next rest use it, switch
  theme, finish the day and see the summary, reload and see the state kept. Count taps for "log at target"
  and "log 7". Save step screenshots to `design/r6/shots/NN-<step>.png` (both modes for the main screen).
- Run `node D:/TarikOS/.brain/skills/tasarim/scripts/avoid_ai_design_detect.mjs` and
  `npx -y impeccable detect` on the file; fix real findings.
- Reply in under 150 words: tap counts, what works, what is faked, and what you would change after
  using it. Touch only `design/r6/`. No commit, no push.

## Scope change (Tarık, 2026-10-24, same day)

"prototip derken görsel yani çalışan değil": the round is static screens (`design/r6/screens.html`: workout
in progress, an advanced day, StrongLifts-style tap-to-lower logging, the independent timer, settings,
finish summary), both modes. The working app is built later from tasks (`plan-wave` → `otopilot`). The
"What it must do" list above stays as the spec for those tasks.
