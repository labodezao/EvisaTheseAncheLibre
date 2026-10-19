// La courbe unique du rapport (Ewen, 19/10/2026) : UN graphique, des cases à
// cocher pour choisir ce qui s'y superpose (rangées, sens, grandeurs, et les
// deux rapports quand une comparaison est chargée) ; à côté, la liste courte
// « à reprendre ». Module pur (Node et navigateur). Les autres courbes
// (graphiquesRapport, graphiquesComparaison) restent dans le détail replié et
// dans le rapport imprimable : rien n'est retiré.

import { courbeSvg, bandeTable, bandeTolerance, PALETTE } from './courbes.js';
import { UNITES_BATT, enUnite, decimalesUnite } from './accordage.js';
import { noteLabel } from './music.js';

export const GRANDEURS = Object.freeze([
  { id: 'ecart', nom: 'écart au battement cible', groupe: 'ecart' },
  { id: 'mesure', nom: 'battement mesuré', groupe: 'absolu' },
  { id: 'cible', nom: 'battement cible', groupe: 'absolu' },
  { id: 'justesse', nom: 'justesse de la voix juste (¢)', groupe: 'cents' },
]);
const GROUPES = { ecart: 'écart (autour de zéro)', absolu: 'battement absolu', cents: 'cents' };

export const CHOIX_DEFAUT = Object.freeze({ auto: true, rangs: [], sens: [], g: { ecart: true, mesure: false, cible: false, justesse: false }, sources: [] });

// Fusionne un choix enregistré avec les défauts (réglages anciens ou absents).
export function choixDe(brut) {
  const c = brut && typeof brut === 'object' ? brut : {};
  return {
    auto: c.auto !== false,
    rangs: Array.isArray(c.rangs) ? c.rangs : [],
    sens: Array.isArray(c.sens) ? c.sens : [],
    g: { ...CHOIX_DEFAUT.g, ...(c.g ?? {}) },
    sources: Array.isArray(c.sources) ? c.sources : [],
  };
}

// Rangées et sens réellement affichés : ceux de l'étape en cours (auto) ou les cases cochées.
export function selectionActive(choix, { courante = null, bellows = 'T', rangsDispo = [] } = {}) {
  if (choix.auto) {
    return { rangs: courante ? [courante.rang] : rangsDispo, sens: [courante ? courante.sens : bellows] };
  }
  return { rangs: choix.rangs, sens: choix.sens };
}

// écart > 0 : battement trop rapide -> fermer ; < 0 -> ouvrir. Sur la voix aiguë (8'+),
// ouvrir = monter l'anche ; sur la grave (8'-), ouvrir = baisser.
const gesteBatt = (ecartHz, signe) => {
  const ouvrir = ecartHz < 0;
  const monter = (signe >= 0) === ouvrir;
  return `${ouvrir ? 'ouvrir' : 'fermer'} (${monter ? 'monter' : 'baisser'} l'anche)`;
};

// La liste « à reprendre » : notes hors tolérance de la sélection, triées par écart décroissant.
export function aReprendre(series, cfg, unite, sel) {
  const out = [];
  const tol = cfg.tolCents ?? 1;
  for (const s of series) {
    if (!sel.sens.includes(s.dir) || (s.rang != null && !sel.rangs.includes(s.rang))) continue;
    for (const p of s.points) {
      const note = noteLabel(p.midi + (cfg.transpose || 0)).full;
      if (s.type === 'battement' && p.hors) {
        out.push({ midi: p.midi, note, voix: s.label, rang: s.rang, dir: s.dir, bouton: p.bouton,
          ecart: enUnite(p.ecartHz, unite), unite: UNITES_BATT[unite], geste: gesteBatt(p.ecartHz, s.signe ?? 1), abs: Math.abs(enUnite(p.ecartHz, unite)) });
      } else if (s.type === 'justesse' && Math.abs(p.y) > tol) {
        out.push({ midi: p.midi, note, voix: s.label, rang: s.rang, dir: s.dir, bouton: p.bouton,
          ecart: p.y, unite: '¢', geste: `${p.y < 0 ? 'monter' : 'baisser'} l'anche`, abs: Math.abs(p.y) / Math.max(tol, 0.01) });
      }
    }
  }
  return out.sort((a, b) => b.abs - a.abs);
}

