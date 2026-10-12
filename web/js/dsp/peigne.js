// Peigne rigide des anches qui se tirent (v58, audit couplage du 11/10/2026 : docs/FREQUENCES-ANCHES.md).
//
// Deux anches voisines se tirent par la chambre : chacune est modulée en phase au rythme du battement et le spectre d'un
// partiel est un PEIGNE de raies à k f1 + m Δ (Δ = f2 − f1, le battement). Les positions ne sont pas libres : le modèle n'a que
// deux paramètres non linéaires (F = k f1 et Δ) ; les amplitudes complexes de toutes les raies sont linéaires, donc éliminées
// par moindres carrés (variable projection, Golub et Pereyra 2003) et F, Δ ajustés par Gauss-Newton sur la bande de base
// complexe du traqueur (Kaufman : on projette la dérivée sur le complément de l'espace des raies).
//
// Ce que cela règle, que la pente de phase de l'amas ne savait pas : l'estimateur de l'amas n'a AUCUN résidu pour savoir
// qu'une raie étrangère l'a biaisé ; le peigne en a un (r = ‖y − Vc‖²/‖y‖²) : une raie hors du peigne (partiel d'une autre
// note, accompagnement) le fait monter, et le moteur garde alors sa lecture d'avant (anches nettes à 0,03 ¢).
//
// La fréquence rendue est la moyenne de l'anche sur la fenêtre ajustée : avec un nombre entier de périodes de battement
// (fenetreEntiere), la modulation de phase se moyenne à zéro, c'est la hauteur de l'anche EN PLACE, ce que le luthier accorde.

import { COH_TOL, COH_ABS_HZ, fenetreEntiere } from './battement.js';
import { centsBetween } from '../music.js';

export const PEIGNE_R_MAX = 0.05;        // résidu relatif au-delà duquel le peigne n'explique pas le son (−13 dB)
export const PEIGNE_LATERALES_DB = -12;  // raies latérales externes sous cette valeur : amas net, le moteur d'avant lit aussi bien
export const PEIGNE_ITER = 14;
export const PEIGNE_NMIN = 40;           // échantillons de bande de base au moins (≈ 0,43 s)

const TWO_PI = 2 * Math.PI;

// Système symétrique défini positif M×M (Cholesky, en place sur une copie), plusieurs seconds membres.
function cholSolve(G, M, B, nrhs) {
  const L = new Float64Array(M * M);
  for (let i = 0; i < M; i++) {
    for (let j = 0; j <= i; j++) {
      let s = G[i * M + j];
      for (let k = 0; k < j; k++) s -= L[i * M + k] * L[j * M + k];
      if (i === j) { if (!(s > 1e-300)) return null; L[i * M + i] = Math.sqrt(s); } else L[i * M + j] = s / L[j * M + j];
    }
  }
  const X = new Float64Array(M * nrhs);
  for (let r = 0; r < nrhs; r++) {
    const y = new Float64Array(M);
    for (let i = 0; i < M; i++) {
      let s = B[i * nrhs + r];
      for (let k = 0; k < i; k++) s -= L[i * M + k] * y[k];
      y[i] = s / L[i * M + i];
    }
    for (let i = M - 1; i >= 0; i--) {
      let s = y[i];
      for (let k = i + 1; k < M; k++) s -= L[k * M + i] * X[k * nrhs + r];
      X[i * nrhs + r] = s / L[i * M + i];
    }
  }
  return X;
}

