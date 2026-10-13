// Verrou de phase par anche (v59, prototype hors moteur) : chaque anche d'un unisson est suivie par sa PHASE, partiel par
// partiel, et sa fréquence est lue comme une différence de phase sur un nombre ENTIER de périodes de battement.
//
// Pourquoi c'est exact. Deux ou trois anches qui sonnent ensemble : autour de k f_i (partiel k de l'anche i), après
// démodulation par un oscillateur local à k f̂_i, le signal ne contient que des raies à des écarts multiples du battement Ω
// (l'autre anche à k Δ, les raies de couplage à m Δ, la modulation d'Adler : tout est périodique de période 1/Ω). Tant que la
// raie de l'anche i domine dans la bande (le signal démodulé ne fait pas le tour de zéro), sa phase s'écrit
//   ψ(t) = 2π k (f_i − f̂_i) t + p(t),   p périodique de période 1/Ω,
// donc ψ(t) − ψ(t − L) = 2π k (f_i − f̂_i) L EXACTEMENT quand L = m/Ω, quelle que soit la fuite de la voisine ou la
// modulation de phase : c'est la définition de « la fréquence de l'anche en place » du banc (vraieEntiere). Les filtres ne
// servent qu'à garder la raie de l'anche dominante dans sa bande : deux moyennes glissantes de longueur 1/(k δ_j) par voisine
// j (δ_j = |f_j − f_i|) placent un zéro double sur chaque voisine. La longueur du filtre est 2/(k δ) : sur le partiel k, deux
// anches à δ Hz se séparent k fois plus vite qu'au fondamental (Rayleigh au partiel k). Les partiels sont combinés par une
// moyenne pondérée (k² A²) après rejet de ceux qui ne disent pas la même fréquence (raie étrangère, partiel creusé).
//
// Références : lecture de fréquence par la phase (compteurs Λ/Ω, Rubiola 2005, Rev. Sci. Instrum. 76, 054703) ; détection
// synchrone (lock-in) ; tirage des anches couplées périodique au battement (Adler 1946 ; Pikovsky, Rosenblum, Kurths 2001).
//
// ÉTAT (13/10/2026) : branché en v59 comme OPTION EXPÉRIMENTALE éteinte par défaut (lecteur-note.js, verrou-worker.js), jamais dans le moteur. Exact sur le banc de synthèse (test/bench_verrou.mjs, test/verrou.test.mjs) et, par
// `lireNote` (verrou-note.js : plage stable, ajustement de raies, étiquette, partiels utiles), juste à 0,1 ¢ sur le banc fidèle au
// réel (test/bench_reel.mjs) et sur 7 notes de la session d'Ewen ; le branchement attend les enregistrements demandés dans
// docs/FREQUENCES-ANCHES.md, « Verrou de phase par anche ».

export const VERROU_DEC_HZ = 1000;      // cadence de la phase démodulée (Hz)
export const VERROU_FILTRE_MAX_S = 1.2; // filtre de séparation le plus long accepté (s) : 2/(k δ) ≤ 1,2 s
export const VERROU_K_MAX = 16;
export const VERROU_K_CONSIGNE = 8;    // partiels lus pour la consigne du soufflet
export const VERROU_FMAX = 10000;       // partiels lus jusqu'à 10 kHz (micro et chambre au-delà : peu fiables)
export const VERROU_SEUL_S = 0.02;      // anche sans voisine : deux moyennes de 20 ms (rejette les autres partiels)
export const VERROU_PAS_CONSIGNE = 0.3;  // ¢ par image de consigne (10 ms) : la consigne suit le soufflet à 10 ¢/s au plus
export const VERROU_TAU_CONSIGNE = 0.2;  // s, constante de temps de la consigne
export const VERROU_ENROULE = 0.05;     // |z| sous 5 % de sa moyenne : passage si près de zéro que le déroulé à 1 kHz peut sauter

// Phase démodulée de chaque partiel de chaque anche. x : signal (Float32Array), sr : Hz, freqs : fréquences des anches (Hz,
// l'ordre est l'étiquette), i0 : premier échantillon de la note. Rend { dt, t0, parAnche: [ [ { k, D (s), n0, psi, amp } ] ] }
// où psi[m] est la phase déroulée (rad) du partiel k démodulé à k f̂ au temps t0 + m dt (déjà retardée de D).
export function phasesVerrouillees(x, sr, freqs, { i0 = 0, i1 = x.length, kMax = VERROU_K_MAX, fMax = VERROU_FMAX,
  filtreMaxS = VERROU_FILTRE_MAX_S } = {}) {
  const dec = Math.max(1, Math.round(sr / VERROU_DEC_HZ));
  const N = i1 - i0;
  const re = new Float64Array(N), im = new Float64Array(N);
  const parAnche = freqs.map(() => []);
  for (let i = 0; i < freqs.length; i++) {
    const fi = freqs[i];
    for (let k = 1; k <= kMax && k * fi < Math.min(fMax, 0.45 * sr); k++) {
      const longueurs = [];
      for (let j = 0; j < freqs.length; j++) {
        if (j === i) continue;
        const g = k * Math.abs(freqs[j] - fi);
        if (!(g > 0)) continue;
        const n = Math.round(sr / g);
        longueurs.push(n, n);
      }
      if (!longueurs.length) longueurs.push(Math.round(VERROU_SEUL_S * sr), Math.round(VERROU_SEUL_S * sr));
      const nTot = longueurs.reduce((a, b) => a + b - 1, 0);
      if (nTot / sr > filtreMaxS || nTot >= N - dec) continue;
      // démodulation par l'oscillateur local à k f̂ (phase exacte en double, sans dérive d'accumulation)
      const w = (2 * Math.PI * k * fi) / sr;
      for (let n = 0; n < N; n++) {
        const a = w * (n + i0), v = x[n + i0];
        re[n] = v * Math.cos(a); im[n] = -v * Math.sin(a);
      }
      // moyennes glissantes en cascade (zéros sur les voisines) ; somme courante, résultat aligné à droite
      for (const L of longueurs) moyenneGlissante(re, im, L);
      // lecture décimée, phase déroulée, retard D = Σ (L − 1)/2 compensé dans l'oscillateur
      const D = nTot / 2;
      const n0 = nTot;   // premier échantillon valide (filtre plein)
      const M = Math.floor((N - 1 - n0) / dec) + 1;
      const psi = new Float64Array(M), amp = new Float64Array(M);
      let prec = 0, tours = 0;
      for (let m = 0; m < M; m++) {
        const n = n0 + m * dec;
        const ph = Math.atan2(im[n], re[n]);
        if (m > 0) {
          const d = ph - prec;
          if (d > Math.PI) tours -= 2 * Math.PI; else if (d < -Math.PI) tours += 2 * Math.PI;
        }
        prec = ph;
        // phase totale = phase démodulée + phase de l'oscillateur au centre du filtre (n − D)
        psi[m] = ph + tours + w * (n + i0 - D);
        amp[m] = Math.hypot(re[n], im[n]);
      }
      // psi[m] est la phase du son à l'instant t0 + m dt (le centre du filtre), connue à t0 + m dt + D
      parAnche[i].push({ k, D: D / sr, t0: (i0 + n0 - D) / sr, dt: dec / sr, psi, amp });
    }
  }
  return { parAnche, freqs };
}

export const DECIM_HZ = 1000;   // cadence du signal démodulé après décimation (Hz)

// Démodulation à c (Hz) de x[i0 + n pas], n < N, puis deux moyennes glissantes de longueur M en cascade et décimation par M : rend le signal
// complexe { zr, zi } à fe/M. Rotation complexe au lieu de cos/sin à chaque échantillon (renormalisée toutes les 1024).
export function demodulerDecimer(x, i0, N, pas, fe, c, M) {
  const re = new Float64Array(N), im = new Float64Array(N), w = (2 * Math.PI * c) / fe, rr = Math.cos(w), ri = Math.sin(w);
  let cr = 1, ci = 0;
  for (let n = 0; n < N; n++) {
    const v = x[i0 + n * pas];
    re[n] = v * cr; im[n] = -v * ci;
    const t = cr * rr - ci * ri; ci = cr * ri + ci * rr; cr = t;
    if ((n & 1023) === 1023) { const m = Math.hypot(cr, ci); cr /= m; ci /= m; }
  }
  if (M > 1) { moyenneGlissante(re, im, M); moyenneGlissante(re, im, M); }
  const s0 = M > 1 ? 2 * (M - 1) : 0, N2 = Math.max(0, Math.floor((N - 1 - s0) / M) + 1);
  const zr = new Float64Array(N2), zi = new Float64Array(N2);
  for (let q = 0; q < N2; q++) { zr[q] = re[s0 + q * M]; zi[q] = im[s0 + q * M]; }
  return { zr, zi };
}
// Réponse en amplitude de deux moyennes glissantes de longueur M à l'écart d (Hz), cadence fe : (sin(π d M / fe) / (M sin(π d / fe)))².
export function reponseBoite(d, fe, M) {
  const a = (Math.PI * d) / fe;
  if (M <= 1 || Math.abs(a) < 1e-12) return 1;
  const s = Math.sin(a * M) / (M * Math.sin(a));
  return s * s;
}

