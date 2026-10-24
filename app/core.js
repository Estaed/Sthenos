/* Calisthenics core (app/core.js): the v5 document, storage, the rules, routes, events and the feature loader.
   The only file in app/ that touches localStorage. Features reach everything through window.Cali, never edit this
   file or another feature's, and are listed once in app/registry.js. Blueprint: docs/blueprint.md (Data, Rules).

   Storage (localStorage; every key starts with "cali.")
     'cali.v5'      the document (below). Written only here; a stored document that cannot be read, or one saved by
                    a newer app, is never written over (Cali.problem() says why, every write throws).
     'cali.sync'    the sync feature's own object (token, last sha, errors) plus the dirty marks core keeps there.
                    The token lives here and never enters the document, a backup or a log line.
     'cali.timers'  the running timers (Cali.timers), on this phone only; never synced.
     The old app's keys (cali4_*, cali_sync_config) and Pantry's (pantry.*) are never written; two are readable
     through Cali.readOnly(key).

   The document (schema v5, Blueprint -> Data), deep-frozen: read it, never mutate it.
     { _version: 5, updatedAt: ISO, programs: [program], activeProgram: id, nextProgram: id, weeks: [week],
       body: [{ date: 'YYYY-MM-DD', kg }], settings: { <key>: value } }
     program  { id, name, days: [{ id, name, exercises: [exercise] }] }
     exercise { id, name, kind: 'reps'|'time'|'check', sets: count, target, repMin, repMax, load, loadStep,
                bodyweight?, pair?, note?, duration? }
              reps: target and the range in reps. time: target in seconds, repMin/repMax null. check: target 1,
              repMin/repMax null, duration? = the countdown in seconds of a timed one-off row (stretch, walk).
              load: kg, the added load when bodyweight is true (0 = bodyweight only). pair: adjacent exercises of a
              day with the same pair are done alternately. Day and exercise ids never contain ':'.
     week     { n, program: id, startedAt: ISO, finishedAt?: ISO, days: { <dayId>: { startedAt?, finishedAt?,
                exercises: { <exId>: { name, kind, repMin, repMax, loadStep, bodyweight?, pair?, note?, duration?,
                load, target, sets: [null | { r, at: ISO, pain?: true }] } } } } }
              Weeks are numbered 1, 2, 3 ... in order; the last one is the current week. sets has one entry per
              set (null = not logged). A week copies its program's exercise rules, load and target when built, so
              a program edit never rewrites history (a week without the copied rules falls back to its program).
     First open: the document is built from app/default-program.js (CALI_DEFAULT_PROGRAM) with week 1 from
     activeProgram, every setting at its default, no logs; it is saved with dirty = false.

   Data
     Cali.doc()                      the current document (frozen).
     Cali.change(fn, opts)           fn(draft) edits a deep copy (or returns a whole new document); the result is
                                     checked, saved and announced; returns the new document. opts.why (a short
                                     word, default 'edit'), opts.detail (an object passed on), opts.dirty (default
                                     true: the sync feature has something to push). Throws and saves nothing when
                                     the shape is wrong, storage is full, Cali.problem() is set, or fn added,
                                     removed or changed a logged set: sets are written only by Cali.log.
     Cali.replace(doc, opts)         replaces the whole document (a sync pull, a backup restore) after the same
                                     check; refuses anything without _version 5. opts.why (default 'replace'),
                                     opts.dirty (default false). Logged sets may differ here.
     Cali.problem()                  null, or a plain sentence saying why the stored document cannot be used.
     Cali.dirty(), Cali.changes()    true while a dirty change has not been pushed; a counter that grows with each.
     Cali.markClean(upTo)            the sync feature calls it after a push with Cali.changes() read when the push
                                     started; a change made during the push keeps it dirty. 'cali.sync' carries
                                     dirty, changes and dirtySince (ISO of the oldest unpushed change).
     Cali.syncState()                a copy of the 'cali.sync' object.
     Cali.setSyncState(patch)        merges patch into 'cali.sync', saves it, emits 'sync' { state }.
     Cali.readOnly(key)              the raw text of 'cali_sync_config' or 'pantry.v1' (null when absent); any other
                                     key throws. Nothing in the app writes either.
     Cali.program(id)                a program by id; no id: the active program. null when absent.
     Cali.week(n)                    week n; no n: the current (last) week. null when absent.
     Cali.weekFrom(program, n)       a new unfrozen week n built from a program (or its id): every exercise's rules,
                                     load and target copied, every set null, startedAt now. Use it inside Cali.change.
     Cali.weekExercise(n, dayId, exId)  one exercise of week n (null n: current) as the rules see it: the week's
                                     copied fields (else the program's) (id, name, kind, repMin, repMax, loadStep, bodyweight, pair, note,
                                     duration) with the week's load, target and sets, plus week and dayId. null
                                     when the week has no such exercise. Frozen.
     Cali.dayExercises(n, dayId)     the day's weekExercises in program order.
     Cali.history(dayId, exId, n)    that exercise in the weeks before week n (null n: the current week), newest
                                     first: [{ week, load, target, sets, dayDone }], dayDone = the day has finishedAt.
     Cali.dayArgs(args)              the day route's args made whole: { week, dayId, readOnly }. Unknown or missing
                                     week: the current week; unknown or missing dayId: the first day of that week
                                     not finished, else the first; readOnly is true for any week but the current.

   Rules (Blueprint -> Rules)
     Cali.log(dayId, exId, i, value) the only writer of a set: set i of an exercise of the current week. value is a
                                     number (reps, seconds, or 1 for a check), null (clears it), or { r, at?, pain? }
                                     to put back an exact earlier value (Undo). A number keeps the set's pain flag.
                                     Returns the stored set or null; emits 'change' then 'log'. Throws on an unknown
                                     day, exercise or index.
     Cali.tap(dayId, exId, i)        the tap rule: an empty set gets the target; a logged one goes one down (reps 1,
                                     time 5 s) to 0, then empty; a check toggles between 1 and empty. Calls Cali.log.
     Cali.hold(dayId, exId, i)       the hold rule: one up (an empty set: target + 1 step); a check toggles.
     Cali.setOrder(dayId, n)         the day's sets in doing order: a pair alternates set by set (A1 B1 A2 B2 A3,
                                     unequal counts end on the longer one), single exercises run through: [{ exId, i }].
     Cali.nextSet(dayId, n)          the first set in that order that is not logged, or null.
     Cali.progress(weekExercise, history)  next week's { load, target, reason } for one exercise: weekExercise from
                                     Cali.weekExercise(n, ...), history from Cali.history(dayId, exId, n). Filled by
                                     app/progress.js through Cali.provide('progress', fn); here a stub that answers
                                     { load, target, reason: 'no change' }. A result of the wrong shape throws.
     Cali.settings.get(key)          a setting, its default when unset. Keys and defaults: restPair 90 and
                                     restExercise 120 (seconds), restAfterLog true, headsUp 10 (seconds before the
                                     end; 0 = off), vibrate true, sound true, keepAwake true, loadStep 2.5 (kg),
                                     theme 'system' ('light', 'dark'). An unknown key throws.
     Cali.settings.set(key, value)   validates and saves it (Cali.change, why 'settings', detail { key, value }).
     Cali.settings.all()             every setting with defaults filled in.
     Cali.settings.defaults          the defaults (frozen).
     Theme (no member): core puts settings.theme on <html data-theme> ('light' or 'dark'; 'system' follows the
     phone, live), color-scheme and the theme-color meta, after every change.

   Time
     Cali.now()                      the clock every rule and timer reads (ms). It is Date.now(): tests drive it with
                                     Playwright's clock (install, pause_at, run_for), which also drives setTimeout.
     Cali.iso(ms)                    ms (default Cali.now()) as an ISO string; documents store ISO strings.
     Cali.timers                     several timers at once (the rest timer and the independent timer), each kept as
                                     start timestamps in 'cali.timers' and computed from Cali.now() when read, never
                                     from counted ticks, so they are right after the phone slept or the app reloaded.
       .start(name, { duration?, kind?, data? })  starts (or restarts) a timer: a countdown of duration ms, else a
                                     stopwatch. kind and data (JSON) are the caller's. Returns the timer.
       .get(name)                    null or { name, kind, data, duration, startedAt, pausedAt, pausedMs, laps,
                                     running, elapsed, remaining, endAt, done }: elapsed ms, remaining ms (null for a
                                     stopwatch), endAt ms while a countdown runs (else null), done = remaining is 0.
       .list()                       every timer, as get() gives it.
       .pause(name), .resume(name)   pausing keeps the elapsed time; resuming goes on from it.
       .add(name, ms)                lengthens a countdown (+1 min).  .lap(name) adds a lap at the elapsed time.
       .stop(name)                   removes it. Every call emits 'timer' { name, action, timer } (timer null on stop).

   Alerts (Task-02 fills them through Cali.provide('alert', { alert, schedule, cancel, requestPermission }))
     Cali.alert(kind)                beep, vibration and the visual change for 'rest', 'headsup', 'timer' or 'test'.
     Cali.alert.schedule(kind, endAt, tag)  an alert at endAt (ms) under tag, so it can be cancelled.
     Cali.alert.cancel(tag)          drops a scheduled alert.
     Cali.alert.requestPermission()  asks for notifications; a Promise of the permission state.
     Here they are no-op stubs (requestPermission answers the current state without asking). An unknown kind, an
     endAt that is not a number or an empty tag throws, stub or not.
     Cali.provide(name, impl)        installs the implementation behind Cali.progress ('progress', a function) or
                                     Cali.alert ('alert', the four functions above).

   Events
     Cali.on(event, fn)              subscribes; returns the unsubscribe function. A handler that throws is logged as
                                     an error and the others still run.
     Cali.emit(event, payload)       calls the handlers of event in order. Core emits:
       'change'        { why, detail, dirty, doc, prev } after every saved change (why 'log' carries detail
                       { week, dayId, exId, i }; 'replace', 'settings', 'storage' when another tab saved, ...).
       'log'           { week, dayId, exId, i, value, prev } after Cali.log: value and prev are the stored set
                       objects or null, so Cali.log(dayId, exId, i, prev) undoes it exactly.
       'timer'         { name, action, timer } after a Cali.timers call.
       'sync'          { state } after Cali.setSyncState.
       'route'         { name, args } after a screen is shown.
     Features emit, with these payloads: 'dayDone' { week, dayId } (the workout's Done, after it stored the day's
     finishedAt); 'weekFinished' { week, next } (Finish week, after it stored the finished week and built week next).

   Screens (hash routes '#/<name>?<key>=<JSON value>&...'; no route or an unknown one opens 'day')
     Cali.route(name, def)           registers a screen. def.render(root, args) fills a fresh <section class="screen"
                                     data-screen="<name>">; def.update(root, args, change) (optional) runs after every
                                     'change' while it is shown (no update: nothing happens); def.leave() (optional)
                                     runs when another screen replaces it. Routes: 'day' { week, dayId, readOnly }
                                     (the workout), 'timer' { countdown } (seconds), 'settings', 'summary' { dayId }.
     Cali.go(name, args, opts)       opens a screen with an args object and adds a history entry (opts.replace:
                                     replaces the current one), so the phone's back gesture returns. A name with no
                                     registered route opens 'day' with no args, replacing the entry, and warns.
     Cali.back()                     one screen back; the day when there is nothing to go back to.
     Cali.current()                  { name, args } of the screen shown, or null before the first.
     Cali.slot(name, node, order)    puts a feature's node into every screen's <… data-slot="name"> holder, now and
                                     after each render or update: 'topbar' (the day screen's app bar between the
                                     session clock and Finish: the timer pill at its start; the timer and settings
                                     buttons on the right, the first of them with class slot-end) or 'dayheader' (the
                                     day screen's week label: the week menu). Nodes sit in order (a number, default 0; ties keep the order
                                     they came in). A holder's child marked data-fallback shows only while no node is
                                     in it. Returns a function that takes the node out for good. Any other name throws.
     Cali.esc(text)                  text made safe for an HTML template.
     Cali.loadLabel(load, bodyweight)  'BW', 'BW +5 kg', '110 kg' (up to two decimals, '.' as the point).

   Features
     app/registry.js lists each feature's script and stylesheet, one line each, append-only. Core loads them in
     that order (stylesheets as <link>, scripts in order) once the page is parsed, then shows the screen in the
     address. sw.js reads the same list, so a listed file works offline with no other edit.

   Gestures the gate uses (tests/acceptance.py): a tap is one touch (touchStart then touchEnd at one point, no clock
   movement between); a hold is touchStart, Playwright's clock run 800 ms, touchEnd; gestures are 1 s of clock time
   apart. A day screen that keeps the gate green logs on that tap and that hold, and puts data-set="<dayId>:<exId>:<i>"
   on every set cell. */
