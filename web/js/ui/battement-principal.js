// Le battement, grandeur principale d'une musette (lot C3 de la v71, audit « superposition » du 19/10/2026, § 6.1 et 6.2).
//
// Ewen : en musette, ce qui compte est le battement (Hz, bat/min, au métronome) ; la voix juste se lit en cents. Cette
// logique ne change aucune mesure : elle met en forme ce que le moteur donne déjà (battement mesuré et son incertitude,
// battement voulu par la table) :
//   - la cible en bat/min à côté du mesuré ;
//   - une fourchette : la tolérance de la table (`table.tolerance`), sinon le réglage `reglages.fourchetteBat`
//     (bat/min), sinon la plus grande de ±2 bat/min et ±8 % de la cible ;
//   - un indicateur « sec / juste / ouvert » (sec : le battement est plus lent que la fourchette ; ouvert : plus rapide) ;
//   - une cible métronome : le tempo à compter, et l'instant des flashs du strobe (`reglages.metronome`) ;
//   - en trois voix (8'-, 8', 8'+), la symétrie des deux voix décalées et les trois lignes
//     « 8' -0,3 cents · 8'+ 24,1 bat/min (table 22-26) · 8'- 21,0 bat/min (table 19-23) ».
// Module pur, testé sous Node (test/ui.test.mjs, test/battement.test.mjs). Éteint (`reglages.battementPrincipal` faux), rien
// de ceci n'est calculé ni affiché.

export const FOURCHETTE_BPM = 2;      // bat/min : tolérance par défaut, en valeur
export const FOURCHETTE_PART = 0.08;  // et en part de la cible : la plus grande des deux
export const FOURCHETTE_MIN = 0.5;    // bat/min : bornes du réglage
export const FOURCHETTE_MAX = 20;
export const FLASH_S = 0.09;          // durée d'un flash du strobe (s)

// Tolérance en bat/min autour d'une cible. `reglage` : le réglage de l'utilisateur (bat/min) ; `table` : tolerance de la table
// (nombre = bat/min, ou { bpm, part }). La table l'emporte sur le défaut, le réglage de l'utilisateur sur la table.
export function toleranceBat(cibleBpm, { reglage = null, table = null } = {}) {
  const borne = (x) => Math.max(FOURCHETTE_MIN, Math.min(FOURCHETTE_MAX, x));
  if (Number.isFinite(reglage) && reglage > 0) return borne(reglage);
  if (Number.isFinite(table) || Number.isFinite(table?.bpm) || Number.isFinite(table?.part)) {
    const bpm = Number.isFinite(table) ? table : table.bpm ?? 0;
    return Math.max(bpm, Math.abs(cibleBpm) * (Number.isFinite(table?.part) ? table.part : 0));
  }
  return Math.max(FOURCHETTE_BPM, Math.abs(cibleBpm) * FOURCHETTE_PART);
}

// Fourchette d'une cible : { cible, bas, haut, tol } en bat/min (cible >= 0).
export function fourchetteBat(cibleBpm, options = {}) {
  const c = Math.abs(cibleBpm);
  const tol = toleranceBat(c, options);
  return { cible: c, tol, bas: Math.max(0, c - tol), haut: c + tol };
}

// 'sec' (plus lent que la fourchette), 'juste' ou 'ouvert' (plus rapide) ; null sans mesure.
export function etatBattement(mesureBpm, f) {
  if (!f || !Number.isFinite(mesureBpm)) return null;
  const m = Math.abs(mesureBpm);
  if (m < f.bas - 1e-9) return 'sec';
  if (m > f.haut + 1e-9) return 'ouvert';
  return 'juste';
}

// Le battement d'une anche : { mesureBpm, cibleBpm, bas, haut, tol, ecartBpm, etat, signe }. `a` : une anche de anchesDuTick
// (battement et battementVoulu en Hz, signés). Rend null si l'anche ne doit pas battre ou si rien n'est mesuré.
export function battementDe(a, options = {}) {
  const voulu = Math.abs(a?.battementVoulu ?? 0) * 60;
  if (!(voulu > 0) || a.battement == null || !Number.isFinite(a.battement)) return null;
  const f = fourchetteBat(voulu, options);
  const mesureBpm = Math.abs(a.battement) * 60;
  return { mesureBpm, cibleBpm: f.cible, bas: f.bas, haut: f.haut, tol: f.tol, ecartBpm: mesureBpm - f.cible, etat: etatBattement(mesureBpm, f), signe: a.battementVoulu < 0 ? -1 : 1 };
}

// Symétrie des deux voix décalées d'un 8'-/8/8'+ : le rapport des battements mesurés (8'- sur 8'+) contre celui que la table
// veut (`asymetrie`, 1 : le même battement des deux côtés ; 0,88 chez Weirig). null s'il manque une voix.
export function symetrieBat(moins, plus, asymetrie = 1) {
  if (!moins || !plus || !(plus.mesureBpm > 0)) return null;
  return { rapport: moins.mesureBpm / plus.mesureBpm, voulu: asymetrie };
}

// Cible du métronome : { bpm, periodeS } pour la cible du battement (bat/min), ou null.
export function cibleMetronome(cibleBpm) {
  if (!(cibleBpm > 0)) return null;
  return { bpm: cibleBpm, periodeS: 60 / cibleBpm };
}

// Intensité (0 à 1) du flash du strobe à l'instant `tS` (s) : un flash au début de chaque battement visé, qui retombe en FLASH_S.
export function flashMetronome(tS, cibleBpm) {
  if (!(cibleBpm > 0) || !Number.isFinite(tS)) return 0;
  const p = 60 / cibleBpm;
  const dans = ((tS % p) + p) % p;
  return dans < FLASH_S ? 1 - dans / FLASH_S : 0;
}

// Les lignes d'une musette : une par voix, la voix juste (8', battement 0) en cents, les voix décalées en bat/min avec leur
// fourchette. `anches` : anchesDuTick. Rend [{ id, cents | bat }] dans l'ordre 8', 8'+, 8'- (celui de l'écran) ; `asymetrie` : celle de la table.
export function lignesMusette(anches, { reglage = null, table = null, asymetrie = 1 } = {}) {
  const ordre = { '8': 0, '8+': 1, '8-': 2 };
  const voix = (anches ?? []).filter((a) => a.id in ordre).sort((x, y) => ordre[x.id] - ordre[y.id]);
  const lignes = [];
  for (const a of voix) {
    if (a.id === '8') { lignes.push({ id: a.id, cents: a.lus ?? a.cents ?? null }); continue; }
    // Le 8'- veut l'écart de la table multiplié par son asymétrie quand les deux côtés sont là (music.js donne le même écart aux deux).
    const aa = a.id === '8-' && asymetrie !== 1 && voix.some((x) => x.id === '8+') ? { ...a, battementVoulu: (a.battementVoulu ?? 0) * asymetrie } : a;
    lignes.push({ id: a.id, bat: battementDe(aa, { reglage, table }) });
  }
  const sym = symetrieBat(lignes.find((l) => l.id === '8-')?.bat, lignes.find((l) => l.id === '8+')?.bat, asymetrie);
  return { lignes, symetrie: sym };
}
