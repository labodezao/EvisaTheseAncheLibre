// Calculs du rapport d'accordage : cibles, écarts, unités de battement,
// recalcul quand le La change, reconnaissance du La de l'instrument.
// Module pur (Node et navigateur), testé par test/accordage.test.mjs.
//
// Principe (Ewen, 19/10/2026 : « si je mets à jour le La de référence, il faut
// mettre à jour les données du rapport ») : une ligne du rapport garde ce qui
// a été MESURÉ (fMeas, beatMeas, voiceMidi, beatSign) ; tout le reste (cible,
// écarts en cents, battement voulu) se recalcule depuis la configuration
// courante (La, tempérament, table d'accordage, décalages). Rien n'est perdu.

import { midiToFreq, beatTarget, decalageDeVoix, centsBetween } from './music.js';

// ---- Unités du battement ----------------------------------------------------
export const UNITES_BATT = Object.freeze({ bpm: 'bat/min', hz: 'Hz' });
export const enUnite = (hz, unite) => (hz == null || !Number.isFinite(hz) ? null : (unite === 'hz' ? hz : hz * 60));
export const depuisUnite = (v, unite) => (v == null || !Number.isFinite(v) ? null : (unite === 'hz' ? v : v / 60));
export const decimalesUnite = (unite) => (unite === 'hz' ? 2 : 0);
export function formatBatt(hz, unite, avecUnite = false) {
  const v = enUnite(hz, unite);
  if (v == null) return '—';
  return v.toFixed(decimalesUnite(unite)) + (avecUnite ? ` ${UNITES_BATT[unite] ?? UNITES_BATT.bpm}` : '');
}

// ---- Une ligne ---------------------------------------------------------------
// Signe de la voix : 8'+ = +1, 8'- = -1, les autres 0. Les anciennes lignes
// n'ont pas `beatSign` : on le lit dans l'identifiant de la voix.
export function signeVoix(r) {
  if (r.beatSign != null) return r.beatSign;
  const id = String(r.voiceId ?? '');
  if (id.endsWith('+')) return 1;
  if (id.endsWith('-') || id.endsWith('\u2212')) return -1;
  return 0;
}

// Tolérance d'affichage du battement : 10 % de la cible, au moins 0,2 Hz
// (12 bat/min). Choix d'affichage (couleurs), pas une source.
export const TOL_BATT_PCT = 0.10;
export const TOL_BATT_MIN_HZ = 0.2;
export function classeBatt(ecartHz, cibleHz) {
  if (ecartHz == null || !Number.isFinite(ecartHz)) return 'dim';
  const tol = Math.max(TOL_BATT_MIN_HZ, TOL_BATT_PCT * Math.abs(cibleHz ?? 0));
  const a = Math.abs(ecartHz);
  if (a <= tol) return 'ok';
  return a <= 2 * tol ? 'warn' : 'bad';
}

// Tout ce qui dépend de la configuration, pour une ligne, sans la modifier.
export function analyser(r, cfg) {
  const signe = signeVoix(r);
  const midiVoix = r.voiceMidi ?? r.midi;
  const nominal = midiToFreq(midiVoix, cfg);
  const battCible = signe ? signe * beatTarget(r.midi, cfg.beatCurve) : 0;
  const d = decalageDeVoix(r.midi, { beatSign: signe }, cfg.decalageParNote);
  const target = (d ? nominal * Math.pow(2, d / 1200) : nominal) + battCible;
  const mesure = r.fMeas;
  const dCents = mesure != null ? centsBetween(mesure, nominal) : null;
  const dTargetCents = mesure != null ? centsBetween(mesure, target) : null;
  // Voix qui bat : on compare des battements en valeur absolue (Hz).
  const battVoulu = signe ? Math.abs(battCible) : null;
  const battMes = signe && r.beatMeas != null ? Math.abs(r.beatMeas) : null;
  const ecartBatt = battVoulu != null && battMes != null ? battMes - battVoulu : null;
  return { signe, nominal, target, dCents, dTargetCents, battCible, battVoulu, battMes, ecartBatt };
}

// Recalcule les valeurs enregistrées d'un tableau de lignes (Map ou liste)
// depuis la configuration courante. Les mesures ne bougent pas.
export function recalculerLignes(lignes, cfg) {
  let n = 0;
  for (const r of (lignes instanceof Map ? lignes.values() : lignes)) {
    const a = analyser(r, cfg);
    r.beatSign = a.signe;
    r.nominal = a.nominal;
    r.target = a.target;
    r.dCents = a.dCents;
    r.dTargetCents = a.dTargetCents;
    r.beatTarget = a.signe ? a.battCible : 0;
    n++;
  }
  return n;
}

// ---- Le La de l'instrument -------------------------------------------------
// Pour chaque voix « juste » (sans battement) : La = fMeas / fréquence du
// tempérament choisi pour un La de 1 Hz. Le décalage global et les décalages
// par note sont mis de côté (ce sont des choix d'accordage, pas le diapason).
// Estimation : médiane (robuste à une anche déréglée) ; incertitude : écart
// médian absolu normalisé (1,4826 MAD), divisé par √n et multiplié par 1,2533
// (erreur type de la médiane). Arrondi au dixième de Hz.
export const LA_MIN_NOTES = 3;
export const LA_AUTO_NOTES = 8;

const mediane = (v) => {
  const s = [...v].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

export function estimerLa(lignes, cfg = {}) {
  const base = { ...cfg, a4: 1, decalageCents: 0 };
  const vus = new Map(); // une valeur par (note jouée, voix, sens) : le dernier relevé
  for (const r of (lignes instanceof Map ? lignes.values() : lignes)) {
    if (signeVoix(r) !== 0 || !(r.fMeas > 0)) continue;
    const a = r.fMeas / midiToFreq(r.voiceMidi ?? r.midi, base);
    if (Math.abs(1200 * Math.log2(a / (cfg.a4 ?? 440))) > 100) continue; // pas une note de cet instrument
    vus.set(`${r.midi}|${r.voiceId}|${r.dir ?? 'T'}|${r.cas ?? ''}`, a);
  }
  const v = [...vus.values()];
  if (v.length < LA_MIN_NOTES) return null;
  const med = mediane(v);
  const mad = mediane(v.map((x) => Math.abs(x - med)));
  const incert = 1.4826 * mad * 1.2533 / Math.sqrt(v.length);
  const a4 = Math.round(med * 10) / 10;
  return {
    a4, hz: med, incert: Math.round(incert * 10) / 10, incertHz: incert, n: v.length,
    ecartCents: centsBetween(med, cfg.a4 ?? 440),
    assez: v.length >= LA_AUTO_NOTES,
  };
}

export function texteLa(e, virgule = true) {
  if (!e) return '';
  const f = (x) => (virgule ? x.toFixed(1).replace('.', ',') : x.toFixed(1));
  return `La de l'instrument : ${f(e.a4)} Hz ± ${f(e.incert)}, sur ${e.n} notes`;
}
