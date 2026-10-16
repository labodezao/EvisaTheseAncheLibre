// Lecture d'une note à deux anches par moindres carrés non linéaires multi-partiels, avec un PEIGNE DE BESSEL (v63, audit Fable du
// 15/10/2026, recommandations R1 et R2 ; J:\claude\audits\2026-10-17-accordeur-fable\RAPPORT-AUDIT.md et docs/CERTIFICAT.md).
//
// Modèle. Deux anches r = 1, 2 de fréquences f1 et f2 = f1 + Ω (Ω : le battement). Elles se tirent par le trou de soupape : chacune
// est modulée en phase ET en amplitude au rythme du battement. Le partiel k de l'anche r est
//   s_rk(t) = [1 + m_r cos(Φ + ψ)] · exp( i [ 2π k f_r τ(t) + k β_r sin Φ ] ),  Φ = 2π Ω τ(t) + θ,
// soit, par Jacobi-Anger, des raies à k f_r + nΩ d'amplitude A_rk · C_n(kβ_r, m_r, ψ) e^{inθ}. L'indice de la modulation de phase est
// PROPORTIONNEL au rang k (mesuré sur le H6, audit § 1.1 : β = 0,10 à 0,37 rad). β_r et m_r sont signés (β2 < 0 : modulation en
// opposition, tirage d'Adler ; β2 > 0 : modulation commune, la pression du trou monte pour les deux). Les amplitudes complexes A_rk
// (le timbre) sont libres et éliminées par moindres carrés (variable projection). Restent comme inconnues non linéaires : f1, Ω, β1, β2,
// m1, ψ, θ, m2 et le « warp » commun τ(t) = ∫(1 + d(t)) dt, d(t) linéaire par morceaux, avec un niveau commun g(t) : la pression du
// soufflet (dérive, agitation de la main) déplace TOUS les partiels des DEUX anches du même écart relatif et change leur niveau.
// Option : une raie étrangère libre (f3, sans modulation) — la fuite d'un autre registre, vue à −9 … −22 dB sur le H6.
//
// Ce que cela apporte (audit § 1.2 et 1.3) : le peigne à amplitudes libres de la v58 est invariant par f1 -> f1 + Ω (même résidu :
// aucune étiquette ne se lit) ; avec la contrainte de Bessel, la raie miroir de l'anche forte au partiel k vaut J_k(kβ), l'anche faible
// reste à kΩ : l'étiquette se lit dès 0,5 battement. Les DEUX hypothèses d'étiquette (f1 = pic ou f1 = pic − Ω) sont ajustées
// séparément ; le rapport de vraisemblance LLR = (SSR_autre − SSR_min)/σ² dit si l'étiquette est sûre (≥ 25). La fenêtre est
// quelconque (la modulation est dans le modèle : plus de biais β/(πT)).
//
// Module pur, sans DOM : tourne dans le Worker du moteur et sous Node (test/certificat.test.mjs).
import { FFT } from './fft.js';

export const C_CENTS = 1731.2340490667561;     // ¢ par unité de df/f
const TWO_PI = 2 * Math.PI;
const NM = 3;                                  // raies latérales de chaque côté (|n| <= 3)
export const NLS_LLR_SUR = 25;                 // étiquette sûre (≈ 5 σ)
export const NLS_BETA_MAX = 0.7;
export const NP0 = 9;                          // paramètres avant le warp : f1, Ω, β1, β2, m1, ψ, θ, m2, f3 (raie étrangère)

export const centsDe = (f, r) => 1200 * Math.log2(f / r);

const bornes = (J) => {
  const LB = [-Infinity, 0.02, 0, -NLS_BETA_MAX, 0, -Infinity, -Infinity, -0.45, -Infinity], UB = [Infinity, Infinity, NLS_BETA_MAX, NLS_BETA_MAX, 0.45, Infinity, Infinity, 0.45, Infinity];
  for (let j = 0; j < J; j++) { LB.push(-3e-3); UB.push(3e-3); }
  for (let j = 0; j < J; j++) { LB.push(-0.6); UB.push(0.6); }
  return { LB, UB };
};

// ---- démodulation : mélange, filtre CIC d'ordre 3, décimation ---------------------------------------------------------------
export function demodPartiel(x, i0, i1, k, mu, sr, D) {
  const N = i1 - i0, M = Math.max(1, Math.round(sr / D)), w = -TWO_PI * mu / sr;
  const nOut = Math.max(0, Math.floor(N / M) - 3);
  const re = new Float64Array(nOut), im = new Float64Array(nOut), t = new Float64Array(nOut);
  let c = 1, s = 0;
  const cw = Math.cos(w), sw = Math.sin(w);
  let a1r = 0, a1i = 0, a2r = 0, a2i = 0, a3r = 0, a3i = 0;           // intégrateurs
  let p1r = 0, p1i = 0, p2r = 0, p2i = 0, p3r = 0, p3i = 0;           // états des peignes
  const gain = 1 / (M * M * M);
  let q = -3, m = 0;
  for (let i = 0; i < N; i++) {
    if ((i & 1023) === 0) { c = Math.cos(w * i); s = Math.sin(w * i); }
    const v = x[i0 + i];
    a1r += v * c; a1i += v * s;
    a2r += a1r; a2i += a1i;
    a3r += a2r; a3i += a2i;
    const c2 = c * cw - s * sw; s = s * cw + c * sw; c = c2;
    if (++m === M) {
      m = 0;
      const d1r = a3r - p1r, d1i = a3i - p1i; p1r = a3r; p1i = a3i;
      const d2r = d1r - p2r, d2i = d1i - p2i; p2r = d1r; p2i = d1i;
      const d3r = d2r - p3r, d3i = d2i - p3i; p3r = d2r; p3i = d2i;
      if (q >= 0 && q < nOut) {
        re[q] = d3r * gain; im[q] = d3i * gain;
        t[q] = ((i - 1.5 * (M - 1)) / sr) - N / (2 * sr);
      }
      q++;
    }
  }
  return { re, im, t, n: nOut, dt: M / sr, M, sr, k, mu, T: N / sr };
}

// Gain du filtre CIC3 à l'écart ν (Hz) de la fréquence de mélange.
export const droop = (nu, M, sr) => {
  const x = Math.PI * nu / sr, sx = Math.sin(x);
  if (Math.abs(sx) < 1e-12) return 1;
  const g = Math.sin(M * x) / (M * sx);
  return g * g * g;
};

// ---- Bessel -----------------------------------------------------------------------------------------------------------------
// J_n(x) pour n = 0 .. nmax+1 (série entière). J_{-n} = (-1)^n J_n.
export function besselJ(x, nmax, out) {
  for (let n = 0; n <= nmax + 1; n++) {
    let term = 1;
    for (let j = 1; j <= n; j++) term *= (x / 2) / j;
    let sum = term;
    for (let j = 1; j < 30; j++) { term *= -((x / 2) * (x / 2)) / (j * (j + n)); sum += term; if (Math.abs(term) < 1e-16 * Math.abs(sum)) break; }
    out[n] = sum;
  }
}
export const Jn = (J, n) => (n >= 0 ? J[n] : (n & 1 ? -J[-n] : J[-n]));

