/* Calisthenics service worker (scope: the app's folder). The app opens offline in the gym, and an online launch
   always gets the newest files. Every same-origin GET goes to the network first (revalidating past the HTTP cache,
   so a GitHub Pages deploy shows on the next launch) and falls back to this worker's own cache when offline or after
   3 s without an answer. Install stores the shell below plus every file in app/registry.js, so a new feature needs
   no edit here. legacy/ (the old app, with its own worker) is left to the network.
   Caches: CACHE is this release's; bump it on every release (the orchestrator does at integration). Activate deletes
   only this app's older caches ('cali-app-*') and 'cali-v4', the cache of the old app's worker that held this scope
   before the old app moved to legacy/. Every other cache on the origin (legacy's 'cali-legacy-*', Pantry's) stays. */
const CACHE = 'cali-app-v2';
const PREFIX = 'cali-app-';
const REPLACED = ['cali-v4'];
importScripts('app/registry.js');

const SHELL = [
  './', 'index.html', 'manifest.json', 'tokens.css', 'app/base.css', 'app/registry.js', 'app/default-program.js', 'app/core.js',
  'fonts/archivo.css', 'fonts/Archivo-latin.woff2', 'fonts/Archivo-latin-ext.woff2', 'fonts/Manrope.woff2',
  'icon-192.png', 'icon-512.png', 'favicon-32x32.png',
];
const WAIT_MS = 3000;
const SCOPE = new URL('./', self.location).href;
const LEGACY = SCOPE + 'legacy/';

self.addEventListener('install', event => {
  self.skipWaiting();
  const files = SHELL.concat(self.CALI_FEATURES || []);
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(files.map(f => new Request(f, { cache: 'reload' })))));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => (k.startsWith(PREFIX) && k !== CACHE) || REPLACED.includes(k)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.href.startsWith(LEGACY)) return;

  let saved = Promise.resolve();
  const network = fetch(request.mode === 'navigate' ? request.url : request, { cache: 'no-cache' }).then(response => {
    if (response.ok && response.type === 'basic') {
      const copy = response.clone();
      saved = caches.open(CACHE).then(cache => cache.put(request, copy));
    }
    return response;
  });
  const cached = () => caches.open(CACHE).then(cache => cache.match(request, { ignoreSearch: request.mode === 'navigate' })
    .then(hit => hit || (request.mode === 'navigate' ? cache.match('index.html') : undefined)));
  const slow = new Promise(resolve => setTimeout(resolve, WAIT_MS)).then(() => cached().then(hit => hit || network));

  event.respondWith(Promise.race([network, slow]).catch(() => cached().then(hit => hit || Response.error())));
  event.waitUntil(network.then(() => saved, () => undefined));
});
importScripts('sw-alert.js');
