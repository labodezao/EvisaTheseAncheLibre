// Ce qu'il faut voir à l'établi pour qu'une mesure se répète (audit du
// 10/10/2026, docs/AUDIT-REPETABILITE.md, étape 4). La hauteur d'une anche
// libre suit la pression du soufflet (plus fort = plus bas : −0,15 à
// −0,25 ¢/dB mesurés au micro sur la session d'Ewen ; Cottingham 2011, Ricot
// et al. 2005) : deux mesures ne se comparent qu'au même niveau. On le
// montre, on ne le cache pas :
//   dispersion  écart type et étendue des images fines de l'anche visée sur la
//               durée de son que le moteur moyenne (sa fenêtre) ;
//   niveau      le niveau du son (dB) à côté de la hauteur, et une consigne :
//               ±1 dB autour du niveau de la mesure « avant » de la case
//               (±0,2 ¢ de pression) ;
//   ramené      quand la pente ¢/dB de l'anche est mesurée (expert.js,
//               derive : au moins 3 dB, R² > 0,5), la hauteur ramenée au
//               niveau de référence, avec son incertitude (celle de la pente
//               fois l'écart de niveau). Sans pente sûre : rien.
// Le niveau est celui du son entier (t.level), le même que la pente de
// expert.js : une seule anche fine (deux anches qui battent font battre le
// niveau, la pente et la consigne n'ont alors plus de sens : rien).
// Module pur, testé sous Node (test/repetabilite.test.mjs).

import { t } from './langue.js';
import { formatCents, nombre } from './format.js';

export const CONSIGNE_DB = 1;        // ±1 dB : ±0,2 ¢ à −0,2 ¢/dB
export const R2_PENTE = 0.5;         // pente sûre : R² au-dessus
export const ETENDUE_PENTE_DB = 3;   // ... mesurée sur au moins 3 dB
export const IMAGES_DISPERSION = 4;  // au moins 4 images fines

// Dispersion de l'anche visée sur sa fenêtre : suit les images fines
// (`hist.fen`, modifié) ; une autre note, une autre anche, une inversion du
// soufflet ou une image qui n'est pas fine la fait repartir. Rend
// { sigma, etendue, n, dureeS } ou null. Pure.
export function dispersionDe(hist, tk, visee, note) {
  const cle = `${note}|${visee?.id}|${tk?.soufflet?.inversions ?? 0}`;
  const temps = tk?.time;
  const bonne = !tk?.quiet && note != null && !!visee?.fine && visee.cents != null && Number.isFinite(visee.cents)
    && Number.isFinite(temps);
  if (!bonne || hist.fen?.cle !== cle) hist.fen = { cle, images: [] };
  if (!bonne) return null;
  const im = hist.fen.images;
  im.push({ t: temps, c: visee.cents });
  const duree = Number.isFinite(visee.fenetreS) ? visee.fenetreS : 0;
  while (im.length && im[0].t < temps - duree - 1e-6) im.shift();
  if (im.length < IMAGES_DISPERSION) return null;
  let m = 0, lo = Infinity, hi = -Infinity;
  for (const x of im) { m += x.c; lo = Math.min(lo, x.c); hi = Math.max(hi, x.c); }
  m /= im.length;
  let v = 0;
  for (const x of im) v += (x.c - m) ** 2;
  return { sigma: Math.sqrt(v / (im.length - 1)), etendue: hi - lo, n: im.length, dureeS: im[im.length - 1].t - im[0].t };
}

// Une seule anche fine dans l'image : le niveau du son est le sien.
export const uneAnche = (mesure) => (mesure?.anches ?? []).filter((a) => a.fine).length === 1;

// Niveau de référence de la case visée : celui de sa mesure « avant » dans la
// séance ouverte (seance.js, noterMesure garde niveauDb), ou null.
export function niveauReference(seance, cle) {
  if (!seance || !cle) return null;
  const m = (seance.mesures ?? []).find((x) => x.cle === cle && x.phase === 'avant');
  return Number.isFinite(m?.niveauDb) ? m.niveauDb : null;
}

