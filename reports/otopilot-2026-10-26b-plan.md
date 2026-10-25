# otopilot plan, 2026-10-26 (b): Sthenos wave 2b

- SOURCE: tasks (Task-06 only). UNTIL: done. Asked by Tarık 2026-10-26 after seeing the muscle map's first look
  (design/muscles.html): orange-to-red scale, week-in-view, day filter, muscles picked per exercise ("önerini yap").
- Direction: orchestrator claude (this interactive session), delegate claude. Wave of one: one general-purpose Opus
  builder (`opus`/`xhigh`) in its own worktree, no Workflow.
- BASE_SHA: 2f57d3ce5865d873ef326aa7bef99cf5611b9db4. Preflight `onkontrol.py . --tasks 06 --orchestrator claude
  --delegate claude --features 1` → OVERALL OK; quota GO (5-hour 17 %).
- Acceptance attacked by a fresh `auditor` (opus/high) before hand-over; its holes are in Task-06.
- Review lens: none (no data-loss path; core still guards the document).

| Task | Engine | Model | Gate | Eye |
|---|---|---|---|---|
| Task-06 Muscle map | Opus builder in worktree | opus / xhigh | `python tests/acceptance.py` | muscle screen + Muscles field, 360 px, both themes |

## Closeout (2026-10-26)
- Task-06: GREEN. Builder commit e62ae08 (one commit inside OWNS), gate in worktree 57 PASS, cherry-picked as 23c0b31.
- Gap the builder reported and the orchestrator fixed on main (outside the builder's OWNS, under 100 lines): at 360 px
  the top bar had no room for the muscle button while the clock showed, so it hid. Now "Week N" shows as "WN" and the
  clock pill tightens while the clock shows, and a finished day's Summary is an icon; measured: the button keeps 44 px
  idle, at 20 min, at 1 h 10 min and on a finished day.
- Use check on Tarık's real document (no `muscles` stored, counted through the name guess): Week and day B in both
  themes. Gate on main 57 PASS. Release 0.3.0 (`cali-app-v0.3.0`). Eye check pending: 1.
- Not run: Impeccable (the builder's npx call was denied); avoid-ai-design 0 findings.

Run closed: the one approved task is green on main, eye check pending.
