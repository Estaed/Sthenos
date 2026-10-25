# otopilot plan, 2026-10-26: Sthenos wave 2a

- SOURCE: tasks (Task-05 only). UNTIL: done.
- Asked by Tarık 2026-10-25 ("şimdiden program ekleme yapalım, sana bıraktım nasıl olacağını"); Task-05 stays inside that ask.
- Direction: orchestrator claude (this interactive session), delegate claude. Wave of one: one general-purpose Opus
  builder (`opus`/`xhigh`) in its own worktree, no Workflow (otopilot SKILL.md, wave of one).
- BASE_SHA: c03a6873c1727ecca14e1096268c066fdfcd22dc. Preflight: `onkontrol.py . --tasks 05 --orchestrator claude
  --delegate claude --features 1` → OVERALL OK; quota GO (5-hour 5 %, ~4 weekly points for one feature). On AC power.
- Review lens: none (no data-loss path beyond what core's Cali.change guards; sets are written only by Cali.log).
- Acceptance attacked before hand-over by a fresh `auditor` (opus/high); its holes were written into Task-05.
- PREVIOUSLY TRIED: none (notes.md After v1 has no program editor attempt).

| Task | Engine | Model | OWNS | Gate | Eye |
|---|---|---|---|---|---|
| Task-05 Programs editor | Opus builder in worktree | opus / xhigh | app/program.js, app/program.css, tests/test_program.py, app/registry.js (append), app/settings.js (Programs row) | `python tests/acceptance.py` | Settings → Programs and editor at 360 px, both themes |

Integration: the orchestrator gates in the worktree, cherry-picks the one commit, bumps `sw.js` cache, gates main,
walks the editor at 360 px, then marks DONE with `eye check pending: 1`.

## Closeout (2026-10-26)
- Task-05: GREEN. Builder commit 4e93b05 (one commit inside OWNS), gate in worktree 56 PASS, cherry-picked as 0baab64,
  cache v10, gate on main 56 PASS, DONE in f188e1a. Use check on Tarık's real document: Programs list and editor
  open, week 1 is reported as having sets (one set at 0 from 2026-10-24), so edits show from week 2. Eye check pending: 1.
- Builder's open point: Finish week carries load and target on from the week before for every exercise the week had,
  so a load or target typed in the program editor for such an exercise does not reach the next week (app/week.js).
- Worktree removed (no junctions). Cost: Claude weekly 1 → 3 % (shared with research and program work).

Run closed: the one approved task is green on main, eye check pending.
