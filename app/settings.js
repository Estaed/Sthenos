/* Settings (app/settings.js, styles in app/settings.css): screen 5 of design/r6/screens.html. Route 'settings' (no
   args); the way in is a gear in the day screen's top bar, right after the 'topbar' holder (after the timer's
   buttons, before Finish). Every value goes through Cali.settings (core saves it in the document and applies the
   theme app-wide).

   Rest and alerts   pair rest and rest between exercises (steps of 15 s, 0:15 to 10:00), start rest after a log,
                     heads-up 10 s before the end, vibrate, sound; "Test alert" (Cali.alert('test')) and
                     notifications: "Allow" calls Cali.alert.requestPermission(); while Notification.permission is
                     not 'granted' one line says the alert then needs the screen kept awake and how to allow them.
   Workout           keep screen awake, default load step (1, 1.25, 2.5, 5 kg), theme (system, light, dark).
   Data              GitHub sync (app/sync.js through self.CaliSync): its state, a token to connect, Sync now and
                     Disconnect; "Download backup" saves the whole v5 document as JSON (the token is never in it;
                     while Cali.problem() is set it saves nothing and says why, as the document in memory is then
                     core's empty stand-in, not the stored log);
                     "Restore from backup" accepts only a file with _version 5 and asks before it replaces the log
                     (Cali.replace, why 'restore', dirty, so sync pushes it like any other change). */