// Résolution d'un système n×n (Gauss, pivot partiel), A plat modifié.
export function resoudre(A, b, n) {
  for (let i = 0; i < n; i++) {
    let p = i;
    for (let j = i + 1; j < n; j++) if (Math.abs(A[j * n + i]) > Math.abs(A[p * n + i])) p = j;
    if (!(Math.abs(A[p * n + i]) > 1e-300)) return null;
    if (p !== i) { for (let c = 0; c < n; c++) { const u = A[i * n + c]; A[i * n + c] = A[p * n + c]; A[p * n + c] = u; } const u = b[i]; b[i] = b[p]; b[p] = u; }
    for (let j = i + 1; j < n; j++) {
      const f = A[j * n + i] / A[i * n + i];
      for (let c = i; c < n; c++) A[j * n + c] -= f * A[i * n + c];
      b[j] -= f * b[i];
    }
  }
  const x = new Float64Array(n);
  for (let i = n - 1; i >= 0; i--) { let s = b[i]; for (let c = i + 1; c < n; c++) s -= A[i * n + c] * x[c]; x[i] = s / A[i * n + i]; }
  return x;
}

// G x = b, G hermitienne nc×nc (Gr symétrique, Gi antisymétrique), par le système réel équivalent de taille 2·nc. Rend { xr, xi }.
export function resoudreHerm(Gr, Gi, br, bi, nc) {
  const n2 = 2 * nc, M = new Float64Array(n2 * n2), v = new Float64Array(n2);
  for (let a = 0; a < nc; a++) {
    for (let b = 0; b < nc; b++) {
      const gr = Gr[a * nc + b] * (a === b ? 1 + 1e-9 : 1), gi = Gi[a * nc + b];
      M[a * n2 + b] = gr; M[a * n2 + nc + b] = -gi; M[(nc + a) * n2 + b] = gi; M[(nc + a) * n2 + nc + b] = gr;
    }
    v[a] = br[a]; v[nc + a] = bi[a];
  }
  const x = resoudre(M, v, n2);
  const xr = new Float64Array(nc), xi = new Float64Array(nc);
  if (x) for (let a = 0; a < nc; a++) { xr[a] = x[a]; xi[a] = x[nc + a]; }
  else { xr[0] = br[0] / Math.max(Gr[0], 1e-300); xi[0] = bi[0] / Math.max(Gr[0], 1e-300); }
  return { xr, xi };
}

// ---- modèle -----------------------------------------------------------------------------------------------------------------
export class Modele {
  // ds : partiels démodulés (même grille de temps) ; J : nombre de nœuds du warp ; libre : avec une raie étrangère libre (f3).
  constructor(ds, J = 3, { libre = false } = {}) {
    this.ds = ds; this.Q = ds.length; this.n = ds[0].n; this.t = ds[0].t; this.J = J; this.libre = libre; this.nc = libre ? 3 : 2;
    const n = this.n;
    this.wr = Array.from({ length: 2 * NM + 1 }, () => new Float64Array(n));
    this.wi = Array.from({ length: 2 * NM + 1 }, () => new Float64Array(n));
    this.tau = new Float64Array(n); this.dq = new Float64Array(n); this.gq = new Float64Array(n);
    this.sr_ = Array.from({ length: 3 }, () => new Float64Array(n)); this.si_ = Array.from({ length: 3 }, () => new Float64Array(n));
    this.cr = new Float64Array(2 * NM + 1); this.ci = new Float64Array(2 * NM + 1);
    this.J1 = new Float64Array(NM + 3); this.J2 = new Float64Array(NM + 3);
    this.Ndata = 2 * n * this.Q;
    this.N = this.Ndata + 2 * J;                 // + les pseudo-résidus de l'a priori sur le warp
    this.npar = NP0 + 2 * J;
    // A priori doux sur le warp (écart type attendu : 0,5 ¢ en fréquence, 20 % en niveau), pesé comme un échantillon de bruit à 40 dB :
    // il ne joue que pour les modes que les données ne contraignent pas (en zig-zag), sans quoi le moindre pas de Gauss-Newton les fait exploser.
    let e = 0; for (const d of ds) for (let q = 0; q < d.n; q++) e += d.re[q] ** 2 + d.im[q] ** 2;
    this.energie = e;
    const nu = 1e-4 * e / this.Ndata;
    this.wd = Math.sqrt(nu) / 3e-4; this.wg = Math.sqrt(nu) / 0.2;
    this.amp = Array.from({ length: this.Q }, () => new Float64Array(6));      // A_c (re, im) pour c < 3
    this.iw = new Int32Array(n); this.uw = new Float64Array(n);
    const t0 = this.t[0], span = this.t[n - 1] - t0 || 1;
    for (let q = 0; q < n; q++) {
      const s = ((this.t[q] - t0) / span) * (J - 1);
      const j = Math.min(J - 2, Math.max(0, Math.floor(s)));
      this.iw[q] = J > 1 ? j : 0; this.uw[q] = J > 1 ? s - j : 0;
    }
    const b = bornes(J); this.LB = b.LB; this.UB = b.UB;
    // chapeaux des nœuds (moyenne retirée) et ∂τ/∂d_j : intégrale cumulée du chapeau
    this.H = Array.from({ length: J }, () => new Float64Array(n));
    this.W = Array.from({ length: J }, () => new Float64Array(n));
    for (let q = 0; q < n; q++) { this.H[this.iw[q]][q] += 1 - this.uw[q]; if (J > 1) this.H[Math.min(J - 1, this.iw[q] + 1)][q] += this.uw[q]; }
    for (let j = 0; j < J; j++) {
      let mh = 0; for (let q = 0; q < n; q++) mh += this.H[j][q]; mh /= n;
      for (let q = 0; q < n; q++) this.H[j][q] -= mh;
      let acc = 0;
      for (let q = 1; q < n; q++) { acc += 0.5 * (this.H[j][q] + this.H[j][q - 1]) * (this.t[q] - this.t[q - 1]); this.W[j][q] = acc; }
    }
    this.ptsS = null;
  }

  // Coefficients complexes C_n d'une anche (indices de phase et d'amplitude signés, phases θ et ψ communes), gain du filtre compris.
  coefs(J, m, psi, th, delta, Om, M, sr) {
    const { cr, ci } = this;
    const cp = Math.cos(psi), sp = Math.sin(psi);
    for (let n = -NM; n <= NM; n++) {
      const j0 = Jn(J, n), jm = Jn(J, n - 1), jp = Jn(J, n + 1);
      const ar = j0 + 0.5 * m * cp * (jm + jp), ai = 0.5 * m * sp * (jm - jp);
      const ang = n * th;
      const ce = Math.cos(ang), se = Math.sin(ang);
      const g = droop(delta + n * Om, M, sr);
      cr[n + NM] = g * (ar * ce - ai * se); ci[n + NM] = g * (ar * se + ai * ce);
    }
  }

  // Le warp : τ(t) = t + ∫ (d − d̄), et le niveau commun g(t) = 1 + (g − ḡ)
  calculerTau(p) {
    const { n, t, tau, dq, gq, iw, uw, J } = this;
    let moy = 0, mg = 0;
    for (let q = 0; q < n; q++) {
      const j1 = Math.min(J - 1, iw[q] + 1);
      const a = p[NP0 + iw[q]], b = p[NP0 + j1];
      dq[q] = a + (b - a) * uw[q];
      moy += dq[q];
      const ga = p[NP0 + J + iw[q]], gb = p[NP0 + J + j1];
      gq[q] = ga + (gb - ga) * uw[q];
      mg += gq[q];
    }
    moy /= n; mg /= n;
    for (let q = 0; q < n; q++) gq[q] = 1 + gq[q] - mg;
    let acc = 0;
    tau[0] = t[0];
    for (let q = 1; q < n; q++) { acc += 0.5 * ((dq[q] - moy) + (dq[q - 1] - moy)) * (t[q] - t[q - 1]); tau[q] = t[q] + acc; }
  }

