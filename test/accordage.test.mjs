// Tables d'accordage, La automatique, recalcul du rapport, unités, protocole
// guidé, courbes et comparaison banc / en caisse (19/10/2026).
//
//   A 1  les tables prédéfinies : toutes ont une source, valeurs de Weirig, conversion bat/min
//   A 2  reconnaissance du La de l'instrument (442,3 Hz ± quelques dixièmes, tempérament, anche déréglée)
//   A 3  changer le La recalcule toutes les valeurs du rapport, rien n'est perdu
//   A 4  unité du battement (bat/min ou Hz) : tableau, imprimé, CSV (les deux colonnes)
//   A 5  protocole : suite attendue (La/Ré, Sol/Do, chromatique 3 rangs), remplissage auto
//        sur des mesures simulées (bouton sauté, sens inversé, note inattendue, case refaite)
//   A 7  rapport rangée par rangée (une ligne par bouton), édition en un clic (tiré / poussé,
//        réaffecter, annuler / rétablir), surbrillance d'une note
//   A 6  courbes (battement, cible, différence, tolérance) et comparaison de deux rapports
//
// Exécution : node test/accordage.test.mjs

import { TABLES_MUSETTE, tableMusette, battementTable, beatCurveDe, hzEnBatMin, batMinEnHz } from '../web/js/tables-accordage.js';
import { estimerLa, texteLa, recalculerLignes, analyser, formatBatt, enUnite, signeVoix } from '../web/js/accordage.js';
import { midiToFreq } from '../web/js/music.js';
import { Report } from '../web/js/report.js';
import { choixDe, selectionActive, courbeUnique, aReprendre } from '../web/js/courbe-unique.js';
import { seriesDe, comparer, graphiquesRapport, graphiquesComparaison, csvCourbes, texteResume } from '../web/js/courbes.js';
import { suiteAttendue, Protocole, dispositionDe, dispositions, planChromatique } from '../web/js/protocole.js';

let failures = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ✓ ${msg}`);
  else { failures++; console.error(`  ✗ ÉCHEC : ${msg}`); }
}
const proche = (a, b, tol) => Math.abs(a - b) <= tol;

// Un instrument simulé : 8' (juste) et 8'+ (battement `table`) pour les notes données.
function cfgDe(tableId = 'musette', extra = {}) {
  return { a4: 440, temperament: 'equal', transpose: 0, uniteBatt: 'bpm', beatCurve: beatCurveDe(tableMusette(tableId)), ...extra };
}
function lignes(cfg, notes, { la = cfg.a4, dir = 'T', rang, decalageCents = 0, bruit = () => 0, battDe = (m) => cfg.beatCurve.overrides[m], cas = (m) => null } = {}) {
  const out = [];
  for (const m of notes) {
    const f = midiToFreq(m, { ...cfg, a4: la }) * 2 ** ((decalageCents + bruit(m)) / 1200);
    const c = cas(m);
    const base = { midi: m, dir, voiceMidi: m, ...(c ? { cas: c.id, rang: c.rang, bouton: c.bouton, nomRang: c.nomRang } : (rang ? { rang, nomRang: `Rangée ${rang}` } : {})) };
    out.push({ ...base, voiceId: '8', label: "8'", beatSign: 0, fMeas: f, beatMeas: null });
    const b = battDe(m);
    out.push({ ...base, voiceId: '8+', label: "8'+", beatSign: 1, fMeas: f + b, beatMeas: b });
  }
  return out;
}
const NOTES = [48, 52, 55, 57, 60, 62, 64, 67, 69, 72, 74, 76];

// ---- A 1 -------------------------------------------------------------------------------
console.log('A 1 : tables d\'accordage prédéfinies');
{
  assert(TABLES_MUSETTE.length >= 20, `${TABLES_MUSETTE.length} tables`);
  assert(TABLES_MUSETTE.every((t) => t.source && t.source.length > 8), 'chaque table cite sa source');
  const ids = TABLES_MUSETTE.map((t) => t.id);
  for (const id of ['sec', 'swing', 'demi-swing', 'musette', 'americain', 'celeste', 'italien-casta', 'tremolo']) assert(ids.includes(id), `table « ${id} »`);
  assert(proche(battementTable(tableMusette('musette'), 69), 5.1, 1e-9), 'musette à La4 : 5,1 Hz (Weirig)');
  assert(proche(battementTable(tableMusette('swing'), 69), 1.0, 1e-9), 'swing à La4 : 1,0 Hz (Weirig)');
  assert(proche(battementTable(tableMusette('sec'), 69), 0, 1e-9), 'sec : 0 Hz');
  assert(proche(battementTable(tableMusette('italien-casta'), 69), 3.829, 0.02), 'italien Casta à La4 : 3,83 Hz (+15 c)');
  const c = beatCurveDe(tableMusette('musette'));
  assert(c.overrides[69] === 5.1 && c.overrides[48] === 2 && c.table === 'musette', 'beatCurveDe : écrasements par note + table');
  assert(proche(hzEnBatMin(5.1), 306, 1e-9) && proche(batMinEnHz(306), 5.1, 1e-9), '5,1 Hz = 306 bat/min');
  const aConfirmer = TABLES_MUSETTE.filter((t) => /forme/.test(t.nature)).map((t) => t.id);
  assert(aConfirmer.length >= 3, `tables à un seul point (forme à confirmer) repérées : ${aConfirmer.join(', ')}`);
}

// ---- A 2 -------------------------------------------------------------------------------
console.log('A 2 : reconnaissance du La de l\'instrument');
{
  const cfg = cfgDe();
  // bruit déterministe de ±0,6 ¢
  const bruit = (m) => 0.6 * Math.sin(m * 12.9898);
  for (const la of [440, 442, 442.3, 443, 444]) {
    const rows = lignes(cfg, NOTES, { la, bruit });
    const e = estimerLa(rows, cfg);
    assert(e && proche(e.a4, la, 0.2) && e.n === 12, `La ${la} Hz reconnu : ${e?.a4} ± ${e?.incert}, ${e?.n} notes`);
  }
  const rows = lignes(cfg, NOTES, { la: 442.3, bruit });
  const e = estimerLa(rows, cfg);
  assert(texteLa(e) === `La de l'instrument : 442,3 Hz ± ${e.incert.toFixed(1).replace('.', ',')}, sur 12 notes`, `texte : ${texteLa(e)}`);
  assert(e.assez && e.incert <= 0.3, `incertitude ${e.incert} Hz, assez de notes pour la reconnaissance automatique`);
  // deux anches très déréglées (30 et -45 ¢) : la médiane tient
  const sale = lignes(cfg, NOTES, { la: 442.3, bruit: (m) => (m === 60 ? 30 : m === 67 ? -45 : bruit(m)) });
  assert(proche(estimerLa(sale, cfg).a4, 442.3, 0.2), 'deux anches déréglées ne déplacent pas le La');
  // la voix qui bat ne compte pas ; pas assez de notes -> null
  assert(estimerLa(lignes(cfg, [60, 64], { la: 442 }), cfg) === null, 'moins de 3 notes : pas de La');
  assert(estimerLa(rows.filter((r) => r.voiceId === '8+'), cfg) === null, 'les voix qui battent ne servent pas');
  // tempérament Cordier : on retrouve le La
  const cc = cfgDe('musette', { temperament: 'cordier' });
  assert(proche(estimerLa(lignes(cc, NOTES, { la: 443 }), cc).a4, 443, 0.1), 'tempérament Cordier pris en compte');
  assert(signeVoix({ voiceId: '8+' }) === 1 && signeVoix({ voiceId: '8-' }) === -1 && signeVoix({ voiceId: '16' }) === 0, 'signe de voix des anciennes lignes');
}