// Un ajustement : lignes = [{ a: [coefficients des Δ] }] ; fréquence de la ligne = F + Σ a_j Δ_j. y : bande de base (re, im),
// N derniers échantillons, temps centré (la fréquence de la porteuse est celle du MILIEU de la fenêtre, F et Δ se découplent).
// Rend { F, D (tableau des Δ), r, c, ok } ; r = résidu relatif.
function ajuster(re, im, N, srd, lignes, F0, D0, iter = PEIGNE_ITER, borneF = Infinity) {
  const M = lignes.length, P = 1 + D0.length;
  const off = re.length - N;
  const ts = new Float64Array(N);
  for (let t = 0; t < N; t++) ts[t] = (t - (N - 1) / 2) / srd;
  let yy = 0;
  for (let t = 0; t < N; t++) yy += re[off + t] ** 2 + im[off + t] ** 2;
  if (!(yy > 0)) return null;
  const Vr = new Float64Array(M * N), Vi = new Float64Array(M * N);
  const yhr = new Float64Array(N), yhi = new Float64Array(N), ur = [], ui = [];
  for (let p = 0; p < P; p++) { ur.push(new Float64Array(N)); ui.push(new Float64Array(N)); }

  // construit V, résout c, rend le résidu relatif et c
  const evaluer = (F, D) => {
    for (let m = 0; m < M; m++) {
      let f = F;
      if (lignes[m].abs != null) f = lignes[m].abs;                   // raie étrangère : position fixe
      else for (let j = 0; j < D.length; j++) f += lignes[m].a[j] * D[j];
      const ph0 = TWO_PI * f * ts[0], dph = TWO_PI * f / srd;
      let cr = Math.cos(ph0), ci = Math.sin(ph0);
      const sr = Math.cos(dph), si = Math.sin(dph);
      const o = m * N;
      for (let t = 0; t < N; t++) {
        Vr[o + t] = cr; Vi[o + t] = ci;
        const nr = cr * sr - ci * si;
        ci = cr * si + ci * sr; cr = nr;
      }
    }
    // Gram : V^H V (réelle ? seulement si les lignes sont symétriques ; calcul général)
    const G = new Float64Array(M * M), Gi = new Float64Array(M * M);
    for (let a = 0; a < M; a++) for (let b = a; b < M; b++) {
      let sr = 0, si = 0;
      const oa = a * N, ob = b * N;
      for (let t = 0; t < N; t++) { sr += Vr[oa + t] * Vr[ob + t] + Vi[oa + t] * Vi[ob + t]; si += Vr[oa + t] * Vi[ob + t] - Vi[oa + t] * Vr[ob + t]; }
      G[a * M + b] = sr; G[b * M + a] = sr; Gi[a * M + b] = si; Gi[b * M + a] = -si;
    }
    return { G, Gi };
  };

  // Système complexe hermitien M×M → réel 2M×2M [[Gr, -Gi],[Gi, Gr]] (défini positif aussi).
  const resoudreC = (G, Gi, br, bi) => {
    const n2 = 2 * M, A = new Float64Array(n2 * n2), B = new Float64Array(n2);
    for (let a = 0; a < M; a++) for (let b = 0; b < M; b++) {
      A[a * n2 + b] = G[a * M + b]; A[a * n2 + M + b] = -Gi[a * M + b];
      A[(M + a) * n2 + b] = Gi[a * M + b]; A[(M + a) * n2 + M + b] = G[a * M + b];
    }
    let tr = 0;
    for (let a = 0; a < n2; a++) tr += A[a * n2 + a];
    for (let a = 0; a < n2; a++) A[a * n2 + a] += 1e-9 * tr / n2;
    for (let a = 0; a < M; a++) { B[a] = br[a]; B[M + a] = bi[a]; }
    const X = cholSolve(A, n2, B, 1);
    if (!X) return null;
    return { xr: X.subarray(0, M), xi: X.subarray(M) };
  };

  const projeter = (F, D) => {
    const { G, Gi } = evaluer(F, D);
    const br = new Float64Array(M), bi = new Float64Array(M);
    for (let m = 0; m < M; m++) {
      let sr = 0, si = 0;
      const o = m * N;
      for (let t = 0; t < N; t++) {
        const yr = re[off + t], yi = im[off + t];
        sr += Vr[o + t] * yr + Vi[o + t] * yi;     // conj(V) · y
        si += Vr[o + t] * yi - Vi[o + t] * yr;
      }
      br[m] = sr; bi[m] = si;
    }
    const c = resoudreC(G, Gi, br, bi);
    if (!c) return null;
    let rr = 0;
    for (let t = 0; t < N; t++) {
      let hr = 0, hi = 0;
      for (let m = 0; m < M; m++) { const o = m * N + t; hr += c.xr[m] * Vr[o] - c.xi[m] * Vi[o]; hi += c.xr[m] * Vi[o] + c.xi[m] * Vr[o]; }
      yhr[t] = hr; yhi[t] = hi;
      rr += (re[off + t] - hr) ** 2 + (im[off + t] - hi) ** 2;
    }
    return { c, r: rr / yy, G, Gi };
  };

  let F = F0, D = D0.slice();
  let cur = projeter(F, D);
  if (!cur) return null;
  let mu = 1e-3, it = 0;
  for (; it < iter; it++) {
    // dérivées (Kaufman) : u_p = j 2π t (Σ_m a_pm c_m V_m) pour Δ_p (a_pm = coefficient), p = 0 : F (tous les a = 1)
    const { c, G, Gi } = cur;
    for (let p = 0; p < P; p++) { ur[p].fill(0); ui[p].fill(0); }
    for (let m = 0; m < M; m++) {
      const o = m * N;
      for (let p = 0; p < P; p++) {
        const coef = lignes[m].abs != null ? 0 : p === 0 ? 1 : lignes[m].a[p - 1];
        if (coef === 0) continue;
        const wr = coef * c.xr[m], wi = coef * c.xi[m];
        for (let t = 0; t < N; t++) {
          const zr = wr * Vr[o + t] - wi * Vi[o + t], zi = wr * Vi[o + t] + wi * Vr[o + t];
          ur[p][t] += zr; ui[p][t] += zi;
        }
      }
    }
    for (let p = 0; p < P; p++) {
      for (let t = 0; t < N; t++) {
        const w = TWO_PI * ts[t];
        const zr = ur[p][t], zi = ui[p][t];
        ur[p][t] = -w * zi; ui[p][t] = w * zr;     // j w z
      }
    }
    // Projection sur le complément : Ĵ_p = u_p − V G⁻¹ V^H u_p
    const Jr = [], Ji = [];
    for (let p = 0; p < P; p++) {
      const br = new Float64Array(M), bi = new Float64Array(M);
      for (let m = 0; m < M; m++) {
        let sr = 0, si = 0;
        const o = m * N;
        for (let t = 0; t < N; t++) { sr += Vr[o + t] * ur[p][t] + Vi[o + t] * ui[p][t]; si += Vr[o + t] * ui[p][t] - Vi[o + t] * ur[p][t]; }
        br[m] = sr; bi[m] = si;
      }
      const x = resoudreC(G, Gi, br, bi);
      if (!x) return null;
      const jr = new Float64Array(N), ji = new Float64Array(N);
      for (let t = 0; t < N; t++) {
        let hr = 0, hi = 0;
        for (let m = 0; m < M; m++) { const o = m * N + t; hr += x.xr[m] * Vr[o] - x.xi[m] * Vi[o]; hi += x.xr[m] * Vi[o] + x.xi[m] * Vr[o]; }
        jr[t] = ur[p][t] - hr; ji[t] = ui[p][t] - hi;
      }
      Jr.push(jr); Ji.push(ji);
    }
    const A = new Float64Array(P * P), g = new Float64Array(P);
    for (let a = 0; a < P; a++) {
      for (let b = a; b < P; b++) {
        let s = 0;
        for (let t = 0; t < N; t++) s += Jr[a][t] * Jr[b][t] + Ji[a][t] * Ji[b][t];
        A[a * P + b] = s; A[b * P + a] = s;
      }
      let s = 0;
      for (let t = 0; t < N; t++) s += Jr[a][t] * (re[off + t] - yhr[t]) + Ji[a][t] * (im[off + t] - yhi[t]);
      g[a] = s;
    }
    let accepte = false;
    for (let essai = 0; essai < 5 && !accepte; essai++) {
      const Ad = Float64Array.from(A);
      for (let a = 0; a < P; a++) Ad[a * P + a] *= 1 + mu;
      const d = cholSolve(Ad, P, g, 1);
      if (!d) { mu *= 10; continue; }
      // pas borné : un demi-battement au plus sur chaque paramètre (la mauvaise étiquette ne se corrige pas par un grand saut)
      let echelle = 1;
      const lim = [Math.min(borneF, 0.5 * Math.max(D[0] ?? 0.1, 0.05)), ...D.map((x) => 0.3 * Math.max(Math.abs(x), 0.05))];
      for (let a = 0; a < P; a++) echelle = Math.min(echelle, lim[a] / (Math.abs(d[a]) + 1e-30));
      const F1 = F + d[0] * echelle, D1 = D.map((x, j) => x + d[1 + j] * echelle);
      const nouv = projeter(F1, D1);
      if (nouv && nouv.r <= cur.r * (1 + 1e-9)) {
        const pas = Math.max(Math.abs(d[0] * echelle), ...D1.map((x, j) => Math.abs(x - D[j])));
        F = F1; D = D1; cur = nouv; mu = Math.max(1e-6, mu / 5); accepte = true;
        if (pas < 2e-5) return finir(F, D, cur, it + 1);
      } else mu *= 8;
    }
    if (!accepte) break;
  }
  return finir(F, D, cur, it);

  function finir(Ff, Df, st, n) {
    const N2 = N;
    const amps = [];
    for (let m = 0; m < M; m++) amps.push(Math.hypot(st.c.xr[m], st.c.xi[m]));
    // borne de Cramér-Rao sur F (Hz, domaine du partiel) ; le résidu inclut le défaut de modèle : borne prudente
    const r = Math.min(Math.max(st.r, 1e-12), 0.99);
    const sigmaF = (srd / (Math.PI * N2)) * Math.sqrt(3 * r / (N2 * (1 - r)));
    return { F: Ff, D: Df, r: st.r, amps, sigmaF, iter: n, N: N2 };
  }
}

