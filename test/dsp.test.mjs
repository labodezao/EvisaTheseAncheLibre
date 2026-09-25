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
  // Erreur quadratique moyenne sur la dernière seconde et demie (fenêtre
  // pleine), pas sur une seule image : à 0,001 ¢ près, une image isolée ne dit
  // rien (la sortie est une médiane de 3 images, cf. stabilize).
  const run2 = (fuse) => {
    const engine = new Engine(SR, { mode: 'auto', response: 'normal', fuseHarmonics: fuse });
    const sig = makeSig();
    let se = 0, k = 0;
    for (let i = 0; i < sig.length; i += 512) {
      const r = engine.process(sig.subarray(i, Math.min(i + 512, sig.length)));
      if (!r || r.time < 2.5) continue;
      const v = r.groups[0]?.voices[0];
      if (!v?.tracked) return Infinity;
      se += cents(v.fMeas, fTrue) ** 2; k++;
    }
    return k ? Math.sqrt(se / k) : Infinity;
  };
  const errFused = run2(true);
  const errSingle = run2(false);
  console.log(`  erreur mono-partiel : ${errSingle.toFixed(6)} ¢ · fusionnée : ${errFused.toFixed(6)} ¢`);
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
console.log('\nTest 23 — musette MMM : les trois anches propres dès la première seconde');
{
  // Mesurées sur la fondamentale, trois anches à ±1,6 Hz ne sont séparées
  // qu'après ~2,7 s : avant, la courbe sautait de 1 à 2 cents par image
  // (c'est ce qui poussait à bloquer les anches). Sur l'harmonique choisi par
  // `unisonHarmonic`, elles sont k fois plus écartées et se séparent tout de
  // suite. On vérifie l'erreur RÉELLE entre 1 et 2 s.
  const truth = [438.4, 440.0, 441.6];
  const engine = new Engine(SR, { mode: 'register', register: 'MMM', response: 'normal' });
  const sig = reedSignal({ freqs: [{ f: 438.4 }, { f: 440.0 }, { f: 441.6, a: 0.9 }], seconds: 2.2 });
  const err = [[], [], []];
  for (let i = 0; i < sig.length; i += 512) {
    const r = engine.process(sig.subarray(i, i + 512));
    const t = (i + 512) / SR;
    if (!r || t < 1.0) continue;
    const g = r.groups.find((gg) => !gg.isHarmonic && !gg.isSub);
    g?.voices.forEach((v, k) => err[k].push(v.tracked ? cents(v.fMeas, truth[k]) : NaN));
  }
  const pire = Math.max(...err.map((e) => Math.sqrt(e.reduce((a, x) => a + x * x, 0) / e.length)));
  assert(Number.isFinite(pire) && pire < 0.2,
    `erreur RMS de la pire anche entre 1 et 2 s = ${pire.toFixed(3)} ¢ (< 0,2 ; ~2 ¢ sur la fondamentale)`);
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

// ---------------------------------------------------------------------------
console.log('\nTest 24 — registre LM à l\'octave juste : le 8\' ne fuit pas vers une raie parasite');
{
  // Bandonéon La3 + La4 (Ballone Burini) : la fondamentale du 8' tombe dans
  // le H2 du 16'. Avant, le 8' refusait cette raie « revendiquée » et prenait
  // une bande latérale 20 dB plus bas (−7,4 ¢ affichés pour une octave juste).
  const sig = reedSignal({ freqs: [{ f: 220 }, { f: 440 }, { f: 438.2, a: 0.1 * 0.25 }] });
  const last = run(new Engine(SR, { mode: 'register', register: 'LM' }), sig);
  const by = Object.fromEntries(last.groups.filter((g) => !g.isHarmonic)
    .flatMap((g) => g.voices.map((v) => [v.def.id, v])));
  const e16 = by['16']?.tracked ? cents(by['16'].fMeas, 220) : NaN;
  const e8 = by['8']?.tracked ? cents(by['8'].fMeas, 440) : NaN;
  assert(Math.abs(e16) < 0.1, `16' à ${e16.toFixed(3)} ¢ de 220 Hz`);
  assert(Math.abs(e8) < 0.1, `8' à ${e8.toFixed(3)} ¢ de 440 Hz (la raie à 438,2 Hz est ignorée)`);
  assert(by['8']?.merged === true, '8\' marqué « confondu avec l\'octave » (merged)');
}

// ---------------------------------------------------------------------------
console.log('\nTest 25 — auto-anches : un 16\' coché mais absent n\'est pas inventé');
{
  // Seul un 8' sonne. Le 16' était suivi sur son H2… qui est la fondamentale
  // du 8' : il affichait une « anche » à f/2 qui n'existe pas.
  const sig = reedSignal({ freqs: [{ f: 220 }] });
  const last = run(new Engine(SR, { mode: 'reeds', reedOctaves: [0, -1] }), sig);
  const v16 = last.groups.filter((g) => !g.isHarmonic && g.key === 'o-1').flatMap((g) => g.voices);
  const v8 = last.groups.filter((g) => !g.isHarmonic && g.key === 'o0').flatMap((g) => g.voices);
  assert(v16.length > 0 && v16.every((v) => !v.tracked), `aucune anche 16' annoncée (${v16.filter((v) => v.tracked).length} inventée(s))`);
  const t8 = v8.filter((v) => v.tracked);
  assert(t8.length === 1 && Math.abs(cents(t8[0].fMeas, 220)) < 0.1, `une seule anche 8', à 220 Hz (${t8.map((v) => v.fMeas.toFixed(3)).join(', ')})`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 26 — courbe sans dents de scie sous un soufflet vivant (MMM, ±1 ¢ à 1,5 Hz)');
{
  // Le soufflet module la hauteur : chaque partiel devient un amas de raies
  // (porteuse + raies latérales presque aussi fortes). Avant, le traqueur
  // sautait de la porteuse à une raie latérale d'une image à l'autre :
  // +1,2 ¢, 0, +1,2 ¢… sur l'anche 8'+.
  // Spectre mesuré sur un vrai Mi4 (Gaillard) : partiels hauts presque
  // aussi forts que la fondamentale — c'est là que la modulation se voit.
  const spectre = [-1, -19, 0, -1.4, 0, -0.8, -2.5, -6, -9.5, -13.5, -7.8, -5.4, -15, -9.8].map((d) => 10 ** (d / 20));
  const truth = [438.4, 440, 441.6], sens = [0.8, 1, 1.3], amp = [1, 1, 0.9];
  const n = SR * 8, sig = new Float32Array(n);
  truth.forEach((f, r) => {
    let ph = 0;
    const phi = spectre.map((_, h) => 1.7 * h + 2.3 * r);
    for (let i = 0; i < n; i++) {
      const m = Math.sin(2 * Math.PI * 1.5 * i / SR);
      ph += 2 * Math.PI * f * 2 ** (sens[r] * m / 1200) / SR;
      const env = Math.min(1, i / SR / 0.3) * 10 ** (6 * m / 20);
      let y = 0;
      for (let h = 0; h < spectre.length; h++) y += spectre[h] * Math.sin((h + 1) * ph + phi[h]);
      sig[i] += 0.05 * amp[r] * env * y;
    }
  });
  for (let i = 0; i < n; i++) sig[i] += 3e-4 * (Math.random() * 2 - 1);
  const engine = new Engine(SR, { mode: 'register', register: 'MMM' });
  const prev = [null, null, null], jump = [0, 0, 0], err = [[], [], []];
  for (let i = 0; i + 512 <= n; i += 512) {
    const r = engine.process(sig.subarray(i, i + 512));
    if (!r || (i + 512) / SR < 3.5) continue;
    const g = r.groups.find((gg) => !gg.isHarmonic && !gg.isSub);
    g.voices.forEach((v, k) => {
      if (!v.tracked) return;
      const c = cents(v.fMeas, truth[k]);
      err[k].push(c);
      if (prev[k] != null) jump[k] = Math.max(jump[k], Math.abs(c - prev[k]));
      prev[k] = c;
    });
  }
  const worstJump = Math.max(...jump);
  const worstMean = Math.max(...err.map((e) => Math.abs(e.reduce((a, x) => a + x, 0) / Math.max(1, e.length))));
  assert(worstJump < 0.1, `plus grand saut image à image = ${worstJump.toFixed(3)} ¢ (< 0,1 ; 1,2 ¢ avant)`);
  assert(worstMean < 0.05, `écart moyen de la pire anche = ${worstMean.toFixed(3)} ¢ (< 0,05)`);
}

// ---------------------------------------------------------------------------
console.log('\nTest 27 — une seule version : page, appli, moteur, cache du service worker');
{
  // Après une mise à jour, un navigateur qui mélange deux versions (cache
  // HTTP) donnait un strobe vide et des boutons sans effet. Chaque fichier
  // porte son numéro ; ils doivent être identiques.
  const { readFileSync } = await import('node:fs');
  const lire = (f) => readFileSync(new URL(`../web/${f}`, import.meta.url), 'utf8');
  const { ENGINE_VERSION } = await import('../web/js/dsp/engine.js');
  const app = lire('js/app.js').match(/const APP_VERSION = '(\d+)'/)?.[1];
  const page = lire('index.html').match(/data-version="(\d+)"/)?.[1];
  const sw = lire('sw.js').match(/aal-shell-v(\d+)/)?.[1];
  assert(app && app === ENGINE_VERSION && app === page && app === sw,
    `versions : page ${page}, app.js ${app}, moteur ${ENGINE_VERSION}, service worker ${sw}`);
  assert(lire('sw.js').includes("cache: 'no-cache'"), 'le service worker revalide ses fichiers (pas de cache HTTP périmé)');
}

console.log('\nTest 28 — marches de hauteur (tiré/poussé) : la courbe saute net, sans rampe ni créneaux');
{
  // Une marche nette (anche du tiré puis du poussé, accordées différemment).
  // Vu sur un vrai enregistrement (Do au téléphone, 24/09/2026, marches
  // dues à l'horloge du navigateur) : la longue fenêtre en faisait une
  // colline de 2,7 s en retard d'1,4 s ; l'estimation rapide, fausse de
  // 5 à 15 ¢ sur ce son, la remplaçait par moments : des « signaux carrés ».
  const f0 = midiToFreq(60);
  const plateaux = [[0, -7], [3, 6], [6, -7], [9, 6]];           // [début s, cents]
  const centsAt = (t) => plateaux.filter(([t0]) => t >= t0).pop()[1];
  const n = SR * 12, sig = new Float32Array(n);
  const harm = [1, 0.8, 0.5, 0.4, 0.2, 0.15];
  let ph = 0;
  for (let i = 0; i < n; i++) {
    ph += (2 * Math.PI * f0 * 2 ** (centsAt(i / SR) / 1200)) / SR;
    for (let h = 0; h < harm.length; h++) sig[i] += 0.1 * harm[h] * Math.sin((h + 1) * ph + h);
    sig[i] += 3e-4 * (Math.random() * 2 - 1);
  }
  const engine = new Engine(SR, { mode: 'auto', trackHarmonics: 3 });
  let worstBase = 0, worstH3 = 0, outside = 0, nH = 0;
  for (let i = 0; i + 512 <= n; i += 512) {
    const r = engine.process(sig.subarray(i, i + 512));
    if (!r) continue;
    const t = (i + 512) / SR;
    const base = r.groups.find((g) => !g.isHarmonic && !g.isSub)?.voices[0];
    const h3 = r.groups.find((g) => g.isHarmonic && !g.isSub && g.kTrack === 3)?.voices[0];
    nH = r.groups.filter((g) => g.isHarmonic && !g.isSub).length;
    if (t < 1.5 || !base?.tracked) continue;
    const c = cents(base.fMeas, f0);
    if (c < -8 || c > 7) outside++;                              // ni au-delà, ni entre deux
    const since = t - plateaux.filter(([t0]) => t >= t0).pop()[0];
    if (since > 0.6 && since < 2.9) {
      worstBase = Math.max(worstBase, Math.abs(c - centsAt(t)));
      if (h3?.tracked) worstH3 = Math.max(worstH3, Math.abs(cents(h3.fMeas / 3, f0) - centsAt(t)));
    }
  }
  assert(worstBase < 1, `anche : à ${worstBase.toFixed(2)} ¢ du palier dès 0,6 s après chaque marche (< 1 ¢ requis)`);
  assert(worstH3 < 1, `H3 : à ${worstH3.toFixed(2)} ¢ du palier dès 0,6 s après chaque marche (< 1 ¢ requis)`);
  assert(outside === 0, `aucune valeur hors des deux paliers (${outside} image(s) aberrante(s))`);
  assert(nH === 2, `harmoniques affichées : ${nH} (H2 et H3 attendues, sans doublons)`);
}

console.log('\nTest 29 — export du mode dev : une seule archive ZIP lisible');
{
  const { zipBytes, crc32 } = await import('../web/js/zip.js');
  assert(crc32(new TextEncoder().encode('123456789')) === 0xcbf43926, 'CRC-32 de référence (« 123456789 » → cbf43926)');
  const z = zipBytes([{ name: 'a.wav', data: new Uint8Array([1, 2, 3]) }, { name: 'é.csv', data: 'x;y' }]);
  const v = new DataView(z.buffer);
  const eocd = z.length - 22;
  const ok = v.getUint32(0, true) === 0x04034b50 && v.getUint32(eocd, true) === 0x06054b50
    && v.getUint16(eocd + 10, true) === 2
    && v.getUint32(v.getUint32(eocd + 16, true), true) === 0x02014b50;
  assert(ok, `structure ZIP (en-têtes locaux, répertoire central, 2 fichiers) — ${z.length} octets`);
}

function twoReeds(reeds, seconds = 8, gaps = []) {
  const n = SR * seconds, x = new Float32Array(n);
  for (const { f, a = 1, fAfter } of reeds) {
    const H = [1, 0.8, 0.5, 0.4, 0.25, 0.15];
    let ph = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const silent = gaps.some(([a0, a1]) => t >= a0 && t < a1);
      const after = gaps.length && t >= gaps[0][1];
      ph += (2 * Math.PI * (after && fAfter ? fAfter : f)) / SR;
      if (silent) continue;
      for (let h = 0; h < H.length; h++) x[i] += 0.08 * a * H[h] * Math.sin((h + 1) * ph + h);
    }
  }
  for (let i = 0; i < n; i++) x[i] += 3e-4 * (Math.random() * 2 - 1);
  return x;
}
const at = (m, ct) => midiToFreq(m) * 2 ** (ct / 1200);

console.log('\nTest 30 — registre « Quinte » : la basse et sa quinte, chacune mesurée');
{
  // La quinte (3:2) a une période commune une octave SOUS la basse : la
  // détection trouvait Do2 pour Do3 + Sol3. Et à la quinte grave, le partiel 3
  // de la basse tombe sur le partiel 2 de la quinte.
  for (const root of [36, 48, 57]) {
    const e = new Engine(SR, { mode: 'register', register: 'Q' });
    const last = run(e, twoReeds([{ f: at(root, -4) }, { f: at(root + 7, 3), a: 0.8 }]));
    const vs = last.groups.filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices);
    const f1 = vs.find((v) => v.def.id === '1'), f5 = vs.find((v) => v.def.id === '5');
    assert(last.playedMidi === root && f1?.tracked && f5?.tracked
      && Math.abs(f1.dTargetCents + 4) < 0.1 && Math.abs(f5.dTargetCents - 3) < 0.1,
      `${noteLabel(root).full} + ${noteLabel(root + 7).full} : note ${noteLabel(last.playedMidi ?? 0).full}, `
      + `fond. ${f1?.dTargetCents?.toFixed(2)} ¢ (−4), quinte ${f5?.dTargetCents?.toFixed(2)} ¢ (+3)`);
  }
}

console.log('\nTest 31 — mode Automatique : alerte « deux anches ? » quand les partiels se contredisent');
{
  const count = (reeds) => {
    const e = new Engine(SR, { mode: 'auto' });
    const x = twoReeds(reeds);
    let n = 0;
    for (let i = 0; i + 512 <= x.length; i += 512) { const r = e.process(x.subarray(i, i + 512)); if (r?.partialsDisagree) n++; }
    return n;
  };
  const oct = count([{ f: at(48, 9), a: 0.7 }, { f: at(60, 4) }]);
  const fifth = count([{ f: at(48, -4) }, { f: at(55, 3), a: 0.8 }]);
  const one = count([{ f: at(60, 4) }]);
  const one2 = count([{ f: at(69, -2) }]);
  assert(oct > 20 && fifth > 20, `deux anches signalées (octave : ${oct} images, quinte : ${fifth} images)`);
  assert(one === 0 && one2 === 0, `une anche seule jamais signalée (${one}, ${one2} images)`);
}

console.log('\nTest 32 — inversion du soufflet (silence) : trou franc, puis la nouvelle hauteur directement');
{
  // Tiré à −3 ¢, silence de 0,4 s, poussé à +4 ¢. Avant, la valeur figée
  // restait affichée ~0,5 s après la reprise puis sautait.
  const e = new Engine(SR, { mode: 'auto' });
  const x = twoReeds([{ f: at(62, -3), fAfter: at(62, 4) }], 8, [[4, 4.4]]);
  let stale = 0, first = null;
  for (let i = 0; i + 512 <= x.length; i += 512) {
    const r = e.process(x.subarray(i, i + 512));
    if (!r || r.quiet || r.time < 4.4) continue;
    const v = r.groups.find((g) => !g.isHarmonic && !g.isSub)?.voices[0];
    if (!v?.tracked) continue;
    if (Math.abs(v.dTargetCents + 3) < 1) stale++;
    if (first == null) first = { t: r.time - 4.4, c: v.dTargetCents };
  }
  assert(stale === 0, `aucune valeur de l'ancien sens après la reprise (${stale} image(s))`);
  assert(first && first.t < 0.6 && Math.abs(first.c - 4) < 1,
    `première mesure ${first?.t.toFixed(2)} s après la reprise, à ${first?.c.toFixed(2)} ¢ (+4 attendu)`);
}

console.log('\nTest 33 — mode Accord (degrés) : fondamentale reconnue, accords renversés, enchaînés');
{
  // Demande d'Ewen : 36 accords de basses d'un chromatique à vérifier. On dit
  // « majeur » une fois ; chaque accord joué est reconnu, même renversé (sur
  // les basses, les notes d'un accord sont repliées dans une octave).
  const chords = [
    { name: 'Sol majeur renversé (Ré4 Sol4 Si4)', notes: [[62, 3], [67, -2], [71, 5]], root: 7, deg: { 1: 67, 3: 71, 5: 62 } },
    { name: 'Do majeur (Do4 Mi4 Sol4)', notes: [[60, -4], [64, 2], [67, 1]], root: 0, deg: { 1: 60, 3: 64, 5: 67 } },
    { name: 'Fa majeur renversé (Do4 Fa4 La4)', notes: [[60, 0], [65, -3], [69, 4]], root: 5, deg: { 1: 65, 3: 69, 5: 60 } },
  ];
  const seg = 4, n = SR * seg * chords.length, x = new Float32Array(n);
  chords.forEach((ch, ci) => {
    for (const [m, ct] of ch.notes) {
      const f = midiToFreq(m) * 2 ** (ct / 1200), H = [1, 0.7, 0.45, 0.3, 0.2];
      for (let h = 0; h < H.length; h++) {
        const w = (2 * Math.PI * f * (h + 1)) / SR;
        for (let i = ci * seg * SR; i < (ci + 1) * seg * SR; i++) x[i] += 0.05 * H[h] * Math.sin(w * i + h + m);
      }
    }
  });
  for (let i = 0; i < n; i++) x[i] += 3e-4 * (Math.random() * 2 - 1);
  const e = new Engine(SR, { mode: 'chord', chordDegrees: [0, 4, 7] });
  const seen = chords.map(() => null);
  for (let i = 0; i + 512 <= n; i += 512) {
    const r = e.process(x.subarray(i, i + 512));
    if (!r) continue;
    const ci = Math.floor(r.time / seg), local = r.time - ci * seg;
    if (ci < chords.length && local > 3.6 && local < 3.99) seen[ci] = r;
  }
  chords.forEach((ch, ci) => {
    const r = seen[ci];
    const vs = r ? r.groups.filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices) : [];
    const byDeg = Object.fromEntries(vs.map((v) => [v.def.label, v]));
    const want = Object.fromEntries(ch.notes.map(([m, ct]) => [m, ct]));
    const ok = r?.chord?.rootPc === ch.root && Object.entries(ch.deg).every(([d, m]) =>
      byDeg[d]?.midi === m && byDeg[d].tracked && Math.abs(byDeg[d].dTargetCents - want[m]) < 0.3);
    assert(ok, `${ch.name} : fondamentale ${r?.chord ? noteLabel(r.chord.rootMidi).name : '—'}, `
      + Object.entries(ch.deg).map(([d, m]) => `${d}=${byDeg[d] ? noteLabel(byDeg[d].midi).full : '—'} `
        + `${byDeg[d]?.dTargetCents?.toFixed(2) ?? '—'} ¢ (${want[m] > 0 ? '+' : ''}${want[m]})`).join(', '));
  });
}

