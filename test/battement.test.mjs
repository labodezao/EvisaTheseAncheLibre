// Battement affiché d'un unisson stable (v56 ; session d'Ewen du 11/10/2026 :
// « l'accordeur ça marche vraiment pas du tout, impossible d'avoir une valeur
// stable avec les battements »).
//
//   B 1  fuserBattement (battement.js), isolé : une image folle ne passe pas,
//        l'enveloppe sûre fait le battement, une enveloppe « modulation » qui
//        s'accorde avec l'écart mesuré ne le remplace pas, une enveloppe en
//        désaccord de plus de 40 % le remplace, le signe d'un 8'− reste négatif
//   B 2  le vrai moteur sur des sons de synthèse qui reproduisent le défaut :
//        trois raies à ±Δ jouées sous un registre MM (la voix lit tantôt Δ, tantôt
//        2Δ), pression qui dérive, vibrato lent, bruit : le battement affiché,
//        une fois la note établie, reste à ±0,05 Hz (écart type) de la vérité
//   B 3  deux anches nettes : aucun changement (0,80 Hz exact)
//
// Exécution : node test/battement.test.mjs

import { methodesBattement, FUS_PAIR_S } from '../web/js/dsp/battement.js';
import { anches, at, rejoue, voix } from './synthese-anches.mjs';

let failures = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ✓ ${msg}`);
  else { failures++; console.error(`  ✗ ÉCHEC : ${msg}`); }
}
const moy = (a) => a.reduce((x, y) => x + y, 0) / a.length;
const ecartType = (a) => { const m = moy(a); return Math.sqrt(moy(a.map((v) => (v - m) ** 2))); };

// ---- B 1 : fuserBattement seul -------------------------------------------------------------------

// Un moteur factice : l'horloge et un groupe de deux voix (8' et 8'+, ou 8'− et 8').
function banc(signes = [0, 1]) {
  const moteur = { samplesTotal: 0, sr: 1000, ...methodesBattement };
  const voixDe = signes.map((s, i) => ({ def: { id: `v${i}`, beatSign: s }, tracked: true, beatMeas: 0 }));
  const g = { key: 'g', isHarmonic: false, isSub: false, voices: voixDe };
  return {
    moteur, g, voix: voixDe,
    // Une image : le temps (s), l'écart brut de la 2e voix, l'enveloppe du moment.
    image(t, brut, env = null) {
      moteur.samplesTotal = t * 1000;
      voixDe[0].beatMeas = 0;
      voixDe[1].beatMeas = brut;
      moteur.fuserBattement([g], env);
      return voixDe[1];
    },
  };
}
const ENV_SURE = (hz) => ({ hz, kind: 'anches', sure: true, conf: 0.9 });

console.log('\nB 1 — fuserBattement : écart brut, enveloppe, signe');
{
  const b = banc();
  // 0,80 Hz tenu, avec une image folle à 3,2 Hz toutes les 10 images (sans enveloppe).
  const lus = [];
  for (let i = 0; i < 60; i++) lus.push(b.image(i * 0.085, i % 10 === 5 ? 3.2 : 0.8).beatMeas);
  const apres = lus.slice(15);
  assert(Math.max(...apres) <= 0.81 && Math.min(...apres) >= 0.79,
    `une image folle sur dix (3,2 Hz) ne passe pas : ${Math.min(...apres).toFixed(2)} à ${Math.max(...apres).toFixed(2)} Hz`);
  assert(b.voix[1].beatBrut === 0.8 || b.voix[1].beatBrut === 3.2, "l'écart brut reste lu dans beatBrut");
}
{
  const b = banc();
  // L'anche est prise 1,7 s sur la mauvaise raie (3 Hz) : l'enveloppe sûre, à 0,80 Hz, tranche.
  const lus = [];
  for (let i = 0; i < 80; i++) {
    const t = i * 0.085;
    const faux = t > 2 && t < 3.7;
    lus.push(b.image(t, faux ? 3.0 : 0.82, t > 1 ? ENV_SURE(0.8) : null));
  }
  const apres = lus.filter((_, i) => i * 0.085 > 1.4).map((v) => v.beatMeas);
  assert(Math.max(...apres) - Math.min(...apres) < 0.03 && Math.abs(moy(apres) - 0.8) < 0.02,
    `1,7 s sur la mauvaise raie (3 Hz) : le chiffre reste à ${moy(apres).toFixed(2)} Hz (±${(Math.max(...apres) - Math.min(...apres)).toFixed(3)})`);
  assert(lus.at(-1).beatSource === 'enveloppe', "la source est dite : 'enveloppe'");
}
{
  const b = banc();
  // Enveloppe « modulation » (rythme commun à tous les partiels) qui s'accorde avec l'écart : on garde l'écart.
  let v;
  for (let i = 0; i < 40; i++) v = b.image(i * 0.085, 0.8, { hz: 0.9, kind: 'modulation', sure: true, conf: 0.9 });
  assert(Math.abs(v.beatMeas - 0.8) < 1e-9 && v.beatSource === 'ecart',
    `enveloppe « modulation » à 0,9 Hz (12 % d'écart) : l'écart mesuré fait foi (${v.beatMeas.toFixed(2)} Hz, ${v.beatSource})`);
  // …mais en désaccord de plus de 40 % avec lui, c'est l'écart qui a pris une raie à côté.
  for (let i = 40; i < 80; i++) v = b.image(i * 0.085, 2.4, { hz: 1.2, kind: 'modulation', sure: true, conf: 0.9 });
  assert(Math.abs(v.beatMeas - 1.2) < 1e-9 && v.beatSource === 'enveloppe',
    `écart de 2,4 Hz contre une enveloppe à 1,2 Hz : l'enveloppe l'emporte (${v.beatMeas.toFixed(2)} Hz, ${v.beatSource})`);
}
{
  const b = banc([0, -1]);
  // 8'− (beatSign −1) sous le 8' : écart négatif, le signe est gardé avec l'enveloppe.
  let v;
  for (let i = 0; i < 40; i++) v = b.image(i * 0.085, -1.1, i > 5 ? ENV_SURE(1.15) : null);
  assert(Math.abs(v.beatMeas + 1.15) < 1e-9, `8'− : l'enveloppe garde le signe (${v.beatMeas.toFixed(2)} Hz)`);
}
{
  const b = banc();
  for (let i = 0; i < 20; i++) b.image(i * 0.085, 0.8, ENV_SURE(0.8));
  // La note s'arrête 2 s puis une autre commence : l'historique ne traverse pas le silence.
  const v = b.image(20 * 0.085 + 2, 1.9);
  assert(Math.abs(v.beatMeas - 1.9) < 1e-9 && v.beatSource === 'ecart',
    `après un silence de 2 s, rien de l'ancienne note ne reste (${v.beatMeas.toFixed(2)} Hz)`);
  assert(FUS_PAIR_S > 0, 'constantes exportées');
}

