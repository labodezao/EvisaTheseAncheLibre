// L'accordeur sur un vrai enregistrement : ce que chaque anche donne, fenêtre
// par fenêtre, et ce que chaque partiel en dit.
//
//   node test/bench_wav.mjs note.wav            (mode auto)
//   node test/bench_wav.mjs note.wav MM         (registre MM, MMM, LMM…)
//
// WAV PCM 16/24/32 bits ou float 32, mono ou stéréo (moyenné), lu à sa
// fréquence d'échantillonnage d'origine (pas de rééchantillonnage). Une prise
// au micro du téléphone suffit : c'est fait pour mesurer sans matériel.
import { readFileSync } from 'node:fs';
import { Engine } from '../web/js/dsp/engine.js';

function lireWav(chemin) {
  const b = readFileSync(chemin);
  if (b.toString('ascii', 0, 4) !== 'RIFF' || b.toString('ascii', 8, 12) !== 'WAVE')
    throw new Error(`${chemin} : pas un fichier WAV`);
  let fmt = null, data = null;
  for (let o = 12; o + 8 <= b.length;) {
    const id = b.toString('ascii', o, o + 4), n = b.readUInt32LE(o + 4);
    if (id === 'fmt ') fmt = {
      format: b.readUInt16LE(o + 8), canaux: b.readUInt16LE(o + 10),
      sr: b.readUInt32LE(o + 12), bits: b.readUInt16LE(o + 22),
    };
    if (id === 'data') data = b.subarray(o + 8, Math.min(o + 8 + n, b.length));
    o += 8 + n + (n & 1);
  }
  if (!fmt || !data) throw new Error(`${chemin} : fmt/data introuvable`);
  const oct = fmt.bits / 8, nf = Math.floor(data.length / (oct * fmt.canaux));
  const lit = fmt.format === 3 ? (o) => data.readFloatLE(o)
    : fmt.bits === 16 ? (o) => data.readInt16LE(o) / 32768
    : fmt.bits === 24 ? (o) => data.readIntLE(o, 3) / 8388608
    : fmt.bits === 32 ? (o) => data.readInt32LE(o) / 2147483648
    : null;
  if (!lit) throw new Error(`${chemin} : ${fmt.bits} bits non géré`);
  const x = new Float32Array(nf);
  for (let i = 0; i < nf; i++) {
    let s = 0;
    for (let c = 0; c < fmt.canaux; c++) s += lit((i * fmt.canaux + c) * oct);
    x[i] = s / fmt.canaux;
  }
  return { x, sr: fmt.sr };
}

const cents = (f, r) => 1200 * Math.log2(f / r);
const signe = (v, d) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(d)}`;

const [chemin, registre] = process.argv.slice(2);
if (!chemin) {
  console.log('usage : node test/bench_wav.mjs note.wav [M|MM|MMM|LM|LMM|LMH]');
  process.exit(1);
}
const { x, sr } = lireWav(chemin);
const cfg = registre ? { mode: 'register', register: registre } : { mode: 'auto' };
const e = new Engine(sr, cfg);
const serie = [];                       // [t, [fMeas | null par voix]]
let dernier = null;
for (let i = 0; i + 512 <= x.length; i += 512) {
  const r = e.process(x.subarray(i, i + 512));
  if (!r) continue;
  const g = (r.groups ?? []).find((g) => !g.isHarmonic && !g.isSub && !g.hidden);
  if (!g) continue;
  dernier = g;
  serie.push([(i + 512) / sr, g.voices.map((v) => (v.tracked ? v.fMeas : null))]);
}
const duree = x.length / sr;
console.log(`${chemin} — ${duree.toFixed(2)} s à ${sr} Hz, ${registre ?? 'auto'}`);
if (!dernier) { console.log('aucune note détectée'); process.exit(0); }
const NOMS = ['Do', 'Do#', 'Ré', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'Sib', 'Si'];
const midi = dernier.voices[0].midi;
const note = Number.isInteger(midi) ? `${NOMS[midi % 12]}${Math.floor(midi / 12) - 1}` : '?';
console.log(`note ${note}, ${dernier.voices.length} anche(s)`);

// Moyenne et écart-type (en cents) de chaque anche par fenêtre d'une demi-seconde :
// l'écart-type, c'est ce que l'œil voit trembler sur l'écran.
const nv = dernier.voices.length;
for (let a = 0; a < duree; a += 0.5) {
  const w = serie.filter(([t]) => t >= a && t < a + 0.5);
  const cols = [];
  for (let k = 0; k < nv; k++) {
    const ok = w.map(([, v]) => v[k]).filter((f) => f != null && Number.isFinite(f));
    if (!ok.length) { cols.push('—'.padStart(26)); continue; }
    const m = ok.reduce((s, f) => s + f, 0) / ok.length;
    const sd = Math.sqrt(ok.reduce((s, f) => s + cents(f, m) ** 2, 0) / ok.length);
    const cible = dernier.voices[k].target;
    const ec = cible ? ` ${signe(cents(m, cible), 2)}¢` : '';
    cols.push(`${m.toFixed(3)} Hz${ec} ±${sd.toFixed(3)}`.padStart(26));
  }
  console.log(`  ${a.toFixed(1)}–${(a + 0.5).toFixed(1)} s ${cols.join('')}`);
}

// Ce que chaque partiel dit de chaque anche (f/k) : s'ils s'accordent à
// mieux que 0,1 ¢, le son est harmonique et n'importe lequel suffit.
if (dernier.partials) {
  console.log('partiels (f/k, écart au suivi principal) :');
  const base = dernier.voices.map((v) => v.fMeas);
  for (const [k, p] of Object.entries(dernier.partials)) {
    const cells = Object.values(p).map((f, j) => {
      if (f == null) return '…';
      const ref = base.reduce((b, fb) => (fb && Math.abs(fb - f / k) < Math.abs(b - f / k) ? fb : b), Infinity);
      return `${(f / k).toFixed(3)} (${signe(cents(f / k, ref), 2)}¢)`;
    });
    console.log(`  H${k}  ${cells.join('   ')}`);
  }
}
