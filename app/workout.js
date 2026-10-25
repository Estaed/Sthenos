/* The workout day (Task-01): route 'day' { week, dayId, readOnly }, round 6 tap-only look (design/screens.html,
   screens 1, 2, 7, 8; styles in app/workout.css). The whole day on one screen: day tabs, every exercise with last
   week's sets and a 4-week trend line, a cell per set, and the docked score bug (current set, reps, rest).

   Logging: a tap on a set cell is Cali.tap (empty = target, again = one less), a hold of HOLD_MS is Cali.hold (one
   more). Tap and hold are told apart here from pointer down/up on Cali.now(), never from the browser's click or long
   press, so the hold opens no context menu and selects no text; a touch that starts within BOUNCE_MS of the last
   accepted one is a bounce and does nothing. A keyboard click (Enter / Space) on a cell is a tap. Cells are patched
   in place on every change, so a finger is never left on a replaced element.

   After a log (any source, through the 'log' event): the Undo snackbar shows until the next log or UNDO_MS, and as long
   a short set just tapped down carries the '−1' badge (screen 8); a new set
   (empty -> logged) cancels the running rest and, on a running day, starts the next one from Cali.settings (restPair
   inside a pair, restExercise after the pair's last set or a single exercise; none after the day's last set or a
   check row) as the countdown 'rest' in Cali.timers, scheduled at once with Cali.alert.schedule('rest', endAt, 'rest')
   and 'headsup' (tag 'rest-headsup') headsUp seconds before; an edit of a logged set keeps the rest running; tapping
   the set the rest belongs to down to 0 or clearing it stops it, and a hold back up from 0 starts a new one (a set at
   0 counts as not done everywhere: it can be the set in hand again). Each exercise runs through its sets before the
   next (Cali.setOrder), so every rest is restExercise unless settings.alternatePairs is on. The first log of a day
   that was never started starts it; clearing, undoing or tapping down to 0 the last done set of a running day takes it
   back to not started, which is how a day is reset (Tarık 2026-10-24). A rest lives only
   while its day runs in the current week: Finish (or the summary's Done, a new week) stops it and cancels its alerts,
   and the score bug shows a rest only on its own day; any other day shows the rest its next log will start.

   Session: Start stores the day's startedAt (the clock in the app bar counts from it); Finish stores finishedAt and
   opens 'summary' { week, dayId } (app/summary.js: Resume, Done -> 'dayDone'). The screen stays awake (Wake Lock)
   while a day of the current week runs and the keepAwake setting is on; the lock is taken again when the page
   becomes visible. Timed one-off rows (check rows with a duration: stretch, walk) are tiles: a tap or a hold that marks
   one done opens Cali.go('timer', { countdown: seconds }) once the finger lifts. A past week (or readOnly: true) shows the same sheet with no taps. */
