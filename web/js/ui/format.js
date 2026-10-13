// Mise en forme des nombres de l'interface. Module pur, testé sous Node.
// Une seule fonction pour les cents (Accorder, Le carnet, L'anche, Réglages,
// CSV, rapport) : partout la même règle de décimales et la même unité, « ¢ ».
// Séparateur décimal de la langue (langue.js) : virgule en français, point en
// anglais. Le tableur (CSV) garde ses règles : virgule, moins ASCII.

import { langue } from './langue.js';

const MOINS = '−'; // signe moins typographique, plus lisible de loin que « - »
export const CENTS = '¢';

// Séparateur décimal de la langue : ',' ou '.'.
export const separateur = () => (langue() === 'fr' ? ',' : '.');

// Nombre à `d` décimales avec le séparateur de la langue : « 2,40 » ou « 2.40 ».
// `tableur` : la virgule du CSV, quelle que soit la langue. Pas de signe ajouté.
export function nombre(x, d = 0, { tableur = false } = {}) {
  const s = Number(x).toFixed(d);
  return tableur || langue() === 'fr' ? s.replace('.', ',') : s;
}

// Nombre avec le moins typographique (« −2,8 ») : jamais « −0,0 ».
export function nombreSigne(x, d = 0) {
  let r = Number(Number(x).toFixed(d));
  if (r === 0) r = 0;
  return `${r < 0 ? MOINS : ''}${nombre(Math.abs(r), d)}`;
}

// Nombre tel qu'il s'écrit, sans zéros inutiles (« 0,3 », « 12 ») : String(x)
// avec le séparateur de la langue.
export const nombreLibre = (x) => (langue() === 'fr' ? String(x).replace('.', ',') : String(x));

// Entier avec les milliers de la langue (« 48 000 » ou « 48,000 »).
export const entier = (n) => Math.round(n).toLocaleString(langue() === 'fr' ? 'fr-FR' : 'en-GB');

// Dates de la langue : « 6 octobre 2026 » ou « 6 October 2026 » ; courte :
// « 06/10/2026 » dans les deux langues (le jour d'abord, comme l'atelier).
const LOCALE = () => (langue() === 'fr' ? 'fr-FR' : 'en-GB');
export const dateLongue = (d) => new Date(d).toLocaleDateString(LOCALE(), { day: 'numeric', month: 'long', year: 'numeric' });
export const dateCourte = (d) => new Date(d).toLocaleDateString(LOCALE());

// Décimales d'un écart en cents : une au-dessus de 2 ¢, deux en dessous.
export const decimalesCents = (c) => (Math.abs(c) > 2 ? 1 : 2);

// Écart en cents : « +3,2 » au-dessus de 2 ¢, « +0,45 » en dessous ; séparateur
// de la langue, signe toujours (« +0,00 » pour zéro, jamais « −0,00 »).
// Options :
//   signe     '+' (défaut, toujours un signe), '±' (écart sans sens : « ±0,40 »),
//             '' (le moins seulement) ;
//   unite     true : « +3,2 ¢ » ;
//   decimales imposées (un réglage : « ±1,0 ¢ ») ;
//   tableur   true (CSV) : « -1,29 », moins ASCII, sans « + », vide si absent.
export function formatCents(c, { signe = '+', unite = false, decimales = null, tableur = false } = {}) {
  if (c == null || !Number.isFinite(c)) return tableur ? '' : '—';
  const d = decimales ?? decimalesCents(c);
  let r = Number(c.toFixed(d));
  if (r === 0) r = 0; // -0 → 0
  const s = nombre(Math.abs(r), d, { tableur });
  let avant = '';
  if (signe === '±') avant = '±';
  else if (r < 0) avant = tableur ? '-' : MOINS;
  else if (signe === '+' && !tableur) avant = '+';
  return `${avant}${s}${unite ? ` ${CENTS}` : ''}`;
}

// Fréquence ou battement en Hz, sans signe : « 2,4 » ; `d` décimales
// (Le carnet, CSV et rapport : deux). `tableur` : la virgule du CSV.
export function formatHz(x, d = 1, { tableur = false } = {}) {
  if (x == null || !Number.isFinite(x)) return '—';
  return nombre(Math.abs(x), d, { tableur });
}