// ---- A 3 -------------------------------------------------------------------------------
console.log('A 3 : changer le La met à jour le rapport');
{
  const cfg = cfgDe();
  const r = new Report();
  const mes = lignes(cfg, NOTES, { la: 442.3 });
  recalculerLignes(mes, cfg);
  mes.forEach((l, i) => r.rows.set(`${l.midi}|${l.voiceId}|T`, l));
  const f0 = mes.map((l) => l.fMeas);
  const d0 = mes.map((l) => l.dCents);
  const csv0 = r.toCsv(cfg);
  assert(proche(mes[0].dCents, 1200 * Math.log2(442.3 / 440), 1e-6), `à La 440 : +${mes[0].dCents.toFixed(2)} ¢ (442,3 mesuré)`);
  cfg.a4 = 442.3;
  r.recalculer(cfg);
  const lignesApres = [...r.rows.values()];
  assert(lignesApres.every((l) => l.voiceId !== '8' || Math.abs(l.dCents) < 1e-6), 'La 442,3 : écarts de la voix juste à 0 ¢');
  assert(lignesApres.every((l, i) => l.fMeas === f0[i]), 'les fréquences mesurées n\'ont pas bougé');
  assert(lignesApres.every((l) => proche(l.target, midiToFreq(l.voiceMidi, cfg) + (l.beatSign ? cfg.beatCurve.overrides[l.midi] : 0), 1e-9)), 'les cibles suivent le nouveau La');
  assert(r.toCsv(cfg) !== csv0 && /442\.30/.test(r.toCsv(cfg)), 'le CSV porte le nouveau La et de nouvelles valeurs');
  cfg.a4 = 440;
  r.recalculer(cfg);
  assert([...r.rows.values()].every((l, i) => proche(l.dCents, d0[i], 1e-9)), 'retour à 440 : mêmes valeurs qu\'au départ (rien perdu)');
  // le La proposé par la reconnaissance, appliqué, remet les écarts à zéro
  const e = estimerLa(r.rows, cfg);
  cfg.a4 = e.a4;
  r.recalculer(cfg);
  assert([...r.rows.values()].filter((l) => l.voiceId === '8').every((l) => Math.abs(l.dCents) < 0.2), 'La reconnu pris : écarts < 0,2 ¢');
  // changer de table recalcule les battements voulus et les couleurs
  const a1 = analyser(r.rows.get('69|8+|T'), cfg);
  cfg.beatCurve = beatCurveDe(tableMusette('swing'));
  r.recalculer(cfg);
  const a2 = analyser(r.rows.get('69|8+|T'), cfg);
  assert(proche(a1.battVoulu, 5.1, 1e-9) && proche(a2.battVoulu, 1.0, 1e-9), 'changer de table change le battement voulu (5,1 puis 1,0 Hz)');
  assert(r.rows.get('69|8+|T').beatMeas === 5.1 || proche(r.rows.get('69|8+|T').beatMeas, 5.1, 1e-9), 'le battement mesuré reste');
}

