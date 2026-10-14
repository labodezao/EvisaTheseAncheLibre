// Valide le contrôle de la prise (dsp/prise.js) sur des prises réelles : les WAV d'un micro
// traité par Windows doivent déclencher l'alerte, ceux d'un enregistreur propre (Zoom H6)
// jamais. Mêmes blocs de 512 échantillons que le Worker.
//   node test/outils/prise_sessions.mjs --alerte pc1.wav pc2.wav --propre h6.wav [--canal 1]
// Code de sortie 1 si une prise « à alerte » n'alerte pas, ou si une prise « propre » alerte
// (fausse alerte). Premier essai du 14/10/2026 : docs/PRISE-DE-SON.md.

import { ControlePrise } from '../../web/js/dsp/prise.js';
import { lireWav } from './wav.mjs';

const args = process.argv.slice(2);
let mode = null, canal = 0, attendu = 'gate';
const fichiers = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--alerte' || a === '--propre') mode = a.slice(2);
  else if (a === '--canal') canal = Number(args[++i]);
  else if (a === '--code') attendu = args[++i];
  else fichiers.push({ chemin: a, mode, canal });
}
if (!fichiers.length) { console.error('usage : prise_sessions.mjs [--code gate] --alerte f.wav ... --propre g.wav ... [--canal n]'); process.exit(2); }

let echecs = 0;
for (const f of fichiers) {
  const { x, sr } = lireWav(f.chemin, f.canal);
  const c = new ControlePrise(sr);
  const premiere = {};
  for (let o = 0, k = 0; o + 512 <= x.length; o += 512) {
    c.alimenter(x.subarray(o, o + 512));
    if (++k % 8 === 0) { const e = c.etat(); for (const code of e.codes) premiere[code] ??= Math.round(c.temps * 10) / 10; }
  }
  const e = c.etat();
  const ok = f.mode === 'alerte' ? e.codes.includes(attendu) : f.mode === 'propre' ? e.codes.length === 0 && !Object.keys(premiere).length : true;
  if (!ok) echecs++;
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${f.mode ?? '-'} ${f.chemin} (${(x.length / sr).toFixed(0)} s, ${sr} Hz) première alerte : ${JSON.stringify(premiere)}`);
  console.log(`      ${JSON.stringify(c.resume())}`);
}
process.exit(echecs ? 1 : 0);
