/* Alerts (Task-02): fills Cali.alert through Cali.provide('alert', { alert, schedule, cancel, requestPermission }).
   Design: reports/2026-10-24-rest-alert-screen-off.md -> Recommended design, tested on Tarik's phone (Blueprint ->
   Riskiest assumption): the screen kept awake with an in-page beep, vibration and visual change is the main path; a
   service-worker notification at the end time is the fallback.

   Cali.alert(kind)       'rest', 'headsup', 'timer' or 'test': a beep (Web Audio; the audio context is made on the first
                          tap, since a phone plays nothing before one) when settings.sound is on, a vibration
                          (navigator.vibrate, only after a tap) when settings.vibrate is on, and the visual change: the
                          whole screen flashes inverted with the alert's words (role="alert"); it never catches a tap.
   Cali.alert.schedule(kind, endAt, tag)
                          Two triggers for one end:
                          1. the page posts { type: 'cali-alert', op: 'schedule', kind, endAt, tag, title } to the
                             service worker (sw-alert.js), which holds the event open with event.waitUntil until endAt and
                             shows a requireInteraction notification under tag, even when the page is frozen or gone
                             (about 5 min per event on Android);
                          2. the page keeps its own timer: at endAt, while it is awake, it plays Cali.alert(kind) when
                             visible and asks the worker to show the same notification (op 'show'). The worker keeps one
                             notification per tag and end, so only one appears and it rings once.
                          A later schedule under the same tag and kind replaces the earlier one. When the page goes
                          hidden it posts its pending alerts again, so the worker's 5-minute window starts then. When the
                          worker's own timer fires it tells the open pages ('fired'); a visible page that lost its timer
                          (a reload) plays the in-page alert then. An end more than 60 s past is not played in the page:
                          the phone slept through it and the notification covered it.
   Cali.alert.cancel(tag) drops every pending alert under tag, in the page and in the worker, and closes a notification
                          already shown under it (the next set was logged, the countdown was reset).
   Cali.alert.requestPermission()  asks for notifications only while the permission is 'default', one prompt at a time;
                          otherwise answers the state ('granted', 'denied', 'unsupported'). Never called on load; the
                          button is in Settings (Task-03).
   Callers (the rest timer, app/timer.js) only schedule and cancel: the in-page alert at the end comes from here, so they
   never also call Cali.alert(kind) for the same end. Without notification permission only the in-page alert runs. */