// Interface de l'audit : ajusterPeigne(bb, f1_0, D_0, ms, etrangeres, { N }). `bb` : { re, im, srd, fc } du traqueur ; f1_0 : valeur
// initiale de F (Hz depuis la porteuse du traqueur, domaine du partiel) ; D_0 : celle de Δ ; `ms` : indices des raies du peigne
// (−2..3 pour k = 1) ; `etrangeres` : positions (Hz depuis la porteuse) de raies libres, hors peigne, à loger avant l'ajustement
// (amplitudes ajustées, positions fixes). Rend { F, D: [Δ], r, amps, lignes: [{ m, f, amp }], sigmaF, N, iter } ou null.
export function ajusterPeigne(bb, f1_0, D_0, ms = [-2, -1, 0, 1, 2, 3], etrangeres = [], { N = null, iter = PEIGNE_ITER } = {}) {
  const len = bb.re.length;
  const n = Math.min(N ?? len, len);
  if (n < PEIGNE_NMIN) return null;
  const lignes = [...ms.map((m) => ({ a: [m], m })), ...etrangeres.map((f) => ({ a: [0], m: null, abs: f }))];
  const res = ajuster(bb.re, bb.im, n, bb.srd, lignes, f1_0, [D_0], iter);
  if (!res) return null;
  return { ...res, lignes: lignes.map((l, i) => ({ m: l.m, f: l.abs ?? res.F + l.m * res.D[0], amp: res.amps[i] })) };
}

