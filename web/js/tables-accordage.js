// Tables d'accordage prédéfinies (musette, sec, swing, américain, céleste,
// italien, trémolo…) : le battement voulu du 8'+ contre le 8', note par note.
// Valeurs de PolyReed (docs/tables-musette.md : relevés et courbes
// d'atelier d'Arnold Weirig, Benetoux, Liberty Bellows, tableur d'Ewen),
// copiées avec leur source. Les tables « convention, forme à choisir » n'ont
// qu'un point à La4 (source) : leur forme « cents constants » est un choix par
// défaut, À CONFIRMER PAR EWEN. Module pur, testé sous Node.
//
// Conventions : La4 = 440 Hz ici (les luthiers français disent « La3 ») ;
// un battement = écart en Hz entre le 8'+ et le 8' ; 1 Hz = 60 bat/min ;
// c = 1200 log2(1 + b/f).
//
// Une table : { id, nom, description, source, nature, forme, points:
// [{ note, midi, hz }], asymetrie8moins, points8moins?, cents? }.
// Formes : 'morceaux' = exponentielle entre points voisins ; 'lineaire' =
// droite en Hz ; 'cents' = écart constant ; 'exp' = une exponentielle sur tous
// les points. Hors des points : on prolonge le segment du bout.
// Limite du moteur (music.js, beatSign) : le 8'- reçoit le même écart en Hz
// que le 8'+ ; `asymetrie8moins` et `points8moins` restent des données.

import { NOTE_NAMES_FR } from './music.js';

// « Do3 », « Fa#3 », « Ré5 » -> numéro MIDI (La4 = 69).
export function midiDeNote(note) {
  const m = /^(.+?)(-?\d+)$/u.exec(String(note).normalize('NFC').trim());
  const i = m ? NOTE_NAMES_FR.findIndex((n) => n.toLowerCase() === m[1].toLowerCase()) : -1;
  if (i < 0) throw new Error(`note inconnue : ${note}`);
  return (Number(m[2]) + 1) * 12 + i;
}

const pts = (liste) => liste.map(([note, hz]) => ({ note, midi: midiDeNote(note), hz }));

