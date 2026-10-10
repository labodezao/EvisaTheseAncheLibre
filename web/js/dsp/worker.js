// Worker DSP : reçoit l'audio du AudioWorklet via un MessagePort dédié
// (sans passer par le thread principal) et renvoie les analyses au thread
// principal pour l'affichage.
//
// Mode dev (session de recherche) : le Worker garde aussi le son brut et
// chaque mesure, datés sur la MÊME horloge (le compteur d'échantillons du
// moteur). À l'export, la mesure du temps t correspond exactement à l'instant
// t du WAV. Session longue (60 min par défaut, 120 au plus, Ewen 07/10/2026) :
// rien ne s'accumule ici. Le son est converti en Int16 au fil de l'eau et
// rendu au thread principal par morceaux de MORCEAU_S secondes, avec les
// lignes du CSV de ces secondes (message devMorceau) ; la page les écrit hors
// de la mémoire vive (session-stockage.js).

import { Engine } from './engine.js';
import {
  MORCEAU_S, versInt16, rangeesTick, lignesCsv, lireEnteteWav, echantillonsWav,
} from '../session-format.js';

let engine = null;

// --- enregistrement de session (mode dev) ------------------------------------
let devMaxS = 3600;                 // durée maximale (s), réglée par la page
let devGen = 0;                     // numéro de la session (une nouvelle à chaque début)
let dev = null;                     // { gen, index, start, n, maxN, pcm, fill, csv, ticks, ticksM, full }

function devStart() {
  const sr = engine.sr;
  dev = { gen: ++devGen, index: 0, start: engine.samplesTotal, n: 0, maxN: Math.round(devMaxS * sr),
    pcm: new Int16Array(MORCEAU_S * sr), fill: 0, csv: [], ticks: 0, ticksM: 0, full: false };
}

// Rend le morceau en cours (son et lignes du CSV), s'il y a quelque chose.
function devFlush() {
  if (!dev || (dev.fill === 0 && dev.csv.length === 0)) return;
  const pcm = dev.fill === dev.pcm.length ? dev.pcm : dev.pcm.slice(0, dev.fill);
  self.postMessage({ type: 'devMorceau', gen: dev.gen, index: dev.index, sr: engine.sr, pcm,
    csv: dev.csv.join(''), mesures: dev.ticksM, cfg: dev.index === 0 ? engine.cfg : undefined,
    n: dev.n, ticks: dev.ticks, full: dev.full }, [pcm.buffer]);
  dev.index++;
  dev.pcm = new Int16Array(MORCEAU_S * engine.sr);
  dev.fill = 0; dev.csv = []; dev.ticksM = 0;
}

function devAppend(chunk) {
  if (!dev || dev.full) return;
  let i = 0;
  while (i < chunk.length && !dev.full) {
    const n = Math.min(chunk.length - i, dev.pcm.length - dev.fill, dev.maxN - dev.n);
    versInt16(chunk.subarray(i, i + n), dev.pcm, dev.fill);
    dev.fill += n; dev.n += n; i += n;
    if (dev.n >= dev.maxN) dev.full = true;
    if (dev.fill === dev.pcm.length || dev.full) devFlush();
  }
}

// Une ligne par anche et par mesure : ce qu'il faut pour rejouer l'analyse.
function devTick(r) {
  if (!dev || dev.full) return;
  const t = r.time - dev.start / engine.sr;
  dev.csv.push(lignesCsv({ t, midi: r.playedMidi, level: r.level, quiet: r.quiet ? 1 : 0, rows: rangeesTick(r) },
    engine.cfg?.transpose || 0));
  dev.ticks++; dev.ticksM++;
}

function devStatus() {
  return dev ? { seconds: dev.n / engine.sr, ticks: dev.ticks, full: dev.full, maxS: devMaxS, morceaux: dev.index } : null;
}

