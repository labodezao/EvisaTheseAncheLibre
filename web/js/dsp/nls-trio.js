// Lecture d'une note à TROIS anches (super musette) par moindres carrés non linéaires multi-partiels à peigne de Bessel (v64, audit Fable du
// 15/10/2026, recommandation R3 ; docs/CERTIFICAT.md).
//
// Modèle. Anche basse f_L = f_C − Δ−, anche centrale f_C, anche haute f_H = f_C + Δ+. Les anches voisines se tirent par le trou de soupape : chacune est
// modulée en phase ET en amplitude au rythme de ses battements. L'anche basse l'est à Δ− (battement avec la centrale), la haute à Δ+, la centrale aux
// DEUX (deux tons de modulation : le produit de deux séries de Bessel). Le terme Δ− + Δ+ (basse contre haute) est d'ordre β² : négligé (audit § 2).
// Partiel k de l'anche r : [1 + AM] · exp(i [2π k f_r τ(t) + k Σ β sin Φ]) ; indice de phase proportionnel au rang k (mesuré sur le H6, § 1.1).
//   inconnues non linéaires : f_C, Δ−, Δ+, β_L, β_Cm, β_Cp, β_H (signés), m_L, m_C, m_H, ψ, θ−, θ+ (13), plus le warp commun (dérive et agitation du
//   soufflet, niveau commun) ; les amplitudes complexes des partiels (le timbre) sont libres et éliminées (variable projection), comme nls-bessel.js.
// Quand Δ− = Δ+ le réseau se replie (les raies ±kΔ de la centrale tombent sur les anches extérieures) : au partiel 1 l'étiquette est indécidable,
// les partiels k ≥ 2 la lèvent par l'échelle de Bessel ; le rapport de vraisemblance contre les autres triplets de raies dit si c'est sûr.
//
// Module pur, sans DOM.
import {
  C_CENTS, demodPartiel, besselJ, Jn, resoudre, resoudreHerm, droop, spectreHarmonique, pics, planchersDb, ajusterLMg, NLS_LLR_SUR,
} from './nls-bessel.js';

const TWO_PI = 2 * Math.PI;
const NMO = 3;                    // raies latérales des anches extérieures : |n| <= 3
const NMC = 2;                    // raies de la centrale : |n|, |n'| <= 2 (25 raies)
export const NP3 = 14;            // fC, Δ−, Δ+, βL, βCm, βCp, βH, mL, mC, mH, ψ, θ−, θ+, f3 (raie étrangère)
export const NLS3_BETA_MAX = 0.7;

const bornes3 = (J) => {
  const B = NLS3_BETA_MAX;
  const LB = [-Infinity, 0.02, 0.02, -B, -B, -B, -B, -0.45, -0.45, -0.45, -Infinity, -Infinity, -Infinity, -Infinity];
  const UB = [Infinity, Infinity, Infinity, B, B, B, B, 0.45, 0.45, 0.45, Infinity, Infinity, Infinity, Infinity];
  for (let j = 0; j < J; j++) { LB.push(-3e-3); UB.push(3e-3); }
  for (let j = 0; j < J; j++) { LB.push(-0.6); UB.push(0.6); }
  return { LB, UB };
};

export const pasFD3 = (T, J) => {
  const s = [1e-3 / T, 1e-3 / T, 1e-3 / T, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 2e-3, 1e-3 / T];
  for (let j = 0; j < J; j++) s.push(2e-5);
  for (let j = 0; j < J; j++) s.push(2e-3);
  return s;
};