// Données (PolyReed web/js/ui/donnees/musettes.js, 19/10/2026)
const TABLES = [
  {
    id: "sec", nom: "Sec", forme: "morceaux", nature: "convention",
    description: "Aucun battement.",
    source: "Weirig ; Liberty Bellows (0 Hz)",
    points: [["Do3", 0], ["Sol3", 0], ["Do4", 0], ["Sol4", 0], ["La4", 0], ["Do5", 0], ["Sol5", 0], ["Do6", 0], ["Sol6", 0], ["Do7", 0]],
    asymetrie8moins: 1,
  },
  {
    id: "demi-swing", nom: "Demi-swing", forme: "morceaux", nature: "convention",
    description: "Weirig : plus léger que le swing (3 c à La4).",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 0.3], ["Sol3", 0.4], ["Do4", 0.6], ["Sol4", 0.8], ["La4", 0.8], ["Do5", 0.9], ["Sol5", 1.1], ["Do6", 1.3], ["Sol6", 1.4], ["Do7", 1.6]],
    asymetrie8moins: 1,
  },
  {
    id: "swing", nom: "Swing", forme: "morceaux", nature: "convention",
    description: "4 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 0.4], ["Sol3", 0.6], ["Do4", 0.7], ["Sol4", 0.9], ["La4", 1], ["Do5", 1.1], ["Sol5", 1.4], ["Do6", 1.6], ["Sol6", 1.9], ["Do7", 2.1]],
    asymetrie8moins: 1,
  },
  {
    id: "americain-doux", nom: "Américain doux", forme: "morceaux", nature: "convention",
    description: "« américain atténué », 6 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 0.7], ["Sol3", 0.8], ["Do4", 1], ["Sol4", 1.4], ["La4", 1.5], ["Do5", 1.8], ["Sol5", 2.3], ["Do6", 2.8], ["Sol6", 3.3], ["Do7", 3.8]],
    asymetrie8moins: 1,
  },
  {
    id: "americain", nom: "Américain", forme: "morceaux", nature: "convention",
    description: "7 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 0.8], ["Sol3", 1], ["Do4", 1.2], ["Sol4", 1.7], ["La4", 1.8], ["Do5", 2.1], ["Sol5", 2.8], ["Do6", 3.3], ["Sol6", 4], ["Do7", 4.5]],
    asymetrie8moins: 1,
  },
  {
    id: "americain-fort", nom: "Américain fort", forme: "morceaux", nature: "convention",
    description: "9 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 0.9], ["Sol3", 1.2], ["Do4", 1.6], ["Sol4", 2.2], ["La4", 2.4], ["Do5", 2.8], ["Sol5", 3.6], ["Do6", 4.3], ["Sol6", 5.4], ["Do7", 6.2]],
    asymetrie8moins: 1,
  },
  {
    id: "celeste-leger", nom: "Céleste léger", forme: "morceaux", nature: "convention",
    description: "« céleste très atténué », 12 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 1], ["Sol3", 1.5], ["Do4", 2], ["Sol4", 2.8], ["La4", 3.1], ["Do5", 3.5], ["Sol5", 4.4], ["Do6", 5.3], ["Sol6", 6.9], ["Do7", 8.3]],
    asymetrie8moins: 1,
  },
  {
    id: "celeste-doux", nom: "Céleste doux", forme: "morceaux", nature: "convention",
    description: "« céleste atténué », 14 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 1.1], ["Sol3", 1.9], ["Do4", 2.5], ["Sol4", 3.4], ["La4", 3.7], ["Do5", 4.3], ["Sol5", 5.8], ["Do6", 7], ["Sol6", 8.9], ["Do7", 10.7]],
    asymetrie8moins: 1,
  },
  {
    id: "celeste", nom: "Céleste", forme: "morceaux", nature: "convention",
    description: "19 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 1.3], ["Sol3", 2.3], ["Do4", 3], ["Sol4", 4.3], ["La4", 4.7], ["Do5", 5.4], ["Sol5", 7.4], ["Do6", 9], ["Sol6", 11.6], ["Do7", 13.7]],
    asymetrie8moins: 1,
  },
  {
    id: "musette", nom: "Musette", forme: "morceaux", nature: "convention",
    description: "Musette française, 20 c à La4 ; 3 voix : 8- symétrique.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 2], ["Sol3", 2.7], ["Do4", 3.4], ["Sol4", 4.6], ["La4", 5.1], ["Do5", 5.8], ["Sol5", 8], ["Do6", 10], ["Sol6", 13.7], ["Do7", 17.2]],
    asymetrie8moins: 1,
  },
  {
    id: "musette-forte", nom: "Musette forte", forme: "morceaux", nature: "convention",
    description: "« musette fort », 24 c à La4.",
    source: "Weirig, Guide de dépannage d'accordéons (PDF accarnoldw.com), p. 62 et 64, « courbes conventionnelles »",
    points: [["Do3", 2.4], ["Sol3", 3.3], ["Do4", 4.1], ["Sol4", 5.6], ["La4", 6.1], ["Do5", 7], ["Sol5", 9.5], ["Do6", 11.9], ["Sol6", 16.3], ["Do7", 20.3]],
    asymetrie8moins: 1,
  },
  {
    id: "musette-relevee", nom: "Musette relevée", forme: "morceaux", nature: "mesure",
    description: "Musette 3 voix vers 1985 (diapason 444), accord proposé par Weirig après relevé ; 8- plus lent que 8+.",
    source: "Weirig, Guide, p. 68 (relevé d'un instrument réel)",
    points: [["Do3", 1.9], ["Sol3", 2.5], ["Do4", 3], ["Sol4", 3.8], ["La4", 4.1], ["Do5", 4.6], ["Sol5", 5.9], ["Do6", 7.1], ["Sol6", 9.2], ["Do7", 11.1]],
    points8moins: [["Do3", 1.9], ["Sol3", 2.3], ["Do4", 2.7], ["Sol4", 3.4], ["La4", 3.6], ["Do5", 4], ["Sol5", 4.9], ["Do6", 5.8], ["Sol6", 7.2], ["Do7", 8.4]],
    asymetrie8moins: 0.85,
  },
  {
    id: "italien-casta", nom: "Italien Castagnari", forme: "cents", nature: "reglage Ewen",
    description: "8+ à +15 c constants au-dessus du 8', 8- symétrique en Hz (réglage d'Ewen).",
    source: "Tableur d'Ewen « Tempérament Cordier.xlsx » (2019), feuille « Italiano Cordier »",
    points: [["Sol3", 1.704], ["Do4", 2.275], ["Sol4", 3.411], ["La4", 3.829], ["Do5", 4.554], ["Sol5", 6.827], ["Do6", 9.117]],
    asymetrie8moins: 1, cents: 15,
  },
  {
    id: "benetoux-am-doux", nom: "Benetoux doux", forme: "lineaire", nature: "convention, de seconde main",
    description: "Deux points : Fa le plus grave et La le plus aigu d'un clavier 41 touches.",
    source: "Benetoux, Comprendre et réparer votre accordéon (éd. anglaise The Ins and Outs of the Accordion), cité par accordionrevival.pages.dev/accordion-repair3 ; livre non lu",
    points: [["Fa3", 0.7], ["La6", 3.5]],
    asymetrie8moins: 1,
  },
  {
    id: "benetoux-am", nom: "Benetoux américain", forme: "lineaire", nature: "convention, de seconde main",
    description: "Deux points : Fa le plus grave et La le plus aigu d'un clavier 41 touches.",
    source: "Benetoux, Comprendre et réparer votre accordéon (éd. anglaise The Ins and Outs of the Accordion), cité par accordionrevival.pages.dev/accordion-repair3 ; livre non lu",
    points: [["Fa3", 0.9], ["La6", 4.2]],
    asymetrie8moins: 1,
  },
  {
    id: "benetoux-mus-legere", nom: "Benetoux léger", forme: "lineaire", nature: "convention, de seconde main",
    description: "Deux points : Fa le plus grave et La le plus aigu d'un clavier 41 touches.",
    source: "Benetoux, Comprendre et réparer votre accordéon (éd. anglaise The Ins and Outs of the Accordion), cité par accordionrevival.pages.dev/accordion-repair3 ; livre non lu",
    points: [["Fa3", 1.6], ["La6", 5.3]],
    asymetrie8moins: 1,
  },
  {
    id: "benetoux-musette", nom: "Benetoux musette", forme: "lineaire", nature: "convention, de seconde main",
    description: "Deux points : Fa le plus grave et La le plus aigu d'un clavier 41 touches.",
    source: "Benetoux, Comprendre et réparer votre accordéon (éd. anglaise The Ins and Outs of the Accordion), cité par accordionrevival.pages.dev/accordion-repair3 ; livre non lu",
    points: [["Fa3", 2.2], ["La6", 7]],
    asymetrie8moins: 1,
  },
  {
    id: "tremolo", nom: "Trémolo", forme: "cents", nature: "convention, forme à choisir",
    description: "4 Hz = 15 c à La4 ; forme hors source.",
    source: "Liberty Bellows, General Accordion Questions (libertybellows.com) ; un seul point, à La4",
    points: [["La4", 4]],
    asymetrie8moins: 1, cents: 15,
  },
  {
    id: "italien-vif", nom: "Italien vif", forme: "cents", nature: "convention, forme à choisir",
    description: "6 Hz = 22 c à La4 ; forme hors source.",
    source: "Liberty Bellows, General Accordion Questions (libertybellows.com) ; un seul point, à La4",
    points: [["La4", 6]],
    asymetrie8moins: 1, cents: 22,
  },
  {
    id: "ecossais", nom: "Écossais", forme: "cents", nature: "convention, forme à choisir",
    description: "7 Hz = 25 c à La4 ; forme hors source.",
    source: "Liberty Bellows, General Accordion Questions (libertybellows.com) ; un seul point, à La4",
    points: [["La4", 7]],
    asymetrie8moins: 1, cents: 25,
  },
  {
    id: "irlandais", nom: "Irlandais", forme: "cents", nature: "convention, forme à choisir",
    description: "2 Hz = 7 c à La4 ; forme hors source.",
    source: "Liberty Bellows, General Accordion Questions (libertybellows.com) ; un seul point, à La4",
    points: [["La4", 2]],
    asymetrie8moins: 1, cents: 7,
  },
];

