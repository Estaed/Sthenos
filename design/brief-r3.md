# Round 3 brief: clickable workout prototypes

Rounds 1-2 (`yonler.html`, `yonler-2.html`) were judged on looks and failed on use. Tarık, 2026-10-24:
"görünüşleri iyi olsa da kullanışlı değil" (P3b and P4a "fena değil ama yeterli değil"). What he wants:

1. **See the whole program at once** ("programı tekte göreyim"): the day's exercises with their sets visible
   together, without opening each one.
2. **Enter the reps he did, fast** ("kaç tekrar yaptığımı kolay bir şekilde gireyim"), and when a set falls
   short, **enter the actual reps just as fast** ("eksik yaparsam da tekrarı da gireyim, pratik bir şekilde").
3. **What the current app provides** (functions, not its look or how it works), in a good look:
   - Weeks (H1, H2, …): finishing a week creates the next from it, with double progression applied
     (top of the rep range reached on every set → load + loadStep, reps back to the bottom); a short
     set means no progression for that exercise. Past weeks stay viewable.
   - Days of the week as tabs; the 3-day plan A Ağır / B Hacim / C Bacak.
   - Per exercise: sets × reps × load, rep range, last week's result beside it.
   - **Program editing:** add, remove, rename, reorder exercises; change sets, reps, load, rep range,
     load step; add/rename/delete a day.
   - **History:** past weeks per exercise (what he lifted, how it moved), and the old weeks.
   - Rest timer (start, stop; ~90 s between alternated pair sets).
   - Sync state (GitHub, pushes when the day's workout is finished), JSON backup download/upload.
4. Anything a serious lifter would consider must-have or quality of life that is missing (Eko and the
   builder decide, say why on the page): e.g. screen stays awake during the workout (Wake Lock API),
   undo for a mis-tap, the pair partner shown next, the timer starting itself after a logged set,
   one-handed reach (controls in the lower half), a finished-day summary.

**Who and where:** Tarık alone, Android phone (Samsung Internet), in the gym between sets, one hand,
sweaty, glancing. Text size 1.0, 360×780.

**Data (real):** program `C:/Users/TARIK/AppData/Local/Temp/claude/D--TarikOS/83355f36-0b28-44e1-a465-0ddc63cdd2ad/scratchpad/cali-data/calisthenics-data.json`
(week 1, days A/B/C, v2 program; ↔ pairs are adjacent exercises done alternately: Weighted Pull-up/Weighted Dip,
Leg Press/Side Lateral Raise, Machine Row/Shoulder Press, Seated Leg Curl/Standing Calf on A, and so on).
Real past weeks for the history view: `.../cali-data/archive/2026-09-15-h1-h4-before-reset.json` (H1-H4 of an
older 5-day program, real numbers). The last two rows of each day are a 4-minute stretch and a 22-minute
incline walk (timed, not sets).

**Design language:** follow `D:/TarikOS/.brain/skills/tasarim/SKILL.md` (read it, including the new App-screen
row: judged by doing the task), `references/DESIGN.md`, `tokens.css`, `preview.html`; project layer
`D:/Projects/Calisthenics-App/design/DESIGN.md` (taste record: rounds 1-2) and the Pantry layer it points to.
Grey + one orange, flat (no grain), English UI.

**Build:** one self-contained clickable HTML per prototype (state in memory or localStorage under a
prototype-only key; never the real sync), working by double-click over file://, phone frame 360×780 with
light and dark toggle. It must actually do: log a set at target with one tap, log a short set (e.g. 7 of 10)
in at most two taps, undo, move to the next exercise/pair, finish the day, open history for one exercise,
edit one exercise in the program, finish the week and see week 2 generated with progression.

**Done means:** you used it like Tarık would, with Playwright at 360×780: the scenario above step by step,
counting taps for "log 10 reps" and "log 7 of 10", with screenshots of each step saved to
`design/shots/r3-<name>-NN.png`; both modes looked at; `npx -y impeccable detect` and
`node D:/TarikOS/.brain/skills/tasarim/scripts/avoid_ai_design_detect.mjs` run and fixed. Report the tap counts,
what works, what is faked, and anything you would change after using it. Do not touch files outside
your own prototype file and its shots; no commit, no push.
