/* Programs (app/program.js, styles in app/program.css): Settings -> Programs. Blueprint -> Decisions (Settings ->
   Programs: edit, duplicate, import, use now or from next week) and Data (the program schema, checked by core).

   Route 'programs' (no args): every program, the one this week runs and the one next week runs (a pill on each);
     New program (blank: one day A, no exercise; its name field opens selected) and Import a program file.
   Route 'program' { id } (no id: the active program): the editor. Name; one line saying which week runs it and where
     an edit shows; the days in order, each a card: a tap on a day's name opens its panel (name, move up or down,
     remove), a tap on an exercise opens its editor under it (one at a time): name, kind (reps, time, check), sets,
     target, rep range, load (typed, kg), load step, bodyweight, pair with the next exercise, muscles, note, and for a
     check row its countdown (typed, minutes); move up or down, remove. Add exercise ends each day, Add day ends the list.
     { id, dayId, exId } opens that exercise's editor at its Muscles field (the muscle map's "Not counted" rows).
     Top bar: Duplicate and Delete. Docked: the last message and "Use this program" (hidden while using it would
     change nothing: it is nextProgram and runs this week too, or this week has a set).

   Every edit is one Cali.change, so core checks the shape; a change core refuses leaves the document as it was and
   one plain line in the dock ("Not saved: ...", core's message translated by plain(), not a second copy of its
   checks). Names save when the field is left or Enter is pressed; an empty name is put back, with a line.
   - New ids (program, day, exercise) are unused in every program and every stored week and never contain ':'.
     Duplicate keeps day and exercise ids, so a copy continues each exercise's log (history and progression are
     keyed by them); the copy is named "<name> copy" and opens in place of the original's editor.
   - A new exercise is usable with only its name typed: reps, 3 sets, 8-12, target 8, load 0, the settings' load
     step. A new day after lettered days (A, B, C or "A Heavy") takes the next letter (D), else "Day N".
   - Kind: to time or check the rep range becomes null, to check the target and sets become 1 and the pair goes; the
     values a kind had come back when it is chosen again in this visit (to reps the first time: 8-12, target 8; to
     time: 30 s); leaving check drops the countdown.
   - Muscles (reps and time rows; Blueprint -> Data, the muscle map in app/muscles.js): a chip per key of
     Cali.muscles, named by CaliMuscles.names; a tap cycles it off -> main (1, filled with a check) -> helper (0.5,
     "½") -> off and saves the whole object (all off stores {}: counts nothing). An exercise without muscles shows
     the name table's guess (CaliMuscles.guess) and a tap starts from it. The first time such an exercise gets its
     name saved here, the guess for that name is written into it: never over a pick ({} included), never again on a
     rename, and nothing when the table knows no muscle for the name (it stays unguessed, so the map lists it). One
     line says when it is guessed, counts nothing or has none; another, while the week this program runs has a set
     stored, that the week keeps the muscles it was built with and a change shows from the next week.
   - Pairs: "Pair with the next exercise" links two adjacent non-check rows; the pair value is one unused elsewhere
     in that day (joining a row already paired joins its group). Unpairing, removing or moving a row out of its group
     clears a pair left with one member, so both lose it; moving a row past another pair jumps the whole pair.
   - Where an edit shows: on the program the current week runs, while that week has no set stored (a set at 0 is
     stored), the week is rebuilt from the edited program (rebuilt(): its n, startedAt and each kept day's
     startedAt and finishedAt stay); a week with a set keeps its copy, the in-card editor on the day screen stays
     the one way to change it, and the line under the name says so.
   - Use this program: refused, with the reason, while a day has no exercise. A current week with no set stored is
     rebuilt from it at once and activeProgram and nextProgram become it; a week with a set stays as it is and only
     nextProgram moves (Finish week builds from it). rebuilt() keeps the week's load and target of an exercise both
     programs have with the same kind and the same program value, so a copy used on a week Finish week built keeps
     its progression; a value the edit or the other program changed is taken from the program.
   - Delete asks first and is refused, with the reason, for the program a stored week names (core needs every
     week.program) and for nextProgram, so in practice only a never-used program can go. Removing a day or an
     exercise asks first too; the last day of a program stays (core needs one).
   - Import takes one program object as JSON (a whole document is refused and pointed at Restore): added as it is,
     under a fresh program id when its id is taken, day and exercise ids kept so a file can continue a log on
     purpose; anything core refuses leaves the document unchanged and one line saying why.
   A program change pushes at once through app/sync.js (any change to programs, activeProgram or nextProgram is due
   at once); nothing here reads or writes the token. Components come from Settings (rows, switches, pills, the
   confirm dialog: app/settings.css) and the in-card exercise editor (steppers, segments, fields: app/workout.css). */
