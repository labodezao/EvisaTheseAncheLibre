// Estimation paramétrique à sous-espaces — méthode Matrix Pencil (Hua &
// Sarkar, 1990). Modélise un signal complexe comme une somme de M
// exponentielles amorties  y[n] = Σ_i c_i · z_i^n , z_i = e^{(−α_i + j2πf_i)/fs}.
//
// Intérêt pour l'anche libre, appliquée à la bande de base hétérodyne du
// traqueur zoom (signal complexe I/Q, ~93,75 Hz, 1–3 composantes) :
//   • sépare deux anches d'un unisson tremblé SOUS la limite de Fourier 1/T
//     (résolution en ~1 s au lieu de ~5,5 s) ;
//   • donne l'amortissement/croissance α_i de CHAQUE composante — le taux σ
//     du « parler » de l'anche, par partiel, mesuré et non ajusté au RMS.
//
// La bande de base ayant peu d'échantillons et peu de composantes, la
// décomposition (O(L³)) est bon marché et bien conditionnée. Implémentation
// autonome : arithmétique complexe, diagonalisation de Jacobi hermitienne
// pour le sous-espace signal, Faddeev–LeVerrier + Durand–Kerner pour les
// valeurs propres du petit pinceau M×M.

// --- arithmétique complexe : un nombre = [re, im] ---------------------------
const cadd = (a, b) => [a[0] + b[0], a[1] + b[1]];
const csub = (a, b) => [a[0] - b[0], a[1] - b[1]];
const cmul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
const cdiv = (a, b) => {
  const d = b[0] * b[0] + b[1] * b[1] || 1e-300;
  return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
};
const cabs = (a) => Math.hypot(a[0], a[1]);

function zeros2(r, c) {
  const m = new Array(r);
  for (let i = 0; i < r; i++) { m[i] = new Array(c); for (let j = 0; j < c; j++) m[i][j] = [0, 0]; }
  return m;
}

// Diagonalisation d'une matrice hermitienne n×n (Jacobi cyclique complexe).
// Renvoie { values: number[], vectors } avec vectors[i][j] = j-ième vecteur
// propre (colonnes). A est modifiée sur une copie.
function hermitianEigen(Ain, n) {
  const A = zeros2(n, n);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) A[i][j] = [Ain[i][j][0], Ain[i][j][1]];
  const V = zeros2(n, n);
  for (let i = 0; i < n; i++) V[i][i] = [1, 0];
  for (let sweep = 0; sweep < 100; sweep++) {
    let off = 0;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) off += A[p][q][0] ** 2 + A[p][q][1] ** 2;
    if (off < 1e-28) break;
    for (let p = 0; p < n; p++) {
      for (let q = p + 1; q < n; q++) {
        const apq = A[p][q];
        const mod = cabs(apq);
        if (mod < 1e-300) continue;
        const alpha = Math.atan2(apq[1], apq[0]); // apq = mod·e^{iα}
        const app = A[p][p][0], aqq = A[q][q][0];
        const theta = (aqq - app) / (2 * mod);
        const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const c = 1 / Math.sqrt(t * t + 1);
        const s = t * c;
        // Unitaire J = diag(1, e^{-iα})·[[c,s],[−s,c]] qui diagonalise le bloc
        // hermitien 2×2 : Jᴴ A J annule (p,q). J_qq n'est pas réel.
        const eR = Math.cos(alpha), eI = Math.sin(alpha);   // e^{iα}
        const Jpp = [c, 0], Jpq = [s, 0];
        const Jqp = [-s * eR, s * eI];   // −s·e^{-iα}
        const Jqq = [c * eR, -c * eI];   // c·e^{-iα}
        const cj = (z) => [z[0], -z[1]];
        // Colonnes (B = A J) puis lignes (A = Jᴴ B).
        for (let k = 0; k < n; k++) {
          const akp = A[k][p], akq = A[k][q];
          A[k][p] = cadd(cmul(akp, Jpp), cmul(akq, Jqp));
          A[k][q] = cadd(cmul(akp, Jpq), cmul(akq, Jqq));
        }
        for (let k = 0; k < n; k++) {
          const apk = A[p][k], aqk = A[q][k];
          A[p][k] = cadd(cmul(cj(Jpp), apk), cmul(cj(Jqp), aqk));
          A[q][k] = cadd(cmul(cj(Jpq), apk), cmul(cj(Jqq), aqk));
        }
        for (let k = 0; k < n; k++) {
          const vkp = V[k][p], vkq = V[k][q];
          V[k][p] = cadd(cmul(vkp, Jpp), cmul(vkq, Jqp));
          V[k][q] = cadd(cmul(vkp, Jpq), cmul(vkq, Jqq));
        }
      }
    }
  }
  const values = new Array(n);
  for (let i = 0; i < n; i++) values[i] = A[i][i][0];
  return { values, vectors: V };
}

