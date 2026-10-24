# Task-03: Settings, sync and backup
**Status: DONE** — verified 2026-10-24, eye check pending: 1
> **Execution:** agent `ultracode`
> *Why:* Tarık's data must reach his private repo; everyone else needs settings and a backup.

**Lane**
- OWNS: `app/settings.js`, `app/settings.css`, `app/sync.js`, `tests/test_settings.py`, `tests/test_sync.py`
- MUST NOT TOUCH: `app/core.js` (Task-00), `app/workout.js` (Task-01), `app/timer.js`, `app/alert.js` (Task-02), `app/week.js`, `app/progress.js` (Task-04), `legacy/`
- GATE: `python tests/acceptance.py` (from the repo root)
- DEPENDS ON: Task-00

## Goal
A Settings screen (screen 5) for rest times, start rest after a log, heads-up, vibrate, sound, keep
awake, default load step and theme (system / light / dark, applied app-wide); an alerts section with
"Allow notifications" (`Cali.alert.requestPermission()`), "Test alert" (`Cali.alert('test')`) and one
line, shown only while permission is not granted, saying the alert then needs the screen kept awake and
how to allow site notifications (Tarık's first request returned `denied` until he allowed them); a GitHub section showing the sync
state; JSON backup download and restore. Without a token the app works fully, offline.

## Why
The sync keeps a lost phone from losing months of training; the policy is Blueprint → Rules.

## Acceptance
- [x] Port of the old app's GitHub sync (`legacy/index.html`, its sync section ~3400-3860: config, safe
  fetch, repo check, error messages, sha handling, the `pushDue`/`dirtySince` gate, the conflict modal with
  its text in English). Deliver a port map: each function group ported, merged or dropped, and why;
  acceptance tests follow the old behaviour where the Blueprint does not change it.
- [x] Token: on first open, if `cali.sync` is empty and the old `cali_sync_config` holds a token, it is
  copied once (read only; the old key is never written). The token never enters the document, the
  backup or a log line.
- [x] Target `Estaed/Calisthenics-Data` → `calisthenics-data.json`. A remote without `_version: 5` is never
  adopted: it is first copied to `archive/calisthenics-data-v4.json`, then replaced; a test fails the
  second PUT and proves the v4 copy and the original are both intact and the next open retries.
- [x] Push policy: a day's edits on `dayDone`; `weekFinished`, an edit to a finished day or a program at
  once; anything older than 12 h on the next open; nothing mid-day from timers or visibility. Pull on
  open; a remote `sha` mismatch opens the conflict choice, never a silent overwrite.
- [x] Backup: download the whole v5 document as JSON; restore validates `_version: 5` before replacing.
- [x] Changing rest to 60 s changes the next rest (through `Cali.settings`).
- [x] Tests run against the mocked GitHub API in both states (no token; token with a v4 file there).
- [x] Before Monday, the orchestrator runs one real push and pull with Tarık's token on a test path and
  reports the result.
- [ ] (eye) screen 5 of `design/screens.html`, both modes.

## Out of scope
- Programs list and editor (wave 2), sync for people without GitHub (*After v1*).