// ---------------------------------------------------------------------------------------------------------------------------
// Côté moteur : le peigne d'un unisson de deux anches. Appelé par cohererPaire (battement.js) sur les voix FINALES.
//
// Identification (audit § 7) : les positions donnent f1 modulo Δ. Les porteuses sont les deux raies du peigne les plus fortes
// et ADJACENTES de k pas (indices s et s + k) : le critère est le plus petit des deux modules (une raie latérale est à −16 dB
// au plus de sa porteuse quand β ≤ 0,3 rad, l'anche faible est à −12 dB au plus : la faible l'emporte sur toute raie latérale).
// Deux partiels (1 et 2, sinon 3) disent f1 : leurs f1(k)/k doivent s'accorder à 0,3 ¢ ; sinon, pas de peigne.
export const PEIGNE_HOP_S = 0.04;        // un ajustement toutes les 40 ms (la fenêtre en dure 2 à 6)
export const PEIGNE_D_MIN = 0.35;        // Hz : en dessous, deux périodes ne tiennent pas dans FEN_MAX_S (cas 3 et 4 de l'audit)
export const PEIGNE_PERIODES = 2;        // périodes de battement au moins dans la fenêtre ajustée (de quoi séparer les raies)
export const PEIGNE_FEN_S = 1.5;         // …et au moins cette durée, en nombre entier de périodes
export const PEIGNE_FEN_MAX_S = 6;
export const PEIGNE_AMBIGU = 0.7;        // l'étiquette des porteuses est sûre si la deuxième meilleure vaut moins de 70 % de la meilleure
export const PEIGNE_K_CENTS = 0.3;       // f1(k)/k de deux partiels
export const PEIGNE_TENUE_S = 0.5;       // un ajustement qui échoue une fois : la valeur précédente tient (pas d'aller-retour de source)
export const PEIGNE_ENTREE = 3;          // ajustements valides d'affilée avant que le peigne prenne la main
export const PEIGNE_SIGMA_SUR = 0.3;    // ¢ : au-delà, la lecture n'est jamais dite « sûre » (audit § 11)