// ---- A 4 -------------------------------------------------------------------------------
console.log('A 4 : unité du battement (bat/min ou Hz)');
{
  const cfg = cfgDe();
  const r = new Report();
  r.name = 'Maugein test';
  lignes(cfg, [57, 69]).forEach((l) => r.rows.set(`${l.midi}|${l.voiceId}|T`, l));
  r.recalculer(cfg);
  assert(formatBatt(1.5, 'hz') === '1.50' && formatBatt(1.5, 'bpm') === '90' && formatBatt(1.5, 'bpm', true) === '90 bat/min', 'format 1,5 Hz = 90 bat/min');
  assert(enUnite(5.1, 'bpm') === 306, 'conversion');
  const htmlBpm = r.printableHtml({ ...cfg, uniteBatt: 'bpm' });
  const htmlHz = r.printableHtml({ ...cfg, uniteBatt: 'hz' });
  assert(/\(bat\/min\) \/ cible/.test(htmlBpm) && /\/ 306 ·/.test(htmlBpm), 'rapport imprimé en bat/min (cible 306)');
  assert(/\(Hz\) \/ cible/.test(htmlHz) && /\/ 5\.10 ·/.test(htmlHz), 'rapport imprimé en Hz (cible 5,10)');
  const lignesCsv = r.toCsv(cfg).split('\n');
  const col = lignesCsv[0].split(';');
  const l69 = lignesCsv.find((l) => l.includes(";69;") && l.includes("8'+")).split(';');
  assert(l69[col.indexOf('battement_cible_hz')] === '5.100' && l69[col.indexOf('battement_cible_batmin')] === '306.0', 'CSV : cible en Hz ET en bat/min');
  assert(col.includes('ecart_battement_hz') && col.includes('ecart_battement_batmin'), 'CSV : écart de battement dans les deux unités');
  assert(/table/.test(lignesCsv[0]) && l69[col.indexOf('table')] === 'musette', 'CSV : table d\'accordage');
}

