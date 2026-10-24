/* The day's summary (Task-01): route 'summary' { dayId, week? } (no week: the current one), screen 6 of
   design/r6/screens.html; styles in app/summary.css. The workout's Finish opens it after storing the day's finishedAt.
   It shows the duration (startedAt to finishedAt), sets done of the day's sets, short sets, and what moves next week,
   asked of Cali.progress(Cali.weekExercise(...), Cali.history(...)) for each reps and time row (the only source).
   Resume clears finishedAt and goes back to the day; Done keeps it (storing it first if missing), emits 'dayDone'
   { week, dayId } and goes back; the close button goes back and changes nothing. A past week's day shows no buttons. */
(() => {
  'use strict';
  const esc = Cali.esc;
  const ICONS = {
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    cloud: '<path d="M12 13v8"/><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="m8 17 4-4 4 4"/>',
  };
  const ic = name => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
  const pad = n => String(n).padStart(2, '0');
  const hms = s => (s >= 3600 ? `${Math.floor(s / 3600)}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}` : `${Math.floor(s / 60)}:${pad(s % 60)}`);
  const kg = n => String(Math.round(n * 100) / 100);
  const clockOf = ms => new Date(ms).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  const dateOf = ms => new Date(ms).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });

  function where(args) {
    const a = Cali.dayArgs({ week: args.week, dayId: args.dayId });
    const w = Cali.week(a.week);
    const pday = (Cali.program(w.program) || { days: [] }).days.find(d => d.id === a.dayId);
    return { week: a.week, dayId: a.dayId, current: w === Cali.week(), name: pday ? pday.name : a.dayId, day: w.days[a.dayId] };
  }

  // next week for each reps and time row, as Cali.progress answers it
  function nextWeek(p, list) {
    const up = [], down = [], more = [];
    for (const ex of list) {
      if (ex.kind === 'check') continue;
      let r;
      try { r = Cali.progress(ex, Cali.history(p.dayId, ex.id, p.week)); } catch (e) {
        console.warn(`Cali: no progression for ${ex.name}`, e);
        continue;
      }
      const from = ex.bodyweight ? (ex.load > 0 ? `BW +${kg(ex.load)}` : 'BW') : kg(ex.load);
      const to = ex.bodyweight ? `+${kg(r.load)} kg` : `${kg(r.load)} kg`;
      if (r.load > ex.load) up.push({ ex, from, to });
      else if (r.load < ex.load) down.push({ ex, from, to });
      else if (r.target > ex.target) {
        const d = r.target - ex.target;
        more.push(ex.kind === 'time' ? `${ex.name} +${kg(d)} s` : d === 1 ? ex.name : `${ex.name} +${kg(d)}`);
      }
    }
    return { up, down, more };
  }

  function draw(root, args) {
    const p = where(args);
    const list = Cali.dayExercises(p.week, p.dayId);
    const day = p.day || {};
    const start = day.startedAt ? Date.parse(day.startedAt) : null;
    const end = day.finishedAt ? Date.parse(day.finishedAt) : Cali.now();
    const took = start === null ? null : Math.max(0, Math.floor((end - start) / 1000));
    const rows = list.filter(e => e.kind !== 'check');
    const sets = rows.flatMap(e => e.sets.map((s, i) => ({ e, s, i })));
    const done = sets.filter(o => o.s !== null);
    const short = done.filter(o => o.s.r < o.e.target);
    const next = nextWeek(p, list);

    const lrow = (o, cls) => `<div class="summary-row"><span class="summary-n">${esc(o.ex.name)}</span>` +
      `<span class="summary-from">${esc(o.from)} to</span><span class="tag${cls}">${esc(o.to)}</span></div>`;
    const moves = next.up.map(o => lrow(o, '')).join('') + next.down.map(o => lrow(o, ' summary-down')).join('') +
      (next.more.length ? `<div class="summary-reps"><b>One rep more:</b> ${esc(next.more.join(', '))}</div>` : '') ||
      '<div class="summary-reps">Same loads and targets next week.</div>';
    const mini = o => {
      const pc = o.e.target > 0 ? Math.round(100 * o.s.r / o.e.target) : 0;
      return `<span class="cell num short" style="--p:${pc}%" aria-label="${o.s.r} of ${o.e.target}"><span>${o.s.r}<small>/${o.e.target}</small></span></span>`;
    };
    const synced = p.current && typeof Cali.syncState().token === 'string' && Cali.syncState().token !== '';

    root.innerHTML =
      '<header class="bar2"><button type="button" class="iconbtn" data-act="close" aria-label="Close the summary">' + ic('x') + '</button></header>' +
      '<div class="summary-body">' +
        `<div class="eyebrow">Week ${p.week}, ${esc(dateOf(start === null ? end : start))}</div>` +
        `<h2 class="summary-title">${esc(p.name)}${day.finishedAt ? ' done' : ', so far'}</h2>` +
        '<div class="anchor summary-time" role="group" aria-label="Duration">' +
          `<div class="top"><b>Duration</b><span>${start === null ? 'not started' : `${clockOf(start)} to ${clockOf(end)}`}</span></div>` +
          `<div class="metric">${took === null ? '0:00' : hms(took)}</div></div>` +
        '<div class="summary-tiles">' +
          `<div class="summary-mt"><div class="eyebrow">Sets done</div><div class="summary-v num" data-sum="sets">${done.length}<small> of ${sets.length}</small></div></div>` +
          `<div class="summary-mt"><div class="eyebrow">Short sets</div><div class="summary-v num" data-sum="short">${short.length}</div></div></div>` +
        `<div class="eyebrow summary-head">${next.up.length || next.more.length ? 'Load up next week' : 'Next week'}</div>` +
        `<div class="group" data-sum="next">${moves}</div>` +
        (short.length ? '<div class="eyebrow summary-head">Short sets</div><div class="group" data-sum="shorts">' +
          short.map(o => `<div class="summary-row"><span class="summary-n">${esc(o.e.name)}</span><span class="summary-from">Set ${o.i + 1}</span>${mini(o)}</div>`).join('') +
          '</div>' : '') +
        (synced ? `<div class="summary-sync">${ic('cloud')}Pushes to GitHub when you tap Done</div>` : '') +
      '</div>' +
      (p.current ? '<div class="summary-dock"><button type="button" class="btn secondary" data-act="resume">Resume</button>' +
        '<button type="button" class="btn primary" data-act="done">Done</button></div>' : '');
  }

  function act(root, args, what) {
    const p = where(args);
    if (what === 'close' || !p.current) { Cali.back(); return; }
    const set = fn => Cali.change(d => { fn(d.weeks.find(w => w.n === p.week).days[p.dayId]); },
      { why: what === 'resume' ? 'resume' : 'finish', detail: { week: p.week, dayId: p.dayId } });
    if (what === 'resume') {
      if (p.day && p.day.finishedAt) set(day => { delete day.finishedAt; });
    } else if (what === 'done') {
      if (!p.day || !p.day.finishedAt) set(day => { if (!day.startedAt) day.startedAt = Cali.iso(); day.finishedAt = Cali.iso(); });
      Cali.emit('dayDone', { week: p.week, dayId: p.dayId });
    }
    Cali.back();
  }

  Cali.route('summary', {
    render(root, args) {
      draw(root, args);
      root.addEventListener('click', e => {
        const btn = e.target.closest('[data-act]');
        if (btn) act(root, args, btn.dataset.act);
      });
    },
    update(root, args) { draw(root, args); },
  });
})();