(() => {
  'use strict';

  const KEY = 'cali.v5';
  const SYNC_KEY = 'cali.sync';
  const TIMERS_KEY = 'cali.timers';
  const READ_ONLY = ['cali_sync_config', 'pantry.v1'];
  const VERSION = 5;
  const KINDS = ['reps', 'time', 'check'];
  const STEP = { reps: 1, time: 5, check: 1 };
  const ALERT_KINDS = ['rest', 'headsup', 'timer', 'test'];
  const SLOTS = ['topbar', 'dayheader'];

  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const isNum = v => typeof v === 'number' && Number.isFinite(v);
  const isId = v => typeof v === 'string' && v.length > 0 && !v.includes(':');
  const isIso = v => typeof v === 'string' && !Number.isNaN(Date.parse(v));
  const bool = v => typeof v === 'boolean';

  const DEFAULTS = Object.freeze({
    restPair: 90, restExercise: 120, restAfterLog: true, headsUp: 10, vibrate: true, sound: true,
    keepAwake: true, loadStep: 2.5, theme: 'system',
  });
  const VALID = {
    restPair: v => Number.isInteger(v) && v >= 0 && v <= 3600,
    restExercise: v => Number.isInteger(v) && v >= 0 && v <= 3600,
    restAfterLog: bool,
    headsUp: v => Number.isInteger(v) && v >= 0 && v <= 60,
    vibrate: bool,
    sound: bool,
    keepAwake: bool,
    loadStep: v => isNum(v) && v > 0 && v <= 50,
    theme: v => ['system', 'light', 'dark'].includes(v),
  };

  // ── time ──────────────────────────────────────────────────────────
  const now = () => Date.now();
  const iso = (ms = now()) => new Date(ms).toISOString();

  // ── the document's shape ──────────────────────────────────────────
  function checkProgram(p) {
    if (!isObj(p) || !isId(p.id) || typeof p.name !== 'string') throw new Error('a program without id or name');
    if (!Array.isArray(p.days) || !p.days.length) throw new Error(`program ${p.id}: no days`);
    const dayIds = new Set();
    for (const day of p.days) {
      if (!isObj(day) || !isId(day.id) || typeof day.name !== 'string') throw new Error(`program ${p.id}: a day without id or name`);
      if (dayIds.has(day.id)) throw new Error(`program ${p.id}: day ${day.id} twice`);
      dayIds.add(day.id);
      if (!Array.isArray(day.exercises)) throw new Error(`program ${p.id}, day ${day.id}: exercises is not a list`);
      const exIds = new Set();
      for (const e of day.exercises) {
        const at = `program ${p.id}, day ${day.id}, exercise ${isObj(e) ? e.id : '?'}`;
        if (!isObj(e) || !isId(e.id) || typeof e.name !== 'string') throw new Error(`${at}: no id or name`);
        if (exIds.has(e.id)) throw new Error(`${at}: twice in the day`);
        exIds.add(e.id);
        if (!KINDS.includes(e.kind)) throw new Error(`${at}: kind ${e.kind}`);
        if (!Number.isInteger(e.sets) || e.sets < 1 || e.sets > 20) throw new Error(`${at}: sets ${e.sets}`);
        if (!isNum(e.target) || e.target < 0) throw new Error(`${at}: target ${e.target}`);
        if (!isNum(e.load) || e.load < 0) throw new Error(`${at}: load ${e.load}`);
        if (!isNum(e.loadStep) || e.loadStep < 0) throw new Error(`${at}: loadStep ${e.loadStep}`);
        if (e.kind === 'reps') {
          if (!isNum(e.repMin) || !isNum(e.repMax) || e.repMin > e.repMax) throw new Error(`${at}: range ${e.repMin}-${e.repMax}`);
        } else if (e.repMin !== null || e.repMax !== null) throw new Error(`${at}: a ${e.kind} row has no rep range (null)`);
        if (e.bodyweight !== undefined && !bool(e.bodyweight)) throw new Error(`${at}: bodyweight ${e.bodyweight}`);
        if (e.pair !== undefined && typeof e.pair !== 'string') throw new Error(`${at}: pair ${e.pair}`);
        if (e.note !== undefined && typeof e.note !== 'string') throw new Error(`${at}: note is not text`);
        if (e.duration !== undefined && !(isNum(e.duration) && e.duration > 0)) throw new Error(`${at}: duration ${e.duration}`);
      }
    }
  }

  function checkWeek(w, i, programs) {
    if (!isObj(w) || w.n !== i + 1) throw new Error(`week ${i + 1}: n is ${isObj(w) ? w.n : w}`);
    if (!programs.has(w.program)) throw new Error(`week ${w.n}: program ${w.program} is not in programs`);
    if (!isIso(w.startedAt)) throw new Error(`week ${w.n}: startedAt ${w.startedAt}`);
    if (w.finishedAt !== undefined && !isIso(w.finishedAt)) throw new Error(`week ${w.n}: finishedAt ${w.finishedAt}`);
    if (!isObj(w.days)) throw new Error(`week ${w.n}: days is not an object`);
    for (const [dayId, day] of Object.entries(w.days)) {
      const at = `week ${w.n}, day ${dayId}`;
      if (!isId(dayId) || !isObj(day) || !isObj(day.exercises)) throw new Error(`${at}: no exercises`);
      for (const k of ['startedAt', 'finishedAt']) if (day[k] !== undefined && !isIso(day[k])) throw new Error(`${at}: ${k} ${day[k]}`);
      for (const [exId, ex] of Object.entries(day.exercises)) {
        if (!isId(exId) || !isObj(ex) || !isNum(ex.load) || !isNum(ex.target)) throw new Error(`${at}, ${exId}: load or target`);
        if (!Array.isArray(ex.sets) || !ex.sets.length) throw new Error(`${at}, ${exId}: sets is not a list`);
        for (const s of ex.sets) {
          if (s === null) continue;
          if (!isObj(s) || !isNum(s.r) || s.r < 0 || !isIso(s.at)) throw new Error(`${at}, ${exId}: a set without r or at`);
          if (s.pain !== undefined && s.pain !== true) throw new Error(`${at}, ${exId}: pain ${s.pain}`);
        }
      }
    }
  }

  function check(d) {
    if (!isObj(d)) throw new Error('the document is not an object');
    if (d._version !== VERSION) throw new Error(`_version ${d._version}, expected ${VERSION}`);
    if (!Array.isArray(d.programs) || !d.programs.length) throw new Error('programs missing');
    const programs = new Set();
    for (const p of d.programs) {
      checkProgram(p);
      if (programs.has(p.id)) throw new Error(`program ${p.id} twice`);
      programs.add(p.id);
    }
    if (!programs.has(d.activeProgram) || !programs.has(d.nextProgram)) throw new Error('activeProgram or nextProgram is not in programs');
    if (!Array.isArray(d.weeks) || !d.weeks.length) throw new Error('weeks missing');
    d.weeks.forEach((w, i) => checkWeek(w, i, programs));
    if (!Array.isArray(d.body)) throw new Error('body is not a list');
    for (const b of d.body) {
      if (!isObj(b) || typeof b.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(b.date) || !isNum(b.kg) || b.kg <= 0) throw new Error('a body line without date or kg');
    }
    if (!isObj(d.settings)) throw new Error('settings missing');
    for (const [k, v] of Object.entries(d.settings)) if (VALID[k] && !VALID[k](v)) throw new Error(`setting ${k} = ${JSON.stringify(v)}`);
    if (d.updatedAt !== undefined && !isIso(d.updatedAt)) throw new Error(`updatedAt ${d.updatedAt}`);
    return d;
  }

  // Logged sets of every week as "n:dayId:exId:i" -> JSON. Cali.change may move nothing in it.
  function loggedSets(d) {
    const out = new Map();
    for (const w of d.weeks) {
      for (const [dayId, day] of Object.entries(w.days)) {
        for (const [exId, ex] of Object.entries(day.exercises)) {
          ex.sets.forEach((s, i) => { if (s !== null) out.set(`${w.n}:${dayId}:${exId}:${i}`, JSON.stringify(s)); });
        }
      }
    }
    return out;
  }
  function guardSets(prev, next) {
    const a = loggedSets(prev), b = loggedSets(next);
    const moved = [...a.keys()].find(k => b.get(k) !== a.get(k)) || [...b.keys()].find(k => !a.has(k));
    if (moved) throw new Error(`sets are written only by Cali.log (set ${moved} would change)`);
  }

  function freeze(v) {
    if (v && typeof v === 'object' && !Object.isFrozen(v)) { Object.freeze(v); for (const k of Object.keys(v)) freeze(v[k]); }
    return v;
  }

  // ── storage ───────────────────────────────────────────────────────
  let problem = null;

  function weekFrom(programOrId, n) {
    const p = typeof programOrId === 'string' ? findProgram(programOrId) : programOrId;
    if (!isObj(p) || !Array.isArray(p.days)) throw new Error(`Cali.weekFrom: no program ${programOrId}`);
    if (!Number.isInteger(n) || n < 1) throw new Error(`Cali.weekFrom: week ${n}`);
    const days = {};
    for (const day of p.days) {
      const exercises = {};
      for (const e of day.exercises) {
        const { id: _id, sets: count, load, target, ...rules } = e;
        exercises[e.id] = { ...structuredClone(rules), load, target, sets: Array(count).fill(null) };
      }
      days[day.id] = { exercises };
    }
    return { n, program: p.id, startedAt: iso(), days };
  }

  function fresh() {
    const program = structuredClone(self.CALI_DEFAULT_PROGRAM);
    if (!isObj(program)) throw new Error('app/default-program.js did not load');
    checkProgram(program);
    return {
      _version: VERSION, updatedAt: iso(), programs: [program], activeProgram: program.id, nextProgram: program.id,
      weeks: [weekFrom(program, 1)], body: [], settings: { ...DEFAULTS },
    };
  }

  function write(next) {
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch (e) {
      throw new Error(e && e.name === 'QuotaExceededError'
        ? 'Could not save: the storage this app has on the phone is full.'
        : `Could not save on this phone (${e && e.message}).`);
    }
    return next;
  }

  function load() {
    let raw;
    try { raw = localStorage.getItem(KEY); } catch (e) {
      problem = 'This browser blocks storage for the app, so nothing can be saved. Open it from its home-screen icon or allow site data.';
      return fresh();
    }
    if (raw === null) {
      const d = fresh();
      try { write(d); } catch (e) { problem = e.message; }
      return d;
    }
    let stored;
    try { stored = JSON.parse(raw); } catch (e) { stored = undefined; }
    if (isObj(stored) && isNum(stored._version) && stored._version > VERSION) {
      problem = 'The workout log on this phone was saved by a newer version of the app. Reload to get the update; until then nothing is saved.';
      return fresh();
    }
    try { return check(stored); } catch (e) {
      // Keep the stored text untouched: refusing to save beats writing over a log that could not be read.
      problem = `The workout log saved on this phone could not be read (${e.message}), so nothing is saved over it.`;
      console.error('Cali: ' + problem);
      return fresh();
    }
  }

  function readSync() {
    try { const v = JSON.parse(localStorage.getItem(SYNC_KEY) || '{}'); return isObj(v) ? v : {}; } catch (e) { return {}; }
  }
  function writeSync(next) { localStorage.setItem(SYNC_KEY, JSON.stringify(next)); return next; }
  function markDirty() {
    try {
      const st = readSync();
      writeSync({ ...st, dirty: true, changes: (st.changes || 0) + 1, dirtySince: st.dirtySince || iso() });
    } catch (e) { console.error('Cali: could not mark the change for sync', e); }
  }

  let doc = freeze(load());

  // ── events ────────────────────────────────────────────────────────
  const handlers = new Map();
  function on(event, fn) {
    if (typeof event !== 'string' || typeof fn !== 'function') throw new Error('Cali.on(event, fn)');
    if (!handlers.has(event)) handlers.set(event, new Set());
    handlers.get(event).add(fn);
    return () => handlers.get(event).delete(fn);
  }
  function emit(event, payload) {
    for (const fn of [...(handlers.get(event) || [])]) {
      try { fn(payload); } catch (e) { console.error(`Cali: a "${event}" handler failed`, e); }
    }
  }

  function commit(fn, opts, fromLog) {
    if (problem) throw new Error(problem);
    const draft = structuredClone(doc);
    const returned = fn(draft);
    const next = check(returned === undefined ? draft : structuredClone(returned));
    if (!fromLog) guardSets(doc, next);
    const dirty = opts.dirty !== false;
    if (dirty) next.updatedAt = iso();
    write(next);
    const prev = doc;
    doc = freeze(next);
    if (dirty) markDirty();
    announce({ why: opts.why || 'edit', detail: opts.detail || {}, dirty, doc, prev });
    return doc;
  }
  const change = (fn, opts = {}) => commit(fn, opts, false);

  function replace(next, opts = {}) {
    if (problem) throw new Error(problem);
    if (!isObj(next) || next._version !== VERSION) throw new Error(`Cali.replace: a document without _version ${VERSION} is never adopted`);
    const copy = check(structuredClone(next));
    const dirty = opts.dirty === true;
    if (dirty) copy.updatedAt = iso();
    write(copy);
    const prev = doc;
    doc = freeze(copy);
    if (dirty) markDirty();
    announce({ why: opts.why || 'replace', detail: opts.detail || {}, dirty, doc, prev });
    return doc;
  }

  function announce(payload) {
    applyTheme();
    emit('change', payload);
    if (current && current.def.update) {
      try { current.def.update(current.root, current.args, payload); } catch (e) { console.error('Cali: screen update failed', e); }
      fillSlots();
    }
  }

  // Another tab of the app saved: take its document instead of writing over it later.
  window.addEventListener('storage', e => {
    if (e.key !== KEY || e.newValue === null || problem) return;
    try {
      const prev = doc;
      doc = freeze(check(JSON.parse(e.newValue)));
      announce({ why: 'storage', detail: {}, dirty: false, doc, prev });
    } catch (err) { console.error('Cali: another tab saved an unreadable document', err); }
  });

  // ── lookups ───────────────────────────────────────────────────────
  const findProgram = id => doc.programs.find(p => p.id === id) || null;
  const program = id => findProgram(id === undefined || id === null ? doc.activeProgram : id);
  const currentWeek = () => doc.weeks[doc.weeks.length - 1];
  const week = n => (n === undefined || n === null ? currentWeek() : doc.weeks.find(w => w.n === n) || null);
  function programExercise(programId, dayId, exId) {
    const p = findProgram(programId);
    const day = p && p.days.find(d => d.id === dayId);
    return (day && day.exercises.find(e => e.id === exId)) || null;
  }

  function weekExercise(n, dayId, exId) {
    const w = week(n);
    const ex = w && w.days[dayId] && w.days[dayId].exercises[exId];
    if (!ex) return null;
    const p = ex.kind ? {} : programExercise(w.program, dayId, exId) || {};
    const { sets: _count, ...rules } = p;
    const { load: _l, target: _t, sets: _s, ...own } = ex;
    const name = own.name || p.name || exId;
    return freeze({ kind: 'reps', repMin: null, repMax: null, loadStep: 0, ...rules, ...own, id: exId, name,
      load: ex.load, target: ex.target, sets: ex.sets, week: w.n, dayId });
  }

  function dayExercises(n, dayId) {
    const w = week(n);
    const day = w && w.days[dayId];
    if (!day) return [];
    const p = findProgram(w.program);
    const pday = p && p.days.find(d => d.id === dayId);
    const ids = pday ? pday.exercises.map(e => e.id).filter(id => day.exercises[id]) : [];
    for (const id of Object.keys(day.exercises)) if (!ids.includes(id)) ids.push(id);
    return ids.map(id => weekExercise(w.n, dayId, id));
  }

  function historyOf(dayId, exId, n) {
    const cut = (week(n) || currentWeek()).n;
    return doc.weeks.filter(w => w.n < cut && w.days[dayId] && w.days[dayId].exercises[exId]).reverse().map(w => {
      const ex = w.days[dayId].exercises[exId];
      return { week: w.n, load: ex.load, target: ex.target, sets: ex.sets, dayDone: Boolean(w.days[dayId].finishedAt) };
    });
  }

  function dayIds(w) {
    const p = findProgram(w.program);
    const ids = p ? p.days.map(d => d.id).filter(id => w.days[id]) : [];
    for (const id of Object.keys(w.days)) if (!ids.includes(id)) ids.push(id);
    return ids;
  }
  function dayArgs(args = {}) {
    const cur = currentWeek();
    const w = (isObj(args) && doc.weeks.find(x => x.n === args.week)) || cur;
    const ids = dayIds(w);
    const dayId = isObj(args) && ids.includes(args.dayId) ? args.dayId : (ids.find(id => !w.days[id].finishedAt) || ids[0]);
    return { week: w.n, dayId, readOnly: w !== cur || (isObj(args) && args.readOnly === true) };
  }

  // ── the rules ─────────────────────────────────────────────────────
  function cellOf(dayId, exId, i) {
    const w = currentWeek();
    const ex = w.days[dayId] && w.days[dayId].exercises[exId];
    if (!ex) throw new Error(`no exercise ${dayId}:${exId} in week ${w.n}`);
    if (!Number.isInteger(i) || i < 0 || i >= ex.sets.length) throw new Error(`no set ${i} of ${dayId}:${exId}`);
    return { w, ex };
  }

  function log(dayId, exId, i, value) {
    const { w, ex } = cellOf(dayId, exId, i);
    const prev = ex.sets[i] === null ? null : structuredClone(ex.sets[i]);
    let set;
    if (value === null) set = null;
    else if (isNum(value) && value >= 0) {
      set = { r: value, at: iso() };
      if (prev && prev.pain) set.pain = true;
    } else if (isObj(value) && isNum(value.r) && value.r >= 0) {
      set = { r: value.r, at: isIso(value.at) ? value.at : iso() };
      if (value.pain === true) set.pain = true;
    } else throw new Error('Cali.log: value is a number, null or { r, at?, pain? }');
    commit(d => { d.weeks[d.weeks.length - 1].days[dayId].exercises[exId].sets[i] = set; },
      { why: 'log', detail: { week: w.n, dayId, exId, i } }, true);
    emit('log', { week: w.n, dayId, exId, i, value: set === null ? null : structuredClone(set), prev });
    return set === null ? null : structuredClone(set);
  }

  function kindOf(dayId, exId) {
    const own = currentWeek().days[dayId];
    const e = (own && own.exercises[exId] && own.exercises[exId].kind ? own.exercises[exId] : null)
      || programExercise(currentWeek().program, dayId, exId);
    return e ? e.kind : 'reps';
  }
  function tap(dayId, exId, i) {
    const { ex } = cellOf(dayId, exId, i);
    const kind = kindOf(dayId, exId), cur = ex.sets[i];
    if (kind === 'check') return log(dayId, exId, i, cur ? null : 1);
    if (!cur) return log(dayId, exId, i, ex.target);
    if (cur.r <= 0) return log(dayId, exId, i, null);
    return log(dayId, exId, i, Math.max(0, cur.r - STEP[kind]));
  }
  function hold(dayId, exId, i) {
    const { ex } = cellOf(dayId, exId, i);
    const kind = kindOf(dayId, exId), cur = ex.sets[i];
    if (kind === 'check') return log(dayId, exId, i, cur ? null : 1);
    return log(dayId, exId, i, (cur ? cur.r : ex.target) + STEP[kind]);
  }

  function setOrder(dayId, n) {
    const list = dayExercises(n, dayId);
    const out = [];
    for (let k = 0; k < list.length;) {
      const group = [list[k]];
      while (list[k].pair && list[k + group.length] && list[k + group.length].pair === list[k].pair) group.push(list[k + group.length]);
      const most = Math.max(...group.map(e => e.sets.length));
      for (let i = 0; i < most; i++) for (const e of group) if (i < e.sets.length) out.push({ exId: e.id, i });
      k += group.length;
    }
    return out;
  }
  function nextSet(dayId, n) {
    const w = week(n);
    if (!w || !w.days[dayId]) return null;
    return setOrder(dayId, w.n).find(({ exId, i }) => w.days[dayId].exercises[exId].sets[i] === null) || null;
  }

  // ── implementations features provide ──────────────────────────────
  const impl = { alert: null, progress: null };
  function provide(name, value) {
    if (name === 'progress') {
      if (typeof value !== 'function') throw new Error("Cali.provide('progress', fn)");
    } else if (name === 'alert') {
      if (!isObj(value) || !['alert', 'schedule', 'cancel', 'requestPermission'].every(k => typeof value[k] === 'function')) {
        throw new Error("Cali.provide('alert', { alert, schedule, cancel, requestPermission })");
      }
    } else throw new Error(`Cali.provide: nothing called ${name}`);
    impl[name] = value;
  }

  function progress(weekEx, hist) {
    if (!isObj(weekEx)) throw new Error('Cali.progress(weekExercise, history)');
    const out = impl.progress ? impl.progress(weekEx, Array.isArray(hist) ? hist : [])
      : { load: weekEx.load, target: weekEx.target, reason: 'no change' };
    if (!isObj(out) || !isNum(out.load) || !isNum(out.target) || typeof out.reason !== 'string') {
      throw new Error('Cali.progress must answer { load, target, reason }');
    }
    return out;
  }

  const alertKind = kind => { if (!ALERT_KINDS.includes(kind)) throw new Error(`Cali.alert: unknown kind ${kind}`); };
  function alert(kind) {
    alertKind(kind);
    return impl.alert ? impl.alert.alert(kind) : undefined;
  }
  alert.schedule = (kind, endAt, tag) => {
    alertKind(kind);
    if (!isNum(endAt)) throw new Error('Cali.alert.schedule: endAt is a time in ms');
    if (typeof tag !== 'string' || !tag) throw new Error('Cali.alert.schedule: a tag is needed');
    return impl.alert ? impl.alert.schedule(kind, endAt, tag) : undefined;
  };
  alert.cancel = tag => {
    if (typeof tag !== 'string' || !tag) throw new Error('Cali.alert.cancel: a tag is needed');
    return impl.alert ? impl.alert.cancel(tag) : undefined;
  };
  alert.requestPermission = () => (impl.alert ? impl.alert.requestPermission()
    : Promise.resolve(typeof Notification === 'undefined' ? 'unsupported' : Notification.permission));
  Object.freeze(alert);

  // ── settings ──────────────────────────────────────────────────────
  const known = key => { if (!(key in DEFAULTS)) throw new Error(`Cali.settings: no setting ${key}`); };
  const settings = Object.freeze({
    get(key) { known(key); const v = doc.settings[key]; return v === undefined ? DEFAULTS[key] : v; },
    set(key, value) {
      known(key);
      if (!VALID[key](value)) throw new Error(`Cali.settings: ${key} cannot be ${JSON.stringify(value)}`);
      change(d => { d.settings[key] = value; }, { why: 'settings', detail: { key, value } });
      return value;
    },
    all() { const out = {}; for (const k of Object.keys(DEFAULTS)) out[k] = settings.get(k); return out; },
    defaults: DEFAULTS,
  });

  // ── timers ────────────────────────────────────────────────────────
  let timers = {};
  try { const t = JSON.parse(localStorage.getItem(TIMERS_KEY) || '{}'); if (isObj(t)) timers = t; } catch (e) { timers = {}; }
  function saveTimers() {
    try { localStorage.setItem(TIMERS_KEY, JSON.stringify(timers)); } catch (e) { console.error('Cali: could not save the timers', e); }
  }
  function timerView(t) {
    if (!t) return null;
    const at = t.pausedAt === null ? now() : t.pausedAt;
    const elapsed = Math.max(0, at - t.startedAt - t.pausedMs);
    const remaining = t.duration === null ? null : Math.max(0, t.duration - elapsed);
    return {
      ...t, data: t.data === null ? null : structuredClone(t.data), laps: [...t.laps], running: t.pausedAt === null, elapsed, remaining,
      endAt: t.duration === null || t.pausedAt !== null ? null : t.startedAt + t.pausedMs + t.duration,
      done: remaining === 0,
    };
  }
  function timerAct(name, action, fn) {
    const t = timers[name];
    if (!t) throw new Error(`Cali.timers: no timer ${name}`);
    fn(t);
    saveTimers();
    const view = timerView(t);
    emit('timer', { name, action, timer: view });
    return view;
  }
  const timerApi = Object.freeze({
    start(name, opts = {}) {
      if (typeof name !== 'string' || !name) throw new Error('Cali.timers.start(name, opts)');
      if (opts.duration !== undefined && !(isNum(opts.duration) && opts.duration > 0)) throw new Error('Cali.timers.start: duration in ms');
      timers[name] = {
        name, kind: opts.kind || null, data: opts.data === undefined ? null : JSON.parse(JSON.stringify(opts.data)),
        duration: opts.duration === undefined ? null : opts.duration, startedAt: now(), pausedAt: null, pausedMs: 0, laps: [],
      };
      saveTimers();
      const view = timerView(timers[name]);
      emit('timer', { name, action: 'start', timer: view });
      return view;
    },
    get: name => timerView(timers[name]),
    list: () => Object.values(timers).map(timerView),
    pause: name => timerAct(name, 'pause', t => { if (t.pausedAt === null) t.pausedAt = now(); }),
    resume: name => timerAct(name, 'resume', t => { if (t.pausedAt !== null) { t.pausedMs += now() - t.pausedAt; t.pausedAt = null; } }),
    add(name, ms) {
      if (!isNum(ms)) throw new Error('Cali.timers.add(name, ms)');
      return timerAct(name, 'add', t => { if (t.duration === null) throw new Error(`Cali.timers: ${name} is a stopwatch`); t.duration = Math.max(0, t.duration + ms); });
    },
    lap: name => timerAct(name, 'lap', t => { t.laps.push(timerView(t).elapsed); }),
    stop(name) {
      if (!timers[name]) return null;
      delete timers[name];
      saveTimers();
      emit('timer', { name, action: 'stop', timer: null });
      return null;
    },
  });

  // ── theme ─────────────────────────────────────────────────────────
  // settings.theme 'system' follows the phone, live; 'light' and 'dark' hold. The browser's own colours follow the
  // theme on screen (color-scheme `only <theme>`), so a forced dark mode leaves Light light.
  const lightQuery = matchMedia('(prefers-color-scheme: light)');
  const bars = {};
  function applyTheme() {
    const pick = settings.get('theme');
    const shown = pick === 'system' ? (lightQuery.matches ? 'light' : 'dark') : pick;
    const root = document.documentElement;
    if (root.dataset.theme !== shown) root.dataset.theme = shown;
    root.style.colorScheme = `only ${shown}`;
    const meta = document.querySelector('meta[name="color-scheme"]');
    if (meta) meta.content = `only ${shown}`;
    bars[shown] = bars[shown] || getComputedStyle(root).getPropertyValue('--canvas').trim();
    if (bars[shown]) for (const bar of document.querySelectorAll('meta[name="theme-color"]')) bar.content = bars[shown];
  }
  lightQuery.addEventListener('change', applyTheme);

  // ── screens ───────────────────────────────────────────────────────
  const routes = {};
  let current = null;   // { name, args, def, root, hash }
  let started = false;
  const depth = () => (history.state && history.state.depth) || 0;

  function hashFor(name, args) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(isObj(args) ? args : {})) if (v !== undefined && v !== null) q.set(k, JSON.stringify(v));
    const s = q.toString();
    return `#/${encodeURIComponent(name)}${s ? '?' + s : ''}`;
  }
  function parseHash() {
    const h = location.hash.replace(/^#\/?/, '');
    const cut = h.indexOf('?');
    const name = decodeURIComponent(cut < 0 ? h : h.slice(0, cut));
    const args = {};
    for (const [k, v] of new URLSearchParams(cut < 0 ? '' : h.slice(cut + 1))) {
      try { args[k] = JSON.parse(v); } catch (e) { args[k] = v; }
    }
    return { name, args };
  }

  function show() {
    let { name, args } = parseHash();
    if (!routes[name]) {
      if (name && name !== 'day') console.warn(`Cali: no route "${name}", opening the day`);
      name = 'day';
      args = {};
      if (location.hash) history.replaceState(history.state, '', hashFor('day', {}));
    }
    if (current && current.def.leave) {
      try { current.def.leave(); } catch (e) { console.error('Cali: leaving a screen failed', e); }
    }
    const app = document.getElementById('app');
    const root = document.createElement('section');
    root.className = 'screen';
    root.dataset.screen = name;
    app.replaceChildren(root);
    window.scrollTo(0, 0);
    const def = routes[name];
    current = def ? { name, args, def, root, hash: location.hash } : null;
    if (!def) root.innerHTML = '<p class="note">No screen is installed.</p>';
    else {
      try { def.render(root, args); } catch (e) {
        console.error('Cali: screen failed', e);
        root.innerHTML = `<div class="banner" role="alert"><b>This screen failed to open.</b> ${esc(e.message)}</div>`;
      }
    }
    fillSlots();
    if (current) emit('route', { name, args: { ...args } });
  }

  function go(name, args = {}, opts = {}) {
    if (!routes[name]) {
      console.warn(`Cali.go: no route "${name}", opening the day`);
      history.replaceState({ depth: depth() }, '', hashFor('day', {}));
      show();
      return;
    }
    const h = hashFor(name, args);
    if (opts.replace) history.replaceState({ depth: depth() }, '', h);
    else history.pushState({ depth: depth() + 1 }, '', h);
    show();
  }
  function back() {
    if (depth() > 0) history.back();
    else { history.replaceState({ depth: 0 }, '', hashFor('day', {})); show(); }
  }
  const onNavigate = () => { if (started && (!current || location.hash !== current.hash)) show(); };
  window.addEventListener('popstate', onNavigate);
  window.addEventListener('hashchange', onNavigate);

  function route(name, def) {
    if (typeof name !== 'string' || !/^[a-z][a-z0-9-]*$/.test(name)) throw new Error(`Cali.route: name ${name}`);
    if (!isObj(def) || typeof def.render !== 'function') throw new Error('Cali.route(name, { render(root, args) })');
    routes[name] = def;
    if (started && parseHash().name === name) show();   // registered late: the address already asks for it
  }

  // ── slots ─────────────────────────────────────────────────────────
  const slots = Object.fromEntries(SLOTS.map(s => [s, []]));
  let slotSeq = 0;
  function fillSlots() {
    for (const name of SLOTS) {
      const host = document.querySelector(`#app [data-slot="${name}"]`);
      if (host) for (const item of slots[name]) host.appendChild(item.node);
    }
  }
  function slot(name, node, order = 0) {
    if (!SLOTS.includes(name)) throw new Error(`Cali.slot: no slot ${name} (topbar, dayheader)`);
    if (!(node instanceof Node)) throw new Error('Cali.slot(name, node, order)');
    const item = { node, order: isNum(order) ? order : 0, seq: slotSeq++ };
    slots[name].push(item);
    slots[name].sort((a, b) => a.order - b.order || a.seq - b.seq);
    fillSlots();
    return () => {
      const at = slots[name].indexOf(item);
      if (at >= 0) slots[name].splice(at, 1);
      node.remove();
    };
  }

  // ── helpers ───────────────────────────────────────────────────────
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const kg = n => String(Math.round(n * 100) / 100);
  const loadLabel = (load, bodyweight) => (bodyweight ? (load > 0 ? `BW +${kg(load)} kg` : 'BW') : `${kg(load)} kg`);

  // ── features ──────────────────────────────────────────────────────
  function loadFeatures() {
    const list = self.CALI_FEATURES || [];
    return Promise.all(list.map(src => new Promise(resolve => {
      const css = /\.css$/.test(src);
      const el = document.createElement(css ? 'link' : 'script');
      if (css) { el.rel = 'stylesheet'; el.href = src; } else { el.src = src; el.async = false; }
      el.onload = resolve;
      el.onerror = () => { console.error('Cali: feature failed to load: ' + src); resolve(); };
      document.head.appendChild(el);
    })));
  }

  function showProblem() {
    if (!problem) return;
    const box = document.createElement('div');
    box.className = 'banner';
    box.setAttribute('role', 'alert');
    box.textContent = problem;
    document.body.prepend(box);
  }

  window.Cali = Object.freeze({
    doc: () => doc,
    change, replace,
    problem: () => problem,
    dirty: () => readSync().dirty === true,
    changes: () => readSync().changes || 0,
    markClean(upTo) {
      const st = readSync();
      if (upTo === undefined || (st.changes || 0) === upTo) writeSync({ ...st, dirty: false, dirtySince: null });
    },
    syncState: () => readSync(),
    setSyncState(patch) { const state = writeSync({ ...readSync(), ...patch }); emit('sync', { state: { ...state } }); return state; },
    readOnly(key) {
      if (!READ_ONLY.includes(key)) throw new Error(`Cali.readOnly: ${key} is not readable here`);
      try { return localStorage.getItem(key); } catch (e) { return null; }
    },
    program, week, weekFrom, weekExercise, dayExercises, history: historyOf, dayArgs,
    log, tap, hold, setOrder, nextSet, progress, settings,
    now, iso, timers: timerApi,
    alert, provide,
    on, emit,
    route, go, back, current: () => (current ? { name: current.name, args: { ...current.args } } : null), slot,
    esc, loadLabel,
  });

  applyTheme();
  document.addEventListener('DOMContentLoaded', () => {
    showProblem();
    loadFeatures().then(() => { started = true; show(); });
  });
  window.addEventListener('load', () => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js', { updateViaCache: 'none' })
        .catch(e => console.warn('Cali: offline support is not available here', e));
    }
  });
})();
