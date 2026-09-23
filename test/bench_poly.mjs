// Banc de mesure : combien de temps faut-il tenir la note pour que
// l'accordeur rende la fréquence de CHAQUE anche d'un registre, à 0,1 cent,
// sans en bloquer aucune ?   node test/bench_poly.mjs
import { Engine } from '../web/js/dsp/engine.js';

const SR = 48000;
let seed = 12345;
const rnd = () => { seed = (1103515245 * seed + 12345) & 0x7fffffff; return seed / 0x40000000 - 1; };

// Spectre d'anche libre : riche (le modèle physique en donne une douzaine
// d'harmoniques au-dessus de -30 dB sur dq/dt).
const SPECTRE = [1, 0.7, 0.5, 0.38, 0.28, 0.2, 0.14, 0.1, 0.07, 0.05];

function signal(reeds, seconds, noise = 3e-4, opt = {}) {
  const n = Math.floor(SR * seconds);
  const out = new Float32Array(n);
  // Soufflet : la pression ondule lentement (~0,7 Hz) et la note suit.
  // `wobbleC` = amplitude crête de la variation de hauteur, en cents.
  const wob = opt.wobbleC ?? 0, fw = opt.wobbleHz ?? 0.7;
  const attaque = opt.attackS ?? 0;
  for (const { f, a = 1 } of reeds) {
    for (let h = 0; h < SPECTRE.length; h++) {
      const fh = f * (h + 1);
      if (fh > SR * 0.45) break;
      const amp = 0.12 * a * SPECTRE[h];
      let ph = (rnd() + 1) * Math.PI;
      for (let i = 0; i < n; i++) {
        const t = i / SR;
        const k = wob ? 2 ** ((wob * Math.sin(2 * Math.PI * fw * t)) / 1200) : 1;
        ph += (2 * Math.PI * fh * k) / SR;
        const env = attaque ? Math.min(1, t / attaque) : 1;
        out[i] += amp * env * Math.sin(ph);
      }
    }
  }
  for (let i = 0; i < n; i++) out[i] += noise * rnd();
  return out;
}

const cents = (f, r) => 1200 * Math.log2(f / r);

// Premier instant après lequel l'anche reste à moins de `tol` cent jusqu'à la fin.
function tempsDeConvergence(serie, fVrai, tol) {
  let t0 = null;
  for (const [t, f] of serie) {
    const ok = f != null && Number.isFinite(f) && Math.abs(cents(f, fVrai)) < tol;
    if (ok && t0 === null) t0 = t;
    if (!ok) t0 = null;
  }
  return t0;
}

function banc(nom, cfg, reeds, seconds = 8, tol = 0.1, opt = {}) {
  const e = new Engine(SR, cfg);
  const sig = signal(reeds, seconds, 3e-4, opt);
  const series = new Map();                       // id de voix -> [[t, f]]
  for (let i = 0; i < sig.length; i += 512) {
    const r = e.process(sig.subarray(i, Math.min(i + 512, sig.length)));
    if (!r) continue;
    const t = (i + 512) / SR;
    for (const g of r.groups ?? []) {
      if (g.isHarmonic || g.isSub) continue;
      (g.voices ?? []).forEach((v, k) => {
        const id = `${g.key}:${k}`;               // les voix n'ont pas d'id : rang dans le groupe
        if (!series.has(id)) series.set(id, []);
        series.get(id).push([t, v.tracked ? v.fMeas : null]);
      });
    }
  }
  // Associe chaque anche vraie à la voix dont la mesure finale est la plus proche.
  const fin = [...series.entries()].map(([id, s]) => [id, s[s.length - 1][1], s]);
  const lignes = reeds.map(({ f }) => {
    let best = null;
    for (const [id, fm, s] of fin) {
      if (fm == null) continue;
      const d = Math.abs(cents(fm, f));
      if (!best || d < best.d) best = { id, d, fm, s };
    }
    if (!best) return { f, id: '—', t: null, err: null };
    return { f, id: best.id, fm: best.fm, err: cents(best.fm, f),
             t: tempsDeConvergence(best.s, f, tol) };
  });
  const tmax = lignes.every((l) => l.t != null) ? Math.max(...lignes.map((l) => l.t)) : null;
  console.log(`\n${nom}  — toutes les anches à < ${tol} ¢ après : ` +
              (tmax == null ? 'JAMAIS (sur ' + seconds + ' s)' : tmax.toFixed(2) + ' s'));
  for (const l of lignes) {
    console.log(`   vraie ${l.f.toFixed(3).padStart(9)} Hz → voix ${String(l.id).padEnd(5)} ` +
      (l.fm == null ? 'non suivie' :
        `${l.fm.toFixed(3).padStart(9)} Hz  (${l.err >= 0 ? '+' : ''}${l.err.toFixed(2)} ¢)  ` +
        `stable dès ${l.t == null ? 'jamais' : l.t.toFixed(2) + ' s'}`));
  }
  return tmax;
}

const f = (m) => 440 * 2 ** ((m - 69) / 12);
const musette = (m, beat) => [{ f: f(m) - beat }, { f: f(m) }, { f: f(m) + beat, a: 0.9 }];

const cfg = { mode: 'register', register: 'MMM', response: 'normal' };
const la = (beat, amps = [1, 1, 0.9]) => [
  { f: 440 - beat, a: amps[0] }, { f: 440, a: amps[1] }, { f: 440 + beat, a: amps[2] }];
const dB = (x) => 10 ** (x / 20);
banc('La4 musette, référence', cfg, la(1.6));
banc('La4, anche 8− plus faible de 12 dB', cfg, la(1.6, [dB(-12), 1, 0.9]));
banc('La4, anche 8− plus faible de 20 dB', cfg, la(1.6, [dB(-20), 1, 0.9]));
banc('La4, attaque de 0,4 s', cfg, la(1.6), 8, 0.1, { attackS: 0.4 });
banc('La4, soufflet ±0,1 ¢', cfg, la(1.6), 8, 0.1, { wobbleC: 0.1 });
banc('La4, soufflet ±0,3 ¢', cfg, la(1.6), 8, 0.1, { wobbleC: 0.3 });
banc('La4, soufflet ±1 ¢', cfg, la(1.6), 8, 0.1, { wobbleC: 1.0 });
