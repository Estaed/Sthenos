/* GitHub sync (app/sync.js): keeps the v5 document in the private repo Estaed/Calisthenics-Data, file
   calisthenics-data.json, through the GitHub Contents API and a fine-grained token. Ported from the old app's sync
   (legacy/index.html, "SYNC (GitHub Contents API)"), with the push policy of Blueprint -> Rules -> Sync. Without a
   token nothing here sends a request: the app works fully on the phone, offline.

   The token lives only in 'cali.sync' (Cali.setSyncState): never in the document, a push, a backup or a log line.
   On the first open, when 'cali.sync' holds no token and the old app's cali_sync_config does, that token is copied
   once (read through Cali.readOnly; the old key is never written). Disconnecting later does not copy it again.

   When it talks to GitHub
     open                 pull: read the remote file and compare its sha with the last one this phone saw. A change
                          older than 12 h (dirtySince) is pushed then.
     dayDone, weekFinished, an edit to a finished day or week, an edit to a program (programs, activeProgram,
                          nextProgram): push at once.
     nothing else         a set logged mid-day waits for Done; timers and the page being hidden or shown never make
                          a change due. A push asked for above (or by Sync now) that failed (no signal in the gym) is
                          retried when the phone is back online, when the app is shown again, on the next open, or
                          from Sync now; a change due only by its 12 h age goes on an open alone, so a screen turned
                          off between sets never sends a half-done day.
   What it does with the remote file
     none                 creates it from this phone's document.
     sha = lastSha        pushes this phone's document when a push is due, else nothing.
     sha is this phone's  a push whose answer was lost, or the same document: taken as lastSha, then as above.
     changed, not dirty   adopted (Cali.replace, why 'pull'); a phone that has logged nothing adopts it too.
     changed, dirty       the conflict choice (a dialog): use this phone's (GitHub's history keeps the replaced one),
                          take GitHub's (replaces this phone's), or not now (sync pauses until the next open or Sync
                          now). Never a silent overwrite.
     not _version 5       never adopted. Above 5: sync stops with an error. Below 5 or none (the old app's v4 file):
                          copied byte for byte to archive/calisthenics-data-v4.json first, then replaced by this
                          phone's document; if the replace fails both files stay as they were and the next open
                          retries.
     not JSON             sync stops with an error; nothing is overwritten.
   A PUT that GitHub refuses as stale (409, 422) reads the remote once more and decides again.

   self.CaliSync (frozen), used by app/settings.js
     status()             { configured, online, running, paused, conflict, dirty, due, lastSyncedAt, lastError,
                            problem, repo, path }
     now({ manual })      one sync pass, single flight; manual also unpauses and makes a dirty change due. A Promise
                          that never rejects: errors land in status().lastError.
     connect(token)       stores the token and syncs (manual).  disconnect() removes the token and the remote marks.
   Emits Cali.emit('syncstatus', status()) whenever the status may have changed. */