(() => {
  'use strict';
  const LATE_MS = 60000;
  const GAP_MS = 110;
  const REST = [[1046, 180], [1046, 180], [1046, 360]];
  const REST_BUZZ = [300, 120, 300, 120, 500];
  const KINDS = {
    rest: { title: () => 'Rest over', tones: REST, buzz: REST_BUZZ, flashes: 2 },
    headsup: { title: () => `Rest ends in ${Cali.settings.get('headsUp')} s`, tones: [[784, 140]], buzz: [150], flashes: 1 },
    timer: { title: () => 'Countdown done', tones: [[1175, 220], [1175, 220], [1175, 220], [1568, 420]],
      buzz: [500, 150, 500, 150, 500], flashes: 2 },
    test: { title: () => 'Test alert', tones: REST, buzz: REST_BUZZ, flashes: 2 },
  };

  const style = document.createElement('style');
  style.textContent = `
.alert-flash { position: fixed; inset: 0; z-index: 1000; pointer-events: none; display: grid; place-items: center; padding: 24px;
  background: var(--anchor); color: var(--on-anchor); opacity: 0; animation: alert-flash-2 2400ms linear forwards; }
.alert-flash[data-flashes="1"] { animation-name: alert-flash-1; animation-duration: 1400ms; }
.alert-flash b { font-family: var(--font-display); font-stretch: var(--display-stretch); font-weight: 700; font-size: 2.5rem;
  line-height: 1.1; letter-spacing: -0.5px; text-align: center; }
@keyframes alert-flash-2 { 0% { opacity: 0; } 6% { opacity: 1; } 20% { opacity: 0.15; } 30% { opacity: 1; } 80% { opacity: 1; } 100% { opacity: 0; } }
@keyframes alert-flash-1 { 0% { opacity: 0; } 10% { opacity: 1; } 70% { opacity: 1; } 100% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .alert-flash { animation-name: alert-flash-1; } }
`;
  document.head.appendChild(style);

  // ── the in-page alert ─────────────────────────────────────────────
  let audio = null;
  function unlock() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    try {
      if (!audio || audio.state === 'closed') audio = new AC();
      if (audio.state !== 'running') audio.resume().catch(() => {});
    } catch (e) { audio = null; }
  }
  for (const type of ['touchend', 'pointerup', 'click', 'keydown']) document.addEventListener(type, unlock, { capture: true, passive: true });

  function beep(tones) {
    if (!audio || audio.state === 'closed') return;
    if (audio.state !== 'running') audio.resume().catch(() => {});
    let t = audio.currentTime + 0.03;
    for (const [hz, ms] of tones) {
      const end = t + ms / 1000;
      const osc = audio.createOscillator();
      const gain = audio.createGain();
      osc.type = 'square';
      osc.frequency.value = hz;
      gain.gain.setValueAtTime(0, t);
      gain.gain.linearRampToValueAtTime(0.2, t + 0.01);
      gain.gain.setValueAtTime(0.2, end - 0.02);
      gain.gain.linearRampToValueAtTime(0, end);
      osc.connect(gain).connect(audio.destination);
      osc.start(t);
      osc.stop(end + 0.01);
      t = end + GAP_MS / 1000;
    }
  }

  // A phone vibrates only for a page that has been tapped; before that the call is refused with a console intervention.
  const canBuzz = () => typeof navigator.vibrate === 'function'
    && (!navigator.userActivation || navigator.userActivation.hasBeenActive);

  function flash(kind) {
    for (const old of document.querySelectorAll('.alert-flash')) old.remove();
    const el = document.createElement('div');
    el.className = 'alert-flash';
    el.dataset.kind = kind;
    el.dataset.flashes = String(KINDS[kind].flashes);
    el.setAttribute('role', 'alert');
    el.innerHTML = `<b>${Cali.esc(KINDS[kind].title())}</b>`;
    document.body.appendChild(el);
    const gone = () => el.remove();
    el.addEventListener('animationend', gone, { once: true });
    setTimeout(gone, 3000);
  }

  function alert(kind) {
    const k = KINDS[kind];
    if (Cali.settings.get('sound')) beep(k.tones);
    if (Cali.settings.get('vibrate') && canBuzz()) navigator.vibrate(k.buzz);
    flash(kind);
  }

  // ── scheduled alerts ──────────────────────────────────────────────
  const pending = new Map();   // tag + kind -> { kind, endAt, tag, timer }
  const played = new Set();    // ends this page has played or dropped (tag, kind, endAt)
  const keyOf = (tag, kind) => `${tag}\n${kind}`;
  const idOf = e => `${e.tag}\n${e.kind}\n${e.endAt}`;
  const permission = () => (typeof Notification === 'undefined' ? 'unsupported' : Notification.permission);
  const note = (op, e) => ({ op, kind: e.kind, endAt: e.endAt, tag: e.tag, title: KINDS[e.kind].title() });

  function remember(id) {
    played.add(id);
    if (played.size > 100) played.delete(played.values().next().value);
  }

  function post(msg) {
    if (!('serviceWorker' in navigator)) return;
    navigator.serviceWorker.ready
      .then(reg => { if (reg.active) reg.active.postMessage({ type: 'cali-alert', ...msg }); })
      .catch(() => {});
  }

  function arm(entry) {
    const wait = Math.min(Math.max(0, entry.endAt - Cali.now()), 2 ** 31 - 1);
    entry.timer = setTimeout(() => (entry.endAt > Cali.now() ? arm(entry) : fire(entry)), wait);
  }

  function fire(entry) {
    const key = keyOf(entry.tag, entry.kind);
    if (pending.get(key) !== entry) return;
    pending.delete(key);
    if (played.has(idOf(entry))) return;
    remember(idOf(entry));
    if (document.visibilityState === 'visible' && Cali.now() - entry.endAt <= LATE_MS) alert(entry.kind);
    if (permission() === 'granted') post(note('show', entry));
  }

  function schedule(kind, endAt, tag) {
    const key = keyOf(tag, kind);
    const old = pending.get(key);
    if (old) clearTimeout(old.timer);
    const entry = { kind, endAt, tag, timer: 0 };
    pending.set(key, entry);
    arm(entry);
    post(note('schedule', entry));
  }

  function cancel(tag) {
    for (const [key, e] of pending) {
      if (e.tag !== tag) continue;
      clearTimeout(e.timer);
      pending.delete(key);
      remember(idOf(e));
    }
    post({ op: 'cancel', tag });
  }

  // Hidden: post the pending ends again, so the worker's event (about 5 min) starts now, not when the alert was set.
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') for (const e of pending.values()) post(note('schedule', e));
  });

  // The worker's own timer fired: play it here if this page did not, and the page's clock agrees that it is the end.
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', event => {
      const m = event.data;
      if (!m || m.type !== 'cali-alert' || m.op !== 'fired' || !KINDS[m.kind] || typeof m.endAt !== 'number') return;
      const now = Cali.now();
      if (played.has(idOf(m)) || now < m.endAt - 2000 || now - m.endAt > LATE_MS) return;
      const key = keyOf(m.tag, m.kind);
      const e = pending.get(key);
      if (e && e.endAt !== m.endAt) return;
      if (e) { clearTimeout(e.timer); pending.delete(key); }
      remember(idOf(m));
      if (document.visibilityState === 'visible') alert(m.kind);
    });
    if (typeof navigator.serviceWorker.startMessages === 'function') navigator.serviceWorker.startMessages();
  }

  // ── permission ────────────────────────────────────────────────────
  let asking = null;
  function requestPermission() {
    if (permission() !== 'default') return Promise.resolve(permission());
    if (!asking) {
      asking = new Promise(resolve => {
        let answer;
        try { answer = Notification.requestPermission(resolve); } catch (e) { resolve(permission()); return; }
        if (answer && typeof answer.then === 'function') answer.then(resolve, () => resolve(permission()));
      }).then(state => { asking = null; return state; });
    }
    return asking;
  }

  Cali.provide('alert', { alert, schedule, cancel, requestPermission });
})();