function moyenneGlissante(re, im, L) {
  const N = re.length;
  let sr = 0, si = 0;
  const qr = new Float64Array(L), qi = new Float64Array(L);   // tampon circulaire : la somme glissante sans perte
  for (let n = 0; n < N; n++) {
    const p = n % L;
    sr += re[n] - qr[p]; si += im[n] - qi[p];
    qr[p] = re[n]; qi[p] = im[n];
    re[n] = sr / L; im[n] = si / L;
  }
}

// Verrou EN CONTINU (le même calcul, échantillon par échantillon, comme dans le moteur) : l'oscillateur de chaque anche SUIT
// sa fréquence (le soufflet déplace les deux anches de plusieurs cents ; un oscillateur fixe laisserait la raie sortir de sa
// bande et glisser vers le zéro de la voisine). La consigne de chaque anche est relue toutes les `pasConsigne` images sur une
// période de fuite 1/(kΩ) de chaque partiel (la fuite s'y annule), médiane des partiels. La phase de l'oscillateur passe par
// le MÊME filtre que le signal démodulé : Ψ = arg(h * x e^{−jkθ}) + h * kθ = h * φ (à la linéarisation près), sans erreur aux
// changements de consigne. Seul le surplus δθ (θ = ω0 n + δθ) est filtré, pour garder la précision des sommes glissantes.
export class VerrouAnches {
  constructor(sr, freqs, { kMax = VERROU_K_MAX, fMax = VERROU_FMAX, filtreMaxS = VERROU_FILTRE_MAX_S, omega = null,
    suivre = true, pasConsigne = 10, memoireS = 10, partiels = null, etrangeres = [], consigneExterne = null } = {}) {
    this.consigneExterne = consigneExterne;   // (t en s depuis le début du signal) -> écart relatif de toutes les anches ; remplace la consigne lue sur les phases
    this.sr = sr; this.f0 = [...freqs]; this.suivre = suivre; this.pasConsigne = pasConsigne;
    this.dec = Math.max(1, Math.round(sr / VERROU_DEC_HZ)); this.dt = this.dec / sr;
    this.omega = omega ?? (freqs.length > 1 ? Math.min(...freqs.slice(1).map((f, j) => Math.abs(f - freqs[j]))) : 5);
    this.n = 0; this.m = 0;
    this.dth = freqs.map(() => 0);         // δθ de chaque anche (rad, fondamental)
    this.dw = freqs.map(() => 0);          // δω (rad par échantillon)
    this.cap = Math.ceil(memoireS / this.dt);
    this.lignes = [];
    for (let i = 0; i < freqs.length; i++) {
      const fi = freqs[i];
      for (let k = 1; k <= kMax && k * fi < Math.min(fMax, 0.45 * sr); k++) {
        if (partiels && !partiels.includes(k)) continue;   // partiels utiles (SNR) : les autres ne coûtent rien
        let Ls = [];
        for (let j = 0; j < freqs.length; j++) {
          if (j === i) continue;
          const g = k * Math.abs(freqs[j] - fi);
          if (g > 0) { const n = Math.round(sr / g); Ls.push(n, n); }
        }
        // zéros sur les raies étrangères quand le filtre reste assez court (sinon la raie reste, voir `lireNote`)
        const Lf = [];
        for (const fe of etrangeres) { const g = k * Math.abs(fe - fi); if (g > 0.05) { const n = Math.round(sr / g); Lf.push(n, n); } }
        if (!Ls.length) Ls.push(Math.round(VERROU_SEUL_S * sr), Math.round(VERROU_SEUL_S * sr));
        let nTot = [...Ls, ...Lf].reduce((a, b) => a + b - 1, 0);
        if (nTot / sr <= filtreMaxS) Ls = [...Ls, ...Lf]; else nTot = Ls.reduce((a, b) => a + b - 1, 0);
        if (nTot / sr > filtreMaxS) continue;
        this.lignes.push({ i, k, D: nTot / 2, nTot, etages: Ls.map((L) => ({ L, br: new Float64Array(L), bi: new Float64Array(L), bt: new Float64Array(L), sr: 0, si: 0, st: 0 })),
          psi: new Float64Array(this.cap), amp: new Float64Array(this.cap), prec: 0, tours: 0, pret: false, mPret: -1 });
      }
    }
    this.nMax = Math.max(0, ...this.lignes.map((l) => l.nTot));
    this.epsHist = new Float64Array(this.cap);
    this.fCons = [...freqs];
  }

  // Consomme un bloc d'échantillons (Float32Array).
  traiter(bloc) {
    const R = this.f0.length, w0 = this.f0.map((f) => (2 * Math.PI * f) / this.sr);
    // e^{−jkθ} par récurrence sur k, une fois par anche et par échantillon (au lieu de cos et sin de k θ par ligne : 2 appels par ligne et par
    // échantillon) ; mêmes valeurs à 1e-15 près (k ≤ 16)
    const kmax = new Int32Array(R);
    for (const l of this.lignes) if (l.k > kmax[l.i]) kmax[l.i] = l.k;
    const Er = Array.from({ length: R }, (_, i) => new Float64Array(kmax[i] + 1)), Ei = Array.from({ length: R }, (_, i) => new Float64Array(kmax[i] + 1));
    for (let q = 0; q < bloc.length; q++) {
      const n = this.n, v = bloc[q];
      for (let i = 0; i < R; i++) {
        this.dth[i] += this.dw[i];
        const a = w0[i] * n + this.dth[i], c1 = Math.cos(a), s1 = -Math.sin(a), er = Er[i], ei = Ei[i];
        er[1] = c1; ei[1] = s1;
        for (let k = 2; k <= kmax[i]; k++) { er[k] = er[k - 1] * c1 - ei[k - 1] * s1; ei[k] = er[k - 1] * s1 + ei[k - 1] * c1; }
      }
      for (const l of this.lignes) {
        const er = Er[l.i][l.k], ei = Ei[l.i][l.k];
        let xr = v * er, xi = v * ei, xt = l.k * this.dth[l.i];
        for (const e of l.etages) {
          const p = n % e.L;
          e.sr += xr - e.br[p]; e.si += xi - e.bi[p]; e.st += xt - e.bt[p];
          e.br[p] = xr; e.bi[p] = xi; e.bt[p] = xt;
          xr = e.sr / e.L; xi = e.si / e.L; xt = e.st / e.L;
        }
        l._zr = xr; l._zi = xi; l._zt = xt;
      }
      this.n++;
      if (this.n % this.dec === 0) this.lire();
    }
  }

  lire() {
    const m = this.m, slot = m % this.cap, n = this.n - 1;
    for (const l of this.lignes) {
      const ph = Math.atan2(l._zi, l._zr);
      if (l.pret) {
        const d = ph - l.prec;
        if (d > Math.PI) l.tours -= 2 * Math.PI; else if (d < -Math.PI) l.tours += 2 * Math.PI;
      }
      l.prec = ph;
      if (!l.pret && n >= l.nTot) { l.pret = true; l.mPret = m; }
      // phase totale du partiel au centre du filtre : arg z + k ω0 (n − D) + h * kδθ
      l.psi[slot] = ph + l.tours + l.k * (2 * Math.PI * this.f0[l.i] / this.sr) * (n - l.D) + l._zt;
      l.amp[slot] = Math.hypot(l._zr, l._zi);
    }
    this.epsHist[slot] = this.eps ?? 0;
    this.m++;
    if (this.consigneExterne) {
      // la consigne vient d'ailleurs (droite de la plage stable) : toutes les anches suivent le même écart relatif, sans biais de partiel
      if (this.m % this.pasConsigne === 0) {
        const eps = this.consigneExterne(this.n / this.sr);
        this.eps = eps;
        for (let i = 0; i < this.f0.length; i++) { this.fCons[i] = this.f0[i] * (1 + eps); this.dw[i] = (2 * Math.PI * this.f0[i] * eps) / this.sr; }
      }
    } else if (this.suivre && this.m % this.pasConsigne === 0) this.consigne();
  }

