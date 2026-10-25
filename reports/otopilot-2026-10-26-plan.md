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