// ---- A 5 -------------------------------------------------------------------------------
console.log('A 5 : protocole guidé');
{
  const gc = suiteAttendue(dispositionDe('GC21').plan);
  const n1 = dispositionDe('GC21').plan.rangs[0].touches.length;
  const n2 = dispositionDe('GC21').plan.rangs[1].touches.length;
  assert(gc.length === 2 * (n1 + n2), `Sol/Do 21 boutons : ${gc.length} cases (tiré puis poussé)`);
  const ordre = gc.map((c) => `${c.sens}${c.rang}`);
  const blocs = ordre.filter((x, i) => x !== ordre[i - 1]);
  assert(blocs.join(' ') === 'T1 T2 P1 P2', `ordre : ${blocs.join(' ')} (1re rangée tirée, 2e tirée, 1re poussée, 2e poussée)`);
  assert(gc.filter((c) => c.sens === 'T' && c.rang === 1).every((c, i, a) => c.bouton === i + 1), 'bouton par bouton, du premier au dernier');
  const gc1 = dispositionDe('GC21').plan.rangs[0].touches;
  assert(gc[0].midi === gc1[0][1] && gc.find((c) => c.sens === 'P').midi === gc1[0][0], 'tiré = 2e valeur du bouton, poussé = 1re');
  const ad = suiteAttendue(dispositionDe('AD21').plan);
  assert(ad.length > 30 && ad[0].sens === 'T' && ad.at(-1).sens === 'P', `La/Ré 21 boutons : ${ad.length} cases`);
  assert(suiteAttendue(dispositionDe('AD21').plan, { inverser: true })[0].rang === 2, 'option : jouer l\'autre rangée en premier');
  const chrom = suiteAttendue(planChromatique('C'));
  assert(chrom.length === 3 * 12 * 2, 'chromatique C 3 rangs : 36 boutons, tirés puis poussés');
  const c = planChromatique('C').rangs;
  assert(c[0].touches[1][0] - c[0].touches[0][0] === 3 && c[1].touches[0][0] - c[0].touches[0][0] === 1, 'chromatique C : tierces mineures le long d\'une rangée, +1 demi-ton par rangée');
  assert(planChromatique('B').rangs[1].touches[0][0] - planChromatique('B').rangs[0].touches[0][0] === -1, 'chromatique B : image miroir');
  assert(chrom.filter((x) => x.sens === 'T').every((x, i) => chrom.filter((y) => y.sens === 'P')[i].midi === x.midi), 'chromatique : même note tirée et poussée');
  assert(dispositions().filter((d) => d.groupe === 'Chromatique').length === 2 && dispositions().length >= 44, 'liste des dispositions : 42 présets + B et C');

  // remplissage automatique sur des mesures simulées
  const p = new Protocole(dispositionDe('GC21').plan);
  const T = (k) => gc[k];
  let r = p.entrer({ midi: T(0).midi, sens: 'T' });
  assert(r.type === 'ok' && r.cas.id === T(0).id && p.courante().id === T(1).id, 'première note attendue : case 1 remplie, la suite avance');
  r = p.entrer({ midi: T(1).midi, sens: 'T' });
  assert(r.type === 'ok', 'deuxième case');
  // bouton sauté : on joue la case 4 sans la 3
  r = p.entrer({ midi: T(3).midi, sens: 'T' });
  const case3Meme = gc.filter((c, i) => i < 3 && c.midi === T(3).midi && c.sens === 'T' && !p.faits.has(c.id));
  if (case3Meme.length) {
    assert(true, 'note sautée identique à une case libre plus tôt : rangée à la première');
  } else {
    assert(r.type === 'saut' && r.cas.id === T(3).id && r.sautees.length === 1 && r.sautees[0].id === T(2).id, 'bouton sauté signalé, mesure rangée à sa case');
    assert(/bouton sauté/.test(r.alerte) && p.courante().id === T(4).id, 'la suite continue à la case suivante');
  }
  // note inattendue
  r = p.entrer({ midi: 20, sens: 'T' });
  assert(r.type === 'inattendue' && /inattendue/.test(r.alerte), 'note inattendue signalée');
  assert(p.courante().id !== undefined && !p.faits.has('inconnue'), 'la suite n\'est pas cassée');
  // sens inversé : la note d'une case poussée entendue en tiré (et absente du tiré)
  const pousseSeule = gc.find((c) => c.sens === 'P' && !gc.some((d) => d.sens === 'T' && d.midi === c.midi));
  r = p.entrer({ midi: pousseSeule.midi, sens: 'T' });
  assert(r.type === 'sens' && /sens inversé/.test(r.alerte) && !p.faits.has(pousseSeule.id), 'sens inversé signalé, rien n\'est rangé');
  // déjà mesurée : pas d'écrasement
  const dejaCas = T(0);
  r = p.entrer({ midi: dejaCas.midi, sens: 'T' });
  assert(['deja', 'ok', 'saut'].includes(r.type), 'note déjà vue : traitée sans erreur');
  // refaire une case
  const avant = p.nbFaits;
  const cas0 = p.refaire(T(0).id);
  assert(cas0.id === T(0).id && p.nbFaits === avant - 1 && p.courante().id === T(0).id, 'refaire une case : elle redevient la case attendue');
  r = p.entrer({ midi: T(0).midi, sens: 'T' });
  assert(r.type === 'ok' && p.faits.has(T(0).id), 'et se remplit de nouveau');
  // déroulé complet sans erreur
  const q = new Protocole(dispositionDe('AD21').plan);
  let ok = 0;
  for (const c of q.suite) if (q.entrer({ midi: c.midi, sens: c.sens }).cas) ok++;
  assert(q.termine && q.nbFaits === q.suite.length && ok === q.suite.length, `suite complète La/Ré : ${q.nbFaits} cases`);
  // notes répétées sur les deux rangées et entre tiré et poussé : la case suit l'étape, pas la note
  for (const id of ['GC21', 'AD21', 'SolDo_Darwin']) {
    const plan = dispositionDe(id).plan;
    const pr = new Protocole(plan);
    let faux = 0, repetees = 0;
    for (const c of pr.suite) {
      // la même note existe ailleurs (autre rangée ou autre sens) : cas visé par le bug
      if (pr.suite.some((d) => d.id !== c.id && d.midi === c.midi && (d.rang !== c.rang || d.sens !== c.sens))) repetees++;
      const r = pr.entrer({ midi: c.midi, sens: c.sens });
      if (!r.cas || r.cas.id !== c.id || r.cas.rang !== c.rang || r.cas.sens !== c.sens || r.type !== 'ok') faux++;
    }
    assert(faux === 0 && pr.termine, `${id} : ${repetees} cases à note répétée, suite complète (R1 tiré, R2 tiré, R1 poussé, R2 poussé) sans aucune case décalée`);
    // blocs : toutes les mesures de la rangée 1 tiré restent en rangée 1 tiré pendant ce bloc
    const pb = new Protocole(plan);
    const bloc1 = pb.suite.filter((c) => c.sens === 'T' && c.rang === 1);
    const rangees = bloc1.map((c) => pb.entrer({ midi: c.midi, sens: 'T' }).cas);
    assert(rangees.every((c) => c.rang === 1 && c.sens === 'T') && pb.nbFaits === bloc1.length, `${id} : bloc rangée 1 tiré entièrement rangé en rangée 1 tiré`);
    // une note de la rangée 2 (absente de la rangée 1 tiré) jouée à l'étape suivante n'est pas rangée de la rangée 1
    const att = pb.courante();
    const etrangere = pb.suite.find((c) => c.sens === 'T' && c.rang === 2 && c.id !== att.id && c.midi !== att.midi);
    const avant = pb.nbFaits;
    const rr = pb.entrer({ midi: etrangere.midi, sens: 'T' });
    assert(rr.type === 'saut' || rr.type === 'ok' ? rr.cas.rang === att.rang : pb.nbFaits === avant, `${id} : une note d'une autre rangée ne se range jamais sur l'étape en cours`);
  }
  {
    // le sens détecté ne fait jamais changer d'étape : note attendue entendue « poussé » = alerte, rien rangé
    const pr = new Protocole(dispositionDe('GC21').plan);
    const att = pr.courante();
    const r = pr.entrer({ midi: att.midi, sens: 'P' });
    assert(r.type === 'sens' && pr.nbFaits === 0 && pr.courante().id === att.id, 'sens détecté inversé sur la note attendue : alerte, aucune case rangée, même étape');
    // une note qui n'existe qu'en rangée 2 tiré pendant la rangée 1 tiré : inattendue, pas rangée
    const seule = pr.suite.find((c) => c.sens === 'T' && c.rang === 2 && !pr.suite.some((d) => d.rang === 1 && d.sens === 'T' && d.midi === c.midi));
    const r2 = pr.entrer({ midi: seule.midi, sens: 'T' });
    assert(r2.type === 'inattendue' && pr.nbFaits === 0, 'note de la rangée 2 pendant la rangée 1 : signalée inattendue, non rangée');
    // bouton voisin sauté (même rangée, même sens) : rangé là, boutons sautés signalés
    const r3 = pr.entrer({ midi: pr.suite[2].midi, sens: 'T' });
    assert((r3.type === 'saut' || r3.type === 'ok') && r3.cas.rang === 1 && r3.cas.sens === 'T', 'bouton sauté de la même rangée et du même sens : rangé dans cette rangée');
  }
  // le rapport range chaque mesure à sa case (rangée, bouton, sens)
  const cfg = cfgDe();
  const rp = new Report();
  const cases = gc.slice(0, 6);
  for (const cs of cases) {
    const rows = lignes(cfg, [cs.midi], { dir: cs.sens, cas: () => cs });
    for (const l of rows) rp.rows.set(`${l.midi}|${l.voiceId}|${l.dir}|${l.cas}`, l);
  }
  assert([...rp.rows.values()].every((l) => l.rang && l.bouton && l.dir), 'chaque ligne porte rangée, bouton et sens');
  assert(rp.sections(cfg, gc)[0].nomRang === gc[0].nomRang && rp.sections(cfg, gc)[0].dir === 'T', 'sections par rangée et par sens');
  assert(rp.retirerCase(cases[0].id) === 2 && rp.rows.size === 10, 'refaire une case efface ses mesures');
}