// Le graphique unique. `sources` : [{ nom, series }] (le rapport courant d'abord,
// puis le rapport comparé s'il est chargé). Rend { svg, refus } : `refus` est un
// message si les grandeurs cochées ne vont pas ensemble (échelles différentes).
export function courbeUnique(sources, cfg, unite, choix, sel) {
  const actives = GRANDEURS.filter((g) => choix.g[g.id]);
  if (!actives.length) return { svg: '', refus: 'Cochez au moins une grandeur à afficher.' };
  const groupes = new Set(actives.map((g) => g.groupe));
  if (groupes.size > 1) {
    return { svg: '', refus: `Ces grandeurs n'ont pas la même échelle (${[...groupes].map((x) => GROUPES[x]).join(' et ')}) : une seule famille à la fois sur un même graphique.` };
  }
  const groupe = [...groupes][0];
  const voix = (s) => String(s.voiceId);
  const listeVoix = [...new Set(sources.flatMap((x) => x.series.filter((s) => s.type === 'battement').map(voix)))].sort();
  const series = [];
  sources.forEach((src, si) => {
    for (const s of src.series) {
      if (!sel.sens.includes(s.dir) || (s.rang != null && !sel.rangs.includes(s.rang))) continue;
      const bat = s.type === 'battement';
      const rangIdx = Math.max(0, (s.rang ?? 1) - 1);
      const couleur = PALETTE[(rangIdx * 2 + (bat ? Math.max(0, listeVoix.indexOf(voix(s))) : 0)) % PALETTE.length];
      const court = `${s.rang != null ? `R${s.rang} ` : ''}${s.dir === 'P' ? 'poussé' : 'tiré'} ${s.label}${sources.length > 1 ? ` (${src.nom})` : ''}`;
      const base = { couleur, tirets: s.dir === 'P', creux: si > 0 };
      if (groupe === 'cents' && !bat) {
        series.push({ ...base, nom: court, points: s.points.map((p) => ({ midi: p.midi, y: p.y })) });
      } else if (bat && groupe === 'ecart') {
        series.push({ ...base, nom: court, points: s.points.map((p) => ({ midi: p.midi, y: enUnite(p.ecartHz, unite), hors: p.hors })) });
      } else if (bat && groupe === 'absolu') {
        if (choix.g.mesure) series.push({ ...base, nom: `${court} mesuré`, points: s.points.map((p) => ({ midi: p.midi, y: p.y, hors: p.hors })) });
        if (choix.g.cible) series.push({ ...base, tirets: false, pointille: true, nom: `${court} cible`, points: s.points.map((p) => ({ midi: p.midi, y: p.cible })) });
      }
    }
  });
  const tousPts = series.flatMap((s) => s.points);
  if (!tousPts.length) return { svg: '', refus: 'Aucune mesure pour cette sélection (rangée, sens).' };
  const mids = tousPts.map((p) => p.midi);
  const de = Math.min(...mids);
  const a = Math.max(...mids);
  const u = UNITES_BATT[unite];
  const spec = { series, transpose: cfg.transpose, largeur: 760, hauteur: 300 };
  const tol = cfg.tolCents ?? 1;
  if (groupe === 'ecart') Object.assign(spec, { titre: `Écart au battement cible (mesure − cible, ${u}) : cercle rouge = hors tolérance`, unite: u, bande: bandeTolerance(cfg, unite, de, a), bandeNom: 'tolérance', zero: true });
  else if (groupe === 'absolu') Object.assign(spec, { titre: `Battement (${u}) : mesure et cible de la table`, unite: u, bande: bandeTable(cfg, unite, de, a) });
  else Object.assign(spec, { titre: 'Justesse de la voix juste (cents)', unite: 'cents', zero: true,
    bande: Array.from({ length: a - de + 1 }, (_, i) => ({ midi: de + i, lo: -tol, hi: tol })), bandeNom: 'tolérance' });
  return { svg: courbeSvg(spec), refus: null, decimales: groupe === 'cents' ? 1 : decimalesUnite(unite) };
}