  // Colonnes du partiel qi pour les paramètres p (w déjà calculés) : remplit this.sr_[c], this.si_[c].
  colonnes(p, qi) {
    const { ds, n, tau, gq, wr, wi, cr, ci } = this;
    const f1 = p[0], Om = p[1], b1 = p[2], b2 = p[3], m = p[4], psi = p[5], th = p[6], m2 = p[7], f3 = p[8], f2 = f1 + Om;
    const d = ds[qi], k = d.k, M = d.M, sr = d.sr;
    besselJ(k * b1, NM, this.J1); besselJ(k * b2, NM, this.J2);
    for (let r = 0; r < 2; r++) {
      const del = k * (r ? f2 : f1) - d.mu, sRe = this.sr_[r], sIm = this.si_[r];
      this.coefs(r ? this.J2 : this.J1, r ? m2 : m, psi, th, del, Om, M, sr);
      for (let q = 0; q < n; q++) {
        let ar = 0, ai = 0;
        for (let j = 0; j < 2 * NM + 1; j++) { ar += cr[j] * wr[j][q] - ci[j] * wi[j][q]; ai += cr[j] * wi[j][q] + ci[j] * wr[j][q]; }
        const ph = TWO_PI * (del * tau[q] + d.mu * (tau[q] - this.t[q])), c = Math.cos(ph), s = Math.sin(ph);   // k f_r τ − μ t
        const gg = gq[q];
        sRe[q] = gg * (ar * c - ai * s); sIm[q] = gg * (ar * s + ai * c);
      }
    }
    if (this.libre) {
      const del = k * f3 - d.mu, sRe = this.sr_[2], sIm = this.si_[2];
      for (let q = 0; q < n; q++) {
        const ph = TWO_PI * (del * tau[q] + d.mu * (tau[q] - this.t[q])), gg = gq[q];
        sRe[q] = gg * Math.cos(ph); sIm[q] = gg * Math.sin(ph);
      }
    }
  }

  // Gram et second membre du partiel qi : renvoie { Gr, Gi, br, bi, A } (A = { xr, xi })
  normales(qi) {
    const nc = this.nc, n = this.n, d = this.ds[qi], yr = d.re, yi = d.im;
    const Gr = new Float64Array(nc * nc), Gi = new Float64Array(nc * nc), br = new Float64Array(nc), bi = new Float64Array(nc);
    for (let a = 0; a < nc; a++) {
      const ar_ = this.sr_[a], ai_ = this.si_[a];
      for (let b = a; b < nc; b++) {
        const cr_ = this.sr_[b], ci_ = this.si_[b];
        let gr = 0, gi = 0;
        for (let q = 0; q < n; q++) { gr += ar_[q] * cr_[q] + ai_[q] * ci_[q]; gi += ar_[q] * ci_[q] - ai_[q] * cr_[q]; }
        Gr[a * nc + b] = gr; Gr[b * nc + a] = gr; Gi[a * nc + b] = gi; Gi[b * nc + a] = -gi;
      }
      let sr_ = 0, si__ = 0;
      for (let q = 0; q < n; q++) { sr_ += ar_[q] * yr[q] + ai_[q] * yi[q]; si__ += ar_[q] * yi[q] - ai_[q] * yr[q]; }
      br[a] = sr_; bi[a] = si__;
    }
    return { Gr, Gi, br, bi, A: resoudreHerm(Gr, Gi, br, bi, nc) };
  }

  // Résidu projeté (concaténé sur les partiels) ; rend la SSR. Remplit `res` (taille N) si fourni ; `garder` : mémorise les A et les colonnes.
  residu(p, res, garder = false) {
    const { ds, Q, n, tau, wr, wi, nc } = this;
    const Om = p[1];
    this.calculerTau(p);
    for (let q = 0; q < n; q++) {
      const ang = TWO_PI * Om * tau[q], c1 = Math.cos(ang), s1 = Math.sin(ang);
      wr[NM][q] = 1; wi[NM][q] = 0;
      for (let j = 1; j <= NM; j++) {
        const pr = wr[NM + j - 1][q], pi = wi[NM + j - 1][q];
        const nr = pr * c1 - pi * s1, ni = pr * s1 + pi * c1;
        wr[NM + j][q] = nr; wi[NM + j][q] = ni; wr[NM - j][q] = nr; wi[NM - j][q] = -ni;
      }
    }
    let ssr = 0, o = 0, prior = 0;
    for (let j = 0; j < this.J; j++) { const a = this.wd * p[NP0 + j], b = this.wg * p[NP0 + this.J + j]; prior += a * a + b * b; }
    for (let qi = 0; qi < Q; qi++) {
      this.colonnes(p, qi);
      const N = this.normales(qi), { xr, xi } = N.A, yr = ds[qi].re, yi = ds[qi].im;
      if (garder) {
        const A = this.amp[qi]; for (let a = 0; a < 3; a++) { A[2 * a] = a < nc ? xr[a] : 0; A[2 * a + 1] = a < nc ? xi[a] : 0; }
        if (!this.ptsS) this.ptsS = Array.from({ length: Q }, () => ({}));
        const P = this.ptsS[qi];
        P.s = Array.from({ length: nc }, (_, a) => ({ r: Float64Array.from(this.sr_[a]), i: Float64Array.from(this.si_[a]) }));
        P.Gr = N.Gr; P.Gi = N.Gi;
        P.wr = wr.map((a) => Float64Array.from(a)); P.wi = wi.map((a) => Float64Array.from(a));
      }
      for (let q = 0; q < n; q++) {
        let mr = 0, mi = 0;
        for (let a = 0; a < nc; a++) { mr += xr[a] * this.sr_[a][q] - xi[a] * this.si_[a][q]; mi += xr[a] * this.si_[a][q] + xi[a] * this.sr_[a][q]; }
        const er = yr[q] - mr, ei = yi[q] - mi;
        ssr += er * er + ei * ei;
        if (res) { res[o++] = er; res[o++] = ei; }
      }
    }
    this.ssrData = ssr;
    if (res) { for (let j = 0; j < this.J; j++) { res[o++] = this.wd * p[NP0 + j]; res[o++] = this.wg * p[NP0 + this.J + j]; } }
    ssr += prior;
    return ssr;
  }

