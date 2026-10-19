// Réharmonisation (Ewen, 19/10/2026) : quand l'accordéon est dans le rapport, un
// ajustement par moindres carrés ROBUSTES (Huber, moindres carrés repondérés)
// du battement mesuré en fonction de la note, par voix musette (aiguë et grave
// séparées), en tiré et poussé, et par rangée quand les rangées diffèrent.
// Trois modèles lisses, choisis par critère d'information (AICc) :
//   cents  : battement = a·fréquence (écart constant en cents), 1 paramètre ;
//   exp    : battement = a·e^(b·demi-tons), 2 paramètres ;
//   quad   : polynôme de degré 2 en log du battement, 3 paramètres.
// Même logique pour la voix juste (cents) : constante, droite (étirement), parabole.
// Il en sort la courbe d'accordage propre à l'instrument, sa ressemblance avec
// les tables prédéfinies, et la liste des notes à retoucher (écart à la courbe
// ajustée au-delà de la tolérance, triées, avec le geste). Module pur.

import { TABLES_MUSETTE, battementTable } from './tables-accordage.js';
import { classeBatt, enUnite, UNITES_BATT, TOL_BATT_PCT, TOL_BATT_MIN_HZ } from './accordage.js';
import { noteLabel } from './music.js';

const LN2 = Math.LN2;
const HUBER_K = 1.345;
export const MIN_NOTES = 8;
const nOct = (midi) => (midi - 69) / 12; // octaves depuis La4 (conditionnement)