  // indice (dans la mémoire circulaire) de l'image m ; null si sortie de mémoire ou avant le filtre plein
  _idx(l, m) { return m < l.mPret || m < this.m - this.cap || m >= this.m || !l.pret ? null : m % this.cap; }

  // Consigne COMMUNE : le soufflet déplace toutes les anches du même rapport. Suivie seule, chaque anche se laisse capturer
  // par la plus forte ; une médiane sur toutes les anches aussi (les partiels d'une anche faible capturée la tirent vers la
  // forte, et l'emballement suit : essais du 12/10/2026 sur la session d'Ewen). L'écart relatif ε est donc lu sur l'anche la
  // PLUS FORTE seule, sur ses partiels bas (k ≤ 4 : aux partiels hauts d'anches réelles, les raies de couplage à ±Δ valent la
  // porteuse, mesuré sur Fa#4), chacun sur sa période de fuite 1/(kΩ). Et ε bouge LENTEMENT (constante de temps 0,3 s, pas de
  // plus de 0,02 ¢ par 10 ms soit 2 ¢/s) : un saut de consigne fait tourner la phase résiduelle de plusieurs radians dans le
  // filtre, la lecture se fausse et la consigne s'emballe (vu : +8 ¢ en 0,5 s sur une note stable).
  consigne() {
    const m1 = this.m - 1, R = this.f0.length;
    let sw = 0, sm = 0;
    for (const l of this.lignes) {
      const a = this._idx(l, m1);
      if (a == null || l.k > VERROU_K_CONSIGNE) continue;
      if (m1 - l.mPret < VERROU_DEC_HZ / 2) continue;           // 0,5 s après le filtre plein (attaque)
      const P = Math.max(20, Math.round(1 / (l.k * this.omega) / this.dt));
      const b = this._idx(l, m1 - P);
      if (b == null) continue;
      // moyenne pondérée par l'amplitude sur TOUTES les anches : le tirage de deux anches voisines est en opposition de phase,
      // il se compense (lire la seule anche forte injectait sa modulation de fréquence dans la consigne des autres)
      sw += l.amp[a]; sm += l.amp[a] * ((l.psi[a] - l.psi[b]) / (2 * Math.PI * l.k * P * this.dt) / this.f0[l.i] - 1);
    }
    if (!(sw > 0)) return;
    const mes = sm / sw, e0 = this.eps ?? 0, pasMax = VERROU_PAS_CONSIGNE / 1731;   // en rapport (1 ¢ ≈ 1/1731)
    const g = Math.min(1, (this.pasConsigne * this.dt) / VERROU_TAU_CONSIGNE);
    const eps = e0 + Math.max(-pasMax, Math.min(pasMax, g * (mes - e0)));
    this.eps = eps;
    for (let i = 0; i < R; i++) { this.fCons[i] = this.f0[i] * (1 + eps); this.dw[i] = (2 * Math.PI * this.f0[i] * eps) / this.sr; }
  }

  // Lecture à l'instant présent (ou `retardS` plus tôt) sur L s : comme lireFrequences.
  lireFrequences(L, opts = {}) { return lireFrequences(this.vue(), this.n / this.sr, L, opts); }

  // vue compatible avec lireFrequences : par anche, ses partiels { k, D (s), t0, dt, psi, amp } (copie linéaire de la mémoire)
  vue() {
    const parAnche = this.f0.map(() => []);
    for (const l of this.lignes) {
      if (!l.pret) continue;
      const m0 = Math.max(l.mPret, this.m - this.cap), M = this.m - m0;
      const psi = new Float64Array(M), amp = new Float64Array(M);
      for (let q = 0; q < M; q++) { const s = (m0 + q) % this.cap; psi[q] = l.psi[s]; amp[q] = l.amp[s]; }
      // l'image m est lue à l'échantillon n = (m + 1) dec − 1 et parle de l'instant n − D
      parAnche[l.i].push({ k: l.k, D: l.D / this.sr, t0: ((m0 + 1) * this.dec - 1 - l.D) / this.sr, dt: this.dt, psi, amp });
    }
    // fréquence de verrouillage de l'anche i à l'instant t (s) : la référence qui lève l'ambiguïté entière des partiels
    const ref = (i, t) => {
      const m = Math.round(t / this.dt);
      const e = m >= 0 && m < this.m && m >= this.m - this.cap ? this.epsHist[m % this.cap] : (this.eps ?? 0);
      return this.f0[i] * (1 + e);
    };
    return { parAnche, freqs: this.f0, ref };
  }
}