function onChunk(chunk) {
  if (!engine) return;
  devAppend(chunk);
  const t0 = performance.now();
  const result = engine.process(chunk);
  if (result) {
    // Charge DSP : temps de calcul rapporté à la période d'analyse.
    result.dspMs = performance.now() - t0;
    devTick(result);
    if (dev) result.dev = devStatus();
    // Les spectres sont transférés (zéro copie) plutôt que clonés.
    const transfer = [];
    if (result.coarseSpectrum) transfer.push(result.coarseSpectrum.buffer);
    for (const g of result.groups) if (g.spectrum) transfer.push(g.spectrum.buffer);
    self.postMessage(result, transfer);
  }
}

// Micro lu DIRECTEMENT (MediaStreamTrackProcessor), à l'horloge du micro.
//
// Par le chemin Web Audio (AudioContext → AudioWorklet), Chrome fait passer
// le micro dans un rééchantillonneur qui rattrape la dérive entre l'horloge
// du micro et celle de la sortie son, en changeant son rapport par à-coups.
// Mesuré sur un enregistrement d'Ewen (téléphone, 24/09/2026) : TOUT le son
// — la note, mais aussi le ronflement du secteur à 50 Hz, qui lui ne bouge
// jamais — sautait de ±6 ¢ toutes les ~2 s, même dans les silences. C'était
// les « signaux carrés » de la courbe : l'anche, elle, ne sautait pas.
// Ici, chaque bloc arrive tel que le micro l'a échantillonné.
async function readStream(readable) {
  const reader = readable.getReader();
  let buf = new Float32Array(0), fill = 0;
  const HOPS = 512;
  for (;;) {
    const { value: ad, done } = await reader.read();
    if (done) break;
    try {
      if (!engine || engine.sr !== ad.sampleRate) {
        const cfg = engine ? engine.cfg : pendingCfg;
        engine = new Engine(ad.sampleRate, cfg || {});
        if (dev || pendingDev) devStart();
        self.postMessage({ type: 'capture', direct: true, sampleRate: ad.sampleRate, format: ad.format });
      }
      const n = ad.numberOfFrames;
      if (buf.length < fill + n) { const b = new Float32Array(2 * (fill + n)); b.set(buf.subarray(0, fill)); buf = b; }
      const plane = buf.subarray(fill, fill + n);
      if (/^f32/.test(ad.format)) {
        ad.copyTo(plane, { planeIndex: 0, format: 'f32-planar' });
      } else {
        const tmp = new Int16Array(n * (ad.format.endsWith('planar') ? 1 : ad.numberOfChannels));
        ad.copyTo(tmp, { planeIndex: 0 });
        const step = ad.format.endsWith('planar') ? 1 : ad.numberOfChannels;
        for (let i = 0; i < n; i++) plane[i] = tmp[i * step] / 32768;
      }
      fill += n;
      let o = 0;
      for (; o + HOPS <= fill; o += HOPS) onChunk(buf.slice(o, o + HOPS));
      buf.copyWithin(0, o, fill); fill -= o;
    } finally {
      ad.close();
    }
  }
}