// Résout A·X = B (A n×n complexe, B n×m) par élimination de Gauss avec pivot.
function cSolve(Ain, Bin, n, m) {
  const A = zeros2(n, n), B = zeros2(n, m);
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) A[i][j] = [Ain[i][j][0], Ain[i][j][1]];
    for (let j = 0; j < m; j++) B[i][j] = [Bin[i][j][0], Bin[i][j][1]];
  }
  for (let col = 0; col < n; col++) {
    let piv = col, best = cabs(A[col][col]);
    for (let r = col + 1; r < n; r++) { const v = cabs(A[r][col]); if (v > best) { best = v; piv = r; } }
    if (best < 1e-300) continue;
    if (piv !== col) { [A[col], A[piv]] = [A[piv], A[col]]; [B[col], B[piv]] = [B[piv], B[col]]; }
    const d = A[col][col];
    for (let j = 0; j < n; j++) A[col][j] = cdiv(A[col][j], d);
    for (let j = 0; j < m; j++) B[col][j] = cdiv(B[col][j], d);
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = A[r][col];
      if (f[0] === 0 && f[1] === 0) continue;
      for (let j = 0; j < n; j++) A[r][j] = csub(A[r][j], cmul(f, A[col][j]));
      for (let j = 0; j < m; j++) B[r][j] = csub(B[r][j], cmul(f, B[col][j]));
    }
  }
  return B;
}

// Coefficients du polynôme caractéristique d'une matrice M×M (Faddeev–
// LeVerrier). Renvoie a[0..M] avec p(λ)=Σ a[k]λ^k, a[M]=[1,0].
function charPoly(A, M) {
  const a = new Array(M + 1);
  a[M] = [1, 0];
  let Mk = zeros2(M, M);
  for (let i = 0; i < M; i++) Mk[i][i] = [1, 0]; // M_0 = I
  for (let k = 1; k <= M; k++) {
    // AM = A·Mk
    const AM = zeros2(M, M);
    for (let i = 0; i < M; i++)
      for (let j = 0; j < M; j++) {
        let s = [0, 0];
        for (let l = 0; l < M; l++) s = cadd(s, cmul(A[i][l], Mk[l][j]));
        AM[i][j] = s;
      }
    let tr = [0, 0];
    for (let i = 0; i < M; i++) tr = cadd(tr, AM[i][i]);
    const ck = [-tr[0] / k, -tr[1] / k];
    a[M - k] = ck;
    // Mk = AM + ck·I
    for (let i = 0; i < M; i++)
      for (let j = 0; j < M; j++) Mk[i][j] = i === j ? cadd(AM[i][j], ck) : AM[i][j];
  }
  return a;
}

// Racines d'un polynôme monique complexe (Durand–Kerner).
function roots(a, M) {
  const evalP = (z) => {
    let r = a[M];
    for (let k = M - 1; k >= 0; k--) r = cadd(cmul(r, z), a[k]);
    return r;
  };
  let z = new Array(M);
  const seed = [0.4, 0.9];
  z[0] = [1, 0];
  for (let i = 1; i < M; i++) z[i] = cmul(z[i - 1], seed);
  for (let it = 0; it < 200; it++) {
    let move = 0;
    for (let i = 0; i < M; i++) {
      let den = [1, 0];
      for (let j = 0; j < M; j++) if (j !== i) den = cmul(den, csub(z[i], z[j]));
      const dz = cdiv(evalP(z[i]), den);
      z[i] = csub(z[i], dz);
      move += cabs(dz);
    }
    if (move < 1e-14) break;
  }
  return z;
}

