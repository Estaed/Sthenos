# Round 4 brief: ten styles for the workout screen (static)

Round 3 built three clickable prototypes; none sat right with Tarık. The Day sheet came closest
("aralarında en çok hoşuma giden ama yeterli değil"). Round 4 decides the **look** first: ten
directions that differ in style, each drawing the **same working screen**, so the style is judged
on the real task and not on a pretty picture (rounds 1-2 were "görünüşleri iyi olsa da kullanışlı
değil").

## The screen every direction draws (same content, same state)

The workout day **A Heavy**, mid-session, on Tarık's Android phone between sets:

- Header: week (Week 1), day tabs A Heavy / B Volume / C Legs, the session clock running (e.g.
  0:23:41 since Start), a Finish control, a small sync state.
- **The whole day visible at once** without opening anything: every exercise with its load, rep
  range and one cell per set. Pairs done alternately are shown as pairs (Weighted Pull-up ↔
  Weighted Dip, Leg Press ↔ Side Lateral Raise, Machine Row ↔ Shoulder Press, Seated Leg Curl ↔
  Standing Calf Raise), then Plank, then the timed rows (Hamstring stretch 4 min, Incline walk 22 min).
  Take names, loads, ranges and set counts from the real data (below), day A of week 1.
- State: the first pair is done (Pull-up 6, 6, 6; Dip 8, 8, 8), Leg Press set 1 done at 10, Side
  Lateral Raise set 1 **short: 9 of 12** (shown as short, with its real number), current set =
  Leg Press set 2. Rest timer running (1:12 left of 1:30, pair rest).
- **Logging control for the current set**, reachable by thumb in the lower half: one tap logs the
  target (10), and a short set is two taps at most (pick 7, 8, 9 …). Show that control's look.
- Last week's value beside each exercise (invent plausible week-0 numbers close to the targets; mark
  nothing else as fake) and a "+2.5 kg next" style hint on one exercise whose sets all hit the top.

Text in English. 360×780 phone, text size 1.0, one hand, sweaty, glancing: touch targets ≥ 44 px,
contrast AA, numbers readable at arm's length.

## Real data

`C:/Users/TARIK/AppData/Local/Temp/claude/D--Projects-Calisthenics-App/5be50840-7a9a-4974-a907-dab39604bfb3/scratchpad/cali-data/calisthenics-data.json`
(plans → day A; weeks[0]). Read only.

## Design language

Read `D:/TarikOS/.brain/skills/tasarim/SKILL.md` and `references/DESIGN.md` (Overview, Taste record,
Colors, Typography, Components, Do's and Don'ts) before the first line, and the project layer
`D:/Projects/Calisthenics-App/design/DESIGN.md`. Fonts: `D:/TarikOS/.brain/skills/tasarim/assets/fonts/`
(Archivo, Manrope, Schibsted Grotesk; embed them as base64 `@font-face` so the file stands alone).

Your direction is a **style**; it may bend the base on purpose (that is the point of this round), but
these stay: one restrained accent hue plus neutrals, contrast AA, ≥ 44 px targets, both modes, say each
thing once, dense not empty. Never: cream/brown ground + serif + paper texture (the Claude look),
indigo/purple gradients, glassmorphism, handwriting, stamps, mono for big numbers, condensed type, grain
on an app screen, emoji as icons. Tarık likes: black + orange with grey, YouTube / X / AusPost as app UIs,
heavy even-stroke sturdy letters, hard offset depth (never blurred), one big anchor per screen.

## Deliverable

1. `D:/Projects/Calisthenics-App/design/r4/<NN>-<slug>.html`: one self-contained static HTML, the phone
   drawn at 360×780, with a light/dark switch via `data-theme` on `<html>` (both modes fully designed).
   No interaction needed beyond the theme; no external requests.
2. Screenshots with Playwright (Python, `pip` is available; Chromium headless), viewport 360×780,
   deviceScaleFactor 2, the page opened by `file://`: `D:/Projects/Calisthenics-App/design/r4/shots/<NN>-dark.png`
   and `<NN>-light.png`. Look at both images yourself and fix what reads badly at phone size before you stop.
3. Run `node D:/TarikOS/.brain/skills/tasarim/scripts/avoid_ai_design_detect.mjs <your html>` and fix
   real findings.
4. Reply in under 120 words: the direction's idea in one sentence, what you bent from the base and why,
   the logging control's tap counts (target, short set), and the one thing you would change next.

Touch only your own HTML and its two PNGs. No commit, no push. Who judges: Tarık, choosing a style he
will look at three times a week for months in the gym; the best is the one a serious lifter would
want on his phone, not the most impressive poster.
