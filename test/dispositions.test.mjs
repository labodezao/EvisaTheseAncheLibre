// Dispositions de clavier des stages (web/js/plans-clavier.js) : TOUS les présets contre la référence
// Sol/Do (GC21, plan Loffet), transposée rang par rang (20/10/2026, bogue La/Ré : Do#6 au bouton 6
// et Do#7 au bouton 10 au lieu de Do#5 et Do#6).
//   D 1  la référence GC21 est celle du site (b1, b1', b6' et b10' corrigés)
//   D 2  chaque préset à deux rangs = GC21 transposé, bouton par bouton, poussé et tiré
//   D 3  chaque préset à trois rangs = suite diatonique de la tonique de chaque rang
//   D 4  contrôles physiques : notes croissantes, pas de saut de plus de 5 demi-tons, tiré/poussé à 7 demi-tons
//   D 5  les présets douteux (instruments réels) sont listés, jamais vérifiés à tort
//   D 6  le cas signalé par Ewen : La/Ré, rangée Ré, tiré
//
// Exécution : node test/dispositions.test.mjs

import { PLANS_CLAVIER } from '../web/js/plans-clavier.js';
import { REF_GC21, DOUTEUX, BOUTON1_PROPRE, verifierPlans, nomNote } from './outils/dispositions-reference.mjs';

let failures = 0;
function assert(cond, msg) {
  if (!cond) { failures++; console.error('ECHEC : ' + msg); } else console.log('ok : ' + msg);
}

const plans = PLANS_CLAVIER;
const ids = Object.keys(plans);

// D 1
const gc = plans.GC21.rangs;
assert(JSON.stringify(gc[0].touches) === JSON.stringify(REF_GC21.sol) && JSON.stringify(gc[1].touches) === JSON.stringify(REF_GC21.do),
  'GC21 du site = référence (Sol 11 boutons, Do 10 boutons)');
const sol = REF_GC21.sol.map((b) => nomNote(b[1]).replace(/\d/, '')).join(' ');
assert(sol === 'Do# Fa# La Do Mi Fa# La Do Mi Fa# La', `rang Sol, tiré : ${sol}`);

const r = verifierPlans(plans);
const lignes = (liste) => liste.slice(0, 12).map((e) => `${e.id} ${e.rang} ${e.sens} b${e.bouton} ${e.calcule ?? e.detail} (attendu ${e.attendu ?? '-'}) [${e.type}]`).join('\n  ');

// D 2 et D 3
assert(r.ecarts.length === 0, `aucun écart à la référence sur ${r.verifies.length} présets (${r.ecarts.length})${r.ecarts.length ? '\n  ' + lignes(r.ecarts) : ''}`);
const deux = r.verifies.filter((id) => plans[id].rangs.length === 2);
const trois = r.verifies.filter((id) => plans[id].rangs.length === 3);
assert(deux.length >= 18 && trois.length >= 8, `présets comparés : ${deux.length} à deux rangs, ${trois.length} à trois rangs`);
assert(['GC21', 'AD21', 'CF21', 'EbBb21', 'BE21', 'EA21', 'ABb21', 'FD21', 'CA21', 'GDA21', 'GCD33', 'SolDoFa33_12'].every((id) => r.verifies.includes(id)),
  'GC21, AD21, CF21, EbBb21 et les présets recalculés sont tous comparés');

// D 4
assert(r.physiques.length === 0, `contrôles physiques : ${r.physiques.length} défaut(s)${r.physiques.length ? '\n  ' + lignes(r.physiques) : ''}`);

// D 5
const inconnus = Object.keys(DOUTEUX).filter((id) => !ids.includes(id));
assert(inconnus.length === 0, 'chaque préset douteux existe');
assert(r.douteux.length + r.verifies.length === ids.length, `tous les présets sont vérifiés (${r.verifies.length}) ou listés douteux (${r.douteux.length}) : ${ids.length}`);
assert(BOUTON1_PROPRE.every((id) => ids.includes(id)), 'présets au bouton 1 propre (irlandais, Fa/Sib) présents');

// D 6
const nom = (m) => nomNote(m);
const ad = plans.AD21.rangs;
const ire = ad[1].touches.map((b) => nom(b[1]));
assert(ire.slice(1).join(' ') === 'Do#4 Mi4 Sol4 Si4 Do#5 Mi5 Sol5 Si5 Do#6', `La/Ré, rangée Ré, tiré : ${ire.join(' ')}`);
assert(!ire.includes('Do#7') && ire[5] === 'Do#5' && ire[9] === 'Do#6', 'plus de saut d\'octave aux boutons 6 et 10');
// toutes les tonalités à deux rangs : aucun tiré ne saute d'octave dans un rang (b2 à la fin)
for (const id of deux) for (const rg of plans[id].rangs) {
  const t = rg.touches.slice(1).map((b) => b[1]);
  assert(t.every((m, i) => i === 0 || (m - t[i - 1] > 0 && m - t[i - 1] <= 5)), `${id} ${rg.nom.trim()} : tiré croissant, sans saut`);
}

console.log(failures ? `\n${failures} échec(s)` : '\nTous les tests de dispositions passent.');
if (failures) process.exit(1);