// Fréquence de chaque anche lue à t (s, fin de la lecture) sur L s (un nombre entier de périodes de battement : voir
// fenetreEntiere). Chaque partiel donne f_ik = (Ψ(tLu) − Ψ(tLu − L)) / (2π k L), tous à l'instant COMMUN tLu = t − Dmax
// (le plus long retard de filtre : seul ce qui est arrivé avant t sert) pour qu'ils parlent de la même fenêtre.
// AMBIGUÏTÉ ENTIÈRE : quand, dans la bande d'un partiel, une raie de couplage (k f + m Ω) ou la voisine passe devant la
// porteuse de l'anche, le signal démodulé fait des tours de zéro en plus et le partiel lit f + w/(k L), w entier (Ω/k par
// tour et par période quand tout est périodique ; vibrato et dérive en font des demi-quanta, vu au banc « tout réaliste »).
// Mesuré sur la session d'Ewen (Fa#4, Fa#5, Sol5, partiels 2 à 8). Comme la phase de porteuse en GPS (Teunissen 1995,
// LAMBDA), w se lève par une référence connue à mieux que 1/(2L) : f* maximise Σ a_k cos(2π k L (f_k − f)) sur
// [réf − 1/(2L), réf + 1/(2L)] (un seul sommet par 1/L), puis chaque partiel est ramené de w/(kL). Références : l'anche la PLUS
// FORTE se réfère à la médiane brute de ses partiels (ses porteuses dominent) ; chaque autre anche à la forte + l'écart de
// l'accrochage (`ph.ref(i, t)` ou `ref[i]`, sinon `ph.freqs`) : l'étiquette ne peut plus glisser d'un battement.
// `court` : avant L, chaque partiel lit le plus grand multiple de sa période de fuite 1/(kΩ) disponible (`omega` requis).
// Rend par anche { f, a, sigmaHz, n, tLu, court, parPartiel: [{ k, f, w, L, a, refuse }] } ou null.
export function lireFrequences(ph, t, L, { tolCents = 0.08, omega = null, court = false, kMin = 1, ref = null, prec = null, ecarts = null } = {}) {
  const brut = ph.parAnche.map((parts) => {
    const utiles = parts.filter((p) => p.k >= kMin);
    if (!utiles.length) return null;
    const Dmax = Math.max(...utiles.map((p) => p.D));
    const tLu = t - Dmax;
    const lus = [];
    let estCourt = false;
    for (const p of utiles) {
      const m1 = Math.round((tLu - p.t0) / p.dt);
      if (m1 >= p.psi.length || m1 < 1) continue;
      let nL = Math.round(L / p.dt);
      if (nL > m1) {
        if (!court || !(omega > 0)) continue;
        const per = 1 / (p.k * omega);
        const nb = Math.floor((m1 * p.dt) / per);
        if (nb < 1) continue;
        nL = Math.round((nb * per) / p.dt);
        estCourt = true;
      }
      const m0 = m1 - nL;
      let aMoy = 0, aMin = Infinity;
      for (let m = m0; m <= m1; m++) { aMoy += p.amp[m]; if (p.amp[m] < aMin) aMin = p.amp[m]; }
      aMoy /= nL + 1;
      const f = (p.psi[m1] - p.psi[m0]) / (2 * Math.PI * p.k * nL * p.dt);
      lus.push({ k: p.k, f, w: 0, L: nL * p.dt, a: aMoy, refuse: aMin < VERROU_ENROULE * aMoy ? 'creux' : null });
    }
    const bons = lus.filter((l) => !l.refuse);
    return bons.length ? { tLu, court: estCourt, lus, bons, A: bons.reduce((q, l) => q + l.a, 0) } : null;
  });
  const medPond = (ls) => {
    const tri = [...ls].sort((x, y) => x.f - y.f), tot = tri.reduce((q, l) => q + l.a, 0);
    let acc = 0;
    for (const l of tri) { acc += l.a; if (acc >= tot / 2) return l.f; }
    return tri.at(-1).f;
  };
  const lever = (bons, fr) => {
    const Lm = Math.min(...bons.map((l) => l.L));
    const kMx = Math.max(...bons.map((l) => l.k * l.L));
    const pas = 1 / (32 * kMx);
    let best = -Infinity, fb = fr;
    // Les partiels PAIRS ne distinguent pas f de f + 1/(2L) (leur réseau est 1/(kL)) : seuls les impairs le font, et ils sont souvent
    // les plus faibles (partiel 3 creusé, 5 et 7 refusés). Quand deux sommets se valent, c'est celui qui est près de la référence
    // qui gagne : pénalité quadratique, d'un tiers de l'amplitude totale au bord de l'intervalle (vu au banc fidèle : l'anche faible
    // lue Ω de trop une lecture sur trois, la médiane suivait).
    const At = bons.reduce((q, l) => q + l.a, 0);
    for (let f = fr - 1 / (2 * Lm); f <= fr + 1 / (2 * Lm); f += pas) {
      let g = 0;
      for (const l of bons) g += l.a * Math.cos(2 * Math.PI * l.k * l.L * (l.f - f));
      g -= (At / 3) * (2 * (f - fr) * Lm) ** 2;
      if (g > best) { best = g; fb = f; }
    }
    for (const l of bons) {
      const w = Math.round((l.f - fb) * l.k * l.L);
      if (w !== 0) { l.w = w; l.f -= w / (l.k * l.L); }
    }
  };
  let iS = -1;
  brut.forEach((b, i) => { if (b && (iS < 0 || b.A > brut[iS].A)) iS = i; });
  if (iS < 0) return brut.map(() => null);
  const verrouillage = (i, tq) => (typeof ph.ref === 'function' ? ph.ref(i, tq) : ref?.[i] ?? ph.freqs?.[i]);
  const verrouillageForte = (i) => (brut[i] ? verrouillage(i, brut[i].tLu - L / 2) : null);
  // L'anche forte : sa référence est la lecture d'avant, sinon la fréquence de l'oscillateur (l'accrochage, suivi par la consigne),
  // JAMAIS la médiane brute des partiels : elle peut tomber d'un cran du réseau 1/L commun à tous les partiels (vu au banc fidèle :
  // 6 notes sur 72 lues sûres, fausses de Ω/2 ou de Ω, tous les partiels d'accord entre eux sur la mauvaise valeur).
  const osc = verrouillageForte(iS);
  lever(brut[iS].bons, prec?.[iS] ?? osc ?? medPond(brut[iS].bons));
  const fS = medPond(brut[iS].bons);
  return brut.map((b, i) => {
    if (!b) return null;
    if (i !== iS) {
      const tq = b.tLu - L / 2, gS = verrouillage(iS, tq), gi = verrouillage(i, tq);
      // l'étiquette : la référence est la lecture précédente ; sans elle, la forte + l'écart ENTENDU (battement de l'enveloppe,
      // `ecarts` : écarts entre anches consécutives, en Hz) ; sans lui, l'écart de l'accrochage
      let rf = prec?.[i];
      if (rf == null && ecarts) {
        let d = 0;
        for (let q = Math.min(i, iS); q < Math.max(i, iS); q++) d += ecarts[q];
        rf = i > iS ? fS + d : fS - d;
      }
      lever(b.bons, rf ?? (gS != null && gi != null ? fS + (gi - gS) : medPond(b.bons)));
    }
    // Consensus : le plus lourd groupe de partiels à `tolCents` les uns des autres (poids k² a²), et non la médiane pondérée : les
    // partiels pairs d'une anche faible se décalent d'un cran de leur réseau (1,1 ¢ à 280 Hz) alors que les impairs sont justes ;
    // la médiane tombait sur le mauvais côté de la coupure quand ils pesaient pareil (vu au banc fidèle, anche faible à Ω < 1 Hz).
    let med = medPond(b.bons), pmax = -1;
    for (const c of b.bons) {
      const th = c.f * (2 ** (tolCents / 1200) - 1);
      let w = 0;
      for (const l of b.bons) if (Math.abs(l.f - c.f) <= th) w += l.k * l.k * l.a * l.a;
      if (w > pmax) { pmax = w; med = c.f; }
    }
    const tol = med * (2 ** (tolCents / 1200) - 1);
    let sw = 0, sf = 0;
    for (const l of b.bons) {
      if (Math.abs(l.f - med) > tol) { l.refuse = 'ecart'; continue; }
      const p = l.k * l.k * l.a * l.a;
      sw += p; sf += p * l.f;
    }
    if (!(sw > 0)) return null;
    const f = sf / sw;
    let s2 = 0, n = 0, a = 0;
    for (const l of b.bons) if (!l.refuse) { s2 += l.k * l.k * l.a * l.a * (l.f - f) ** 2; n++; a += l.a; }
    return { f, a, sigmaHz: n > 1 ? Math.sqrt(s2 / sw / (n - 1)) : NaN, n, coh: a / b.A, tLu: b.tLu, court: b.court, parPartiel: b.lus };
  });
}

// Lecteur AVEC CONTINUITÉ (le « vrai verrou ») : la dernière lecture sûre de chaque anche sert de référence à la lecture suivante
// (la levée de l'ambiguïté entière se fait autour d'elle, et non plus autour de la médiane brute des partiels, qui tombait
// d'un cran de 1/(kL) quand deux ou trois partiels se faisaient prendre par des raies de couplage : vu sur la session d'Ewen,
// Ré5, sauts de 0,2 Hz). Un saut de plus de `tolC` cents (+ `derC` ¢/s de dérive permise) n'est PAS suivi : la lecture est
// tenue à la référence (`tenu: true`) tant que le même autre résultat ne revient pas `confirme` fois de suite à `tolC` près
// (un vrai saut : soufflet inversé), alors la référence passe à la nouvelle valeur. Une lecture est « sûre » quand au moins
// `nMin` partiels sont acceptés, avec `coh` ≥ `cohMin` de l'amplitude totale.
export class SuiviLectures {
  constructor(R, { tolC = 0.1, derC = 3, confirme = 3, ageMax = 1.5, nMin = 3, cohMin = 0.6 } = {}) {
    Object.assign(this, { tolC, derC, confirme, ageMax, nMin, cohMin });
    this.prec = Array.from({ length: R }, () => null);    // { f, t }
    this.cand = Array.from({ length: R }, () => null);    // { f, n }
  }
  // Rend un tableau par anche : null, ou { ...lecture de lireFrequences, f (retenue), fBrute, tenu, sure }
  lire(vue, t, L, opts = {}) {
    const refs = this.prec.map((p) => (p && t - p.t <= this.ageMax ? p.f : null));
    const lus = lireFrequences(vue, t, L, { ...opts, prec: refs });
    return lus.map((l, i) => {
      if (!l) return null;
      const p = this.prec[i], sure = l.n >= this.nMin && l.coh >= this.cohMin;
      const out = { ...l, fBrute: l.f, tenu: false, sure };
      if (!sure) {
        if (p && t - p.t <= this.ageMax) { out.f = p.f; out.tenu = true; }
        return out;
      }
      if (!p || t - p.t > this.ageMax) { this.prec[i] = { f: l.f, t }; this.cand[i] = null; return out; }
      const dC = 1200 * Math.log2(l.f / p.f), tol = this.tolC + this.derC * Math.abs(t - p.t);
      if (Math.abs(dC) <= tol) { this.prec[i] = { f: l.f, t }; this.cand[i] = null; return out; }
      // saut : on tient la référence, sauf si le même autre résultat revient `confirme` fois
      const c = this.cand[i];
      if (c && Math.abs(1200 * Math.log2(l.f / c.f)) <= this.tolC) { c.n++; c.f = l.f; } else this.cand[i] = { f: l.f, n: 1 };
      if (this.cand[i].n >= this.confirme) { this.prec[i] = { f: l.f, t }; this.cand[i] = null; return out; }
      out.f = p.f; out.tenu = true;
      return out;
    });
  }
}