export class Modele3 {
  constructor(ds, J = 3, { libre = false } = {}) {
    this.ds = ds; this.Q = ds.length; this.n = ds[0].n; this.t = ds[0].t; this.J = J; this.libre = libre; this.nc = libre ? 4 : 3;
    this.NP = NP3; this.freqIdx = [0, 1, 2, 13];
    const n = this.n;
    const W = () => Array.from({ length: 2 * NMO + 1 }, () => new Float64Array(n));
    this.wmr = W(); this.wmi = W(); this.wpr = W(); this.wpi = W();
    this.tau = new Float64Array(n); this.dq = new Float64Array(n); this.gq = new Float64Array(n);
    this.sr_ = Array.from({ length: 4 }, () => new Float64Array(n)); this.si_ = Array.from({ length: 4 }, () => new Float64Array(n));
    this.ur = new Float64Array(n); this.ui = new Float64Array(n); this.vr = new Float64Array(n); this.vi = new Float64Array(n);
    this.Jb = Array.from({ length: 4 }, () => new Float64Array(NMO + 3));
    this.Ndata = 2 * n * this.Q;
    this.N = this.Ndata + 2 * J;
    this.npar = NP3 + 2 * J;
    let e = 0; for (const d of ds) for (let q = 0; q < d.n; q++) e += d.re[q] ** 2 + d.im[q] ** 2;
    this.energie = e;
    const nu = 1e-4 * e / this.Ndata;
    this.wd = Math.sqrt(nu) / 3e-4; this.wg = Math.sqrt(nu) / 0.2;
    this.amp = Array.from({ length: this.Q }, () => new Float64Array(8));
    this.iw = new Int32Array(n); this.uw = new Float64Array(n);
    const t0 = this.t[0], span = this.t[n - 1] - t0 || 1;
    for (let q = 0; q < n; q++) {
      const s = ((this.t[q] - t0) / span) * (J - 1);
      const j = Math.min(J - 2, Math.max(0, Math.floor(s)));
      this.iw[q] = J > 1 ? j : 0; this.uw[q] = J > 1 ? s - j : 0;
    }
    const b = bornes3(J); this.LB = b.LB; this.UB = b.UB;
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
    // coefficients (réutilisés) : outer 7 raies, centre 5×5
    this.cor = new Float64Array(2 * NMO + 1); this.coi = new Float64Array(2 * NMO + 1);
    this.ccr = new Float64Array((2 * NMC + 1) ** 2); this.cci = new Float64Array((2 * NMC + 1) ** 2);
    this.inr = new Float64Array(n); this.ini = new Float64Array(n); this.inr2 = new Float64Array(n); this.ini2 = new Float64Array(n);
  }

  calculerTau(p) {
    const { n, t, tau, dq, gq, iw, uw, J } = this;
    let moy = 0, mg = 0;
    for (let q = 0; q < n; q++) {
      const j1 = Math.min(J - 1, iw[q] + 1);
      const a = p[NP3 + iw[q]], b = p[NP3 + j1];
      dq[q] = a + (b - a) * uw[q];
      moy += dq[q];
      const ga = p[NP3 + J + iw[q]], gb = p[NP3 + J + j1];
      gq[q] = ga + (gb - ga) * uw[q];
      mg += gq[q];
    }
    moy /= n; mg /= n;
    for (let q = 0; q < n; q++) gq[q] = 1 + gq[q] - mg;
    let acc = 0;
    tau[0] = t[0];
    for (let q = 1; q < n; q++) { acc += 0.5 * ((dq[q] - moy) + (dq[q - 1] - moy)) * (t[q] - t[q - 1]); tau[q] = t[q] + acc; }
  }

  // Phaseurs des deux tons de modulation : w−[n] = e^{i n 2π Δ− τ}, w+[n] = e^{i n 2π Δ+ τ}.
  phaseurs(p) {
    const { n, tau, wmr, wmi, wpr, wpi } = this;
    const Dm = p[1], Dp = p[2];
    for (let q = 0; q < n; q++) {
      for (const [Dx, wr, wi] of [[Dm, wmr, wmi], [Dp, wpr, wpi]]) {
        const ang = TWO_PI * Dx * tau[q], c1 = Math.cos(ang), s1 = Math.sin(ang);
        wr[NMO][q] = 1; wi[NMO][q] = 0;
        for (let j = 1; j <= NMO; j++) {
          const pr = wr[NMO + j - 1][q], pi = wi[NMO + j - 1][q];
          const nr = pr * c1 - pi * s1, ni = pr * s1 + pi * c1;
          wr[NMO + j][q] = nr; wi[NMO + j][q] = ni; wr[NMO - j][q] = nr; wi[NMO - j][q] = -ni;
        }
      }
    }
  }

  // Coefficient d'une raie (n, n') de l'anche r (0 basse, 1 centrale, 2 haute) au partiel k ; remplit cor/coi (extérieures) ou ccr/cci (centrale).
  // Les facteurs du filtre (droop) dépendent de la fréquence de la raie.
  coefsExt(Jv, m, psi, th, delta, Dx, M, sr) {
    const { cor, coi } = this;
    const cp = Math.cos(psi), sp = Math.sin(psi);
    for (let nn = -NMO; nn <= NMO; nn++) {
      const j0 = Jn(Jv, nn), jm = Jn(Jv, nn - 1), jp = Jn(Jv, nn + 1);
      const ar = j0 + 0.5 * m * cp * (jm + jp), ai = 0.5 * m * sp * (jm - jp);
      const ang = nn * th, ce = Math.cos(ang), se = Math.sin(ang);
      const g = droop(delta + nn * Dx, M, sr);
      cor[nn + NMO] = g * (ar * ce - ai * se); coi[nn + NMO] = g * (ar * se + ai * ce);
    }
  }
  coefsCentre(Ja, Jb, m, psi, thm, thp, delta, Dm, Dp, M, sr) {
    const { ccr, cci } = this;
    const cp = Math.cos(psi), sp = Math.sin(psi), W = 2 * NMC + 1;
    for (let a = -NMC; a <= NMC; a++) {
      for (let b = -NMC; b <= NMC; b++) {
        // PM : J_a(A) J_b(B) ; AM : (m/2)[e^{iψ}(J_{a−1}J_b + J_a J_{b−1}) + e^{−iψ}(J_{a+1}J_b + J_a J_{b+1})]
        const pm = Jn(Ja, a) * Jn(Jb, b);
        const s1 = Jn(Ja, a - 1) * Jn(Jb, b) + Jn(Ja, a) * Jn(Jb, b - 1), s2 = Jn(Ja, a + 1) * Jn(Jb, b) + Jn(Ja, a) * Jn(Jb, b + 1);
        const ar = pm + 0.5 * m * cp * (s1 + s2), ai = 0.5 * m * sp * (s1 - s2);
        const ang = a * thm + b * thp, ce = Math.cos(ang), se = Math.sin(ang);
        const g = droop(delta + a * Dm + b * Dp, M, sr);
        ccr[(a + NMC) * W + (b + NMC)] = g * (ar * ce - ai * se); cci[(a + NMC) * W + (b + NMC)] = g * (ar * se + ai * ce);
      }
    }
  }

