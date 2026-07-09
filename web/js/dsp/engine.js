// Moteur d'analyse : reçoit l'audio par blocs, identifie la note jouée
// (analyse grossière) puis mesure chaque anche avec un traqueur zoom par
// groupe d'octave. Fonctionne dans un Worker (ou dans Node pour les tests).

import { CoarseAnalyzer } from './coarse.js';
import { ZoomTracker } from './zoom.js';
import {
  midiToFreq, nearestMidi, centsBetween, voiceTargetFreq,
  MIDI_MIN, MIDI_MAX, REGISTER_PRESETS,
} from '../music.js';

const HOP = 4096;             // période d'analyse (~85 ms à 48 kHz)
const GATE_RMS = 2.5e-4;      // seuil de silence (~ −72 dBFS)
const MAXWIN = { fast: 128, normal: 256, precise: 512 };

export class Engine {
  constructor(sampleRate, cfg = {}) {
    this.sr = sampleRate;
    this.cfg = {
      a4: 440,
      temperament: 'equal',
      transpose: 0,
      calibrationPpm: 0,
      mode: 'auto',            // 'auto' | 'manual' | 'register'
      register: 'MM',
      manualNotes: null,       // [midi, ...] en mode manuel
      trackHarmonics: 0,       // suit les partiels 2..n de chaque note (hors registre)
      response: 'normal',      // 'fast' | 'normal' | 'precise'
      beatCurve: { midiLow: 48, bLow: 0.8, midiHigh: 96, bHigh: 3.0, overrides: {} },
      ...cfg,
    };
    this.coarse = new CoarseAnalyzer(sampleRate);
    this.trackers = new Map();   // clé: écart d'octave → ZoomTracker
    this.acc = 0;
    this.rmsAcc = 0;
    this.rmsN = 0;
    this.playedMidi = null;
    this.candMidi = null;
    this.candCount = 0;
    this.samplesTotal = 0;
  }

  configure(patch) {
    Object.assign(this.cfg, patch);
    if (patch.beatCurve) this.cfg.beatCurve = { ...patch.beatCurve };
    // Tout changement de cible invalide les traqueurs.
    this.retune(true);
  }

  voices() {
    const c = this.cfg;
    if (c.mode === 'register') {
      const preset = REGISTER_PRESETS[c.register] ?? REGISTER_PRESETS.M;
      return preset.voices;
    }
    if (c.mode === 'manual' && c.manualNotes?.length) {
      // Chaque note manuelle devient une voix ancrée sur sa propre note.
      return c.manualNotes.map((m, i) => ({
        id: `n${i}`, label: null, oct: 0, beatSign: 0, fixedMidi: m,
      }));
    }
    return [{ id: 'auto', label: null, oct: 0, beatSign: 0 }];
  }

  // (Re)centre les traqueurs sur la note jouée courante.
  retune(force = false) {
    const played = this.playedMidi;
    if (played == null && this.cfg.mode !== 'manual') {
      if (force) this.trackers.clear();
      return;
    }
    const groups = this.groupVoices(played);
    const keep = new Set();
    for (const g of groups) {
      keep.add(g.key);
      let t = this.trackers.get(g.key);
      if (!t) { t = new ZoomTracker(this.sr); this.trackers.set(g.key, t); }
      const fc = g.center * g.kTrack;
      if (force || t.fc !== fc) t.setCenter(fc);
    }
    for (const k of [...this.trackers.keys()]) if (!keep.has(k)) this.trackers.delete(k);
  }

  // Regroupe les voix par centre de mesure (une FFT zoom couvre ±40 Hz :
  // toutes les voix à l'unisson d'une même octave partagent un traqueur).
  // Pour les notes graves, on suit un partiel supérieur (k·f0 ≥ 150 Hz) et on
  // divise la fréquence mesurée par k : la fondamentale d'une anche grave est
  // souvent faible et sa bande encombrée de partiels voisins ; le partiel k
  // est net, et l'écart entre anches y est multiplié par k (meilleure
  // séparation des basses tremblées).
  groupVoices(playedMidi) {
    const c = this.cfg;
    const map = new Map();
    for (const v of this.voices()) {
      const base = v.fixedMidi ?? (playedMidi + 12 * v.oct);
      if (base < MIDI_MIN - 1 || base > MIDI_MAX + 1) continue;
      const t = v.fixedMidi != null
        ? { midi: v.fixedMidi, nominal: midiToFreq(v.fixedMidi, c), beat: 0,
            target: midiToFreq(v.fixedMidi, c) }
        : voiceTargetFreq(playedMidi, v, c);
      const key = v.fixedMidi != null ? `m${v.fixedMidi}` : `o${v.oct}`;
      let g = map.get(key);
      if (!g) {
        const kTrack = Math.max(1, Math.ceil(150 / t.nominal));
        g = { key, center: t.nominal, kTrack, voices: [] };
        map.set(key, g);
      }
      g.voices.push({ def: v, ...t });
    }
    const groups = [...map.values()];

    // Suivi individuel des harmoniques : un traqueur zoom dédié par partiel
    // (2..n). Chaque partiel est mesuré à sa fréquence réelle — l'anche
    // n'étant pas parfaitement harmonique, l'écart de chaque partiel au
    // multiple exact devient une grandeur mesurée, pas une hypothèse.
    const nH = c.mode !== 'register' ? (c.trackHarmonics | 0) : 0;
    if (nH > 1) {
      for (const g of groups.slice()) {
        for (let k = 2; k <= nH; k++) {
          if (k === g.kTrack) continue;             // déjà couvert par la voix de base
          if (g.center * k > 9500) break;
          groups.push({
            key: `${g.key}h${k}`,
            center: g.center,
            kTrack: k,
            isHarmonic: true,
            voices: [{
              def: { id: `H${k}`, label: `H${k}`, oct: 0, beatSign: 0 },
              midi: g.voices[0].midi,
              nominal: g.center * k,
              beat: 0,
              target: g.center * k,
            }],
          });
        }
      }
    }
    return groups;
  }

