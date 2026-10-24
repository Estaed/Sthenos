# Otopilot report — 2026-10-24

Plan: `reports/otopilot-2026-10-24-plan.md`. Direction Claude → Claude; orchestrator this interactive session.

## Wave 0 — Task-00 (one Opus builder, `opus`/`xhigh`)
| Task | Outcome | Main SHA | Evidence |
|---|---|---|---|
| Task-00 | DONE, eye check pending: 1 | `fde8b06` | gate in worktree and on main: 46 PASS, exit 0; builder's red runs: tap stores target − 1 → 6 FAIL, service worker deletes every cache → 1 FAIL |

- Builder: 27 min, 76 tool calls. Old app moved to `legacy/` with history; legacy suite still 88 PASS from its new place.
- Codex lens (`gpt-6.1-sol`/high, read-only): one real finding — a past week read exercise rules from the
  current program, so a program edit changed history (logged 6 reps shown as `6s`). Reproduced, fixed by the
  orchestrator in the lane (week copies each exercise's rules in `Cali.weekFrom`; `weekExercise` and `tap`
  read the copy), new check fails without the fix (2 FAIL) and passes with it; folded into the Task-00 commit.
- Blueprint amended (Tarık's call, 2026-10-24): a `time` row all at target → +5 s (screen 6 "Plank +5 s"
  contradicted Task-04's "time rows copy"); the week shape now names the copied rules. Task-04 updated to match.
- Eye: day A at 360×740 follows screen 7's structure (shots in `D:/Projects/_work/cali-t00/shots/`); polish is Task-01.

## Wave 1 — Task-01..04 (ultracode Workflow `wf_ae656432-606`, started 13:45)
- BASE_SHA `fde8b06`; quota before: Claude 5-hour 50%, weekly 19%; Codex 3% weekly.
- Lenses: Task-01 screen; Task-02 screen; Task-03 screen + spec; Task-04 spec. Codex lens per feature in Phase 3.
- Shared files: each lane appends its own `app/registry.js` lines; Task-02 appends `importScripts('sw-alert.js')`
  to `sw.js`; the orchestrator merges them and bumps the cache name at integration.

- Workflow: 29 agents, 152 min wall clock, 3 review rounds per feature; every lane ended as one commit over `fde8b06`.
- Quota: Claude weekly 19 % → 26 %, 5-hour 50 % → 18 % (window reset during the run); Codex weekly 3 %.

| Task | Outcome | Main SHA | Evidence |
|---|---|---|---|
| Task-01 | DONE, eye check pending: 1 | `628f70c` | lane gate ALL PASS; red runs: bounce filter off → 4 FAIL, summary ignoring Cali.progress → 1 FAIL |
| Task-02 | DONE, eye check pending: 1 | `91b5ad4` | lane gate red only on Task-00's slot check; settled on main (`a7c0f1c`), then ALL PASS |
| Task-03 | DONE, eye check pending: 1 | `3833e68` | lane gate ALL PASS; real push and pull on `sthenos-test/` in the data repo (below) |
| Task-04 | DONE, eye check pending: 1 | `8d2db0b` | lane gate ALL PASS; gate on main with all four: 54 PASS, exit 0 |

### Integration
- `app/registry.js`: the four lanes' appended lines merged in task order; `sw.js` keeps `importScripts('sw-alert.js')`;
  cache `cali-app-v1` → `cali-app-v2`.
- Old-look test assertions changed, behaviour kept: Task-00's slot check counts only its own nodes (the timer's pill
  and button now share the top bar); the timer check measures its button against its holder (Start/Finish follows
  it); the summary test supplies its own no-change progress (Task-04's rules replaced the stub); the alert test
  unlocks sound with a tap on the column header (Task-04's week menu replaced the "Week N" text).
- Use check on Tarık's default program at 360×740, light and dark (shots in `D:/Projects/_work/cali-w1/use/shots/`):
  day A fits with the sheet; a tap logs 6, a second tap 5/6 with the orange ring; the pair moves to the dip with pair
  rest 1:30 draining; timer, settings, week menu, Finish week confirmation and the day summary all render with no
  console error.
- Real sync (Task-03's last box): the app connected with Tarık's GitHub token, every contents path moved under
  `sthenos-test/`: first connection pushed the v5 document, Done pushed the logged set and finishedAt, a second
  fresh phone connected and pulled identical weeks; the token was in neither the remote document nor any key but
  `cali.sync`. The test file was deleted afterwards; `calisthenics-data.json` (v4) was not touched.

### Codex lens (`gpt-6.1-sol`/high, read-only, final commits)
- Task-01: 2 findings, both rejected (contract-conform behaviour). Task-02: 1 real, minor, left (a countdown ending
  resets a half-typed custom length). Task-03: 2 real, left: first connection with edited loads but no sets takes
  GitHub's copy (latent: no load edit exists yet); a push queued during the conflict's upload waits for the next
  trigger (nothing lost). Task-04: 1 real, latent until wave 2: Finish week into a `nextProgram` with a changed range
  keeps the old target. All logged in `review-calibration.md`.

### Needs Tarık
- **The pencil (load edit) is missing.** The Blueprint has it ("the pencil in the sheet edits load, never reps"),
  screens 1, 2, 7, 8 show it, but no wave-1 task owned it. Without it a wrong load in the default program cannot be
  fixed in the app on Monday. Small work (one sheet, `Cali.change` on the week's load); fix the Task-03 pristine
  check in the same change.
- Eye: screens 1, 2, 6, 7, 8 (Task-01), 2 and 4 (Task-02), 5 (Task-03), 3 (Task-04) of `design/r6/screens.html`, on
  the phone after the install.

Run closed: every approved task DONE on main (eye checks pending: 5, Task-00 included).