  // Colonnes de la jacobienne (dr/dd_j et dr/dg_j) par la dérivée analytique de variable projection (Kaufman) : dr/dp = -P_perp (dS/dp) A.
  // À appeler juste après residu(p, ., true). Remplit cols[NP0 + j] (warp) et cols[NP0 + J + j] (niveau).
  jacobienneWarp(p, cols) {
    const { ds, Q, n, J, tau, gq, t, nc } = this;
    const f1 = p[0], Om = p[1], f2 = f1 + Om, f3 = p[8];
    const Nd = this.Ndata;
    for (let j = 0; j < J; j++) { cols[NP0 + j].fill(0); cols[NP0 + J + j].fill(0); }
    let o = 0;
    const Er = new Float64Array(n), Ei = new Float64Array(n), Mr = new Float64Array(n), Mi = new Float64Array(n);
    const zr = new Float64Array(n), zi = new Float64Array(n);
    for (let qi = 0; qi < Q; qi++) {
      const d = ds[qi], k = d.k, M = d.M, sr = d.sr, P = this.ptsS[qi], A = this.amp[qi];
      besselJ(k * p[2], NM, this.J1); besselJ(k * p[3], NM, this.J2);
      Er.fill(0); Ei.fill(0); Mr.fill(0); Mi.fill(0);
      for (let r = 0; r < nc; r++) {
        const Ar = A[2 * r], Ai = A[2 * r + 1];
        if (r < 2) {
          const fr = r ? f2 : f1, del = k * fr - d.mu;
          this.coefs(r ? this.J2 : this.J1, r ? p[7] : p[4], p[5], p[6], del, Om, M, sr);
          const { cr, ci } = this;
          for (let q = 0; q < n; q++) {
            let ar = 0, ai = 0, br = 0, bi = 0;
            for (let jj = 0; jj < 2 * NM + 1; jj++) {
              const wr_ = P.wr[jj][q], wi_ = P.wi[jj][q], ur = cr[jj] * wr_ - ci[jj] * wi_, ui = cr[jj] * wi_ + ci[jj] * wr_;
              ar += ur; ai += ui;
              const fl = k * fr + (jj - NM) * Om; br += ur * fl; bi += ui * fl;
            }
            const ph = TWO_PI * (del * tau[q] + d.mu * (tau[q] - t[q])), c = Math.cos(ph), s = Math.sin(ph);
            const g = gq[q];
            const dr_ = -TWO_PI * g * (br * s + bi * c), di_ = TWO_PI * g * (br * c - bi * s);
            Er[q] += Ar * dr_ - Ai * di_; Ei[q] += Ar * di_ + Ai * dr_;
            const sr_ = (ar * c - ai * s), si_ = (ar * s + ai * c);
            Mr[q] += Ar * sr_ - Ai * si_; Mi[q] += Ar * si_ + Ai * sr_;
          }
        } else {
          // raie libre : s3 = g · porteuse ; ∂s3/∂τ = i 2π (k f3) s3
          const s3r = P.s[2].r, s3i = P.s[2].i, w3 = TWO_PI * k * f3;
          for (let q = 0; q < n; q++) {
            const dr_ = -w3 * s3i[q], di_ = w3 * s3r[q];
            Er[q] += Ar * dr_ - Ai * di_; Ei[q] += Ar * di_ + Ai * dr_;
            const g = gq[q];
            Mr[q] += (Ar * s3r[q] - Ai * s3i[q]) / g; Mi[q] += (Ar * s3i[q] + Ai * s3r[q]) / g;
          }
        }
      }
      for (let jj = 0; jj < 2 * J; jj++) {
        const warp = jj < J, j = warp ? jj : jj - J;
        const Wj = warp ? this.W[j] : this.H[j];
        for (let q = 0; q < n; q++) { const w = Wj[q]; zr[q] = (warp ? Er[q] : Mr[q]) * w; zi[q] = (warp ? Ei[q] : Mi[q]) * w; }
        // S^H z, puis G a = S^H z
        const cr_ = new Float64Array(nc), ci_ = new Float64Array(nc);
        for (let a = 0; a < nc; a++) {
          const sa = P.s[a]; let x = 0, y = 0;
          for (let q = 0; q < n; q++) { x += sa.r[q] * zr[q] + sa.i[q] * zi[q]; y += sa.r[q] * zi[q] - sa.i[q] * zr[q]; }
          cr_[a] = x; ci_[a] = y;
        }
        const { xr, xi } = resoudreHerm(P.Gr, P.Gi, cr_, ci_, nc);
        const col = cols[NP0 + jj];
        for (let q = 0; q < n; q++) {
          let pr = 0, pi = 0;
          for (let a = 0; a < nc; a++) { pr += xr[a] * P.s[a].r[q] - xi[a] * P.s[a].i[q]; pi += xr[a] * P.s[a].i[q] + xi[a] * P.s[a].r[q]; }
          col[o + 2 * q] = -(zr[q] - pr); col[o + 2 * q + 1] = -(zi[q] - pi);
        }
      }
      o += 2 * n;
    }
    for (let j = 0; j < J; j++) { cols[NP0 + j][Nd + 2 * j] = this.wd; cols[NP0 + J + j][Nd + 2 * j + 1] = this.wg; }
  }
}

export const pasFD = (T, J) => {
  const s = [1e-3 / T, 1e-3 / T, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 1e-3 / T];
  for (let j = 0; j < J; j++) s.push(2e-5);
  for (let j = 0; j < J; j++) s.push(2e-3);
  return s;
};

// Levenberg-Marquardt sur les paramètres `libres` (indices dans p). Générateur : un `yield` par itération, pour que le moteur
// répartisse le calcul sur plusieurs images (certificat.js) ; ajusterLM l'exécute d'un trait.
export function ajusterLM(mod, p0, libres, steps, opts) {
  const g = ajusterLMg(mod, p0, libres, steps, opts);
  let r;
  while (!(r = g.next()).done);
  return r.value;
}
export function* ajusterLMg(mod, p0, libres, steps, { iter = 25, tol = 1e-5 } = {}) {
  const N = mod.N, P = libres.length;
  let p = Float64Array.from(p0);
  const r0 = new Float64Array(N), r1 = new Float64Array(N);
  let S = mod.residu(p, r0);
  let lam = 1e-2, it = 0;
  const J = Array.from({ length: P }, () => new Float64Array(N));
  const T = mod.ds[0].T, fmax = 0.25 / T;
  const NP = mod.NP ?? NP0, freqIdx = mod.freqIdx ?? [0, 1, 8];
  const warpIdx = new Map(); libres.forEach((idx, a) => { if (idx >= NP) warpIdx.set(idx, a); });
  const colsW = Array.from({ length: mod.npar }, (_, i) => (i >= NP ? new Float64Array(N) : null));
  for (; it < iter; it++) {
    // base (mémorise colonnes et Gram) puis dérivées analytiques du warp, puis différences finies des autres
    if (warpIdx.size) { mod.residu(p, r0, true); mod.jacobienneWarp(p, colsW); }
    for (let a = 0; a < P; a++) {
      const idx = libres[a], Ja = J[a];
      if (idx >= NP) { Ja.set(colsW[idx]); continue; }
      const q = Float64Array.from(p), h = steps[idx];
      q[idx] += h;
      mod.residu(q, r1);
      for (let i = 0; i < N; i++) Ja[i] = (r1[i] - r0[i]) / h;
    }
    const A = new Float64Array(P * P), g = new Float64Array(P);
    let tr = 0;
    for (let a = 0; a < P; a++) {
      for (let b = a; b < P; b++) { let s = 0; const Ja = J[a], Jb = J[b]; for (let i = 0; i < N; i++) s += Ja[i] * Jb[i]; A[a * P + b] = s; A[b * P + a] = s; }
      let s = 0; const Ja = J[a]; for (let i = 0; i < N; i++) s += Ja[i] * r0[i]; g[a] = -s;
      tr += A[a * P + a];
    }
    let ok = false;
    for (let essai = 0; essai < 10; essai++) {
      const Al = A.slice(); for (let a = 0; a < P; a++) Al[a * P + a] = Al[a * P + a] * (1 + lam) + 1e-10 * tr / P;
      const d = resoudre(Al, g.slice(), P);
      if (!d) { lam *= 10; continue; }
      const q = Float64Array.from(p);
      let sc = 1;
      for (let a = 0; a < P; a++) { const idx = libres[a]; if (freqIdx.includes(idx)) sc = Math.min(sc, fmax / Math.max(1e-300, Math.abs(d[a]))); }
      for (let a = 0; a < P; a++) { const idx = libres[a]; q[idx] = Math.min(mod.UB[idx], Math.max(mod.LB[idx], p[idx] + sc * d[a])); }
      const S2 = mod.residu(q, r1);
      if (S2 < S) {
        const conv = (S - S2) < tol * S;
        p = q; S = S2; r0.set(r1); lam = Math.max(1e-7, lam / 5); ok = true;
        if (conv) it = iter;
        break;
      }
      lam *= 5;
    }
    if (!ok) break;
    yield (P + 2) * mod.n * mod.Q * 1e-3;       // coût de l'itération en milliers de « partiel-échantillon évalué » (une évaluation du résidu par paramètre, plus le pas et son essai) : le temps de calcul se compte en ça, pas en nombre de pas
  }
  return { p, ssr: S, it };
}