console.log('\nTest 34 — régler le seuil de silence ne remet pas la mesure à zéro');
{
  const e = new Engine(SR, { mode: 'auto' });
  const x = twoReeds([{ f: at(69, 2) }], 6);
  let before = null, after = null;
  for (let i = 0; i + 512 <= x.length; i += 512) {
    if (i === 512 * Math.floor((4 * SR) / 512)) e.configure({ gateDb: -60 });
    const r = e.process(x.subarray(i, i + 512));
    if (!r) continue;
    const g = r.groups.find((gr) => !gr.isHarmonic && !gr.isSub);
    if (r.time < 4 && r.time > 3.8) before = g?.W;
    if (r.time > 4.05 && r.time < 4.2) after = g?.W;
  }
  assert(before >= 256 && after >= 256, `fenêtre gardée pleine : ${before} → ${after} échantillons`);
}

console.log('\nTest 35 — accord reconnu TOUT SEUL (type et fondamentale), comme l\'accordeur de Dirk');
{
  // Les accords d'un chromatique enchaînés sans rien régler : majeur, mineur
  // renversé, septième (sans quinte, comme sur les basses), diminué, quinte.
  const { chordName } = await import('../web/js/dsp/chord.js');
  const chords = [
    { name: 'Do', notes: [60, 64, 67] },
    { name: 'Rém', notes: [57, 62, 65] },          // La3 Ré4 Fa4 (renversé)
    { name: 'La7', notes: [57, 61, 67] },          // La3 Do#4 Sol4
    { name: 'Si dim', notes: [59, 62, 68] },       // Si3 Ré4 Sol#4 (1 ♭3 6)
    { name: 'Sol 5', notes: [55, 62] },            // Sol3 Ré4
  ];
  const seg = 4, n = SR * seg * chords.length, x = new Float32Array(n);
  chords.forEach((ch, ci) => {
    for (const m of ch.notes) {
      const f = midiToFreq(m), H = [1, 0.7, 0.45, 0.3, 0.2, 0.12, 0.08];
      for (let h = 0; h < H.length; h++) {
        const w = (2 * Math.PI * f * (h + 1)) / SR;
        for (let i = ci * seg * SR; i < (ci + 1) * seg * SR; i++) x[i] += 0.05 * H[h] * Math.sin(w * i + h + m);
      }
    }
  });
  for (let i = 0; i < n; i++) x[i] += 3e-4 * (Math.random() * 2 - 1);
  const e = new Engine(SR, { mode: 'chord', chordType: 'auto' });
  const got = chords.map(() => null);
  for (let i = 0; i + 512 <= n; i += 512) {
    const r = e.process(x.subarray(i, i + 512));
    if (!r) continue;
    const ci = Math.floor(r.time / seg), local = r.time - ci * seg;
    if (ci < chords.length && local > 3.5 && local < 3.99 && r.chord) {
      got[ci] = chordName(noteLabel(r.chord.rootMidi).name, r.chord.type);
    }
  }
  const ok = chords.every((c, i) => got[i] === c.name);
  assert(ok, `reconnus : ${got.join(', ')} (attendu : ${chords.map((c) => c.name).join(', ')})`);
}