// Rapport J1(x)/J0(x) (séries, x < 4) : amplitude d'une raie latérale d'une modulation de phase d'indice x sur sa porteuse.
function rapportBessel(x) {
  let j0 = 0, j1 = 0, t0 = 1, t1 = x / 2;
  for (let n = 0; n < 14; n++) {
    j0 += t0; j1 += t1;
    t0 *= -(x * x) / (4 * (n + 1) * (n + 1));
    t1 *= -(x * x) / (4 * (n + 1) * (n + 2));
  }
  return Math.abs(j0) < 1e-9 ? 9 : Math.abs(j1 / j0);
}
// Énergie des raies latérales externes sur celle des porteuses au partiel kCible, d'après ce qu'on lit au partiel kLu (l'indice de
// modulation de phase est proportionnel au rang du partiel : x = k β).
export function lateralesAuPartiel(laterales, kLu, kCible) {
  if (!(laterales > 0)) return 0;
  const rho = Math.sqrt(laterales);
  let lo = 0, hi = 3;
  for (let i = 0; i < 30; i++) { const mid = (lo + hi) / 2; if (rapportBessel(mid) < rho) lo = mid; else hi = mid; }
  const xc = Math.min(3.5, ((lo + hi) / 2) * kCible / kLu);
  return rapportBessel(xc) ** 2;
}

// Indices des raies au partiel k : porteuses en 0 et k, deux raies latérales de chaque côté.
const MS = (k) => { const m = []; for (let i = -2; i <= k + 2; i++) m.push(i); return m; };

// Étiquette des porteuses d'un ajustement au partiel k : décalage s ∈ {−1, 0, 1} des indices (0 et k), score = plus petit module.
// Quand les amplitudes ne tranchent pas (l'anche faible vaut une raie latérale de la forte : `amb` > PEIGNE_AMBIGU), les lectures
// d'avant (`lect` = { f0, f1, pas } : hauteurs des deux anches en Hz, `pas` : l'écart en Hz entre deux étiquettes, soit Δ) tranchent si
// elles désignent la MÊME étiquette et sans équivoque (le meilleur coût sous 60 % du suivant) ; sinon l'étiquette reste ambiguë.
export function etiqueter(res, k, lect = null) {
  const amp = (m) => res.lignes.find((l) => l.m === m)?.amp ?? 0;
  const sc = [-1, 0, 1].map((s) => ({ s, v: Math.min(amp(s), amp(s + k)) }));
  sc.sort((a, b) => b.v - a.v);
  let s = sc[0].s;
  let amb = sc[0].v > 0 ? sc[1].v / sc[0].v : 1;
  if (amb > PEIGNE_AMBIGU && lect) {
    const cout = [-1, 0, 1].map((t) => ({ s: t, v: Math.abs(lect.fa(t) - lect.f0) + Math.abs(lect.fa(t) + lect.pas - lect.f1) })).sort((a, b) => a.v - b.v);
    if (cout[0].s === s && cout[0].v <= 0.6 * cout[1].v) amb = 0;    // les lectures confirment les amplitudes
  }
  const car = amp(s) ** 2 + amp(s + k) ** 2;
  const ext = amp(s - 1) ** 2 + amp(s + k + 1) ** 2;
  return { s, amb, laterales: car > 0 ? ext / car : 1, a0: amp(s), a1: amp(s + k) };
}