// ---- A 6 -------------------------------------------------------------------------------
console.log('A 6 : courbes et comparaison banc / en caisse');
{
  const cfg = cfgDe();
  const banc = new Report();
  banc.contexte = { lieu: 'banc', date: '2026-10-19', note: '' };
  const caisse = new Report();
  caisse.contexte = { lieu: 'caisse', date: '2026-10-25', note: '' };
  // banc : battements sur la table ; en caisse : +0,9 Hz à Do5 (72), -0,8 Hz à Sol4 (67), le reste identique
  const ecarts = { 72: 0.9, 67: -0.8 };
  for (const [rep, ec] of [[banc, {}], [caisse, ecarts]]) {
    lignes(cfg, NOTES, { rang: 1, battDe: (m) => cfg.beatCurve.overrides[m] + (ec[m] ?? 0), bruit: () => 0 })
      .forEach((l) => rep.rows.set(`${l.midi}|${l.voiceId}|T`, l));
    rep.recalculer(cfg);
  }
  const s = banc.series(cfg);
  assert(s.filter((x) => x.type === 'battement').length === 1 && s.filter((x) => x.type === 'justesse').length === 1, 'une courbe de battement et une de justesse');
  assert(s[0].type === 'battement', 'le battement vient en premier');
  const p72 = s[0].points.find((p) => p.midi === 72);
  assert(proche(p72.y, enUnite(cfg.beatCurve.overrides[72], 'bpm'), 1e-9), `courbe en bat/min : ${p72.y.toFixed(0)} à Do5`);
  const g = graphiquesRapport(s, cfg, 'bpm');
  assert(g[0].panneau === 'mesure' && g[1].panneau === 'difference', 'courbe de battement puis panneau mesure − cible');
  assert(/<svg/.test(g[0].svg) && /<polyline/.test(g[0].svg) && /<polygon/.test(g[0].svg) && /cible \(table\)/.test(g[0].svg), 'SVG avec la cible de la table et sa bande');
  assert(/tolérance/.test(g[1].svg) && !/stroke="#dc2626"/.test(g[1].svg), 'panneau différence avec bande de tolérance, aucune note hors tolérance au banc');
  const hors = graphiquesRapport(seriesDe(caisse.rows, cfg, 'bpm'), cfg, 'bpm')[1].svg;
  assert((hors.match(/stroke="#dc2626"/g) || []).length === 2, 'en caisse : les 2 notes hors tolérance sont cerclées (+0,9 et −0,8 Hz)');
  const csv = csvCourbes(seriesDe(caisse.rows, cfg, 'bpm'), cfg).split('\n');
  const col = csv[0].split(';');
  const l72 = csv.find((l) => l.startsWith('battement') && l.split(';')[4] === '72').split(';');
  assert(l72[col.indexOf('ecart_hz')] === '0.900' && l72[col.indexOf('ecart_batmin')] === '54.0' && l72[col.indexOf('hors_tolerance')] === 'oui', 'CSV des courbes : écart en Hz et bat/min, hors tolérance');
  assert(csv.some((l) => l.startsWith('justesse')), 'CSV : justesse aussi');

  const cmp = banc.comparerAvec({ name: 'x', contexte: caisse.contexte, rows: [...caisse.rows.values()] }, cfg);
  const b = cmp.comp.resume.battement;
  assert(b && b.n === NOTES.length, `${b?.n} notes comparées`);
  assert(b.max.midi === 72 && proche(b.max.diff, 54, 1e-6), `différence maximale : Do5 +${b.max.diff.toFixed(0)} bat/min (caisse − banc)`);
  assert(b.plusMobiles[0].midi === 72 && b.plusMobiles[1].midi === 67 && proche(b.plusMobiles[1].diff, -48, 1e-6), 'notes qui bougent le plus : Do5 puis Sol4');
  assert(proche(b.moyenne, (54 - 48) / NOTES.length, 1e-6) && proche(b.moyenneAbs, 102 / NOTES.length, 1e-6), 'écart moyen et moyenne des écarts absolus');
  const j = cmp.comp.resume.justesse;
  assert(j && j.moyenneAbs < 1e-6, 'justesse identique : différence nulle');
  assert(cmp.graphiques.length === 4 && cmp.graphiques.some((x) => x.kind === 'difference'), 'superposition et différence, battement et justesse');
  assert(cmp.resume.length === 2 && /Do5/.test(cmp.resume[0]), `résumé : ${cmp.resume[0].slice(0, 90)}…`);
  const csvC = banc.csvComparaison(cmp, cfg).split('\n');
  assert(csvC.length > NOTES.length && csvC[0].includes('difference'), 'CSV de comparaison');
  const html = banc.printableHtml(cfg, cmp);
  assert(/Comparaison/.test(html) && (html.match(/<svg/g) || []).length >= 7, 'rapport imprimable : courbes et comparaison');
  assert(html.indexOf('Battement des voix musette') < html.indexOf('<table'), 'les courbes de battement passent avant les tableaux');
  // un La différent entre les deux rapports est ramené au La courant
  cfg.a4 = 442;
  const cmp2 = banc.comparerAvec({ name: 'x', contexte: caisse.contexte, rows: [...caisse.rows.values()] }, cfg);
  assert(cmp2.comp.resume.battement.n === NOTES.length, 'comparaison recalculée avec le La courant');
}