  // Somme des raies de l'anche r au partiel qi : this.ur/ui (et vr/vi = Σ u · fréquence absolue de la raie si `avecV`).
  somme(p, qi, r, avecV) {
    const { ds, n, ur, ui, vr, vi } = this;
    const d = ds[qi], k = d.k, M = d.M, sr = d.sr;
    const fc = p[0], Dm = p[1], Dp = p[2], fr = r === 0 ? fc - Dm : r === 2 ? fc + Dp : fc;
    const delta = k * fr - d.mu;
    ur.fill(0); ui.fill(0);
    if (avecV) { vr.fill(0); vi.fill(0); }
    if (r !== 1) {
      const low = r === 0, Jv = this.Jb[low ? 0 : 3], th = low ? p[11] : p[12], Dx = low ? Dm : Dp, m = low ? p[7] : p[9];
      this.coefsExt(Jv, m, p[10], th, delta, Dx, M, sr);
      const wr = low ? this.wmr : this.wpr, wi = low ? this.wmi : this.wpi, { cor, coi } = this;
      for (let nn = -NMO; nn <= NMO; nn++) {
        const cr = cor[nn + NMO], ci = coi[nn + NMO], wrr = wr[nn + NMO], wii = wi[nn + NMO], fl = k * fr + nn * Dx;
        for (let q = 0; q < n; q++) {
          const a = cr * wrr[q] - ci * wii[q], b = cr * wii[q] + ci * wrr[q];
          ur[q] += a; ui[q] += b;
          if (avecV) { vr[q] += a * fl; vi[q] += b * fl; }
        }
      }
    } else {
      this.coefsCentre(this.Jb[1], this.Jb[2], p[8], p[10], p[11], p[12], delta, Dm, Dp, M, sr);
      const W = 2 * NMC + 1, { ccr, cci, inr, ini, wmr, wmi, wpr, wpi } = this;
      for (let a = -NMC; a <= NMC; a++) {
        // s_a(q) = Σ_b C[a][b] w+[b](q)
        inr.fill(0); ini.fill(0);
        let vr_ = null;
        if (avecV) { this.inr2.fill(0); this.ini2.fill(0); vr_ = true; }
        for (let b = -NMC; b <= NMC; b++) {
          const cr = ccr[(a + NMC) * W + (b + NMC)], ci = cci[(a + NMC) * W + (b + NMC)], wrr = wpr[b + NMO], wii = wpi[b + NMO], fb = b * Dp;
          for (let q = 0; q < n; q++) {
            const x = cr * wrr[q] - ci * wii[q], y = cr * wii[q] + ci * wrr[q];
            inr[q] += x; ini[q] += y;
            if (vr_) { this.inr2[q] += x * fb; this.ini2[q] += y * fb; }
          }
        }
        const mr = wmr[a + NMO], mi = wmi[a + NMO], fa = k * fr + a * Dm;
        for (let q = 0; q < n; q++) {
          const x = inr[q] * mr[q] - ini[q] * mi[q], y = inr[q] * mi[q] + ini[q] * mr[q];
          ur[q] += x; ui[q] += y;
          if (avecV) {
            const x2 = this.inr2[q] * mr[q] - this.ini2[q] * mi[q], y2 = this.inr2[q] * mi[q] + this.ini2[q] * mr[q];
            vr[q] += x * fa + x2; vi[q] += y * fa + y2;
          }
        }
      }
    }
  }

