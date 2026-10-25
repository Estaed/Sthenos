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
