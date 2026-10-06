// Anche « confondue avec l'octave » (le 8' d'un 16'+8' que la fenêtre ne
// sépare pas encore du partiel 2 du 16') : une estimation honnête de sa
// hauteur, avec sa marge (demande d'Ewen, 06/10/2026 : « on peut quand même
// avoir la valeur de cette note-là, en termes de justesse »).
//
// Le 8' est à f8 = 2 f16 + δ. Le 16' est mesuré à part, précisément, sur un
// partiel impair (avoidEven). Trois estimations (la 3e plus bas, cf.
// estimeRaie) :
//
// 1) Par l'octave : f8 ≈ 2 f16, erreur exactement δ. Tant que la fenêtre ne
//    sépare pas les deux raies, |δ| reste sous la résolution : on annonce
//    ±1/T_fenêtre (Hz, ramené à la fondamentale du 8'). Mesuré sur synthèse
//    (7 800 images confondues, 8' de −10 à +6 dB, 16' au timbre riche ou
//    pauvre) : |δ|·T ne dépasse jamais 0,82 ; un 8' plus de 12 dB sous le
//    16' sur TOUS ses partiels n'est pas couvert (il faudrait 4/T).
//    Pourquoi pas la raie commune mesurée ? Sa fréquence n'est PAS entre
//    2 f16 et f8 : la phase d'une somme de deux sinusoïdes proches déborde
//    (biais jusqu'à δ ρ/(1 − ρ), ρ = rapport des amplitudes) ; mesuré : 1,45 ¢
//    d'erreur pour un 8' à 1 ¢ de l'octave. 2 f16 a une erreur bornée par δ.
//
// 2) Par le battement : sur chaque partiel k du 8', la bande contient deux
//    raies, celle du 8' (k f8) et celle, CONNUE, du 16' (2k f16). On
//    démodule la bande par la phase du 16' lue sur son partiel impair m
//    (multipliée par 2k/m : les partiels d'une anche sont verrouillés en
//    phase), qui retire aussi la dérive du soufflet. Il reste
//        y_k(t) = g(t) (C_k + B_k e^{i 2π k δ t}) :
//    un cercle parcouru à la vitesse k δ autour de la raie du 16'. Le SENS
//    de rotation donne le signe de δ, sa vitesse sa valeur, et cela sur
//    toute la note depuis l'attaque (jusqu'à CONF_MAX_S), pas seulement la
//    fenêtre glissante. Ajustement par moindres carrés (C_k, B_k linéaires,
//    δ commun à tous les partiels, balayé), g(t) = enveloppe du 16' (le
//    soufflet module les deux anches ensemble ; l'attaque pèse peu).
//    Marge (Hz) = √(A² + B² + S²) :
//      A = CONF_SYST / (k_max T) : erreur systématique (attaque, modulations
//          qui ne sont pas communes), une fraction de la résolution de
//          Fourier du plus haut partiel sur la durée T ;
//      B = plus grand écart entre la note entière, ses deux moitiés et la
//          seule fenêtre de la mesure normale : un δ qui bouge (soufflet,
//          anche qui glisse) ;
//      S = intervalle statistique à 95 % (courbure du critère).
//    Mesuré sur synthèse (16'+8' de Ré#2, Fa2, La#2, La3 ; 8' à ±0,3, ±1,
//    +3 ¢ de l'octave ; −10 à +6 dB ; dérive commune et différentielle,
//    soufflet en hauteur et en volume, bruit à 35 dB ; notes de 1,5 à 6 s) :
//    erreur au 95e centile 0,08 ¢ dès 1 s, 0,05 ¢ vers 3 s ; signe juste
//    dans 99,6 à 100 % des images, à tous les rapports d'amplitude.
//
// 3) Par la raie commune, quand le 8' y domine : cf. estimeRaie.
//
// On garde l'estimation de plus petite marge. Le chiffre mesuré de la voix
// (fMeas, dCents, dTargetCents : la raie commune) ne change pas ; tout est
// dans des champs à part (cf. estimerConfondues).