// ---- Moindres carrés repondérés (Huber) ------------------------------------------
function resoudre(A, b) { // élimination de Gauss, petite matrice
  const n = b.length;
  const M = A.map((l, i) => [...l, b[i]]);
  for (let i = 0; i < n; i++) {
    let p = i;
    for (let r = i + 1; r < n; r++) if (Math.abs(M[r][i]) > Math.abs(M[p][i])) p = r;
    [M[i], M[p]] = [M[p], M[i]];
    if (Math.abs(M[i][i]) < 1e-12) return null;
    for (let r = i + 1; r < n; r++) {
      const f = M[r][i] / M[i][i];
      for (let c = i; c <= n; c++) M[r][c] -= f * M[i][c];
    }
  }
  const x = new Array(n).fill(0);
  for (let i = n - 1; i >= 0; i--) {
    let s = M[i][n];
    for (let c = i + 1; c < n; c++) s -= M[i][c] * x[c];
    x[i] = s / M[i][i];
  }
  return x;
}
const mediane = (v) => { const s = [...v].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

// base(x) -> vecteur de p fonctions ; y' = y - decal(x) ; plancher : écart-type minimal
// (pour que le bruit de mesure ne fasse pas passer de bonnes notes pour des aberrantes).
function ajusterRobuste(xs, ys, p, base, decal, plancher) {
  const n = xs.length;
  const yy = ys.map((y, i) => y - decal(xs[i]));
  let w = new Array(n).fill(1);
  let coef = null;
  let s = plancher;
  for (let it = 0; it < 30; it++) {
    const A = Array.from({ length: p }, () => new Array(p).fill(0));
    const b = new Array(p).fill(0);
    for (let i = 0; i < n; i++) {
      const f = base(xs[i]);
      for (let r = 0; r < p; r++) { b[r] += w[i] * f[r] * yy[i]; for (let c = 0; c < p; c++) A[r][c] += w[i] * f[r] * f[c]; }
    }
    const nc = resoudre(A, b);
    if (!nc) return null;
    coef = nc;
    const res = xs.map((x, i) => yy[i] - base(x).reduce((t, f, k) => t + f * coef[k], 0));
    s = Math.max(1.4826 * mediane(res.map(Math.abs)), plancher);
    const nw = res.map((r) => (Math.abs(r) <= HUBER_K * s ? 1 : (HUBER_K * s) / Math.abs(r)));
    const change = nw.reduce((t, v, i) => t + Math.abs(v - w[i]), 0);
    w = nw;
    if (change < 1e-6) break;
  }
  const res = xs.map((x, i) => yy[i] - base(x).reduce((t, f, k) => t + f * coef[k], 0));
  const rss = res.reduce((t, r, i) => t + w[i] * r * r, 0);
  const aic = n * Math.log(Math.max(rss / n, 1e-12)) + 2 * p + (n - p - 1 > 0 ? (2 * p * (p + 1)) / (n - p - 1) : 1e6);
  return { coef, res, w, s, aic, p };
}

const MODELES_BATT = [
  { id: 'cents', nom: 'écart constant en cents (battement proportionnel à la fréquence)', p: 1, base: () => [1], decal: (x) => LN2 * x },
  { id: 'exp', nom: 'exponentielle (battement = a·e^(b·demi-tons))', p: 2, base: (x) => [1, x], decal: () => 0 },
  { id: 'quad', nom: 'polynôme de degré 2 en log', p: 3, base: (x) => [1, x, x * x], decal: () => 0 },
];
const MODELES_CENTS = [
  { id: 'const', nom: 'constante', p: 1, base: () => [1], decal: () => 0 },
  { id: 'droite', nom: 'droite (étirement)', p: 2, base: (x) => [1, x], decal: () => 0 },
  { id: 'quad', nom: 'parabole', p: 3, base: (x) => [1, x, x * x], decal: () => 0 },
];

function meilleur(modeles, xs, ys, plancher) {
  let best = null;
  for (const m of modeles) {
    if (xs.length <= m.p + 1) continue;
    const r = ajusterRobuste(xs, ys, m.p, m.base, m.decal, plancher);
    if (r && (!best || r.aic < best.r.aic - 1e-9)) best = { m, r };
  }
  return best;
}

// ---- Les ajustements d'un rapport -----------------------------------------------
// pts : [{ midi, hz, bouton, rang }] (battement mesuré, Hz).
export function ajusterBattement(pts) {
  const bons = pts.filter((p) => p.hz > 0);
  if (bons.length < MIN_NOTES) return null;
  const xs = bons.map((p) => nOct(p.midi));
  const ys = bons.map((p) => Math.log(p.hz));
  const b = meilleur(MODELES_BATT, xs, ys, 0.04);
  if (!b) return null;
  const { m, r } = b;
  const pred = (midi) => { const x = nOct(midi); return Math.exp(m.base(x).reduce((t, f, k) => t + f * r.coef[k], 0) + m.decal(x)); };
  return { modele: m, aic: r.aic, pred, ecartType: r.s, bons, res: r.res, poids: r.w, n: bons.length };
}

export function ajusterJustesse(pts, tolCents = 1) {
  if (pts.length < MIN_NOTES) return null;
  const xs = pts.map((p) => nOct(p.midi));
  const ys = pts.map((p) => p.y);
  const b = meilleur(MODELES_CENTS, xs, ys, Math.max(tolCents / 3, 0.15));
  if (!b) return null;
  const { m, r } = b;
  const pred = (midi) => m.base(nOct(midi)).reduce((t, f, k) => t + f * r.coef[k], 0);
  return { modele: m, aic: r.aic, pred, ecartType: r.s, bons: pts, res: r.res, poids: r.w, n: pts.length, coef: r.coef };
}

// Ressemblance (en %) de la courbe ajustée avec chaque table prédéfinie, sur les notes mesurées :
// 100 · e^(−écart moyen en log). Seules les tables qui battent (non nulles) comptent.
export function ressemblance(pred, midis, de = 3) {
  const out = [];
  for (const t of TABLES_MUSETTE) {
    const e = [];
    for (const m of midis) {
      const v = battementTable(t, m);
      if (v > 0.01) e.push(Math.abs(Math.log(pred(m) / v)));
    }
    if (e.length < Math.max(3, midis.length / 2)) continue;
    const moy = e.reduce((a, b) => a + b, 0) / e.length;
    out.push({ id: t.id, nom: t.nom, pct: Math.round(100 * Math.exp(-moy)) });
  }
  return out.sort((a, b) => b.pct - a.pct).slice(0, de);
}

// écart > 0 : battement trop rapide -> fermer ; < 0 -> ouvrir. Voix aiguë : ouvrir = monter l'anche.
export const gesteBattement = (ecartHz, signe = 1) => {
  const ouvrir = ecartHz < 0;
  const monter = (signe >= 0) === ouvrir;
  return `${ouvrir ? 'ouvrir' : 'fermer'} (${monter ? 'monter' : 'baisser'} l'anche)`;
};

// Tous les ajustements : une courbe par (sens, voix) ; par rangée si cela explique mieux les données.
export function ajuster(series, cfg = {}, { minNotes = MIN_NOTES } = {}) {
  const tol = cfg.tolCents ?? 1;
  const fits = [];
  const groupes = new Map();
  for (const s of series) {
    const cle = `${s.type}|${s.dir}|${s.voiceId}`;
    if (!groupes.has(cle)) groupes.set(cle, []);
    groupes.get(cle).push(s);
  }
  for (const ss of groupes.values()) {
    const s0 = ss[0];
    const bat = s0.type === 'battement';
    const points = ss.flatMap((s) => s.points.map((p) => ({ midi: p.midi, hz: p.hz, y: p.y, bouton: p.bouton, rang: s.rang, nomRang: s.nomRang })));
    const ajuste = (pts) => (bat ? ajusterBattement(pts) : ajusterJustesse(pts, tol));
    const global = ajuste(points);
    const rangs = [...new Set(points.map((p) => p.rang).filter((x) => x != null))];
    let parRang = null;
    if (rangs.length > 1 && rangs.every((r) => points.filter((p) => p.rang === r).length >= minNotes)) {
      const f = rangs.map((r) => [r, ajuste(points.filter((p) => p.rang === r))]);
      if (f.every(([, x]) => x) && global && f.reduce((t, [, x]) => t + x.aic, 0) < global.aic - 4) parRang = f;
    }
    const lot = parRang ?? (global ? [[null, global]] : []);
    for (const [rang, f] of lot) {
      const pts = rang == null ? points : points.filter((p) => p.rang === rang);
      fits.push(decrire(f, { type: s0.type, dir: s0.dir, voiceId: s0.voiceId, label: s0.label, signe: s0.signe ?? 1, rang, nomRang: pts.find((p) => p.nomRang)?.nomRang ?? null }, pts, cfg, tol));
    }
  }
  return { fits, assez: fits.length > 0, minNotes };
}

function decrire(f, id, pts, cfg, tol) {
  const bat = id.type === 'battement';
  const midis = [...new Set(pts.map((p) => p.midi))].sort((a, b) => a - b);
  const de = midis[0];
  const a = midis.at(-1);
  const sortie = { ...id, modele: f.modele, n: f.n, pred: f.pred, de, a, ecartType: f.ecartType, retoucher: [] };
  const nom = (m) => noteLabel(m + (cfg.transpose || 0)).full;
  if (bat) {
    const hzMoy = Math.exp(midis.reduce((t, m) => t + Math.log(f.pred(m)), 0) / midis.length);
    Object.assign(sortie, {
      batMoyenHz: hzMoy,
      parOctave: f.pred(69 + 12) / f.pred(69),
      ressemble: ressemblance(f.pred, midis),
    });
    f.bons.forEach((p, i) => {
      const pr = f.pred(p.midi);
      const ecart = p.hz - pr;
      if (classeBatt(ecart, pr) !== 'ok') sortie.retoucher.push({ midi: p.midi, note: nom(p.midi), rang: p.rang, bouton: p.bouton, mesure: p.hz, ajuste: pr, ecart, geste: gesteBattement(ecart, id.signe), abs: Math.abs(ecart) / Math.max(TOL_BATT_MIN_HZ, TOL_BATT_PCT * pr) });
    });
  } else {
    Object.assign(sortie, { parOctaveCents: f.pred(81) - f.pred(69), moyenneCents: midis.reduce((t, m) => t + f.pred(m), 0) / midis.length });
    f.bons.forEach((p) => {
      const ecart = p.y - f.pred(p.midi);
      if (Math.abs(ecart) > tol) sortie.retoucher.push({ midi: p.midi, note: nom(p.midi), rang: p.rang, bouton: p.bouton, mesure: p.y, ajuste: f.pred(p.midi), ecart, geste: `${ecart < 0 ? 'monter' : 'baisser'} l'anche`, abs: Math.abs(ecart) / tol });
    });
  }
  sortie.retoucher.sort((x, y) => y.abs - x.abs);
  return sortie;
}

// ---- Textes ---------------------------------------------------------------------------
export function titreFit(f) {
  return `${f.label}, ${f.dir === 'P' ? 'poussé' : 'tiré'}${f.rang != null ? `, rangée ${f.rang}` : ''}`;
}
export function texteFit(f, unite = 'bpm') {
  if (f.type === 'battement') {
    const r = f.ressemble?.[0];
    return `${titreFit(f)} : modèle « ${f.modele.nom} » (choisi par critère d'information, ${f.n} notes) ; battement moyen ${enUnite(f.batMoyenHz, unite).toFixed(unite === 'hz' ? 2 : 1)} ${UNITES_BATT[unite]}, `
      + `×${f.parOctave.toFixed(2)} par octave${r ? ` ; votre accord ressemble à « ${r.nom} » à ${r.pct} %` : ''} ; ${f.retoucher.length} note(s) à retoucher.`;
  }
  return `${titreFit(f)} : modèle « ${f.modele.nom} » (${f.n} notes) ; justesse moyenne ${f.moyenneCents.toFixed(1)} ¢, étirement ${f.parOctaveCents >= 0 ? '+' : ''}${f.parOctaveCents.toFixed(1)} ¢ par octave ; ${f.retoucher.length} note(s) à retoucher.`;
}

// ---- La courbe ajustée comme cible du rapport ----------------------------------------
// Écrasements de battement (Hz) par note, de `de` à `a`, depuis un ajustement ; `facteur`
// (1 = telle quelle, 1,1 = relever de 10 %) pour la retoucher avant de la prendre.
export function ciblesDepuis(fit, de = 36, a = 96, facteur = 1) {
  const out = {};
  for (let m = de; m <= a; m++) out[m] = Math.round(fit.pred(m) * facteur * 1000) / 1000;
  return out;
}