// Estimateur Matrix Pencil. yr/yi : bande de base complexe. M : nombre de
// composantes. fs : fréquence d'échantillonnage de la bande de base.
// Renvoie [{ freq, damping, amp, phase }] trié par fréquence (freq en Hz
// relatifs à la porteuse ; damping en s⁻¹, >0 = décroissance, <0 = croissance).
export function matrixPencil(yr, yi, M, fs) {
  const N = yr.length;
  if (N < 2 * M + 2 || M < 1) return [];
  const L = Math.min(N - M - 1, Math.max(M + 1, Math.floor(N / 2)));
  const P = N - L;                       // lignes de Hankel
  const cols = L + 1;
  // Hankel Y (P×cols), Y[k][l] = y[k+l].
  const Y = zeros2(P, cols);
  for (let k = 0; k < P; k++) for (let l = 0; l < cols; l++) Y[k][l] = [yr[k + l], yi[k + l]];
  // C = Yᴴ Y (cols×cols, hermitienne) → sous-espace par vecteurs propres.
  const C = zeros2(cols, cols);
  for (let i = 0; i < cols; i++)
    for (let j = i; j < cols; j++) {
      let s = [0, 0];
      for (let k = 0; k < P; k++) s = cadd(s, cmul([Y[k][i][0], -Y[k][i][1]], Y[k][j]));
      C[i][j] = s;
      C[j][i] = [s[0], -s[1]];
    }
  const { values, vectors } = hermitianEigen(C, cols);
  // M plus grandes valeurs propres = sous-espace signal.
  const order = values.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0]);
  const Meff = Math.min(M, cols - 1);
  const idx = order.slice(0, Meff).map((o) => o[1]);
  // V1 = V_M sans la dernière ligne ; V2 = sans la première (chacune L×Meff).
  const V1 = zeros2(L, Meff), V2 = zeros2(L, Meff);
  for (let r = 0; r < L; r++)
    for (let c = 0; c < Meff; c++) { V1[r][c] = vectors[r][idx[c]]; V2[r][c] = vectors[r + 1][idx[c]]; }
  // Ψ = (V1ᴴ V1)⁻¹ (V1ᴴ V2) — pinceau Meff×Meff dont les valeurs propres
  // sont les pôles z_i.
  const A11 = zeros2(Meff, Meff), A12 = zeros2(Meff, Meff);
  for (let i = 0; i < Meff; i++)
    for (let j = 0; j < Meff; j++) {
      let s1 = [0, 0], s2 = [0, 0];
      for (let r = 0; r < L; r++) {
        const conj = [V1[r][i][0], -V1[r][i][1]];
        s1 = cadd(s1, cmul(conj, V1[r][j]));
        s2 = cadd(s2, cmul(conj, V2[r][j]));
      }
      A11[i][j] = s1; A12[i][j] = s2;
    }
  const Psi = cSolve(A11, A12, Meff, Meff);
  // Les vecteurs singuliers droits (issus de YᴴY) engendrent l'espace des
  // {conj(z_i)^l} : les valeurs propres du pinceau sont donc conj(z_i). On
  // conjugue pour retrouver les vrais pôles (fréquence, et base correcte pour
  // l'ajustement des amplitudes).
  const poles = roots(charPoly(Psi, Meff), Meff).map((z) => [z[0], -z[1]]);

  // Amplitudes par moindres carrés sur la Vandermonde A[n][i] = z_i^n.
  const comps = [];
  const Van = zeros2(N, Meff);
  for (let i = 0; i < Meff; i++) {
    let p = [1, 0];
    for (let n = 0; n < N; n++) { Van[n][i] = p; p = cmul(p, poles[i]); }
  }
  // (Aᴴ A) c = Aᴴ y
  const G = zeros2(Meff, Meff), rhs = zeros2(Meff, 1);
  for (let i = 0; i < Meff; i++) {
    for (let j = 0; j < Meff; j++) {
      let s = [0, 0];
      for (let n = 0; n < N; n++) s = cadd(s, cmul([Van[n][i][0], -Van[n][i][1]], Van[n][j]));
      G[i][j] = s;
    }
    let sy = [0, 0];
    for (let n = 0; n < N; n++) sy = cadd(sy, cmul([Van[n][i][0], -Van[n][i][1]], [yr[n], yi[n]]));
    rhs[i][0] = sy;
  }
  const coef = cSolve(G, rhs, Meff, 1);
  for (let i = 0; i < Meff; i++) {
    const z = poles[i];
    const mag = cabs(z);
    if (!isFinite(mag) || mag < 1e-12) continue;
    const freq = (Math.atan2(z[1], z[0]) * fs) / (2 * Math.PI);
    const damping = -Math.log(mag) * fs;
    comps.push({ freq, damping, amp: cabs(coef[i][0]), phase: Math.atan2(coef[i][0][1], coef[i][0][0]) });
  }
  comps.sort((a, b) => a.freq - b.freq);
  return comps;
}