// Un enregistrement (WAV) rejoué à la place du micro, lu par morceaux : un
// WAV de 60 min (345 Mo) n'est jamais chargé en entier (decodeAudioData en
// faisait 691 Mo de Float32). Premier canal, à sa fréquence d'échantillonnage
// (sans rééchantillonnage), au rythme du temps réel × `vitesse`.
let fichierEnCours = 0;
async function lireFichier(blob, vitesse = 1) {
  const jeton = ++fichierEnCours;
  const tete = new Uint8Array(await blob.slice(0, Math.min(blob.size, 1 << 16)).arrayBuffer());
  const info = lireEnteteWav(tete, blob.size);
  if (!info) throw new Error('WAV illisible'); // interne
  engine = new Engine(info.sr, pendingCfg || {});
  if (dev || pendingDev) devStart();
  self.postMessage({ type: 'capture', direct: false, sampleRate: info.sr, fichier: true, duree: info.n / info.sr });
  const HOPS = 512;
  const parLecture = Math.max(1, Math.round(info.sr / 2)) * info.bloc; // une demi-seconde à la fois
  let pos = info.debut;
  const fin = info.debut + info.taille;
  let file = new Float32Array(0), o = 0;   // échantillons lus, pas encore donnés au moteur
  let donnes = 0;                          // échantillons donnés au moteur
  const t0 = performance.now();
  const v = Math.min(64, Math.max(0.25, Number(vitesse) || 1));
  while (jeton === fichierEnCours) {
    if (file.length - o < HOPS) {
      if (pos >= fin) break;
      const b = Math.min(parLecture, fin - pos);
      const x = echantillonsWav(new Uint8Array(await blob.slice(pos, pos + b).arrayBuffer()), info);
      pos += b;
      const reste = file.subarray(o);
      file = new Float32Array(reste.length + x.length);
      file.set(reste); file.set(x, reste.length); o = 0;
      continue;
    }
    // Au rythme du temps réel : pas plus que le temps écoulé (+ 50 ms).
    const permis = ((performance.now() - t0) / 1000 + 0.05) * info.sr * v;
    if (donnes + HOPS > permis) { await new Promise((ok) => setTimeout(ok, 10)); continue; }
    onChunk(file.slice(o, o + HOPS));
    o += HOPS; donnes += HOPS;
  }
  if (jeton === fichierEnCours) self.postMessage({ type: 'fichierFin', secondes: donnes / info.sr });
}

let pendingCfg = null, pendingDev = false;

// Fin de session : le morceau en cours, puis « fini » (les messages
// arrivent dans l'ordre : la page a tout reçu quand elle lit devFin).
function devFin(req) {
  const gen = dev?.gen ?? null;
  const full = !!dev?.full;
  devFlush();
  dev = null;
  self.postMessage({ type: 'devFin', gen, full, req });
}

self.onmessage = (e) => {
  const d = e.data;
  if (d.type === 'init') {
    engine = new Engine(d.sampleRate, d.cfg || {});
    pendingCfg = d.cfg || {}; pendingDev = !!d.dev;
    if (d.devMaxS > 0) devMaxS = d.devMaxS;
    if (d.dev) devStart();
    if (d.port) d.port.onmessage = (ev) => onChunk(ev.data);
  } else if (d.type === 'stream') {
    // Le moteur est recréé à la fréquence réelle du micro au premier bloc.
    engine = null;
    readStream(d.readable).catch((err) => self.postMessage({ type: 'capture', error: String(err) }));
  } else if (d.type === 'fichier') {
    lireFichier(d.blob, d.vitesse).catch((err) => self.postMessage({ type: 'capture', error: String(err?.message ?? err) }));
  } else if (d.type === 'config') {
    pendingCfg = { ...(pendingCfg || {}), ...d.cfg };
    engine?.configure(d.cfg);
  } else if (d.type === 'dev') {
    // { on, maxS } : marche ou arrêt, durée maximale (réduite si le disque
    // ne suffit pas). Arrêt : le morceau en cours part avant (devFin).
    if (d.maxS > 0) {
      devMaxS = d.maxS;
      if (dev) {
        dev.maxN = Math.round(devMaxS * engine.sr);
        if (dev.n >= dev.maxN && !dev.full) { dev.full = true; devFlush(); }
      }
    }
    pendingDev = !!d.on;
    if (d.on) { if (!dev && engine) devStart(); } else if (dev) devFin(null);
    self.postMessage({ type: 'devStatus', dev: devStatus() });
  } else if (d.type === 'devFlush') {
    // Export pendant l'enregistrement : le morceau en cours part tout de suite.
    devFlush();
    self.postMessage({ type: 'devFlushOk', req: d.req, gen: dev?.gen ?? null });
  } else if (d.type === 'devFin') {
    devFin(d.req);
  } else if (d.type === 'devClear') {
    // Effacer : la session en cours est abandonnée (la page l'efface), une
    // nouvelle commence.
    if (dev) { const gen = dev.gen; dev = null; self.postMessage({ type: 'devAbandon', gen }); devStart(); }
    self.postMessage({ type: 'devStatus', dev: devStatus() });
  }
};