  process(chunk) {
    this.coarse.write(chunk);
    this.samplesTotal += chunk.length;

    let sum = 0;
    for (let i = 0; i < chunk.length; i++) sum += chunk[i] * chunk[i];
    const rms = Math.sqrt(sum / chunk.length);
    this.rmsAcc += sum;
    this.rmsN += chunk.length;

    // En silence, on gèle les traqueurs : la dernière mesure reste valable
    // et le bruit ne dégrade pas la fenêtre d'analyse.
    if (rms >= GATE_RMS) {
      for (const t of this.trackers.values()) t.process(chunk);
    }

    this.acc += chunk.length;
    if (this.acc >= HOP) {
      this.acc -= HOP;
      return this.tick();
    }
    return null;
  }

  tick() {
    const c = this.cfg;
    const level = Math.sqrt(this.rmsAcc / Math.max(1, this.rmsN));
    this.rmsAcc = 0; this.rmsN = 0;
    const quiet = level < GATE_RMS;
    const calib = 1 + (c.calibrationPpm || 0) * 1e-6;

    const coarse = this.coarse.ready() ? this.coarse.analyze() : null;
    let f0 = coarse?.f0 ? coarse.f0.freq * calib : null;

    // Décision de note avec hystérésis (2 trames stables).
    if (!quiet && f0 && c.mode !== 'manual') {
      let midi = nearestMidi(f0, c);
      if (c.mode === 'register') {
        // La fondamentale détectée correspond à la voix la plus grave.
        const minOct = Math.min(...this.voices().map((v) => v.oct));
        midi -= 12 * minOct;
      }
      if (midi >= MIDI_MIN && midi <= MIDI_MAX) {
        if (midi === this.playedMidi) {
          this.candCount = 0;
        } else if (midi === this.candMidi) {
          if (++this.candCount >= 2) {
            this.playedMidi = midi;
            this.candCount = 0;
            this.retune();
          }
        } else {
          this.candMidi = midi;
          this.candCount = 1;
        }
      }
    }
    if (c.mode === 'manual' && this.trackers.size === 0) this.retune(true);

    // Mesures fines par groupe, du grave vers l'aigu : les harmoniques des
    // voix déjà mesurées sont « revendiquées » pour que, par exemple, la 2e
    // harmonique du 16' ne soit pas prise pour la fondamentale du 8'.
    const maxWin = MAXWIN[c.response] ?? 256;
    const groups = [];
    const played = this.playedMidi;
    const claimed = [];
    const defs = this.groupVoices(played ?? 0).sort((a, b) => a.center - b.center);
    for (const g of defs) {
      if (played == null && c.mode !== 'manual') break;
      const t = this.trackers.get(g.key);
      if (!t) continue;
      const az = t.analyze(maxWin, Math.max(3, g.voices.length + 1));
      const voices = this.matchVoices(g, az, calib, claimed);
      if (!g.isHarmonic) {
        // Les harmoniques mesurées d'une voix de base sont « revendiquées »
        // pour les groupes plus aigus ; les groupes harmoniques, eux,
        // mesurent précisément ces fréquences-là et n'en revendiquent pas.
        for (const v of voices) {
          if (!v.tracked) continue;
          for (let m = 2; m <= 24; m++) {
            const f = m * v.fMeas;
            if (f > 9600) break;
            claimed.push(f);
          }
        }
      }
      groups.push({
        key: g.key,
        center: g.center,
        kTrack: g.kTrack,
        isHarmonic: !!g.isHarmonic,
        srd: t.srd,
        W: az?.W ?? 0,
        fill: az?.fill ?? 0,
        spectrum: az ? az.mags : null,
        voices,
      });
    }

    return {
      type: 'tick',
      time: this.samplesTotal / this.sr,
      level,
      quiet,
      f0,
      playedMidi: played,
      transpose: c.transpose,
      groups,
      coarseSpectrum: coarse ? logResample(coarse.mag, coarse.binHz, 1024) : null,
    };
  }