import { FFT } from './fft.js';
import { centsBetween } from '../music.js';

export const CONF_BANDE_HZ = 6;   // demi-bande gardée autour de la raie du 16' (k δ y tient)
export const CONF_MIN_S = 1;      // durée minimale de son pour le battement
export const CONF_MAX_S = 8;      // au-delà, plus rien à gagner, et δ peut avoir bougé
export const CONF_SYST = 0.2;     // part de la résolution de Fourier comptée en systématique
const CONF_KHI = 1.92;            // ΔJ à 95 % pour un paramètre (bruit complexe)
const CONF_DEBUT = 2;             // échantillons décimés ignorés (filtre qui se remplit)

// Les `N` derniers échantillons de la bande d'un traqueur (ordre chronologique).
function derniers(t, N) {
  const R = t.ringRe.length;
  const re = new Float64Array(N), im = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    const j = (((t.count - N + i) % R) + R) % R;
    re[i] = t.ringRe[j];
    im[i] = t.ringIm[j];
  }
  return { re, im };
}

// Passe-bas idéal ±L Hz (masque de FFT), en place.
function passeBas(re, im, srd, L) {
  const N = re.length;
  let M = 1;
  while (M < N) M <<= 1;
  const fft = FFT.get(M);
  const r = new Float64Array(M), j = new Float64Array(M);
  r.set(re); j.set(im);
  fft.transform(r, j);
  const h = Math.floor((L * M) / srd);
  for (let b = 0; b < M; b++) {
    if (Math.min(b, M - b) > h) { r[b] = 0; j[b] = 0; }
  }
  // FFT inverse par conjugaison : x = conj(FFT(conj X)) / M.
  for (let b = 0; b < M; b++) j[b] = -j[b];
  fft.transform(r, j);
  for (let n = 0; n < N; n++) { re[n] = r[n] / M; im[n] = -j[n] / M; }
}

// Moindres carrés de y ≈ g (c1 + c2 e^{iωt}) sur [i0, i1) : résidu.
function residu(b, w, i0, i1, dt, t0) {
  const { g, yr, yi } = b;
  let Y2 = 0, G11 = 0, r1r = 0, r1i = 0, G12r = 0, G12i = 0, r2r = 0, r2i = 0;
  // e^{iωt} par récurrence (t uniforme).
  const sr = Math.sin(w * dt), cr = Math.cos(w * dt);
  let c = Math.cos(w * (t0 + i0 * dt)), s = Math.sin(w * (t0 + i0 * dt));
  for (let i = i0; i < i1; i++) {
    const gi = g[i], g2 = gi * gi, a = yr[i], q = yi[i];
    Y2 += a * a + q * q;
    G11 += g2;
    r1r += gi * a; r1i += gi * q;
    G12r += g2 * c; G12i += g2 * s;
    r2r += gi * (a * c + q * s); r2i += gi * (q * c - a * s);
    const nc = c * cr - s * sr;
    s = s * cr + c * sr;
    c = nc;
  }
  if (!(G11 > 0)) return 0;
  const det = G11 * G11 - (G12r * G12r + G12i * G12i);
  if (det <= 1e-9 * G11 * G11) return Math.max(0, Y2 - (r1r * r1r + r1i * r1i) / G11);
  const x = r1r * (G12r * r2r - G12i * r2i) + r1i * (G12r * r2i + G12i * r2r);
  return Math.max(0, Y2 - (G11 * (r1r * r1r + r1i * r1i + r2r * r2r + r2i * r2i) - 2 * x) / det);
}