export const TABLES_MUSETTE = Object.freeze(TABLES.map((t) => Object.freeze({
  ...t,
  points: pts(t.points),
  ...(t.points8moins ? { points8moins: pts(t.points8moins) } : {}),
})));

export const tableMusette = (id) => TABLES_MUSETTE.find((x) => x.id === id) ?? null;

// Conversions d'unité du battement : 1 Hz = 60 bat/min.
export const hzEnBatMin = (hz) => (hz == null ? null : hz * 60);
export const batMinEnHz = (bpm) => (bpm == null ? null : bpm / 60);

// ---- Courbes -------------------------------------------------------------------

// Moindres carrés de ln(hz) contre la note, sur les points non nuls.
export function ajustementExp(points) {
  const p = points.filter((x) => x.hz > 0);
  if (p.length < 2) return null;
  const n = p.length;
  const mx = p.reduce((s, x) => s + x.midi, 0) / n;
  const my = p.reduce((s, x) => s + Math.log(x.hz), 0) / n;
  let sxy = 0;
  let sxx = 0;
  for (const x of p) {
    sxy += (x.midi - mx) * (Math.log(x.hz) - my);
    sxx += (x.midi - mx) ** 2;
  }
  if (sxx === 0) return null;
  const b = sxy / sxx;
  return { a: my - b * mx, b };
}

