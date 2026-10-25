/* Weeks (app/week.js, Task-04): the week menu, Finish week and its Undo. Styles in app/week.css (prefix week-).
   Blueprint -> Rules -> Finish week; the rules themselves are Cali.progress (app/progress.js).

   Week menu: a "Week N" button with a chevron in the day screen's 'dayheader' slot (it names the week on screen; a
   past week also shows a "Past" pill). It opens a menu of every week, newest first, each with its dates and days
   done: the current week opens Cali.go('day', { week, dayId }), a past one Cali.go('day', { week, dayId,
   readOnly: true }) (the day shown stays when that week has it). Under the list: "Finish week N", and "Undo finish
   week N-1" while that can be undone. A transparent scrim under the menu takes the tap that closes it, so closing
   never logs a set.

   Finish week (route 'finish-week' { week }): the confirmation. It shows week N's days done, sets and short sets,
   and per day what next week gets from Cali.progress (load up, load down, one rep more, unchanged; a day not done
   carries over unchanged), then Cancel or "Finish week N". Finishing, in one Cali.change (why 'weekFinished'):
   week N gets finishedAt; week N+1 is Cali.weekFrom(nextProgram, N + 1) with each exercise's load and target set
   from Cali.progress(weekExercise + dayDone, history) when the exercise is in both weeks with the same kind (else the
   program's values stay); activeProgram becomes nextProgram. Then 'weekFinished' { week: N, next: N + 1 } is
   emitted, the screen before the confirmation is replaced by week N+1's day, and a snackbar offers Undo for 8 s.
   A second tap, or a confirmation left open for a week that is no longer current, finishes nothing.

   Undo (snackbar or menu) works until the next 'log' event: it drops week N+1 (it has no logged set) and reopens
   week N (finishedAt removed, activeProgram back to week N's program), why 'weekUndone' { week, next }. The window
   is kept in Blueprint -> Data's own week fields, so the synced document carries nothing more and a reload or a
   killed app keeps it right: Finish starts week N+1 at the instant week N finished (its startedAt = week N's
   finishedAt), and the first 'log' event after it moves week N+1's startedAt to that log's time (why
   'undoFinishEnded'), even when that set is cleared again; a week built by Finish so starts at its first set. Undo is
   offered while the current week still starts where the one before it finished and has no logged set. A week
   finished with no set logged keeps its start too, so undoing the later Finish leaves its own Finish undoable, as no
   log came between. */
