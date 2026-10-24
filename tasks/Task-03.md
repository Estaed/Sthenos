# Task-03: Settings, sync and backup
> **Execution:** agent `ultracode`
> *Why:* Tarık's data must reach his private repo; everyone else needs settings and a backup.

**Lane**
- OWNS: `app/settings.js`, `app/settings.css`, `app/sync.js`, `tests/test_settings.py`, `tests/test_sync.py`
- MUST NOT TOUCH: `app/core.js` (Task-00), `app/workout.js` (Task-01), `app/timer.js` (Task-02), `app/week.js` (Task-04), `legacy/`
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
A Settings screen (screen 5) for rest times, start rest after a log, heads-up, vibrate, sound, keep
awake, default load step and theme (system / light / dark); a GitHub section where Tarık pastes his
fine-grained token once and sees the sync state; JSON backup download and restore. Someone without a
token uses the app fully, offline, with only the backup.

## Why
The sync is what keeps a lost phone from losing months of training; the policy is Blueprint → Rules.

## Acceptance
- [ ] Port of the old app's GitHub sync (`legacy/index.html`, its sync section: config, safe fetch,
  repo check, error messages, sha handling). Deliver a port map: each function group ported, merged or
  dropped, and why; acceptance tests follow the old behaviour.
- [ ] Target `Estaed/Calisthenics-Data` → `calisthenics-data.json` (v5); on first push with a v4 file
  there, the v4 file is copied to `archive/` first and never overwritten in place.
- [ ] Push policy: a day's edits at Done; an edit to a finished day or a program at once; anything
  older than 12 h on the next open. Pull on open; a remote `sha` mismatch never overwrites silently.
- [ ] The token lives only under `cali.sync`; never in the document, the backup or a log line.
- [ ] Backup: download the whole v5 document as JSON; restore validates it before replacing.
- [ ] Settings are read by other features through core; changing rest to 60 s changes the next rest.
- [ ] Tests run against the mocked GitHub API in both states (no token; token with an existing file).
- [ ] (eye) screen 5 of `design/r6/screens.html`, both modes.

## Out of scope
- Programs list and editor (wave 2), sync for people without GitHub (*After v1*).
