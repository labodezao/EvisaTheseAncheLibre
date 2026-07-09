// Tests du moteur DSP sur signaux de synthèse.
// Exécution : node test/dsp.test.mjs

import { Engine } from '../web/js/dsp/engine.js';
import { midiToFreq, noteLabel } from '../web/js/music.js';

const SR = 48000;
let failures = 0;

function assert(cond, msg) {
  if (cond) {
    console.log(`  ✓ ${msg}`);
  } else {
    failures++;
    console.error(`  ✗ ÉCHEC : ${msg}`);
  }
}

// Générateur de son d'anche : somme de partiels harmoniques + bruit.
function reedSignal({ freqs, harmonics = [1, 0.6, 0.4, 0.25, 0.15, 0.08], noise = 3e-4, seconds = 8 }) {
  const n = Math.floor(SR * seconds);
  const out = new Float32Array(n);
  for (const { f, a = 1 } of freqs) {
    for (let h = 0; h < harmonics.length; h++) {
      const fh = f * (h + 1);
      if (fh > SR * 0.45) break;
      const amp = 0.25 * a * harmonics[h];
      const phi = Math.random() * 2 * Math.PI;
      const w = (2 * Math.PI * fh) / SR;
      for (let i = 0; i < n; i++) out[i] += amp * Math.sin(w * i + phi);
    }
  }
  for (let i = 0; i < n; i++) out[i] += noise * (Math.random() * 2 - 1);
  return out;
}

function run(engine, signal) {
  let last = null;
  for (let i = 0; i < signal.length; i += 512) {
    const r = engine.process(signal.subarray(i, Math.min(i + 512, signal.length)));
    if (r) last = r;
  }
  return last;
}

function cents(f, ref) { return 1200 * Math.log2(f / ref); }