// Consigne de niveau : { ref, niveau, ecart, dans } ou null (pas de
// référence, plusieurs anches, silence). Pure.
export function consigneDe(mesure, ref) {
  if (!mesure || mesure.silence || !Number.isFinite(ref) || !uneAnche(mesure) || !Number.isFinite(mesure.niveauDb)) return null;
  const ecart = mesure.niveauDb - ref;
  return { ref, niveau: mesure.niveauDb, ecart, dans: Math.abs(ecart) <= CONSIGNE_DB };
}

// Erreur type de la pente d'une régression (R², n points). Pure.
export function erreurPente(pente, r2, n) {
  if (!Number.isFinite(pente) || !(n > 2) || !(r2 > 0)) return null;
  return Math.abs(pente) * Math.sqrt(Math.max(0, 1 / r2 - 1) / (n - 2));
}

// Hauteur ramenée au niveau de référence `ref` par la pente ¢/dB de l'anche
// (`d` : derive(suivi) d'expert.js). null sans pente sûre (moins de 3 dB, R²
// sous 0,5), sans référence, ou avec plusieurs anches : aucune valeur
// inventée. Incertitude : erreur type de la pente × |écart de niveau|. Pure.
export function rameneDe(mesure, d, ref) {
  const v = mesure?.visee;
  if (!v?.fine || v.cents == null || !Number.isFinite(v.cents) || !d || !Number.isFinite(ref)) return null;
  if (!(d.etendueDb >= ETENDUE_PENTE_DB) || !(d.r2 > R2_PENTE) || !uneAnche(mesure) || !Number.isFinite(mesure.niveauDb)) return null;
  const ecart = mesure.niveauDb - ref;
  const se = erreurPente(d.parDb, d.r2, d.n);
  return { cents: v.cents - d.parDb * ecart, refDb: ref, ecartDb: ecart, parDb: d.parDb, r2: d.r2,
    incertitude: se != null ? se * Math.abs(ecart) : null };
}

// ---- Textes (Accorder, L'anche) ------------------------------------------------------

const db = (x) => `${x < 0 ? '−' : ''}${nombre(Math.abs(x), 1)} dB`;

// « ±0,04 ¢ (0,12) · −42,3 dB » : dispersion (écart type, étendue) et niveau. Pure.
export function texteDispersion(disp, niveauDb) {
  const morceaux = [];
  if (disp) morceaux.push(`${formatCents(disp.sigma, { signe: '±', unite: true })} (${nombre(disp.etendue, 2)})`);
  if (Number.isFinite(niveauDb)) morceaux.push(db(niveauDb));
  return morceaux.join(' · ');
}

// « niveau −1,4 dB » (hors consigne) ou « niveau juste » ; '' sans consigne. Pure.
export function texteConsigne(c) {
  if (!c) return '';
  return c.dans ? t('niveau juste') : t('niveau ecart', { db: `${c.ecart > 0 ? '+' : '−'}${nombre(Math.abs(c.ecart), 1)}` });
}

// « ramené à −40,0 dB : +0,32 ±0,12 ¢ » ; '' sans valeur. Pure.
export function texteRamene(r) {
  if (!r) return '';
  const inc = r.incertitude != null ? ` ${formatCents(r.incertitude, { signe: '±' })}` : '';
  return t('ramene a', { db: db(r.refDb), c: `${formatCents(r.cents)}${inc} ¢` });
}

// Ce qu'Accorder et L'anche montrent : { ligne, consigne, ramene } (textes et
// position du curseur de la consigne, 0 à 1 sur ±CONSIGNE_VUE_DB). `ref` :
// niveau de référence (niveauReference) ; `d` : derive(suivi). Pure.
export const CONSIGNE_VUE_DB = 4;
export function vueEtabli(mesure, { ref = null, d = null } = {}) {
  if (!mesure || mesure.silence || !mesure.visee) return { ligne: '', consigne: null, ramene: '' };
  const seul = uneAnche(mesure);
  const ligne = texteDispersion(mesure.dispersion, seul ? mesure.niveauDb : null);
  const c = consigneDe(mesure, ref);
  const consigne = c ? { ...c, texte: texteConsigne(c),
    position: Math.max(0, Math.min(1, 0.5 + c.ecart / (2 * CONSIGNE_VUE_DB))),
    zone: CONSIGNE_DB / CONSIGNE_VUE_DB } : null;
  return { ligne, consigne, ramene: texteRamene(rameneDe(mesure, d, ref)) };
}
