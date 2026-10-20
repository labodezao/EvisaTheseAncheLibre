// Réharmonisation : ajustement robuste du battement, courbe d'accordage de l'instrument,
// notes à retoucher (19/10/2026).
import { TABLES_MUSETTE, tableMusette, beatCurveDe, battementTable } from '../web/js/tables-accordage.js';
import { midiToFreq } from '../web/js/music.js';
import { Report } from '../web/js/report.js';
import { seriesDe } from '../web/js/courbes.js';
import { courbeUnique } from '../web/js/courbe-unique.js';
import { ajuster, ciblesDepuis, texteFit, MIN_NOTES } from '../web/js/reharmonisation.js';

let failures = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ✓ ${msg}`);
  else { failures++; console.error(`  ✗ ÉCHEC : ${msg}`); }
}
const cfgDe = (id = 'musette') => ({ a4: 440, temperament: 'equal', transpose: 0, uniteBatt: 'bpm', tolCents: 1, beatCurve: beatCurveDe(tableMusette(id)) });

// Un instrument qui suit la table (8' juste, 8'+ qui bat), 5 notes déréglées.
function instrument(cfg, notes, deregles = {}, dir = 'T', rang = 1) {
  const rows = new Map();
  notes.forEach((m, i) => {
    const f = midiToFreq(m, cfg);
    const b = cfg.beatCurve.overrides[m] * (deregles[m] ?? 1);
    const base = { midi: m, dir, voiceMidi: m, rang, nomRang: `Rangée ${rang}`, bouton: i + 1 };
    rows.set(`${m}|8|${dir}`, { ...base, voiceId: '8', label: "8'", beatSign: 0, fMeas: f, beatMeas: null });
    rows.set(`${m}|8+|${dir}`, { ...base, voiceId: '8+', label: "8'+", beatSign: 1, fMeas: f + b, beatMeas: b });
  });
  return rows;
}
const NOTES = Array.from({ length: 30 }, (_, i) => 48 + i * 1);

console.log('R 1 : un instrument qui suit la table musette, 5 notes déréglées');
{
  const cfg = cfgDe('musette');
  const mal = { 52: 1.5, 58: 0.6, 63: 1.7, 67: 0.55, 73: 1.45 };
  const rows = instrument(cfg, NOTES, mal);
  const series = seriesDe(rows, cfg, 'bpm');
  const res = ajuster(series, cfg);
  const f = res.fits.find((x) => x.type === 'battement' && x.voiceId === '8+' && x.dir === 'T');
  assert(res.assez && f, 'un ajustement par voix musette et par sens');
  assert(f.modele && ['cents', 'exp', 'quad'].includes(f.modele.id), `modèle choisi par critère d'information : ${f.modele.nom}`);
  const ecartsTable = NOTES.filter((m) => !mal[m]).map((m) => Math.abs(f.pred(m) / cfg.beatCurve.overrides[m] - 1));
  assert(Math.max(...ecartsTable) < 0.06, `l'ajustement retrouve la table (écart maximal ${(100 * Math.max(...ecartsTable)).toFixed(1)} %), les 5 notes déréglées ne le tirent pas`);
  const liste = f.retoucher.map((x) => x.midi).sort((a, b) => a - b);
  assert(liste.join() === Object.keys(mal).map(Number).join(), `la liste des notes à retoucher est exactement les 5 notes : ${liste.join(', ')}`);
  assert(f.retoucher.every((x, i, a) => i === 0 || (a[i - 1].rang ?? 1e9) < (x.rang ?? 1e9) || ((a[i - 1].rang ?? 1e9) === (x.rang ?? 1e9) && ((a[i - 1].bouton ?? 1e9) < (x.bouton ?? 1e9) || ((a[i - 1].bouton ?? 1e9) === (x.bouton ?? 1e9) && a[i - 1].midi <= x.midi)))), "triée dans l'ordre du clavier (rangée, bouton, note)");
  const g52 = f.retoucher.find((x) => x.midi === 52);
  const g58 = f.retoucher.find((x) => x.midi === 58);
  assert(/fermer/.test(g52.geste) && /ouvrir/.test(g58.geste), 'le geste : trop rapide = fermer, trop lent = ouvrir (avec monter / baisser l\'anche)');
  assert(f.ressemble[0].id === 'musette' && f.ressemble[0].pct >= 90, `ressemble à « ${f.ressemble[0].nom} » à ${f.ressemble[0].pct} %`);
  assert(f.parOctave > 1.2 && f.parOctave < 4, `pente : ×${f.parOctave.toFixed(2)} par octave`);
  assert(/ressemble à/.test(texteFit(f)) && /par octave/.test(texteFit(f)), 'texte lisible du résultat');
  const j = res.fits.find((x) => x.type === 'justesse');
  assert(j && j.retoucher.length === 0, 'voix juste parfaite : aucune note à retoucher');
  const cibles = ciblesDepuis(f, 48, 77, 1.1);
  assert(Math.abs(cibles[60] / f.pred(60) - 1.1) < 0.002, 'la courbe ajustée devient une cible, relevable de 10 %');
}