(() => {
  'use strict';

  const OWNER = 'Estaed';
  const REPO = 'Calisthenics-Data';
  const BRANCH = 'main';
  const PATH = 'calisthenics-data.json';
  const ARCHIVE = 'archive/calisthenics-data-v4.json';
  const API = 'https://api.github.com';
  const PUSH_AFTER_MS = 12 * 60 * 60 * 1000;
  const VERSION = 5;
  const REPO_NOT_FOUND = 'Repository not found, or the token cannot reach it. In the token\'s settings, is ' +
    'Calisthenics-Data selected under Repository access?';
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const esc = Cali.esc;

  let running = null;    // the running pass (with its queued reruns); never rejects
  let rerun = false;
  let paused = false;    // "Not now" on a conflict: until the next open or a manual sync
  let conflict = null;   // { doc, sha, dialog } while the choice is open
  let requests = 0;      // due pushes asked for; a push that saw a newer request leaves pushDue set

  // ── state ─────────────────────────────────────────────────────────
  const st = () => Cali.syncState();
  const token = () => (typeof st().token === 'string' ? st().token : '');
  const configured = () => token() !== '';
  const online = () => navigator.onLine !== false;
  function due(s = st()) {
    if (s.dirty !== true) return false;
    if (s.pushDue === true) return true;
    const since = Date.parse(s.dirtySince);
    return Number.isFinite(since) && Cali.now() - since > PUSH_AFTER_MS;
  }

  function status() {
    const s = st();
    return {
      configured: configured(), online: online(), running: running !== null, paused, conflict: conflict !== null,
      dirty: s.dirty === true, due: due(s), lastSyncedAt: s.lastSyncedAt || null, lastError: s.lastError || null,
      problem: Cali.problem(), repo: `${OWNER}/${REPO}`, path: PATH,
    };
  }
  const notify = () => Cali.emit('syncstatus', status());
  function save(patch) { Cali.setSyncState(patch); notify(); }

  // ── GitHub Contents API ───────────────────────────────────────────
  function b64FromBytes(bytes) {
    let bin = '';
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  }
  const b64FromText = text => b64FromBytes(new TextEncoder().encode(text));
  const bytesFromB64 = b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const textFromB64 = b64 => new TextDecoder('utf-8').decode(bytesFromB64(b64));

  // GitHub's sha of a file is git's blob id: SHA-1 over "blob <size>\0" and the bytes. null where it cannot be made.
  async function blobSha(b64) {
    try {
      const bytes = bytesFromB64(b64);
      const head = new TextEncoder().encode(`blob ${bytes.length}\0`);
      const all = new Uint8Array(head.length + bytes.length);
      all.set(head);
      all.set(bytes, head.length);
      const hash = new Uint8Array(await crypto.subtle.digest('SHA-1', all));
      return [...hash].map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (e) { return null; }
  }

  const fileUrl = path => `${API}/repos/${OWNER}/${REPO}/contents/${path.split('/').map(encodeURIComponent).join('/')}`;
  const headers = extra => ({
    Authorization: `Bearer ${token()}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
    ...extra,
  });

  // A thrown fetch (offline, DNS, CORS) becomes a sentence the settings screen can show.
  async function safeFetch(url, opts) {
    try { return await fetch(url, { cache: 'no-store', ...opts }); } catch (e) {
      throw new Error('Could not reach GitHub (network error).');
    }
  }
  async function readJson(res) {
    try { return await res.json(); } catch (e) { throw new Error('GitHub sent an answer this app cannot read.'); }
  }
  // 401 and 403 mean the same on every Contents API call
  function authError(code) {
    if (code === 401) return new Error('The token is invalid or has expired.');
    if (code === 403) return new Error('The token may not read or write this repository: it needs Permissions → Contents → Read and write.');
    return null;
  }

  // { exists: false } or { exists: true, sha, b64 } (b64 = the file's bytes, whitespace removed)
  async function remoteGet(path, repoCheck) {
    const url = `${fileUrl(path)}?ref=${encodeURIComponent(BRANCH)}`;
    const res = await safeFetch(url, { headers: headers() });
    if (res.status === 404) {
      if (!repoCheck) return { exists: false };
      // ambiguous: a missing file, a missing repo, or a token that cannot see the repo
      const repo = await safeFetch(`${API}/repos/${OWNER}/${REPO}`, { headers: headers() });
      if (repo.status === 200) return { exists: false };
      if (repo.status === 404) throw new Error(REPO_NOT_FOUND);
      throw authError(repo.status) || new Error(`Could not read the data on GitHub (${repo.status}).`);
    }
    const auth = authError(res.status);
    if (auth) throw auth;
    if (!res.ok) throw new Error(`Could not read the data on GitHub (${res.status}).`);
    const json = await readJson(res);
    let b64 = typeof json.content === 'string' ? json.content.replace(/\s/g, '') : '';
    if (!b64 && json.size > 0) {
      // files over 1 MB come without inline content: fetch the raw bytes instead
      const raw = await safeFetch(url, { headers: headers({ Accept: 'application/vnd.github.raw+json' }) });
      const rawAuth = authError(raw.status);
      if (rawAuth) throw rawAuth;
      if (!raw.ok) throw new Error(`Could not read the data on GitHub (${raw.status}).`);
      b64 = b64FromBytes(new Uint8Array(await raw.arrayBuffer()));
    }
    return { exists: true, sha: json.sha, b64 };
  }

  async function remotePut(path, b64, sha, message) {
    const body = { message, content: b64, branch: BRANCH };
    if (sha) body.sha = sha;
    const res = await safeFetch(fileUrl(path), {
      method: 'PUT', headers: headers({ 'Content-Type': 'application/json' }), body: JSON.stringify(body),
    });
    if (res.status === 409 || res.status === 422) {
      const e = new Error('The file on GitHub changed meanwhile.');
      e.stale = true;
      throw e;
    }
    if (res.status === 404) throw new Error(REPO_NOT_FOUND);
    const auth = authError(res.status);
    if (auth) throw auth;
    if (!res.ok) throw new Error(`Could not write to GitHub (${res.status}).`);
    const json = await readJson(res);
    if (!json || !isObj(json.content) || typeof json.content.sha !== 'string') throw new Error('GitHub sent an answer this app cannot read.');
    return json.content.sha;
  }

  // ── the sync ──────────────────────────────────────────────────────
  const docB64 = () => b64FromText(JSON.stringify(Cali.doc(), null, 1));

  async function push(sha) {
    const upTo = Cali.changes();
    const asked = requests;
    const b64 = docB64();
    save({ pendingSha: await blobSha(b64) });   // known if the answer is lost and the write landed
    const newSha = await remotePut(PATH, b64, sha, `sync: phone ${Cali.iso()}`);
    Cali.markClean(upTo);
    save({ lastSha: newSha, pendingSha: null, lastSyncedAt: Cali.iso(), lastError: null, pushDue: requests !== asked });
  }

  function adopt(doc, sha) {
    try { Cali.replace(doc, { why: 'pull' }); } catch (e) {
      throw new Error(`The data on GitHub could not be read (${e.message}); nothing was changed.`);
    }
    Cali.markClean();
    save({ lastSha: sha, pendingSha: null, lastSyncedAt: Cali.iso(), lastError: null, pushDue: false });
  }

  // a phone that has logged nothing: one week, no set, no started or finished day, no body weight
  function pristine(d) {
    if (d.weeks.length !== 1 || d.body.length || d.weeks[0].finishedAt) return false;
    return Object.values(d.weeks[0].days).every(day => !day.startedAt && !day.finishedAt
      && Object.values(day.exercises).every(ex => ex.sets.every(s => s === null)));
  }

  // The old app's file is kept byte for byte before this phone's document takes its place.
  async function archiveAndReplace(remote) {
    const kept = await remoteGet(ARCHIVE, false);
    if (!kept.exists || kept.b64 !== remote.b64) {
      await remotePut(ARCHIVE, remote.b64, kept.exists ? kept.sha : null, 'archive: the v4 data, kept before the v5 app replaced it');
    }
    await push(remote.sha);
  }

  async function attempt() {
    if (Cali.problem()) throw new Error(`Sync is off: ${Cali.problem()}`);
    const remote = await remoteGet(PATH, true);
    let s = st();
    if (!remote.exists) { await push(null); return; }
    if (remote.sha !== s.lastSha && (remote.sha === s.pendingSha || remote.sha === await blobSha(docB64()))) {
      save({ lastSha: remote.sha, pendingSha: null, lastSyncedAt: Cali.iso(), lastError: null });
      if (remote.b64 === docB64()) Cali.markClean(Cali.changes());
    }
    s = st();   // read again after the await above: a set logged meanwhile must count as dirty below
    if (remote.sha === s.lastSha) {
      if (due(s)) await push(remote.sha);
      else if (s.lastError) save({ lastError: null });
      return;
    }
    let data;
    try { data = JSON.parse(textFromB64(remote.b64)); } catch (e) { data = undefined; }
    if (!isObj(data)) throw new Error('The file on GitHub is not valid JSON; it was not overwritten.');
    if (typeof data._version === 'number' && data._version > VERSION) {
      throw new Error('GitHub holds data from a newer version of this app; reload the app to update it.');
    }
    if (data._version !== VERSION) { await archiveAndReplace(remote); return; }
    if (s.lastSha ? s.dirty !== true : pristine(Cali.doc())) { adopt(data, remote.sha); return; }
    openConflict(data, remote.sha);
  }

  // at most two passes: a stale PUT reads the remote once more
  async function attemptTwice() {
    for (let pass = 1; ; pass++) {
      try { await attempt(); return; } catch (e) { if (!(e && e.stale) || pass === 2) throw e; }
    }
  }

  function failed(e) {
    const message = e && e.message ? e.message : 'Sync failed.';
    save({ lastError: message });
    console.warn('Cali sync: ' + message);
  }

  async function loop() {
    do {
      rerun = false;
      try { await attemptTwice(); } catch (e) { failed(e); }
    } while (rerun && !paused && !conflict);
  }

  // Runs job as the one sync in flight. The clean-up is chained, so it runs after `running` holds the promise even
  // when job finishes without waiting for anything.
  function fly(job, after) {
    running = job().catch(failed).finally(() => {
      running = null;
      rerun = false;
      notify();
      if (after) after();
    });
    notify();
    return running;
  }

  // Single flight. The Promise never rejects; errors land in the state's lastError.
  function now({ manual = false } = {}) {
    if (manual) {
      paused = false;
      if (configured() && Cali.dirty()) save({ pushDue: true });
    }
    if (!configured() || !online() || conflict) { notify(); return running || Promise.resolve(); }
    if (running) { rerun = true; return running; }
    if (paused) { notify(); return Promise.resolve(); }
    return fly(loop);
  }

  function requestPush() {
    if (!configured()) return;
    requests++;
    save({ pushDue: true });
    now();
  }

  // ── what makes a push due at once ─────────────────────────────────
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  function urgent(c) {
    if (!c || !c.dirty || !c.prev || !c.doc) return false;
    if (c.why === 'log') {
      const w = c.doc.weeks.find(x => x.n === c.detail.week);
      const day = w && w.days[c.detail.dayId];
      return Boolean(w && (w.finishedAt || (day && day.finishedAt)));
    }
    if (!same(c.prev.programs, c.doc.programs) || c.prev.activeProgram !== c.doc.activeProgram
      || c.prev.nextProgram !== c.doc.nextProgram) return true;
    for (const pw of c.prev.weeks) {
      const w = c.doc.weeks.find(x => x.n === pw.n);
      if (pw.finishedAt && !same(pw, w)) return true;
      for (const [dayId, day] of Object.entries(pw.days)) {
        if (day.finishedAt && !same(day, w && w.days[dayId])) return true;
      }
    }
    return false;
  }

  // ── the conflict choice ───────────────────────────────────────────
  const pad = n => String(n).padStart(2, '0');
  function when(isoText) {
    const d = new Date(isoText);
    if (Number.isNaN(d.getTime())) return 'unknown';
    return `${d.getDate()} ${MONTHS[d.getMonth()]}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  function describe(d) {
    try {
      let sets = 0;
      for (const w of d.weeks) for (const day of Object.values(w.days)) for (const ex of Object.values(day.exercises)) for (const s of ex.sets) if (s) sets++;
      const last = d.weeks[d.weeks.length - 1];
      return { updated: d.updatedAt ? when(d.updatedAt) : 'unknown', week: last ? last.n : '–', sets };
    } catch (e) { return { updated: 'unknown', week: '–', sets: '–' }; }
  }
  function side(title, d) {
    const x = describe(d);
    return `<div class="sync-side"><b>${esc(title)}</b><span>Updated ${esc(x.updated)}</span><span>Week ${esc(x.week)}</span>` +
      `<span>${esc(x.sets)} ${x.sets === 1 ? 'set' : 'sets'} logged</span></div>`;
  }

  function openConflict(doc, sha) {
    const dialog = document.createElement('dialog');
    dialog.className = 'sync-dialog';
    dialog.setAttribute('aria-labelledby', 'sync-conflict-title');
    dialog.innerHTML = '<h2 id="sync-conflict-title">Sync conflict</h2>' +
      '<p>This phone and GitHub both changed since the last sync. Keep one; the other is replaced. GitHub keeps the ' +
      'replaced version in its history, this phone does not.</p>' +
      `<div class="sync-sides">${side('This phone', Cali.doc())}${side('GitHub', doc)}</div>` +
      '<div class="sync-actions"><button type="button" class="btn primary" data-choice="local">Use this phone\'s</button>' +
      '<button type="button" class="btn secondary" data-choice="remote">Take GitHub\'s</button>' +
      '<button type="button" class="ghost" data-choice="later">Not now</button></div>';
    dialog.addEventListener('click', e => {
      const b = e.target.closest('[data-choice]');
      if (b) choose(b.dataset.choice);
    });
    // no closing by the backdrop: a choice is needed; Esc or the back gesture means "Not now"
    dialog.addEventListener('cancel', e => { e.preventDefault(); choose('later'); });
    conflict = { doc, sha, dialog };
    document.body.appendChild(dialog);
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
    notify();
  }

  function choose(choice) {
    const c = conflict;
    if (!c) return;
    conflict = null;
    if (c.dialog.open && typeof c.dialog.close === 'function') c.dialog.close();
    c.dialog.remove();
    if (choice === 'later') { paused = true; notify(); return; }
    let again = false;
    fly(async () => {
      try {
        if (choice === 'local') await push(c.sha); else adopt(c.doc, c.sha);
      } catch (e) {
        again = Boolean(e && e.stale);   // GitHub changed once more: read it and ask again
        throw e;
      }
    }, () => { if (again) now(); });
  }

  // ── token ─────────────────────────────────────────────────────────
  function copyOldToken() {
    const s = st();
    if (s.legacyChecked || (typeof s.token === 'string' && s.token)) return;
    let old = null;
    try { old = JSON.parse(Cali.readOnly('cali_sync_config') || 'null'); } catch (e) { old = null; }
    const t = isObj(old) && typeof old.token === 'string' ? old.token.trim() : '';
    Cali.setSyncState(t ? { token: t, legacyChecked: true } : { legacyChecked: true });
  }

  function connect(value) {
    const t = String(value || '').trim();
    if (!t) { save({ lastError: 'Paste a token first.' }); return Promise.resolve(); }
    save({ token: t, lastError: null, legacyChecked: true });
    return now({ manual: true });
  }

  function disconnect() {
    if (conflict) { conflict.dialog.remove(); conflict = null; }
    paused = false;
    save({ token: '', lastSha: null, pendingSha: null, lastSyncedAt: null, lastError: null, pushDue: false, legacyChecked: true });
  }

  // ── triggers ──────────────────────────────────────────────────────
  Cali.on('dayDone', requestPush);
  Cali.on('weekFinished', requestPush);
  Cali.on('change', c => { if (urgent(c)) requestPush(); });
  // only a push already asked for (pushDue); the 12 h rule belongs to an open
  const retryDue = () => { const s = st(); if (configured() && s.dirty === true && s.pushDue === true) now(); else notify(); };
  window.addEventListener('online', retryDue);
  window.addEventListener('offline', notify);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') retryDue(); });

  self.CaliSync = Object.freeze({ status, now, connect, disconnect });

  copyOldToken();
  if (configured()) now();   // pull on open
})();
