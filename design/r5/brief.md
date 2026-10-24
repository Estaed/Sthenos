# Round 5 brief: find what blocks liking (one axis per screen, on 06)

Round 4 (`design/r4/index.html`) drew ten styles of the same workout moment. Tarık, 2026-10-24: liked 05
Instrument's **last-week column** and its **small 4-week trend line**; wants **06 Material native**, maybe
mixed with **04 Scoreboard**; and: "bir şeyler beğenmeme engel ama ne çözemedim, temelde mi acaba?"

All ten shared one foundation (pure grey ground, grey set cells, Manrope, one orange) and differed only in
layout. So round 5 is a taste test of the foundation: **one control screen, then nine screens that each
change exactly one thing from it**. Everything not named in your axis stays pixel-identical to the control,
so Tarık's yes/no tells us which foundation choice is the block.

## The control (`00-control.html`)

Start from `D:/Projects/Calisthenics-App/design/r4/06-material-native.html` (M3 structure: top app bar,
segmented day button, rounded tonal containers, docked bottom sheet for logging) and add:

- 04 Scoreboard's score bug (`design/r4/04-scoreboard.html`) as the top of the docked sheet: current
  exercise, SET 2/3, REPS 10, REST 1:12 in big heavy numerals with the rest progress line.
- 05 Instrument's last-week value per exercise and its 4-point trend line (`design/r4/05-instrument.html`),
  this week's point orange once logged.
- The same moment and data as round 4 (`design/r4/brief.md`: A Heavy, Leg Press set 2 next, Side Lateral
  Raise set 1 short 9 of 12, rest 1:12 of 1:30, +2.5 kg next on Pull-up). Read that brief: its rules on data,
  design language, fonts (embedded base64), 360×780, both modes, the Don'ts and the deliverable all apply.
- Tarik Base v6 palette (pure neutrals + one orange), Manrope text, Archivo numbers, the whole day visible
  above the sheet if it fits.

## The nine variants (each copies the control and changes one axis)

| NN | Axis | The one change |
|---|---|---|
| 01 | Colour: tonal tint | Real M3 dynamic colour from the orange seed: ground and containers carry a faint warm tint instead of pure grey (keep it subtle; never cream/brown, never the Claude look) |
| 02 | Colour: results | Set results carry meaning by colour: hit = green, short = amber, current = orange ring, to-do stays neutral. Tests whether the all-grey sheet hides how the workout is going |
| 03 | Colour: day identity | Each day has its own hue (A orange, B blue, C green) used where the control uses orange; this screen is A, so show the tabs' hues |
| 04 | Type: one sturdy face | Schibsted Grotesk for everything (text and numbers), weights 500-900, instead of Manrope + Archivo |
| 05 | Type: bigger scale | Every text one step bigger (names 18, meta 14, set numbers 24+); the day may scroll, the sheet stays docked |
| 06 | Imagery: exercise icons | A small monoline pictogram of the movement (or muscle group) at the left of every exercise, drawn as inline SVG, one stroke weight, neutral colour |
| 07 | Ground: light first, soft | Light mode is the hero: white ground, pair containers as soft tonal cards (Samsung One UI / Google Fit light), dark mode follows |
| 08 | Layout: One UI reach | Samsung One UI structure: a large title area at the top (A Heavy, clock, Finish) and all content pushed to the lower two thirds for one-hand reach |
| 09 | Density: focus + list | The current pair as one large card (big cells, last week, trend) and every other exercise as one compact line; fewer things at once |

## Deliverable

`D:/Projects/Calisthenics-App/design/r5/<NN>-<slug>.html` and `design/r5/shots/<NN>-dark.png`, `<NN>-light.png`
(Playwright, 360×780, deviceScaleFactor 2, `file://`). Look at both shots and fix what reads badly. Run
`node D:/TarikOS/.brain/skills/tasarim/scripts/avoid_ai_design_detect.mjs <html>`. Reply in under 80 words:
the change, anything else you had to change to make it work (ideally nothing), and what you would watch for.
Touch only your own files. No commit, no push.
