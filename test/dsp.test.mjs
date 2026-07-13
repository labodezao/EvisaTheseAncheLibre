// Tests du moteur DSP sur signaux de synthèse.
// Exécution : node test/dsp.test.mjs

import { Engine } from '../web/js/dsp/engine.js';
import { NsdfTracker } from '../web/js/dsp/nsdf.js';
import { matrixPencil } from '../web/js/dsp/subspace.js';
import { CoarseAnalyzer } from '../web/js/dsp/coarse.js';
import { midiToFreq, noteLabel, overlappingAllan } from '../web/js/music.js';

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

// ---------------------------------------------------------------------------
console.log('\nTest 10 — temps de réponse de l\'anche : rampe d\'attaque de 100 ms mesurée');
{
  const f = 440.0;
  const n = SR * 5;
  const sig = new Float32Array(n);
  const t0 = SR * 1.5;        // début de l'attaque à 1,5 s
  const ramp = SR * 0.1;      // montée linéaire de 100 ms
  const w = (2 * Math.PI * f) / SR;
  for (let i = 0; i < n; i++) {
    const envl = i < t0 ? 0 : Math.min(1, (i - t0) / ramp);
    sig[i] = 0.3 * envl * Math.sin(w * i) + 2e-5 * (Math.random() * 2 - 1);
  }
  const engine = new Engine(SR, { mode: 'auto', response: 'fast' });
  const last = run(engine, sig);
  const a = last?.attack;
  assert(a != null, 'une attaque a été détectée');
  // Rampe linéaire : 10 % → 90 % = 80 % de 100 ms = 80 ms (± résolution 10,7 ms).
  assert(a && Math.abs(a.riseMs - 80) < 25, `temps de réponse mesuré = ${a?.riseMs?.toFixed(0)} ms (attendu ≈ 80 ms)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 11 — détection de bifurcation : énergie sous-harmonique à f/2');
{
  // Anche en doublement de période : composante à f0/2 (période double).
  // Note verrouillée sur La4 pour que la bande f/2 soit surveillée.
  const f0 = 440.0;
  const n = SR * 10;
  const sig = new Float32Array(n);
  for (const [f, a] of [[f0, 0.25], [f0 / 2, 0.06], [f0 * 1.5, 0.04], [f0 * 2, 0.12]]) {
    const w = (2 * Math.PI * f) / SR;
    const phi = Math.random() * 6.28;
    for (let i = 0; i < n; i++) sig[i] += a * Math.sin(w * i + phi);
  }
  for (let i = 0; i < n; i++) sig[i] += 3e-4 * (Math.random() * 2 - 1);
  const engine = new Engine(SR, { mode: 'auto', lockNote: 69, trackSub: true, response: 'normal' });
  const last = run(engine, sig);
  const gSub = last.groups.find((g) => g.key.endsWith('s05'));
  const gS32 = last.groups.find((g) => g.key.endsWith('s15'));
  const vSub = gSub?.voices[0];
  const vS32 = gS32?.voices[0];
  assert(vSub?.tracked && Math.abs(vSub.fMeas - 220) < 0.05,
    `sous-harmonique f/2 détectée à ${vSub?.fMeas?.toFixed(3)} Hz (attendu 220,000)`);
  assert(vS32?.tracked && Math.abs(vS32.fMeas - 660) < 0.05,
    `bande 3f/2 détectée à ${vS32?.fMeas?.toFixed(3)} Hz (attendu 660,000)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 12 — suivi continu : glissando vocal (+40 cents en 4 s), courbe sans trous');
{
  // Une hauteur qui bouge en continu (chant, glissando) empêche le zoom
  // hétérodyne d'accrocher — le repli « suivi continu » (fondamentale de
  // l'analyse harmonique) doit alimenter la mesure sans discontinuités.
  const f0 = midiToFreq(57); // La3
  const n = SR * 5;
  const sig = new Float32Array(n);
  const harmonics = [1, 0.6, 0.4, 0.25];
  let phase = [0, 0, 0, 0];
  for (let i = 0; i < n; i++) {
    // +40 cents répartis linéairement entre t=0,5 s et t=4,5 s.
    const t = i / SR;
    const cents = t < 0.5 ? 0 : t > 4.5 ? 40 : ((t - 0.5) / 4) * 40;
    const f = f0 * Math.pow(2, cents / 1200);
    for (let h = 0; h < harmonics.length; h++) {
      phase[h] += (2 * Math.PI * f * (h + 1)) / SR;
      sig[i] += 0.2 * harmonics[h] * Math.sin(phase[h]);
    }
    sig[i] += 3e-4 * (Math.random() * 2 - 1);
  }
  const engine = new Engine(SR, { mode: 'auto', response: 'normal' });
  let tracked = 0, total = 0, last = null;
  for (let i = 0; i < n; i += 512) {
    const r = engine.process(sig.subarray(i, Math.min(i + 512, n)));
    if (r) {
      last = r;
      if (r.time > 1.2) { // après amorçage de la détection
        total++;
        const v = r.groups[0]?.voices[0];
        if (v?.tracked) tracked++;
      }
    }
  }
  const ratio = total ? tracked / total : 0;
  assert(ratio > 0.9, `mesure disponible sur ${(ratio * 100).toFixed(0)} % des trames pendant le glissando (> 90 % requis)`);
  const v = last.groups[0]?.voices[0];
  const finalCents = v?.tracked ? cents(v.fMeas, f0) : NaN;
  assert(Math.abs(finalCents - 40) < 4, `hauteur finale suivie à ${finalCents.toFixed(1)} cents (+40 attendu, ±4)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 13 — fusion multi-harmonique : gain de précision sous bruit fort');
{
  // Modèle physique : une anche en régime établi est strictement périodique,
  // ses partiels exactement harmoniques — fusionner les mesures de plusieurs
  // partiels (variance en 1/k²) doit battre la mesure mono-partiel.
  const fTrue = 440.13;
  const n = SR * 4;
  const makeSig = () => {
    const sig = new Float32Array(n);
    const harmonics = [0.5, 0.8, 0.6, 0.45];
    for (let h = 0; h < harmonics.length; h++) {
      const w = (2 * Math.PI * fTrue * (h + 1)) / SR;
      for (let i = 0; i < n; i++) sig[i] += 0.08 * harmonics[h] * Math.sin(w * i + h);
    }
    // Bruit déterministe (LCG) pour un test reproductible, niveau élevé.
    let seed = 123456789;
    for (let i = 0; i < n; i++) {
      seed = (1103515245 * seed + 12345) & 0x7fffffff;
      sig[i] += 0.03 * (seed / 0x40000000 - 1);
    }
    return sig;
  };
  const run2 = (fuse) => {
    const engine = new Engine(SR, { mode: 'auto', response: 'normal', fuseHarmonics: fuse });
    const last = run(engine, makeSig());
    const v = last.groups[0]?.voices[0];
    return v?.tracked ? Math.abs(cents(v.fMeas, fTrue)) : Infinity;
  };
  const errFused = run2(true);
  const errSingle = run2(false);
  console.log(`  erreur mono-partiel : ${errSingle.toFixed(4)} ¢ · fusionnée : ${errFused.toFixed(4)} ¢`);
  assert(errFused < 0.1, `erreur fusionnée = ${errFused.toFixed(4)} cent (< 0,1 requis malgré le bruit)`);
  assert(errFused <= errSingle + 1e-9, 'la fusion ne dégrade jamais la mesure mono-partiel');
}

// ---------------------------------------------------------------------------
console.log('\nTest 14 — taux de croissance exponentiel σ de l\'attaque (parler de l\'anche)');
{
  // Le démarrage d'une anche est une instabilité linéaire : A(t) = A0·e^(σt).
  // On génère une attaque exponentielle à σ = 25 s⁻¹ et on vérifie que
  // l'ajustement du moteur retrouve σ.
  const sigmaTrue = 25;
  const f = 440.0;
  const n = SR * 5;
  const sig = new Float32Array(n);
  const t0 = 1.5;      // début de l'attaque
  const tFull = t0 + 0.35; // amplitude pleine (0,3) atteinte ici
  const w = (2 * Math.PI * f) / SR;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    let amp = 0;
    if (t >= t0) amp = 0.3 * Math.min(1, Math.exp(sigmaTrue * (t - tFull)));
    sig[i] = amp * Math.sin(w * i) + 2e-5 * (Math.random() * 2 - 1);
  }
  const engine = new Engine(SR, { mode: 'auto', response: 'fast' });
  const last = run(engine, sig);
  const a = last?.attack;
  assert(a?.sigma != null, 'σ mesuré sur l\'attaque');
  const rel = a?.sigma != null ? Math.abs(a.sigma - sigmaTrue) / sigmaTrue : Infinity;
  assert(rel < 0.25, `σ mesuré = ${a?.sigma?.toFixed(1)} s⁻¹ (vrai : ${sigmaTrue}, écart ${(rel * 100).toFixed(0)} % < 25 %)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 15 — déviation d\'Allan : bruit blanc de fréquence → pente −½');
{
  // Signal de fréquence = bruit blanc gaussien : la déviation d'Allan doit
  // décroître en τ^(−1/2), soit une pente −0,5 en log-log.
  const N = 4000;
  const tau0 = 0.085;
  const y = new Float64Array(N);
  let seed = 987654321;
  const rnd = () => { seed = (1103515245 * seed + 12345) & 0x7fffffff; return seed / 0x40000000 - 1; };
  // Bruit gaussien approché (somme de 3 uniformes).
  for (let i = 0; i < N; i++) y[i] = (rnd() + rnd() + rnd());
  const pts = overlappingAllan(y, tau0);
  assert(pts.length > 5, `${pts.length} points de τ calculés`);
  // Régression log-log sur les τ intermédiaires (évite les bords).
  const use = pts.filter((p) => p.tau >= 3 * tau0 && p.tau <= 30 * tau0);
  let sx = 0, sy = 0, sxx = 0, sxy = 0, k = 0;
  for (const p of use) {
    const lx = Math.log10(p.tau), ly = Math.log10(p.sigma);
    sx += lx; sy += ly; sxx += lx * lx; sxy += lx * ly; k++;
  }
  const slope = (k * sxy - sx * sy) / (k * sxx - sx * sx);
  assert(Math.abs(slope - (-0.5)) < 0.12, `pente log-log = ${slope.toFixed(3)} (attendu −0,5, bruit blanc)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 16 — anti-pic harmonique : H3 suit le vrai partiel, pas une raie parasite près du nominal');
{
  // Reproduit le témoin réel : Si5 sonnant +9 ¢, partiels exactement
  // harmoniques (vrai H3 à +9 ¢ du nominal 3·fNom), plus une raie parasite
  // pile au nominal (0 ¢). L'ancien appariement, cherchant le partiel autour
  // de 3·f_nominale, sautait sur la raie la plus proche du nominal → la
  // courbe de H3 plongeait à ~0 ¢ pendant que fondamentale et H2 tenaient
  // +9 ¢ (pics discontinus). L'ancrage sur 3·f0_mesurée corrige.
  const nMidi = 83; // Si5
  const fNom = midiToFreq(nMidi);
  const fTrue = fNom * Math.pow(2, 9 / 1200); // +9 cents, comme le témoin
  const n = SR * 10;
  const sig = new Float32Array(n);
  const parts = [
    { f: fTrue, a: 0.30 },
    { f: 2 * fTrue, a: 0.18 },
    { f: 3 * fTrue, a: 0.12 },   // vrai H3, à +9 ¢ du nominal
    { f: 3 * fNom, a: 0.09 },    // raie parasite pile au nominal (piège)
  ];
  for (const { f, a } of parts) {
    const w = (2 * Math.PI * f) / SR;
    const phi = Math.random() * 6.28;
    for (let i = 0; i < n; i++) sig[i] += a * Math.sin(w * i + phi);
  }
  for (let i = 0; i < n; i++) sig[i] += 3e-4 * (Math.random() * 2 - 1);
  const engine = new Engine(SR, { mode: 'auto', trackHarmonics: 3, response: 'precise' });
  const last = run(engine, sig);
  assert(last && last.playedMidi === nMidi,
    `note détectée = ${noteLabel(nMidi).full} (obtenu : ${last && noteLabel(last.playedMidi ?? 0).full})`);
  const g3 = last.groups.find((gr) => gr.key.endsWith('h3'));
  const v3 = g3?.voices[0];
  const errTrue = v3?.tracked ? Math.abs(cents(v3.fMeas, 3 * fTrue)) : Infinity;
  const distNom = v3?.tracked ? Math.abs(cents(v3.fMeas, 3 * fNom)) : Infinity;
  assert(errTrue < 1.5, `H3 verrouillée sur le vrai partiel (écart ${errTrue.toFixed(2)} ¢ < 1,5)`);
  assert(distNom > 5, `H3 non capturée par la raie parasite du nominal (écart ${distNom.toFixed(2)} ¢ > 5)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 17 — plancher harmonique : une harmonique trop faible fait une lacune, pas un pic');
{
  // H3 quasi absente (−48 dB sous la fondamentale) noyée dans le bruit : le
  // traqueur se verrouillerait sur une raie de bruit et tracerait une valeur
  // aberrante. Le plancher −42 dB doit la marquer non suivie (lacune franche).
  const nMidi = 83;
  const fNom = midiToFreq(nMidi);
  const n = SR * 8;
  const sig = new Float32Array(n);
  const parts = [
    { f: fNom, a: 0.30 },
    { f: 2 * fNom, a: 0.16 },
    { f: 3 * fNom, a: 0.30 * Math.pow(10, -48 / 20) }, // −48 dB → sous le plancher
  ];
  for (const { f, a } of parts) {
    const w = (2 * Math.PI * f) / SR;
    const phi = Math.random() * 6.28;
    for (let i = 0; i < n; i++) sig[i] += a * Math.sin(w * i + phi);
  }
  for (let i = 0; i < n; i++) sig[i] += 6e-4 * (Math.random() * 2 - 1);
  const engine = new Engine(SR, { mode: 'auto', trackHarmonics: 3, response: 'normal' });
  const last = run(engine, sig);
  const g3 = last.groups.find((gr) => gr.key.endsWith('h3'));
  const v3 = g3?.voices[0];
  assert(!v3?.tracked, `H3 sous le plancher n'est pas suivie (lacune) — tracked=${!!v3?.tracked}`);
  // La fondamentale et H2, elles, restent parfaitement suivies.
  const g2 = last.groups.find((gr) => gr.key.endsWith('h2'));
  assert(last.groups[0]?.voices[0]?.tracked && g2?.voices[0]?.tracked,
    'fondamentale et H2 restent suivies malgré la lacune de H3');
}

// ---------------------------------------------------------------------------
console.log('\nTest 18 — NSDF (méthode McLeod) : justesse et robustesse à l\'octave');
{
  const tracker = new NsdfTracker(SR);
  // Justesse sur une gamme de hauteurs, son riche + bruit.
  let worst = 0;
  for (const f0 of [82.41, 110, 220, 440, 880]) {
    const W = 4096;
    const x = new Float32Array(W);
    const harm = [1, 0.7, 0.5, 0.35, 0.2, 0.1];
    for (let h = 0; h < harm.length; h++) {
      const w = (2 * Math.PI * f0 * (h + 1)) / SR;
      const phi = Math.random() * 6.28;
      for (let i = 0; i < W; i++) x[i] += 0.2 * harm[h] * Math.sin(w * i + phi);
    }
    for (let i = 0; i < W; i++) x[i] += 2e-3 * (Math.random() * 2 - 1);
    const r = tracker.estimate(x);
    const err = r ? Math.abs(cents(r.f0, f0)) : Infinity;
    if (err > worst) worst = err;
  }
  assert(worst < 0.5, `justesse NSDF ≤ ${worst.toFixed(2)} ¢ sur E2–A5 (< 0,5 requis)`);

  // Fondamentale manquante (H2..H5 seulement) : ne doit pas sauter à l'octave.
  const W = 4096;
  const x = new Float32Array(W);
  for (const [k, a] of [[2, 0.6], [3, 0.5], [4, 0.3], [5, 0.2]]) {
    const w = (2 * Math.PI * 220 * k) / SR;
    for (let i = 0; i < W; i++) x[i] += 0.2 * a * Math.sin(w * i);
  }
  for (let i = 0; i < W; i++) x[i] += 2e-3 * (Math.random() * 2 - 1);
  const r = tracker.estimate(x);
  assert(r && Math.abs(cents(r.f0, 220)) < 1,
    `fondamentale manquante : NSDF trouve 220 Hz (obtenu ${r?.f0?.toFixed(2)}), pas l'octave`);

  // Bruit blanc pur : aucune hauteur franche (clarté faible → null).
  const noise = new Float32Array(W);
  for (let i = 0; i < W; i++) noise[i] = Math.random() * 2 - 1;
  const rn = tracker.estimate(noise);
  assert(rn == null, `bruit blanc : pas de hauteur détectée (clarté insuffisante)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 19 — la clarté NSDF est exposée par le moteur');
{
  const engine = new Engine(SR, { mode: 'auto', response: 'normal' });
  const last = run(engine, reedSignal({ freqs: [{ f: 440.0 }] }));
  assert(last && typeof last.clarity === 'number' && last.clarity > 0.8,
    `clarté = ${last?.clarity?.toFixed(3)} sur anche franche (> 0,8 attendu)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 20 — Matrix Pencil : séparation sous la limite de Fourier + amortissement');
{
  const fs = 93.75; // fréquence de la bande de base décimée
  // Deux composantes à 0,4 Hz d'écart sur 64 échantillons (T = 0,68 s →
  // limite de Fourier ≈ 1,46 Hz : la FFT ne les sépare pas).
  const N = 64;
  const yr = new Float64Array(N), yi = new Float64Array(N);
  const parts = [{ f: 1.0, A: 1.0 }, { f: 1.4, A: 0.9 }];
  for (let n = 0; n < N; n++) {
    for (const p of parts) {
      const ph = (2 * Math.PI * p.f * n) / fs;
      yr[n] += p.A * Math.cos(ph); yi[n] += p.A * Math.sin(ph);
    }
    yr[n] += 1e-4 * (Math.random() * 2 - 1); yi[n] += 1e-4 * (Math.random() * 2 - 1);
  }
  const r = matrixPencil(yr, yi, 2, fs);
  const ok = r.length === 2
    && Math.abs(r[0].freq - 1.0) < 0.02 && Math.abs(r[1].freq - 1.4) < 0.02;
  assert(ok, `2 composantes séparées à ${r.map((c) => c.freq.toFixed(3)).join(' & ')} Hz (vraies 1,0 & 1,4)`);

  // Amortissement : une exponentielle décroissante α = 8 s⁻¹.
  const M = 48;
  const dr = new Float64Array(M), di = new Float64Array(M);
  for (let n = 0; n < M; n++) {
    const ph = (2 * Math.PI * 2.0 * n) / fs;
    const env = Math.exp((-8 * n) / fs);
    dr[n] = env * Math.cos(ph); di[n] = env * Math.sin(ph);
  }
  const rd = matrixPencil(dr, di, 1, fs);
  assert(rd.length === 1 && Math.abs(rd[0].damping - 8) < 0.3,
    `amortissement mesuré α = ${rd[0]?.damping?.toFixed(2)} s⁻¹ (vrai 8)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 21 — le moteur sépare un unisson tremblé via Matrix Pencil sur ~1,5 s');
{
  // Deux anches à 1,2 Hz d'écart, observation courte (1,5 s) : la FFT du
  // zoom (fenêtre ≤ 5,5 s) ne les résout pas encore ; l'analyse à
  // sous-espaces, activée, doit rendre les deux fréquences.
  const engine = new Engine(SR, { mode: 'register', register: 'MM', response: 'normal', subspace: true });
  const last = run(engine, reedSignal({ freqs: [{ f: 440.0 }, { f: 441.2, a: 0.9 }], seconds: 1.5 }));
  const bg = last.groups.find((g) => !g.isHarmonic && !g.isSub);
  const sub = bg?.subspace ?? [];
  const near = (f) => sub.some((c) => Math.abs(c.freq - f) < 0.35);
  assert(sub.length >= 2 && near(440.0) && near(441.2),
    `sous-espaces : ${sub.map((c) => c.freq.toFixed(2)).join(' & ')} Hz (vraies 440,0 & 441,2)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 22 — hystérésis de note : la note tenue résiste à une bascule de quinte');
{
  // Spectre ambigu Sol3 (196 Hz) / Do2 (65,4 Hz) : Sol3 = 3·Do2, piège de
  // quinte classique des anches réelles. Partiels forts de Sol3 + fondamentales
  // faibles de Do2 : sans hystérésis le détecteur bascule vers Do2 (erreur),
  // avec la note tenue en référence il conserve la bonne note.
  const ca = new CoarseAnalyzer(48000);
  const sol = midiToFreq(55), doo = midiToFreq(36);
  const peaks = [
    { freq: sol, mag: 1.0 }, { freq: 2 * sol, mag: 0.7 }, { freq: 3 * sol, mag: 0.5 },
    { freq: 4 * sol, mag: 0.3 }, { freq: doo, mag: 0.7 }, { freq: 2 * doo, mag: 0.56 },
  ].sort((a, b) => b.mag - a.mag);
  const toMidi = (f) => Math.round(69 + 12 * Math.log2(f / 440));
  const none = toMidi(ca.detectF0(peaks, null).freq);
  const holdSol = toMidi(ca.detectF0(peaks, sol).freq);
  const holdDo = toMidi(ca.detectF0(peaks, doo).freq);
  assert(none === 36, `sans hystérésis : erreur de quinte vers ${noteLabel(none).full} (Do2 attendu, démontre le piège)`);
  assert(holdSol === 55, `Sol3 tenu → conservé (obtenu ${noteLabel(holdSol).full})`);
  assert(holdDo === 36, `Do2 tenu → conservé (obtenu ${noteLabel(holdDo).full})`);
}

console.log(failures === 0 ? '\nTous les tests DSP passent.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