  colonnes(p, qi) {
    const { ds, n, tau, gq, t } = this;
    const d = ds[qi], k = d.k;
    besselJ(k * p[3], NMO, this.Jb[0]); besselJ(k * p[4], NMC + 1, this.Jb[1]); besselJ(k * p[5], NMC + 1, this.Jb[2]); besselJ(k * p[6], NMO, this.Jb[3]);
    const fc = p[0];
    for (let r = 0; r < 3; r++) {
      const fr = r === 0 ? fc - p[1] : r === 2 ? fc + p[2] : fc;
      this.somme(p, qi, r, false);
      const del = k * fr - d.mu, sRe = this.sr_[r], sIm = this.si_[r];
      for (let q = 0; q < n; q++) {
        const ph = TWO_PI * (del * tau[q] + d.mu * (tau[q] - t[q])), c = Math.cos(ph), s = Math.sin(ph), gg = gq[q];
        sRe[q] = gg * (this.ur[q] * c - this.ui[q] * s); sIm[q] = gg * (this.ur[q] * s + this.ui[q] * c);
      }
    }
    if (this.libre) {
      const del = k * p[13] - d.mu, sRe = this.sr_[3], sIm = this.si_[3];
      for (let q = 0; q < n; q++) {
        const ph = TWO_PI * (del * tau[q] + d.mu * (tau[q] - t[q])), gg = gq[q];
        sRe[q] = gg * Math.cos(ph); sIm[q] = gg * Math.sin(ph);
      }
    }
  }

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