(() => {
  'use strict';
  const HOLD_MS = 500;      // finger down this long = hold (+1)
  const BOUNCE_MS = 150;    // a touch starting this soon after the last accepted one is ignored
  const SLOP_PX = 12;       // a finger that moves further is scrolling, not tapping
  const UNDO_MS = 8000;
  const TICK_MS = 250;
  const esc = Cali.esc;
  const ICONS = {
    check: '<path d="M20 6 9 17l-5-5"/>',
    timer: '<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/><circle cx="12" cy="14" r="8"/>',
  };
  const ic = name => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
  const pad = n => String(n).padStart(2, '0');
  const hms = s => (s >= 3600 ? `${Math.floor(s / 3600)}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}` : `${Math.floor(s / 60)}:${pad(s % 60)}`);
  const ms = iso => (iso ? Date.parse(iso) : NaN);
  const dayOf = (n, dayId) => { const w = Cali.week(n); return (w && w.days[dayId]) || null; };
  const running = day => Boolean(day && day.startedAt && !day.finishedAt);
  const unit = ex => (ex.kind === 'time' ? 's' : '');
  const minutes = s => (s % 60 ? hms(s) : `${s / 60} min`);
  const did = v => Boolean(v && v.r > 0);   // a set at 0 is not done: it holds no rest and does not keep a day started

  let screen = null;   // the day screen shown: { root, args, a, key, list, now, cache, ticker }

  // ── the day's shape ───────────────────────────────────────────────
  // cards as the screen shows them: a pair (adjacent, same pair) shares a card, a single exercise has its own;
  // check rows (stretch, walk, warm-up) become tiles at the end of the card before them, or a card of their own
  function cardsOf(list) {
    const cards = [];
    for (const ex of list) {
      const last = cards[cards.length - 1];
      if (ex.kind === 'check') {
        if (last) last.tiles.push(ex); else cards.push({ rows: [], tiles: [ex] });
      } else if (last && !last.tiles.length && ex.pair && last.rows.length && last.rows[last.rows.length - 1].pair === ex.pair) {
        last.rows.push(ex);
      } else cards.push({ rows: [ex], tiles: [] });
    }
    return cards;
  }

  // the set in hand: the first set not done after the one done last (Cali.setOrder), else the first not done
  function currentSet(n, dayId) {
    const day = dayOf(n, dayId);
    if (!day) return null;
    const order = Cali.setOrder(dayId, n);
    const at = s => { const v = day.exercises[s.exId].sets[s.i]; return v && v.r > 0 ? v.at : null; };   // a set at 0 is not done
    let last = -1, lastAt = '';
    order.forEach((s, k) => { const t = at(s); if (t !== null && t >= lastAt) { lastAt = t; last = k; } });
    for (let k = last + 1; k < order.length; k++) if (at(order[k]) === null) return order[k];
    return order.find(s => at(s) === null) || null;
  }

  // which rest follows set i of exId: with alternatePairs on, 'pair' inside a pair; else 'exercise'
  function restKind(n, dayId, exId, i) {
    const list = Cali.dayExercises(n, dayId);
    const k = list.findIndex(e => e.id === exId);
    const ex = list[k];
    if (!ex || !ex.pair || !Cali.settings.get('alternatePairs')) return 'exercise';
    let from = k, to = k;
    while (from > 0 && list[from - 1].pair === ex.pair) from--;
    while (to < list.length - 1 && list[to + 1].pair === ex.pair) to++;
    if (from === to) return 'exercise';
    const ids = new Set(list.slice(from, to + 1).map(e => e.id));
    const inGroup = Cali.setOrder(dayId, n).filter(s => ids.has(s.exId));
    const end = inGroup[inGroup.length - 1];
    return end.exId === exId && end.i === i ? 'exercise' : 'pair';
  }
  const restSeconds = kind => Cali.settings.get(kind === 'pair' ? 'restPair' : 'restExercise');

  // the rest that logging the set in hand will start, as the 'log' handler below decides it, or null when none will:
  // no set in hand, a check row, the day's last set, a finished day, 'start rest after a log' off, or a 0 s rest
  function restAfter(s, day) {
    const now = s.now;
    const ex = now && s.list.find(e => e.id === now.exId);
    if (!ex || ex.kind === 'check' || (day && day.finishedAt) || !Cali.settings.get('restAfterLog')) return null;
    if (!s.list.some(e => e.sets.some((x, i) => !did(x) && !(e.id === now.exId && i === now.i)))) return null;
    const kind = restKind(s.a.week, s.a.dayId, now.exId, now.i);
    return restSeconds(kind) > 0 ? kind : null;
  }

  // ── rest timer and alerts ─────────────────────────────────────────
  function stopRest() {
    Cali.alert.cancel('rest');
    Cali.alert.cancel('rest-headsup');
    if (Cali.timers.get('rest')) Cali.timers.stop('rest');
  }
  function startRest(week, dayId, exId, i) {
    const kind = restKind(week, dayId, exId, i);
    const seconds = restSeconds(kind);
    if (!(seconds > 0)) return false;
    const t = Cali.timers.start('rest', { duration: seconds * 1000, kind: 'rest', data: { week, dayId, exId, i, rest: kind } });
    Cali.alert.schedule('rest', t.endAt, 'rest');
    const ahead = Cali.settings.get('headsUp');
    if (ahead > 0 && seconds > ahead) Cali.alert.schedule('headsup', t.endAt - ahead * 1000, 'rest-headsup');
    return true;
  }
  const restOf = (l, t = Cali.timers.get('rest')) => Boolean(t && t.data && t.data.week === l.week && t.data.dayId === l.dayId
    && t.data.exId === l.exId && t.data.i === l.i);

  // ── session (Start / Finish) ──────────────────────────────────────
  function setDay(week, dayId, why, fn) {
    Cali.change(d => { fn(d.weeks.find(w => w.n === week).days[dayId]); }, { why, detail: { week, dayId } });
  }
  const startDay = (week, dayId) => setDay(week, dayId, 'start', day => { day.startedAt = Cali.iso(); delete day.finishedAt; });
  const finishDay = (week, dayId) => setDay(week, dayId, 'finish', day => { if (!day.startedAt) day.startedAt = Cali.iso(); day.finishedAt = Cali.iso(); });

  // ── Undo ──────────────────────────────────────────────────────────
  let undo = null;          // { l: the 'log' payload, until, rest: this log started the rest }
  let undoTimer = 0;
  let undoing = false;
  function hideUndo() { clearTimeout(undoTimer); undo = null; if (screen) patch(screen); }   // the snackbar and the '−1' badge
  function doUndo() {
    const u = undo;
    hideUndo();
    if (!u || u.until <= Cali.now() || !Cali.week() || Cali.week().n !== u.l.week) return;
    undoing = true;
    try { Cali.log(u.l.dayId, u.l.exId, u.l.i, u.l.prev); } finally { undoing = false; }
    if (u.rest && restOf(u.l)) stopRest();
    if (!did(u.l.prev)) unstartIfEmpty(u.l.week, u.l.dayId);
  }

  // a running day whose last done set was cleared or tapped down to 0 goes back to not started (its clock and rest
  // stop with it); sets left at 0 stay as they are, a tap clears them
  function unstartIfEmpty(week, dayId) {
    const day = dayOf(week, dayId);
    if (!running(day) || Object.values(day.exercises || {}).some(e => e.sets.some(did))) return;
    setDay(week, dayId, 'unstart', d => { delete d.startedAt; });
  }

  Cali.on('log', l => {
    const cur = Cali.week();
    if (undoing || !cur || l.week !== cur.n) return;
    let day = cur.days[l.dayId];
    if (did(l.value) && day && !day.startedAt) { startDay(l.week, l.dayId); day = dayOf(l.week, l.dayId); }
    const ex = Cali.weekExercise(l.week, l.dayId, l.exId);
    let rest = false;
    if (!did(l.prev) && did(l.value)) {
      stopRest();
      if (ex.kind !== 'check' && running(day) && Cali.settings.get('restAfterLog') && Cali.nextSet(l.dayId, l.week)) {
        rest = startRest(l.week, l.dayId, l.exId, l.i);
      }
    } else if (!did(l.value) && restOf(l)) stopRest();
    if (!did(l.value)) unstartIfEmpty(l.week, l.dayId);
    clearTimeout(undoTimer);
    undo = { l, until: Cali.now() + UNDO_MS, rest };
    undoTimer = setTimeout(hideUndo, UNDO_MS);
    if (screen) patch(screen);   // 'change' redrew the day before this event: now the snackbar and the badge
  });

  // a rest lives while its day runs in the current week: Finish, the summary's Done (which stores finishedAt when it is
  // missing) or a new week ends it and its alerts
  Cali.on('change', () => {
    const t = Cali.timers.get('rest'), cur = Cali.week();
    if (t && t.data && t.data.dayId && !(cur && t.data.week === cur.n && running(dayOf(t.data.week, t.data.dayId)))) stopRest();
  });

  // ── keep the screen awake while a day of the current week runs ─────
  let lock = null, asking = false, refused = false;
  function wantAwake() {
    const w = Cali.week();
    return Boolean(w && Cali.settings.get('keepAwake') && Object.values(w.days).some(running));
  }
  function syncWake() {
    const want = wantAwake();
    if (!want && lock) { const l = lock; lock = null; l.release().catch(() => {}); return; }
    if (!want || lock || asking || refused || document.visibilityState !== 'visible' || !navigator.wakeLock) return;
    asking = true;
    navigator.wakeLock.request('screen').then(sentinel => {
      asking = false;
      lock = sentinel;
      sentinel.addEventListener('release', () => { if (lock === sentinel) lock = null; });
      if (!wantAwake()) syncWake();
    }, () => { asking = false; refused = true; });   // refused (battery saver, policy): asked again when visible
  }
  Cali.on('change', syncWake);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    refused = false;
    syncWake();
    if (screen) tick(screen);
  });

  // ── what each element shows ───────────────────────────────────────
  // a cell's text as a number and its small part ('s', '/12'). It sits in 38 px inside a short set's ring (44 px
  // without one): '11/12', '35/40' or '120s' at full size do not fit, so they take the compact size (workout-fit), and
  // a short set too long even then ('95/100') shows its reps alone, the ring still drawing reps/target.
  function cellText(n, small) {
    const len = String(n).length + small.length;
    if (small.startsWith('/') && len >= 6) return { html: String(n), fit: true };
    return { html: `${n}${small ? `<small>${small}</small>` : ''}`, fit: len >= 5 || (String(n).length >= 3 && small !== '') };
  }

  // edit: this cell holds the log the Undo snackbar shows; a short set just tapped down then carries the round-6 '−1'
  // badge (screen 8): the next tap takes one more step off
  function cellView(ex, i, isNow, edit) {
    const s = ex.sets[i];
    const u = unit(ex);
    const who = `${ex.name}, set ${i + 1}: `;
    const sec = ex.kind === 'time' ? ' s' : '';
    if (s === null) {
      return { cls: isNow ? 'now' : 'todo', ...cellText(ex.target, u), p: '', hint: null,
        label: `${who}${isNow ? 'current, ' : ''}target ${ex.target}${sec}` };
    }
    if (s.r >= ex.target) return { cls: 'hit', ...cellText(s.r, u), p: '', hint: null, label: `${who}${s.r}${sec}, done` };
    const p = ex.target > 0 ? `${Math.round(100 * s.r / ex.target)}%` : '0%';
    const step = ex.kind === 'time' ? 5 : 1;
    const hint = edit && s.r > 0 ? `−${step}` : null;
    return { cls: `short${hint ? ' workout-edit' : ''}`, ...cellText(s.r, `/${ex.target}`), p, hint,
      label: `${who}${s.r} of ${ex.target}${sec}, short${hint ? `; tap again for ${Math.max(0, s.r - step)}` : ''}` };
  }

  function tileView(ex, isNow) {
    const done = Boolean(ex.sets[0]);
    const val = done ? 'Done' : ex.duration ? minutes(ex.duration) : 'To do';
    return { cls: done ? 'hit' : isNow ? 'now' : '', val,
      label: `${ex.name}: ${done ? 'done' : ex.duration ? `${minutes(ex.duration)}, starts the countdown` : 'to do'}` };
  }

  // the latest earlier week with a logged set, and the average per set of up to three earlier weeks
  function past(a, ex) {
    const hist = Cali.history(a.dayId, ex.id, a.week).filter(h => h.sets.some(s => s !== null));
    return { last: hist[0] || null, trend: hist.slice(0, 3).reverse().map(h => average(h.sets)) };
  }
  function average(sets) {
    const r = sets.filter(s => s !== null).map(s => s.r);
    return r.reduce((x, y) => x + y, 0) / r.length;
  }

  function spark(ex, p) {
    const box = 'class="workout-spark" viewBox="0 0 40 16" width="40" height="16"';
    if (!p.trend.length) return `<svg ${box} aria-hidden="true"></svg>`;
    const logged = ex.sets.some(s => s !== null);
    const now = logged ? average(ex.sets) : ex.target;
    const vals = [...p.trend, now];
    const xs = [2, 14, 26, 38].slice(4 - vals.length);
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const span = Math.max(hi - lo, ex.kind === 'time' ? 8 : 1.5), mid = (hi + lo) / 2;
    const y = v => (2.5 + 11 * (1 - (v - (mid - span / 2)) / span)).toFixed(1);
    const pts = vals.map((v, k) => `${xs[k]},${y(v)}`);
    const xy = q => q.split(',');
    const r1 = v => Math.round(v * 10) / 10;
    const u = unit(ex) ? ' s' : '';
    const label = `Average per set in earlier weeks ${p.trend.map(r1).join(', ')}${u}; this week ${logged ? 'so far' : 'planned'} ${r1(now)}${u}`;
    const [ex1, ey1] = xy(pts[pts.length - 1]);
    return `<svg ${box} role="img" aria-label="${esc(label)}">` +
      '<line class="base" x1="0" x2="40" y1="15.5" y2="15.5"/>' +
      (pts.length > 2 ? `<polyline class="ln" points="${pts.slice(0, -1).join(' ')}"/>` : '') +
      `<polyline class="ln${logged ? '' : ' plan'}" points="${pts.slice(-2).join(' ')}"/>` +
      pts.slice(0, -1).map(q => `<circle class="dot" cx="${xy(q)[0]}" cy="${xy(q)[1]}" r="1.6"/>`).join('') +
      (logged ? `<circle class="now" cx="${ex1}" cy="${ey1}" r="3"/>` : `<circle class="tgt" cx="${ex1}" cy="${ey1}" r="2.3"/>`) +
      '</svg>';
  }

  function lastText(ex, p) {
    if (!p.last) return { text: '–', label: 'Last week: none logged' };
    const u = unit(ex);
    const vals = p.last.sets.map(s => (s ? `${s.r}${u}` : '–'));
    return { text: vals.join(' '), label: `Last logged, week ${p.last.week}: ${vals.join(', ')}` };
  }

  // "+2.5 kg next" once every set is logged and Cali.progress moves the load up
  function nextTag(a, ex) {
    if (ex.kind === 'check' || ex.sets.some(s => s === null)) return '';
    let next;
    try { next = Cali.progress(ex, Cali.history(a.dayId, ex.id, a.week)); } catch (e) { return ''; }
    if (!(next.load > ex.load)) return '';
    return `<span class="tag">+${Math.round((next.load - ex.load) * 100) / 100} kg next</span>`;
  }

  const range = ex => (ex.kind === 'reps' ? `${ex.repMin}–${ex.repMax}` : ex.kind === 'time' ? 'hold' : '');
  const metaHtml = (a, ex) => `<b>${esc(Cali.loadLabel(ex.load, ex.bodyweight))}</b><span>${range(ex)}</span>${nextTag(a, ex)}`;

  // ── markup, built once per day shown ──────────────────────────────
  function setAttrs(a, ex, i) {
    return `${a.readOnly ? '' : `type="button" data-set="${esc(`${a.dayId}:${ex.id}:${i}`)}" `}data-cell="${esc(ex.id)}:${i}"`;
  }
  function rowHtml(a, ex) {
    const tag = a.readOnly ? 'span' : 'button';
    const cells = ex.sets.map((_, i) => `<${tag} ${setAttrs(a, ex, i)} class="cell num"><span></span></${tag}>`);
    while (cells.length % 3) cells.push('<span class="cell void" aria-hidden="true"></span>');
    const head = a.readOnly ? '<div class="workout-ex">'
      : `<button type="button" class="workout-ex" data-edit="${esc(ex.id)}" aria-expanded="false" aria-controls="workout-ed-${esc(ex.id)}">`;
    return `<div class="workout-row" data-ex="${esc(ex.id)}">` +
      `${head}<div class="workout-name">${esc(ex.name)}</div><div class="workout-meta"></div>` +
      `${ex.note ? `<div class="workout-note">${esc(ex.note)}</div>` : ''}${a.readOnly ? '</div>' : '</button>'}` +
      '<div class="workout-trend"><span class="workout-spark-box"></span><span class="workout-last"></span></div>' +
      `<div class="workout-cells">${cells.join('')}</div></div>` +
      (a.readOnly ? '' : `<div class="workout-ed" id="workout-ed-${esc(ex.id)}" data-ed="${esc(ex.id)}" hidden></div>`);
  }
  function tileHtml(a, ex) {
    const tag = a.readOnly ? 'span' : 'button';
    return `<${tag} ${setAttrs(a, ex, 0)} class="workout-tile">${ic(ex.duration ? 'timer' : 'check')}` +
      `<span><span class="lbl">${esc(ex.name)}</span><span class="val num"></span></span></${tag}>`;
  }

  // a tile's label holds only the name, so its note (how to do it) is written out in full under the tiles
  const tileNotes = tiles => (tiles.some(ex => ex.note) ? '<div class="workout-notes">' +
    tiles.filter(ex => ex.note).map(ex => `<p><b>${esc(ex.name)}</b> ${esc(ex.note)}</p>`).join('') + '</div>' : '');

  function build(s) {
    const { a, root } = s;
    const w = Cali.week(a.week);
    const days = (Cali.program(w.program) || { days: [] }).days.filter(d => w.days[d.id]).map(d => ({ id: d.id, name: d.name }));
    for (const id of Object.keys(w.days)) if (!days.some(d => d.id === id)) days.push({ id, name: id });
    const cols = days.map(d => (d.id === a.dayId ? '1.15fr' : '1fr')).join(' ');
    root.innerHTML =
      '<header class="appbar workout-bar">' +
        `<span data-slot="dayheader"><span class="week" data-fallback>Week ${w.n}</span></span>` +
        '<span class="workout-clock num" role="timer" hidden></span>' +
        '<span data-slot="topbar"></span>' +
        '<button type="button" class="workout-session" data-act="session" hidden></button>' +
      '</header>' +
      `<nav class="workout-days" aria-label="Day" style="grid-template-columns:${cols}">${days.map(d => {
        const on = d.id === a.dayId;
        return `<button type="button" data-day="${esc(d.id)}" aria-pressed="${on}">${on ? ic('check') : ''}<span>${esc(d.name)}</span></button>`;
      }).join('')}</nav>` +
      '<section class="workout-list" aria-label="Exercises">' +
        '<div class="workout-row workout-cols" aria-hidden="true"><span></span><span>Last wk</span><span>This week</span></div>' +
        cardsOf(s.list).map(c => `<div class="card workout-card">${c.rows.map(ex => rowHtml(a, ex)).join('')}` +
          (c.tiles.length ? `<div class="workout-timed">${c.tiles.map(ex => tileHtml(a, ex)).join('')}</div>` : '') +
          tileNotes(c.tiles) + '</div>').join('') +
      '</section>' +
      (a.readOnly ? '' :
        '<section class="workout-sheet" aria-label="Current set">' +
          '<div class="snack workout-snack" role="status" hidden><span class="workout-snack-text"></span><button type="button" data-act="undo">Undo</button></div>' +
          '<div class="anchor workout-bug" role="group">' +
            '<div class="workout-bug-head"><span class="workout-bug-name"></span><span class="workout-bug-meta"></span></div>' +
            '<div class="workout-score">' +
              '<div><span class="lab"><span data-lab="set"></span></span><span class="big" data-big="set"></span></div>' +
              '<div><span class="lab"><span data-lab="reps"></span></span><span class="big" data-big="reps"></span></div>' +
              '<div class="rest" role="timer"><span class="lab"><span data-lab="rest"></span><span data-lab="of"></span></span><span class="big" data-big="rest"></span></div>' +
            '</div>' +
            '<div class="bar" aria-hidden="true"><i style="width:0%"></i></div>' +
          '</div>' +
        '</section>');
    s.cache = new Map();
  }

  // ── patching: only what changed is written; cells keep their element ──
  function put(s, el, prop, value) {
    if (!el) return;
    let c = s.cache.get(el);
    if (!c) s.cache.set(el, (c = {}));
    if (c[prop] === value) return;
    c[prop] = value;
    if (prop === 'html') el.innerHTML = value;
    else if (prop === 'text') el.textContent = value;
    else if (prop === 'class') el.className = value;
    else if (prop === 'hidden') el.hidden = value;
    else if (prop === '--p') { if (value) el.style.setProperty('--p', value); else el.style.removeProperty('--p'); }
    else if (prop === 'width') el.style.width = value;
    else if (value === null) el.removeAttribute(prop);
    else el.setAttribute(prop, value);
  }
  const at = (root, sel) => root.querySelector(sel);

  function patch(s) {
    const { a, root } = s;
    s.list = Cali.dayExercises(a.week, a.dayId);
    s.now = a.readOnly ? null : currentSet(a.week, a.dayId);
    const isNow = (ex, i) => Boolean(s.now && s.now.exId === ex.id && s.now.i === i);
    const l = !a.readOnly && undo && undo.until > Cali.now() && undo.l.week === a.week && undo.l.dayId === a.dayId ? undo.l : null;
    const isEdit = (ex, i) => Boolean(l && l.value && l.exId === ex.id && l.i === i);
    for (const ex of s.list) {
      if (ex.kind === 'check') {
        const el = at(root, `[data-cell="${CSS.escape(ex.id)}:0"]`);
        const v = tileView(ex, isNow(ex, 0));
        put(s, el, 'class', `workout-tile${v.cls ? ' ' + v.cls : ''}`);
        put(s, el, 'aria-label', v.label);
        put(s, el && el.querySelector('.val'), 'text', v.val);
        continue;
      }
      const row = at(root, `.workout-row[data-ex="${CSS.escape(ex.id)}"]`);
      if (!row) continue;
      const p = past(a, ex);
      const last = lastText(ex, p);
      put(s, at(row, '.workout-meta'), 'html', metaHtml(a, ex));
      put(s, at(row, '.workout-spark-box'), 'html', spark(ex, p));
      put(s, at(row, '.workout-last'), 'text', last.text);
      put(s, at(row, '.workout-last'), 'aria-label', last.label);
      ex.sets.forEach((_, i) => {
        const el = at(row, `[data-cell="${CSS.escape(ex.id)}:${i}"]`);
        const v = cellView(ex, i, isNow(ex, i), isEdit(ex, i));
        put(s, el, 'class', `cell num${ex.kind === 'time' ? ' sec' : ''}${v.fit ? ' workout-fit' : ''} ${v.cls}`);
        put(s, el, 'aria-label', v.label);
        put(s, el, '--p', v.p);
        put(s, el, 'data-hint', v.hint);
        put(s, el && el.firstElementChild, 'html', v.html);
      });
    }
    patchEditor(s);
    patchSession(s);
    patchBug(s);
    patchSnack(s);
    tick(s);
  }

  function patchSession(s) {
    const { a, root } = s;
    const day = dayOf(a.week, a.dayId);
    const btn = at(root, '[data-act="session"]');
    const label = day && day.finishedAt ? 'Summary' : a.readOnly ? '' : day && day.startedAt ? 'Finish' : 'Start';
    put(s, btn, 'hidden', !label);
    put(s, btn, 'text', label);
    put(s, btn, 'class', `workout-session${label === 'Start' ? ' start' : ''}`);
  }

  function patchBug(s) {
    const { a, root } = s;
    if (a.readOnly) return;
    const bug = at(root, '.workout-bug');
    const now = s.now;
    const ex = now && s.list.find(e => e.id === now.exId);
    let name, meta = '', set, reps, repsLab;
    if (ex) {
      name = ex.name;
      if (ex.kind !== 'check') meta = `<span>${esc(Cali.loadLabel(ex.load, ex.bodyweight))}</span><span>${range(ex)}</span>`;
      set = `${now.i + 1}<small>/${ex.sets.length}</small>`;
      // a timed row's length as one number with its unit in the label ("Minutes 22"): "22:00" is wider than the column
      const whole = ex.duration && !(ex.duration % 60);
      repsLab = ex.kind === 'time' ? 'Hold' : ex.kind === 'check' ? (ex.duration ? (whole ? 'Minutes' : 'Seconds') : 'Check') : 'Reps';
      reps = ex.kind === 'time' ? `${ex.target}<small>s</small>`
        : ex.kind === 'check' ? (ex.duration ? String(whole ? ex.duration / 60 : ex.duration) : '✓') : String(ex.target);
    } else {
      const sets = s.list.filter(e => e.kind !== 'check').flatMap(e => e.sets.map(x => ({ x, t: e.target })));
      name = 'Every set is logged';
      set = `${sets.filter(o => o.x !== null).length}<small>/${sets.length}</small>`;
      repsLab = 'Short';
      reps = String(sets.filter(o => o.x !== null && o.x.r < o.t).length);
    }
    put(s, at(bug, '.workout-bug-name'), 'text', name);
    put(s, at(bug, '.workout-bug-meta'), 'html', meta);
    put(s, at(bug, '[data-lab="set"]'), 'text', ex ? 'Set' : 'Sets');
    put(s, at(bug, '[data-big="set"]'), 'html', set);
    put(s, at(bug, '[data-lab="reps"]'), 'text', repsLab);
    put(s, at(bug, '[data-big="reps"]'), 'html', reps);
    put(s, bug, 'aria-label', ex ? `Current set: ${ex.name}, set ${now.i + 1} of ${ex.sets.length}` : 'Every set of this day is logged');
  }

  function snackHtml(l) {
    const ex = Cali.weekExercise(l.week, l.dayId, l.exId);
    if (!ex) return '';
    const name = `<span class="workout-snack-name">${esc(ex.name)}</span>`;
    if (ex.kind === 'check') return `${name}: ${l.value ? 'done' : 'not done'}`;
    const where = `${name} set ${l.i + 1}`;
    if (l.value === null) return `${where} cleared`;
    const u = unit(ex) ? ' s' : '';
    const r = l.value.r;
    const value = r >= ex.target ? `<b class="num">${r}</b>${u}` : `<b class="num">${r}</b> of ${ex.target}${u}`;
    const again = r <= 0 ? 'clear' : `<b class="num">${Math.max(0, r - (ex.kind === 'time' ? 5 : 1))}</b>`;
    return `${where}: ${value}. Tap again: ${again}`;
  }

  // Undo floats 8 px above the docked sheet (screen 8). When the set he taps next or the set it names ("Tap again")
  // lies under that spot (the stretch tile after the last Plank set), it rises just above them, so a tap on either
  // never lands on the snackbar; with no room above, it stays where screen 8 has it.
  function patchSnack(s) {
    const box = at(s.root, '.workout-snack');
    if (!box) return;
    const show = Boolean(undo && undo.until > Cali.now());
    put(s, box, 'hidden', !show);
    if (!show) return;
    put(s, at(box, '.workout-snack-text'), 'html', snackHtml(undo.l));
    const l = undo.l, sheet = box.parentElement, home = sheet.getBoundingClientRect().top + sheet.clientTop - 8, h = box.offsetHeight;
    const keep = [s.now, l.week === s.a.week && l.dayId === s.a.dayId ? l : null]
      .map(c => c && at(s.root, `[data-cell="${CSS.escape(c.exId)}:${c.i}"]`))
      .concat(at(s.root, '.workout-ed:not([hidden]) [data-act="ed-done"]')).filter(Boolean)   // and an open editor's Done
      .map(el => el.getBoundingClientRect()).sort((p, q) => q.top - p.top);
    let bottom = home;
    for (const r of keep) if (r.bottom > bottom - h && r.top < bottom) bottom = r.top - 8;
    const lift = bottom - h < 0 ? 0 : Math.round(home - bottom);
    put(s, box, 'style', lift ? `--workout-snack-lift:${lift}px` : null);
  }
  document.addEventListener('scroll', () => { if (screen && undo) patchSnack(screen); }, { capture: true, passive: true });   // a longer day scrolls a set under it

  // the moving numbers: the session clock and the rest, both computed from stored timestamps on every tick
  function tick(s) {
    const { a, root } = s;
    const day = dayOf(a.week, a.dayId);
    const clock = at(root, '.workout-clock');
    if (day && day.startedAt) {
      const end = day.finishedAt ? ms(day.finishedAt) : Cali.now();
      const t = hms(Math.max(0, Math.floor((end - ms(day.startedAt)) / 1000)));
      put(s, clock, 'hidden', false);
      put(s, clock, 'text', t);
      put(s, clock, 'class', `workout-clock num${day.finishedAt ? ' done' : ''}`);
      put(s, clock, 'aria-label', `${day.finishedAt ? 'The workout took' : 'Workout time'} ${t}`);
    } else put(s, clock, 'hidden', true);
    if (undo && undo.until <= Cali.now()) hideUndo();
    if (a.readOnly) return;
    const rest = at(root, '.workout-score .rest');
    const t = Cali.timers.get('rest');
    let kind, big, on = false, width = 0, of = '';
    if (t && t.duration && t.data && t.data.week === a.week && t.data.dayId === a.dayId) {   // this day's rest only
      kind = t.data && t.data.rest;
      on = true;
      big = hms(Math.ceil(t.remaining / 1000));
      of = `of ${hms(Math.round(t.duration / 1000))}`;
      width = Math.max(0, Math.min(100, Math.round(1000 * t.remaining / t.duration) / 10));   // drains: 1:12 of 1:30 = 80 % (screen 1)
    } else {
      kind = restAfter(s, day);
      big = kind ? hms(restSeconds(kind)) : '–';
    }
    const lab = kind === 'pair' ? 'Pair rest' : 'Rest';
    put(s, rest, 'class', `rest${on ? ' on' : ''}`);
    put(s, at(rest, '[data-lab="rest"]'), 'text', lab);
    put(s, at(rest, '[data-lab="of"]'), 'text', of);
    put(s, at(rest, '[data-big="rest"]'), 'text', big);
    put(s, rest, 'aria-label', on ? `${lab}, ${big} left ${of}` : kind ? `${lab} after this set: ${big}` : 'No rest after this set');
    put(s, at(root, '.workout-bug .bar i'), 'width', `${width}%`);
  }

  // ── the exercise editor, inside its card ──────────────────────────
  // A tap on an exercise's name opens its editor under the row (one at a time; it stays open across a redraw): load,
  // target, sets, the rep range, the load step and the name. A change is written to this week's copy and to the
  // program (the week's and the next one), so it holds for the weeks after; earlier weeks keep their own copy. Sets
  // never drop below the last logged one, so no logged set is lost.
  const LOAD_STEPS = [1, 1.25, 2.5, 5];
  let editing = null;   // { week, dayId, exId } of the open editor
  const r2 = v => Math.round(v * 100) / 100;
  const loadStepOf = ex => (ex.loadStep > 0 ? ex.loadStep : Cali.settings.get('loadStep'));

  // each stepper: its label, the value shown, the step, and its bounds for this exercise
  function fields(ex) {
    const time = ex.kind === 'time';
    const lastLogged = ex.sets.reduce((k, x, i) => (x !== null ? i + 1 : k), 0);
    const out = [
      { k: 'load', label: ex.bodyweight ? 'Added load' : 'Load', show: `${r2(ex.load)} kg`, step: loadStepOf(ex), min: 0, max: 500 },
      { k: 'target', label: time ? 'Target hold' : 'Target reps', show: time ? `${ex.target} s` : String(ex.target), step: time ? 5 : 1, min: time ? 5 : 1, max: time ? 600 : 100 },
      { k: 'sets', label: 'Sets', show: String(ex.sets.length), step: 1, min: Math.max(1, lastLogged), max: 10 },
    ];
    if (ex.kind === 'reps') {
      out.push({ k: 'repMin', label: 'Range low', show: String(ex.repMin), step: 1, min: 1, max: ex.repMax });
      out.push({ k: 'repMax', label: 'Range high', show: String(ex.repMax), step: 1, min: ex.repMin, max: 100 });
    }
    return out;
  }
  const valueOf = (ex, k) => (k === 'sets' ? ex.sets.length : ex[k]);

  function editorHtml(ex) {
    const steps = LOAD_STEPS.includes(ex.loadStep) || !(ex.loadStep > 0) ? LOAD_STEPS : [...LOAD_STEPS, ex.loadStep].sort((p, q) => p - q);
    return '<div class="workout-ed-grid">' + fields(ex).map(f =>
      `<div class="workout-ed-f" role="group" aria-labelledby="workout-ed-l-${esc(ex.id)}-${f.k}">` +
        `<span class="workout-ed-l" id="workout-ed-l-${esc(ex.id)}-${f.k}">${f.label}</span><div class="workout-ed-step">` +
        `<button type="button" data-ed-k="${f.k}" data-ed-d="-1" aria-label="${f.label} down"><span>−</span></button>` +
        `<span class="num" data-ed-v="${f.k}" aria-live="polite"></span>` +
        `<button type="button" data-ed-k="${f.k}" data-ed-d="1" aria-label="${f.label} up"><span>+</span></button></div></div>`).join('') +
      '</div>' +
      '<div class="workout-ed-f workout-ed-wide"><span class="workout-ed-l">Load step, kg</span>' +
        `<div class="workout-ed-seg" role="group" aria-label="Load step in kg">${steps.map(v =>
          `<button type="button" data-ed-step="${v}" aria-pressed="false">${v}</button>`).join('')}</div></div>` +
      `<label class="workout-ed-f workout-ed-wide"><span class="workout-ed-l">Name</span>` +
        `<input type="text" class="workout-ed-name" maxlength="80" autocomplete="off" value="${esc(ex.name)}"></label>` +
      '<div class="workout-ed-foot"><span>This week and the weeks after</span>' +
        '<button type="button" class="btn secondary" data-act="ed-done">Done</button></div>';
  }

  function patchEditor(s) {
    const { a, root } = s;
    for (const box of root.querySelectorAll('[data-ed]')) {
      const id = box.dataset.ed;
      const open = Boolean(editing && editing.week === a.week && editing.dayId === a.dayId && editing.exId === id);
      const btn = at(root, `[data-edit="${CSS.escape(id)}"]`);
      put(s, btn, 'aria-expanded', String(open));
      put(s, box, 'hidden', !open);
      if (!open) { if (box.firstChild) { box.innerHTML = ''; s.cache.delete(box); } continue; }
      const ex = s.list.find(e => e.id === id);
      if (!ex) continue;
      if (!box.firstChild) box.innerHTML = editorHtml(ex);
      for (const f of fields(ex)) {
        put(s, at(box, `[data-ed-v="${f.k}"]`), 'text', f.show);
        const v = valueOf(ex, f.k);
        put(s, at(box, `[data-ed-k="${f.k}"][data-ed-d="-1"]`), 'disabled', v - f.step < f.min - 1e-9 ? '' : null);
        put(s, at(box, `[data-ed-k="${f.k}"][data-ed-d="1"]`), 'disabled', v + f.step > f.max + 1e-9 ? '' : null);
      }
      for (const b of box.querySelectorAll('[data-ed-step]')) put(s, b, 'aria-pressed', String(Number(b.dataset.edStep) === ex.loadStep));
      const name = at(box, '.workout-ed-name');
      if (name && document.activeElement !== name && name.value !== ex.name) name.value = ex.name;
    }
  }

  function editExercise(a, exId, key, value) {
    try {
      Cali.change(d => {
        const w = d.weeks.find(x => x.n === a.week);
        const ex = w.days[a.dayId].exercises[exId];
        if (key === 'sets') {
          while (ex.sets.length < value) ex.sets.push(null);
          while (ex.sets.length > value && ex.sets[ex.sets.length - 1] === null) ex.sets.pop();
        } else ex[key] = value;
        for (const p of d.programs) {
          if (p.id !== w.program && p.id !== d.nextProgram) continue;
          const day = p.days.find(x => x.id === a.dayId);
          const pe = day && day.exercises.find(e => e.id === exId);
          if (pe) pe[key] = key === 'sets' ? ex.sets.length : value;
        }
      }, { why: 'editExercise', detail: { week: a.week, dayId: a.dayId, exId, key, value } });
    } catch (e) { console.warn('Cali: the exercise was not changed', e); }
  }

  function stepField(a, exId, k, dir) {
    const ex = Cali.weekExercise(a.week, a.dayId, exId);
    const f = ex && fields(ex).find(x => x.k === k);
    if (!f) return;
    const v = r2(valueOf(ex, k) + dir * f.step);
    if (v < f.min - 1e-9 || v > f.max + 1e-9) return;
    editExercise(a, exId, k, k === 'load' ? Math.max(0, v) : v);
  }

  function toggleEditor(a, exId) {
    const open = editing && editing.week === a.week && editing.dayId === a.dayId && editing.exId === exId;
    editing = open ? null : { week: a.week, dayId: a.dayId, exId };
    if (!screen) return;
    patch(screen);
    const box = editing && at(screen.root, `[data-ed="${CSS.escape(exId)}"]`);
    if (box && box.scrollIntoView) box.scrollIntoView({ block: 'nearest' });
  }

  // ── gestures ──────────────────────────────────────────────────────
  let lastDown = -Infinity;
  // a tap or hold on a set; returns the countdown (seconds) to open when it marked a timed tile done, else 0
  function act(kind, key) {
    const [dayId, exId, i] = key.split(':');
    let set;
    try { set = Cali[kind](dayId, exId, Number(i)); } catch (e) { console.warn('Cali: the set was not saved', e); return 0; }
    const ex = Cali.weekExercise(null, dayId, exId);
    return ex && ex.kind === 'check' && set && ex.duration ? ex.duration : 0;
  }
  const countdown = seconds => { if (seconds) Cali.go('timer', { countdown: seconds }); };

  function wire(root) {
    let press = null;   // { key, x, y, timer, held, open: the countdown a hold earned, opened when the finger lifts }
    const drop = () => { if (press) clearTimeout(press.timer); press = null; };
    root.addEventListener('pointerdown', e => {
      if (!e.isPrimary || e.button > 0) return;
      const el = e.target.closest('[data-set]');
      if (!el) return;
      drop();
      const t = Cali.now();
      if (t - lastDown < BOUNCE_MS) return;          // the finger bounced: the touch before already counted
      lastDown = t;
      const p = { key: el.dataset.set, x: e.clientX, y: e.clientY, held: false, timer: 0, open: 0 };
      p.timer = setTimeout(() => { if (press === p) { p.held = true; p.open = act('hold', p.key); } }, HOLD_MS);
      press = p;
    });
    root.addEventListener('pointermove', e => {   // a finger moving after the hold counted is still that hold
      if (press && !press.held && e.isPrimary && Math.hypot(e.clientX - press.x, e.clientY - press.y) > SLOP_PX) drop();
    });
    root.addEventListener('pointerup', e => {
      if (!press || !e.isPrimary) return;
      const p = press;
      drop();
      countdown(p.held ? p.open : act('tap', p.key));
    });
    root.addEventListener('pointercancel', e => {
      const p = press;
      if (!p || !e.isPrimary) return;
      drop();
      countdown(p.held ? p.open : 0);
    });
    root.addEventListener('contextmenu', e => { if (e.target.closest('.workout-list, .workout-sheet')) e.preventDefault(); });
    root.addEventListener('selectstart', e => { if (e.target.closest && e.target.closest('.workout-list')) e.preventDefault(); });
    root.addEventListener('click', e => {
      const cell = e.target.closest('[data-set]');
      if (cell) { if (e.detail === 0) countdown(act('tap', cell.dataset.set)); return; }   // Enter or Space on a focused cell
      const day = e.target.closest('[data-day]');
      if (day) {
        const a = screen.a;
        Cali.go('day', { week: a.week, dayId: day.dataset.day, ...(a.readOnly ? { readOnly: true } : {}) }, { replace: true });
        return;
      }
      if (!screen) return;
      const a = screen.a;
      const ed = e.target.closest('[data-edit]');
      if (ed) { toggleEditor(a, ed.dataset.edit); return; }
      const box = e.target.closest('[data-ed]');
      const stepBtn = e.target.closest('[data-ed-k]');
      if (box && stepBtn) { if (!stepBtn.disabled) stepField(a, box.dataset.ed, stepBtn.dataset.edK, Number(stepBtn.dataset.edD)); return; }
      const loadStep = e.target.closest('[data-ed-step]');
      if (box && loadStep) { editExercise(a, box.dataset.ed, 'loadStep', Number(loadStep.dataset.edStep)); return; }
      const btn = e.target.closest('[data-act]');
      if (btn && btn.dataset.act === 'undo') doUndo();
      else if (btn && btn.dataset.act === 'session') session(a);
      else if (btn && btn.dataset.act === 'ed-done') { const n = root.querySelector('.workout-ed-name'); if (n) n.blur(); toggleEditor(a, box.dataset.ed); }
    });
    root.addEventListener('change', e => {   // the name, saved when it is left or Enter is pressed
      const input = e.target.closest('.workout-ed-name');
      const box = input && input.closest('[data-ed]');
      if (!box || !screen) return;
      const name = input.value.trim();
      if (name && name !== Cali.weekExercise(screen.a.week, screen.a.dayId, box.dataset.ed).name) editExercise(screen.a, box.dataset.ed, 'name', name);
      else input.value = Cali.weekExercise(screen.a.week, screen.a.dayId, box.dataset.ed).name;
    });
    root.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('workout-ed-name')) e.target.blur(); });
  }

  function session(a) {
    const day = dayOf(a.week, a.dayId);
    if (!day) return;
    if (day.finishedAt) { Cali.go('summary', { week: a.week, dayId: a.dayId }); return; }
    if (a.readOnly) return;
    if (!day.startedAt) { startDay(a.week, a.dayId); return; }
    finishDay(a.week, a.dayId);
    Cali.go('summary', { week: a.week, dayId: a.dayId });
  }

  // ── the route ─────────────────────────────────────────────────────
  function show(root, args) {
    const a = Cali.dayArgs(args);
    const w = Cali.week(a.week);
    const list = Cali.dayExercises(a.week, a.dayId);
    const key = JSON.stringify([a, w.program, Object.keys(w.days),
      list.map(e => [e.id, e.name, e.kind, e.sets.length, e.pair || '', e.duration || 0])]);
    if (!screen || screen.root !== root || screen.key !== key) {
      const ticker = screen && screen.root === root ? screen.ticker : 0;
      screen = { root, args, a, key, list, now: null, cache: new Map(), ticker };
      build(screen);
    }
    screen.args = args;
    patch(screen);
  }

  Cali.route('day', {
    render(root, args) {
      if (screen) clearInterval(screen.ticker);
      screen = null;
      show(root, args);
      wire(root);
      screen.ticker = setInterval(() => { if (screen) tick(screen); }, TICK_MS);
      syncWake();
    },
    update(root, args) { show(root, args); },
    leave() { if (screen) clearInterval(screen.ticker); screen = null; },
  });
})();