// Étiquettes d'un unisson à deux anches (8 puis 8+, 8+ plus haute par définition). Après la levée de l'ambiguïté des partiels,
// il ne reste que celle de l'étiquette : une anche FAIBLE dont tous les partiels sont dominés par la forte lit f_forte, ou
// f ± Ω. L'écart lu doit valoir le battement entendu (`omegaEnv`, enveloppe du volume, sûr à 0,05 Hz) : sinon la faible est
// déplacée d'un nombre entier de battements, le battement étant celui que lit le verrou quand la paire a été cohérente
// (`omegaVerrou`), sinon celui de l'enveloppe. Rend la paire (copiée) et `etiquette` = 0 si rien n'a bougé.
export function etiqueterPaire(lus, omegaEnv, omegaVerrou = null) {
  if (lus.length !== 2 || !lus[0] || !lus[1] || !(omegaEnv > 0)) return { lus, etiquette: 0 };
  const om = omegaVerrou ?? omegaEnv;
  const n = Math.round((lus[1].f - lus[0].f - omegaEnv) / omegaEnv);
  if (n === 0) return { lus, etiquette: 0 };
  const out = lus.map((l) => ({ ...l }));
  if (out[1].a < out[0].a) out[1].f -= n * om; else out[0].f += n * om;
  return { lus: out, etiquette: n };
}

// Accrochage par les PORTEUSES : au partiel 1 (et 2), l'indice de modulation du couplage est le plus faible, les porteuses des
// anches y dominent leurs raies latérales (session d'Ewen : Sol#4, porteuses à 0 et −2 dB, latérales à −17 et −19 dB ; au
// partiel 8 la plus forte raie est une latérale). On cherche f1 dans [centre − 1,5 Ω, centre + 0,5 Ω] (anches à f1, f1 + Ω ;
// trois anches : f1, f1 + Ω−, f1 + Ω− + Ω+) qui maximise la plus FAIBLE des puissances des porteuses (fenêtre de Hann sur
// x[i0, i1), au moins 2/Ω). Rend les fréquences de départ du verrou, ou null.
export function accrocherPorteuses(x, sr, i0, i1, centre, ecarts, { kListe = [1, 2], pasSurOmega = 40 } = {}) {
  const N = i1 - i0;
  const om = Math.min(...ecarts);
  if (!(N > (1.5 * sr) / om)) return null;
  const tot = ecarts.reduce((a, b) => a + b, 0);
  const puissance = (f) => {
    let s = 0;
    for (const k of kListe) {
      const w = (2 * Math.PI * k * f) / sr;
      let re = 0, im = 0;
      for (let n = 0; n < N; n += 2) {   // 24 kHz suffisent jusqu'au partiel 2 des notes d'accordéon
        const h = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / N);
        const v = x[i0 + n] * h;
        re += v * Math.cos(w * n); im -= v * Math.sin(w * n);
      }
      s += re * re + im * im;
    }
    return s;
  };
  let best = -Infinity, fb = null;
  for (let f1 = centre - tot / 2 - om; f1 <= centre - tot / 2 + om; f1 += om / pasSurOmega) {
    const fs = [f1];
    for (const e of ecarts) fs.push(fs.at(-1) + e);
    const p = Math.min(...fs.map(puissance));
    if (p > best) { best = p; fb = fs; }
  }
  return fb;
}