// Cercle des points y/g (Kåsa : moindres carrés de |z|² = 2 Re(c̄ z) + e) :
// centre c (la raie du 16'), rayon r (celle du 8'), quelle que soit la façon
// dont δ bouge ; R̄ = longueur moyenne des directions vues du centre (1 : un
// point, l'arc n'a pas tourné ; 0 : tour complet). Seuls les points où
// l'enveloppe dépasse la moitié de sa moyenne comptent.
function cercle(b, i0, i1) {
  const { g, yr, yi } = b;
  let n = 0, Sx = 0, Sy = 0, Sxx = 0, Syy = 0, Sxy = 0, Sz = 0, Sxz = 0, Syz = 0;
  for (let i = i0; i < i1; i++) {
    if (!(g[i] > 0.5)) continue;
    const x = yr[i] / g[i], y = yi[i] / g[i], z = x * x + y * y;
    n++; Sx += x; Sy += y; Sxx += x * x; Syy += y * y; Sxy += x * y; Sz += z; Sxz += x * z; Syz += y * z;
  }
  if (n < 6) return null;
  // [2Sxx 2Sxy Sx; 2Sxy 2Syy Sy; 2Sx 2Sy n] [a b e]ᵀ = [Sxz Syz Sz]ᵀ (Cramer).
  const M = [[2 * Sxx, 2 * Sxy, Sx], [2 * Sxy, 2 * Syy, Sy], [2 * Sx, 2 * Sy, n]], V = [Sxz, Syz, Sz];
  const det3 = (A) => A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
    + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]);
  const D0 = det3(M);
  if (!(Math.abs(D0) > 0)) return null;
  const col = (j) => det3(M.map((l, i) => l.map((v, c) => (c === j ? V[i] : v)))) / D0;
  const a = col(0), bb = col(1), e = col(2);
  const r2 = e + a * a + bb * bb;
  if (!(r2 > 0)) return null;
  let cr = 0, ci = 0, e2 = 0;
  const r = Math.sqrt(r2);
  // Points du reste, la raie du 16' (le centre) retirée, rapportés au rayon :
  // le cercle unité que le 8' parcourt à k δ tours par seconde (diagnostic de
  // la section recherche de L'anche ; aucun calcul ne les lit). Temps en
  // échantillons décimés depuis i0.
  const px = [], py = [], pi = [];
  for (let i = i0; i < i1; i++) {
    if (!(g[i] > 0.5)) continue;
    const u = yr[i] / g[i] - a, v = yi[i] / g[i] - bb, ph = Math.atan2(v, u);
    cr += Math.cos(ph); ci += Math.sin(ph);
    e2 += (Math.hypot(u, v) - r) ** 2;
    px.push(u / r); py.push(v / r); pi.push(i - i0);
  }
  // σφ : bruit de phase d'un échantillon (rad), l'écart radial rapporté au rayon.
  return { C: Math.hypot(a, bb), B: r, Rbar: Math.hypot(cr, ci) / n, sphi: Math.sqrt(e2 / n) / r,
    centre: [a / r, bb / r], points: { x: px, y: py, i: pi } };
}

// δ (Hz) qui minimise le critère sur [i0, i1), raffiné autour du meilleur
// point de la grille. Rend { d, courbure, bord } ou null.
function meilleur(bandes, grille, i0, i1, dt, t0) {
  const n = i1 - i0;
  if (n < 6) return null;
  // Variance du bruit de chaque partiel : son plus petit résidu sur la grille.
  const R = bandes.map((b) => grille.map((d) => residu(b, 2 * Math.PI * b.k * d, i0, i1, dt, t0)));
  const s2 = R.map((r) => Math.max(Math.min(...r), 1e-30) / Math.max(1, n - 2));
  const J = (d) => bandes.reduce((acc, b, j) => acc + residu(b, 2 * Math.PI * b.k * d, i0, i1, dt, t0) / s2[j], 0);
  let ib = 0, jb = Infinity;
  grille.forEach((_, i) => {
    const v = R.reduce((acc, r, j) => acc + r[i] / s2[j], 0);
    if (v < jb) { jb = v; ib = i; }
  });
  const bord = ib === 0 || ib === grille.length - 1;
  // Raffinement : grille huit fois plus fine sur ±1 pas, puis parabole.
  const pas = grille[1] - grille[0];
  const h = pas / 8;
  let d = grille[ib], jd = jb;
  for (let x = grille[ib] - pas; x <= grille[ib] + pas + 1e-15; x += h) {
    const v = J(x);
    if (v < jd) { jd = v; d = x; }
  }
  const a = J(d - h), c = J(d + h);
  const den = a - 2 * jd + c;
  if (den > 0) d += Math.max(-1, Math.min(1, (0.5 * (a - c)) / den)) * h;
  return { d, courbure: den > 0 ? den / (2 * h * h) : 0, bord };
}