(() => {
  'use strict';
  const esc = Cali.esc;
  const SNACK_MS = 8000;
  const svg = paths => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${paths}</svg>`;
  const ICON = {
    chevron: svg('<path d="m6 9 6 6 6-6"/>'),
    check: svg('<path d="M20 6 9 17l-5-5"/>'),
    flag: svg('<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>'),
    undo: svg('<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"/>'),
    x: svg('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
  };

  // ── reading weeks ─────────────────────────────────────────────────
  const logged = ex => ex.sets.some(s => s !== null);
  const hasLog = w => Object.values(w.days).some(d => Object.values(d.exercises).some(logged));
  function dayIds(w) {
    const p = Cali.program(w.program);
    const ids = p ? p.days.map(d => d.id).filter(id => w.days[id]) : [];
    for (const id of Object.keys(w.days)) if (!ids.includes(id)) ids.push(id);
    return ids;
  }
  function dayName(w, dayId) {
    const p = Cali.program(w.program);
    const d = p && p.days.find(x => x.id === dayId);
    return d ? d.name : dayId;
  }
  const daysDone = w => Object.values(w.days).filter(d => d.finishedAt).length;

  const fmt = (o) => new Intl.DateTimeFormat('en-GB', o);
  const dayMonth = ms => fmt({ day: 'numeric', month: 'short' }).format(ms);
  const longDate = ms => fmt({ day: 'numeric', month: 'long' }).format(ms);
  function span(from, to) {
    const a = new Date(from), b = new Date(to);
    if (a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth()) {
      return a.getDate() === b.getDate() ? dayMonth(a) : `${a.getDate()}–${dayMonth(b)}`;
    }
    return `${dayMonth(a)} – ${dayMonth(b)}`;
  }

  // what week n's end gives next week, per day: [{ dayId, name, done, started, rows: [{ ex, next }] }]
  function plan(n) {
    const w = Cali.week(n);
    return dayIds(w).map(dayId => {
      const day = w.days[dayId];
      const done = Boolean(day.finishedAt);
      const rows = Cali.dayExercises(w.n, dayId).map(ex => ({
        ex, next: Cali.progress({ ...ex, dayDone: done }, Cali.history(dayId, ex.id, w.n)),
      }));
      return { dayId, name: dayName(w, dayId), done, started: Boolean(day.startedAt) || Object.values(day.exercises).some(logged), rows };
    });
  }

  // ── finish and undo ───────────────────────────────────────────────
  function finish(n) {
    const cur = Cali.week();
    if (cur.n !== n) return false;
    const values = new Map();
    for (const d of plan(n)) for (const { ex, next } of d.rows) values.set(`${d.dayId}:${ex.id}`, { kind: ex.kind, load: next.load, target: next.target });
    Cali.change(draft => {
      const program = draft.programs.find(p => p.id === draft.nextProgram);
      const built = Cali.weekFrom(program, n + 1);
      for (const [dayId, day] of Object.entries(built.days)) {
        for (const [exId, e] of Object.entries(day.exercises)) {
          const v = values.get(`${dayId}:${exId}`);
          if (v && v.kind === e.kind) { e.load = v.load; e.target = v.target; }
        }
      }
      const at = Cali.iso();
      built.startedAt = at;
      draft.weeks[draft.weeks.length - 1].finishedAt = at;
      draft.weeks.push(built);
      draft.activeProgram = draft.nextProgram;
    }, { why: 'weekFinished', detail: { week: n, next: n + 1 } });
    Cali.emit('weekFinished', { week: n, next: n + 1 });
    return true;
  }

  // the last Finish while no log came after it: the current week still starts where the week before it finished
  function lastFinish() {
    const weeks = Cali.doc().weeks;
    const cur = weeks[weeks.length - 1], prev = weeks[weeks.length - 2];
    return prev && prev.finishedAt && cur.startedAt === prev.finishedAt ? { cur, prev } : null;
  }
  function undoable() {
    const f = lastFinish();
    return f && !hasLog(f.cur) ? { week: f.prev.n, next: f.cur.n } : null;
  }

  function undo() {
    const u = undoable();
    if (!u) return false;
    Cali.change(d => {
      d.weeks.pop();
      const prev = d.weeks[d.weeks.length - 1];
      delete prev.finishedAt;
      d.activeProgram = prev.program;
    }, { why: 'weekUndone', detail: u });
    hideSnack();
    const c = Cali.current();
    if (c && c.name === 'day') {
      const dayId = c.args.dayId;
      Cali.go('day', Cali.week().days[dayId] ? { week: u.week, dayId } : { week: u.week }, { replace: true });
    }
    snack(`Week ${u.next} removed. Week ${u.week} is open again.`, false);
    return true;
  }

  Cali.on('log', () => {
    hideSnack();
    const f = lastFinish();
    // never the instant of Finish itself, which would leave the window open
    if (f) Cali.change(d => { d.weeks[d.weeks.length - 1].startedAt = Cali.iso(Math.max(Cali.now(), Date.parse(f.prev.finishedAt) + 1)); }, { why: 'undoFinishEnded' });
  });

  // ── snackbar ──────────────────────────────────────────────────────
  let snackEl = null, snackTimer = 0, snackHash = '';
  function hideSnack() {
    clearTimeout(snackTimer);
    if (snackEl) { snackEl.remove(); snackEl = null; }
  }
  function snack(text, withUndo) {
    hideSnack();
    snackHash = location.hash;            // it belongs to this screen: another screen's buttons are never under it
    snackEl = document.createElement('div');
    snackEl.className = 'snack week-snack';
    snackEl.setAttribute('role', 'status');
    snackEl.innerHTML = `<span>${esc(text)}</span>${withUndo ? '<button type="button" data-week-undo>Undo</button>' : ''}`;
    snackEl.addEventListener('click', e => { if (e.target.closest('[data-week-undo]')) undo(); });
    document.body.appendChild(snackEl);
    snackTimer = setTimeout(hideSnack, withUndo ? SNACK_MS : SNACK_MS / 2);
  }

  // after Finish: the screen before the confirmation becomes week N+1's day
  let landing = null;
  Cali.on('route', () => {
    if (!landing) return;
    const l = landing;
    landing = null;
    Cali.go('day', { week: l.next }, { replace: true });
    snack(`Week ${l.week} finished. Week ${l.next} started.`, true);
  });

  // ── the week menu (dayheader slot) ────────────────────────────────
  const head = document.createElement('span');
  head.className = 'week-head';
  head.innerHTML = `<button type="button" class="week-btn" aria-haspopup="menu" aria-expanded="false" data-week-menu>` +
    `<span class="week-btn-n"></span>${ICON.chevron}</button><span class="pill week-past" hidden>Past</span>`;
  const btn = head.querySelector('.week-btn');
  const label = head.querySelector('.week-btn-n');
  const pastPill = head.querySelector('.week-past');

  function viewed() {
    const c = Cali.current();
    return Cali.dayArgs(c && c.name === 'day' ? c.args : {});
  }
  function paint() {
    const a = viewed();
    const past = a.week !== Cali.week().n;
    label.innerHTML = `<span class="week-word">Week </span>${a.week}`;   // 'W2' while the session clock needs the room (week.css)
    pastPill.hidden = !past;
    btn.setAttribute('aria-label', `Week ${a.week}${past ? ', a past week' : ''}. Open the week menu`);
  }

  let menu = null;
  function closeMenu(focus) {
    if (!menu) return;
    menu.scrim.remove();
    menu.box.remove();
    menu = null;
    btn.setAttribute('aria-expanded', 'false');
    if (focus) btn.focus();
  }

  function weekItem(w, cur, shown) {
    const end = w.finishedAt || (w === cur ? null : w.startedAt);
    const when = w === cur ? `Since ${dayMonth(Date.parse(w.startedAt))}` : span(Date.parse(w.startedAt), Date.parse(end));
    const total = Object.keys(w.days).length;
    return `<button type="button" class="week-item" role="menuitemradio" aria-checked="${w.n === shown}" data-week="${w.n}">` +
      `<span class="week-tick">${w.n === shown ? ICON.check : ''}</span>` +
      `<span class="week-item-t">Week ${w.n}<small>${esc(when)}, ${daysDone(w)} of ${total} days</small></span>` +
      (w === cur ? '<span class="pill">This week</span>' : '') + '</button>';
  }

  function openMenu() {
    closeMenu();
    const cur = Cali.week();
    const shown = viewed().week;
    const u = undoable();
    const scrim = document.createElement('div');
    scrim.className = 'week-scrim';
    const box = document.createElement('div');
    box.className = 'week-menu';
    box.setAttribute('role', 'menu');
    box.setAttribute('aria-label', 'Weeks');
    box.innerHTML = `<div class="week-list">${[...Cali.doc().weeks].reverse().map(w => weekItem(w, cur, shown)).join('')}</div>` +
      '<div class="week-acts">' +
      `<button type="button" class="week-item" role="menuitem" data-week-act="finish">${ICON.flag}<span class="week-item-t">Finish week ${cur.n}<small>See what moves up, then confirm</small></span></button>` +
      (u ? `<button type="button" class="week-item" role="menuitem" data-week-act="undo">${ICON.undo}<span class="week-item-t">Undo finish week ${u.week}<small>Until the next set is logged</small></span></button>` : '') +
      '</div>';
    const r = btn.getBoundingClientRect();
    const top = Math.round(r.bottom + 4);
    box.style.top = `${top}px`;
    box.style.left = `${Math.max(8, Math.round(r.left))}px`;
    box.style.maxHeight = `${Math.max(160, innerHeight - top - 12)}px`;
    scrim.addEventListener('click', () => closeMenu(false));
    box.addEventListener('click', e => {
      const item = e.target.closest('.week-item');
      if (!item) return;
      const a = viewed();
      closeMenu(false);
      if (item.dataset.weekAct === 'finish') { Cali.go('finish-week', { week: Cali.week().n }); return; }
      if (item.dataset.weekAct === 'undo') { undo(); return; }
      const n = Number(item.dataset.week);
      const w = Cali.week(n);
      if (!w || n === a.week) return;
      const now = Cali.week().n;
      const args = { week: n };
      if (w.days[a.dayId]) args.dayId = a.dayId;
      if (n !== now) args.readOnly = true;
      Cali.go('day', args, { replace: a.week !== now });
    });
    box.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(true); });
    document.body.append(scrim, box);
    btn.setAttribute('aria-expanded', 'true');
    menu = { scrim, box };
    const first = box.querySelector('[aria-checked="true"]') || box.querySelector('.week-item');
    if (first) first.focus({ preventScroll: true });
  }

  btn.addEventListener('click', () => (menu ? closeMenu(true) : openMenu()));
  Cali.on('route', () => {
    closeMenu(false);
    if (snackEl && location.hash !== snackHash) hideSnack();
    paint();
  });
  Cali.on('change', () => { if (menu) closeMenu(false); paint(); });
  Cali.slot('dayheader', head);
  paint();

  // ── the confirmation: route 'finish-week' { week } ────────────────
  const kg = n => String(Math.round(n * 100) / 100);
  const fromLabel = ex => (ex.bodyweight ? (ex.load > 0 ? `BW +${kg(ex.load)}` : 'BW') : kg(ex.load));
  const toLabel = (ex, load) => (ex.bodyweight ? `+${kg(load)} kg` : `${kg(load)} kg`);
  const names = rows => rows.map(({ ex }) => esc(ex.name)).join(', ');

  function dayBlock(d, nextN) {
    const status = d.done ? 'Done' : d.started ? 'Not done' : 'Not started';
    let body;
    if (!d.done) {
      body = `<p class="week-line">${d.started
        ? `Started but not done, so it carries over to week ${nextN} unchanged. Finish the day first to count it.`
        : `Carries over to week ${nextN} unchanged.`}</p>`;
    } else {
      const by = reason => d.rows.filter(r => r.ex.kind !== 'check' && r.next.reason === reason);
      const moves = d.rows.filter(r => r.ex.kind !== 'check' && (r.next.reason === 'load up' || r.next.reason === 'deload'));
      const up = by('target up'), down = by('deload'), kept = by('no change');
      const same = kept.filter(r => logged(r.ex)), skipped = kept.filter(r => !logged(r.ex));
      body = moves.map(({ ex, next }) => {
        const isDown = next.reason === 'deload';
        const say = `${ex.name}: ${fromLabel(ex)} ${ex.bodyweight ? '' : 'kg '}${isDown ? 'down' : 'up'} to ${toLabel(ex, next.load)}`;
        return `<div class="week-row" aria-label="${esc(say)}"><span class="week-row-n">${esc(ex.name)}</span>` +
          `<span class="week-row-from">${esc(fromLabel(ex))} to</span><span class="tag${isDown ? ' week-tag-down' : ''}">${esc(toLabel(ex, next.load))}</span></div>`;
      }).join('');
      if (up.length) {
        body += `<p class="week-line"><b>One rep more:</b> ${up.map(({ ex }) => esc(ex.name) + (ex.kind === 'time' ? ' +5 s' : '')).join(', ')}</p>`;
      }
      if (down.length) body += `<p class="week-line"><b>Load down</b> after three short weeks at this load: ${names(down)}</p>`;
      if (same.length) body += `<p class="week-line"><b>Same next week,</b> a set was short: ${names(same)}</p>`;
      if (skipped.length) body += `<p class="week-line"><b>Same next week,</b> nothing logged: ${names(skipped)}</p>`;
      if (!body) body = '<p class="week-line">Nothing to move here.</p>';
    }
    return `<div class="week-dayhead"><h3>${esc(d.name)}</h3><span class="${d.done ? '' : 'week-open'}">${status}</span></div>` +
      `<div class="group week-group">${body}</div>`;
  }

  let finishing = false;
  function drawConfirm(root, args) {
    const cur = Cali.week();
    const n = Number.isInteger(args.week) ? args.week : cur.n;
    const bar = `<header class="bar2"><button type="button" class="iconbtn" data-week-act="close" aria-label="Close">${ICON.x}</button></header>`;
    if (n !== cur.n || !Cali.week(n)) {
      root.innerHTML = bar + `<div class="week-scroll"><h2 class="week-title">Week ${n} is not open</h2>` +
        `<p class="week-text">Week ${cur.n} is this week; only it can be finished.</p></div>` +
        '<div class="week-dock week-dock-one"><button type="button" class="btn secondary" data-week-act="close">Back</button></div>';
      return;
    }
    const steps = plan(n);
    let sets = 0, done = 0, short = 0;
    for (const d of steps) {
      for (const { ex } of d.rows) {
        if (ex.kind === 'check') continue;
        sets += ex.sets.length;
        for (const s of ex.sets) if (s) { done += 1; if (s.r < ex.target) short += 1; }
      }
    }
    const w = Cali.week(n);
    const next = Cali.program(Cali.doc().nextProgram);
    const switching = next && next.id !== w.program;
    const daysDoneN = steps.filter(d => d.done).length;
    root.innerHTML = bar +
      '<div class="week-scroll">' +
      `<div class="eyebrow">${esc(longDate(Date.parse(w.startedAt)))} to ${esc(longDate(Cali.now()))}</div>` +
      `<h2 class="week-title">Finish week ${n}?</h2>` +
      `<div class="anchor"><div class="top"><b>Days done</b><span>Week ${n}</span></div>` +
      `<div class="metric week-metric">${daysDoneN}<small>of ${steps.length}</small></div></div>` +
      '<div class="week-tiles">' +
      `<div class="week-tile"><div class="eyebrow">Sets done</div><div class="v">${done}<small> of ${sets}</small></div></div>` +
      `<div class="week-tile"><div class="eyebrow">Short sets</div><div class="v">${short}</div></div></div>` +
      `<div class="eyebrow week-sub">Week ${n + 1}</div>` +
      steps.map(d => dayBlock(d, n + 1)).join('') +
      `<p class="week-foot">Week ${n + 1} is built from ${esc(next ? next.name : 'the next program')}${switching ? ', the program chosen for next week' : ''}. Undo stays possible until you log its first set.</p>` +
      '</div>' +
      '<div class="week-dock"><button type="button" class="btn secondary" data-week-act="close">Cancel</button>' +
      `<button type="button" class="btn primary" data-week-act="confirm" data-week="${n}">Finish week ${n}</button></div>`;
  }

  function onConfirmClick(e) {
    const b = e.target.closest('[data-week-act]');
    if (!b) return;
    if (b.dataset.weekAct === 'close') { Cali.back(); return; }
    if (b.dataset.weekAct !== 'confirm' || finishing) return;
    finishing = true;
    b.disabled = true;
    const n = Number(b.dataset.week);
    try {
      if (!finish(n)) { finishing = false; return; }
    } catch (err) {
      finishing = false;
      b.disabled = false;
      const box = document.createElement('div');
      box.className = 'banner';
      box.setAttribute('role', 'alert');
      box.textContent = `Week ${n} was not finished: ${err.message}`;
      e.currentTarget.querySelector('.week-scroll').prepend(box);
      return;
    }
    landing = { week: n, next: n + 1 };
    finishing = false;
    Cali.back();
  }

  Cali.route('finish-week', {
    render(root, args) {
      root.classList.add('week-confirm');
      root.addEventListener('click', onConfirmClick);
      drawConfirm(root, args);
    },
    update(root, args) { if (!landing && !finishing) drawConfirm(root, args); },
  });
})();
