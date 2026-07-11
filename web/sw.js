// Service worker : mise en cache de l'app shell pour un fonctionnement hors
// ligne une fois l'accordeur visité. Chemins relatifs à la portée du worker
// (dossier contenant sw.js) — compatible avec un déploiement à la racine du
// domaine ou dans un sous-dossier (ex. GitHub Pages de projet).
const CACHE = 'aal-shell-v1';

const SHELL = [
  '.',
  'index.html',
  'aide.html',
  'manifest.json',
  'icon.svg',
  'css/style.css',
  'js/app.js',
  'js/music.js',
  'js/report.js',
  'js/capture-worklet.js',
  'js/dsp/fft.js',
  'js/dsp/coarse.js',
  'js/dsp/zoom.js',
  'js/dsp/engine.js',
  'js/dsp/worker.js',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(SHELL.map((p) => new URL(p, self.registration.scope).toString())))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

// Cache d'abord (précision hors ligne immédiate), avec repli réseau puis
// mise à jour silencieuse du cache pour la prochaine visite.
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const network = fetch(e.request).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      }).catch(() => cached);
      return cached || network;
    }),
  );
});