// Estimation par le battement. `ref` : traqueur du 16' (partiel impair
// `mRef`, fondamentale mesurée `fRef`) ; `bandes` : [{ k, t }] traqueurs des
// partiels k de l'anche confondue ; `Tw` : fenêtre courante de sa mesure (s).
// Rend { d (Hz, f = 2 fRef + d), marge (Hz), T (s) } ou null.
export function estimeBattement({ ref, mRef, fRef, bandes, Tw }) {
  if (!ref || !(fRef > 0) || !(Tw > 0) || !bandes.length) return null;
  const srd = ref.srd, L = CONF_BANDE_HZ;
  const dmax = 1 / Tw;
  const utiles = bandes.filter((b) => b.t && b.k * dmax <= 0.9 * L);
  if (!utiles.length) return null;
  let N = Math.min(ref.count - ref.start, Math.round(CONF_MAX_S * srd), ref.ringRe.length - 4);
  for (const b of utiles) N = Math.min(N, b.t.count - b.t.start);
  N -= CONF_DEBUT;
  if (N < CONF_MIN_S * srd) return null;
  // Phase du 16' sur son partiel impair (démodulée par sa fréquence mesurée,
  // passe-bas, déroulée) et son enveloppe g(t).
  const z = derniers(ref, N);
  const o = mRef * fRef - ref.fc;
  for (let n = 0; n < N; n++) {
    const p = (-2 * Math.PI * o * n) / srd, c = Math.cos(p), s = Math.sin(p);
    const r = z.re[n] * c - z.im[n] * s;
    z.im[n] = z.re[n] * s + z.im[n] * c;
    z.re[n] = r;
  }
  passeBas(z.re, z.im, srd, L);
  const psi = new Float64Array(N), env = new Float64Array(N);
  let prec = 0, acc = 0, moy = 0;
  for (let n = 0; n < N; n++) {
    const p = Math.atan2(z.im[n], z.re[n]);
    if (n) {
      let dp = p - prec;
      dp -= 2 * Math.PI * Math.round(dp / (2 * Math.PI));
      acc += dp;
    } else acc = p;
    prec = p;
    psi[n] = acc + (2 * Math.PI * o * n) / srd;
    env[n] = Math.hypot(z.re[n], z.im[n]);
    moy += env[n];
  }
  moy /= N;
  if (!(moy > 0)) return null;
  // Décimation au rythme de la bande gardée (échantillons indépendants).
  const D = Math.max(1, Math.floor(srd / (2 * L)));
  const nd = Math.floor(N / D);
  const pos = (i) => i * D + (D >> 1);
  const g = new Float64Array(nd);
  for (let i = 0; i < nd; i++) g[i] = env[pos(i)] / moy;
  const dt = D / srd, t0 = (D >> 1) / srd;
  const data = utiles.map(({ k, t }) => {
    const y = derniers(t, N);
    const q = (2 * k) / mRef;
    const fr = q * ref.fc - t.fc;
    for (let n = 0; n < N; n++) {
      const p = -(q * psi[n] + (2 * Math.PI * fr * n) / srd), c = Math.cos(p), s = Math.sin(p);
      const r = y.re[n] * c - y.im[n] * s;
      y.im[n] = y.re[n] * s + y.im[n] * c;
      y.re[n] = r;
    }
    passeBas(y.re, y.im, srd, L);
    const yr = new Float64Array(nd), yi = new Float64Array(nd);
    for (let i = 0; i < nd; i++) { yr[i] = y.re[pos(i)]; yi[i] = y.im[pos(i)]; }
    return { k, g, yr, yi };
  });
  const T = N / srd;
  const kmax = Math.max(...data.map((b) => b.k));
  const lim = Math.min(dmax, (0.9 * L) / kmax);
  const pas = 1 / (4 * kmax * T);
  const grille = [];
  for (let x = -lim; x <= lim + 1e-12; x += pas) grille.push(x);
  if (grille.length < 3) return null;
  const tout = meilleur(data, grille, 0, nd, dt, t0);
  if (!tout || tout.bord) return null;
  const h = nd >> 1;
  const m1 = meilleur(data, grille, 0, h, dt, t0);
  const m2 = meilleur(data, grille, h, nd, dt, t0);
  // La fenêtre de la mesure normale (Tw, la dernière partie du son) : ce que
  // l'écran montre pour toute autre anche. Si δ y diffère de sa moyenne sur
  // la note (anche qui bouge avec le soufflet), l'écart entre dans la marge.
  const nw = Math.min(nd, Math.round(Tw / dt));
  const mw = nw < nd && nw * dt >= CONF_MIN_S / 2 ? meilleur(data, grille, nd - nw, nd, dt, t0) : null;
  const A = CONF_SYST / (kmax * T);
  // Un δ constant donne la même valeur sur la note et sur ses deux moitiés ;
  // s'il change (le soufflet pousse une anche plus que l'autre, δ passe par
  // zéro), l'ajustement de la note entière peut sortir de l'intervalle des
  // deux moitiés (mesuré : 16'+8' de Ré2, 8' 13 dB plus fort, 16' qui monte
  // de 0,5 ¢/s : note −1,4 ¢, moitiés +0,5 et −0,2). Les trois écarts entrent
  // dans B.
  const B = Math.max(m1 && m2 ? Math.max(Math.abs(m1.d - m2.d), Math.abs(m1.d - tout.d), Math.abs(m2.d - tout.d)) : lim,
      mw ? Math.abs(mw.d - tout.d) : 0);
  const S = tout.courbure > 0 ? Math.sqrt(CONF_KHI / tout.courbure) : lim;
  // Rapport des raies partiel par partiel (ρ_k = |C_k| / |B_k|, 16' sur 8'),
  // cf. estimeRaie : par le cercle (cercle()), qui ne suppose pas δ
  // constant. L'ajustement à δ constant le sous-estime quand δ bouge
  // (mesuré : 0,33 pour 0,55 vrais, 16' qui monte de 0,8 ¢/s).
  const rho = data.map((b) => {
    const cc = cercle(b, 0, nd);
    return cc ? { k: b.k, rho: cc.C / cc.B, Rbar: cc.Rbar, sphi: cc.sphi, dt, centre: cc.centre, points: cc.points } : null;
  }).filter(Boolean);
  // A, B, S et les trois ajustements partiels : diagnostic (section recherche
  // de L'anche), la marge n'en dépend pas autrement.
  return { d: tout.d, marge: Math.hypot(A, B, S), T, kmax, rho,
    A, B, S, d1: m1?.d ?? null, d2: m2?.d ?? null, dFenetre: mw?.d ?? null, dMax: lim };
}

