// Worker DSP : reçoit l'audio du AudioWorklet via un MessagePort dédié
// (sans passer par le thread principal) et renvoie les analyses au thread
// principal pour l'affichage.
//
// Mode dev : le Worker garde aussi, en mémoire, le son brut et chaque mesure,
// datés sur la MÊME horloge (le compteur d'échantillons du moteur). À
// l'export, la mesure du temps t correspond exactement à l'instant t du WAV.

import { Engine } from './engine.js';

let engine = null;

// --- enregistrement de session (mode dev) ------------------------------------
const DEV_MAX_S = 600;              // 10 min : ~58 Mo en 16 bits à 48 kHz
let dev = null;                     // { chunks: Int16Array[], n, start, ticks: [] }

function devStart() {
  dev = { chunks: [], n: 0, start: engine ? engine.samplesTotal : 0, ticks: [], full: false };
}

function devAppend(chunk) {
  if (!dev || dev.full) return;
  if (dev.n >= DEV_MAX_S * engine.sr) { dev.full = true; return; }
  const pcm = new Int16Array(chunk.length);
  for (let i = 0; i < chunk.length; i++) {
    const s = Math.max(-1, Math.min(1, chunk[i]));
    pcm[i] = s < 0 ? s * 32768 : s * 32767;
  }
  dev.chunks.push(pcm);
  dev.n += chunk.length;
}

// Une ligne par anche et par mesure : ce qu'il faut pour rejouer l'analyse.
function devTick(r) {
  if (!dev || dev.full) return;
  const t = r.time - dev.start / engine.sr;
  const rows = [];
  for (const g of r.groups) {
    if (g.isSub) continue;
    for (const v of g.voices) {
      const p = {};
      if (g.partials) for (const k of Object.keys(g.partials)) {
        const f = g.partials[k]?.[v.def.id];
        if (f != null) p[k] = f;
      }
      rows.push({
        g: g.key, id: v.def.id, label: v.def.label ?? '', harm: g.isHarmonic ? 1 : 0,
        k: g.kTrack, target: v.target, f: v.tracked ? v.fMeas : null,
        c: v.tracked ? v.dTargetCents : null, amp: v.amp ?? 0,
        merged: v.merged ? 1 : 0, coarse: v.coarse ? 1 : 0, held: v.held ? 1 : 0,
        W: g.W, srd: g.srd, fill: g.fill, p,
      });
    }
  }
  dev.ticks.push({ t, midi: r.playedMidi, level: r.level, quiet: r.quiet ? 1 : 0, rows });
}

function devStatus() {
  return dev ? { seconds: dev.n / engine.sr, ticks: dev.ticks.length, full: dev.full, maxS: DEV_MAX_S } : null;
}

self.onmessage = (e) => {
  const d = e.data;
  if (d.type === 'init') {
    engine = new Engine(d.sampleRate, d.cfg || {});
    if (d.dev) devStart();
    if (d.port) {
      d.port.onmessage = (ev) => {
        if (!engine) return;
        devAppend(ev.data);
        const t0 = performance.now();
        const result = engine.process(ev.data);
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
      };
    }
  } else if (d.type === 'config' && engine) {
    engine.configure(d.cfg);
  } else if (d.type === 'dev') {
    if (d.on) { if (!dev) devStart(); } else dev = null;
    self.postMessage({ type: 'devStatus', dev: devStatus() });
  } else if (d.type === 'devClear') {
    if (dev) devStart();
    self.postMessage({ type: 'devStatus', dev: devStatus() });
  } else if (d.type === 'devExport') {
    if (!dev || !engine) { self.postMessage({ type: 'devData', empty: true }); return; }
    const pcm = new Int16Array(dev.n);
    let o = 0;
    for (const c of dev.chunks) { pcm.set(c, o); o += c.length; }
    self.postMessage({ type: 'devData', sampleRate: engine.sr, pcm, ticks: dev.ticks,
      full: dev.full, cfg: engine.cfg }, [pcm.buffer]);
  }
};