  // Associe les composantes mesurées aux voix attendues du groupe.
  // `claimed` : fréquences absolues (Hz) déjà expliquées comme harmoniques
  // de voix plus graves — elles ne sont utilisées qu'en dernier recours.
  matchVoices(group, az, calib, claimed = []) {
    const expected = group.voices
      .map((v) => ({ ...v }))
      .sort((a, b) => a.target - b.target);
    const k = group.kTrack ?? 1;
    // Groupes de base : fréquences ramenées à la fondamentale (mesure sur le
    // partiel k). Groupes harmoniques : on reste dans le domaine du partiel,
    // sa fréquence réelle est la grandeur d'intérêt (inharmonicité).
    const div = group.isHarmonic ? 1 : k;
    const tolHz = Math.max(2.5, (group.center * (group.isHarmonic ? k : 1)) * 0.05); // ≈ ±85 cents
    let comps = az
      ? az.components.map((cp) => ({ ...cp, freq: (cp.freq * calib) / div }))
      : [];
    comps = comps.filter((cp) =>
      expected.some((v) => Math.abs(cp.freq - v.target) < tolHz));
    const tolClaim = az ? Math.max(0.08, (0.6 * az.srd) / az.W) : 0.08;
    for (const cp of comps) {
      // Un groupe harmonique mesure par définition une fréquence déjà
      // « revendiquée » par sa fondamentale : pas d'exclusion ici.
      const abs = cp.freq * (div === 1 ? 1 : k);
      cp.claimed = group.isHarmonic
        ? false
        : claimed.some((f) => Math.abs(abs - f) < tolClaim);
    }

    const chosen = assignOrdered(expected, comps, tolHz);
    for (let i = 0; i < expected.length; i++) this.fillVoice(expected[i], chosen[i]);

    // Battements mesurés par rapport à la voix de référence du groupe.
    const base = expected.find((v) => v.def.beatSign === 0) ?? expected[0];
    for (const v of expected) {
      v.beatMeas = (v.fMeas != null && base?.fMeas != null && v !== base)
        ? v.fMeas - base.fMeas
        : (v === base ? 0 : null);
    }
    return expected;
  }

  fillVoice(v, comp) {
    if (comp) {
      v.fMeas = comp.freq;
      v.amp = comp.mag;
      v.dCents = centsBetween(comp.freq, v.nominal);
      v.dHz = comp.freq - v.nominal;
      v.dTargetCents = centsBetween(comp.freq, v.target);
      v.tracked = true;
    } else {
      v.fMeas = null; v.amp = 0; v.dCents = null; v.dHz = null;
      v.dTargetCents = null; v.tracked = false;
    }
  }
}

// Rééchantillonnage log-fréquence du spectre large bande pour l'affichage.
function logResample(mag, binHz, nOut, fLo = 20, fHi = 10000) {
  const out = new Float32Array(nOut);
  const r = Math.log(fHi / fLo);
  for (let i = 0; i < nOut; i++) {
    const fa = fLo * Math.exp((r * i) / nOut);
    const fb = fLo * Math.exp((r * (i + 1)) / nOut);
    let ia = Math.floor(fa / binHz);
    let ib = Math.max(ia + 1, Math.ceil(fb / binHz));
    ia = Math.min(mag.length - 1, Math.max(0, ia));
    ib = Math.min(mag.length, ib);
    let m = 0;
    for (let j = ia; j < ib; j++) if (mag[j] > m) m = mag[j];
    out[i] = m;
  }
  return out;
}

// Appariement voix ↔ composantes préservant l'ordre fréquentiel (alignement
// de séquences par programmation dynamique). Une voix peut rester non
// appariée (coût = tolHz) ; une composante revendiquée par une harmonique
// grave coûte presque autant que l'abandon, elle n'est donc retenue que si
// aucune composante libre ne convient.
function assignOrdered(voices, comps, tolHz) {
  const nV = voices.length;
  const nC = comps.length;
  const skip = tolHz;
  const claimPenalty = tolHz * 0.9;
  const INF = 1e15;
  const cost = (i, j) => {
    const d = Math.abs(comps[j].freq - voices[i].target);
    if (d >= tolHz) return INF;
    return d + (comps[j].claimed ? claimPenalty : 0);
  };
  const dp = [];
  const bt = [];
  for (let i = 0; i <= nV; i++) {
    dp.push(new Float64Array(nC + 1));
    bt.push(new Uint8Array(nC + 1));
  }
  for (let i = 1; i <= nV; i++) { dp[i][0] = i * skip; bt[i][0] = 2; }
  for (let i = 1; i <= nV; i++) {
    for (let j = 1; j <= nC; j++) {
      let best = dp[i][j - 1], which = 1;            // composante ignorée
      const s = dp[i - 1][j] + skip;                 // voix non appariée
      if (s < best) { best = s; which = 2; }
      const m = dp[i - 1][j - 1] + cost(i - 1, j - 1); // appariement
      if (m < best) { best = m; which = 3; }
      dp[i][j] = best; bt[i][j] = which;
    }
  }
  const out = new Array(nV).fill(null);
  let i = nV, j = nC;
  while (i > 0) {
    const w = j > 0 ? bt[i][j] : 2;
    if (w === 1) j--;
    else if (w === 2) i--;
    else { out[i - 1] = comps[j - 1]; i--; j--; }
  }
  return out;
}