// ---- recherche des départs : spectre « somme harmonique » -------------------------------------------------------------------
// Deux spectres : S (somme des puissances des partiels) et G (moyenne géométrique des puissances normalisées par partiel). Une raie latérale de
// modulation de phase (une seule fois par partiel, à f1 ± Ω/k) domine S mais pas G ; une anche, présente à tous les partiels, domine G.
export function spectreHarmonique(ds, fLo, fHi) {
  const T = ds[0].T, K = ds.length, step = 0.5 / (K * T), np = Math.min(6000, Math.ceil((fHi - fLo) / step) + 1), S = new Float64Array(np), G = new Float64Array(np);
  for (const d of ds) {
    const N = d.n;
    let P = 1; while (P < 8 * N) P <<= 1;
    const re = new Float64Array(P), im = new Float64Array(P);
    for (let n = 0; n < N; n++) { const w = 0.5 - 0.5 * Math.cos(TWO_PI * (n + 0.5) / N); re[n] = d.re[n] * w; im[n] = d.im[n] * w; }
    FFT.get(P).transform(re, im);                 // e^{-iωt} : une raie à +ν a son pic à la case +ν/df
    const df = 1 / (P * d.dt);
    const mag = (b) => { const j = ((b % P) + P) % P; return re[j] * re[j] + im[j] * im[j]; };
    const Pk = new Float64Array(np);
    let mk = 1e-300;
    for (let p = 0; p < np; p++) {
      const f = fLo + p * (fHi - fLo) / (np - 1), nu = (d.k * f - d.mu) / df, b = Math.floor(nu), u = nu - b;
      Pk[p] = ((1 - u) * mag(b) + u * mag(b + 1)) / (N * N);
      S[p] += Pk[p];
      if (Pk[p] > mk) mk = Pk[p];
    }
    for (let p = 0; p < np; p++) G[p] += Math.log(Pk[p] / mk + 1e-6);
  }
  for (let p = 0; p < np; p++) G[p] = Math.exp(G[p] / K);
  return { S, G, fLo, df: (fHi - fLo) / (np - 1) };
}
export function pics(sp, M, cle = 'S') {
  const S = sp[cle], { fLo, df } = sp, o = [];
  for (let p = 1; p < S.length - 1; p++) if (S[p] > S[p - 1] && S[p] >= S[p + 1]) {
    const a = S[p - 1], b = S[p], c = S[p + 1], d = a - 2 * b + c, dx = d !== 0 ? 0.5 * (a - c) / d : 0;
    o.push({ f: fLo + (p + dx) * df, h: b });
  }
  o.sort((x, y) => y.h - x.h);
  return o.slice(0, M);
}

