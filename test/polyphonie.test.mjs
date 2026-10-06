// Défauts de la séparation polyphonique, relevés sur les enregistrements
// d'Ewen (docs/POLYPHONIE-ESSAIS.md) et reproduits ici par des sons de
// synthèse : timbre d'anche (partiels qui décroissent, irréguliers), bruit
// blanc, petit vibrato de pression commun aux anches d'une note.
//
// Ces tests ÉCHOUENT EXPRÈS : chacun documente un défaut du moteur. Ils ne
// sont pas dans `npm test` ; on les lance par `npm run test:poly`. Chaque
// correction part d'un de ces tests (il doit passer après, sans casser
// `npm test`), puis le test devient un scénario permanent de dsp.test.mjs :
// D4, D1, D7, D2, D6, D9, D3 corrigés en v33 (scénarios 44 à 50). Restent D5
// (quinte en Automatique et Auto-anches) et D8 (cas dégénéré non reproduit,
// garde). Synthèse partagée : synthese-anches.mjs.
//
//   node test/polyphonie.test.mjs            tous les défauts
//   node test/polyphonie.test.mjs D5         seulement celui-là

import { noteLabel } from '../web/js/music.js';
import { SR, hasard, at, cents, timbre, anches, rejoue, voix, fmt } from './synthese-anches.mjs';

const choix = process.argv.slice(2);
let echecs = 0, passes = 0;

function verifie(cond, msg) {
  if (cond) { passes++; console.log(`  ✓ ${msg}`); } else { echecs++; console.error(`  ✗ DÉFAUT : ${msg}`); }
}
function defaut(id, titre, corps) {
  if (choix.length && !choix.includes(id)) return;
  console.log(`\n${id} — ${titre}`);
  corps();
}


// ---------------------------------------------------------------------------
defaut('D5', 'Quinte en Automatique et Auto-anches : note lue une octave sous la basse, la quinte devient une anche fantôme', () => {
  // Session d'Ewen, quintes Ré#4 + La#4 (256 s) et La#3 + Fa4 (476 s). La
  // période commune d'une quinte (3:2) est une octave sous la basse : la
  // note devient Ré#3 ; en Auto-anches La#4, qui vaut 3 x Ré#3 à +13,8 c,
  // tombe dans la bande d'unisson (±35 c) et prend une case : « 8'+ = Ré#3
  // +13,8 c », une anche qui n'existe pas.
  // En Automatique, la valeur saute de Ré#3 +13,8 c à +31 c, puis Mi3 −47 c.
  // Mécanisme : en auto et auto-anches, la note vient de la fondamentale
  // spectrale (coarse.js), qui explique toutes les raies par f/2 ; rien ne
  // vérifie que cette fondamentale a une énergie à elle (partiels impairs).
  const [m, c1, c5] = [63, 5, 15.7];
  const x = anches([{ f: at(m, c1), a: 0.8 }, { f: at(m + 7, c5), a: 1 }], 4, { graine: 17 });
  for (const cfg of [{ mode: 'reeds', reedOctaves: [0] }, { mode: 'auto' }]) {
    const imgs = rejoue(cfg, x).filter((im) => im.t > 2);
    let faux = 0, ex = null;
    for (const im of imgs) {
      for (const v of im.vs) {
        if (!v.tracked) continue;
        const ok = [at(m, c1), at(m + 7, c5)].some((f) => Math.abs(cents(v.fMeas, f)) < 1);
        if (!ok) { faux++; ex ??= `${noteLabel(v.midi).full} ${fmt(v.dCents)} c (${v.def.label ?? 'auto'})`; }
      }
    }
    verifie(faux === 0, `${cfg.mode} : ${faux} valeurs qui ne sont aucune des deux anches après 2 s${ex ? `, p. ex. ${ex}` : ''}`);
  }
});

// ---------------------------------------------------------------------------
defaut('D8', 'Cas dégénéré (noté le 06/10) : deux anches de même force, sans bruit, partiels en 1/n (NON REPRODUIT, garde)', () => {
  // Relevé en écrivant test/donnees.test.mjs : La4 en 8'+8', 440 et 442 Hz,
  // amplitudes EXACTEMENT égales, aucun bruit, partiels en 1/n : le 8' est
  // lu à −13 c au lieu de 0. Juste dès qu'on met un timbre d'anche et du
  // bruit. Essayé le 06/10 sur le moteur v30 (réglages de cfgMoteur : 8'+8',
  // réponse rapide, note verrouillée ; et aussi normal, précis, sous-espaces,
  // 8'−/8'/8'+ ; 6, 12, 20 et 49 partiels ; phases nulles ou au hasard ;
  // 2 et 3 s) : écart toujours sous 0,5 c, souvent 0,00. Le −13 c n'est PAS
  // reproduit : ce test passe, il reste comme garde. Deux raies de même
  // amplitude font une enveloppe qui s'annule à chaque battement et une
  // phase qui saute de π : c'est le cas limite de l'amas de phase.
  const n = SR * 3, x = new Float32Array(n);
  for (const f of [440, 442]) {
    for (let h = 1; h <= 6; h++) {
      const w = (2 * Math.PI * f * h) / SR;
      for (let i = 0; i < n; i++) x[i] += (0.25 / h) * Math.sin(w * i);
    }
  }
  const imgs = rejoue({ mode: 'register', register: 'MM', response: 'fast', lockNote: 69 }, x);
  const der = imgs[imgs.length - 1];
  const v8 = voix(der, '8'), v8p = voix(der, '8+');
  verifie(v8?.tracked && Math.abs(v8.dCents) < 0.1 && v8p?.tracked && Math.abs(cents(v8p.fMeas, 442)) < 0.1,
    `440 / 442 Hz égales, sans bruit : 8' lu ${fmt(v8?.tracked ? v8.dCents : null)} c (0), 8'+ lu ${fmt(v8p?.tracked ? cents(v8p.fMeas, 440) : null)} c (${fmt(cents(442, 440))})`);
});

console.log(echecs ? `\n${echecs} défaut(s) reproduit(s), ${passes} vérification(s) passée(s).` : `\nAucun défaut reproduit (${passes} vérifications).`);
process.exit(echecs ? 1 : 0);
