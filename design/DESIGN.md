# Calisthenics design layer

Follows Tarik Base v6 (`D:/TarikOS/.brain/skills/tasarim/references/DESIGN.md`) and the Pantry layer
(`D:/Projects/Pantry/design/DESIGN.md`: grey + one orange, open canvas, English UI, text size 1.0); overrides
below. None yet.

## Taste record
- 2026-10-24, round 1 (`design/yonler.html`, deleted, in git): kept P3 Focus (one exercise big, its set ring, two thumb
  buttons) and P4 Sets (every set its own tappable cell); dropped P1 Pantry (day ring + exercise list with
  status buttons), P2 Grain (P1 with the video grain) and P5 Dial (a tick dial of all sets + a queue).
  Read across (hypothesis): in the gym the screen is a logging tool for the set in hand, not a report on the
  session; P3 and P4 put the next set's numbers and a one-tap log first, P1 and P5 lead with a summary of the
  day. A round object earns its place when it measures the current exercise (P3's set ring), not the day.
  Grain lost on the same screen as P1, so the app stays flat. Round 2 (`design/yonler-2.html`, deleted, in git) varies P3
  and P4 only.
- 2026-10-24, round 3 (clickable proto-sheet / proto-dock / proto-notebook, deleted, in git): none sat right; the
  Day sheet came closest ("aralarında en çok hoşuma giden ama yeterli değil"). Round 4 (`design/r4/`, deleted, in git) holds
  the Day sheet's working core fixed and varies only the style, ten directions, static, to choose the look first.
- 2026-10-24, round 4 picks: liked 05 Instrument's last-week column and its small 4-week trend line
  ("last set ve ufak grafik hoşuma gitti"); asked for 06 Material native, maybe mixed with 04 Scoreboard, and said
  something blocks liking any of them that he cannot name ("temelde mi acaba?"). Read across (hypothesis): all ten
  share one foundation (pure grey ground, grey cells, Manrope, one orange) and differ only in layout, so the block is
  likely in what they share. Round 5 (`design/r5/`, deleted, in git) holds a 06+04 control fixed and changes one foundation axis per
  screen (colour, type, imagery, ground, density) to find it.
- 2026-10-24, round 5 pick: 02 result colour, with hit sets orange instead of green and the short set shown
  as partial rather than amber ("yeşil yerine turuncu olur, sarı yerine de yarım olduğunu belli eden bir renk").
  Read (hypothesis): the block was the all-grey sheet that hid how the workout is going, and a second hue is
  still unwanted. Round 6 (now `design/screens.html`, shots in `design/shots/`) is the clickable prototype: short sets fill up to reps/target,
  the current set moves to a neutral ink ring, plus settings and an independent timer.
- 2026-10-24, app icon round 1 (`design/icons.html`, 20 per app, deleted, in git): torn between C16 Muscle-up (bar + orange
  arrow rising over it) and C07 Sets row (orange set cells, the last one partial), liking the orange detail ("turuncu
  detay güzel"). Read (hypothesis): the icon should show the app's own moment (a set logged, a rep over the bar) with
  orange as the result, not an object in plain ink. Round 2 (`design/icons-2.html`, deleted, in git) derives 10 from those two.
- 2026-10-24, app icon final: C16 Muscle-up ("C16 olsun son kararim"), over its own derivations (C21-C23, C28) and the
  set-cell family (C07, C24-C27, C29, C30). Source `icon.svg`, rendered to the PNGs and favicons. Rejected the six
  plain-noun names of round 1 (Chalk, Tally, Rings, Grip, Notch, Hang: "begenmedim").