// ---- lecture ------------------------------------------------------------------------------------------------------------------
// x : échantillons ; [i0, i1) : la fenêtre ; fc : la note visée (Hz) ; sr.
// options : plageBasC / plageHautC (¢ de recherche autour de fc), prior [fa, fb] (lectures du moteur : un départ de plus), Kmax.
// Rend { ok, f:[f1,f2], sigmaC, Om, b, m, psi, th, derive (¢/s), agit (¢ rms), r, llr, ssr, dof, K, Ku, T, snr, plancherDb, libre, ... } ou { ok:false, raison }.
export function lireBessel(x, i0, i1, sr, fc, opts = {}) {
  const g = lireBesselGen(x, i0, i1, sr, fc, opts);
  let r;
  while (!(r = g.next()).done);
  return r.value;
}
export function* lireBesselGen(x, i0, i1, sr, fc, opts = {}) {
  const t0 = typeof performance !== 'undefined' ? performance.now() : 0;
  const { plageBasC = 50, plageHautC = 110, prior = null, priorFirst = false, chaud = false, pInit = null, libreInit = null, dt = 0, Kmax = 4, iter = 15, iterEtape = 5, tol = 1e-4, nGarde = 99, nLibre = 1, nDeparts = 5, noeudsS = 0.5, omegaMax = 60, libre = true } = opts;
  const T = (i1 - i0) / sr;
  if (!(T > 0.3)) return { ok: false, raison: 'court' };
  const fLo = fc * 2 ** (-plageBasC / 1200), fHi = fc * 2 ** (plageHautC / 1200);   // l'anche basse à ±35 ¢ de la note, l'autre jusqu'à ~55 ¢ plus haut
  const K = Math.max(1, Math.min(Kmax, Math.floor(0.42 * sr / fHi)));
  const ks = Array.from({ length: K }, (_, i) => i + 1);
  const J = Math.max(2, Math.min(9, Math.ceil(T / noeudsS) + 1));
  // étage 1 : large bande autour de la note, pour trouver les pics
  const fm = (fLo + fHi) / 2, D1 = Math.min(sr / 2, Math.max(60, 1.2 * K * (fHi - fLo)));
  const ds1 = ks.map((k) => demodPartiel(x, i0, i1, k, k * fm, sr, D1));
  if (ds1[0].n < 12) return { ok: false, raison: 'court' };
  const sp = spectreHarmonique(ds1, fLo, fHi);
  // les candidats : les pics de G (anches présentes à tous les partiels), complétés par ceux de S (anche dont le fondamental manque : micro à bande coupée)
  const pk = pics(sp, 8, 'G');
  if (!pk.length) return { ok: false, raison: 'sans pic' };
  for (const q of pics(sp, 3, 'S')) if (!pk.some((p) => Math.abs(p.f - q.f) < 1.2 / (K * T))) pk.push({ f: q.f, h: 2e-5 * pk[0].h });
  yield;
  // départs (f1, Om) : la raie la plus forte avec chacune des suivantes (et l'autre étiquette de chaque paire : la seconde est la bande latérale
  // de la première), puis la paire lue par le moteur. Pas de classement par résidu avant ajustement : à 0,1 Hz près d'erreur sur une position,
  // le résidu du partiel 2 ne dit rien (agitation de la main) ; chaque départ est ajusté en entier (avec élagage au partiel 2).
  const res1 = 1 / (K * T);
  const dep = [], dep2 = [];
  const addPair = (x1, x2) => { const om = x2 - x1; if (om > 1.2 * res1 && om < omegaMax) { dep.push([x1, om]); dep2.push([x1 - om, om]); } };
  const distincts = [];
  for (const q of pk) if (distincts.every((d) => Math.abs(d.f - q.f) > 1.2 * res1) && q.h > 1e-5 * pk[0].h) distincts.push(q);
  // le spectre d'abord, le moteur ensuite : une paire lue de travers par le moteur ne doit pas prendre la place de la bonne.
  // v64 : TOUTES les paires des trois raies les plus hautes, pas seulement celles de la plus haute avec une autre : avec une raie étrangère forte (un autre son à
  // −3 dB) la vraie paire (B, A) et la fausse (B, C) ne se distinguent pas, et la fausse n'était jamais essayée, donc jamais départagée (4 lectures « sûr » à +4 et +6 ¢).
  // Les étiquettes principales des paires d'abord, les étiquettes décalées ensuite.
  const topD = distincts.slice(0, 4);
  for (const [a, b] of [[0, 1], [0, 2], [1, 2], [0, 3], [1, 3], [2, 3]]) if (b < topD.length) addPair(Math.min(topD[a].f, topD[b].f), Math.max(topD[a].f, topD[b].f));
  dep.push(...dep2);
  const depSpectre = dep.slice();
  if (prior) {
    const n0 = dep.length;
    addPair(Math.min(prior[0], prior[1]), Math.max(prior[0], prior[1]));
    if (priorFirst) dep.unshift(...dep.splice(n0));       // lecture déjà connue (ajustement chaud) : son départ passe devant ceux du spectre
  }
  // ajustement chaud : le pic du spectre le plus proche de la lecture connue passe devant (la hauteur a pu dériver depuis l'ajustement d'où l'on part)
  if (chaud && pInit && prior && depSpectre.length) {
    const p1 = Math.min(prior[0], prior[1]), pO = Math.abs(prior[1] - prior[0]);
    let meilleur = null;
    for (const d of depSpectre) { const dist = Math.abs(d[0] - p1) + Math.abs(d[1] - pO); if (!meilleur || dist < meilleur.dist) meilleur = { d, dist }; }
    if (meilleur && meilleur.dist < 0.6 * pO + res1) dep.unshift(meilleur.d);
  }
  if (!dep.length) { const om = 2 * res1; dep.push([distincts[0].f, om], [distincts[0].f - om, om]); }   // anches non séparées : le critère le dira
  const Dm = (spread) => Math.min(sr / 2, Math.max(opts.D ?? 0, 2.4 * ((K + 4) * spread / 2 + 3) + 10));   // les raies vont de −2Ω à (K+2)Ω autour du partiel
  const cache = new Map();
  const donnees = (f1, Om) => {
    const centre = f1 + Om / 2, D = Dm(Om), clef = `${centre.toFixed(2)}|${D}`;
    if (!cache.has(clef)) cache.set(clef, ks.map((k) => demodPartiel(x, i0, i1, k, k * centre, sr, D)));
    return cache.get(clef);
  };
  const steps = pasFD(T, J);
  const toutes = (mod, avecF3) => Array.from({ length: mod.npar }, (_, i) => i).filter((i) => avecF3 || i !== 8);
  const sols = [];
  const vus = [];
  let rMin = Infinity;
  // Un départ, ajusté en entier. `force` : pas d'élagage (le concurrent du meilleur doit être ajusté pour que le LLR veuille dire quelque chose).
  function* ajusterDepart(f1d, Omd, force) {
    const ds = donnees(f1d, Omd);
    yield;
    // θ de départ : le meilleur de quatre sur le partiel 2 (ajustement chaud : les paramètres de l'ajustement d'avant)
    let best = null;
    if (chaud && pInit) {
      const p = new Float64Array(NP0 + 2 * J);
      for (let i = 0; i < NP0; i++) p[i] = pInit[i] ?? 0;
      p[0] = f1d; p[1] = Omd;
      p[6] += TWO_PI * Omd * dt;      // θ est la phase du battement au CENTRE de la fenêtre : le centre a bougé de dt secondes depuis l'ajustement d'où l'on part
      best = { S: 0, p };
    } else {
      const m2 = new Modele(ds.slice(0, Math.min(2, K)), J);
      for (const th of [0, 1.5708, 3.1416, 4.7124]) {
        const p = new Float64Array(NP0 + 2 * J); p[0] = f1d; p[1] = Omd; p[2] = 0.12; p[3] = -0.12; p[4] = 0.05; p[6] = th; p[7] = -0.05;
        const S = m2.residu(p);
        if (!best || S < best.S) best = { S, p };
      }
    }
    // continuation sur les partiels : 1, 2, 3, 4 … (le warp se cale sur les bas partiels, peu sensibles à la phase)
    let pp = best.p, elague = false;
    const etapes = [1, 2, 3, 4, 6].filter((q) => q < K).concat([K]);      // aussi à chaud : le warp se cale sur les bas partiels avant les hauts (sans quoi la dérive de la fenêtre fait décrocher le partiel 4)
    for (const q of etapes) {
      const mod = new Modele(ds.slice(0, q), J);
      pp = (yield* ajusterLMg(mod, pp, toutes(mod, false), steps, { iter: q === K ? iter : iterEtape, tol })).p;
      // élagage : un départ dont le résidu relatif, aux deux premiers partiels, est bien pire que celui du meilleur ne sera pas rattrapé
      if (q === Math.min(2, K)) {
        mod.residu(pp);
        const rr = mod.ssrData / Math.max(mod.energie, 1e-300);
        if (!force && rr > 3 * rMin + 0.05) { elague = true; break; }
        rMin = Math.min(rMin, rr);
      }
    }
    if (elague) return null;
    const mod = new Modele(ds, J);
    return { p: pp, ssr: mod.residu(pp), ssrData: mod.ssrData, mod, depart: [f1d, Omd] };
  }
  for (const [f1d, Omd] of dep) {
    if (sols.length >= nDeparts) break;
    if (vus.some((v) => Math.abs(v[0] - f1d) < 0.5 * res1 && Math.abs(v[1] - Omd) < 0.5 * res1 + 0.01 * Omd)) continue;
    vus.push([f1d, Omd]);
    const r = yield* ajusterDepart(f1d, Omd, false);
    if (r) sols.push(r);
  }
  // le concurrent du meilleur : l'autre étiquette (la raie la plus forte vue comme la 2e anche, la première étant une anche à peine audible)
  if (sols.length && !chaud) {
    sols.sort((u, v) => u.ssrData - v.ssrData);
    const b0 = sols[0].p;
    // v64 : les deux étiquettes voisines, la paire décalée d'un battement vers le bas (la faible lue pour la forte) ET vers le haut (la raie latérale haute lue pour la
    // faible) ; l'une des deux seules laissait passer le cas Ω = 26 Hz où la vraie paire n'était que le rival « vers le haut » de la mauvaise.
    for (const sens of [-1, 1]) {
      const f1r = b0[0] + sens * b0[1];
      if (sols.some((q) => Math.abs(q.p[0] - f1r) < 0.3 * b0[1] && Math.abs(q.p[1] - b0[1]) < 0.3 * b0[1])) continue;
      const r = yield* ajusterDepart(f1r, b0[1], true);
      if (r) sols.push(r);
    }
  }
  if (!sols.length) return { ok: false, raison: 'sans départ' };
  // Les solutions se comparent sur les MÊMES données : bande commune qui contient toutes les raies de toutes les solutions.
  if (sols.length > nGarde) { sols.sort((u, v) => u.ssrData - v.ssrData); sols.length = nGarde; }
  const lo = Math.min(...sols.map((q) => q.p[0])), hi = Math.max(...sols.map((q) => q.p[0] + q.p[1]));
  const centreC = (lo + hi) / 2, DC = Dm(hi - lo);
  const commun = ks.map((k) => demodPartiel(x, i0, i1, k, k * centreC, sr, DC));
  for (const q of sols) {
    const mod = new Modele(commun, J);
    const r = yield* ajusterLMg(mod, q.p, toutes(mod, false), steps, { iter: 4 });
    q.p = r.p; q.mod = mod; q.ssr = mod.residu(r.p); q.ssrData = mod.ssrData; q.libre = false;
  }
  sols.sort((u, v) => u.ssr - v.ssr);
  // Les trois meilleures hypothèses d'étiquette sont menées jusqu'au bout sur les mêmes données : un rival mal convergé (4 itérations) paraissait 1 000 σ² plus mauvais
  // que la vraie paire et la fausse paire passait (banc v64 : trois lectures « sûr » fausses de 7 ¢ ou 16 ¢, aucune quand les itérations sont poussées).
  if (!chaud) {
    for (const q of sols.slice(0, 3)) {
      const r = yield* ajusterLMg(q.mod, q.p, toutes(q.mod, false), steps, { iter: 10, tol: 1e-5 });
      q.p = r.p; q.ssr = q.mod.residu(r.p); q.ssrData = q.mod.ssrData;
    }
    sols.sort((u, v) => u.ssr - v.ssr);
  }
  // Raie étrangère : chaque hypothèse sérieuse (les trois meilleures) peut avoir une raie libre de plus. Une fuite à −15 dB à 0,3 Hz d'une anche
  // fait préférer à un ajustement sans elle un « modèle » où elle est la seconde anche et où la vraie seconde anche manque (r plus petit !).
  {
    const dofDe = (m) => Math.max(1, m.Ndata - m.npar - 4 * m.Q);
    for (const q of sols.slice(0, chaud ? 1 : nLibre)) {      // à chaud : la meilleure seulement
      if (!libre) break;
      const resB = new Float64Array(q.mod.N);
      q.mod.residu(q.p, resB);
      const dsR = commun.map((d, qi) => {
        const o = commun.slice(0, qi).reduce((a, e) => a + 2 * e.n, 0), re = new Float64Array(d.n), im = new Float64Array(d.n);
        for (let i = 0; i < d.n; i++) { re[i] = resB[o + 2 * i]; im[i] = resB[o + 2 * i + 1]; }
        return { ...d, re, im };
      });
      const dem = 0.42 * DC / K;
      const spR = spectreHarmonique(dsR, centreC - dem, centreC + dem);
      const garde = 1.5 * res1, fa = q.p[0], fb = q.p[0] + q.p[1];
      // Une raie étrangère ne peut pas tenir la place d'une raie latérale (f_r + nΩ) : libre, elle se glisse à la place de la vraie seconde anche
      // (audit v64 : Ω = 26 Hz, l'anche faible à +Ω lue comme raie étrangère, la raie latérale basse prise pour elle, 50 ¢ d'erreur sur les deux, rapport de vraisemblance 3 494).
      const lateral = (f) => [fa, fb].some((fr) => [-3, -2, -1, 1, 2, 3].some((n) => Math.abs(f - (fr + n * q.p[1])) <= garde));
      const cand = pics(spR, 6, 'G').find((c) => Math.abs(c.f - fa) > garde && Math.abs(c.f - fb) > garde && !lateral(c.f));
      yield;
      if (!cand) continue;
      const modL = new Modele(commun, J, { libre: true });
      const p0 = Float64Array.from(q.p); p0[8] = cand.f;
      const r = yield* ajusterLMg(modL, p0, toutes(modL, true), steps, { iter: 10 });
      modL.residu(r.p);
      const s2 = q.ssrData / dofDe(q.mod);
      // adoptée si elle fait mieux de plus de 25 σ² (≈ 5 σ) et si ses deux anches n'ont pas bougé de plus d'un quart de battement (sinon c'est une autre hypothèse)
      if ((q.ssrData - modL.ssrData) / s2 >= NLS_LLR_SUR && Math.abs(r.p[0] - q.p[0]) < 0.25 * Math.abs(q.p[1]) + res1 && Math.abs(r.p[1] - q.p[1]) < 0.25 * Math.abs(q.p[1]) + res1) {
        q.p = r.p; q.mod = modL; q.ssr = modL.residu(r.p); q.ssrData = modL.ssrData; q.libre = true;
      }
    }
    sols.sort((u, v) => u.ssr - v.ssr);
  }
  const best = sols[0], pb = best.p, mod = best.mod;
  const rival = sols.slice(1).find((s) => Math.abs(s.p[0] - pb[0]) > 0.4 * pb[1] || Math.abs(s.p[1] - pb[1]) > 0.3 * pb[1]);
  const dof = Math.max(1, mod.Ndata - mod.npar - 4 * mod.Q);
  const s2 = best.ssrData / dof;
  // Qui est l'anche, qui est la raie étrangère ? Quand une raie étrangère est adoptée, chaque anche peut changer de rôle avec elle (la raie étrangère devient l'anche,
  // l'anche devient étrangère) : si ce modèle-là n'est pas pire de plus de LLR_MIN σ², le rôle des trois raies est indécidable (trois raies pures comparables : un autre
  // son à −3 dB, test de la v58 « raie étrangère à 1,7 Δ » : l'ajustement lisait +4 et +6 ¢ avec un rapport de vraisemblance de 106 contre la vraie paire).
  let llrAffectation = Infinity;
  if (best.libre && !chaud) {
    const fEtr = pb[8];
    for (const r of [0, 1]) {
      const fOut = r === 0 ? pb[0] : pb[0] + pb[1], fRest = r === 0 ? pb[0] + pb[1] : pb[0];
      const [lo, hi] = [fEtr, fRest].sort((u, v) => u - v);
      if (hi - lo < 1.2 * res1) continue;
      const p0 = Float64Array.from(pb); p0[0] = lo; p0[1] = hi - lo; p0[8] = fOut;
      const modA = new Modele(commun, J, { libre: true });
      const rr = yield* ajusterLMg(modA, p0, toutes(modA, true), steps, { iter: 12, tol: 1e-5 });
      modA.residu(rr.p);
      llrAffectation = Math.min(llrAffectation, (modA.ssrData - best.ssrData) / s2);
    }
  }
  const sig = covariance(mod, pb, steps, s2);
  const f1 = pb[0], f2 = pb[0] + pb[1];
  const sigC = [sig[0] * C_CENTS / f1, Math.hypot(sig[0], sig[1]) * C_CENTS / f2];
  let energie = 0;
  const res = new Float64Array(mod.N);
  mod.residu(pb, res, true);
  const snr = [], plancher = [];
  let o = 0;
  for (let qi = 0; qi < mod.Q; qi++) {
    const d = mod.ds[qi];
    let ey = 0, er = 0;
    for (let q = 0; q < d.n; q++) { ey += d.re[q] ** 2 + d.im[q] ** 2; er += res[o + 2 * q] ** 2 + res[o + 2 * q + 1] ** 2; }
    energie += ey;
    snr.push(10 * Math.log10(Math.max(1e-30, ey - er) / Math.max(1e-30, er)));
    plancher.push(planchersDb(d, res, o, mod.amp[qi]));
    o += 2 * d.n;
  }
  const Ku = snr.filter((v) => v >= 20).length;
  // Marge d'étiquette (dB) : au partiel k, la raie de l'anche faible contre la raie latérale que l'anche forte met au même endroit (J1 de son indice de phase, plus la
  // modulation d'amplitude). Sous 0 dB la raie « faible » est plus petite que la raie latérale qui la recouvre : la bande latérale et l'anche se confondent, seul le
  // modèle les distingue — et un faux modèle (raie latérale prise pour l'anche, anche prise pour raie latérale) y ajuste aussi bien (banc v64).
  const coefMag = (beta, m, psi, k, n) => {
    const Jb = new Float64Array(NM + 3); besselJ(k * beta, NM, Jb);
    const j0 = Jn(Jb, n), jm = Jn(Jb, n - 1), jp = Jn(Jb, n + 1);
    return Math.hypot(j0 + 0.5 * m * Math.cos(psi) * (jm + jp), 0.5 * m * Math.sin(psi) * (jm - jp));
  };
  let margeEtiquette = Infinity;
  for (let qi = 0; qi < Math.min(2, mod.Q); qi++) {
    const d = mod.ds[qi], A = mod.amp[qi], k = d.k;
    const a1 = Math.hypot(A[0], A[1]) * coefMag(pb[2], pb[4], pb[5], k, 0), a2 = Math.hypot(A[2], A[3]) * coefMag(pb[3], pb[7], pb[5], k, 0);
    const fort = a1 >= a2 ? 0 : 1;                        // 0 : l'anche basse est la plus forte, la faible est à +Ω ; 1 : l'inverse
    const lateral = fort === 0 ? Math.hypot(A[0], A[1]) * coefMag(pb[2], pb[4], pb[5], k, 1) : Math.hypot(A[2], A[3]) * coefMag(pb[3], pb[7], pb[5], k, -1);
    const faible = Math.min(a1, a2);
    margeEtiquette = Math.min(margeEtiquette, 20 * Math.log10(Math.max(faible, 1e-300) / Math.max(lateral, 1e-300)));
  }
  // la raie étrangère : son niveau relatif à l'anche la plus forte (dB), sur le partiel 1
  let libreInfo = null;
  if (best.libre) {
    const A = mod.amp[0], n3 = Math.hypot(A[4], A[5]), n12 = Math.max(Math.hypot(A[0], A[1]), Math.hypot(A[2], A[3]));
    libreInfo = { f: pb[8], dB: 20 * Math.log10(n3 / Math.max(n12, 1e-300)) };
  }
  // dérive (pente) et agitation (écart type autour de la pente) du warp, en ¢/s et ¢
  const dw = Array.from({ length: J }, (_, j) => pb[NP0 + j]);
  const moy = dw.reduce((a, b) => a + b, 0) / J, tj = dw.map((_, j) => (j / (J - 1) - 0.5) * T);
  const sxx = tj.reduce((a, b) => a + b * b, 0), pente = tj.reduce((a, b, j) => a + b * (dw[j] - moy), 0) / sxx;
  const agit = Math.sqrt(dw.reduce((a, v, j) => a + (v - moy - pente * tj[j]) ** 2, 0) / J) * C_CENTS;
  return {
    ok: true, f: [f1, f2], margeEtiquette, niveauDb: (() => { const A = mod.amp[0]; const a = Math.hypot(A[0], A[1]), b = Math.hypot(A[2], A[3]); return -Math.abs(20 * Math.log10(Math.max(a, 1e-300) / Math.max(b, 1e-300))); })(), sigmaC: sigC, Om: pb[1], b: [pb[2], pb[3]], m: pb[4], m2: pb[7], psi: pb[5], th: pb[6], libre: libreInfo,
    derive: pente * C_CENTS, agit, warpC: dw.map((v) => (v - moy) * C_CENTS), r: best.ssrData / Math.max(1e-300, energie), ssr: best.ssrData, dof, s2, K, Ku, T, J, snr, plancherDb: plancher, nPics: pk.length,
    llr: rival ? (rival.ssrData - best.ssrData) / s2 : Infinity, llrAffectation,
    rival: rival ? { f: [rival.p[0], rival.p[0] + rival.p[1]], ssr: rival.ssr } : null,
    debug: opts.debug ? { pics: pk, departs: dep, sols: sols.map((s) => [s.p[0], s.p[1], s.ssr, s.libre]) } : undefined,
    sol: pb, mod, ms: typeof performance !== 'undefined' ? performance.now() - t0 : 0,
  };
}