console.log('\nTest 36 — battement du trémolo (bat/min), en mode Automatique');
{
  // Demande d'Ewen : deux anches en « vibrato » — combien de battements par
  // minute ? Lu dans l'enveloppe, sans séparer les anches.
  const cases = [
    { nom: 'La4 + 2,30 Hz', reeds: [{ f: 440 }, { f: 442.3, a: 0.9 }], hz: 2.3 },
    { nom: 'Do4 + 0,60 Hz (lent)', reeds: [{ f: 261.63 }, { f: 262.23, a: 0.8 }], hz: 0.6 },
    { nom: 'Mi5 + 6,0 Hz (rapide)', reeds: [{ f: 659.26 }, { f: 665.26, a: 0.9 }], hz: 6.0 },
    { nom: 'Do2 + 1,0 Hz (basse)', reeds: [{ f: 65.41 }, { f: 66.41, a: 0.9 }], hz: 1.0 },
  ];
  for (const c of cases) {
    const last = run(new Engine(SR, { mode: 'auto' }), twoReeds(c.reeds, 10));
    const b = last.beat;
    assert(b && b.kind === 'anches' && Math.abs(b.hz - c.hz) < 0.01 * c.hz,
      `${c.nom} : ${b ? `${b.hz.toFixed(3)} Hz = ${(b.hz * 60).toFixed(1)} bat/min (${b.kind})` : 'rien'}`);
  }
  const solo = run(new Engine(SR, { mode: 'auto' }), twoReeds([{ f: 440 }], 10));
  assert(!solo.beat, `anche seule : aucun battement (${solo.beat ? `${solo.beat.hz.toFixed(2)} Hz` : 'rien'})`);
}

