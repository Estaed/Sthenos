/* Muscle map (app/muscles.js, styles in app/muscles.css, body paths in app/muscles-data.js): route 'muscles' { week }
   and its button in the day screen's top bar. Blueprint -> Decisions (muscle map) and Data (an exercise's muscles);
   the look is design/muscles.html (red is a recorded break, design/deviations.md 2026-10-26).

   What counts (fractional, Pelland 2026): the week in view (week: n; missing or unknown, the current week), never
   the program, so a past week shows the copy it was built with. Per day, in the day screen's order and names (the
   program's current day names, else the day id), every reps or time exercise of the week (Cali.dayExercises) gives
   each of its muscles sets x 1 (the muscle it is for) or sets x 0.5 (a helper); done sets are its logged sets above 0
   (a set at 0 is not done). Check rows (stretch, walk, warm-up) are neither counted nor listed.
   An exercise's muscles: its own `muscles` object (Blueprint -> Data) with every entry that is not a key of
   Cali.muscles set to 1 or 0.5 dropped, so a bad value in a pulled week is ignored, never thrown ({} counts
   nothing); no `muscles`, or one that is not an object: the name table below guesses them (CaliMuscles.guess).
   A reps or time row that neither carries nor guesses is listed once under the box ("Not counted: <name>"), a tap
   opening its program editor at the Muscles field (route 'program' { id, dayId, exId }, app/program.js).

   The screen: Back (to the day screen it came from), "Muscles" and the week's pill; chips Week, then each day; a
   front and back body, each muscle painted from the fractional sets of the selection on one absolute scale (Week
   and a day alike): 0 the body grey, then pale orange through orange (5) to red (FULL = 10 and up), mixed in OKLCH
   from --mm-lo, --mm-mid and --mm-hi (app/muscles.css; a browser without color-mix gets the nearest stop), with
   the scale under the bodies. Then the anchor box: the least worked of the MAIN muscles worked in the selection,
   with the exercises that give its sets and the muscles not worked at all; a tap on a muscle (on the body, where it
   is big enough to hit, or on its row) puts that muscle in the box instead, until the box's close button or a
   second tap on it. Then one row per muscle, most sets first and the ones not worked at the end: the sets planned
   as a grey bar, the sets done filling it orange (orange means done, as on the workout screen), done/planned in
   figures, and on Week only a tick at FLOOR = 4 sets a week (Iversen 2021), the rows under it muted.

   Top bar: a Lucide biceps-flexed button through Cali.slot('topbar', node, -15), right before the timer's hourglass
   (which keeps the holder's right end); it is the first node on the right, so it carries .slot-end; it opens Cali.go('muscles', { week }) with the week the day screen shows (Cali.dayArgs). At 360 px the bar has no
   44 px to spare once the session clock runs (measured 2026-10-26: 22 px free under an hour, none past it or with a
   countdown pill), so the button shrinks there instead of running under Settings, and is hidden while it is narrower
   than 44 px (class mm-cramped, kept by a ResizeObserver); the bar's own layout is not this file's.

   window.CaliMuscles (read by app/program.js and the tests), frozen:
     names               { <muscle key>: the name the screens show } for every key of Cali.muscles.
     guess(name, kind)   the name table's muscles for an exercise name ({ <key>: 1 | 0.5 }, a fresh object), or null
                         when no line matches or kind is 'check'. First matching line wins, so specific lines
                         (Close-grip Bench Press, Upright Row, Bench Dip) come before the general ones.
     of(exercise)        the muscles an exercise counts with (its own, cleaned, else the guess), null when none.
     count(n)            week n (null: current) counted: { week, days: [{ id, name }], total, byDay: { <dayId> } },
                         total and each day { plan: { <key>: sets }, done: { <key>: sets }, from: { <key>: [{ name,
                         sets, part, dayId, dayName }] }, uncounted: [{ name, dayId, exId }] }; null for no such week.
     tone(sets)          the CSS fill for that many fractional sets. */
