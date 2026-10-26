# Tasks

Each wave is one MINOR version (`CHANGELOG.md`); v1 is 1.0.0.

## Wave 1 (0.1.0, 2026-10-24)
- [x] Task-00: Shell, data core, seams and gate; old app to `legacy/` (runs first)
- [x] Task-01: The workout day: tap logging, pair order, rest timer, start/finish, summary
- [x] Task-02: Independent timer and alerts (rest and timer end, screen off)
- [x] Task-03: Settings, GitHub sync (port), JSON backup
- [x] Task-04: Weeks and double progression

Task-00 runs alone; Task-01 to Task-04 then run in parallel (disjoint OWNS, all depend only on Task-00).

## Wave 2 (0.2.0, 2026-10-26; Tarık: program adding first)
- [x] Task-05: Programs: list, editor, import, use now or from next week

## Wave 3 (0.3.0)
- [x] Task-06: Muscle map: the week's muscles by day, muscles picked per exercise

## Later waves (draft)
- Wave 4 (0.4.0), what remains of v1: history per exercise (needs Task-04's weeks); Pantry's weekly kcal beside body weight
  (body weight with its 7-day average, waist and a body-fat estimate came early, 0.3.2, in Settings → Body);
  a note per exercise and a pain flag per set (needs Task-01's cells); Hermes' weekly Discord summary
  (needs Task-03's v5 file in the repo; checks Hermes' GitHub access first).
  Pantry kcal comes from `Estaed/Pantry-Data` through sync (Blueprint -> Pantry kcal; Tarık 2026-10-24);
  `pantry.v1` then leaves `Cali.readOnly` and AGENTS.md.
- 1.0.0: v1, once Blueprint → Done when holds on the phone after wave 4.