// ---------------------------------------------------------------------------------------------------------------------
// ACCROCHAGE PAR AJUSTEMENT DE RAIES (12/10/2026). Le verrou a besoin de départs justes à une fraction du battement près
// (zéros des filtres, référence de l'ambiguïté entière) : le centre de la v58 ± Ω/2 et les porteuses de Hann (3 s) se
// trompaient de 0,3 à 0,7 Ω. Ici : le spectre fenêtré (Hann) du partiel 1 de x[i0, i1) est ajusté par R raies pures PLUS
// `cote` raies de chaque côté, à écart du battement voisin (les raies latérales du couplage et de la fuite de la voisine :
// les oublier tirait les porteuses de 0,14 à 0,29 Ω, vu au banc) ; amplitudes complexes par moindres carrés, fréquences par
// Levenberg-Marquardt (variables projetées). La fenêtre de Hann est modélisée exactement (noyau de Dirichlet).
// Rend { f (Hz, croissants), omega (Hz, écart moyen), E (résidu relatif, 0 = parfait) } ou null.
export function accrocherRaies(x, sr, i0, i1, f0, { cote = 1, iters = 30, k = 1, origine = i0, derives = [-3, -2, -1, 0, 1, 2, 3], libres = [], departs = [], omega: omegaAttendu = null, tolOmega = 0.15, chercherEtrangeres = false, seuilE = 2e-3, gainEtr = 0.5, seuilEtrDb = -30, cache = null, deriveDepart = null } = {}) {
  const R = f0.length;
  if (R < 2) return null;
  const pas = 2, fe0 = sr / pas, Ne0 = Math.floor((i1 - i0) / pas);
  if (Ne0 < fe0) return null;
  const M = Math.max(1, Math.floor(fe0 / DECIM_HZ));   // décimation après la démodulation : la bande lue fait ± 10 Hz, 24 kHz n'en ont pas besoin
  const om0 = Math.min(...f0.slice(1).map((f, j) => f - f0[j]));
  if (!(om0 > 0)) return null;
  const lo = Math.min(...f0), hi = Math.max(...f0);
  const B = Math.max(2.5 * om0, 3), c = (k * (lo + hi)) / 2, half = (k * (hi - lo)) / 2 + B;
  // signal démodulé à c, deux boîtes de longueur M, décimé par M (la fenêtre de Hann se pose ensuite, sur le signal décimé)
  const { zr, zi } = demodulerDecimer(x, i0, Ne0, pas, fe0, c, M);
  const Ne = zr.length, fe = fe0 / M, T = Ne / fe;
  // spectre aux bins (pas df) de la bande, après une dérive commune `d` (¢/s : la pression du soufflet qui monte ou descend,
  // toutes les raies glissent du même rapport ; vu au banc : 1 ¢/s sur 3 s déplace les raies de 0,6 Hz à 370 Hz, de l'ordre
  // du battement) compensée par un glissando de phase -π g (t − T/2)², g = c d / 1731 Hz/s.
  const spectre = (d, df) => {
    const cle = cache ? `${k}|${c}|${half}|${i0}|${i1}|${d}|${df}` : null;   // le même spectre sert l'ajustement contraint, le libre et le suivant
    if (cle && cache.has(cle)) return cache.get(cle);
    const nb = Math.ceil((2 * half) / df), fb = new Float64Array(nb), Sr = new Float64Array(nb), Si = new Float64Array(nb);
    const wr = new Float64Array(Ne), wi = new Float64Array(Ne), g = (c * d) / 1731.234;
    for (let n = 0; n < Ne; n++) {
      const h = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / Ne);
      if (d) { const tt = n / fe - T / 2, a = -Math.PI * g * tt * tt, cc = Math.cos(a), ss = Math.sin(a); wr[n] = h * (zr[n] * cc - zi[n] * ss); wi[n] = h * (zr[n] * ss + zi[n] * cc); } else { wr[n] = h * zr[n]; wi[n] = h * zi[n]; }
    }
    let Etot = 0, Q = 0;
    for (let b = 0; b < nb; b++) {
      const dd = -half + b * df, wd = (-2 * Math.PI * dd) / fe, rr = Math.cos(wd), ri = Math.sin(wd);
      fb[b] = c + dd;
      let cr = 1, ci = 0, a = 0, e = 0;
      for (let n = 0; n < Ne; n++) {
        a += wr[n] * cr - wi[n] * ci; e += wr[n] * ci + wi[n] * cr;
        const t = cr * rr - ci * ri; ci = cr * ri + ci * rr; cr = t;
        if ((n & 4095) === 4095) { const m = Math.hypot(cr, ci); cr /= m; ci /= m; }
      }
      const hc = reponseBoite(dd, fe0, M);   // la décimation a creusé les bords de la bande : on le rend (division par la réponse exacte des deux boîtes)
      Sr[b] = a / hc; Si[b] = e / hc;
      const p = Sr[b] * Sr[b] + Si[b] * Si[b]; Etot += p; Q += p * p;
    }
    const res = { nb, fb, Sr, Si, Etot, conc: Etot > 0 ? Q / (Etot * Etot) : 0 };
    if (cle) cache.set(cle, res);
    return res;
  };
  // Σ_n e^{−j2π d n/fe} = sin(a Ne) / sin(a) e^{−j a (Ne − 1)}, a = π d / fe ; la fenêtre de Hann en est la combinaison 0,5 A − 0,25 B − 0,25 C
  // à d et d ∓ 1/T. Décalés de ∓π/Ne, B et C ont le même sin(a Ne) au signe près et leur phase est celle de A tournée de ± π (Ne − 1) / Ne :
  // 6 fonctions trigonométriques au lieu de 15 par appel (c'était le tiers du temps de la lecture d'une note), mêmes valeurs à 1e-15.
  const dl = Math.PI / Ne, gam = dl * (Ne - 1), cg = Math.cos(gam), sg = Math.sin(gam);
  const noyau = (d) => {
    const a = (Math.PI * d) / fe, sN = Math.sin(a * Ne), ph = -a * (Ne - 1), cp = Math.cos(ph), sp = Math.sin(ph);
    const terme = (aa, num, c0, s0) => {   // [Re, Im] de num / sin(aa) e^{i phase}
      if (Math.abs(aa) < 1e-12) return [Ne, 0];
      const s = num / Math.sin(aa);
      return [s * c0, s * s0];
    };
    const A = terme(a, sN, cp, sp);
    const B = terme(a - dl, -sN, cp * cg - sp * sg, sp * cg + cp * sg);   // phase de A + γ
    const C = terme(a + dl, -sN, cp * cg + sp * sg, sp * cg - cp * sg);   // phase de A − γ
    return [0.5 * A[0] - 0.25 * B[0] - 0.25 * C[0], 0.5 * A[1] - 0.25 * B[1] - 0.25 * C[1]];
  };
  let lib = [...libres];
  const raies = (fr) => {
    const out = [...fr];
    for (let q = 1; q <= cote; q++) { out.push(fr[0] - q * (fr[1] - fr[0])); out.push(fr[R - 1] + q * (fr[R - 1] - fr[R - 2])); }
    for (const l of lib) out.push(l);   // raies étrangères : fréquence fixe, amplitude ajustée
    return out;
  };
  const resoudre = (A, bv, n) => {
    const M = Float64Array.from(A), v = Float64Array.from(bv);
    for (let i = 0; i < n; i++) {
      let p = i;
      for (let r = i + 1; r < n; r++) if (Math.abs(M[r * n + i]) > Math.abs(M[p * n + i])) p = r;
      if (p !== i) { for (let q = 0; q < n; q++) { const t = M[i * n + q]; M[i * n + q] = M[p * n + q]; M[p * n + q] = t; } const t = v[i]; v[i] = v[p]; v[p] = t; }
      const d = M[i * n + i] || 1e-300;
      for (let r = i + 1; r < n; r++) { const q = M[r * n + i] / d; if (!q) continue; for (let m = i; m < n; m++) M[r * n + m] -= q * M[i * n + m]; v[r] -= q * v[i]; }
    }
    const s = new Float64Array(n);
    for (let i = n - 1; i >= 0; i--) { let t = v[i]; for (let m = i + 1; m < n; m++) t -= M[i * n + m] * s[m]; s[i] = t / (M[i * n + i] || 1e-300); }
    return s;
  };
  // ajustement des raies sur le spectre `sp` (dérive d) : Levenberg-Marquardt sur les fréquences, moindres carrés sur les amplitudes
  const ajuster = (sp, f00 = f0, seul = false) => {
    const { nb, fb, Sr, Si } = sp;
    const residu = (fr0) => {
      const fr = raies(fr0), Rl = fr.length, M = 2 * Rl, col = [];
      for (let r = 0; r < Rl; r++) {
        const u = new Float64Array(2 * nb), v = new Float64Array(2 * nb);
        for (let b = 0; b < nb; b++) { const h = noyau(fb[b] - k * fr[r]); u[2 * b] = h[0]; u[2 * b + 1] = h[1]; v[2 * b] = -h[1]; v[2 * b + 1] = h[0]; }
        col.push(u, v);
      }
      const y = new Float64Array(2 * nb);
      for (let b = 0; b < nb; b++) { y[2 * b] = Sr[b]; y[2 * b + 1] = Si[b]; }
      const A = new Float64Array(M * M), g = new Float64Array(M);
      for (let a = 0; a < M; a++) {
        for (let b = a; b < M; b++) { let s = 0; for (let q = 0; q < 2 * nb; q++) s += col[a][q] * col[b][q]; A[a * M + b] = s; A[b * M + a] = s; }
        let s = 0; for (let q = 0; q < 2 * nb; q++) s += col[a][q] * y[q]; g[a] = s;
      }
      for (let a = 0; a < M; a++) A[a * M + a] *= 1 + 1e-9;
      const sol = resoudre(A, g, M), res = new Float64Array(2 * nb);
      let E = 0;
      for (let q = 0; q < 2 * nb; q++) { let m = 0; for (let a = 0; a < M; a++) m += col[a][q] * sol[a]; res[q] = y[q] - m; E += res[q] * res[q]; }
      return { res, E, sol, fr };
    };
    if (seul) return { residu };
    let fr = [...f00], lam = 1e-3, cur = residu(fr);
    for (let it = 0; it < iters; it++) {
      const h = 1e-3 / T;
      const J = fr.map((_, r) => { const g = [...fr]; g[r] += h; const rr = residu(g).res; return Array.from(rr, (v, q) => (v - cur.res[q]) / h); });
      const Mx = new Float64Array(R * R), gv = new Float64Array(R);
      for (let a = 0; a < R; a++) {
        for (let b = a; b < R; b++) { let s = 0; for (let q = 0; q < cur.res.length; q++) s += J[a][q] * J[b][q]; Mx[a * R + b] = s; Mx[b * R + a] = s; }
        let s = 0; for (let q = 0; q < cur.res.length; q++) s += J[a][q] * cur.res[q]; gv[a] = -s;
      }
      let ok = false;
      for (let essai = 0; essai < 8; essai++) {
        const M2 = Float64Array.from(Mx);
        for (let a = 0; a < R; a++) M2[a * R + a] *= 1 + lam;
        const d = resoudre(M2, gv, R), cand = fr.map((f, r) => f + Math.max(-0.5 * om0, Math.min(0.5 * om0, d[r]))), rn = residu(cand);
        if (rn.E < cur.E) { const gain = cur.E - rn.E; fr = cand; cur = rn; lam = Math.max(1e-6, lam / 5); ok = true; if (gain < 1e-10 * cur.E) it = iters; break; }
        lam *= 5;
      }
      if (!ok) break;
    }
    return { fr, E: sp.Etot > 0 ? cur.E / sp.Etot : 1, cur, sp, residu };
  };
  // d'abord sans dérive ; si le résidu reste gros, on essaie les dérives de la grille et on garde la meilleure SI elle divise le
  // résidu par 2 au moins (sinon la dérive inventée déplacerait des raies stationnaires : vu au banc, 17 ¢ de faux sur des cas propres)
  const df = 1 / (4 * T);
  const sp0 = spectre(0, df);
  // le battement attendu (enveloppe) borne l'écart des raies : sans cela l'ajustement trouve parfois un peigne de pas moitié (vu au banc)
  const gapOk = (r) => !(omegaAttendu > 0) || Math.abs((r.fr.at(-1) - r.fr[0]) / (R - 1) - omegaAttendu) <= tolOmega * omegaAttendu;
  let meilleur = null;
  // Balayage du départ : un départ à plus de quelques cases (1/T) des raies reste coincé dans un minimum local (vu au banc de plage, A5 à A6,
  // battements de 2 à 3 Hz : un centroïde à 0,16 Ω du bon peigne laissait 98 % du spectre inexpliqué). Le peigne de départ glisse de ± 0,6 Ω par pas
  // de 1/(3T), moindres carrés sur les amplitudes seuls ; le meilleur résidu devient un départ de plus (il ne peut que baisser le résidu final).
  const departsBalayes = [];
  {
    const { residu: res0 } = ajuster(sp0, f0, true), pasB = 1 / (3 * T * k), gapB = Math.abs(f0[R - 1] - f0[0]) / Math.max(1, R - 1);
    let bestE = Infinity, bestD = 0;
    for (let dlt = -0.6 * gapB; dlt <= 0.6 * gapB; dlt += pasB) {
      const e = res0(f0.map((f) => f + dlt)).E;
      if (e < bestE) { bestE = e; bestD = dlt; }
    }
    if (Math.abs(bestD) > 2 * pasB) departsBalayes.push(f0.map((f) => f + bestD));
  }
  for (const dep of [f0, ...departsBalayes, ...departs]) {   // autres départs (centre décalé d'un demi-battement) : le meilleur résidu gagne
    const r = ajuster(sp0, dep);
    if (gapOk(r) && (!meilleur || r.E < meilleur.E)) meilleur = { ...r, derive: 0 };
  }
  if (!meilleur) return null;
  // Dérive de la plage (pente du centroïde, ¢/s) : à 1,3 kHz, 0,1 ¢/s font 0,7 Hz en 9 s, six cases de 1/T : les raies se mélangent, le résidu monte à 0,25
  // et la note est refusée (banc de plage). Recherche du minimum du résidu autour de la pente donnée (section d'or, résidu des moindres carrés sur
  // les amplitudes seuls), puis ajustement complet à la meilleure dérive ; gardée si elle baisse le résidu d'un cinquième.
  if (deriveDepart != null && Math.abs(deriveDepart) <= 3) {
    const evalE = (d) => { const s = spectre(d, df), { residu: rs } = ajuster(s, meilleur.fr, true); return rs(meilleur.fr).E / (s.Etot || 1); };
    let a = deriveDepart - 0.3, b = deriveDepart + 0.3;
    const g = 0.381966;
    let c1 = a + g * (b - a), c2 = b - g * (b - a), e1 = evalE(c1), e2 = evalE(c2);
    for (let it = 0; it < 7; it++) {
      if (e1 < e2) { b = c2; c2 = c1; e2 = e1; c1 = a + g * (b - a); e1 = evalE(c1); } else { a = c1; c1 = c2; e1 = e2; c2 = b - g * (b - a); e2 = evalE(c2); }
    }
    const dBest = e1 < e2 ? c1 : c2;
    if (Math.abs(dBest) > 0.01) {
      const r = ajuster(spectre(dBest, df), meilleur.fr);
      if (r.E < 0.8 * meilleur.E) meilleur = { ...r, derive: dBest };
    }
  }
  if (meilleur.E > 1e-3) {
    for (const d of derives) {
      if (!d) continue;
      const r = ajuster(spectre(d, df), meilleur.fr);
      if (r.E < 0.5 * meilleur.E) meilleur = { ...r, derive: d };
    }
  }
  // RAIE ÉTRANGÈRE (audit réel, recommandation 3) : une raie hors du peigne (une autre anche qui parle faiblement, −9 à −22 dB, à
  // 0,13-0,5 Hz d'une porteuse) capture une voie. Si le résidu reste gros, on balaie sa fréquence (le résidu après ajustement,
  // aux pas de 1/(8T), sur la bande) en refaisant les amplitudes par moindres carrés ; on la garde si elle divise le résidu par
  // 2 (`gainEtr`) et si elle vaut plus que `seuilEtrDb` sous la porteuse la plus forte. Elle entre alors comme raie libre (fréquence
  // fixe, amplitude ajustée) et les porteuses sont réajustées avec elle.
  const etrangeres = [];
  if (chercherEtrangeres) {
    for (let tour = 0; tour < 2 && meilleur.E > seuilE; tour++) {
      const { fb, nb } = meilleur.sp, fr = meilleur.fr;
      const lo = fb[0] / k, hi = fb[nb - 1] / k, pasF = 1 / (8 * T * k);
      const pasPeigne = (fr[fr.length - 1] - fr[0]) / (R - 1), zone = 0.07 * Math.abs(pasPeigne);
      const bal = [];
      for (let fe = lo; fe <= hi; fe += pasF) {
        // une raie sur le peigne (f + m Ω) est une latérale ou une porteuse, pas une étrangère
        const m = (fe - fr[0]) / pasPeigne;
        if (Math.abs(m - Math.round(m)) * Math.abs(pasPeigne) < zone) { bal.push({ fe, E: Infinity }); continue; }
        lib = [...etrangeres, fe];
        bal.push({ fe, E: meilleur.residu(fr).E });
      }
      // les trois meilleurs sommets (minima locaux du résidu à porteuses figées) sont ajustés avec les porteuses libres : une étrangère
      // dans le lobe d'une porteuse (0,13 Hz à T = 9 s) ne fait pas baisser le résidu tant que les porteuses n'ont pas bougé
      const minima = bal.map((v2, q) => ({ ...v2, q })).filter((v2, q) => Number.isFinite(v2.E) && (q === 0 || v2.E <= bal[q - 1].E) && (q === bal.length - 1 || v2.E <= bal[q + 1].E)).sort((p, q) => p.E - q.E).slice(0, 3);
      let choix = null;
      for (const c of minima) {
        let fe = c.fe;
        const q = c.q;
        if (q > 0 && q < bal.length - 1) {   // affinage : parabole sur les trois pas autour du minimum
          const e0 = bal[q - 1].E, e1 = bal[q].E, e2 = bal[q + 1].E, den = e0 - 2 * e1 + e2;
          if (Number.isFinite(e0 + e2) && den > 0) fe += (pasF * (e0 - e2)) / (2 * den);
        }
        lib = [...etrangeres, fe];
        const r2 = ajuster(meilleur.sp, fr);
        const sol = r2.cur.sol, nl = sol.length / 2, amp = (u) => Math.hypot(sol[2 * u], sol[2 * u + 1]);
        let aMax = 0;
        for (let u = 0; u < nl - lib.length; u++) aMax = Math.max(aMax, amp(u));
        const dB = 20 * Math.log10(amp(nl - 1) / aMax);
        if (dB > seuilEtrDb && r2.E < gainEtr * meilleur.E && (!choix || r2.E < choix.r2.E)) choix = { r2, fe, dB };
      }
      if (!choix) { lib = [...etrangeres]; break; }
      lib = [...etrangeres, choix.fe];
      etrangeres.push({ f: choix.fe, dB: choix.dB });
      meilleur = { ...choix.r2, derive: meilleur.derive };
    }
  }
  const { fr, E, derive } = meilleur;
  // amplitudes des raies du peigne (porteuses, latérales) et des étrangères : [{ f (Hz au partiel 1), a, role }]
  const dtOrig = (i0 + (Ne0 * pas) / 2 - origine) / sr, e = derive / 1731.234;
  const sol = meilleur.cur.sol, ls = raies(fr), lignes = ls.map((f, q) => ({ f: f * (1 - e * dtOrig), a: Math.hypot(sol[2 * q], sol[2 * q + 1]), role: q < R ? 'porteuse' : q < ls.length - lib.length ? 'laterale' : 'etrangere' }));
  // fréquences à l'instant `origine` (la dérive est lue au centre de la fenêtre)
  const tri = [...fr].sort((p, q) => p - q).map((f) => f * (1 - e * dtOrig));
  return { f: tri, omega: (tri.at(-1) - tri[0]) / (R - 1), E, derive, lignes, etrangeres: etrangeres.map((q) => ({ f: q.f * (1 - e * dtOrig), dB: q.dB })) };
}

