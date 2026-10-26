# AGENTS.md — Sthenos (Android PWA, vanilla JS, no build step (Pantry's stack))

This is Tarık's **Sthenos** project. The
brain is `D:/TarikOS`; read it for anything outside this project. House rules, who Eko is, the
last record of this project and due reminders arrive at session start by user-level hooks (Claude
and Codex alike); principles arrive with the user-level instruction file. If that context is
missing or cut, read the sources: `D:/TarikOS/850-Companion 🔮/Kurallar.md` (house rules),
`Core.md` and `Kisilik.md` next to it (identity, Tarık's patterns), and `D:/TarikOS/AGENTS.md`
(where things live in the brain). Skills are global, so never copy them here. A rule in this
file stays consistent with the house rules; a deliberate exception is stated here explicitly.

**How this project runs** (PRINCIPLES #7, Project lane): ideas and notes go in `notes.md`, and
anything v1 doesn't need goes under *After v1* → `compass` if the approach is open → Blueprint
(`docs/blueprint.md`, `blueprint` skill) → v1, the simplest complete version, in waves: `plan-wave` writes the next
wave (every v1 feature ready to run at once), `otopilot` runs it → Tarık looks at each wave and the next is chosen together.
After v1, growth comes from what the running product showed.

**Where things go.** A folder is created the first time something belongs in it, never as an
empty skeleton; when a topic outgrows `notes.md`, it moves to its own file in the matching folder
and `notes.md` keeps a one-line link.

- `notes.md`: goal, ideas, *After v1*.
- `references/`: material Tarık brings (brief, rubric, PDFs, links, sample data); read, not edited.
- `design/`: the visual source of truth (`design/screens.html` prototype and its screenshots), a
  `design/DESIGN.md` holding only what this project overrides, and `design/deviations.md`. The base
  design language is `D:/TarikOS/.brain/skills/tasarim/references/DESIGN.md`; read it before any UI
  work and never copy it here. The only files copied from there are its code tokens (`tokens.css`
  or `tarik_theme.dart`), unchanged, into the app's theme folder.
- `reports/`: research, `compass` and spike write-ups, otopilot reports and `screens/`; dated, input not decisions.
- `docs/`: `blueprint.md` (the plan: what v1 is, stack, layout, decisions), long specs, and
  `docs/TASKS_INDEX.md`.
- `tasks/`: task files, only when `plan-wave` writes them.

## Sthenos at a glance
<!-- Written with the Blueprint: what the project is in two or three sentences, and its dates. -->

- **Read `docs/blueprint.md` before** planning a task, changing a stage, the screen or a number,
  and whenever code seems to contradict a decision.
- **What:** Sthenos (Greek "strength"; Tarık 2026-10-24), a public workout-log PWA; the data repo keeps its name; the GitHub repo is `Estaed/Sthenos`, live at `https://estaed.github.io/Sthenos/` (2026-10-24); the local folder is `D:/Projects/Sthenos` (2026-10-25); Tarık syncs to private `Estaed/Calisthenics-Data` with his key. v1 wave 1 due Monday 2026-10-26.
- **Code:** `index.html` shell, `app/` one script per feature + `app/registry.js`, `tests/`, `design/screens.html` (look), `legacy/` (old app).
- **Commands:** serve `python -m http.server` from `D:/Projects` and open `/Sthenos/`; test `python tests/acceptance.py` (serves the repo under `/Sthenos/` itself).
- **Gate:** `python tests/acceptance.py` from the repo root; clean = every check PASS, exit 0.

## Constraints
- localStorage keys start with `cali.`; never write the legacy app's keys (`cali4_*`, `cali_sync_config`) or any `pantry.*` key; `pantry.v1` and `cali_sync_config` are read only.
- The GitHub token never enters the synced document or the repo.
- Reps are entered only by tapping the set cell (tap, tap again, hold); no second input path.
- Timers are computed from stored start timestamps, never from counted ticks.
- A set is written only through `Cali.log`; a week copies program values when built, so a program edit never rewrites history.
- Every visual change follows `D:/TarikOS/.brain/skills/tasarim/SKILL.md` and `design/screens.html`; intended breaks go to `design/deviations.md`.
- UI text in English; `tokens.css` copied unchanged from Tarik Base v6.
- Personal data (logs, body weight) never enters this repo; tests use fixtures.
