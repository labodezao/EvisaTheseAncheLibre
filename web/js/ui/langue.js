// Langue de l'interface : français ou anglais (PolyReed se vend aussi hors de
// France, face à Peterson et Dirk's). Toute chaîne visible passe par `t(cle)` :
// les mots vivent dans deux dictionnaires plats, langues/fr.js et
// langues/en.js, qui ont exactement les mêmes clés (test/langue.test.mjs).
// Clé = quelques mots de français sans accent (« suivant », « a faire ») ;
// `{n}` dans un texte : un paramètre, t('voix n', { n: 2 }) -> « voix 2 ».
//
// Langue choisie : Réglages > Atelier (`reglages.langue`, 'fr' ou 'en') ;
// sans choix, celle du navigateur si c'est le français ou l'anglais, sinon
// l'anglais. Un changement recharge la page (Réglages) : les écrans sont
// construits une fois, avec les mots de la langue du moment.
//
// Règle pour le code : jamais de t() au chargement d'un module (Node lit les
// modules avant que le test choisisse sa langue) ; les objets de textes
// exportés passent par `textes()`, lus au moment où on s'en sert.
//
// Module pur côté Node (sans document ni stockage, il ne fait que traduire).

import { noteLabel } from '../music.js';
import fr from './langues/fr.js';
import en from './langues/en.js';

export const LANGUES = Object.freeze(['fr', 'en']);
const DICOS = { fr, en };
const CLE_REGLAGES = 'polyreed.reglages';

// Langue du navigateur (« fr-FR », « en-GB », « de ») : fr ou en, sinon en.
export function langueDuNavigateur(code) {
  const c = String(code ?? '').slice(0, 2).toLowerCase();
  return LANGUES.includes(c) ? c : 'en';
}

// Langue de départ : le réglage enregistré, sinon le navigateur.
export function langueDeDepart({ stockage = globalThis.localStorage, nav = globalThis.navigator } = {}) {
  try {
    const r = JSON.parse(stockage?.getItem(CLE_REGLAGES) || '{}');
    if (LANGUES.includes(r?.langue)) return r.langue;
  } catch { /* stockage indisponible : le navigateur décide */ }
  return langueDuNavigateur(nav?.language);
}

let courante = langueDeDepart();

export const langue = () => courante;

// Change la langue des textes lus ensuite ; la page suit (attribut lang,
// manifeste) quand il y a un document.
export function choisirLangue(l) {
  courante = LANGUES.includes(l) ? l : langueDuNavigateur(l);
  const doc = globalThis.document;
  if (doc?.documentElement) {
    doc.documentElement.lang = courante;
    const m = doc.querySelector?.('link[rel="manifest"]');
    if (m) m.setAttribute('href', courante === 'fr' ? 'manifest.json' : 'manifest-en.json');
  }
  return courante;
}

// Le texte de `cle` dans la langue choisie ; `params` remplit les {nom}.
// Clé absente de la langue : le français ; absente des deux : la clé elle-même
// (le test des clés la trouve avant qu'Ewen ne la voie).
export function t(cle, params) {
  let s = DICOS[courante][cle] ?? fr[cle] ?? cle;
  if (params) s = s.replace(/\{(\w+)\}/g, (m, k) => (params[k] != null ? String(params[k]) : m));
  return s;
}

// Le texte de `cle` dans une langue donnée, quelle que soit celle de
// l'interface (le gabarit du rapport reconnaît ses deux versions).
export function tDans(l, cle, params) {
  const avant = courante;
  courante = LANGUES.includes(l) ? l : 'en';
  try { return t(cle, params); } finally { courante = avant; }
}

// Objet de textes lus à la demande : textes({ titre: 'notes' }).titre vaut
// t('notes') au moment de la lecture (Object.values aussi).
export function textes(cles) {
  const o = {};
  for (const [nom, cle] of Object.entries(cles)) {
    Object.defineProperty(o, nom, { get: () => t(cle), enumerable: true });
  }
  return Object.freeze(o);
}

// Nom d'une note dans la langue : Do4, Ré#5 en français ; C4, D#5 en anglais.
export const nomNote = (midi) => noteLabel(midi, courante);

// Le sens du soufflet : la donnée reste 'tiré' ou 'poussé' (séquence, carnet,
// cases de L'instrument) ; seul le mot affiché change.
export const motSens = (sens) => (sens === 'tiré' ? t('tire') : sens === 'poussé' ? t('pousse') : String(sens ?? '')); // donnée

// Pour index.html : lang et manifeste dès le premier rendu.
choisirLangue(courante);