(() => {
  'use strict';
  const esc = Cali.esc;
  const KEYS = Cali.muscles;
  const BODY = self.CALI_BODY;
  const FULL = 10;     // fractional sets that paint a muscle full red, for Week and for a day
  const FLOOR = 4;     // sets a week, the floor for growth (Iversen 2021): the tick on Week's bars
  const NAMES = Object.freeze({
    chest: 'Chest', deltoids: 'Shoulders', biceps: 'Biceps', triceps: 'Triceps', forearm: 'Forearms', abs: 'Abs',
    obliques: 'Obliques', 'upper-back': 'Upper back', trapezius: 'Traps', 'lower-back': 'Lower back', gluteal: 'Glutes',
    quadriceps: 'Quads', hamstring: 'Hamstrings', adductors: 'Adductors', calves: 'Calves', tibialis: 'Shins',
  });
  // the muscles the least-worked box chooses from; the small ones (forearms, traps, ...) are named only when not worked
  const MAIN = ['chest', 'upper-back', 'deltoids', 'quadriceps', 'hamstring', 'gluteal', 'biceps', 'triceps', 'calves', 'abs'];
  const PATHS = {
    back: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    muscle: '<path d="M12.409 13.017A5 5 0 0 1 22 15c0 3.866-4 7-9 7-4.077 0-8.153-.82-10.371-2.462-.426-.316-.631-.832-.62-1.362C2.118 12.723 2.627 2 10 2a3 3 0 0 1 3 3 2 2 0 0 1-2 2c-1.105 0-1.64-.444-2-1"/><path d="M15 14a5 5 0 0 0-7.584 2"/><path d="M9.964 6.825C8.019 7.977 9.5 13 8 15"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    right: '<path d="m9 18 6-6-6-6"/>',
  };
  const icon = name => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${PATHS[name]}</svg>`;
  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const half = n => String(Math.round(n * 2) / 2);
  const sets = n => `${half(n)} ${n === 1 ? 'set' : 'sets'}`;

  // ── the name table: an exercise's name -> its muscles (1 the muscle it is for, 0.5 a helper) ──
  // matched on the name in lower case with every run of other characters made one space ("Pull-up" -> "pull up")
  const RULES = [
    [/\b(close|narrow) grip (bench|press)|\bdiamond (push|press) ?ups?\b|\bjm press\b/, { triceps: 1, chest: 0.5, deltoids: 0.5 }],
    [/\b(bench|triceps?|tricep) dips?\b/, { triceps: 1, deltoids: 0.5 }],
    [/\btriceps?\b|\bskull ?crushers?\b|\bpush ?downs?\b|\bfrench press\b|\boverhead extensions?\b/, { triceps: 1 }],
    [/\bupright rows?\b/, { deltoids: 1, trapezius: 0.5 }],
    [/\bface pulls?\b|\brear delts?\b|\breverse (fly|flys|flye|flyes|flies|pec deck)\b/, { deltoids: 1, 'upper-back': 0.5, trapezius: 0.5 }],
    [/\bshrugs?\b/, { trapezius: 1 }],
    [/\b(lateral|side|front|y|delt|deltoid) raises?\b/, { deltoids: 1 }],
    [/\b(overhead|shoulder|military|arnold|push|landmine|z) press\b|\bohp\b|\b(pike|handstand) (push|press) ?ups?\b/, { deltoids: 1, triceps: 0.5 }],
    [/\bpullovers?\b|\bstraight arm (pull ?downs?|pushdowns?)\b/, { 'upper-back': 1 }],
    [/\b(pull|chin|muscle) ?ups?\b/, { 'upper-back': 1, biceps: 0.5, forearm: 0.5 }],
    [/\bpull ?downs?\b|\blat pulls?\b/, { 'upper-back': 1, biceps: 0.5 }],
    [/\brows?\b|\bt bar\b|\bpendlay\b/, { 'upper-back': 1, trapezius: 0.5, biceps: 0.5, deltoids: 0.5 }],
    [/\bdips?\b/, { chest: 1, triceps: 0.5, deltoids: 0.5 }],
    [/\b(push|press) ?ups?\b/, { chest: 1, triceps: 0.5, deltoids: 0.5 }],
    [/\b(fly|flys|flye|flyes|flies)\b|\bpec deck\b|\bcrossovers?\b|\bcable cross\b/, { chest: 1, deltoids: 0.5 }],
    [/\bbench\b|\b(chest|incline|decline|floor)( dumbbell| db| barbell| machine| smith)? press\b/, { chest: 1, deltoids: 0.5, triceps: 0.5 }],
    [/\bleg extensions?\b|\bsissy squats?\b/, { quadriceps: 1 }],
    [/\b(leg|hamstring|nordic) curls?\b|\bnordics?\b|\bglute ham\b|\bghr\b/, { hamstring: 1 }],
    [/\bdeadlifts?\b|\brdls?\b|\bgood mornings?\b/, { hamstring: 1, gluteal: 0.5, 'lower-back': 0.5 }],
    [/\bhip thrusts?\b|\bbridges?\b|\bpull ?throughs?\b|\bswings?\b|\bkick ?backs?\b|\bdonkey kicks?\b/, { gluteal: 1, hamstring: 0.5 }],
    [/\babduct(ion|ions|or|ors)\b|\bclam ?shells?\b/, { gluteal: 1 }],
    [/\badduct(ion|ions|or|ors)\b|\bcopenhagen\b/, { adductors: 1 }],
    [/\bleg press\b|\bsquats?\b|\bpistols?\b/, { quadriceps: 1, gluteal: 0.5, adductors: 0.5 }],
    [/\blunges?\b|\bstep ?ups?\b/, { quadriceps: 1, gluteal: 0.5 }],
    [/\bcalf\b|\bcalves\b/, { calves: 1 }],
    [/\btibialis\b|\btib raises?\b|\btoe raises?\b/, { tibialis: 1 }],
    [/\bback extensions?\b|\bhyper ?extensions?\b|\breverse hypers?\b|\bsupermans?\b/, { 'lower-back': 1, gluteal: 0.5, hamstring: 0.5 }],
    [/\bwrist\b|\bfarmers?\b|\bdead hangs?\b|\bgrip\b/, { forearm: 1 }],
    [/\b(hammer|reverse|zottman) curls?\b/, { biceps: 1, forearm: 0.5 }],
    [/\bcurls?\b|\bbiceps?\b/, { biceps: 1 }],
    [/\bside planks?\b|\btwists?\b|\bwood ?chops?\b|\bpallof\b|\bobliques?\b|\bside bends?\b/, { obliques: 1, abs: 0.5 }],
    [/\bplanks?\b/, { abs: 1, obliques: 0.5 }],
    [/\b(leg|knee) raises?\b|\btoes to bar\b|\bcrunch(es)?\b|\bsit ?ups?\b|\bab wheel\b|\brollouts?\b|\bhollow\b|\bdead bugs?\b|\bl sits?\b|\bdragon flags?\b|\bv ups?\b|\babs\b/, { abs: 1 }],
  ];
  const norm = name => String(name === undefined || name === null ? '' : name).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  function guess(name, kind) {
    if (kind === 'check') return null;
    const n = norm(name);
    const hit = n && RULES.find(([re]) => re.test(n));
    return hit ? { ...hit[1] } : null;
  }
  // a stored muscles object with only its valid entries; null when it is not an object (then the name guesses)
  function clean(m) {
    if (!isObj(m)) return null;
    const out = {};
    for (const k of KEYS) if (Object.prototype.hasOwnProperty.call(m, k) && (m[k] === 1 || m[k] === 0.5)) out[k] = m[k];
    return out;
  }
  function musclesOf(ex) {
    if (!isObj(ex) || ex.kind === 'check') return null;
    return clean(ex.muscles) || guess(ex.name, ex.kind);
  }

  // ── counting the week in view ─────────────────────────────────────
  function daysOf(w) {
    const p = Cali.program(w.program);
    const days = (p ? p.days : []).filter(d => w.days[d.id]).map(d => ({ id: d.id, name: d.name }));
    for (const id of Object.keys(w.days)) if (!days.some(d => d.id === id)) days.push({ id, name: id });
    return days;
  }
  const blank = () => ({ plan: {}, done: {}, from: {}, uncounted: [] });
  function count(n) {
    const w = Cali.week(n === undefined ? null : n);
    if (!w) return null;
    const days = daysOf(w);
    const total = blank(), byDay = {};
    for (const day of days) {
      const t = blank();
      byDay[day.id] = t;
      for (const ex of Cali.dayExercises(w.n, day.id)) {
        if (ex.kind === 'check') continue;
        const m = musclesOf(ex);
        if (!m) {
          const u = { name: ex.name, dayId: day.id, exId: ex.id };
          for (const into of [t, total]) if (!into.uncounted.some(x => x.name === u.name)) into.uncounted.push(u);
          continue;
        }
        const planned = ex.sets.length;
        const done = ex.sets.filter(s => s && typeof s.r === 'number' && s.r > 0).length;
        for (const [k, part] of Object.entries(m)) {
          for (const into of [t, total]) {
            into.plan[k] = (into.plan[k] || 0) + part * planned;
            into.done[k] = (into.done[k] || 0) + part * done;
            (into.from[k] = into.from[k] || []).push({ name: ex.name, sets: planned, part, dayId: day.id, dayName: day.name });
          }
        }
      }
    }
    return { week: w.n, days, total, byDay };
  }

  // ── colour: 0 the body grey; pale orange -> orange (FULL / 2) -> red (FULL and up), mixed in OKLCH ──
  const MIX = typeof CSS !== 'undefined' && CSS.supports && CSS.supports('color', 'color-mix(in oklch, red 50%, blue)');
  const pct = x => `${Math.round(x * 1000) / 10}%`;
  function tone(n) {
    if (!(n > 0)) return 'var(--mm-zero)';
    const t = Math.min(1, n / FULL);
    if (!MIX) return t < 1 / 3 ? 'var(--mm-lo)' : t < 2 / 3 ? 'var(--mm-mid)' : 'var(--mm-hi)';
    return t < 0.5 ? `color-mix(in oklch, var(--mm-mid) ${pct(t * 2)}, var(--mm-lo))`
      : `color-mix(in oklch, var(--mm-hi) ${pct((t - 0.5) * 2)}, var(--mm-mid))`;
  }

  // ── the screen ────────────────────────────────────────────────────
  let screen = null;   // { root, n, sel: null (Week) | dayId, pick: null | muscle key, c: count(n) }

  function bodySvg(side) {
    let out = `<svg class="mm-svg" viewBox="${BODY.viewBox[side]}" aria-hidden="true" focusable="false">`;
    for (const [slug, ds] of Object.entries(BODY[side])) {
      const muscle = KEYS.includes(slug);
      out += `<g class="${muscle ? 'mm-m' : 'mm-rest'}"${muscle ? ` data-m="${slug}"` : ''}>${ds.map(d => `<path d="${d}"/>`).join('')}</g>`;
    }
    return `${out}<path class="mm-outline" d="${BODY.outline[side]}"/></svg>`;
  }

  function markup() {
    return '<header class="bar2"><button type="button" class="iconbtn" data-act="back" aria-label="Back">' + icon('back') + '</button>' +
        '<h2>Muscles</h2><span class="pill mm-pill" data-v="week"></span></header>' +
      '<div class="mm-body">' +
        '<div class="mm-days" role="group" aria-label="Show the sets of" data-v="days"></div>' +
        `<figure class="card mm-figure">${bodySvg('front')}${bodySvg('back')}<figcaption>Front</figcaption><figcaption>Back</figcaption>` +
          '<div class="mm-scale"><span class="mm-none"><i></i>None</span><span>1 set</span><i class="mm-ramp"></i><span>10+ sets</span></div></figure>' +
        '<div class="anchor mm-pick" data-v="box" aria-live="polite"></div>' +
        '<div class="group mm-fix" data-v="fix" hidden></div>' +
        '<div class="group mm-list" data-v="list" role="group" aria-label="Sets per muscle"></div>' +
      '</div>';
  }

  const selName = s => (s.sel ? (s.c.days.find(d => d.id === s.sel) || { name: s.sel }).name : null);
  const fromLine = (s, list) => list.map(f => `${f.name} ${f.sets}${s.sel ? '' : ` (${f.dayName})`}`).join(', ');

  function boxHtml(s, t) {
    const day = selName(s);
    const where = day ? `on ${day}` : 'a week';
    const p = text => `<p>${esc(text)}</p>`;
    if (s.pick) {
      const k = s.pick, n = t.plan[k] || 0, from = t.from[k] || [];
      const mains = from.filter(f => f.part === 1), helps = from.filter(f => f.part !== 1);
      const lines = n ? (mains.length ? p(fromLine(s, mains)) : '') + (helps.length ? p(`Helper, counts half: ${fromLine(s, helps)}`) : '')
        : p(`No exercise ${day ? `on ${day}` : `in week ${s.c.week}`} works it.`);
      return '<span class="eyebrow">Selected muscle</span>' +
        `<button type="button" class="iconbtn mm-close" data-act="unpick" aria-label="Back to the least worked">${icon('x')}</button>` +
        `<h3>${esc(NAMES[k])} · ${esc(n ? `${sets(n)} ${where}` : 'not worked')}</h3>${lines}`;
    }
    const none = KEYS.filter(k => !(t.plan[k] > 0)).map(k => NAMES[k]);
    const notWorked = none.length === KEYS.length ? '' : none.length ? p(`Not worked: ${none.join(', ')}`) : '';
    const least = MAIN.filter(k => t.plan[k] > 0).sort((a, b) => t.plan[a] - t.plan[b] || MAIN.indexOf(a) - MAIN.indexOf(b))[0];
    if (!least) {
      const any = KEYS.some(k => t.plan[k] > 0);
      return '<span class="eyebrow">Least worked</span>' +
        `<h3>${esc(any ? 'No main muscle worked' : 'No sets counted')}</h3>` +
        (any ? notWorked : p(`No exercise ${day ? `on ${day}` : `in week ${s.c.week}`} works a muscle.`));
    }
    const from = t.from[least] || [];
    const mains = from.filter(f => f.part === 1);
    return '<span class="eyebrow">Least worked</span>' +
      `<h3>${esc(NAMES[least])} · ${esc(`${sets(t.plan[least])} ${where}`)}</h3>` +
      p(mains.length ? fromLine(s, mains) : 'Only as a helper') + notWorked;
  }

  function rowsHtml(s, t) {
    const worked = KEYS.filter(k => t.plan[k] > 0).sort((a, b) => t.plan[b] - t.plan[a] || KEYS.indexOf(a) - KEYS.indexOf(b));
    const idle = KEYS.filter(k => !(t.plan[k] > 0));
    const week = !s.sel;
    const max = Math.max(week ? FLOOR * 1.25 : 1, ...worked.map(k => t.plan[k]));
    const w = v => `${Math.round((1000 * v) / max) / 10}%`;
    return [...worked, ...idle].map(k => {
      const plan = t.plan[k] || 0, done = t.done[k] || 0;
      const cls = ['mm-row', plan ? '' : 'idle', week && plan < FLOOR ? 'low' : ''].filter(Boolean).join(' ');
      return `<button type="button" class="${cls}" data-m="${k}" aria-pressed="${s.pick === k}" ` +
        `aria-label="${esc(`${NAMES[k]}: ${half(done)} of ${sets(plan)} done`)}"><b>${esc(NAMES[k])}</b>` +
        `<span class="mm-bar" aria-hidden="true"><span class="plan" style="width:${w(plan)}"></span><span class="done" style="width:${w(done)}"></span>` +
        (week ? `<span class="floor" style="left:${w(FLOOR)}"></span>` : '') + '</span>' +
        `<span class="num" aria-hidden="true">${half(done)}<small>/${half(plan)}</small></span></button>`;
    }).join('');
  }

  function fixHtml(t) {
    return t.uncounted.map(u => `<button type="button" class="settings-row mm-fixrow" data-act="fix" data-day="${esc(u.dayId)}" data-ex="${esc(u.exId)}">` +
      `<span class="settings-t">Not counted: ${esc(u.name)}<small>No muscle picked or guessed. Pick them in the program.</small></span>` +
      `<span class="settings-chev">${icon('right')}</span></button>`).join('');
  }

  function paint() {
    const s = screen;
    const { root, c } = s;
    if (s.sel && !c.byDay[s.sel]) s.sel = null;
    const t = s.sel ? c.byDay[s.sel] : c.total;
    root.querySelector('[data-v="week"]').textContent = `Week ${c.week}`;
    root.querySelector('[data-v="days"]').innerHTML = [{ id: '', name: 'Week' }, ...c.days].map(d =>
      `<button type="button" data-sel="${esc(d.id)}" aria-pressed="${(d.id || null) === s.sel}"><span>${esc(d.name)}</span></button>`).join('');
    for (const g of root.querySelectorAll('.mm-m')) {
      const k = g.dataset.m;
      g.style.fill = tone(t.plan[k] || 0);
      g.toggleAttribute('data-on', k === s.pick);
    }
    root.querySelector('.mm-figure').toggleAttribute('data-picked', Boolean(s.pick));
    root.querySelector('[data-v="box"]').innerHTML = boxHtml(s, t);
    const fix = root.querySelector('[data-v="fix"]');
    fix.innerHTML = fixHtml(t);
    fix.hidden = !t.uncounted.length;
    root.querySelector('[data-v="list"]').innerHTML = rowsHtml(s, t);
  }

  function pick(k) {
    const s = screen;
    s.pick = s.pick === k ? null : k;
    paint();
    const box = s.root.querySelector('[data-v="box"]');
    if (box.scrollIntoView) box.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }

  function click(ev) {
    const s = screen;
    if (!s) return;
    const b = ev.target.closest('button');
    if (b && s.root.contains(b)) {
      if (b.dataset.act === 'back') { Cali.back(); return; }
      if (b.dataset.act === 'unpick') { s.pick = null; paint(); return; }
      if (b.dataset.act === 'fix') {
        const w = Cali.week(s.c.week);
        Cali.go('program', { id: w.program, dayId: b.dataset.day, exId: b.dataset.ex });
        return;
      }
      if (b.dataset.sel !== undefined) { s.sel = b.dataset.sel || null; paint(); return; }
      if (b.dataset.m) { pick(b.dataset.m); return; }
      return;
    }
    const g = ev.target.closest && ev.target.closest('.mm-m');
    if (g && s.root.contains(g)) pick(g.dataset.m);
  }

  Cali.route('muscles', {
    render(root, args) {
      root.classList.add('mm');
      const w = Cali.week(args && Number.isInteger(args.week) ? args.week : null) || Cali.week();
      screen = { root, n: w.n, sel: null, pick: null, c: count(w.n) };
      root.innerHTML = markup();
      root.addEventListener('click', click);
      paint();
    },
    update(root) {
      if (!screen || screen.root !== root) return;
      const w = Cali.week(screen.n) || Cali.week();
      screen.n = w.n;
      screen.c = count(w.n);
      paint();
    },
    leave() { screen = null; },
  });

  // ── the way in: the top bar of the day screen, beside the hourglass ──
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'iconbtn slot-end mm-open';
  open.setAttribute('aria-label', 'Muscles');
  open.innerHTML = icon('muscle');
  open.addEventListener('click', () => {
    const cur = Cali.current();
    Cali.go('muscles', { week: Cali.dayArgs(cur && cur.name === 'day' ? cur.args : {}).week });
  });
  Cali.slot('topbar', open, -15);
  // a full bar shrinks it (app/muscles.css) rather than letting it run under Settings; under 44 px it is hidden
  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(() => { open.classList.toggle('mm-cramped', open.isConnected && open.getBoundingClientRect().width < 43.5); }).observe(open);
  }

  self.CaliMuscles = Object.freeze({ names: NAMES, guess, of: musclesOf, count, tone });
})();