function covariance(mod, p, steps, s2) {
  const N = mod.N, P = mod.npar;
  const r0 = new Float64Array(N), r1 = new Float64Array(N);
  mod.residu(p, r0);
  const J = [];
  for (let a = 0; a < P; a++) {
    const q = Float64Array.from(p); q[a] += steps[a];
    mod.residu(q, r1);
    J.push(Float64Array.from(r1, (v, i) => (v - r0[i]) / steps[a]));
  }
  const A = new Float64Array(P * P);
  let tr = 0;
  for (let a = 0; a < P; a++) { for (let b = a; b < P; b++) { let s = 0; for (let i = 0; i < N; i++) s += J[a][i] * J[b][i]; A[a * P + b] = s; A[b * P + a] = s; } tr += A[a * P + a]; }
  for (let a = 0; a < P; a++) A[a * P + a] = A[a * P + a] * (1 + 1e-9) + 1e-9 * tr / P;
  const sig = [];
  for (let a = 0; a < 2; a++) {
    const e = new Float64Array(P); e[a] = 1;
    const c = resoudre(A.slice(), e, P);
    sig.push(c ? Math.sqrt(Math.max(0, s2 * c[a])) : Infinity);
  }
  return sig;
}

// Plancher hors modèle d'un partiel : médiane du module du spectre du résidu (Hann), relative à la plus forte porteuse (dB).
export function planchersDb(d, res, o, amp) {
  const n = d.n;
  if (n < 16) return null;
  let P = 1; while (P < 4 * n) P <<= 1;
  const re = new Float64Array(P), im = new Float64Array(P);
  for (let q = 0; q < n; q++) { const w = 0.5 - 0.5 * Math.cos(TWO_PI * (q + 0.5) / n); re[q] = res[o + 2 * q] * w; im[q] = res[o + 2 * q + 1] * w; }
  FFT.get(P).transform(re, im);
  const mags = new Float64Array(P);
  for (let j = 0; j < P; j++) mags[j] = Math.hypot(re[j], im[j]);
  mags.sort();
  const med = mags[P >> 1];
  const A = Math.max(Math.hypot(amp[0], amp[1]), Math.hypot(amp[2], amp[3]));
  return 20 * Math.log10(med / (0.5 * n * Math.max(A, 1e-300)) + 1e-300);
}
