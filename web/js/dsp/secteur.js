// Retirer le ronflement du secteur du signal, avant le moteur et le verrou (v62, Ewen, 14/10/2026 :
// « il faut virer le 50 Hz »). Le ronflement est une somme de sinusoïdes exactes aux multiples de la
// fréquence du secteur (50 ou 60 Hz, à ±0,1 Hz près) : on les estime et on les soustrait, sans filtrer
// de bande, donc sans toucher aux anches qui en sont à plus de quelques dixièmes de hertz.
//
// Méthode : un annuleur adaptatif de sinusoïdes (LMS à deux poids, cosinus et sinus, par harmonique).
// Chaque harmonique est un cran de largeur LARGEUR_HZ (0,3 Hz à -3 dB) qui SUIT l'amplitude et la
// phase du ronflement ; la fréquence du secteur est estimée finement (pas de 0,01 Hz) sur la fenêtre
// de 2 s du contrôle de la prise (prise.js) et le cran la suit. Un partiel d'anche à plus de ~1 Hz
// d'une harmonique n'est ni atténué de plus de quelques centièmes de dB ni déphasé en fonction du temps ;
// un partiel plus près est abîmé : l'interface le dit (`secteurProche`, ui/mesure.js) au lieu de le
// donner pour sûr.
//
// Module pur : tourne dans le Worker et sous Node (test/secteur.test.mjs).

export const LARGEUR_HZ = 0.3;
export const PROCHE_HZ = 1.0;        // un partiel à moins de 1 Hz d'une harmonique est « proche »
export const HARMONIQUES_MAX = 24;
export const F_MAX_HZ = 1500;        // au-dessus, le ronflement n'est plus qu'un bruit de convertisseur

// Affine la fréquence du secteur : cherche f dans [base - 0,35, base + 0,35] qui maximise la
// puissance des 3 premières harmoniques (fenêtre de Hann, Goertzel), pas de 0,05 puis de 0,01 Hz.
export function affinerSecteur(x, sr, base = 50) {
  const N = x.length;
  const hann = new Float32Array(N);
  for (let i = 0; i < N; i++) hann[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N);
  const puiss = (f) => {
    if (f >= sr / 2 - 10) return 0;
    const w = 2 * Math.PI * f / sr, c = 2 * Math.cos(w);
    let s1 = 0, s2 = 0;
    for (let i = 0; i < N; i++) { const v = x[i] * hann[i] + c * s1 - s2; s2 = s1; s1 = v; }
    const re = s1 - s2 * Math.cos(w), im = s2 * Math.sin(w);
    return re * re + im * im;
  };
  const score = (f) => puiss(f) + puiss(2 * f) + puiss(3 * f);
  let meilleur = base, sm = -1;
  for (let f = base - 0.35; f <= base + 0.3501; f += 0.05) { const s = score(f); if (s > sm) { sm = s; meilleur = f; } }
  const centre = meilleur;
  for (let f = centre - 0.05; f <= centre + 0.0501; f += 0.01) { const s = score(f); if (s > sm) { sm = s; meilleur = f; } }
  return Math.round(meilleur * 100) / 100;
}

export class RetireSecteur {
  constructor(sr, largeurHz = LARGEUR_HZ) {
    this.sr = sr;
    this.mu = Math.PI * largeurHz / sr * 2;   // pas du LMS : largeur du cran (étalonné par test/secteur.test.mjs)
    this.f0 = 0;
    this.h = 0;
    this.actif = false;
    this.phase = [];   // phase de chaque référence (rad)
    this.wc = []; this.ws = [];
    this.cos = []; this.sin = [];   // phaseurs de rotation
    this.rc = []; this.rs = [];
  }

  // Fréquence du secteur et nombre d'harmoniques à retirer. Les poids déjà appris sont gardés quand
  // la fréquence ne change que de quelques centièmes.
  regler(f0, harmoniques) {
    const H = Math.max(1, Math.min(HARMONIQUES_MAX, harmoniques, Math.floor(Math.min(F_MAX_HZ, this.sr / 2 - 20) / f0)));
    const change = Math.abs(f0 - this.f0) > 0.4;
    this.f0 = f0;
    for (let k = this.h; k < H; k++) {
      this.phase[k] = 0; this.wc[k] = 0; this.ws[k] = 0;
    }
    if (change) for (let k = 0; k < H; k++) { this.wc[k] = 0; this.ws[k] = 0; }
    this.h = H;
    for (let k = 0; k < H; k++) {
      const w = 2 * Math.PI * (k + 1) * f0 / this.sr;
      this.cos[k] = Math.cos(w); this.sin[k] = Math.sin(w);
      if (this.rc[k] === undefined || this.rc[k] === null) { this.rc[k] = Math.cos(this.phase[k]); this.rs[k] = Math.sin(this.phase[k]); }
    }
    this.actif = true;
  }

  arreter() { this.actif = false; }

  // Rend le bloc sans ronflement (nouveau tableau). Hors service : le bloc lui-même.
  traiter(x) {
    if (!this.actif) return x;
    const n = x.length, H = this.h, mu = this.mu;
    const y = new Float32Array(n);
    const { wc, ws, rc, rs, cos, sin } = this;
    for (let i = 0; i < n; i++) {
      let pred = 0;
      for (let k = 0; k < H; k++) pred += wc[k] * rc[k] + ws[k] * rs[k];
      const e = x[i] - pred;
      y[i] = e;
      const g = mu * e;
      for (let k = 0; k < H; k++) {
        wc[k] += g * rc[k]; ws[k] += g * rs[k];
        // le phaseur tourne de h × f0 par échantillon
        const c = rc[k] * cos[k] - rs[k] * sin[k];
        const s = rc[k] * sin[k] + rs[k] * cos[k];
        rc[k] = c; rs[k] = s;
      }
    }
    // renormalise les phaseurs (l'erreur d'arrondi les fait dériver)
    for (let k = 0; k < H; k++) { const m = Math.hypot(rc[k], rs[k]) || 1; rc[k] /= m; rs[k] /= m; }
    return y;
  }

  // Les fréquences que le cran retire (Hz), pour dire quels partiels en sont proches.
  frequences() {
    return this.actif ? Array.from({ length: this.h }, (_, k) => (k + 1) * this.f0) : [];
  }
}

// Un partiel à `hz` est-il à moins de PROCHE_HZ d'une harmonique retirée ?
export function partielProche(hz, frequences) {
  if (!Number.isFinite(hz)) return false;
  return frequences.some((f) => Math.abs(hz - f) < PROCHE_HZ);
}
