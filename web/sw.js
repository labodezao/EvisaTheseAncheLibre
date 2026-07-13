// Service worker : fonctionnement hors ligne, mais SANS jamais servir de code
// périmé. Stratégie « réseau d'abord » pour l'app shell (HTML/JS/CSS) : en
// ligne, l'utilisateur reçoit toujours la dernière version ; hors ligne, on
// sert la dernière copie mise en cache. C'est l'inverse de la stratégie
// « cache d'abord », qui gelait le code jusqu'à un double rechargement — la
// cause de « des valeurs s'affichent mais pas la courbe » après une mise à
// jour (mélange d'anciens et de nouveaux fichiers).
const CACHE = 'aal-shell-v5';

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
  'js/dsp/nsdf.js',
  'js/dsp/subspace.js',
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

// Réseau d'abord, repli sur le cache hors ligne. Le cache est rafraîchi à
// chaque réponse réseau réussie.
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return; // laisse passer l'externe
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(e.request).then((c) => c || caches.match(new URL('index.html', self.registration.scope).toString()))),
  );
});