(() => {
  'use strict';
  const esc = Cali.esc;
  const KINDS = [['reps', 'Reps'], ['time', 'Time'], ['check', 'Check']];
  const LOAD_STEPS = [1, 1.25, 2.5, 5];
  const PATHS = {
    back: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
    down: '<path d="m6 9 6 6 6-6"/>',
    right: '<path d="m9 18 6-6-6-6"/>',
    up: '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    lower: '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    alert: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
  };
  const icon = name => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${PATHS[name]}</svg>`;
  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const pad = n => String(n).padStart(2, '0');
  const minutes = s => (s % 60 ? `${Math.floor(s / 60)}:${pad(s % 60)}` : `${s / 60} min`);
  const decimal = v => String(Math.round(v * 1000) / 1000);
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const hasSets = w => Object.values(w.days).some(d => Object.values(d.exercises).some(e => e.sets.some(s => s !== null)));
  const findIn = (p, dayId, exId) => {
    const day = p && p.days.find(d => d.id === dayId);
    return (day && day.exercises.find(e => e.id === exId)) || null;
  };
  const linked = (a, b) => Boolean(a && b && a.pair && a.pair === b.pair);
  const pairable = (a, b) => Boolean(a && b && a.kind !== 'check' && b.kind !== 'check');

  // ── ids and names ─────────────────────────────────────────────────
  function takenIds(d) {
    const s = new Set();
    for (const p of d.programs) {
      s.add(p.id);
      for (const day of p.days) { s.add(day.id); for (const e of day.exercises) s.add(e.id); }
    }
    for (const w of d.weeks) {
      for (const [dayId, day] of Object.entries(w.days)) { s.add(dayId); for (const exId of Object.keys(day.exercises)) s.add(exId); }
    }
    return s;
  }
  // as the built-in program's: base-36 time, '_', four random base-36 characters (never ':')
  function newId(taken) {
    for (;;) {
      const r = crypto.getRandomValues(new Uint32Array(1))[0].toString(36).padStart(4, '0').slice(-4);
      const id = `${Cali.now().toString(36)}_${r}`;
      if (!taken.has(id)) { taken.add(id); return id; }
    }
  }
  function freeName(base, names) {
    if (!names.includes(base)) return base;
    for (let k = 2; ; k++) if (!names.includes(`${base} ${k}`)) return `${base} ${k}`;
  }
  // days lettered A, B, C (or "A Heavy", "B Pump") get the next letter; any other names get "Day N"
  function dayName(p) {
    const names = p.days.map(d => d.name);
    const letters = names.map(n => (/^([A-Z])(\s|$)/.exec(n) || [])[1]);
    if (letters.every(Boolean) && new Set(letters).size === letters.length) {
      const next = String.fromCharCode(Math.max(64, ...letters.map(c => c.charCodeAt(0))) + 1);
      if (next <= 'Z' && !names.includes(next)) return next;
    }
    for (let k = p.days.length + 1; ; k++) if (!names.includes(`Day ${k}`)) return `Day ${k}`;
  }
  const newExercise = id => ({ id, name: 'New exercise', kind: 'reps', sets: 3, target: 8, repMin: 8, repMax: 12, load: 0,
    loadStep: Cali.settings.get('loadStep') });

  // ── pairs (adjacent exercises of a day with the same pair are done alternately) ──
  function freePair(day) {
    const used = new Set(day.exercises.map(e => e.pair));
    for (let k = 1; ; k++) if (!used.has(`p${k}`)) return `p${k}`;
  }
  // a pair value is one run of adjacent rows: a run of one loses it, a second run of the same value gets a new one
  function tidyPairs(day) {
    const ex = day.exercises;
    const runs = [];
    ex.forEach((e, k) => {
      if (!e.pair) return;
      const last = runs[runs.length - 1];
      if (last && last.end === k - 1 && last.v === e.pair) last.end = k;
      else runs.push({ v: e.pair, start: k, end: k });
    });
    const seen = new Set();
    for (const r of runs) {
      if (r.start === r.end) { delete ex[r.start].pair; continue; }
      if (!seen.has(r.v)) { seen.add(r.v); continue; }
      const v = freePair(day);
      for (let k = r.start; k <= r.end; k++) ex[k].pair = v;
      seen.add(v);
    }
  }
  function link(day, k) {
    const ex = day.exercises, a = ex[k], b = ex[k + 1];
    const v = a.pair || b.pair || freePair(day);
    const old = b.pair;
    a.pair = v;
    if (old && old !== v) for (let j = k + 1; j < ex.length && ex[j].pair === old; j++) ex[j].pair = v;
    else b.pair = v;
  }
  function unlink(day, k) {
    const ex = day.exercises, v = ex[k].pair;
    const nv = freePair(day);
    for (let j = k + 1; j < ex.length && ex[j].pair === v; j++) ex[j].pair = nv;
  }
  // inside its group a row swaps with its neighbour; at the group's edge it leaves the group; it jumps a whole pair
  function moveExercise(day, k, dir) {
    const ex = day.exercises, e = ex[k], t = k + dir;
    if (t < 0 || t >= ex.length) return false;
    if (e.pair && ex[t].pair === e.pair) { [ex[k], ex[t]] = [ex[t], ex[k]]; return true; }
    delete e.pair;
    let s = t, f = t;
    if (ex[t].pair) {
      while (s > 0 && ex[s - 1].pair === ex[t].pair) s--;
      while (f < ex.length - 1 && ex[f + 1].pair === ex[t].pair) f++;
    }
    ex.splice(k, 1);
    ex.splice(dir < 0 ? s : f, 0, e);
    return true;
  }

  // ── kind and its dependent fields ─────────────────────────────────
  const kept = new Map();   // "<program>:<day>:<exercise>" -> { <kind>: the fields it had }, for this visit
  function setKind(p, day, e, kind) {
    if (e.kind === kind) return;
    const key = `${p.id}:${day.id}:${e.id}`;
    const memo = kept.get(key) || {};
    memo[e.kind] = { target: e.target, repMin: e.repMin, repMax: e.repMax, sets: e.sets, duration: e.duration };
    kept.set(key, memo);
    const back = memo[kind] || {};
    const from = e.kind;
    e.kind = kind;
    if (kind === 'reps') {
      e.repMin = back.repMin === undefined ? 8 : back.repMin;
      e.repMax = back.repMax === undefined ? 12 : back.repMax;
      e.target = back.target === undefined ? e.repMin : back.target;
    } else { e.repMin = null; e.repMax = null; }
    if (kind === 'time') e.target = back.target === undefined ? 30 : back.target;
    if (kind === 'check') {
      e.target = 1;
      e.sets = 1;
      delete e.pair;
      if (back.duration !== undefined) e.duration = back.duration;
    } else {
      delete e.duration;
      if (from === 'check') e.sets = back.sets === undefined ? 3 : back.sets;
      if (!(e.loadStep > 0)) e.loadStep = Cali.settings.get('loadStep');
    }
  }

  // ── the week the edit or the choice reaches ───────────────────────
  // the current week built anew from program p: its n and startedAt stay, a kept day keeps its session times, and an
  // exercise both programs have (same kind, same program value as `before`, the program the week came from) keeps the
  // week's load and target, which Finish week may have moved on
  function rebuilt(w, p, before) {
    const built = Cali.weekFrom(p, w.n);
    built.startedAt = w.startedAt;
    for (const [dayId, day] of Object.entries(built.days)) {
      const old = w.days[dayId];
      if (!old) continue;
      if (old.startedAt) day.startedAt = old.startedAt;
      if (old.finishedAt) day.finishedAt = old.finishedAt;
      for (const [exId, e] of Object.entries(day.exercises)) {
        const o = old.exercises[exId], was = findIn(before, dayId, exId), now = findIn(p, dayId, exId);
        if (!o || !was || o.kind !== e.kind || was.kind !== now.kind) continue;
        if (was.load === now.load) e.load = o.load;
        if (was.target === now.target) e.target = o.target;
      }
    }
    return built;
  }

  // ── core's refusals in plain words ────────────────────────────────
  function plain(message, p) {
    const bad = (what, v) => (typeof v !== 'string' || !v ? `has no ${what}` : `${what} “${v}” contains “:”, which ids cannot`);
    if (message === 'a program without id or name') {
      return !isObj(p) || typeof p.id !== 'string' || !p.id || p.id.includes(':') ? `the program ${bad('id', isObj(p) ? p.id : null)}` : 'the program has no name';
    }
    const m = /^program (.*?)(?:, day (.*?))?(?:, exercise (.*?))?: (.*)$/s.exec(message);
    if (!m) return message;
    const [, , dayId, exId, what] = m;
    const days = isObj(p) && Array.isArray(p.days) ? p.days.filter(isObj) : [];
    const day = days.find(d => d.id === dayId) || null;
    const list = day && Array.isArray(day.exercises) ? day.exercises.filter(isObj) : [];
    const ex = list.find(e => e.id === exId) || null;
    const dayText = day && typeof day.name === 'string' && day.name ? `day ${day.name}` : `day ${dayId}`;
    const where = `${ex && typeof ex.name === 'string' && ex.name ? `“${ex.name}”` : `exercise ${exId}`} on ${dayText}`;
    if (what === 'no days') return 'the program has no days';
    if (what === 'a day without id or name') {
      const d = days.find(x => typeof x.id !== 'string' || !x.id || x.id.includes(':'));
      return d || days.length < p.days.length ? `a day ${bad('id', d ? d.id : null)}` : 'a day has no name';
    }
    let t;
    if ((t = /^day (.*) twice$/s.exec(what))) return `the day id “${t[1]}” is used twice`;
    if (what === 'exercises is not a list') return `${dayText} has no list of exercises`;
    if (what === 'no id or name') {
      const e = list.find(x => typeof x.id !== 'string' || !x.id || x.id.includes(':'));
      return e || list.length < (day && Array.isArray(day.exercises) ? day.exercises.length : 0) ? `an exercise on ${dayText} ${bad('id', e ? e.id : null)}` : `an exercise on ${dayText} has no name`;
    }
    if (what === 'twice in the day') return `the exercise id “${exId}” is used twice on ${dayText}`;
    if (/^kind /.test(what)) return `${where} has the kind “${ex ? ex.kind : what.slice(5)}”; it must be reps, time or check`;
    if (/^sets /.test(what)) return `${where} has ${what.slice(5)} sets; it must be 1 to 20`;
    if (/^target /.test(what)) return `the target of ${where} must be a number, 0 or more`;
    if (/^load /.test(what)) return `the load of ${where} must be a number of kg, 0 or more`;
    if (/^loadStep /.test(what)) return `the load step of ${where} must be a number of kg, 0 or more`;
    if (/^range /.test(what)) {
      return ex && typeof ex.repMin === 'number' && typeof ex.repMax === 'number'
        ? `${where} has the rep range ${ex.repMin}–${ex.repMax}: its low end is above its high end`
        : `${where} needs a rep range (repMin and repMax)`;
    }
    if (/row has no rep range/.test(what)) return `${where} is a ${ex ? ex.kind : ''} row, so its rep range is empty (repMin and repMax null)`;
    if (/^bodyweight /.test(what)) return `bodyweight on ${where} must be true or false`;
    if (/^pair /.test(what)) return `the pair of ${where} must be text`;
    if (/^note /.test(what)) return `the note of ${where} must be text`;
    if (/^duration /.test(what)) return `the countdown of ${where} must be a number above 0`;
    if (what === 'muscles is not an object') return `the muscles of ${where} must be an object of muscle names`;
    if ((t = /^muscle (.*) is not a key of Cali\.muscles$/s.exec(what))) return `${where} names the muscle “${t[1]}”, which is not one of ${Cali.muscles.join(', ')}`;
    if ((t = /^muscle (.*?) counts (.*), not 1 or 0\.5$/s.exec(what))) return `the muscle “${t[1]}” of ${where} counts ${t[2]}; it must be 1 (main) or 0.5 (helper)`;
    return what;
  }

  // ── writing ───────────────────────────────────────────────────────
  let carry = null;   // what the next screen shows first: { msg, err, focus }

  // fn(program, day?, exercise?, draft) edits the draft; true when saved, else the line says why
  function edit(id, fn, what, at = {}) {
    try {
      Cali.change(d => {
        const p = d.programs.find(x => x.id === id);
        const before = structuredClone(p);
        const day = at.dayId ? p.days.find(x => x.id === at.dayId) : null;
        const e = day && at.exId ? day.exercises.find(x => x.id === at.exId) : null;
        fn(p, day, e, d);
        for (const x of p.days) tidyPairs(x);
        const w = d.weeks[d.weeks.length - 1];
        if (w.program === id && !hasSets(w)) d.weeks[d.weeks.length - 1] = rebuilt(w, p, before);
      }, { why: 'program', detail: { id, what } });
      return true;
    } catch (err) {
      say(`Not saved: ${plain(err.message, Cali.program(id))}.`, true);
      return false;
    }
  }

  function addProgram(p, how) {
    Cali.change(d => { d.programs.push(p); }, { why: 'addProgram', detail: { id: p.id, how } });
  }

  function useProgram(id) {
    const p = Cali.program(id);
    const empty = p.days.find(d => !d.exercises.length);
    if (empty) { say(`Not used: day ${empty.name} has no exercise yet. Add one or remove the day.`, true); return; }
    const w = Cali.week();
    const now = !hasSets(w);
    try {
      Cali.change(d => {
        const last = d.weeks.length - 1;
        if (now) {
          d.weeks[last] = rebuilt(d.weeks[last], d.programs.find(x => x.id === id), d.programs.find(x => x.id === d.weeks[last].program));
          d.activeProgram = id;
        }
        d.nextProgram = id;
      }, { why: 'useProgram', detail: { id, now } });
    } catch (err) { say(`Not used: ${plain(err.message, p)}.`, true); return; }
    say(now ? `Week ${w.n} now runs ${p.name}.` : `${p.name} starts with week ${w.n + 1}; week ${w.n} keeps its sets.`);
  }

  function deleteRefusal(id) {
    const d = Cali.doc(), cur = Cali.week();
    if (cur.program === id || d.activeProgram === id) return `week ${cur.n} runs it, and the log keeps every program a week ran`;
    const past = d.weeks.find(w => w.program === id);
    if (past) return `week ${past.n} ran it, and the log keeps every program a week ran`;
    if (d.nextProgram === id) return `week ${cur.n + 1} is set to run it; use another program first`;
    return null;
  }

  // ── a confirm dialog: title, one sentence, Cancel and the chosen action (the look of Settings') ──
  function ask({ title, text, ok }) {
    return new Promise(resolve => {
      const dlg = document.createElement('dialog');
      dlg.className = 'settings-dialog program-dialog';
      dlg.setAttribute('aria-labelledby', 'program-dialog-title');
      dlg.innerHTML = `<h2 id="program-dialog-title">${esc(title)}</h2><p>${esc(text)}</p><div class="settings-dialog-actions">` +
        '<button type="button" class="btn secondary" data-answer="no">Cancel</button>' +
        `<button type="button" class="btn settings-danger" data-answer="yes">${esc(ok)}</button></div>`;
      const done = yes => { if (dlg.open && typeof dlg.close === 'function') dlg.close(); dlg.remove(); resolve(yes); };
      dlg.addEventListener('click', e => { const b = e.target.closest('[data-answer]'); if (b) done(b.dataset.answer === 'yes'); });
      dlg.addEventListener('cancel', e => { e.preventDefault(); done(false); });
      document.body.appendChild(dlg);
      if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
    });
  }
  const closeDialogs = () => { for (const dlg of document.querySelectorAll('dialog.program-dialog')) dlg.remove(); };

  // ── the line: the last thing done or refused ──────────────────────
  let screen = null;   // { kind: 'list' | 'editor', root, msg, ... }
  function say(text, err = false) {
    if (!screen) { carry = { ...(carry || {}), msg: text, err }; return; }
    screen.msg = { text, err };
    paintMsg();
  }
  function paintMsg() {
    const box = screen && screen.root.querySelector('[data-msg]');
    if (!box) return;
    const m = screen.msg;
    box.hidden = !m;
    box.classList.toggle('program-err', Boolean(m && m.err));
    box.innerHTML = m ? `${m.err ? icon('alert') : ''}<span>${esc(m.text)}</span>` : '';
    const dock = screen.root.querySelector('.program-dock');
    if (dock) dock.hidden = !m && dock.querySelector('[data-act="use"]').hidden;
  }

  // ── the list: route 'programs' ────────────────────────────────────
  function pillOf(p) {
    const now = Cali.week().program === p.id, next = Cali.doc().nextProgram === p.id;
    const word = now && next ? 'This and next week' : now ? 'This week' : next ? 'Next week' : '';
    return word ? `<span class="pill">${word}</span>` : '';
  }
  function drawList(root) {
    const progs = Cali.doc().programs;
    root.innerHTML = `<header class="bar2"><button type="button" class="iconbtn" data-act="back" aria-label="Back">${icon('back')}</button><h2>Programs</h2></header>` +
      '<div class="program-body">' +
        `<div class="group program-list">${progs.map(p => {
          const days = p.days.map(d => d.name).join(', ');
          return `<button type="button" class="settings-row" data-act="open" data-id="${esc(p.id)}">` +
            `<span class="settings-t">${esc(p.name)}<small>${esc(`${plural(p.days.length, 'day')}: ${days}`)}</small></span>` +
            `${pillOf(p)}<span class="settings-chev">${icon('right')}</span></button>`;
        }).join('')}</div>` +
        '<div class="group program-list">' +
          `<button type="button" class="settings-row" data-act="new">${icon('plus')}<span class="settings-t">New program<small>One empty day to fill</small></span></button>` +
          `<button type="button" class="settings-row" data-act="import">${icon('upload')}<span class="settings-t">Import a program file<small>JSON, one program</small></span></button>` +
          '<input type="file" accept=".json,application/json" data-import hidden>' +
        '</div>' +
        '<p class="program-msg" data-msg role="status" hidden></p>' +
      '</div>';
    paintMsg();
  }

  async function importFile(file) {
    let data;
    try { data = JSON.parse(await file.text()); } catch (e) { say('Not imported: the file is not JSON.', true); return; }
    if (!isObj(data)) { say(`Not imported: the file holds ${Array.isArray(data) ? 'a list' : 'no program'}; it needs one program object.`, true); return; }
    if ('_version' in data || 'weeks' in data || 'programs' in data) {
      say('Not imported: that is a whole backup, not one program. Restore it in Settings, Restore from backup.', true);
      return;
    }
    const d = Cali.doc();
    const p = structuredClone(data);
    if (d.programs.some(x => x.id === p.id)) p.id = newId(takenIds(d));
    try { addProgram(p, 'import'); } catch (err) { say(`Not imported: ${plain(err.message, p)}.`, true); return; }
    carry = { msg: `Imported ${p.name}.` };
    Cali.go('program', { id: p.id });
  }

  function listClick(e) {
    const b = e.target.closest('button');
    if (!b || !screen || !screen.root.contains(b)) return;
    const act = b.dataset.act;
    screen.msg = null;
    if (act === 'back') { Cali.back(); return; }
    if (act === 'open') { Cali.go('program', { id: b.dataset.id }); return; }
    if (act === 'import') { paintMsg(); screen.root.querySelector('[data-import]').click(); return; }
    if (act === 'new') {
      const d = Cali.doc(), taken = takenIds(d);
      const p = { id: newId(taken), name: freeName('New program', d.programs.map(x => x.name)), days: [{ id: newId(taken), name: 'A', exercises: [] }] };
      try { addProgram(p, 'new'); } catch (err) { say(`Not made: ${plain(err.message, p)}.`, true); return; }
      carry = { focus: '[data-f="pname"]' };
      Cali.go('program', { id: p.id });
    }
  }

  Cali.route('programs', {
    render(root) {
      root.classList.add('program');
      screen = { kind: 'list', root, msg: carry && carry.msg ? { text: carry.msg, err: Boolean(carry.err) } : null };
      carry = null;
      drawList(root);
      root.addEventListener('click', listClick);
      root.addEventListener('change', e => {
        if (!e.target.matches('[data-import]')) return;
        const file = e.target.files && e.target.files[0];
        e.target.value = '';
        if (file) importFile(file);
      });
    },
    update(root) { if (screen && screen.root === root) drawList(root); },
    leave() { screen = null; closeDialogs(); },
  });

  // ── the editor: route 'program' { id } ────────────────────────────
  function summary(e, next) {
    const parts = e.kind === 'reps' ? [`${e.sets} × ${e.repMin}–${e.repMax}`] : e.kind === 'time' ? [`${e.sets} × ${e.target} s`]
      : [e.duration ? `Check, ${minutes(e.duration)}` : 'Check'];
    if (e.kind !== 'check') parts.push(Cali.loadLabel(e.load, e.bodyweight));
    if (linked(e, next)) parts.push('paired with next');
    return parts.join(', ');
  }

  function stateLine(p) {
    const d = Cali.doc(), w = Cali.week(), sets = hasSets(w), now = w.program === p.id, next = d.nextProgram === p.id;
    const other = (Cali.program(d.nextProgram) || {}).name;
    if (now && next) return sets ? `Week ${w.n} runs it and has sets logged, so edits here show from week ${w.n + 1}.` : `Week ${w.n} runs it; edits here show on it at once.`;
    if (now) return sets ? `Week ${w.n} runs it and keeps its copy; week ${w.n + 1} runs ${other}.` : `Week ${w.n} runs it; edits show at once. Week ${w.n + 1} runs ${other}.`;
    if (next) return `Starts with week ${w.n + 1}.`;
    return 'Not in use.';
  }

  // the line under an exercise's load: Finish week carries a logged exercise's load and target on from the week
  function carryLine(p, day, e) {
    const d = Cali.doc(), w = Cali.week();
    const o = w.days[day.id] && w.days[day.id].exercises[e.id];
    if (e.kind === 'check' || d.nextProgram !== p.id || !hasSets(w) || !o || o.kind !== e.kind) return '';
    return `Week ${w.n + 1} carries load and target on from week ${w.n}.`;
  }

  // ── muscles (the muscle map's names and name table are app/muscles.js's CaliMuscles) ──
  const table = () => self.CaliMuscles || null;
  const shownMuscles = e => (isObj(e.muscles) ? e.muscles : table().guess(e.name, e.kind) || {});
  // the first name saved on an exercise without muscles writes the guess for it (see the header)
  function firstGuess(e) {
    if (!table() || e.muscles !== undefined || e.kind === 'check') return;
    const g = table().guess(e.name, e.kind);
    if (g) e.muscles = g;
  }
  // a tap on a muscle: off -> main (1) -> helper (0.5) -> off, from what the chips show; the keys in Cali.muscles order
  function cycleMuscle(e, key) {
    const from = shownMuscles(e);
    const next = { ...from, [key]: from[key] === 1 ? 0.5 : from[key] === 0.5 ? undefined : 1 };
    e.muscles = {};
    for (const k of Cali.muscles) if (next[k] === 1 || next[k] === 0.5) e.muscles[k] = next[k];
  }
  function muscleLine(e) {
    const rule = 'A tap makes a muscle main, a second tap a helper (½, counts half), a third off.';
    if (isObj(e.muscles)) return Object.keys(e.muscles).length ? '' : 'Counts nothing on the muscle map.';
    return table().guess(e.name, e.kind) ? `Guessed from the name. ${rule}` : `No muscle yet, so the muscle map does not count it. ${rule}`;
  }
  function muscleWeekLine(p) {
    const w = Cali.week();
    if (w.program !== p.id || !hasSets(w)) return '';
    return Cali.doc().nextProgram === p.id ? `Week ${w.n} keeps the muscles it was built with; a change shows from week ${w.n + 1}.`
      : `Week ${w.n} keeps the muscles it was built with.`;
  }
  function musclesHtml(e) {
    if (e.kind === 'check' || !table()) return '';
    return '<div class="workout-ed-f workout-ed-wide program-muscles" role="group" aria-labelledby="program-l-muscles">' +
      '<span class="workout-ed-l" id="program-l-muscles">Muscles</span><div class="program-mchips">' +
      Cali.muscles.map(k => `<button type="button" class="program-mchip" data-act="muscle" data-m="${k}" aria-pressed="false">` +
        `${icon('check')}<span>${esc(table().names[k])}</span><span class="program-mhalf" aria-hidden="true">½</span></button>`).join('') +
      '</div><p class="program-hint" data-v="mline" hidden></p><p class="program-hint" data-v="mweek" hidden></p></div>';
  }

  // the steppers of an open exercise: label, value shown, step and bounds
  function steppers(e) {
    const out = [];
    if (e.kind !== 'check') out.push({ k: 'sets', label: 'Sets', show: String(e.sets), step: 1, min: 1, max: 20 });
    if (e.kind === 'reps') {
      out.push({ k: 'target', label: 'Target reps', show: String(e.target), step: 1, min: 1, max: 100 });
      out.push({ k: 'repMin', label: 'Range low', show: String(e.repMin), step: 1, min: 1, max: e.repMax });
      out.push({ k: 'repMax', label: 'Range high', show: String(e.repMax), step: 1, min: e.repMin, max: 100 });
    }
    if (e.kind === 'time') out.push({ k: 'target', label: 'Target hold', show: `${e.target} s`, step: 5, min: 5, max: 600 });
    return out;
  }

  function stepperHtml(f) {
    const id = `program-l-${f.k}`;
    return `<div class="workout-ed-f" role="group" aria-labelledby="${id}"><span class="workout-ed-l" id="${id}">${f.label}</span><div class="workout-ed-step">` +
      `<button type="button" data-act="step" data-k="${f.k}" data-d="-1" aria-label="${f.label} down"><span>−</span></button>` +
      `<span class="num" data-v="${f.k}" aria-live="polite"></span>` +
      `<button type="button" data-act="step" data-k="${f.k}" data-d="1" aria-label="${f.label} up"><span>+</span></button></div></div>`;
  }
  const switchHtml = (act, label, sub) => `<button type="button" class="settings-row" role="switch" aria-checked="false" data-act="${act}">` +
    `<span class="settings-t">${esc(label)}<small data-v="${act}sub">${esc(sub)}</small></span><span class="settings-tog" aria-hidden="true"></span></button>`;

  function exEditorHtml(p, day, e, k) {
    const next = day.exercises[k + 1];
    const steps = LOAD_STEPS.includes(e.loadStep) || !(e.loadStep > 0) ? LOAD_STEPS : [...LOAD_STEPS, e.loadStep].sort((a, b) => a - b);
    const field = (f, label, attrs) => `<label class="workout-ed-f"><span class="workout-ed-l" data-l="${f}">${label}</span>` +
      `<input type="text" class="workout-ed-name program-num" data-f="${f}" autocomplete="off" ${attrs}></label>`;
    return `<div class="program-ed" id="program-ed-${esc(e.id)}">` +
      '<label class="workout-ed-f workout-ed-wide"><span class="workout-ed-l">Name</span>' +
        '<input type="text" class="workout-ed-name" data-f="ename" maxlength="80" autocomplete="off" enterkeyhint="done"></label>' +
      '<div class="workout-ed-f workout-ed-wide"><span class="workout-ed-l">Kind</span>' +
        `<div class="workout-ed-seg" role="group" aria-label="Kind">${KINDS.map(([v, t]) =>
          `<button type="button" data-act="kind" data-v="${v}" aria-pressed="false">${t}</button>`).join('')}</div></div>` +
      `<div class="workout-ed-grid">${steppers(e).map(stepperHtml).join('')}` +
        (e.kind === 'check' ? '' : field('load', 'Load, kg', 'inputmode="decimal" enterkeyhint="done"')) +
        (e.kind === 'check' ? field('dur', 'Countdown, minutes', 'inputmode="decimal" enterkeyhint="done" placeholder="None"') : '') +
      '</div>' +
      '<p class="program-hint" data-v="carry" hidden></p>' +
      (e.kind === 'check' ? '' : '<div class="workout-ed-f workout-ed-wide"><span class="workout-ed-l">Load step, kg</span>' +
        `<div class="workout-ed-seg" role="group" aria-label="Load step in kg">${steps.map(v =>
          `<button type="button" data-act="lstep" data-v="${v}" aria-pressed="false">${decimal(v)}</button>`).join('')}</div></div>`) +
      (e.kind === 'check' ? '' : switchHtml('bw', 'Bodyweight', 'The load is added to it')) +
      (pairable(e, next) ? switchHtml('pair', 'Pair with the next exercise', '') : '') +
      musclesHtml(e) +
      '<label class="workout-ed-f workout-ed-wide"><span class="workout-ed-l">Note</span>' +
        '<textarea class="workout-ed-name program-note" data-f="note" rows="2" maxlength="300" placeholder="A cue under its name"></textarea></label>' +
      '<div class="workout-ed-foot"><div class="program-acts">' +
        `<button type="button" class="iconbtn" data-act="exup" aria-label="Move up">${icon('up')}</button>` +
        `<button type="button" class="iconbtn" data-act="exdown" aria-label="Move down">${icon('lower')}</button>` +
        '<button type="button" class="btn settings-outline-danger" data-act="exrm">Remove</button></div>' +
        '<button type="button" class="btn secondary" data-act="exclose">Done</button></div>' +
    '</div>';
  }

  function dayPanelHtml(day) {
    return `<div class="program-ed program-panel" id="program-dp-${esc(day.id)}">` +
      '<label class="workout-ed-f workout-ed-wide"><span class="workout-ed-l">Day name</span>' +
        '<input type="text" class="workout-ed-name" data-f="dname" maxlength="40" autocomplete="off" enterkeyhint="done"></label>' +
      '<div class="workout-ed-foot"><div class="program-acts">' +
        `<button type="button" class="iconbtn" data-act="dayup" aria-label="Move day up">${icon('up')}</button>` +
        `<button type="button" class="iconbtn" data-act="daydown" aria-label="Move day down">${icon('lower')}</button>` +
        '<button type="button" class="btn settings-outline-danger" data-act="dayrm">Remove day</button></div>' +
        '<button type="button" class="btn secondary" data-act="dayclose">Done</button></div>' +
    '</div>';
  }

  function editorHtml(p) {
    const ed = screen;
    return '<header class="bar2"><button type="button" class="iconbtn" data-act="back" aria-label="Back">' + icon('back') + '</button>' +
        '<h2>Program</h2><span class="program-bar-end"></span>' +
        `<button type="button" class="ghost program-bar-act" data-act="dup">${icon('copy')}Duplicate</button>` +
        `<button type="button" class="iconbtn" data-act="del" aria-label="Delete program">${icon('trash')}</button></header>` +
      '<div class="program-body">' +
        '<label class="workout-ed-f program-name"><span class="workout-ed-l">Name</span>' +
          '<input type="text" class="workout-ed-name" data-f="pname" maxlength="80" autocomplete="off" enterkeyhint="done"></label>' +
        '<p class="program-state" data-v="state"></p>' +
        p.days.map(day => {
          const openDay = ed.openDay === day.id;
          return `<div class="group program-day" data-day="${esc(day.id)}">` +
            `<button type="button" class="settings-row program-dayhead" data-act="day" aria-expanded="${openDay}" aria-controls="program-dp-${esc(day.id)}">` +
              `<span class="settings-t"><span data-v="dname"></span><small data-v="dcount"></small></span><span class="settings-chev">${icon('down')}</span></button>` +
            (openDay ? dayPanelHtml(day) : '') +
            day.exercises.map((e, k) => {
              const open = Boolean(ed.openEx && ed.openEx.dayId === day.id && ed.openEx.exId === e.id);
              return `<div class="program-exbox" data-ex="${esc(e.id)}">` +
                `<button type="button" class="settings-row program-ex" data-act="ex" aria-expanded="${open}" aria-controls="program-ed-${esc(e.id)}">` +
                  `<span class="settings-t"><span data-v="ename"></span><small data-v="esum"></small></span><span class="settings-chev">${icon('down')}</span></button>` +
                (open ? exEditorHtml(p, day, e, k) : '') + '</div>';
            }).join('') +
            `<button type="button" class="settings-row program-add" data-act="addex">${icon('plus')}<span class="settings-t">Add exercise</span></button>` +
            '</div>';
        }).join('') +
        `<button type="button" class="btn secondary program-addday" data-act="addday">${icon('plus')}Add day</button>` +
      '</div>' +
      '<div class="program-dock"><p class="program-msg" data-msg role="status" hidden></p>' +
        '<button type="button" class="btn primary" data-act="use">Use this program</button></div>';
  }

  // rebuilt only when the shape changes (a day, an exercise, a kind, what is open); values are painted in place, so
  // the field being typed in and the button under the finger stay the same elements
  function shapeKey(p) {
    const ed = screen;
    return JSON.stringify([p.id, ed.openDay, ed.openEx, p.days.map(d => [d.id, d.exercises.map((e, k) => [e.id, e.kind,
      pairable(e, d.exercises[k + 1]), ed.openEx && ed.openEx.exId === e.id ? e.loadStep : 0])])]);
  }

  const put = (el, prop, v) => { if (el && el[prop] !== v) el[prop] = v; };
  const setValue = (el, v) => { if (el && document.activeElement !== el && el.value !== v) el.value = v; };

  function paintEditor(p) {
    const { root } = screen;
    const w = Cali.week();
    setValue(root.querySelector('[data-f="pname"]'), p.name);
    put(root.querySelector('[data-v="state"]'), 'textContent', stateLine(p));
    for (const day of p.days) {
      const card = root.querySelector(`.program-day[data-day="${CSS.escape(day.id)}"]`);
      if (!card) continue;
      put(card.querySelector('.program-dayhead [data-v="dname"]'), 'textContent', day.name);
      put(card.querySelector('.program-dayhead [data-v="dcount"]'), 'textContent', day.exercises.length ? plural(day.exercises.length, 'exercise') : 'No exercise yet');
      setValue(card.querySelector('[data-f="dname"]'), day.name);
      const at = p.days.indexOf(day);
      put(card.querySelector('[data-act="dayup"]'), 'disabled', at === 0);
      put(card.querySelector('[data-act="daydown"]'), 'disabled', at === p.days.length - 1);
      day.exercises.forEach((e, k) => {
        const box = card.querySelector(`.program-exbox[data-ex="${CSS.escape(e.id)}"]`);
        if (!box) return;
        const next = day.exercises[k + 1];
        put(box.querySelector('.program-ex [data-v="ename"]'), 'textContent', e.name);
        put(box.querySelector('.program-ex [data-v="esum"]'), 'textContent', summary(e, next));
        const ed = box.querySelector('.program-ed');
        if (!ed) return;
        setValue(ed.querySelector('[data-f="ename"]'), e.name);
        for (const b of ed.querySelectorAll('[data-act="kind"]')) b.setAttribute('aria-pressed', String(b.dataset.v === e.kind));
        for (const f of steppers(e)) {
          put(ed.querySelector(`[data-v="${f.k}"]`), 'textContent', f.show);
          const v = e[f.k];
          put(ed.querySelector(`[data-k="${f.k}"][data-d="-1"]`), 'disabled', v - f.step < f.min);
          put(ed.querySelector(`[data-k="${f.k}"][data-d="1"]`), 'disabled', v + f.step > f.max);
        }
        put(ed.querySelector('[data-l="load"]'), 'textContent', e.bodyweight ? 'Added load, kg' : 'Load, kg');
        setValue(ed.querySelector('[data-f="load"]'), decimal(e.load));
        setValue(ed.querySelector('[data-f="dur"]'), e.duration ? decimal(e.duration / 60) : '');
        for (const b of ed.querySelectorAll('[data-act="lstep"]')) b.setAttribute('aria-pressed', String(Number(b.dataset.v) === e.loadStep));
        const bw = ed.querySelector('[data-act="bw"]');
        if (bw) bw.setAttribute('aria-checked', String(e.bodyweight === true));
        const pair = ed.querySelector('[data-act="pair"]');
        if (pair) pair.setAttribute('aria-checked', String(linked(e, next)));
        put(ed.querySelector('[data-v="pairsub"]'), 'textContent', next ? `With ${next.name}` : '');
        const chips = ed.querySelectorAll('[data-act="muscle"]');
        if (chips.length) {
          const shown = shownMuscles(e);
          for (const c of chips) {
            const v = shown[c.dataset.m];
            const state = v === 1 ? 'true' : v === 0.5 ? 'mixed' : 'false';
            if (c.getAttribute('aria-pressed') !== state) c.setAttribute('aria-pressed', state);
          }
          for (const [v, text] of [['mline', muscleLine(e)], ['mweek', muscleWeekLine(p)]]) {
            const el = ed.querySelector(`[data-v="${v}"]`);
            put(el, 'textContent', text);
            put(el, 'hidden', !text);
          }
        }
        setValue(ed.querySelector('[data-f="note"]'), e.note || '');
        const hint = ed.querySelector('[data-v="carry"]');
        const line = carryLine(p, day, e);
        put(hint, 'textContent', line);
        put(hint, 'hidden', !line);
        put(ed.querySelector('[data-act="exup"]'), 'disabled', k === 0);
        put(ed.querySelector('[data-act="exdown"]'), 'disabled', k === day.exercises.length - 1);
      });
    }
    const use = root.querySelector('[data-act="use"]'), next = Cali.doc().nextProgram === p.id;
    put(use, 'hidden', next && (w.program === p.id || hasSets(w)));   // Use would change nothing
    paintMsg();
  }

  function drawEditor() {
    const { root } = screen;
    const p = Cali.program(screen.id);
    if (!p) {
      screen.key = null;
      root.innerHTML = `<header class="bar2"><button type="button" class="iconbtn" data-act="back" aria-label="Back">${icon('back')}</button><h2>Program</h2></header>` +
        '<p class="note">This program is not on this phone any more.</p>';
      return;
    }
    if (screen.openDay && !p.days.some(d => d.id === screen.openDay)) screen.openDay = null;
    if (screen.openEx && !findIn(p, screen.openEx.dayId, screen.openEx.exId)) screen.openEx = null;
    const key = shapeKey(p);
    if (key !== screen.key) {
      const y = window.scrollY;
      root.innerHTML = editorHtml(p);
      screen.key = key;
      window.scrollTo(0, y);
    }
    paintEditor(p);
  }

  function reveal(sel, focus) {
    const el = screen && screen.root.querySelector(sel);
    if (!el) return;
    if (focus) { el.focus({ preventScroll: true }); if (el.select) el.select(); }
    if (el.scrollIntoView) el.scrollIntoView({ block: focus ? 'center' : 'nearest' });
  }

  async function editorClick(ev) {
    const b = ev.target.closest('button');
    if (!b || !screen || screen.kind !== 'editor' || !screen.root.contains(b) || b.disabled || !b.dataset.act) return;
    const act = b.dataset.act;
    if (act === 'back') { Cali.back(); return; }
    screen.msg = null;
    // a field being typed in saves first (its 'change'); when that was refused, the line stays and the tap does nothing
    const active = document.activeElement;
    if (active && active !== b && screen.root.contains(active) && active.matches('input, textarea')) active.blur();
    if (!screen || (screen.msg && screen.msg.err)) return;
    const id = screen.id;
    const p = Cali.program(id);
    if (!p) return;
    paintMsg();
    const card = b.closest('[data-day]'), box = b.closest('[data-ex]');
    const dayId = card && card.dataset.day, exId = box && box.dataset.ex;
    const day = dayId ? p.days.find(d => d.id === dayId) : null;
    const k = day && exId ? day.exercises.findIndex(e => e.id === exId) : -1;
    const at = { dayId, exId };

    if (act === 'dup') {
      const d = Cali.doc(), copy = structuredClone(p);
      copy.id = newId(takenIds(d));
      copy.name = freeName(`${p.name} copy`, d.programs.map(x => x.name));
      try { addProgram(copy, 'duplicate'); } catch (err) { say(`Not copied: ${plain(err.message, copy)}.`, true); return; }
      carry = { msg: `This is the copy; ${p.name} is unchanged.` };
      Cali.go('program', { id: copy.id }, { replace: true });
      return;
    }
    if (act === 'del') {
      const why = deleteRefusal(id);
      if (why) { say(`Not deleted: ${why}.`, true); return; }
      if (!(await ask({ title: `Delete ${p.name}?`, text: 'No week has run it, so no log is lost. This cannot be undone.', ok: 'Delete' }))) return;
      const again = deleteRefusal(id);
      if (again) { say(`Not deleted: ${again}.`, true); return; }
      try { Cali.change(d => { d.programs = d.programs.filter(x => x.id !== id); }, { why: 'deleteProgram', detail: { id } }); } catch (err) {
        say(`Not deleted: ${plain(err.message, p)}.`, true);
        return;
      }
      carry = { msg: `Deleted ${p.name}.` };
      Cali.back();
      return;
    }
    if (act === 'use') { useProgram(id); paintEditor(Cali.program(id)); return; }
    if (act === 'day') { screen.openDay = screen.openDay === dayId ? null : dayId; drawEditor(); if (screen.openDay) reveal(`#program-dp-${CSS.escape(dayId)}`); return; }
    if (act === 'dayclose') { screen.openDay = null; drawEditor(); return; }
    if (act === 'dayup' || act === 'daydown') {
      const i = p.days.findIndex(d => d.id === dayId), j = i + (act === 'dayup' ? -1 : 1);
      edit(id, x => { const [moved] = x.days.splice(i, 1); x.days.splice(j, 0, moved); }, 'moveDay', at);
      reveal(`.program-day[data-day="${CSS.escape(dayId)}"]`);
      return;
    }
    if (act === 'dayrm') {
      if (p.days.length === 1) { say('Not removed: a program needs at least one day.', true); return; }
      const n = day.exercises.length;
      if (!(await ask({ title: `Remove day ${day.name}?`, ok: 'Remove',
        text: `${n ? `Its ${plural(n, 'exercise')} go${n === 1 ? 'es' : ''} with it. ` : ''}Weeks already logged keep theirs.` }))) return;
      edit(id, x => { x.days = x.days.filter(d => d.id !== dayId); }, 'removeDay', at);
      return;
    }
    if (act === 'addday') {
      const taken = takenIds(Cali.doc()), newDay = { id: newId(taken), name: dayName(p), exercises: [] };
      if (edit(id, x => { x.days.push(newDay); }, 'addDay')) reveal(`.program-day[data-day="${CSS.escape(newDay.id)}"]`);
      return;
    }
    if (act === 'addex') {
      const e = newExercise(newId(takenIds(Cali.doc())));
      if (!edit(id, (x, dd) => { dd.exercises.push(e); }, 'addExercise', at)) return;
      screen.openEx = { dayId, exId: e.id };
      drawEditor();
      reveal(`#program-ed-${CSS.escape(e.id)} [data-f="ename"]`, true);
      return;
    }
    if (act === 'ex') {
      const open = screen.openEx && screen.openEx.dayId === dayId && screen.openEx.exId === exId;
      screen.openEx = open ? null : { dayId, exId };
      drawEditor();
      if (!open) reveal(`#program-ed-${CSS.escape(exId)}`);
      return;
    }
    if (act === 'exclose') { screen.openEx = null; drawEditor(); reveal(`.program-exbox[data-ex="${CSS.escape(exId)}"]`); return; }
    if (k < 0) return;
    const e = day.exercises[k];
    if (act === 'kind') { edit(id, (x, dd, ee) => setKind(x, dd, ee, b.dataset.v), 'kind', at); return; }
    if (act === 'step') {
      const f = steppers(e).find(s => s.k === b.dataset.k);
      const v = f && e[f.k] + Number(b.dataset.d) * f.step;
      if (f && v >= f.min && v <= f.max) edit(id, (x, dd, ee) => { ee[f.k] = v; }, f.k, at);
      return;
    }
    if (act === 'lstep') { edit(id, (x, dd, ee) => { ee.loadStep = Number(b.dataset.v); }, 'loadStep', at); return; }
    if (act === 'muscle') { edit(id, (x, dd, ee) => cycleMuscle(ee, b.dataset.m), 'muscles', at); return; }
    if (act === 'bw') { edit(id, (x, dd, ee) => { if (ee.bodyweight) delete ee.bodyweight; else ee.bodyweight = true; }, 'bodyweight', at); return; }
    if (act === 'pair') {
      edit(id, (x, dd) => { if (linked(dd.exercises[k], dd.exercises[k + 1])) unlink(dd, k); else link(dd, k); }, 'pair', at);
      return;
    }
    if (act === 'exup' || act === 'exdown') {
      edit(id, (x, dd) => { moveExercise(dd, k, act === 'exup' ? -1 : 1); }, 'moveExercise', at);
      reveal(`#program-ed-${CSS.escape(exId)}`);
      return;
    }
    if (act === 'exrm') {
      if (!(await ask({ title: `Remove ${e.name}?`, ok: 'Remove', text: `It leaves day ${day.name} of ${p.name}. Weeks already logged keep it.` }))) return;
      edit(id, (x, dd) => { dd.exercises = dd.exercises.filter(z => z.id !== exId); }, 'removeExercise', at);
    }
  }

  // a field: saved when it is left or Enter is pressed
  function editorChange(ev) {
    const input = ev.target;
    const f = input.dataset && input.dataset.f;
    if (!f || !screen || screen.kind !== 'editor') return;
    const id = screen.id, p = Cali.program(id);
    if (!p) return;
    const card = input.closest('[data-day]'), box = input.closest('[data-ex]');
    const at = { dayId: card && card.dataset.day, exId: box && box.dataset.ex };
    const day = at.dayId && p.days.find(d => d.id === at.dayId);
    const e = day && at.exId && day.exercises.find(x => x.id === at.exId);
    const text = input.value.trim();
    screen.msg = null;
    if (f === 'pname' || f === 'dname' || f === 'ename') {
      const was = f === 'pname' ? p.name : f === 'dname' ? day.name : e.name;
      if (!text) { input.value = was; say(`Not saved: a name is needed; it stays ${was}.`, true); return; }
      if (text === was) { input.value = was; return; }
      edit(id, (x, dd, ee) => { if (f === 'pname') x.name = text; else if (f === 'dname') dd.name = text; else { ee.name = text; firstGuess(ee); } }, f, at);
      return;
    }
    if (!e) return;
    const number = t => Number(t.replace(',', '.'));
    let ok = true;
    if (f === 'load') ok = edit(id, (x, dd, ee) => { ee.load = text === '' ? 0 : number(text); }, 'load', at);
    if (f === 'dur') ok = edit(id, (x, dd, ee) => { if (text === '') delete ee.duration; else ee.duration = Math.round(number(text) * 60); }, 'duration', at);
    if (f === 'note') {
      const note = input.value.replace(/\s+/g, ' ').trim();
      if (note !== (e.note || '')) ok = edit(id, (x, dd, ee) => { if (note) ee.note = note; else delete ee.note; }, 'note', at);
    }
    if (!ok) { input.value = f === 'load' ? decimal(e.load) : f === 'dur' ? (e.duration ? decimal(e.duration / 60) : '') : (e.note || ''); }
  }

  Cali.route('program', {
    render(root, args) {
      root.classList.add('program');
      const start = carry || {};
      carry = null;
      screen = { kind: 'editor', root, id: args && typeof args.id === 'string' ? args.id : Cali.doc().activeProgram, key: null, openDay: null, openEx: null,
        msg: start.msg ? { text: start.msg, err: Boolean(start.err) } : null };
      const at = args && typeof args.dayId === 'string' && typeof args.exId === 'string' ? { dayId: args.dayId, exId: args.exId } : null;
      if (at) { screen.openEx = at; start.focus = null; }
      root.addEventListener('click', editorClick);
      root.addEventListener('change', editorChange);
      root.addEventListener('keydown', ev => {
        if (ev.key === 'Enter' && ev.target.matches && ev.target.matches('[data-f]')) { ev.preventDefault(); ev.target.blur(); }
      });
      drawEditor();
      if (start.focus) reveal(start.focus, true);
      else if (at && screen.openEx) reveal(`#program-ed-${CSS.escape(at.exId)} .program-muscles`);
    },
    update(root) { if (screen && screen.root === root) drawEditor(); },
    leave() { screen = null; closeDialogs(); },
  });
})();
