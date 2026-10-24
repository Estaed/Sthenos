/* Alerts in the service worker (Task-02), loaded by sw.js with importScripts('sw-alert.js'). Design:
   reports/2026-10-24-rest-alert-screen-off.md -> Recommended design. The page (app/alert.js) posts
   { type: 'cali-alert', op, kind, endAt, tag, title }:
     schedule  holds this event open with event.waitUntil until endAt (ms), then shows the notification and tells the open
               pages ('fired'). A later schedule under the same tag and kind replaces the wait. An end more than 30 s
               past or more than an hour ahead is not held: a worker lives about 5 min per event, and a page on a test
               clock sends times far from this worker's clock.
     show      the page's own timer reached the end while it was awake: show the notification now.
     cancel    drops every wait under tag and closes what is shown under it.
   One notification per end: data.id is tag, kind and endAt; shows run one at a time, and each first looks for its id
   among the notifications already shown, so the page's trigger and the worker's never show or ring twice. The
   notification carries the page's title, the tag, requireInteraction (it stays until tapped or cancelled) and renotify
   (a new end under the same tag rings again). Tapping it focuses the app's open window, or opens the app. */
(() => {
  'use strict';
  const AHEAD_MS = 60 * 60 * 1000;
  const STALE_MS = 30 * 1000;
  const waits = new Map();       // tag + kind -> { tag, endAt, stop }
  let queue = Promise.resolve(); // shows, one at a time
  const scope = self.registration.scope;
  const ours = url => url.startsWith(scope) && !url.startsWith(scope + 'legacy/');

  function show(m, by) {
    const run = async () => {
      if (self.Notification && self.Notification.permission !== 'granted') return;
      const id = `${m.tag}\n${m.kind}\n${m.endAt}`;
      const shown = await self.registration.getNotifications({ tag: m.tag });
      if (shown.some(n => n.data && n.data.id === id)) return;
      await self.registration.showNotification(String(m.title || 'Calisthenics'), {
        tag: m.tag, renotify: true, requireInteraction: true, icon: 'icon-192.png', timestamp: m.endAt,
        data: { app: 'cali-alert', id, kind: m.kind, endAt: m.endAt, by },
      });
    };
    queue = queue.then(run).catch(() => {});
    return queue;
  }

  async function tell(m) {
    for (const client of await self.clients.matchAll({ type: 'window', includeUncontrolled: true })) {
      if (ours(client.url)) client.postMessage({ type: 'cali-alert', op: 'fired', kind: m.kind, endAt: m.endAt, tag: m.tag });
    }
  }

  function hold(m) {
    const key = `${m.tag}\n${m.kind}`;
    if (waits.has(key)) waits.get(key).stop();
    const delay = m.endAt - Date.now();
    if (delay > AHEAD_MS || delay < -STALE_MS) return Promise.resolve();
    return new Promise(resolve => {
      let timer = 0;
      const w = {
        tag: m.tag, endAt: m.endAt,
        stop() { clearTimeout(timer); if (waits.get(key) === w) waits.delete(key); resolve(); },
      };
      timer = setTimeout(() => {
        if (waits.get(key) === w) waits.delete(key);
        show(m, 'worker').then(() => tell(m)).catch(() => {}).then(resolve);
      }, Math.max(0, delay));
      waits.set(key, w);
    });
  }

  async function drop(tag) {
    for (const w of [...waits.values()]) if (w.tag === tag) w.stop();
    await queue;
    for (const n of await self.registration.getNotifications({ tag })) if (n.data && n.data.app === 'cali-alert') n.close();
  }

  self.addEventListener('message', event => {
    const m = event.data;
    if (!m || m.type !== 'cali-alert' || typeof m.tag !== 'string' || !m.tag) return;
    const timed = typeof m.endAt === 'number' && Number.isFinite(m.endAt);
    if (m.op === 'schedule' && timed) event.waitUntil(hold(m));
    else if (m.op === 'show' && timed) {
      const w = waits.get(`${m.tag}\n${m.kind}`);
      if (w && w.endAt === m.endAt) w.stop();
      event.waitUntil(show(m, 'page'));
    } else if (m.op === 'cancel') event.waitUntil(drop(m.tag));
  });

  self.addEventListener('notificationclick', event => {
    const data = event.notification.data;
    if (!data || data.app !== 'cali-alert') return;
    event.notification.close();
    event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      const open = list.find(c => ours(c.url));
      return open ? open.focus() : self.clients.openWindow(scope);
    }));
  });
})();