// 3) Par la raie commune, quand le 8' y domine (P08 : 8' 9 à 13 dB au-dessus
//    du 16', qui monte de 2,5 ¢ sous lui pendant la note). Le battement
//    suppose δ constant ; s'il bouge, sa marge s'élargit (B) et son centre
//    peut glisser. La raie commune, elle, ne dépend pas du 16'. Sur le
//    partiel k, c'est la somme B e^{iω8 t} + C e^{iω16 t} : sa phase est
//    celle du 8' plus arg(1 + ρ e^{−i 2π k δ t}), ρ = |C|/|B| < 1. La pente de
//    phase de la fenêtre (moindres carrés sur L = 0,7 T, cf. clusterRefine)
//    est celle du 8' à un biais près, borné deux fois :
//      - par la dérivée de ce terme : k |δ| ρ/(1 − ρ) (la pente des moindres
//        carrés est une moyenne, à poids positifs, de la dérivée) ;
//      - par son amplitude : un terme borné par asin ρ a une pente de
//        moindres carrés d'au plus 3 asin(ρ) / L (rad/s).
//    Ramené à la fondamentale (÷ k) : b_k = min(|δ| ρ/(1 − ρ), 3 asin ρ /
//    (2π k L)) Hz, |δ| borné par le battement et sa marge, plus le bruit de
//    la lecture. ρ_k vient du cercle (cercle()), qui ne suppose pas δ
//    constant ; il faut que l'arc ait tourné (R̄ ≤ CONF_RBAR_MAX) et que le
//    8' domine (ρ ≤ CONF_RHO_MAX). Une lecture hors de l'intervalle du
//    battement élargi de son biais n'est pas la raie commune (raie parasite,
//    repli) : écartée. Si les bornes sont justes, la vraie hauteur est dans
//    CHACUN des intervalles [x_k ± b_k] : on donne leur intersection (centre,
//    demi-largeur). Il en faut deux au moins (une lecture seule ne se
//    contrôle pas) ; une intersection vide dit qu'une borne est fausse : rien.
export const CONF_RHO_MAX = 0.5;
export const CONF_RBAR_MAX = 0.8;

