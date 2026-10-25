# Task-05: Programs: list, editor, import, use now or from next week
> **Execution:** agent `ultracode`
> *Why:* product code with one owner and no parallel partner: one Opus agent builds it end to end, the main loop gates it.

**Lane**
- OWNS: `app/program.js`, `app/program.css`, `tests/test_program.py`, `app/registry.js` (append only), `app/settings.js` (only the row that opens Programs)
- MUST NOT TOUCH: `app/core.js` (Task-00), `app/workout.js`, `app/summary.js` (Task-01), `app/timer.js`, `app/alert.js` (Task-02), `app/sync.js` (Task-03), `app/week.js`, `app/progress.js` (Task-04), `app/default-program.js` (main loop), `sw.js` (orchestrator bumps the cache)
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-04

## Goal
Anyone who opens Sthenos can set up the training they actually do without Eko and without editing a file:
Tarık making a 4-day split next month, or a stranger on their first day replacing the built-in program with
their own. From Settings → Programs they see every program, which one this week runs and which one the next
week will run; they can create a program (blank or a copy), rename and delete one, and inside it add, rename,
remove and reorder days and exercises and set every exercise field the Blueprint's schema has (name, kind
reps/time/check, sets, rep range, target, load, load step, bodyweight, paired with the next exercise, note,
duration for a timed check row). Day names are free text (the built-in program's days are `A`, `B`, `C`). They
can import a program JSON file (Eko writes one, or another person shares one). Then "Use this program": when
the current week has no set stored, the current week is rebuilt from it at once (the stranger sees it
immediately); otherwise it becomes `nextProgram` and the screen says it starts with the next week. The judge is
Tarık at the gym bench, one hand, phone at 360 px: building a 4-day program from a copy must feel quicker than
writing it to Eko.

The program editor edits programs; the in-card editor on the day screen stays the one way to change the week
in hand (Blueprint → Rules). So an edit made here reaches the current week only when that week has no set
stored (it is rebuilt); a week with sets keeps its copy and the edit shows from the next week, and the editor
says so in one line.

## Why
Blueprint → Decisions: Settings → Programs (edit, duplicate, import, use now or from next week). Today only the
in-card editor exists (load, target, sets, range, step, name); a stranger cannot leave the built-in program and
day names cannot be changed (Tarık 2026-10-25: "A B C diye yap isim koymana gerek yok ya da editlenebilir
yap"). Tarık left how it works to Eko (2026-10-25: "sana bıraktım nasıl olacağını").

## Acceptance
- [ ] `tests/test_program.py` (run by the gate; it starts its own server through `acceptance.py`'s helpers and
  collects its own console errors) works through the visible controls with touch taps, never by calling
  `Cali.change` itself, and checks the stored document after each step: create blank, duplicate, rename,
  delete; add, rename, remove and reorder a day and an exercise; every field above saved.
- [ ] A new exercise starts usable with only its name typed (reps, 3 sets, 8–12, target 8, load 0, the
  settings' load step). Switching its kind rewrites the dependent fields to what core accepts (time/check: no rep
  range; check: target 1); a change core refuses leaves one plain line on screen, never a silent loss.
- [ ] The path "duplicate the built-in program, add day D, add one exercise and name it, use the program" is
  walked in the test and its tap count printed; the main loop reads it.
- [ ] Pairing: pairing two adjacent exercises gives both one `pair` value unused elsewhere in that day; unpairing
  or moving either one away clears it on both.
- [ ] Duplicate keeps day and exercise ids (history and progression are keyed by them, so a copy continues the
  log); a new day or exercise gets an id unused in every program, never containing ':'.
- [ ] Use this program: on a current week with no set stored (a set at 0 is stored) the week is rebuilt from it,
  keeping that week's `n` and `startedAt`, and `activeProgram` and `nextProgram` follow; on a week with any set
  stored nothing in it changes and only `nextProgram` moves; Finish week then builds from it. Use is refused,
  with the reason on screen, for a program with a day that has no exercise.
- [ ] Delete asks first; it is refused (with the reason) for the program the current week or `nextProgram` uses
  and for any program a stored week names (core requires every `week.program` to exist), so in practice only a
  never-used program can go. Removing a day or exercise asks first too.
- [ ] Import takes one program object (not a whole document). It is added under a fresh program id when its id
  is taken; its day and exercise ids are kept, so a file can continue an exercise's history on purpose. A file
  core refuses (not JSON, an unknown kind, sets outside 1–20, a rep range with min above max, an id with ':', a
  day or exercise id twice) is refused with one plain line saying why and the document is unchanged. The checks
  are core's (`Cali.change` throws on a document of the wrong shape), translated, not a second copy.
- [ ] A program change pushes at once (sync already treats any change to `programs`, `activeProgram` or
  `nextProgram` as urgent); the GitHub token never enters the document.
- [ ] (eye) Settings → Programs and the program editor at 360 px, both themes, built from the components
  Settings (screen 5 of `design/screens.html`, shot `design/shots/05-settings-*.png`) and the in-card exercise
  editor already use; no new component kind. Walk it as Tarık would: duplicate, add a day D, add two exercises,
  pair them, rename the days, use it; every control a 44 px target; no name cut where a full name fits.

## Out of scope
- Exercise swap when a machine is busy, a starter template library, exporting a program file, history and body
  weight screens (later wave 2 tasks).
- The built-in program's content (main loop, `app/default-program.js`).

Fixed: routes are registered through `Cali.route` and opened with `Cali.go`; new ids never contain ':' (core
rule); UI text in English; every visual change follows `D:/TarikOS/.brain/skills/tasarim/SKILL.md`.
