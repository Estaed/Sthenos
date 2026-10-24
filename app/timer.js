/* The independent timer (Task-02): route 'timer' { countdown } (design/screens.html, screen 4) and its pill in the
   day screen's top bar (screen 2). Separate from the rest timer: both live in Cali.timers at once, this one under the
   names 'countdown' (kind 'timer', data { pick }: the length chosen, in seconds) and 'stopwatch'. Every number on
   screen is computed from their start timestamps on each tick, never counted, so it is right after the phone slept.

   Countdown  the presets 30 s, 1, 2 and 4 min start at once; Custom takes minutes and seconds. Start / Pause / Resume,
              Reset (removes it), +1 min (on a finished one: a fresh minute). While it runs its end is scheduled with
              Cali.alert.schedule('timer', endAt, 'timer'); a pause, a reset or a new start cancels or moves it, and a
              reload schedules a running one again. The beep, vibration, flash and notification come from app/alert.js.
   Stopwatch  Start / Pause / Resume, Lap (while running), Reset; laps newest first, each with its split and the total.
   Taps       a second tap within 350 ms at the spot of the last one does nothing: it ends a double tap or a bouncing
              finger, and the button under it was just redrawn (Start is Pause now; the custom Start is +1 min). The
              counting buttons, +1 min and Lap, stay what they were, so every tap on them counts.
   Route      Cali.go('timer', { countdown: seconds }) starts that countdown (a timed row: stretch, walk), unless one of
              that length is running; the history entry is then marked handled, so a reload or the back and forward
              gestures never start it again.
   Top bar    through Cali.slot('topbar'): a pill with the countdown's time left (else the stopwatch's) while one is
              running or paused part-way, at the bar's start; otherwise the timer button (slot-end). Both open this
              screen. */
