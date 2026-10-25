# Changelog

All notable changes to Sthenos are written here. The format follows
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) and the numbers follow
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):

- **0.y.z** until v1 (the Blueprint's "Done when" holds); **1.0.0** is v1.
- **MINOR** (0.2.0, 1.1.0): one wave of features. **PATCH** (0.2.1): fixes and small changes between waves.
- **MAJOR** (2.0.0): a change that breaks what exists (the stored data needs a migration, a command or API changes).
- The release string a deploy needs (a service worker cache, a package version) is this file's newest version.

Each wave adds its lines under *Unreleased* as it lands; the closing wave turns *Unreleased* into the new version
with the date. What later versions will bring lives in `notes.md` → *After v1* and `docs/TASKS_INDEX.md`.

Versions before 0.2.0 were numbered afterwards, from the git history; the service worker cache went `cali-app-v2`
to `cali-app-v13` then.

## [Unreleased]

## [0.3.0] - 2026-10-26

### Added
- Muscle map, from a button beside the hourglass: front and back body for the week in view, a Week / per-day filter,
  colour from pale orange to red with the fractional sets, the least worked muscle, bars that fill orange with sets
  done; a tap on a muscle lists the exercises behind it (Task-06).
- The program editor's Muscles field: each exercise's muscles as chips (main, helper, off), guessed from its name.

### Changed
- While the day's clock shows, the top bar says "W1" instead of "Week 1", and a finished day's Summary is an icon,
  so the bar holds the muscle button at 360 px.

## [0.2.0] - 2026-10-26

### Added
- Settings → Programs: list, new, duplicate, rename, delete, import a program file; days and exercises added,
  renamed, reordered and paired; "Use this program" now on an empty week, else from the next week (Task-05).
- An exercise's note opens from an info mark: a dialog on a timed tile, the top of the editor on a row.
- On a short day the rows grow to reach the docked sheet, with room kept for Undo.

### Changed
- Built-in program v4: pull-ups on A and C, dips on A and B, a chest-supported row on B and C, a 7-minute
  mobility tile; days named A, B, C.
- The version comes from this file; the service worker cache is `cali-app-v<version>`.

## [0.1.1] - 2026-10-25

### Changed
- Built-in program v3: six lifts a day, shorter names, form cues in each exercise's note.

## [0.1.0] - 2026-10-24

### Added
- The workout day on one screen: tap logging (tap, tap again, hold), pair order, rest timer, start and finish with
  a summary (Task-01).
- An independent timer and alerts that reach the phone with the screen off (Task-02).
- Settings, sync to the user's own private GitHub repository, JSON backup and restore (Task-03).
- Weeks with double progression, the week menu and Finish week with Undo (Task-04).
- The shell, the v5 data core and the acceptance gate; the old app moved to `legacy/` (Task-00).