export function estimeRaie({ lectures, b, fBat, Tw }) {
  if (!b?.rho?.length || !lectures?.length) return null;
  const dMax = Math.abs(b.d) + b.marge;
  const prises = [];
  for (const L of lectures) {
    const q = b.rho.find((x) => x.k === L.k);
    if (!q || !(q.rho <= CONF_RHO_MAX) || !(q.Rbar <= CONF_RBAR_MAX) || !(L.W > 0) || !(L.f > 0)) continue;
    const T = L.W / L.srd;
    if (T < 0.99 * Tw) continue;
    const x = L.f / L.k;
    // Biais borné (Hz, à la fondamentale), plus le bruit de la lecture : pente
    // de moindres carrés sur L = 0,7 T de N = L/dt échantillons indépendants
    // de bruit de phase σφ, σω = σφ √12 / (L √N), à 2σ, et la précision visée.
    const Lw = 0.7 * T, N = Math.max(1, Lw / q.dt);
    const bruit = (2 * q.sphi * Math.sqrt(12)) / (Lw * Math.sqrt(N) * 2 * Math.PI * L.k);
    const borne = Math.min((dMax * q.rho) / (1 - q.rho), (3 * Math.asin(q.rho)) / (2 * Math.PI * L.k * Lw))
      + Math.hypot(bruit, x * (2 ** (CONF_PRECISION / 1200) - 1));
    if (Math.abs(x - fBat) > b.marge + borne) continue;
    prises.push({ x, borne, w: (L.amp * L.k) ** 2 });
  }
  // Une lecture faible (poids (A k)² sous le quart du plus fort) n'apporte
  // presque rien et c'est elle qu'un reste d'une autre raie dévie le plus.
  const wMax = Math.max(0, ...prises.map((p) => p.w));
  let lo = -Infinity, hi = Infinity, n = 0;
  for (const p of prises) {
    if (p.w < wMax / 4) continue;
    lo = Math.max(lo, p.x - p.borne);
    hi = Math.min(hi, p.x + p.borne);
    n++;
  }
  // Une lecture seule ne se contrôle pas ; des intervalles sans point commun
  // disent qu'une borne est fausse : rien.
  if (n < 2 || !(hi >= lo)) return null;
  return { f: (lo + hi) / 2, marge: (hi - lo) / 2, n };
}