(() => {
  'use strict';
  const CD = 'countdown';
  const SW = 'stopwatch';
  const PRESETS = [30, 60, 120, 240];
  const MAX_S = 10 * 3600;
  const TICK_MS = 100;
  const SECOND_MS = 350;  // a second tap sooner than this ends a double tap (Pantry's tap guard uses the same 350 ms)
  const SPOT_PX = 40;     // about a fingertip: the nearest other button's centre is 62 px away
  const COUNTING = ['cd-add', 'sw-lap'];  // a quick second tap on the same one is a second request
  const PATHS = {
    hourglass: '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
    timer: '<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/><circle cx="12" cy="14" r="8"/>',
    back: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    play: '<polygon points="6 3 20 12 6 21 6 3"/>',
    pause: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    reset: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
    alert: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
  };
  const icon = name => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${PATHS[name]}</svg>`;

  let chosen = 60;      // the countdown's length while none exists (seconds)
  let editing = false;  // the custom editor is open
  let screen = null;    // the timer screen's root while it is shown
  let drawn = '';       // the state the screen was last drawn for
  let ticker = 0;
  let lastTap = null;   // { at, x, y, act } of the last tap a button on the timer screen took

  // ── formats ───────────────────────────────────────────────────────
  const two = n => String(n).padStart(2, '0');
  function hms(s) {
    const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, x = s % 60;
    return h ? `${h}:${two(m)}:${two(x)}` : `${m}:${two(x)}`;
  }
  const left = ms => hms(Math.ceil(ms / 1000));
  const watch = ms => { const d = Math.floor(ms / 100); return `${hms(Math.floor(d / 10))}.${d % 10}`; };
  const chip = s => (s < 60 ? `${s} s` : `${s / 60} min`);
  function spoken(s) {
    const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, x = s % 60;
    const part = (n, w) => (n ? `${n} ${w}${n === 1 ? '' : 's'}` : '');
    return [part(h, 'hour'), part(m, 'minute'), part(x, 'second')].filter(Boolean).join(' ') || '0 seconds';
  }

  // ── state ─────────────────────────────────────────────────────────
  const cd = () => Cali.timers.get(CD);
  const sw = () => Cali.timers.get(SW);
  const pickOf = c => (c.data && c.data.pick) || Math.round(c.duration / 1000);
  const live = c => Boolean(c && !c.done);

  function start(sec) {
    chosen = sec;
    editing = false;
    Cali.timers.start(CD, { duration: sec * 1000, kind: 'timer', data: { pick: sec } });
  }

  // The countdown's end is an alert while it runs; anything else drops it.
  function follow(t) {
    if (t && t.running && !t.done) Cali.alert.schedule('timer', t.endAt, 'timer');
    else Cali.alert.cancel('timer');
  }

  function stateKey() {
    const c = cd(), s = sw();
    return [c ? `${c.running ? 'run' : 'pause'}${c.done ? '-done' : ''}-${c.duration}-${pickOf(c)}` : `none-${chosen}`,
      s ? `${s.running ? 'run' : 'pause'}-${s.laps.length}` : 'none', editing].join('|');
  }

  // ── the screen ────────────────────────────────────────────────────
  function countdown() {
    const c = cd();
    const total = c ? c.duration : chosen * 1000;
    const rest = c ? c.remaining : total;
    const pick = c ? pickOf(c) : chosen;
    const status = !c ? '' : c.done ? 'Done' : c.running ? `of ${hms(Math.round(total / 1000))}` : 'Paused';
    const custom = editing || !PRESETS.includes(pick);
    const main = !c || c.done ? `${icon('play')}Start` : c.running ? `${icon('pause')}Pause` : `${icon('play')}Resume`;
    const m = Math.floor(pick / 60), s = pick % 60;
    return `<div class="anchor timer-count" role="timer" data-timer="countdown">` +
        `<div class="top"><b>Countdown</b><span data-timer="status">${status}</span></div>` +
        `<div class="metric" data-timer="left">${left(rest)}</div>` +
        `<div class="bar" aria-hidden="true"><i data-timer="bar"></i></div></div>` +
      `<div class="timer-chips" role="group" aria-label="Countdown length">` +
        PRESETS.map(p => `<button type="button" class="timer-chip" data-preset="${p}" aria-pressed="${!custom && pick === p}">${chip(p)}</button>`).join('') +
        `<button type="button" class="timer-chip" data-act="custom" aria-pressed="${custom}" aria-expanded="${editing}">Custom</button></div>` +
      (editing
        ? `<form class="timer-custom" novalidate aria-label="Custom countdown">` +
            `<label class="timer-field"><input name="min" type="number" inputmode="numeric" min="0" max="600" step="1" value="${m}" aria-label="Minutes"><span>min</span></label>` +
            `<label class="timer-field"><input name="sec" type="number" inputmode="numeric" min="0" max="59" step="1" value="${two(s)}" aria-label="Seconds"><span>s</span></label>` +
            `<button type="submit" class="btn primary">${icon('play')}Start</button></form>` +
          `<p class="timer-error" data-timer="error" hidden>${icon('alert')}<span>Enter a length from 1 s to 10 hours.</span></p>`
        : `<div class="timer-ctrls">` +
            `<button type="button" class="btn secondary" data-act="cd-reset"${c ? '' : ' aria-disabled="true"'}>${icon('reset')}Reset</button>` +
            `<button type="button" class="btn primary" data-act="cd-main">${main}</button>` +
            `<button type="button" class="btn secondary" data-act="cd-add" aria-label="Add one minute">${icon('plus')}1 min</button></div>`);
  }

  function stopwatch() {
    const s = sw();
    const laps = s ? s.laps : [];
    const main = !s ? `${icon('play')}Start` : s.running ? `${icon('pause')}Pause` : `${icon('play')}Resume`;
    const rows = laps.map((at, i) => `<li class="timer-lap"><span>Lap ${i + 1}</span><span class="num">${watch(at - (laps[i - 1] || 0))}</span><span>${watch(at)}</span></li>`).reverse();
    return `<section class="card timer-sw${laps.length ? ' has-laps' : ''}" aria-label="Stopwatch">` +
        `<div class="timer-sw-head"><b>Stopwatch</b><span>${s && !s.running ? 'Paused' : ''}</span></div>` +
        `<div class="timer-sw-val" role="timer" data-timer="watch">${watch(s ? s.elapsed : 0)}</div>` +
        `<div class="timer-ctrls">` +
          `<button type="button" class="btn secondary" data-act="sw-reset"${s ? '' : ' aria-disabled="true"'}>${icon('reset')}Reset</button>` +
          `<button type="button" class="btn secondary" data-act="sw-main">${main}</button>` +
          `<button type="button" class="btn secondary" data-act="sw-lap"${s && s.running ? '' : ' aria-disabled="true"'}>${icon('flag')}Lap</button></div>` +
        (rows.length ? `<ol class="timer-laps" aria-label="Laps">${rows.join('')}</ol>` : '') +
      '</section>';
  }

  function draw() {
    if (!screen) return;
    drawn = stateKey();
    screen.innerHTML =
      `<header class="bar2"><button type="button" class="iconbtn" data-act="back" aria-label="Back to the workout">${icon('back')}</button><h2>Timer</h2></header>` +
      `<div class="timer-body">${countdown()}${stopwatch()}</div>`;
    numbers();
  }

  // The moving numbers, rewritten in place on each tick so a button is never replaced under the finger.
  function numbers() {
    const c = cd(), s = sw();
    const total = c ? c.duration : chosen * 1000;
    const rest = c ? c.remaining : total;
    const q = sel => screen.querySelector(`[data-timer="${sel}"]`);
    const text = (el, v) => { if (el && el.textContent !== v) el.textContent = v; };
    text(q('left'), left(rest));
    const len = left(rest).length;
    q('left').dataset.len = String(len);
    q('bar').style.width = `${total ? (100 * rest) / total : 0}%`;
    const box = q('countdown');
    box.setAttribute('aria-label', `Countdown, ${spoken(Math.ceil(rest / 1000))} left of ${spoken(Math.round(total / 1000))}` +
      (c && c.done ? ', done' : c && !c.running ? ', paused' : ''));
    const w = q('watch');
    const shown = watch(s ? s.elapsed : 0);
    text(w, shown);
    if (w.dataset.len !== String(shown.length)) w.dataset.len = String(shown.length);
    w.setAttribute('aria-label', `Stopwatch ${spoken(Math.floor((s ? s.elapsed : 0) / 1000))}${s && !s.running ? ', paused' : ''}`);
  }

  function act(name) {
    const c = cd(), s = sw();
    switch (name) {
      case 'back': Cali.back(); break;
      case 'custom': editing = !editing; draw(); if (editing) focusMinutes(); break;
      case 'cd-main':
        if (!c || c.done) start(c ? pickOf(c) : chosen);
        else if (c.running) Cali.timers.pause(CD);
        else Cali.timers.resume(CD);
        break;
      case 'cd-reset': if (c) { chosen = pickOf(c); Cali.timers.stop(CD); } break;
      case 'cd-add':
        if (live(c)) Cali.timers.add(CD, 60000);
        else if (c) start(60);
        else { chosen = Math.min(chosen + 60, MAX_S); draw(); }
        break;
      case 'sw-main':
        if (!s) Cali.timers.start(SW, { kind: 'stopwatch' });
        else if (s.running) Cali.timers.pause(SW);
        else Cali.timers.resume(SW);
        break;
      case 'sw-reset': if (s) Cali.timers.stop(SW); break;
      case 'sw-lap': if (s && s.running) Cali.timers.lap(SW); break;
      default: break;
    }
  }

  function focusMinutes() {
    const input = screen && screen.querySelector('.timer-custom input[name="min"]');
    if (input) { input.focus(); input.select(); }
  }

  function submitCustom(form) {
    const n = name => { const v = form.elements[name].value.trim(); return /^\d+$/.test(v) ? Number(v) : NaN; };
    const total = n('min') * 60 + n('sec');
    if (Number.isInteger(total) && total > 0 && total <= MAX_S && n('sec') < 60) { start(total); return; }
    screen.querySelector('[data-timer="error"]').hidden = false;
  }

  function wire(root) {
    root.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b || !root.contains(b) || b.getAttribute('aria-disabled') === 'true') return;
      const what = b.dataset.act || '';
      const again = lastTap && COUNTING.includes(what) && what === lastTap.act;
      if (lastTap && !again && e.timeStamp - lastTap.at < SECOND_MS && Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y) < SPOT_PX) {
        e.preventDefault();   // the end of a double tap: no second step, and no submit of the custom form
        return;
      }
      lastTap = { at: e.timeStamp, x: e.clientX, y: e.clientY, act: what };
      if (b.dataset.preset) start(Number(b.dataset.preset));
      else if (b.dataset.act) act(b.dataset.act);
    });
    root.addEventListener('submit', e => {
      e.preventDefault();
      if (e.target.classList.contains('timer-custom')) submitCustom(e.target);
    });
  }

  // A timed row's request: start it once per history entry, keeping a running countdown of the same length.
  function request(args) {
    const sec = args && args.countdown;
    if (typeof sec !== 'number' || !Number.isFinite(sec) || sec <= 0 || sec > MAX_S) return;
    const state = history.state && typeof history.state === 'object' ? history.state : {};
    if (state.timerHandled) return;
    history.replaceState({ ...state, timerHandled: true }, '', location.href);
    const s = Math.round(sec) || 1;
    const c = cd();
    if (c && c.running && !c.done && c.duration === s * 1000) { chosen = s; return; }
    start(s);
  }

  Cali.route('timer', {
    render(root, args) { screen = root; editing = false; wire(root); request(args); draw(); plan(); },
    leave() { screen = null; editing = false; plan(); },
  });

  // ── the top bar ───────────────────────────────────────────────────
  const pill = document.createElement('button');
  pill.type = 'button';
  pill.className = 'timer-pill';
  pill.hidden = true;
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'iconbtn slot-end timer-open';
  open.setAttribute('aria-label', 'Timer');
  open.innerHTML = icon('hourglass');
  for (const b of [pill, open]) b.addEventListener('click', () => Cali.go('timer'));
  Cali.slot('topbar', pill, -20);
  Cali.slot('topbar', open, -10);

  let pillDrawn = '';
  function updatePill() {
    const c = cd(), s = sw();
    const shown = live(c) ? 'countdown' : s ? 'stopwatch' : '';
    pill.hidden = !shown;
    open.hidden = Boolean(shown);
    if (!shown) { pillDrawn = ''; return; }
    const t = shown === 'countdown' ? c : s;
    const value = shown === 'countdown' ? left(c.remaining) : hms(Math.floor(s.elapsed / 1000));
    const look = `${shown}|${value}|${t.running}`;
    if (look === pillDrawn) return;
    pillDrawn = look;
    pill.innerHTML = `${icon(shown === 'countdown' ? 'hourglass' : 'timer')}<span class="num">${value}</span>`;
    pill.toggleAttribute('data-paused', !t.running);
    pill.setAttribute('aria-label', `${shown === 'countdown' ? 'Countdown' : 'Stopwatch'} ${value}${shown === 'countdown' ? ' left' : ''}` +
      `${t.running ? '' : ', paused'}, open the timer`);
  }

  // ── ticking ───────────────────────────────────────────────────────
  function tick() {
    updatePill();
    if (screen) { if (stateKey() !== drawn) draw(); else numbers(); }
    plan();
  }
  function plan() {
    const c = cd(), s = sw();
    const want = document.visibilityState === 'visible' && ((c && c.running && !c.done) || (s && s.running));
    if (want && !ticker) ticker = setInterval(tick, TICK_MS);
    else if (!want && ticker) { clearInterval(ticker); ticker = 0; }
  }

  Cali.on('timer', e => {
    if (e.name !== CD && e.name !== SW) return;
    if (e.name === CD) follow(e.timer);
    tick();
  });
  document.addEventListener('visibilitychange', tick);

  const running = cd();
  if (running && running.running && !running.done) follow(running);
  updatePill();
  plan();
})();