// ---------------------------------------------------------------------------------------------------------------------
// PLAGE STABLE (12/10/2026, audit réel de la session du 11/10). L'attaque d'une note d'accordéon monte de 12 à 16 ¢ pendant 1 à
// 2,6 s avant de se tenir (9 notes sur 23) : un accrochage fait dans cette excursion se trompe de 5 à 11 ¢, et le verrou se verrouille
// alors un battement trop haut. On ne regarde donc que la plus longue suite de la note où la hauteur se tient.
// Centroïde (¢ rapporté à `fc`) du partiel `k` dans des fenêtres de Hann de W s, pas `hop` s : la moyenne de puissance sur ±B Hz
// ne dépend pas de la phase du battement (W ≥ 0,4 s mélange les deux anches). Plus longue suite de fenêtres qui reste à ±tol ¢
// d'une droite, dérive totale ≤ 3 tol. Rend { i0, i1 (échantillons), t0, t1 (s), derive (¢/s), agitation (¢ rms), k } ou null.
export function plageStable(x, sr, i0, i1, fc, { W: W0 = null, hop = 0.1, tol = 3, kMax = 4, B: B0 = 8, omega = 0, garde = null } = {}) {
  // Fenêtre : un nombre ENTIER de battements quand on connaît Ω (la modulation de phase du tirage des deux anches fait osciller le
  // centroïde au rythme du battement, de ± β Ω / f × 1731 ¢ : 5 ¢ à 400 Hz pour Ω = 1,9 Hz et β = 0,9 ; une fenêtre d'un battement
  // l'annule), au moins 0,4 s, au plus 1,5 s.
  const W = W0 ?? (omega > 0 ? Math.min(1.5, Math.max(1, Math.ceil(0.4 * omega)) / omega) : 0.4);
  const pas = 2, fe = sr / pas, M = Math.max(1, Math.floor(fe / DECIM_HZ)), fe2 = fe / M, Nw2 = Math.floor(W * fe2), nW = Math.floor(((i1 - i0) / sr - W) / hop) + 1;
  if (nW < 3) return null;
  const centroides = (k) => {
    // la bande du partiel k contient les deux anches (k Ω d'écart), leurs latérales ET l'excursion de l'attaque (± 25 ¢ : au partiel 3 d'un
    // Do6, 25 ¢ font 46 Hz ; une bande fixe de 8 Hz perdait la raie dès 5 ¢ et le centroïde restait « stable » sur du bruit)
    const B = Math.min(0.35 * fe2, Math.max(B0, (k * fc * 25) / 1731.234) + k * omega);
    const c = k * fc, df = 1 / (2 * W), nb = Math.ceil((2 * B) / df);
    const cs = new Float64Array(nW), pw = new Float64Array(nW);
    // une seule démodulation pour toute la note (les fenêtres se recouvrent de 80 à 95 %), décimée à 1 kHz
    const dm = demodulerDecimer(x, i0, Math.floor((i1 - i0) / pas), pas, fe, c, M);
    const han = new Float64Array(Nw2);
    const comp = new Float64Array(nb);   // réponse des deux boîtes à chaque bin : les bords de la bande sont rendus
    for (let b = 0; b < nb; b++) comp[b] = reponseBoite(-B + b * df, fe, M);
    // fenêtre quasi rectangulaire (Tukey, 5 % de chaque côté) : sur un nombre ENTIER de battements, la modulation de fréquence du tirage
    // des deux anches (± β Ω / f × 1731 ¢, 5 ¢ à 400 Hz pour Ω = 1,9 Hz et β = 0,9) s'annule dans le centroïde ; la fenêtre de Hann, dont
    // le carré pondère inégalement la période, la laissait osciller de ± 4 ¢ et la plage cassait. Le bord net sert aussi à l'attaque.
    const tap = Math.max(1, Math.floor(0.05 * Nw2));
    for (let n = 0; n < Nw2; n++) han[n] = n < tap ? 0.5 - 0.5 * Math.cos((Math.PI * n) / tap) : n >= Nw2 - tap ? 0.5 - 0.5 * Math.cos((Math.PI * (Nw2 - 1 - n)) / tap) : 1;
    const zr = new Float64Array(Nw2), zi = new Float64Array(Nw2);
    for (let w = 0; w < nW; w++) {
      // la sortie q de la cascade parle des échantillons qM … qM + M − 1 : le début de la fenêtre w (w hop s) est à q = (w hop fe − (M − 1)) / M
      const q0 = Math.max(0, Math.round((w * hop * fe - (M - 1)) / M));
      for (let n = 0; n < Nw2; n++) { const q = q0 + n; zr[n] = q < dm.zr.length ? dm.zr[q] * han[n] : 0; zi[n] = q < dm.zr.length ? dm.zi[q] * han[n] : 0; }
      let S = 0, Sd = 0;
      for (let b = 0; b < nb; b++) {
        const d = -B + b * df, th = (-2 * Math.PI * d) / fe2, rr = Math.cos(th), ri = Math.sin(th);
        let cr = 1, ci = 0, a = 0, e = 0;
        for (let n = 0; n < Nw2; n++) {
          a += zr[n] * cr - zi[n] * ci; e += zr[n] * ci + zi[n] * cr;
          const t = cr * rr - ci * ri; ci = cr * ri + ci * rr; cr = t;
        }
        a /= comp[b]; e /= comp[b];
        const pp = a * a + e * e; S += pp; Sd += pp * d;
      }
      pw[w] = S; cs[w] = S > 0 ? Sd / S : 0;
    }
    return { cs, pw, c };
  };
  // partiel le plus fort (k ≤ kMax) sur la note entière : sa puissance moyenne
  let meil = null;
  for (let k = 1; k <= kMax; k++) {
    if (k * fc > 0.45 * sr) break;
    const r = centroides(k), m = r.pw.reduce((a, b) => a + b, 0);
    if (!meil || m > meil.m) meil = { ...r, m, k };
  }
  if (!meil) return null;
  const cts = Array.from(meil.cs, (d) => 1200 * Math.log2((meil.c + d) / meil.c));   // ¢ rapportés à k fc
  const nS = nW, extra = 0;
  const pwMax = Math.max(...meil.pw);
  const ok = (a, b) => {   // fenêtres a..b incluses : droite des moindres carrés, écart maximal et dérive totale
    const n = b - a + 1;
    let sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (let w = a; w <= b; w++) { const t = w * hop; sx += t; sy += cts[w]; sxx += t * t; sxy += t * cts[w]; }
    const den = n * sxx - sx * sx, pente = den > 0 ? (n * sxy - sx * sy) / den : 0, orig = (sy - pente * sx) / n;
    let max = 0, ss = 0;
    for (let w = a; w <= b; w++) { const e = cts[w] - (orig + pente * w * hop); max = Math.max(max, Math.abs(e)); ss += e * e; }
    return { bon: max <= tol && Math.abs(pente) * (n - 1) * hop <= 2 * tol, pente, orig, rms: Math.sqrt(ss / n) };
  };
  let best = null;
  for (let a = 0; a < nS; a++) {
    if (meil.pw[a] < 0.01 * pwMax) continue;   // silence : pas une plage
    let dernier = null;
    for (let b = a + 2; b < nS; b++) {
      if (meil.pw[b] < 0.01 * pwMax) break;
      const r = ok(a, b);
      if (!r.bon) break;
      dernier = { a, b, ...r };
    }
    if (dernier && (!best || dernier.b - dernier.a > best.b - best.a)) best = dernier;
  }
  if (!best) return null;
  plageStable.derniere = { cts, pw: meil.pw, k: meil.k };   // diagnostic de banc
  // la plage couvre les fenêtres a..b : de a·hop à b·hop + W
  // marge de garde : la première fenêtre acceptée peut encore toucher la fin de l'excursion (un dixième de sa largeur, sous la
  // tolérance) ; on n'en garde que ce qui est à `garde` s de ce bord, sauf contre le début ou la fin de la note elle-même
  const fin = (i1 - i0) / sr;
  let t0 = best.a * hop, t1 = best.b * hop + extra + W;
  // Une fenêtre acceptée peut contenir jusqu'à tol / c de transitoire (c : 12 à 16 ¢ d'excursion) : le quart de sa largeur ; la rampe de
  // l'excursion dure encore 0,15 s. Le début de la partie sûre est donc à W/4 + 0,15 s du début de la première fenêtre (vu au banc :
  // la plage commençait dans la fin de l'excursion, 0,6 ¢ de faux).
  const gd = garde ?? 0.25 * W + 0.15;
  if (best.a > 0) t0 += gd;
  if (t1 < fin - hop) t1 -= gd;
  if (t1 - t0 < 3 * hop) return null;
  let cm = 0;
  for (let w = best.a; w <= best.b; w++) cm += meil.cs[w];
  const fCentre = (meil.c + cm / (best.b - best.a + 1)) / meil.k;   // centroïde de puissance du peigne au partiel 1 (Hz) : entre les deux anches
  return { droite: { pente: best.pente, orig: best.orig, W, hop, a: best.a }, fCentre, i0: i0 + Math.round(t0 * sr), i1: i0 + Math.round(t1 * sr), t0: i0 / sr + t0, t1: i0 / sr + t1, derive: best.pente, agitation: best.rms, k: meil.k };
}

// Accrochage par ajustement de raies sur la seule plage stable de la note [i0, i1). Refus (null) si la plage fait moins de
// max(2 s, 2/Ω) : anches à moins de 0,8 ¢ (Ω·T < 2), dérive ou agitation trop fortes ou note trop courte, sans lecture inventée.
// `omega` : battement attendu (Hz, enveloppe ou v58). Rend { ...accrocherRaies, plage } ou null.
export function accrocherStable(x, sr, i0, i1, f0, { omega, tol = 3, derMax = 0.5, agitMax = 2, ...opts } = {}) {
  const fc = f0.reduce((a, b) => a + b, 0) / f0.length;
  const plage = plageStable(x, sr, i0, i1, fc, { tol });
  if (!plage) return null;
  const T = (plage.i1 - plage.i0) / sr;
  if (T < Math.max(2, omega ? 2 / omega : 0)) return null;
  if (Math.abs(plage.derive) > derMax || plage.agitation > agitMax) return null;
  const r = accrocherRaies(x, sr, plage.i0, plage.i1, f0, opts);
  return r ? { ...r, plage } : null;
}
