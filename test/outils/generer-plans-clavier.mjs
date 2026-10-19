// Génère web/js/plans-clavier.js à partir des présets de l'outil « Plan de
// claviers » du site des stages (dépôt stages-lutherie,
// outils/clavier-accordeon/presets/*.json), lus en lecture seule.
// Même conversion que PolyReed (outils/plans-clavier.mjs) : noms français ->
// MIDI (La4 = 69), un bouton = [poussé, tiré]. Main droite seulement.
//   node test/outils/generer-plans-clavier.mjs "<dossier des presets>"
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const CLASSES = { do: 0, 're': 2, 'ré': 2, mi: 4, fa: 5, sol: 7, la: 9, si: 11 };
export function midiDe(nom) {
  const m = /^(do|ré|re|mi|fa|sol|la|si)(#|b|♭)?(-?\d)$/i.exec(String(nom ?? '').trim());
  if (!m) return null;
  const alt = m[2] === '#' ? 1 : m[2] ? -1 : 0;
  return 12 * (Number(m[3]) + 1) + CLASSES[m[1].toLowerCase()] + alt;
}

const dossier = process.argv[2];
const index = JSON.parse(readFileSync(join(dossier, 'index.json'), 'utf8'));
const infos = new Map(index.map((x) => [x.id, x]));
const plans = {};
for (const f of readdirSync(dossier).sort()) {
  if (!f.endsWith('.json') || f === 'index.json') continue;
  const id = f.replace(/\.json$/, '');
  const plan = JSON.parse(readFileSync(join(dossier, f), 'utf8'));
  const info = infos.get(id) ?? {};
  plans[id] = {
    nom: info.label ?? plan.nom ?? id,
    categorie: info.category ?? null,
    rangs: (plan.notes?.droite ?? []).map((rangee, r) => ({
      nom: plan.rangees?.[r]?.nom ?? `rang ${r + 1}`,
      touches: rangee.map((b) => [midiDe(b?.p), midiDe(b?.t)]),
    })),
  };
}
const ici = resolve(fileURLToPath(new URL('.', import.meta.url)));
const sortie = join(ici, '..', '..', 'web', 'js', 'plans-clavier.js');
const texte = `// Dispositions de clavier diatonique des stages d'Ewen, main droite.
// Source : dépôt labodezao/stages-lutherie, outils/clavier-accordeon/presets/*.json
// (outil « Plan de claviers » du site des stages), converti par
// test/outils/generer-plans-clavier.mjs. Fichier produit : ne pas modifier à la main.
// Un plan : { nom, categorie, rangs: [{ nom, touches: [[poussé, tiré]] }] }.
// Notes MIDI (La4 = 69), null : case absente. Les rangs sont dans l'ordre du préset.

export const PLANS_CLAVIER = Object.freeze(${JSON.stringify(plans, null, 0).replace(/},"/g, '},\n  "')});
`;
writeFileSync(sortie, texte);
console.log(Object.keys(plans).length, 'plans écrits');