console.log('\nTest 37 — registre 16\'+8\' : on lâche une anche, elle devient « — », l\'autre reste mesurée');
{
  // Session d'Ewen : Fa♯3 + Fa♯4 tenus, puis le 16' lâché. Avant, la note
  // basculait d'une octave et l'anche restante était ré-attribuée à l'autre
  // voix, ou le 16' affichait une valeur fausse (−28 ¢).
  const n = SR * 9, x = new Float32Array(n);
  const H = [1, 0.7, 0.5, 0.35, 0.2];
  for (const [f, stop] of [[midiToFreq(54) * 2 ** (2 / 1200), 5], [midiToFreq(66) * 2 ** (-1 / 1200), 9]]) {
    for (let h = 0; h < H.length; h++) {
      const w = (2 * Math.PI * f * (h + 1)) / SR;
      for (let i = 0; i < stop * SR; i++) x[i] += 0.06 * H[h] * Math.sin(w * i + h);
    }
  }
  for (let i = 0; i < n; i++) x[i] += 3e-4 * (Math.random() * 2 - 1);
  const e = new Engine(SR, { mode: 'register', register: 'LM' });
  let before = null, after = null, notes = new Set();
  for (let i = 0; i + 512 <= n; i += 512) {
    const r = e.process(x.subarray(i, i + 512));
    if (!r || r.time < 3) continue;
    const vs = r.groups.filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices);
    const v16 = vs.find((v) => v.def.id === '16'), v8 = vs.find((v) => v.def.id === '8');
    notes.add(r.playedMidi);
    if (r.time > 4.5 && r.time < 4.9) before = { t16: v16?.tracked, c8: v8?.dTargetCents };
    if (r.time > 6 && r.time < 8.8 && (v16?.tracked || !v8?.tracked)) after = { t: r.time, t16: v16?.tracked, t8: v8?.tracked };
  }
  assert(before?.t16 && Math.abs(before.c8 + 1) < 0.3, `les deux anches mesurées avant (8' à ${before?.c8?.toFixed(2)} ¢)`);
  assert(after == null, after ? `à ${after.t.toFixed(2)} s : 16' ${after.t16 ? 'encore affiché' : '—'}, 8' ${after.t8 ? 'mesuré' : 'perdu'}` : 'après l\'arrêt du 16\' : 16\' « — », 8\' toujours mesuré');
  assert(notes.size === 1, `la note ne bascule pas d'octave (${[...notes].map((m) => noteLabel(m).full).join(', ')})`);
}

console.log(failures === 0 ? '\nTous les tests DSP passent.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