console.log('R 2 : autres tables, sens poussé, deux rangées');
{
  for (const id of ['swing', 'americain', 'celeste']) {
    const cfg = cfgDe(id);
    const mal = { 55: 1.8, 61: 0.5, 66: 1.9, 70: 0.45, 75: 1.7 };
    const series = seriesDe(instrument(cfg, NOTES, mal, 'P'), cfg, 'bpm');
    const f = ajuster(series, cfg).fits.find((x) => x.type === 'battement' && x.voiceId === '8+');
    const liste = f.retoucher.map((x) => x.midi).sort((a, b) => a - b).join();
    assert(f.dir === 'P' && liste === Object.keys(mal).join(), `${id} poussé : retrouve la table, exactement les 5 notes (${liste}) ; ressemble à « ${f.ressemble[0].nom} » ${f.ressemble[0].pct} %`);
  }
  const cfg = cfgDe('musette');
  const a = instrument(cfg, NOTES.slice(0, 15), {}, 'T', 1);
  const b = instrument(cfg, NOTES.slice(15), {}, 'T', 2);
  for (const [k, v] of b) a.set(k, v);
  const fits = ajuster(seriesDe(a, cfg, 'bpm'), cfg).fits.filter((x) => x.type === 'battement' && x.voiceId === '8+');
  assert(fits.length >= 1, 'deux rangées qui suivent la même loi : un ajustement');
  const trop = ajuster(seriesDe(instrument(cfg, NOTES.slice(0, MIN_NOTES - 1)), cfg, 'bpm'), cfg);
  assert(!trop.assez, `moins de ${MIN_NOTES} notes : pas d'ajustement`);
}

console.log('R 3 : voix juste (étirement)');
{
  const cfg = cfgDe('musette');
  const rows = instrument(cfg, NOTES);
  for (const r of rows.values()) if (r.voiceId === '8') r.fMeas *= 2 ** ((0.2 * (r.midi - 69) + (r.midi === 60 ? 9 : 0)) / 1200);
  const res = ajuster(seriesDe(rows, cfg, 'bpm'), cfg);
  const j = res.fits.find((x) => x.type === 'justesse');
  assert(j && j.retoucher.length === 1 && j.retoucher[0].midi === 60, 'justesse : étirement de la droite retrouvé, une seule note à retoucher (Do4)');
  assert(Math.abs(j.parOctaveCents - 2.4) < 0.4, `étirement : ${j.parOctaveCents.toFixed(1)} ¢ par octave (2,4 attendus)`);
}

console.log('R 4 : sur la courbe unique et dans le rapport imprimable');
{
  const cfg = cfgDe('musette');
  const mal = { 52: 1.5, 58: 0.6, 63: 1.7, 67: 0.55, 73: 1.45 };
  const rep = new Report();
  for (const [k, v] of instrument(cfg, NOTES, mal)) rep.rows.set(k, v);
  const series = rep.series(cfg);
  const aj = ajuster(series, cfg);
  const sel = { rangs: [1], sens: ['T'] };
  const ch = (g) => ({ auto: false, rangs: [1], sens: ['T'], sources: [], g: { ecart: false, mesure: false, cible: false, justesse: false, ajustee: false, ...g } });
  const abs = courbeUnique([{ nom: 'r', series }], cfg, 'bpm', ch({ mesure: true, ajustee: true }), sel, aj);
  assert(!abs.refus && /ajustée/.test(abs.svg) && /mesuré/.test(abs.svg), 'case « courbe ajustée » : la courbe ajustée se superpose au battement mesuré');
  const ec = courbeUnique([{ nom: 'r', series }], cfg, 'bpm', ch({ ecart: true, ajustee: true }), sel, aj);
  assert(!ec.refus && /ajustée/.test(ec.svg), 'avec l\'écart : écart à la courbe ajustée');
  assert(!courbeUnique([{ nom: 'r', series }], cfg, 'bpm', ch({ ajustee: true }), sel, aj).refus, 'la courbe ajustée seule s\'affiche');
  const html = rep.printableHtml(cfg);
  assert(/Réharmonisation/.test(html) && /Notes à retoucher/.test(html) && /ressemble à/.test(html), 'rapport imprimable : section réharmonisation, notes à retoucher');
}

if (failures) { console.error(`${failures} échec(s)`); process.exit(1); }
console.log('\nTous les tests de réharmonisation passent.');