(() => {
  'use strict';

  const esc = Cali.esc;
  const REST_STEP = 15;
  const REST_MIN = 15;
  const REST_MAX = 600;
  const LOAD_STEPS = [1, 1.25, 2.5, 5];
  const THEMES = [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const PERMISSION_HELP = 'Until notifications are allowed, the rest alert needs the screen kept awake. Tap Allow; if ' +
    'nothing changes, allow notifications for this site in the browser\'s site settings, then come back.';

  // Lucide icons (the set design/r6/screens.html uses)
  const IC = {
    gear: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    back: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    minus: '<path d="M5 12h14"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    bell: '<path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/>',
    cloud: '<path d="M12 13v8"/><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="m8 17 4-4 4 4"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
    alert: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
  };
  const icon = name => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${IC[name]}</svg>`;

  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const pad = n => String(n).padStart(2, '0');
  const clock = s => `${Math.floor(s / 60)}:${pad(s % 60)}`;
  const sync = () => self.CaliSync || null;
  const permission = () => (typeof Notification === 'undefined' ? 'unsupported' : Notification.permission);

  function when(isoText) {
    const t = Date.parse(isoText);
    if (!Number.isFinite(t)) return '';
    const ago = Cali.now() - t;
    if (ago >= 0 && ago < 60000) return 'just now';
    if (ago >= 0 && ago < 3600000) return `${Math.floor(ago / 60000)} min ago`;
    const d = new Date(t);
    const today = new Date(Cali.now());
    const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    return d.toDateString() === today.toDateString() ? `today ${hm}` : `${d.getDate()} ${MONTHS[d.getMonth()]}, ${hm}`;
  }

  // ── the way in ────────────────────────────────────────────────────
  // The gear sits right after the day screen's 'topbar' holder, so after the timer's buttons and before Finish (screen
  // 2). It is kept there, not put in through Cali.slot, because tests/test_core.py expects that holder to hold only
  // its own probe nodes; an observer puts it back whenever the day screen is drawn again.
  const gear = document.createElement('button');
  gear.type = 'button';
  gear.className = 'iconbtn settings-open';
  gear.setAttribute('aria-label', 'Settings');
  gear.innerHTML = icon('gear');
  gear.addEventListener('click', () => Cali.go('settings'));
  function placeGear() {
    const holder = document.querySelector('#app [data-screen="day"] [data-slot="topbar"]');
    if (!holder) { if (gear.isConnected) gear.remove(); return; }
    if (gear.previousElementSibling !== holder) holder.after(gear);
  }
  new MutationObserver(placeGear).observe(document.getElementById('app'), { childList: true, subtree: true });
  placeGear();

  // ── markup ────────────────────────────────────────────────────────
  function stepper(key, label) {
    return `<div class="settings-row" role="group" aria-labelledby="settings-l-${key}">` +
      `<span class="settings-t" id="settings-l-${key}">${esc(label)}</span><div class="settings-step">` +
      `<button type="button" data-key="${key}" data-step="-${REST_STEP}" aria-label="${esc(label)} ${REST_STEP} seconds shorter"><span>${icon('minus')}</span></button>` +
      `<span class="num" data-show="${key}" aria-live="polite"></span>` +
      `<button type="button" data-key="${key}" data-step="${REST_STEP}" aria-label="${esc(label)} ${REST_STEP} seconds longer"><span>${icon('plus')}</span></button>` +
      '</div></div>';
  }
  function toggle(key, label, sub) {
    return `<button type="button" class="settings-row" role="switch" aria-checked="false" data-key="${key}">` +
      `<span class="settings-t"><span data-label="${key}">${esc(label)}</span>${sub ? `<small>${esc(sub)}</small>` : ''}</span>` +
      '<span class="settings-tog" aria-hidden="true"></span></button>';
  }
  function seg(key, label, sub, options, groupLabel) {
    return `<div class="settings-row"><span class="settings-t">${esc(label)}${sub ? `<small>${esc(sub)}</small>` : ''}</span>` +
      `<div class="settings-seg" role="group" aria-label="${esc(groupLabel)}">` +
      options.map(([value, text]) => `<button type="button" data-key="${key}" data-val="${esc(value)}" aria-pressed="false">${icon('check')}${esc(text)}</button>`).join('') +
      '</div></div>';
  }

  function markup() {
    return '<header class="bar2"><button type="button" class="iconbtn" data-act="back" aria-label="Back">' + icon('back') +
      '</button><h2>Settings</h2></header><div class="settings-body">' +
      '<div class="settings-head"><h3 class="settings-eyebrow">Rest and alerts</h3>' +
      `<button type="button" class="ghost" data-act="test">${icon('bell')}Test alert</button></div>` +
      '<div class="group settings-first">' +
        stepper('restPair', 'Pair rest') +
        stepper('restExercise', 'Rest between exercises') +
        toggle('restAfterLog', 'Start rest after a log') +
        toggle('headsUp', 'Heads-up 10 s before the end', 'Time to get set before the beep') +
        toggle('vibrate', 'Vibrate') +
        toggle('sound', 'Sound') +
        '<div class="settings-row"><span class="settings-t">Notifications<small>For the alert while the screen is off</small></span>' +
        '<span data-perm></span></div>' +
      '</div>' +
      `<p class="settings-help" data-perm-help hidden>${esc(PERMISSION_HELP)}</p>` +
      '<h3 class="settings-eyebrow settings-section">Workout</h3>' +
      '<div class="group">' +
        toggle('keepAwake', 'Keep screen awake', 'While a workout runs') +
        seg('loadStep', 'Load step', 'For new exercises', LOAD_STEPS.map(v => [String(v), String(v)]), 'Default load step in kg') +
        seg('theme', 'Theme', '', THEMES, 'Theme') +
      '</div>' +
      '<h3 class="settings-eyebrow settings-section">Data</h3>' +
      '<div class="group">' +
        '<button type="button" class="settings-row" data-act="github" aria-expanded="false" aria-controls="settings-gh">' +
          `${icon('cloud')}<span class="settings-t">GitHub sync<small data-sync-repo></small></span><span class="pill" data-sync-pill></span></button>` +
        '<div class="settings-gh" id="settings-gh" hidden>' +
          '<p class="settings-gh-detail" data-sync-detail role="status"></p>' +
          '<div class="settings-gh-form" data-sync-form>' +
            '<label for="settings-token">Token</label>' +
            '<input id="settings-token" type="password" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="github_pat_…">' +
            '<p class="settings-gh-note">A fine-grained token with Contents: Read and write on Estaed/Calisthenics-Data. It stays on this phone and never goes into the log or a backup.</p>' +
            '<button type="button" class="btn primary" data-act="connect">Connect</button>' +
          '</div>' +
          '<div class="settings-gh-actions" data-sync-actions>' +
            '<button type="button" class="btn secondary" data-act="syncnow">Sync now</button>' +
            '<button type="button" class="btn settings-outline-danger" data-act="disconnect">Disconnect</button>' +
          '</div>' +
        '</div>' +
        `<button type="button" class="settings-row" data-act="download">${icon('download')}<span class="settings-t">Download backup<small>JSON, all weeks</small></span></button>` +
        `<button type="button" class="settings-row" data-act="restore">${icon('upload')}<span class="settings-t">Restore from backup<small>A file this app saved</small></span></button>` +
        '<input type="file" accept=".json,application/json" data-restore hidden>' +
      '</div>' +
      '</div>';
  }

  // ── painting the values in place (a redraw would drop a half-typed token) ──
  function syncView(s) {
    if (!s) return { word: 'Off', err: false, detail: 'Sync is not installed in this copy of the app.' };
    const last = s.lastSyncedAt ? ` Last sync ${when(s.lastSyncedAt)}.` : '';
    if (!s.configured) return { word: 'Off', err: false, detail: 'Add a token to keep this log in Estaed/Calisthenics-Data. Without one the log stays on this phone only; download a backup now and then.' };
    if (s.problem) return { word: 'Error', err: true, detail: s.problem };
    if (s.conflict) return { word: 'Choose', err: true, detail: 'This phone and GitHub both changed: choose which log to keep.' };
    if (s.running) return { word: 'Syncing', err: false, detail: 'Syncing with GitHub…' };
    if (!s.online) return { word: 'Offline', err: false, detail: `Offline. The log is safe on this phone and goes to GitHub once it is online.${last}` };
    if (s.paused) return { word: 'Paused', err: false, detail: `Paused after a conflict. Tap Sync now to choose again.${last}` };
    if (s.lastError) return { word: 'Error', err: true, detail: s.lastError };
    if (s.dirty && !s.due) return { word: 'Waiting', err: false, detail: `New changes go to GitHub when you tap Done after a workout.${last}` };
    if (s.dirty) return { word: 'Pending', err: false, detail: `Changes are due to go to GitHub.${last}` };
    return { word: 'Synced', err: false, detail: s.lastSyncedAt ? `Synced. Last sync ${when(s.lastSyncedAt)}.` : 'Connected.' };
  }

  function paint(root) {
    const all = Cali.settings.all();
    for (const key of ['restPair', 'restExercise']) {
      root.querySelector(`[data-show="${key}"]`).textContent = clock(all[key]);
      root.querySelector(`[data-key="${key}"][data-step^="-"]`).disabled = all[key] - REST_STEP < REST_MIN;
      root.querySelector(`[data-key="${key}"]:not([data-step^="-"])`).disabled = all[key] + REST_STEP > Math.max(REST_MAX, all[key]);
    }
    for (const b of root.querySelectorAll('[role="switch"][data-key]')) {
      const v = all[b.dataset.key];
      b.setAttribute('aria-checked', String(b.dataset.key === 'headsUp' ? v > 0 : v === true));
    }
    root.querySelector('[data-label="headsUp"]').textContent = `Heads-up ${all.headsUp > 0 ? all.headsUp : 10} s before the end`;
    for (const b of root.querySelectorAll('.settings-seg [data-key]')) {
      const v = all[b.dataset.key];
      b.setAttribute('aria-pressed', String(b.dataset.key === 'theme' ? v === b.dataset.val : v === Number(b.dataset.val)));
    }

    const p = permission();
    root.querySelector('[data-perm]').innerHTML = p === 'granted' ? '<span class="pill">Allowed</span>'
      : p === 'unsupported' ? '<span class="pill">Not available</span>'
      : '<button type="button" class="settings-act" data-act="allow">Allow</button>';
    root.querySelector('[data-perm-help]').hidden = p === 'granted';

    const s = sync() ? sync().status() : null;
    const v = syncView(s);
    root.querySelector('[data-sync-repo]').textContent = s ? s.repo : 'Estaed/Calisthenics-Data';
    const pill = root.querySelector('[data-sync-pill]');
    pill.textContent = v.word;
    pill.classList.toggle('settings-pill-err', v.err);
    const detail = root.querySelector('[data-sync-detail]');
    detail.innerHTML = (v.err ? icon('alert') : '') + `<span>${esc(v.detail)}</span>`;
    detail.classList.toggle('settings-err', v.err);
    root.querySelector('[data-sync-form]').hidden = !s || s.configured;
    root.querySelector('[data-sync-actions]').hidden = !s || !s.configured;
    root.querySelector('[data-act="syncnow"]').disabled = Boolean(s && s.running);
  }

  // ── small pieces of feedback ──────────────────────────────────────
  let snackTimer = 0;
  function snack(text) {
    let el = document.querySelector('.settings-snack');
    if (!el) {
      el = document.createElement('div');
      el.className = 'snack settings-snack';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.innerHTML = `<span>${esc(text)}</span>`;
    clearTimeout(snackTimer);
    snackTimer = setTimeout(() => el.remove(), 4000);
  }

  // A confirm dialog: title, one sentence, the safe action and the chosen one. Resolves true for the chosen one.
  function ask({ title, text, ok, danger }) {
    return new Promise(resolve => {
      const d = document.createElement('dialog');
      d.className = 'settings-dialog';
      d.setAttribute('aria-labelledby', 'settings-dialog-title');
      d.innerHTML = `<h2 id="settings-dialog-title">${esc(title)}</h2><p>${esc(text)}</p><div class="settings-dialog-actions">` +
        '<button type="button" class="btn secondary" data-answer="no">Cancel</button>' +
        `<button type="button" class="btn ${danger ? 'settings-danger' : 'primary'}" data-answer="yes">${esc(ok)}</button></div>`;
      const done = yes => { if (d.open && typeof d.close === 'function') d.close(); d.remove(); resolve(yes); };
      d.addEventListener('click', e => { const b = e.target.closest('[data-answer]'); if (b) done(b.dataset.answer === 'yes'); });
      d.addEventListener('cancel', e => { e.preventDefault(); done(false); });
      document.body.appendChild(d);
      if (typeof d.showModal === 'function') d.showModal(); else d.setAttribute('open', '');
    });
  }

  function set(key, value) {
    try { Cali.settings.set(key, value); } catch (e) { snack(Cali.problem() || e.message); }
  }

  // ── backup ────────────────────────────────────────────────────────
  function download() {
    if (Cali.problem()) { snack(`No backup made. ${Cali.problem()}`); return; }
    const text = JSON.stringify(Cali.doc(), null, 1);
    const d = new Date(Cali.now());
    const name = `calisthenics-backup-${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}.json`;
    const href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = href;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(href), 60000);
    snack(`Saved ${name}`);   // one line at 360 px; "Backup saved: …" broke the name over two
  }

  function counts(d) {
    try {
      let sets = 0;
      for (const w of d.weeks) for (const day of Object.values(w.days)) for (const ex of Object.values(day.exercises)) for (const s of ex.sets) if (s) sets++;
      return { week: d.weeks[d.weeks.length - 1].n, sets };
    } catch (e) { return null; }
  }

  async function restore(file) {
    let data;
    try { data = JSON.parse(await file.text()); } catch (e) { snack('That file is not JSON; nothing was changed.'); return; }
    if (!isObj(data) || data._version !== 5) {
      snack(isObj(data) && typeof data._version === 'number' && data._version < 5
        ? 'That is a backup of the old app (version 4); only this app\'s backups can be restored. Nothing was changed.'
        : 'That file is not a backup of this app (no _version 5); nothing was changed.');
      return;
    }
    const c = counts(data);
    const what = c ? ` (week ${c.week}, ${c.sets} ${c.sets === 1 ? 'set' : 'sets'} logged${data.updatedAt ? `, saved ${when(data.updatedAt)}` : ''})` : '';
    const yes = await ask({
      title: 'Restore this backup?',
      text: `The log on this phone is replaced by the backup${what}. Download a backup first if you may want the current log back.`,
      ok: 'Restore', danger: true,
    });
    if (!yes) return;
    try {
      Cali.replace(data, { why: 'restore', dirty: true });
      snack('Backup restored.');
    } catch (e) {
      snack(`The backup could not be used (${e.message}); nothing was changed.`);
    }
  }

  // ── the screen ────────────────────────────────────────────────────
  let off = [];

  async function act(root, b) {
    const name = b.dataset.act;
    if (name === 'back') { Cali.back(); return; }
    if (name === 'test') { Cali.alert('test'); return; }
    if (name === 'allow') {
      try { await Cali.alert.requestPermission(); } catch (e) { /* the state below says what holds */ }
      paint(root);
      return;
    }
    if (name === 'github') {
      const panel = root.querySelector('#settings-gh');
      panel.hidden = !panel.hidden;
      b.setAttribute('aria-expanded', String(!panel.hidden));
      return;
    }
    if (name === 'connect') {
      const input = root.querySelector('#settings-token');
      const value = input.value;
      if (!value.trim()) { snack('Paste a token first.'); input.focus(); return; }
      input.value = '';
      if (sync()) await sync().connect(value);
      return;
    }
    if (name === 'syncnow') { if (sync()) await sync().now({ manual: true }); return; }
    if (name === 'disconnect') {
      const yes = await ask({
        title: 'Disconnect GitHub?', ok: 'Disconnect',
        text: 'The token is removed from this phone. The log stays here and on GitHub; nothing is deleted.',
      });
      if (yes && sync()) sync().disconnect();
      return;
    }
    if (name === 'download') { download(); return; }
    if (name === 'restore') root.querySelector('[data-restore]').click();
  }

  Cali.route('settings', {
    render(root) {
      root.classList.add('settings');
      root.innerHTML = markup();
      root.addEventListener('click', e => {
        const b = e.target.closest('button');
        if (!b || !root.contains(b) || b.disabled) return;
        const key = b.dataset.key;
        if (key && b.dataset.step) {
          const v = Cali.settings.get(key) + Number(b.dataset.step);
          if (v >= REST_MIN) set(key, v);
        } else if (key && b.getAttribute('role') === 'switch') {
          set(key, key === 'headsUp' ? (Cali.settings.get(key) > 0 ? 0 : 10) : !Cali.settings.get(key));
        } else if (key && b.dataset.val !== undefined) {
          set(key, key === 'theme' ? b.dataset.val : Number(b.dataset.val));
        } else if (b.dataset.act) act(root, b);
      });
      root.querySelector('[data-restore]').addEventListener('change', e => {
        const file = e.target.files && e.target.files[0];
        e.target.value = '';
        if (file) restore(file);
      });
      root.querySelector('#settings-token').addEventListener('keydown', e => {
        if (e.key === 'Enter') act(root, root.querySelector('[data-act="connect"]'));
      });
      const repaint = () => paint(root);
      const onVisible = () => { if (document.visibilityState === 'visible') repaint(); };
      document.addEventListener('visibilitychange', onVisible);   // back from the browser's site settings
      off = [Cali.on('syncstatus', repaint), Cali.on('sync', repaint), () => document.removeEventListener('visibilitychange', onVisible)];
      paint(root);
    },
    update(root) { paint(root); },
    leave() {
      for (const f of off) f();
      off = [];
      for (const el of document.querySelectorAll('.settings-snack')) el.remove();
    },
  });
})();