// ---------------------------------------------------------------------------
console.log('\nTest 1 — précision 0,1 cent sur anche isolée (La4 à 440,05 Hz, réponse « normal »)');
{
  const fTrue = 440.05;
  const engine = new Engine(SR, { mode: 'auto', response: 'normal' });
  const last = run(engine, reedSignal({ freqs: [{ f: fTrue }] }));
  assert(last && last.playedMidi === 69, `note détectée = La4 (obtenu : ${last && noteLabel(last.playedMidi ?? 0).full})`);
  const v = last.groups[0]?.voices[0];
  assert(v?.tracked, 'anche suivie');
  const err = Math.abs(cents(v.fMeas, fTrue));
  assert(err < 0.1, `écart de mesure = ${err.toFixed(4)} cent (< 0,1 cent requis) — mesuré ${v.fMeas.toFixed(4)} Hz`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 2 — tremolo 8\'+8\' : séparation des anches et battement (440,0 / 442,3 Hz)');
{
  const engine = new Engine(SR, { mode: 'register', register: 'MM', response: 'normal' });
  const last = run(engine, reedSignal({ freqs: [{ f: 440.0 }, { f: 442.3, a: 0.9 }], seconds: 10 }));
  assert(last && last.playedMidi === 69, 'note jouée = La4');
  const g = last.groups[0];
  const v8 = g?.voices.find((v) => v.def.id === '8');
  const v8p = g?.voices.find((v) => v.def.id === '8+');
  assert(v8?.tracked && v8p?.tracked, 'les deux anches sont résolues séparément');
  const e1 = Math.abs(v8.fMeas - 440.0);
  const e2 = Math.abs(v8p.fMeas - 442.3);
  assert(e1 < 0.03 && e2 < 0.03, `fréquences : ${v8.fMeas.toFixed(3)} / ${v8p.fMeas.toFixed(3)} Hz (écarts ${e1.toFixed(4)} / ${e2.toFixed(4)} Hz)`);
  const beatErr = Math.abs(v8p.beatMeas - 2.3);
  assert(beatErr < 0.05, `battement mesuré = ${v8p.beatMeas.toFixed(3)} Hz (cible 2,300, écart ${beatErr.toFixed(4)})`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 3 — note grave à fondamentale faible (Mi1 ≈ 41,2 Hz) : pas d\'erreur d\'octave');
{
  const fTrue = midiToFreq(28) * Math.pow(2, 3 / 1200); // Mi1 +3 cents
  const engine = new Engine(SR, { mode: 'auto', response: 'normal' });
  const harmonics = [0.05, 0.5, 0.9, 0.7, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15];
  const last = run(engine, reedSignal({ freqs: [{ f: fTrue }], harmonics, seconds: 8 }));
  assert(last && last.playedMidi === 28, `note détectée = Mi1 (obtenu : ${last && noteLabel(last.playedMidi ?? 0).full})`);
  const v = last.groups[0]?.voices[0];
  const err = v?.tracked ? Math.abs(cents(v.fMeas, fTrue)) : Infinity;
  assert(err < 0.15, `écart de mesure = ${err.toFixed(4)} cent`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 4 — 2e harmonique dominante : pas d\'erreur d\'octave vers le haut');
{
  const fTrue = 220.6; // La3 légèrement haut
  const engine = new Engine(SR, { mode: 'auto', response: 'normal' });
  const harmonics = [0.4, 1.0, 0.5, 0.35, 0.2, 0.1];
  const last = run(engine, reedSignal({ freqs: [{ f: fTrue }], harmonics, seconds: 8 }));
  assert(last && last.playedMidi === 57, `note détectée = La3 (obtenu : ${last && noteLabel(last.playedMidi ?? 0).full})`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 5 — registre 16\'+8\' : mesure simultanée des deux octaves');
{
  // Cas réaliste : 16' à +1,2 cent, 8' à +5 cents. La 2e harmonique du 16'
  // (440,30 Hz) tombe à 1,1 Hz de la fondamentale du 8' (441,27 Hz) : le mode
  // « précis » (fenêtre ~5,5 s) les sépare. Plus proches, la mesure du 8'
  // pendant que le 16' sonne est physiquement indéterminée à fenêtre courte.
  const f16 = 220.15, f8 = 441.27;
  const engine = new Engine(SR, { mode: 'register', register: 'LM', response: 'precise' });
  const last = run(engine, reedSignal({ freqs: [{ f: f16 }, { f: f8, a: 0.8 }], seconds: 12 }));
  assert(last && last.playedMidi === 69, `note jouée = La4 (obtenu : ${last && noteLabel(last.playedMidi ?? 0).full})`);
  const g16 = last.groups.find((g) => g.voices.some((v) => v.def.id === '16'));
  const g8 = last.groups.find((g) => g.voices.some((v) => v.def.id === '8'));
  const v16 = g16?.voices.find((v) => v.def.id === '16');
  const v8 = g8?.voices.find((v) => v.def.id === '8');
  assert(v16?.tracked && v8?.tracked, 'les deux voix sont suivies');
  const e16 = v16 ? Math.abs(v16.fMeas - f16) : Infinity;
  const e8 = v8 ? Math.abs(v8.fMeas - f8) : Infinity;
  assert(e16 < 0.05 && e8 < 0.05, `16' : ${v16?.fMeas?.toFixed(3)} Hz (±${e16.toFixed(4)}), 8' : ${v8?.fMeas?.toFixed(3)} Hz (±${e8.toFixed(4)})`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 6 — mode manuel polyphonique : accord Do4-Mi4-Sol4');
{
  const notes = [60, 64, 67];
  const freqs = notes.map((m) => ({ f: midiToFreq(m) * Math.pow(2, (Math.random() * 8 - 4) / 1200) }));
  const engine = new Engine(SR, { mode: 'manual', manualNotes: notes, response: 'normal' });
  const last = run(engine, reedSignal({ freqs, seconds: 10 }));
  let ok = 0;
  for (let i = 0; i < notes.length; i++) {
    const g = last.groups.find((gr) => gr.key === `m${notes[i]}`);
    const v = g?.voices[0];
    if (v?.tracked && Math.abs(cents(v.fMeas, freqs[i].f)) < 0.3) ok++;
  }
  assert(ok === 3, `3 notes de l'accord mesurées à < 0,3 cent (obtenu : ${ok}/3)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 7 — mode « précis » : convergence < 0,02 cent sur ton stable');
{
  const fTrue = 261.71; // Do4 légèrement haut
  const engine = new Engine(SR, { mode: 'auto', response: 'precise' });
  const last = run(engine, reedSignal({ freqs: [{ f: fTrue }], seconds: 12, noise: 1e-4 }));
  const v = last.groups[0]?.voices[0];
  const err = v?.tracked ? Math.abs(cents(v.fMeas, fTrue)) : Infinity;
  assert(err < 0.02, `écart de mesure = ${err.toFixed(5)} cent`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 8 — anche inharmonique : partiels étirés jusqu\'à +30 cents, fondamentale non biaisée');
{
  // Partiels volontairement désaccordés du multiple exact, comme sur une
  // anche réelle : la détection ne doit être ni faussée (note) ni tirée
  // (fréquence de la fondamentale, mesurée directement à k=1).
  const fTrue = 165.15; // Mi3 légèrement haut
  const stretch = [0, 6, 12, 18, 25, 30]; // cents par partiel
  const amps = [1, 0.7, 0.5, 0.35, 0.2, 0.12];
  const n = SR * 8;
  const sig = new Float32Array(n);
  for (let h = 0; h < stretch.length; h++) {
    const fh = fTrue * (h + 1) * Math.pow(2, stretch[h] / 1200);
    const w = (2 * Math.PI * fh) / SR;
    const phi = Math.random() * 6.28;
    for (let i = 0; i < n; i++) sig[i] += 0.2 * amps[h] * Math.sin(w * i + phi);
  }
  for (let i = 0; i < n; i++) sig[i] += 3e-4 * (Math.random() * 2 - 1);
  const engine = new Engine(SR, { mode: 'auto', response: 'normal' });
  const last = run(engine, sig);
  assert(last && last.playedMidi === 52, `note détectée = Mi3 (obtenu : ${last && noteLabel(last.playedMidi ?? 0).full})`);
  const v = last.groups[0]?.voices[0];
  const err = v?.tracked ? Math.abs(cents(v.fMeas, fTrue)) : Infinity;
  assert(err < 0.1, `fondamentale mesurée à ${err.toFixed(4)} cent de la vraie valeur (partiels étirés ignorés)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 9 — suivi individuel des harmoniques : chaque partiel mesuré à sa fréquence réelle');
{
  const fTrue = 220.28; // La3 +2,2 cents
  const stretch = [0, 5, 11, 17, 23]; // cents par partiel
  const amps = [1, 0.7, 0.5, 0.3, 0.2];
  const n = SR * 10;
  const sig = new Float32Array(n);
  const partials = [];
  for (let h = 0; h < stretch.length; h++) {
    const fh = fTrue * (h + 1) * Math.pow(2, stretch[h] / 1200);
    partials.push(fh);
    const w = (2 * Math.PI * fh) / SR;
    const phi = Math.random() * 6.28;
    for (let i = 0; i < n; i++) sig[i] += 0.2 * amps[h] * Math.sin(w * i + phi);
  }
  for (let i = 0; i < n; i++) sig[i] += 3e-4 * (Math.random() * 2 - 1);
  const engine = new Engine(SR, { mode: 'auto', trackHarmonics: 5, response: 'normal' });
  const last = run(engine, sig);
  assert(last && last.playedMidi === 57, `note détectée = La3 (obtenu : ${last && noteLabel(last.playedMidi ?? 0).full})`);
  let ok = 0;
  const details = [];
  for (let k = 2; k <= 5; k++) {
    const g = last.groups.find((gr) => gr.key.endsWith(`h${k}`));
    const v = g?.voices[0];
    const err = v?.tracked ? Math.abs(cents(v.fMeas, partials[k - 1])) : Infinity;
    details.push(`H${k}: ${err.toFixed(4)}¢`);
    if (err < 0.1) ok++;
  }
  assert(ok === 4, `4 harmoniques suivies à < 0,1 cent de leur fréquence réelle (${details.join(', ')})`);
  // L'inharmonicité mesurée (écart de H_k au multiple exact) correspond à
  // l'étirement programmé.
  const g3 = last.groups.find((gr) => gr.key.endsWith('h3'));
  const v3 = g3?.voices[0];
  const inh3 = v3 ? cents(v3.fMeas, 3 * midiToFreq(57)) : NaN;
  const expected3 = cents(partials[2], 3 * midiToFreq(57));
  assert(Math.abs(inh3 - expected3) < 0.1,
    `écart de H3 à 3·f_nominale = ${inh3.toFixed(2)}¢ (attendu ${expected3.toFixed(2)}¢)`);
}

console.log(failures === 0 ? '\nTous les tests DSP passent.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