export const methodesPeigne = {
  // Rend { f0, f1, delta, sigmaCents, r, laterales (rapport d'énergie), k, N, T } pour les deux anches v0 < v1 d'un unisson, ou null.
  // `D0` : Δ attendu (enveloppe, dernier peigne, ou écart brut) ; `env` : { hz, sure } ou null pour la vérification de Δ.
  ajusterUnisson(g, v0, v1, D0, env, tNow) {
    if (!(D0 >= PEIGNE_D_MIN)) return null;
    const calib = 1 + (this.cfg.calibrationPpm || 0) * 1e-6;
    const nper = Math.max(PEIGNE_PERIODES, Math.round(PEIGNE_FEN_S * D0));
    const T = nper / D0;
    if (T > PEIGNE_FEN_MAX_S) return null;
    const tracker = (k) => this.trackers.get(`${g.key}p${k}`) ?? (k === g.kTrack ? this.trackers.get(g.key) : null);
    const bons = [];
    for (const k of [2, 1, 3]) {
      if (bons.length >= 2) break;
      const tr = tracker(k);
      if (!tr) continue;
      const N = Math.round(T * tr.srd);
      if (Math.min(tr.count - tr.start, 2048) < N + 4) continue;
      const bb = tr.baseband(N);
      if (!bb || bb.re.length < N) continue;
      // Deux hypothèses pour la porteuse de départ : celle de la lecture du 8', ou celle du 8'+ moins k Δ (le peigne est rigide :
      // tomber sur n'importe quelle raie suffit, l'étiquette est décidée ensuite).
      let res = null;
      for (const F0 of [v0.fMeas / calib * k - bb.fc, v1.fMeas / calib * k - bb.fc - k * D0]) {
        const r = ajusterPeigne(bb, F0, D0, MS(k), [], { N });
        if (r && (!res || r.r < res.r)) res = r;
        if (res && res.r < PEIGNE_R_MAX / 2) break;
      }
      if (!res) { if (k === 2) return null; continue; }
      const D = res.D[0];
      const et = etiqueter(res, k, { f0: v0.fMeas, f1: v1.fMeas, pas: D, fa: (t) => calib * (bb.fc + res.F + t * D) / k });
      const f1 = calib * (bb.fc + res.F + et.s * D) / k;
      bons.push({ k, N, res, et, D, f1, sigmaHz: calib * res.sigmaF / k, bb });
      if (res.r >= PEIGNE_R_MAX) return null;     // le premier ne tient pas : ni le contrôle, ni le suivant ne le sauveront
    }
    if (bons.length < 2) return null;
    const [a, b] = bons;                           // a : partiel 2 (ou le premier lu), b : le contrôle
    if (a.et.amb > PEIGNE_AMBIGU || b.et.amb > PEIGNE_AMBIGU) return null;
    const tolD = 0.05 * a.D + 0.01;
    if (Math.abs(a.D - b.D) > tolD) return null;
    const sc = (x) => 1731.2 * x.sigmaHz / x.f1;
    if (Math.abs(1200 * Math.log2(a.f1 / b.f1)) > PEIGNE_K_CENTS + 3 * Math.hypot(sc(a), sc(b))) return null;
    // La vérité d'un partiel plus haut est mieux résolue en cents : la valeur rendue est celle du partiel le plus haut.
    const h = a.k >= b.k ? a : b;
    const D = h.D;
    if (env && Math.abs(D - env.hz) > 0.1 * env.hz + 0.02) return null;   // même une enveloppe pas sûre : un peigne dont Δ la contredit n’est pas cru
    if (Math.abs(D - D0) > 0.5 * D0) return null;
    // Les raies latérales au partiel que le moteur mesure (kTrack, 3 à 8 sur une note grave), déduites de ce qu'on lit en bas.
    const lat = lateralesAuPartiel(Math.min(h.et.laterales, 1), h.k, g.kTrack || 1);
    return { f0: h.f1, f1: h.f1 + D, delta: D, sigmaCents: sc(h), r: Math.max(a.res.r, b.res.r), laterales: lat, k: h.k, N: h.N, T };
  },

  // État de la paire d'un unisson (v58, audit § c) : ce qu'on peut dire d'une lecture par anche, et avec quelle marge. Pose sur
  // chaque anche `etatAnche` ('sur' | 'en cours' | 'centre'), `margeAnche` (¢, la marge à montrer : 0 si aucune), `tBesoin` (s) et
  // `ageNote` (s). Rien n'est jamais dit « sûr » : avant T_besoin = max(1 s, 1,2/Δ) ; quand le peigne a la main avec un σ > 0,3 ¢ ;
  // quand les deux anches sont plus proches que la résolution de la fenêtre sans que le peigne les sépare (cas 3 et 4 : Do6-Do7 sous
  // 0,5 Hz) : on donne alors le CENTRE (immunisé contre la paire : 0,03 ¢) et chaque anche à ± Δ/2 près.
  etatPaire(g, tNow, envHz, envSure) {
    const c = this.cohEtat?.get(`${g.key}:${g.center}`);
    const [v0, v1] = [...g.voices].sort((x, y) => x.target - y.target);
    const sets = (champs) => { for (const v of [v0, v1]) if (v.tracked) Object.assign(v, champs); };
    const efface = () => { for (const v of g.voices) { v.etatAnche = null; v.margeAnche = 0; v.tBesoin = null; v.ageNote = null; } };
    if (!c || !v0?.tracked || !v1?.tracked || v0.coarse || v1.coarse) return efface();
    const pg = c.pgActif && c.pg && tNow - c.pg.t <= 3 ? c.pg : null;
    // Le battement connu : le peigne (deux partiels d'accord), l'enveloppe sûre, sinon l'écart des deux lectures de la dernière
    // demi-seconde, à condition qu'il tienne (sinon deux raies que la fenêtre ne sépare pas encore : l'écart lu n'est pas Δ).
    const recents = (c.hist ?? []).filter((h) => tNow - h.t <= 0.7).map((h) => h.f1 - h.f0);
    const med = recents.length ? [...recents].sort((x, y) => x - y)[recents.length >> 1] : null;
    const tient = med != null && recents.length >= 5 && Math.max(...recents) - Math.min(...recents) <= 0.25 * Math.abs(med) + 0.05;
    const envD = envHz != null && envSure ? envHz : null;
    const D0 = pg?.delta ?? envD ?? (tient && med >= 0.05 ? med : null) ?? envHz;
    if (D0 == null || D0 < 0.05) return efface();
    const age = tNow - c.t0;
    const fen = g.W > 0 && g.srd > 0 ? g.W / g.srd : 2.7;
    this.moyennerPaire(v0, v1, tNow, D0, c, !!pg || D0 >= 1 / fen);
    const centsDe = (hz, f) => 1731.2 * hz / f;
    const fRef = (v0.fMeas + v1.fMeas) / 2;
    // T_besoin = max(1 s, 1,2/Δ) ; sous 0,8 Hz les raies sont à moins de deux cases de la fenêtre : deux périodes au moins.
    const tBesoin = D0 < 0.8 ? Math.max(1, 2 / D0) : Math.max(1, 1.2 / D0);
    const champs = { tBesoin, ageNote: age };
    if (pg) {
      const sg = pg.sigmaCents;
      return sets({ ...champs, etatAnche: sg <= PEIGNE_SIGMA_SUR && age >= tBesoin ? 'sur' : 'en cours', margeAnche: sg > 0.1 ? sg : centsDe(sg > PEIGNE_SIGMA_SUR ? D0 / 2 : 0, fRef) });
    }
    if (D0 < 1 / fen) {
      // Deux anches sous la résolution de la fenêtre : le centre fait foi (immunisé contre le tirage), chacune à ± Δ/2 près ; l'enveloppe
      // donne Δ à 0,03 Hz. Jamais une valeur sûre par anche (cas 3 et 4 de l'audit : Do6-Do7 sous 0,5 Hz).
      if (envD != null) {
        for (const [v, f] of [[v0, fRef - envD / 2], [v1, fRef + envD / 2]]) {
          v.fMeas = f;
          v.dCents = centsBetween(f, v.nominal);
          v.dHz = f - v.nominal;
          v.dTargetCents = centsBetween(f, v.target);
        }
      }
      return sets({ ...champs, etatAnche: age < tBesoin ? 'en cours' : 'centre', margeAnche: centsDe(D0 / 2, fRef) });
    }
    // Lecture par l'amas : sûre quand la note a duré T_besoin ET que les deux lectures collent à un battement connu.
    // « Cohérente » : la paire lue colle à Δ depuis un instant (une image qui s'en écarte ne fait pas clignoter l'état).
    if (Math.abs((v1.fMeas - v0.fMeas) - D0) <= COH_TOL * D0 + COH_ABS_HZ) c.cohT = tNow;
    const coherente = tNow - (c.cohT ?? -1e9) <= 0.5;
    if (age < tBesoin || !coherente || (envD == null && !tient)) {
      return sets({ ...champs, etatAnche: 'en cours', margeAnche: centsDe(D0 / 2, fRef) });
    }
    return sets({ ...champs, etatAnche: 'sur', margeAnche: 0 });
  },

  // Valeur affichée = moyenne sur un nombre ENTIER de périodes de battement (fenetreEntiere) : sur une période entière la modulation
  // de phase du tirage se moyenne à zéro. Le peigne la donne déjà (sa fenêtre en est une). Pour l'amas, la moyenne n'est faite que
  // dans l'état « centre » (deux anches sous la résolution de la fenêtre, Do6-Do7 sous 0,5 Hz : la lecture brute y saute d'une raie
  // à l'autre et le vibrato du soufflet y est du même ordre que Δ). Ailleurs elle ajoutait du retard sans rien ôter : essayé sur le
  // banc, la dérive de pression 1 ¢/s passait de 1,0 à 1,5 ¢. `aSauter` : le peigne a la main, ou l'amas est résolu.
  // Pas assez d'histoire (début de note, anche perdue) ou une marche : la valeur brute.
  moyennerPaire(v0, v1, tNow, D0, c, aSauter) {
    if (aSauter) { c.moy = null; return; }
    const ok = (v) => v.tracked && !v.held && !v.coarse && !v.merged && !v.step && Number.isFinite(v.fMeas);
    if (!ok(v0) || !ok(v1)) { c.moy = null; return; }
    const L = fenetreEntiere(D0);
    const m = c.moy ?? (c.moy = []);
    m.push({ t: tNow, f0: v0.fMeas, f1: v1.fMeas });
    while (m.length && m[0].t < tNow - L - 0.05) m.shift();
    if (m.length < 4 || tNow - m[0].t < 0.9 * L) return;
    let a = 0, b = 0;
    for (const x of m) { a += x.f0; b += x.f1; }
    for (const [v, f] of [[v0, a / m.length], [v1, b / m.length]]) {
      v.fBrute = v.fMeas;
      v.fMeas = f;
      v.dCents = centsBetween(f, v.nominal);
      v.dHz = f - v.nominal;
      v.dTargetCents = centsBetween(f, v.target);
    }
  },

  // Appelée par cohererPaire : essaie le peigne et, s'il est choisi, pose les hauteurs des deux anches. Rend vrai quand il a la
  // main. Critère de choix (audit § 8) : peigne seulement si son résidu r < PEIGNE_R_MAX, ses Δ concordent (deux partiels,
  // enveloppe), ET (raies latérales à −12 dB ou plus, OU la paire lue ne colle pas à Δ). Un amas net (latérales sous −12 dB,
  // paire cohérente) garde sa lecture d'avant : 0,03 ¢ depuis la v56, le peigne n'y apporte rien. Une fois choisi pour la note, le
  // peigne reste tant qu'il tient (pas d'aller-retour de source entre deux images).
  appliquerPeigne(g, v0, v1, tNow, envHz, envSure, c, ok) {
    if (!ok(v0) || !ok(v1)) return false;
    let pg = c.pg ?? null;
    if (pg && tNow - pg.t > 3) pg = c.pg = null;
    const sep = v1.fMeas - v0.fMeas;
    const D0 = envHz ?? pg?.delta ?? (sep >= PEIGNE_D_MIN && sep <= 14 ? sep : null);
    if (D0 == null) return false;
    if (!pg || tNow - pg.tFit >= PEIGNE_HOP_S) {
      const res = this.ajusterUnisson(g, v0, v1, D0, envHz != null ? { hz: envHz, sure: envSure } : null, tNow);
      if (res) {
        pg = c.pg = { ...res, t: tNow, tFit: tNow };
        c.pgOk = (c.pgOk ?? 0) + 1;
      } else {
        // Un ajustement qui échoue une fois n'ôte pas la main au peigne : sa dernière valeur tient PEIGNE_TENUE_S (une image
        // folle ne fait pas aller et venir la source) ; un peigne qui échoue plus longtemps la rend à l'amas.
        c.pgOk = 0;
        if (c.pgActif && pg && tNow - pg.t <= PEIGNE_TENUE_S) pg = { ...pg, tFit: tNow };
        else { c.pgActif = false; c.pg = null; return false; }
      }
    }
    const dB = pg.laterales > 0 ? 10 * Math.log10(pg.laterales) : -99;
    const coherente = Math.abs(sep - pg.delta) <= COH_TOL * pg.delta + COH_ABS_HZ;
    // Entrée : trois ajustements valides d'affilée (120 ms), et un amas qui a besoin du peigne (raies latérales à −12 dB ou plus, ou
    // paire qui ne colle pas à Δ).
    if (!c.pgActif && (c.pgOk < PEIGNE_ENTREE || (coherente && dB < PEIGNE_LATERALES_DB))) return false;
    c.pgActif = true;
    for (const [v, f] of [[v0, pg.f0], [v1, pg.f1]]) {
      v.fMeas = f;
      v.dCents = centsBetween(f, v.nominal);
      v.dHz = f - v.nominal;
      v.dTargetCents = centsBetween(f, v.target);
      v.source = 'peigne';
      v.sigmaCents = pg.sigmaCents;
      v.peigne = { r: pg.r, laterales: dB, k: pg.k, T: pg.T, delta: pg.delta };
      v.pairRepaired = false;
    }
    const base = g.voices.find((v) => v.def.beatSign === 0) ?? g.voices[0];
    for (const v of g.voices) v.beatMeas = v === base ? 0 : v.fMeas - base.fMeas;
    c.ref = { t: tNow, f0: v0.fMeas, f1: v1.fMeas };
    return true;
  },
};