function entre(p, midi, geometrique) {
  if (p.length === 1) return p[0].hz;
  let i = p.findIndex((x) => x.midi > midi) - 1;
  if (i < 0) i = midi < p[0].midi ? 0 : p.length - 2;
  const [g, d] = [p[i], p[i + 1]];
  const t = (midi - g.midi) / (d.midi - g.midi);
  if (geometrique && g.hz > 0 && d.hz > 0) return g.hz * (d.hz / g.hz) ** t;
  return g.hz + (d.hz - g.hz) * t;
}

// Battement voulu en Hz pour une note, selon la forme de la table.
export function battementTable(table, midi, { voix = '8+', a4 = 440 } = {}) {
  const moins = voix === '8-';
  const p = moins && table.points8moins ? table.points8moins : table.points;
  const facteur = moins && !table.points8moins ? (table.asymetrie8moins ?? 1) : 1;
  let hz;
  if (table.forme === 'cents') {
    hz = a4 * 2 ** ((midi - 69) / 12) * (2 ** (table.cents / 1200) - 1);
  } else if (table.forme === 'exp') {
    const f = ajustementExp(p);
    hz = f ? Math.exp(f.a + f.b * midi) : entre(p, midi, false);
  } else {
    hz = entre(p, midi, table.forme === 'morceaux');
  }
  return Math.max(0, hz * facteur);
}

const MIDI_BAS = 48;  // Do3 : ancrages comme la courbe par défaut de music.js
const MIDI_HAUT = 96; // Do7
const arrondi = (x) => Math.round(x * 100) / 100;

// `beatCurve` (celui que music.js lit : midiLow, bLow, midiHigh, bHigh,
// overrides) d'une table : les ancrages et un écrasement par note de Do2 à Mi7.
export function beatCurveDe(table, { de = 36, a = 100, voix, a4 } = {}) {
  const opt = { voix, a4 };
  const ancre = (m) => Math.max(0.01, arrondi(battementTable(table, m, opt)));
  const courbe = { midiLow: MIDI_BAS, bLow: ancre(MIDI_BAS), midiHigh: MIDI_HAUT, bHigh: ancre(MIDI_HAUT), overrides: {}, table: table.id };
  for (let m = de; m <= a; m++) courbe.overrides[m] = arrondi(battementTable(table, m, opt));
  return courbe;
}