// Garde-fou après la séparation. La cause des premières images séparées
// fausses de 1 à 26 ¢ (une raie parasite, ou une lecture de la raie commune
// qui franchit seule le seuil de 2 cases) est corrigée à la source :
// appariement.js n'accepte une raie séparée que confirmée par un autre
// partiel (octaveFuse). Reste, mesuré sur synthèse, un biais d'au plus 1 à
// 3 ¢ sur la toute première image, quand la fenêtre est courte (0,34 à
// 1,4 s) : à 2 cases de la raie du 16', la pente de phase penche vers la
// plus forte. Pendant au plus CONF_TENUE_S après la dernière image
// confondue, l'anche reste donc dite confondue (champ `confondu`, `merged`
// ne change pas) tant que sa mesure sort de la marge de l'estimation (plus
// la précision visée, CONF_PRECISION ¢).
export const CONF_TENUE_S = 1;
export const CONF_PRECISION = 0.1;

// Marge annoncée (¢) : celle de la confusion, et la précision de la mesure du
// 16' sur laquelle l'estimation s'appuie (CONF_PRECISION, la précision visée
// d'une mesure séparée : sur synthèse, le 16' bouge de 0,05 à 0,1 ¢ quand sa
// fenêtre double ou que le soufflet ondule).
function margeTotale(est) {
  return Math.hypot(centsBetween(est.f + est.marge, est.f), CONF_PRECISION);
}