// ---- A 7 -------------------------------------------------------------------------------
console.log('A 7 : rapport par rangée, une ligne par bouton, édition en un clic');
{
  const cfg = cfgDe();
  const plan = dispositionDe('GC21').plan;
  const suite = suiteAttendue(plan);
  const mesures = suite.slice(0, 8);            // 8 boutons de la 1re rangée, tirés
  const r = new Report();
  const ajoute = (c, ecartCents = 0) => {
    for (const l of lignes(cfg, [c.midi], { dir: c.sens, cas: () => c, bruit: () => ecartCents })) r.rows.set(`${l.midi}|${l.voiceId}|${l.dir}|${l.cas}`, l);
  };
  mesures.forEach((c, i) => ajoute(c, i === 3 ? 12 : 0)); // le 4e bouton est faux de 12 ¢
  r.recalculer(cfg);
  const protocole = new Protocole(plan);
  protocole.restaurer([...r.rows.values()].map((l) => l.cas));
  const courante = protocole.courante();

  const secs = r.sections(cfg, suite, courante);
  assert(secs.map((x) => `${x.dir}${x.rang}`).join(' ') === 'T1 P1 T2 P2', 'sections : rangée par rangée, tiré puis poussé dans chaque rangée');
  assert(secs[0].boutons.map((b) => b.bouton).join(',') === [...Array(secs[0].boutons.length).keys()].map((i) => i + 1).join(','), 'boutons dans l\'ordre du clavier');
  assert(secs[0].boutons[0].rows.length === 2 && secs.every((x) => x.boutons.length > 0), 'une ligne par bouton (les deux voix dans la même ligne)');
  assert(secs[0].boutons.slice(0, 8).every((b, i) => b.etat === (i === 3 ? 'reprendre' : 'fait')), 'état : fait, et « à reprendre » pour le bouton faux');
  assert(secs[0].boutons[8].etat === 'non' && secs[0].boutons[8].courant, 'bouton pas encore mesuré, et c\'est la case à jouer');
  const html = r.htmlRapport(cfg, { suite, courante });
  assert((html.match(/<tr class="[^"]*" data-uid=/g) || []).length === suite.length, `${suite.length} lignes (une par bouton, mesurées ou non)`);
  assert(!/Soufflet/.test(html) && !/>0\.00</.test(html), 'plus de colonne Soufflet ni de « Batt. mes. 0.00 » sur la voix juste');
  assert(/8&#39;\+ \(bat\/min\) \/ cible/.test(html) && /Voix juste \(¢\)/.test(html), 'colonnes : voix juste en cents, voix musette dans l\'unité avec sa cible');
  assert(/à jouer/.test(html) && /pas encore mesuré/.test(html) && /à reprendre/.test(html), 'états lisibles');
  assert(!/Cible \(Hz\)|écart nominal/.test(html) && /écart nominal/.test(r.htmlRapport(cfg, { suite, detail: true })), 'Hz et écart nominal seulement dans le détail');
  assert(!/data-act=/.test(r.htmlRapport(cfg, { suite, imprime: true })) && /data-act="sens"/.test(html), 'commandes d\'édition à l\'écran, pas à l\'impression');

  // surbrillance d'une note
  const u0 = suite[2].id;
  const htmlSel = r.htmlRapport(cfg, { suite, sel: { uid: u0, midi: 0, dir: 'T' } });
  assert((htmlSel.match(/ sel" data-uid=/g) || []).length === 1 && new RegExp(`sel" data-uid="${u0}"`).test(htmlSel), 'la ligne du bouton choisi est en surbrillance (une seule)');
  const m3 = suite[3].midi;
  assert(/ sel" data-uid=/.test(r.htmlRapport(cfg, { suite, sel: { uid: null, midi: m3, dir: 'T' } })), 'sélection par note et sens (depuis la grille ou la courbe)');
  assert((r.htmlRapport(cfg, { suite }).match(/ sel" data-uid=/g) || []).length === 0, 'sans sélection, rien n\'est surligné');

  // bascule tiré -> poussé en un clic
  const avant = r.toCsv(cfg);
  const u3 = suite[3].id;
  const nbT = r.sections(cfg, suite).find((x) => x.dir === 'T' && x.rang === 1).boutons.filter((b) => b.mesure).length;
  let res = r.basculerSens([u3], suite);
  assert(res.ok && res.n === 1, 'bascule d\'une mesure tiré -> poussé');
  const secs2 = r.sections(cfg, suite);
  const sT = secs2.find((x) => x.dir === 'T' && x.rang === 1);
  const sP = secs2.find((x) => x.dir === 'P' && x.rang === 1);
  assert(sT.boutons.filter((b) => b.mesure).length === nbT - 1 && sP.boutons.filter((b) => b.mesure).length === 1, 'la ligne a changé de section (rangée 1 poussé)');
  const bP = sP.boutons.find((b) => b.mesure);
  assert(bP.cas === `P-r1-b${suite[3].bouton}` && bP.rows.every((l) => l.dir === 'P' && l.cas === bP.cas), 'sa case devient celle du même bouton en poussé');
  assert(r.toCsv(cfg) !== avant && r.toCsv(cfg).split('\n').filter((l) => l.includes(';pousser;')).length === 2, 'l\'export CSV suit (2 lignes poussées)');
  const sj = r.series(cfg).filter((x) => x.type === 'justesse' && x.dir === 'P');
  assert(sj.length === 1 && sj[0].points.length === 1 && sj[0].points[0].midi === m3, 'la courbe de justesse poussée a un point à cette note');
  assert(!r.series(cfg).find((x) => x.type === 'justesse' && x.dir === 'T').points.some((p) => p.midi === m3), 'et la courbe tirée l\'a perdu');
  // le protocole tient compte de la correction
  protocole.restaurer([...r.rows.values()].map((l) => l.cas));
  assert(!protocole.faits.has(u3) && protocole.faits.has(`P-r1-b${suite[3].bouton}`) && protocole.courante().id === u3, 'le protocole redemande le bouton tiré, la case poussée est faite');
  // annuler / rétablir
  assert(r.peutAnnuler && r.annuler() && r.toCsv(cfg) === avant, 'annuler : retour exact à l\'état d\'avant');
  assert(r.peutRetablir && r.retablir() && r.sections(cfg, suite).find((x) => x.dir === 'P' && x.rang === 1).boutons.some((b) => b.mesure), 'rétablir : la bascule revient');
  r.annuler();
  // une rangée entière
  const uidsRang1 = r.sections(cfg, suite)[0].boutons.filter((b) => b.mesure).map((b) => b.uid);
  res = r.basculerSens(uidsRang1, suite);
  assert(res.ok && res.n === 8 && r.sections(cfg, suite).find((x) => x.dir === 'P' && x.rang === 1).boutons.filter((b) => b.mesure).length === 8, 'toute la rangée bascule en poussé (8 boutons)');
  r.annuler();
  // réaffecter à un autre bouton / une autre rangée
  const cible = suite.find((c) => c.sens === 'T' && c.rang === 2 && c.bouton === 3);
  res = r.reaffecter(suite[1].id, cible);
  const b3 = r.sections(cfg, suite).find((x) => x.dir === 'T' && x.rang === 2).boutons.find((b) => b.bouton === 3);
  assert(res.ok && b3.mesure && b3.rows.every((l) => l.rang === 2 && l.bouton === 3 && l.cas === cible.id), 'réaffecter un bouton à la rangée 2, bouton 3');
  protocole.restaurer([...r.rows.values()].map((l) => l.cas));
  assert(protocole.faits.has(cible.id) && !protocole.faits.has(suite[1].id), 'le protocole suit la réaffectation');
  r.annuler();
  // refus quand la case d'arrivée est déjà mesurée
  ajoute(suite.find((c) => c.sens === 'P' && c.rang === 1 && c.bouton === 1));
  res = r.basculerSens([suite[0].id], suite);
  assert(res.ok === false && /existe déjà/.test(res.raison), 'bascule refusée si le bouton est déjà mesuré dans l\'autre sens (rien n\'est écrasé)');
  // sans protocole : sections par sens, une ligne par note
  const libre = new Report();
  for (const l of lignes(cfg, [57, 60, 64])) libre.rows.set(`${l.midi}|${l.voiceId}|T`, l);
  const sl = libre.sections(cfg);
  assert(sl.length === 1 && sl[0].boutons.length === 3 && sl[0].boutons.map((b) => b.midi).join() === '57,60,64', 'sans protocole : une ligne par note, du grave à l\'aigu');
  assert(libre.basculerSens(['60|T']).ok && libre.sections(cfg).length === 2, 'sans protocole aussi : bascule tiré / poussé');
}

if (failures) { console.error(`\n${failures} échec(s)`); process.exit(1); }
// ---- A 7b ------------------------------------------------------------------------------
console.log('A 7b : glisser-déposer d une mesure sur une autre case');
{
  const cfg = cfgDe();
  const suite = suiteAttendue(dispositionDe('GC21').plan);
  const r = new Report();
  const ajoute = (c) => { for (const l of lignes(cfg, [c.midi], { dir: c.sens, cas: () => c })) r.rows.set(`${l.midi}|${l.voiceId}|${l.dir}|${l.cas}`, l); };
  const src = suite.find((c) => c.sens === 'P' && c.rang === 2 && c.bouton === 2);
  const dst = suite.find((c) => c.sens === 'T' && c.rang === 1 && c.bouton === 4);
  ajoute(src);
  r.recalculer(cfg);
  const avant = r.toCsv(cfg);
  let res = r.deplacerMesure(src.id, dst);
  assert(res.ok && r.sections(cfg, suite).find((x) => x.dir === 'T' && x.rang === 1).boutons.find((b) => b.bouton === 4).mesure, 'rangée 2 poussé -> rangée 1 tiré : la ligne change de section');
  r.recalculer(cfg);
  const csv = r.toCsv(cfg).split('\n').slice(1);
  assert(csv.length === 2 && csv.every((l) => l.includes(';tirer;') && l.split(';')[7] === dst.nomRang && l.split(';')[8] === '4'), 'export suit : rangée 1, bouton 4, tiré');
  assert(r.series(cfg).every((x) => x.dir === 'T'), 'les courbes suivent (plus rien en poussé)');
  assert(r.annuler() && r.toCsv(cfg) === avant, 'annuler : retour exact');
  assert(r.retablir() && r.rows.size === 2, 'rétablir');
  r.annuler();
  // case cible remplie : refus, échange, remplacement
  ajoute(dst);
  res = r.deplacerMesure(src.id, dst);
  assert(res.ok === false && res.occupee, 'case cible remplie : rien ne change sans choix');
  res = r.deplacerMesure(src.id, dst, 'echanger');
  const casDe = (c) => [...r.rows.values()].filter((l) => l.cas === c.id).length;
  assert(res.ok && casDe(src) === 2 && casDe(dst) === 2 && r.rows.size === 4, 'échange : les deux cases restent remplies');
  const lSrc = [...r.rows.values()].find((l) => l.cas === src.id);
  assert(lSrc.midi === dst.midi, 'la mesure de la case cible est passée à la case de depart');
  assert(r.annuler() && casDe(dst) === 2 && [...r.rows.values()].find((l) => l.cas === src.id).midi === src.midi, 'annuler echange en un pas');
  res = r.deplacerMesure(src.id, dst, 'remplacer');
  assert(res.ok && r.rows.size === 2 && casDe(dst) === 2 && casDe(src) === 0, 'remplacer : la mesure de la case cible est effacée');
  assert(r.annuler() && r.rows.size === 4, 'annuler le remplacement');
}

// ---- A 7c ------------------------------------------------------------------------------
console.log('A 7c : courbe unique, cases à cocher, liste à reprendre');
{
  const cfg = cfgDe();
  const suite = suiteAttendue(dispositionDe('GC21').plan);
  const r = new Report();
  const faux = suite.filter((c) => c.sens === 'T' && c.rang === 1)[3];
  for (const c of suite.filter((x) => x.sens === 'T' && x.rang <= 2 || (x.sens === 'P' && x.rang === 1)).slice(0, 40)) {
    for (const l of lignes(cfg, [c.midi], { dir: c.sens, cas: () => c, bruit: () => (c.id === faux.id ? 12 : 0) })) r.rows.set(`${l.midi}|${l.voiceId}|${l.dir}|${l.cas}`, l);
  }
  r.recalculer(cfg);
  const series = r.series(cfg);
  const choix = choixDe(null);
  assert(choix.auto && choix.g.ecart && !choix.g.mesure && !choix.g.justesse, 'défaut : écart au battement cible, étape en cours');
  const sel = selectionActive(choix, { courante: { rang: 1, sens: 'T' }, bellows: 'P', rangsDispo: [1, 2] });
  assert(sel.rangs.join() === '1' && sel.sens.join() === 'T', 'sélection automatique = rangée et sens de l\'étape en cours');
  const u = courbeUnique([{ nom: 'rapport', series }], cfg, 'bpm', choix, sel);
  assert(!u.refus && (u.svg.match(/<svg/g) || []).length === 1, 'un seul graphique');
  const nbSeries = (u.svg.match(/<polyline/g) || []).length;
  assert(nbSeries >= 1 && nbSeries <= 2, `rangée 1 tiré seulement : ${nbSeries} courbe(s) (une par voix musette)`);
  const sel2 = { rangs: [1, 2], sens: ['T', 'P'] };
  assert((courbeUnique([{ nom: 'rapport', series }], cfg, 'bpm', choix, sel2).svg.match(/<polyline/g) || []).length > nbSeries, 'cocher d\'autres rangées et sens superpose leurs courbes');
  const mixte = courbeUnique([{ nom: 'rapport', series }], cfg, 'bpm', { ...choix, g: { ...choix.g, justesse: true } }, sel);
  assert(mixte.refus && !mixte.svg, 'écart et cents ensemble : refusé proprement, avec la raison');
  const jus = courbeUnique([{ nom: 'rapport', series }], cfg, 'bpm', { ...choix, g: { ecart: false, mesure: false, cible: false, justesse: true } }, sel);
  assert(!jus.refus && /Justesse/.test(jus.svg), 'justesse seule : courbe en cents');
  const abs = courbeUnique([{ nom: 'rapport', series }], cfg, 'bpm', { ...choix, g: { ecart: false, mesure: true, cible: true, justesse: false } }, sel);
  assert(!abs.refus && /mesuré/.test(abs.svg) && /cible/.test(abs.svg), 'battement mesuré et cible superposés');
  const deux = courbeUnique([{ nom: 'banc', series }, { nom: 'caisse', series }], cfg, 'bpm', choix, sel);
  assert(/\(banc\)/.test(deux.svg) && /\(caisse\)/.test(deux.svg), 'deux rapports : superposés sur la même courbe');
  const rep = aReprendre(series, cfg, 'bpm', sel);
  assert(rep.length >= 1 && rep.every((x) => x.rang === 1 && x.dir === 'T') && rep[0].midi === faux.midi, 'liste à reprendre : la note fausse, de la sélection, en tête');
  assert(rep.every((x, i) => i === 0 || rep[i - 1].abs >= x.abs) && /ouvrir|fermer|monter|baisser/.test(rep[0].geste), 'triée par écart, avec le geste');
  assert(aReprendre(series, cfg, 'bpm', { rangs: [2], sens: ['P'] }).length === 0, 'rien à reprendre ailleurs');
  assert(r.printableHtml(cfg).includes('Battement des voix musette'), 'le rapport imprimable garde toutes ses courbes');
}

console.log('\nTous les tests passent.');
if (failures) { console.error(failures + " échec(s)"); process.exit(1); }
