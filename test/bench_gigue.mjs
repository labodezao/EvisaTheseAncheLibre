// Ce que l'œil voit : la gigue des valeurs affichées, image par image, pendant
// que la note sonne. La valeur finale peut être juste à 0,1 cent alors que la
// courbe, elle, saute dans tous les sens.   node test/bench_gigue.mjs
import { Engine } from '../web/js/dsp/engine.js';

const SR = 48000;
let seed = 7;
const rnd = () => { seed = (1103515245 * seed + 12345) & 0x7fffffff; return seed / 0x40000000 - 1; };
const SPECTRE = [1, 0.7, 0.5, 0.38, 0.28, 0.2, 0.14, 0.1, 0.07, 0.05];

function signal(reeds, seconds, wobbleC = 0.2) {
  const n = Math.floor(SR * seconds), out = new Float32Array(n);
  for (const { f, a = 1 } of reeds) for (let h = 0; h < SPECTRE.length; h++) {
    const fh = f * (h + 1); if (fh > SR * 0.45) break;
    let ph = (rnd() + 1) * Math.PI; const amp = 0.12 * a * SPECTRE[h];
    for (let i = 0; i < n; i++) {
      const k = 2 ** ((wobbleC * Math.sin(2 * Math.PI * 0.7 * i / SR)) / 1200);
      ph += (2 * Math.PI * fh * k) / SR;
      out[i] += amp * Math.min(1, i / SR / 0.3) * Math.sin(ph);
    }
  }
  for (let i = 0; i < n; i++) out[i] += 3e-4 * rnd();
  return out;
}

function gigue(nom, cfg, reeds, seconds = 8) {
  const e = new Engine(SR, cfg), sig = signal(reeds, seconds), series = new Map();
  for (let i = 0; i < sig.length; i += 512) {
    const r = e.process(sig.subarray(i, i + 512)); if (!r) continue;
    const t = (i + 512) / SR;
    for (const g of r.groups ?? []) {
      if (g.isHarmonic || g.isSub) continue;
      (g.voices ?? []).forEach((v, k) => {
        const id = `${g.key}:${k}`; if (!series.has(id)) series.set(id, []);
        series.get(id).push([t, v.tracked ? v.dCents : null]);
      });
    }
  }
  const fen = [[0, 1], [1, 2], [2, 3], [3, 5], [5, 8]];
  console.log(`\n${nom}`);
  console.log('   voix   ' + fen.map(([a, b]) => `${a}-${b} s`.padStart(16)).join(''));
  for (const [id, s] of series) {
    const cells = fen.map(([a, b]) => {
      const x = s.filter(([t, v]) => t >= a && t < b).map(([, v]) => v);
      const ok = x.filter((v) => v != null);
      if (ok.length < 2) return '— (non suivie)'.padStart(16);
      const d = ok.slice(1).map((v, i) => v - ok[i]);                 // saut image à image
      const rms = Math.sqrt(d.reduce((a, b) => a + b * b, 0) / d.length);
      const trous = x.length - ok.length;
      return `±${rms.toFixed(2)}¢${trous ? ` ${trous}trou` : ''}`.padStart(16);
    });
    console.log(`   ${id.padEnd(6)} ${cells.join('')}`);
  }
}

const f = 440, dB = (x) => 10 ** (x / 20);
const K = +(process.argv[2] ?? 0);   // 0 = règle automatique
const mmm = { mode: 'register', register: 'MMM', response: 'normal', polyHarmonic: K || null };
console.log(`=== harmonique suivi pour l'unisson : ${K ? 'H' + K + ' forcé' : 'automatique'} ===`);
gigue('Musette MMM, ±1,6 Hz', mmm, [{ f: f - 1.6 }, { f }, { f: f + 1.6, a: 0.9 }]);
gigue('Musette MMM, anche 8− à −12 dB', mmm, [{ f: f - 1.6, a: dB(-12) }, { f }, { f: f + 1.6, a: 0.9 }]);
