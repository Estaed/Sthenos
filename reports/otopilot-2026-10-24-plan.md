# Otopilot plan — 2026-10-24, wave 0 (Task-00) and wave 1 (Task-01..04)

Approved by Tarık's "başlayabilirsin task 00 ile sonrasında direkt wave 1" (2026-10-24 12:40); the
plan stays inside the written tasks. The Workflow for wave 1 is asked separately (Eko invoked the skill).

## Run shape
- Direction: Claude main loop orchestrates, Claude agents build (`--orchestrator claude --delegate claude`).
- Seats: orchestrator and planner = this interactive session (`opus`, Claude Code); builders `opus`/`xhigh`,
  reviewers `opus`/`high` (`auditor`), Codex second-family lens `sol`/`high` read-only.
- SOURCE: `tasks` (Task-00..04). UNTIL: `done`. Target: wave 1 on main before Monday 2026-10-26.
- BASE_SHA (wave 0): `b2bc7452cdeb91887e0590203aa919dfb168df89`. Wave 1 BASE_SHA = main after Task-00 integrates.
- Timebox per builder: 150 min (not measured for this project; Pantry wave 3 builders ran inside 169 min).

## Preflight (2026-10-24 12:43)
- `onkontrol.py --tasks 00,01,02,03,04 --orchestrator claude --delegate claude`: OVERALL OK, exit 0;
  OWNS disjoint; no stop markers; quota GO.
- Baseline gate at BASE_SHA: `python tests/acceptance.py` (old app's test) → ALL PASS, exit 0.
  Task-00 moves it to `legacy/tests/` and writes the new gate.
- Power: on AC (BatteryStatus 2, 97%). Free memory 12.3 GB; no emulator in this run (headless Playwright only).
- Phone: `adb devices` empty → the phone use check waits for Tarık to plug in; otherwise headless 360 px.
- Quota: Claude 5-hour 41% (resets 14:40 local), weekly 19% (resets 2026-10-25 21:30 local);
  Codex 5-hour 0%, weekly 3%.
- notes.md → After v1: no selected task was tried before; no PREVIOUSLY TRIED.

## Estimate
- Wave 0: one builder ~60-120 min, about 10-20 points of the 5-hour window, ~2 weekly points (Pantry 2026-10-20: two single builders = 2 weekly points).
- Wave 1: four features in one Workflow with screen lenses and fix rounds: ~11 weekly points
  (Pantry 2026-10-21: 4-5 features = 11 points); measured again with `--features 4` before the wave.

## Rows
| Task | Wave | Engine | Model/effort | OWNS | GATE | Attempts |
|---|---|---|---|---|---|---|
| Task-00 Shell, data core, seams, gate | 0 | one Opus builder (wave of one, no Workflow) | `opus`/`xhigh` | per task file (16 paths) | `python tests/acceptance.py` | ≤2 |
| Task-01 Workout day | 1 | ultracode Workflow | build `opus`/`xhigh`; screen lens `opus`/`high` | per task file | same | ≤2 |
| Task-02 Timer and alerts | 1 | ultracode Workflow | build `opus`/`xhigh`; screen lens `opus`/`high` | per task file | same | ≤2 |
| Task-03 Settings, sync, backup | 1 | ultracode Workflow | build `opus`/`xhigh`; screen + spec lens (can lose data) `opus`/`high` | per task file | same | ≤2 |
| Task-04 Weeks and progression | 1 | ultracode Workflow | build `opus`/`xhigh`; spec lens (wrong load = costliest bug) `opus`/`high` | per task file | same | ≤2 |

Excluded: none. Wave 2 (draft in TASKS_INDEX) is not written yet; it is `plan-wave`'s next step after Tarık looks at wave 1.

## Notes for the briefs
- Worktrees live under `D:/Projects/.lanes/cali-w<n>-t<id>`; the gate must test the worktree it runs
  in, so `tests/acceptance.py` maps `/Calisthenics-App/` to its own repo root rather than serving the
  real `D:/Projects/Calisthenics-App`.
- Default program source: the private v4 file (`gh api repos/Estaed/Calisthenics-Data/contents/calisthenics-data.json`,
  read only, kept outside the repo); its program sits in `weeks[0].days` with `plans["3"]` naming the day
  ids; pairs (↔) from `D:/TarikOS/600-Life 🌿/Health/Antrenman.md` → *Güncel program — v2* if the v4 file lacks them.
- Integration: the orchestrator adds registry lines, the `importScripts('sw-alert.js')` line and bumps the cache name.
- Task-03's real push and pull with Tarık's token on a test path runs before Monday, by the orchestrator.
