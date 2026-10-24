/* The day screen, thin version (Task-00; Task-01 replaces this file and adds app/workout.css): the round-6 day
   sheet (design/r6/screens.html, screen 7) without polish. Route 'day' { week, dayId, readOnly }.
   A tap on a set cell logs through Cali.tap, a hold (500 ms) through Cali.hold; the cell under the finger is found
   by its data-set="<dayId>:<exId>:<i>". It renders both slot holders: 'dayheader' (its fallback is the week label)
   and 'topbar'. No session clock, Finish, rest timer or Undo here (Task-01). */
(() => {
  'use strict';
  const HOLD_MS = 500;
  const style = document.createElement('style');
  style.textContent = `
.workout-days { flex: none; margin: 2px var(--margin) 0; height: 44px; display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
  border: 1px solid var(--outline); border-radius: 22px; overflow: hidden; }
.workout-days button { min-width: 0; padding: 0 6px; font-size: 0.875rem; font-weight: 600; color: var(--ink-muted);
  border-left: 1px solid var(--outline); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.workout-days button:first-child { border-left: 0; }
.workout-days button[aria-pressed="true"] { background: var(--tonal); color: var(--ink); font-weight: 700; }
.workout-list { flex: 1; padding: 0 var(--margin) 8px; display: flex; flex-direction: column; gap: 4px; }
.workout-row { min-height: 46px; display: grid; align-items: center; column-gap: 4px; padding: 0 3px 0 10px;
  grid-template-columns: minmax(0, 1fr) 40px calc(3 * var(--cell-w) + 2 * var(--cell-gap)); }
.workout-row + .workout-row { border-top: 1px solid var(--divider); }
.workout-cols { min-height: 16px; margin: 4px 0 -3px; font-size: 0.75rem; font-weight: 600; color: var(--ink-subtle); line-height: 14px; }
.workout-cols span:nth-child(2) { text-align: center; white-space: nowrap; }
.workout-cols span:nth-child(3) { padding-left: 2px; }
.workout-card { padding: 1px 0; }
.workout-name { font-size: 0.90625rem; font-weight: 700; line-height: 19px; letter-spacing: -0.1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.workout-meta { display: flex; gap: 6px; margin-top: 1px; font-size: 0.75rem; line-height: 16px; color: var(--ink-muted); font-weight: 500; white-space: nowrap; }
.workout-meta b { color: var(--ink); font-weight: 700; }
.workout-last { font-size: 0.75rem; line-height: 14px; color: var(--ink-subtle); font-weight: 600; text-align: center; white-space: nowrap; overflow: hidden; }
.workout-cells { display: grid; grid-template-columns: repeat(3, var(--cell-w)); gap: var(--cell-gap); justify-content: end; }
.workout-timed { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 3px 3px 2px 10px; border-top: 1px solid var(--divider); }
.workout-tile { height: 44px; width: 100%; border-radius: var(--radius-cell); box-shadow: inset 0 0 0 1.5px var(--todo-line); display: flex;
  flex-direction: column; justify-content: center; padding: 0 10px; text-align: left; min-width: 0; user-select: none;
  -webkit-user-select: none; -webkit-touch-callout: none; touch-action: manipulation; }
.workout-tile.hit { background: var(--hit-bg); box-shadow: none; }
.workout-tile.now { box-shadow: inset 0 0 0 3px var(--now-ring); }
.workout-tile .lbl { font-size: 0.75rem; color: var(--ink-muted); font-weight: 600; line-height: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.workout-tile .val { font-size: 1rem; line-height: 20px; white-space: nowrap; }
.workout-tile.hit .val { color: var(--hit-ink); }
.workout-sheet { position: sticky; bottom: 0; flex: none; background: var(--sheet); border-top: 1px solid var(--sheet-line);
  box-shadow: var(--sheet-shadow); border-radius: 24px 24px 0 0; padding: 7px var(--margin) calc(8px + env(safe-area-inset-bottom)); }
.workout-bug-head { height: 30px; display: flex; align-items: center; gap: 8px; padding: 0 14px; }
.workout-bug-name { font-size: 1.0625rem; font-weight: 800; letter-spacing: -0.3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.workout-bug-meta { margin-left: auto; display: flex; gap: 8px; font-size: 0.8125rem; font-weight: 700; color: var(--on-anchor-muted); white-space: nowrap; }
.workout-score { display: grid; grid-template-columns: .92fr .8fr 1.38fr; }
.workout-score > div { padding: 0 14px 8px; display: flex; flex-direction: column; min-width: 0; }
.workout-score > div + div { border-left: 2px solid var(--anchor-rule); }
.workout-score .lab { font-size: 0.75rem; font-weight: 700; color: var(--on-anchor-muted); line-height: 14px; white-space: nowrap; }
.workout-score .big { font-family: var(--font-num); font-stretch: var(--num-stretch-big); font-weight: 800; font-size: 2.5rem; line-height: 1;
  letter-spacing: -0.03em; font-variant-numeric: tabular-nums; margin-top: 4px; white-space: nowrap; }
.workout-score .big small { font-size: 1.375rem; font-weight: 700; color: var(--on-anchor-muted); letter-spacing: 0; }
.workout-score .rest .big { color: var(--on-anchor-muted); }
.workout-legend { margin: calc(var(--slab-y) + 8px) 0 2px; text-align: center; font-size: 0.8125rem; color: var(--ink-muted); }
.workout-legend b { color: var(--ink); font-weight: 700; }
.workout-legend span { margin: 0 7px; opacity: .6; }
.workout-done { margin: 6px 4px 2px; text-align: center; font-size: 0.875rem; font-weight: 700; }
`;
  document.head.appendChild(style);

  const esc = Cali.esc;
  const TIMER_ICON = '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/><circle cx="12" cy="14" r="8"/></svg>';
  const unit = ex => (ex.kind === 'time' ? '<small>s</small>' : '');
  const range = ex => (ex.kind === 'reps' ? `${ex.repMin}–${ex.repMax}` : ex.kind === 'time' ? 'hold' : '');
  const minutes = s => (s % 60 ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` : `${s / 60} min`);

  function cell(a, ex, i, now) {
    const s = ex.sets[i];
    const key = `${a.dayId}:${ex.id}:${i}`;
    const name = `${ex.name}, set ${i + 1}: `;
    const attrs = a.readOnly ? 'aria-disabled="true"' : `data-set="${esc(key)}"`;
    if (s === null) {
      const cls = now ? 'now' : 'todo';
      return `<button type="button" class="cell ${cls}" ${attrs} ${now ? 'aria-current="step" ' : ''}aria-label="${esc(name)}target ${ex.target}"><span>${ex.target}${unit(ex)}</span></button>`;
    }
    if (s.r >= ex.target) return `<button type="button" class="cell hit" ${attrs} aria-label="${esc(name)}${s.r}, hit"><span>${s.r}${unit(ex)}</span></button>`;
    const p = ex.target > 0 ? Math.round(100 * s.r / ex.target) : 0;
    return `<button type="button" class="cell short" style="--p:${p}%" ${attrs} aria-label="${esc(name)}${s.r} of ${ex.target}, short"><span>${s.r}<small>/${ex.target}</small></span></button>`;
  }

  function tile(a, ex, now) {
    const s = ex.sets[0];
    const key = `${a.dayId}:${ex.id}:0`;
    const attrs = a.readOnly ? 'aria-disabled="true"' : `data-set="${esc(key)}"`;
    const cls = s ? 'hit' : now ? 'now' : '';
    const val = ex.duration ? minutes(ex.duration) : 'Done';
    return `<button type="button" class="workout-tile ${cls}" ${attrs} aria-label="${esc(ex.name)}: ${s ? 'done' : 'to do'}">` +
      `<span class="lbl">${esc(ex.name)}</span><span class="val num">${s ? 'Done' : val}</span></button>`;
  }

  function row(a, ex, now) {
    const last = Cali.history(a.dayId, ex.id, a.week)[0];
    const lastText = last ? last.sets.map(s => (s ? s.r : '–')).join(' ') : '–';
    const cells = ex.sets.map((_, i) => cell(a, ex, i, now && now.exId === ex.id && now.i === i));
    while (cells.length % 3) cells.push('<span class="cell void" aria-hidden="true"></span>');
    return `<div class="workout-row" data-ex="${esc(ex.id)}">` +
      `<div><div class="workout-name">${esc(ex.name)}</div><div class="workout-meta"><b>${esc(Cali.loadLabel(ex.load, ex.bodyweight))}</b><span>${range(ex)}</span></div></div>` +
      `<span class="workout-last" aria-label="Last week ${esc(lastText)}">${esc(lastText)}</span>` +
      `<div class="workout-cells">${cells.join('')}</div></div>`;
  }

  // the day's exercises as cards: a pair (adjacent, same pair) shares one card; one-off rows sit as tiles at the end
  function cards(a, list, now) {
    const groups = [];
    const tiles = list.filter(ex => ex.kind === 'check');
    const rows = list.filter(ex => ex.kind !== 'check');
    for (const ex of rows) {
      const g = groups[groups.length - 1];
      if (g && ex.pair && g[g.length - 1].pair === ex.pair) g.push(ex); else groups.push([ex]);
    }
    const html = groups.map((g, gi) => `<div class="card workout-card">${g.map(ex => row(a, ex, now)).join('')}` +
      (gi === groups.length - 1 && tiles.length ? `<div class="workout-timed">${tiles.map(ex => tile(a, ex, now && now.exId === ex.id)).join('')}</div>` : '') +
      '</div>');
    if (!groups.length && tiles.length) html.push(`<div class="card workout-card"><div class="workout-timed">${tiles.map(ex => tile(a, ex, now && now.exId === ex.id)).join('')}</div></div>`);
    return html.join('');
  }

  function sheet(a, list, now) {
    if (!now) return `<section class="workout-sheet" aria-label="Current set"><p class="workout-done">Every set of this day is logged.</p></section>`;
    const ex = list.find(e => e.id === now.exId);
    const reps = ex.kind === 'time' ? `${ex.target}<small>s</small>` : ex.kind === 'check' ? '✓' : String(ex.target);
    const rest = Cali.settings.get(ex.pair ? 'restPair' : 'restExercise');   // the length only; the timer is Task-01's
    return `<section class="workout-sheet" aria-label="Current set">` +
      `<div class="anchor" role="group" aria-label="Current set">` +
      `<div class="workout-bug-head"><span class="workout-bug-name">${esc(ex.name)}</span>` +
      `<span class="workout-bug-meta"><span>${esc(Cali.loadLabel(ex.load, ex.bodyweight))}</span><span>${range(ex)}</span></span></div>` +
      `<div class="workout-score"><div><span class="lab">Set</span><span class="big">${now.i + 1}<small>/${ex.sets.length}</small></span></div>` +
      `<div><span class="lab">Reps</span><span class="big">${reps}</span></div>` +
      `<div class="rest"><span class="lab">${ex.pair ? 'Pair rest' : 'Rest'}</span><span class="big">${Math.floor(rest / 60)}:${String(rest % 60).padStart(2, '0')}</span></div></div></div>` +
      `<p class="workout-legend"><b>Tap</b> done<span>·</span><b>again</b> −1<span>·</span><b>hold</b> +1</p></section>`;
  }

  function draw(root, args) {
    const a = Cali.dayArgs(args);
    const w = Cali.week(a.week);
    const days = (Cali.program(w.program) || { days: [] }).days.filter(d => w.days[d.id]);
    const list = Cali.dayExercises(a.week, a.dayId);
    const now = a.readOnly ? null : Cali.nextSet(a.dayId, a.week);
    root.innerHTML =
      `<header class="appbar"><span data-slot="dayheader"><span class="week" data-fallback>Week ${w.n}</span></span>` +
      '<span data-slot="topbar"></span></header>' +
      `<nav class="workout-days" aria-label="Day">${days.map(d => `<button type="button" data-day="${esc(d.id)}" aria-pressed="${d.id === a.dayId}">${esc(d.name)}</button>`).join('')}</nav>` +
      `<section class="workout-list" aria-label="Exercises"><div class="workout-row workout-cols" aria-hidden="true"><span></span><span>Last wk</span><span>This week</span></div>` +
      cards(a, list, now) + '</section>' +
      (a.readOnly ? '' : sheet(a, list, now));
  }

  // tap = a click on a set cell; hold = the finger kept down HOLD_MS (its click is then swallowed)
  let press = null;   // { key, timer, held }
  function act(kind, key) {
    const [dayId, exId, i] = key.split(':');
    Cali[kind](dayId, exId, Number(i));
  }
  function wire(root) {
    root.addEventListener('pointerdown', e => {
      const el = e.target.closest('[data-set]');
      if (press) clearTimeout(press.timer);
      press = null;
      if (!el) return;
      const p = { key: el.dataset.set, held: false, timer: 0 };
      p.timer = setTimeout(() => { p.held = true; act('hold', p.key); }, HOLD_MS);
      press = p;
    });
    const release = () => { if (press) clearTimeout(press.timer); };
    root.addEventListener('pointerup', release);
    root.addEventListener('pointercancel', () => { release(); press = null; });
    root.addEventListener('contextmenu', e => { if (e.target.closest('[data-set]')) e.preventDefault(); });
    root.addEventListener('click', e => {
      const day = e.target.closest('[data-day]');
      if (day) { Cali.go('day', { week: Cali.dayArgs(Cali.current().args).week, dayId: day.dataset.day }, { replace: true }); return; }
      const el = e.target.closest('[data-set]');
      const held = press && press.held;
      press = null;
      if (!el || held) return;
      act('tap', el.dataset.set);
    });
  }

  Cali.route('day', {
    render(root, args) { wire(root); draw(root, args); },
    update(root, args) { draw(root, args); },
  });
})();