// ---- B 2 et B 3 : le vrai moteur -----------------------------------------------------------------

const F = at(66, 0);   // Fa#4, 370 Hz
// Établi = au-delà de 4 s de note ; battement affiché de la voix 8'+ (id « 8+ »).
function lecture(x, cfg = { mode: 'register', register: 'MM' }) {
  const im = rejoue(cfg, x).filter((i) => i.t > 4);
  const brut = [], aff = [];
  for (const i of im) {
    const v = voix(i, '8+');
    if (v?.tracked && v.beatMeas != null) { aff.push(v.beatMeas); brut.push(v.beatBrut ?? v.beatMeas); }
  }
  return { aff, brut };
}
// Trois raies à −Δ, 0, +Δ (une musette à trois anches jouée sous un registre MM), amplitudes A.
const peigne = (D, A, opts) => A.map((a, i) => ({ f: F + (i - 1) * D + D / 2, a, ...opts }));

console.log('\nB 2 — trois raies à ±Δ sous un registre MM : le battement reste Δ');
for (const [nom, D, A, opts, sons] of [
  ['Δ = 1,3 Hz, pression qui dérive de 3 ¢/s', 1.3, [0.7, 1, 0.7], { derive: 3, vib: 0.5 }, { graine: 4, rsb: 30, fv: 0.6 }],
  ['Δ = 1,1 Hz, trois raies égales', 1.1, [1, 1, 1], {}, { graine: 4, rsb: 30, fv: 0.6 }],
  ['Δ = 0,9 Hz, soufflet qui tremble de 3 ¢ à 0,6 Hz', 0.9, [0.3, 1, 0.6], { vib: 3 }, { graine: 4, rsb: 30, fv: 0.6 }],
]) {
  const { aff, brut } = lecture(anches(peigne(D, A, opts), 9, sons));
  const e = ecartType(aff), m = moy(aff);
  assert(aff.length > 30 && e < 0.05 && Math.abs(m - D) < 0.05,
    `${nom} : ${m.toFixed(3)} ± ${e.toFixed(3)} Hz affichés (vrai ${D}) ; écart brut ${moy(brut).toFixed(2)} ± ${ecartType(brut).toFixed(2)}`);
}

console.log('\nB 3 — deux anches nettes : rien ne change');
{
  const { aff } = lecture(anches([{ f: F }, { f: F + 0.8 }], 9, { graine: 3 }));
  assert(Math.abs(moy(aff) - 0.8) < 0.005 && ecartType(aff) < 0.005,
    `0,80 Hz → ${moy(aff).toFixed(3)} ± ${ecartType(aff).toFixed(4)} Hz`);
}
{
  const { aff } = lecture(anches([{ f: F, vib: 3, derive: 3 }, { f: F + 1.5, a: 0.8, vib: 3, derive: 3 }], 9, { graine: 5, rsb: 25, fv: 0.4 }));
  assert(Math.abs(moy(aff) - 1.5) < 0.05 && ecartType(aff) < 0.05,
    `1,5 Hz avec vibrato et dérive → ${moy(aff).toFixed(3)} ± ${ecartType(aff).toFixed(3)} Hz`);
}

console.log(failures === 0 ? '\nTous les tests du battement passent.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