  residu(p, res, garder = false) {
    const { ds, Q, n, nc } = this;
    this.calculerTau(p);
    this.phaseurs(p);
    let ssr = 0, o = 0, prior = 0;
    for (let j = 0; j < this.J; j++) { const a = this.wd * p[NP3 + j], b = this.wg * p[NP3 + this.J + j]; prior += a * a + b * b; }
    for (let qi = 0; qi < Q; qi++) {
      this.colonnes(p, qi);
      const N = this.normales(qi), { xr, xi } = N.A, yr = ds[qi].re, yi = ds[qi].im;
      if (garder) {
        const A = this.amp[qi]; for (let a = 0; a < 4; a++) { A[2 * a] = a < nc ? xr[a] : 0; A[2 * a + 1] = a < nc ? xi[a] : 0; }
        if (!this.ptsS) this.ptsS = Array.from({ length: Q }, () => ({}));
        const P = this.ptsS[qi];
        P.s = Array.from({ length: nc }, (_, a) => ({ r: Float64Array.from(this.sr_[a]), i: Float64Array.from(this.si_[a]) }));
        P.Gr = N.Gr; P.Gi = N.Gi;
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
    if (res) { for (let j = 0; j < this.J; j++) { res[o++] = this.wd * p[NP3 + j]; res[o++] = this.wg * p[NP3 + this.J + j]; } }
    return ssr + prior;
  }

  // Jacobienne analytique du warp et du niveau (dérivée de variable projection, comme Modele.jacobienneWarp).
  jacobienneWarp(p, cols) {
    const { ds, Q, n, J, tau, gq, t, nc } = this;
    const Nd = this.Ndata;
    for (let j = 0; j < J; j++) { cols[NP3 + j].fill(0); cols[NP3 + J + j].fill(0); }
    this.phaseurs(p);
    let o = 0;
    const Er = new Float64Array(n), Ei = new Float64Array(n), Mr = new Float64Array(n), Mi = new Float64Array(n);
    const zr = new Float64Array(n), zi = new Float64Array(n);
    for (let qi = 0; qi < Q; qi++) {
      const d = ds[qi], k = d.k, P = this.ptsS[qi], A = this.amp[qi];
      besselJ(k * p[3], NMO, this.Jb[0]); besselJ(k * p[4], NMC + 1, this.Jb[1]); besselJ(k * p[5], NMC + 1, this.Jb[2]); besselJ(k * p[6], NMO, this.Jb[3]);
      Er.fill(0); Ei.fill(0); Mr.fill(0); Mi.fill(0);
      for (let r = 0; r < nc; r++) {
        const Ar = A[2 * r], Ai = A[2 * r + 1];
        if (r < 3) {
          const fr = r === 0 ? p[0] - p[1] : r === 2 ? p[0] + p[2] : p[0], del = k * fr - d.mu;
          this.somme(p, qi, r, true);
          const { ur, ui, vr, vi } = this;
          for (let q = 0; q < n; q++) {
            const ph = TWO_PI * (del * tau[q] + d.mu * (tau[q] - t[q])), c = Math.cos(ph), s = Math.sin(ph), g = gq[q];
            const dr_ = -TWO_PI * g * (vr[q] * s + vi[q] * c), di_ = TWO_PI * g * (vr[q] * c - vi[q] * s);
            Er[q] += Ar * dr_ - Ai * di_; Ei[q] += Ar * di_ + Ai * dr_;
            const sr_ = (ur[q] * c - ui[q] * s), si_ = (ur[q] * s + ui[q] * c);
            Mr[q] += Ar * sr_ - Ai * si_; Mi[q] += Ar * si_ + Ai * sr_;
          }
        } else {
          const s3r = P.s[3].r, s3i = P.s[3].i, w3 = TWO_PI * k * p[13];
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
        const cr_ = new Float64Array(nc), ci_ = new Float64Array(nc);
        for (let a = 0; a < nc; a++) {
          const sa = P.s[a]; let x = 0, y = 0;
          for (let q = 0; q < n; q++) { x += sa.r[q] * zr[q] + sa.i[q] * zi[q]; y += sa.r[q] * zi[q] - sa.i[q] * zr[q]; }
          cr_[a] = x; ci_[a] = y;
        }
        const { xr, xi } = resoudreHerm(P.Gr, P.Gi, cr_, ci_, nc);
        const col = cols[NP3 + jj];
        for (let q = 0; q < n; q++) {
          let pr = 0, pi = 0;
          for (let a = 0; a < nc; a++) { pr += xr[a] * P.s[a].r[q] - xi[a] * P.s[a].i[q]; pi += xr[a] * P.s[a].i[q] + xi[a] * P.s[a].r[q]; }
          col[o + 2 * q] = -(zr[q] - pr); col[o + 2 * q + 1] = -(zi[q] - pi);
        }
      }
      o += 2 * n;
    }
    for (let j = 0; j < J; j++) { cols[NP3 + j][Nd + 2 * j] = this.wd; cols[NP3 + J + j][Nd + 2 * j + 1] = this.wg; }
  }
}

// ---- lecture --------------------------------------------------------------------------------------------------------------
// Rend { ok, f: [fL, fC, fH], Om: [Δ−, Δ+], b, m, r, llr, K, Ku, T, derive, agit, plancherDb, sigmaC, ... } ou { ok: false, raison }.
export function lireTrio(x, i0, i1, sr, fc, opts = {}) {
  const g = lireTrioGen(x, i0, i1, sr, fc, opts);
  let r;
  while (!(r = g.next()).done);
  return r.value;
}

export function* lireTrioGen(x, i0, i1, sr, fc, opts = {}) {
  const t0 = typeof performance !== 'undefined' ? performance.now() : 0;
  const { plageC = 110, prior = null, chaud = false, pInit = null, libreInit = null, dt = 0, Kmax = 4, iter = 15, iterEtape = 5, tol = 1e-4, nTriplets = 3, noeudsS = 0.5, omegaMax = 60, libre = true } = opts;
  const T = (i1 - i0) / sr;
  if (!(T > 0.3)) return { ok: false, raison: 'court' };
  const fLo = fc * 2 ** (-plageC / 1200), fHi = fc * 2 ** (plageC / 1200);
  const K = Math.max(1, Math.min(Kmax, Math.floor(0.42 * sr / fHi)));
  const ks = Array.from({ length: K }, (_, i) => i + 1);
  const J = Math.max(2, Math.min(9, Math.ceil(T / noeudsS) + 1));
  const fm = (fLo + fHi) / 2, D1 = Math.min(sr / 2, Math.max(60, 1.2 * K * (fHi - fLo)));
  const ds1 = ks.map((k) => demodPartiel(x, i0, i1, k, k * fm, sr, D1));
  if (ds1[0].n < 12) return { ok: false, raison: 'court' };
  const sp = spectreHarmonique(ds1, fLo, fHi);
  const pk = pics(sp, 10, 'G');
  if (!pk.length) return { ok: false, raison: 'sans pic' };
  for (const q of pics(sp, 4, 'S')) if (!pk.some((p) => Math.abs(p.f - q.f) < 1.2 / (K * T))) pk.push({ f: q.f, h: 2e-5 * pk[0].h });
  yield;
  const res1 = 1 / (K * T);
  const distincts = [];
  for (const q of pk) if (distincts.every((d) => Math.abs(d.f - q.f) > 1.2 * res1) && q.h > 1e-5 * pk[0].h) distincts.push(q);
  // triplets de raies : le lu par le moteur d'abord, puis les combinaisons des raies les plus hautes
  const trip = [];
  let chaudDepart = null;
  const ajoute = (a, b, c) => { const [u, v, w] = [a, b, c].sort((p, q) => p - q); if (v - u > 1.2 * res1 && w - v > 1.2 * res1 && v - u < omegaMax && w - v < omegaMax && !trip.some((t) => Math.abs(t[0] - u) < 0.5 * res1 && Math.abs(t[1] - v) < 0.5 * res1 && Math.abs(t[2] - w) < 0.5 * res1)) trip.push([u, v, w]); };
  if (prior && prior.length === 3) ajoute(prior[0], prior[1], prior[2]);
  const top = distincts.slice(0, 5);
  const comb = [];
  for (let a = 0; a < top.length; a++) for (let b = a + 1; b < top.length; b++) for (let c = b + 1; c < top.length; c++) comb.push({ f: [top[a].f, top[b].f, top[c].f], sc: Math.log(top[a].h) + Math.log(top[b].h) + Math.log(top[c].h) });
  comb.sort((u, v) => v.sc - u.sc);
  for (const c of comb) ajoute(...c.f);
  // ajustement chaud : le triplet de pics le plus proche de la lecture connue passe devant (la hauteur a pu dériver depuis l'ajustement d'où l'on part)
  if (chaud && pInit && prior && prior.length === 3 && comb.length) {
    const pr = [...prior].sort((a, b) => a - b), mD = Math.min(pr[1] - pr[0], pr[2] - pr[1]);
    let meilleur = null;
    for (const c of comb) { const f = [...c.f].sort((a, b) => a - b), dist = Math.abs(f[0] - pr[0]) + Math.abs(f[1] - pr[1]) + Math.abs(f[2] - pr[2]); if (!meilleur || dist < meilleur.dist) meilleur = { f, dist }; }
    if (meilleur && meilleur.dist < 1.2 * mD + res1) chaudDepart = meilleur.f;
  }
  if (!trip.length) return { ok: false, raison: 'moins de trois raies' };
  const Dm = (spread) => Math.min(sr / 2, Math.max(opts.D ?? 0, 2.4 * ((K + 4) * spread / 2 + 3) + 10));
  const cache = new Map();
  const donnees = (lo, hi) => {
    const centre = (lo + hi) / 2, D = Dm(hi - lo), clef = `${centre.toFixed(2)}|${D}`;
    if (!cache.has(clef)) cache.set(clef, ks.map((k) => demodPartiel(x, i0, i1, k, k * centre, sr, D)));
    return cache.get(clef);
  };
  const steps = pasFD3(T, J);
  const toutes = (mod, avecF3) => Array.from({ length: mod.npar }, (_, i) => i).filter((i) => avecF3 || i !== 13);
  const sols = [];
  let rMin = Infinity;
  function* ajusterDepart(tr, force, init) {
    const ds = donnees(tr[0], tr[2]);
    yield;
    const best = { S: Infinity, p: null };
    const m2 = new Modele3(ds.slice(0, Math.min(2, K)), J);
    if (init) { best.p = Float64Array.from(init); }
    else {
      const th0 = [0, 1.5708, 3.1416, 4.7124];
      for (const thm of th0) for (const thp of th0) {
        const p = new Float64Array(NP3 + 2 * J);
        p[0] = tr[1]; p[1] = tr[1] - tr[0]; p[2] = tr[2] - tr[1];
        p[3] = 0.1; p[4] = -0.1; p[5] = -0.1; p[6] = 0.1; p[7] = 0.04; p[8] = -0.04; p[9] = 0.04; p[11] = thm; p[12] = thp;
        const S = m2.residu(p);
        if (S < best.S) { best.S = S; best.p = p; }
      }
    }
    let pp = best.p, elague = false;
    const etapes = [1, 2, 3, 4, 6].filter((q) => q < K).concat([K]);      // aussi à chaud (voir nls-bessel.js)
    for (const q of etapes) {
      const mod = new Modele3(ds.slice(0, q), J);
      pp = (yield* ajusterLMg(mod, pp, toutes(mod, false), steps, { iter: q === K ? iter : iterEtape, tol })).p;
      if (q === Math.min(2, K)) {
        mod.residu(pp);
        const rr = mod.ssrData / Math.max(mod.energie, 1e-300);
        if (!force && rr > 3 * rMin + 0.05) { elague = true; break; }
        rMin = Math.min(rMin, rr);
      }
    }
    if (elague) return null;
    const mod = new Modele3(ds, J);
    return { p: pp, ssr: mod.residu(pp), ssrData: mod.ssrData, mod, triplet: tr };
  }
  if (chaud && pInit && prior && prior.length === 3) {
    const init = Float64Array.from({ length: NP3 + 2 * J }, (_, i) => (i < NP3 ? pInit[i] ?? 0 : 0));
    const [u, v, w] = chaudDepart ?? [...prior].sort((a, b) => a - b);
    init[0] = v; init[1] = v - u; init[2] = w - v;
    init[11] += TWO_PI * init[1] * dt; init[12] += TWO_PI * init[2] * dt;      // θ−, θ+ : phases des battements au CENTRE de la fenêtre, qui a bougé de dt secondes
    const r = yield* ajusterDepart([u, v, w], true, init);
    if (r) sols.push(r);
  } else {
    for (const tr of trip.slice(0, nTriplets)) {
      const r = yield* ajusterDepart(tr, false, null);
      if (r) sols.push(r);
    }
  }
  if (!sols.length) return { ok: false, raison: 'sans départ' };
  // comparaison sur les MÊMES données
  const lo = Math.min(...sols.map((q) => q.p[0] - q.p[1])), hi = Math.max(...sols.map((q) => q.p[0] + q.p[2]));
  const centreC = (lo + hi) / 2, DC = Dm(hi - lo);
  const commun = ks.map((k) => demodPartiel(x, i0, i1, k, k * centreC, sr, DC));
  for (const q of sols) {
    const mod = new Modele3(commun, J);
    const r = yield* ajusterLMg(mod, q.p, toutes(mod, false), steps, { iter: 4 });
    q.p = r.p; q.mod = mod; q.ssr = mod.residu(r.p); q.ssrData = mod.ssrData; q.libre = false;
  }
  sols.sort((u, v) => u.ssr - v.ssr);
  if (!chaud) {      // les meilleures hypothèses menées jusqu'au bout sur les mêmes données (voir nls-bessel.js)
    for (const q of sols.slice(0, 3)) {
      const r = yield* ajusterLMg(q.mod, q.p, toutes(q.mod, false), steps, { iter: 10, tol: 1e-5 });
      q.p = r.p; q.ssr = q.mod.residu(r.p); q.ssrData = q.mod.ssrData;
    }
    sols.sort((u, v) => u.ssr - v.ssr);
  }
  // raie étrangère (une fuite d'un autre registre) : sur la meilleure hypothèse seulement
  if (libre) {
    const q = sols[0];
    const dofDe = (m) => Math.max(1, m.Ndata - m.npar - 4 * m.Q);
    const resB = new Float64Array(q.mod.N);
    q.mod.residu(q.p, resB);
    const dsR = commun.map((d, qi) => {
      const o = commun.slice(0, qi).reduce((a, e) => a + 2 * e.n, 0), re = new Float64Array(d.n), im = new Float64Array(d.n);
      for (let i = 0; i < d.n; i++) { re[i] = resB[o + 2 * i]; im[i] = resB[o + 2 * i + 1]; }
      return { ...d, re, im };
    });
    const dem = 0.42 * DC / K;
    const spR = spectreHarmonique(dsR, centreC - dem, centreC + dem);
    const garde = 1.5 * res1, fs = [q.p[0] - q.p[1], q.p[0], q.p[0] + q.p[2]];
    // jamais à la place d'une raie latérale (f_r ± nΔ−, f_r ± nΔ+) : libre, la raie étrangère se substituerait à une vraie anche (voir nls-bessel.js)
    const lateral = (f) => fs.some((fr) => [-2, -1, 1, 2].some((n) => Math.abs(f - (fr + n * q.p[1])) <= garde || Math.abs(f - (fr + n * q.p[2])) <= garde));
    const cand = pics(spR, 6, 'G').find((c) => fs.every((f) => Math.abs(c.f - f) > garde) && !lateral(c.f));
    yield;
    if (cand) {
      const modL = new Modele3(commun, J, { libre: true });
      const p0 = Float64Array.from(q.p); p0[13] = cand.f;
      const r = yield* ajusterLMg(modL, p0, toutes(modL, true), steps, { iter: 10 });
      modL.residu(r.p);
      const s2 = q.ssrData / dofDe(q.mod);
      const ok3 = [0, 1, 2].every((i) => Math.abs((i === 0 ? r.p[0] - r.p[1] : i === 1 ? r.p[0] : r.p[0] + r.p[2]) - fs[i]) < 0.25 * Math.min(q.p[1], q.p[2]) + res1);
      if ((q.ssrData - modL.ssrData) / s2 >= NLS_LLR_SUR && ok3) { q.p = r.p; q.mod = modL; q.ssr = modL.residu(r.p); q.ssrData = modL.ssrData; q.libre = true; }
    }
  }
  const best = sols[0], pb = best.p, mod = best.mod;
  const dof = Math.max(1, mod.Ndata - mod.npar - 4 * mod.Q);
  const s2 = best.ssrData / dof;
  const rival = sols.slice(1).find((s) => Math.abs(s.p[0] - pb[0]) > 0.4 * Math.min(pb[1], pb[2]) || Math.abs(s.p[1] - pb[1]) > 0.3 * pb[1] || Math.abs(s.p[2] - pb[2]) > 0.3 * pb[2]);
  // rôle des raies : voir nls-bessel.js (une anche et la raie étrangère échangent leurs rôles)
  let llrAffectation = Infinity;
  if (best.libre && !chaud) {
    const fEtr = pb[13], fs3 = [pb[0] - pb[1], pb[0], pb[0] + pb[2]];
    for (let r = 0; r < 3; r++) {
      const reste = fs3.filter((_, i) => i !== r), tri = [...reste, fEtr].sort((u, v) => u - v);
      if (tri[1] - tri[0] < 1.2 * res1 || tri[2] - tri[1] < 1.2 * res1) continue;
      const p0 = Float64Array.from(pb); p0[0] = tri[1]; p0[1] = tri[1] - tri[0]; p0[2] = tri[2] - tri[1]; p0[13] = fs3[r];
      const modA = new Modele3(commun, J, { libre: true });
      const rr = yield* ajusterLMg(modA, p0, toutes(modA, true), steps, { iter: 12, tol: 1e-5 });
      modA.residu(rr.p);
      llrAffectation = Math.min(llrAffectation, (modA.ssrData - best.ssrData) / (best.ssrData / dof));
    }
  }
  const cov = covariance3(mod, pb, steps, s2);
  const fL = pb[0] - pb[1], fC = pb[0], fH = pb[0] + pb[2];
  const sigC = [Math.sqrt(Math.max(0, cov.v(0, 0) + cov.v(1, 1) - 2 * cov.v(0, 1))) * C_CENTS / fL, Math.sqrt(Math.max(0, cov.v(0, 0))) * C_CENTS / fC, Math.sqrt(Math.max(0, cov.v(0, 0) + cov.v(2, 2) + 2 * cov.v(0, 2))) * C_CENTS / fH];
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
    const A = mod.amp[qi];
    plancher.push(planchersDb(d, res, o, [Math.max(Math.hypot(A[0], A[1]), Math.hypot(A[2], A[3]), Math.hypot(A[4], A[5])), 0, 0, 0]));
    o += 2 * d.n;
  }
  const Ku = snr.filter((v) => v >= 20).length;
  const J_ = mod.J, dw = Array.from({ length: J_ }, (_, j) => pb[NP3 + j]);
  const moy = dw.reduce((a, b) => a + b, 0) / J_, tj = dw.map((_, j) => (j / (J_ - 1) - 0.5) * T);
  const sxx = tj.reduce((a, b) => a + b * b, 0), pente = tj.reduce((a, b, j) => a + b * (dw[j] - moy), 0) / sxx;
  const agit = Math.sqrt(dw.reduce((a, v, j) => a + (v - moy - pente * tj[j]) ** 2, 0) / J_) * C_CENTS;
  // niveaux des anches au partiel 1 (dB, relatifs à la plus forte) : une anche à plus de 25 dB sous la plus forte n'est pas lisible
  const A1 = mod.amp[0], na = [Math.hypot(A1[0], A1[1]), Math.hypot(A1[2], A1[3]), Math.hypot(A1[4], A1[5])];
  const nmax = Math.max(...na);
  return {
    ok: true, f: [fL, fC, fH], Om: [pb[1], pb[2]], sigmaC: sigC, b: [pb[3], pb[4], pb[5], pb[6]], m: [pb[7], pb[8], pb[9]], psi: pb[10], th: [pb[11], pb[12]],
    derive: pente * C_CENTS, agit, warpC: dw.map((v) => (v - moy) * C_CENTS), r: best.ssrData / Math.max(1e-300, energie), ssr: best.ssrData, dof, s2, K, Ku, T, J: J_, snr, plancherDb: plancher,
    niveauxDb: na.map((v) => 20 * Math.log10(Math.max(v, 1e-300) / nmax)),
    llr: rival ? (rival.ssrData - best.ssrData) / s2 : Infinity, llrAffectation,
    rival: rival ? { f: [rival.p[0] - rival.p[1], rival.p[0], rival.p[0] + rival.p[2]], ssr: rival.ssr } : null,
    libre: best.libre ? { f: pb[13] } : null, sol: pb, mod, ms: typeof performance !== 'undefined' ? performance.now() - t0 : 0,
  };
}

function covariance3(mod, p, steps, s2) {
  const N = mod.N, P = mod.npar;
  const r0 = new Float64Array(N), r1 = new Float64Array(N);
  mod.residu(p, r0);
  const Jc = [];
  for (let a = 0; a < P; a++) {
    if (a === 13 && !mod.libre) { Jc.push(new Float64Array(N)); continue; }
    const q = Float64Array.from(p); q[a] += steps[a];
    mod.residu(q, r1);
    Jc.push(Float64Array.from(r1, (v, i) => (v - r0[i]) / steps[a]));
  }
  const A = new Float64Array(P * P);
  let tr = 0;
  for (let a = 0; a < P; a++) { for (let b = a; b < P; b++) { let s = 0; for (let i = 0; i < N; i++) s += Jc[a][i] * Jc[b][i]; A[a * P + b] = s; A[b * P + a] = s; } tr += A[a * P + a]; }
  for (let a = 0; a < P; a++) A[a * P + a] = A[a * P + a] * (1 + 1e-9) + 1e-9 * tr / P + (a === 13 && !mod.libre ? 1 : 0);
  // inverse colonne par colonne pour les trois premiers paramètres
  const inv = [];
  for (let a = 0; a < 3; a++) { const e = new Float64Array(P); e[a] = 1; inv.push(resoudre(A.slice(), e, P)); }
  return { v: (a, b) => (inv[a] ? s2 * inv[a][b] : Infinity) };
}