// Méthodes d'Engine (cf. engine.js, Object.assign).
export const methodesConfondu = {
  // Estimation d'une anche à l'octave d'une autre, mesurée une octave plus
  // bas : { f, marge (Hz), methode, signeConnu } ou null.
  estimationOctave(g, groups) {
    const h = groups.find((x) => x !== g && !x.isHarmonic && !x.isSub && x.voices.length === 1
      && Math.abs(centsBetween(2 * x.center, g.center)) < 50);
    const r = h?.voices[0];
    const Tw = g.W > 0 ? g.W / g.srd : 0;
    if (!r?.tracked || r.merged || r.coarse || !(Tw > 0)) return null;
    const fOct = 2 * r.fMeas;
    let est = { f: fOct, marge: 1 / Tw, methode: 'octave', signeConnu: false };
    const mRef = h.kTrack || 1;
    if (mRef % 2 === 1 && this.plan) {
      const bandes = [{ k: g.kTrack || 1, t: this.trackers.get(g.key) }];
      for (const k of this.plan.partials.get(g.key) ?? []) bandes.push({ k, t: this.trackers.get(`${g.key}p${k}`) });
      const b = estimeBattement({ ref: this.trackers.get(h.key), mRef, fRef: r.fMeas, bandes, Tw });
      if (b && b.marge < est.marge) {
        est = { f: fOct + b.d, marge: b.marge, methode: 'battement', signeConnu: Math.abs(b.d) > b.marge };
      }
      const lect = g.voices[0].lecturesOctave;
      const rc = b && lect?.n === this.samplesTotal ? estimeRaie({ lectures: lect.liste, b, fBat: fOct + b.d, Tw }) : null;
      if (rc && rc.marge < est.marge) {
        est = { f: rc.f, marge: rc.marge, methode: 'raie', signeConnu: Math.abs(rc.f - fOct) > rc.marge };
      }
      est.detail = detailEstimation(r.fMeas, mRef, Tw, b, rc);
    } else {
      est.detail = detailEstimation(r.fMeas, mRef, Tw, null, null);
    }
    return est;
  },

  // Pour chaque anche marquée « confondue avec l'octave » (`merged`), pose :
  //   confondu (true), fEstimee (Hz), centsEstimes (écart à l'échelle, comme
  //   dCents), centsEstimesCible (écart à la cible, comme dTargetCents),
  //   margeCents (±, en cents), methode ('octave' | 'battement'),
  //   signeConnu (le 8' est-il sûrement au-dessus, ou au-dessous, de
  //   l'octave du 16' ?).
  // Sans anche mesurée une octave plus bas : confondu seul, estimation null.
  // Une anche séparée depuis moins de CONF_TENUE_S dont la mesure contredit
  // l'estimation reste dite confondue (cf. plus haut) ; aucune autre n'a ces
  // champs.
  estimerConfondues(groups) {
    const tNow = this.samplesTotal / this.sr;
    this.confT ??= new Map();
    for (const g of groups) {
      if (g.isHarmonic || g.isSub || g.voices.length !== 1) continue;
      const v = g.voices[0];
      if (!v.tracked) continue;
      const key = `${g.key}:${v.def.id}`;
      const der = this.confT.get(key);   // { t : dernière image confondue, f, m : dernière estimation montrée }
      if (!v.merged) {
        if (!der || !(tNow - der.t < CONF_TENUE_S)) { this.confT.delete(key); continue; }
        const est = der.f != null ? this.estimationOctave(g, groups) : null;
        // La mesure séparée prend la main quand elle rejoint l'estimation
        // montrée à l'image d'avant (pas de saut) et celle de cette image.
        if (!est || (Math.abs(centsBetween(v.fMeas, der.f)) <= der.m
            && Math.abs(centsBetween(v.fMeas, est.f)) <= margeTotale(est))) {
          this.confT.delete(key);
          continue;
        }
        this.poserEstimation(v, est);
        der.f = v.fEstimee; der.m = v.margeCents;
        continue;
      }
      this.poserEstimation(v, this.estimationOctave(g, groups));
      this.confT.set(key, { t: tNow, f: v.fEstimee, m: v.margeCents });
    }
  },

  poserEstimation(v, est) {
    v.confondu = true;
    v.fEstimee = est ? est.f : null;
    v.centsEstimes = est ? centsBetween(est.f, v.nominal) : null;
    v.centsEstimesCible = est ? centsBetween(est.f, v.target) : null;
    v.margeCents = est ? margeTotale(est) : null;
    v.methode = est ? est.methode : null;
    v.signeConnu = est ? est.signeConnu : false;
    v.detailConfondu = est?.detail ?? null;
  },
};

// Les trois estimations d'une anche confondue, chacune avec sa marge (Hz, à la
// fondamentale de l'anche), pour la section recherche de L'anche (carte
// « anches confondues ») : rien ici ne change l'estimation retenue.
//   f16, mRef      fondamentale mesurée du 16' et son partiel de mesure (impair)
//   Tw             fenêtre de la mesure normale (s)
//   octave         { f : 2 f16, marge : 1/Tw }
//   battement      { f, d (δ, Hz), marge, A, B, S, T (durée lue, s), kmax,
//                    d1, d2 (moitiés), dFenetre, dMax, partiels : [{ k, rho,
//                    Rbar, sphi, dt (s entre deux points), centre [x, y],
//                    points { x, y, i } }] } ou null (moins d'une seconde de son)
//   raie           { f, marge, n } ou null (la raie commune ne passe pas)
function detailEstimation(f16, mRef, Tw, b, rc) {
  const fOct = 2 * f16;
  return {
    f16, mRef, Tw,
    octave: { f: fOct, marge: 1 / Tw },
    battement: b ? {
      f: fOct + b.d, d: b.d, marge: b.marge, A: b.A, B: b.B, S: b.S, T: b.T, kmax: b.kmax,
      d1: b.d1, d2: b.d2, dFenetre: b.dFenetre, dMax: b.dMax, partiels: b.rho,
    } : null,
    raie: rc ? { f: rc.f, marge: rc.marge, n: rc.n } : null,
  };
}
