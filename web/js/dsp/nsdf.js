// Détection de hauteur par la méthode McLeod (MPM) : autocorrélation
// normalisée (NSDF), d'après McLeod & Wyvill, « A Smarter Way to Find
// Pitch » (2005). Étage temporel complémentaire de la détection grossière :
// robuste aux erreurs d'octave, faible latence (quelques périodes), idéal
// pour suivre une hauteur en mouvement (glissando, chant). Ne remplace pas
// la mesure fine (zoom hétérodyne, < 0,001 Hz) ni la séparation polyphonique
// des anches — la NSDF est monophonique par nature.
//
//   NSDF(τ) = 2·Σ x[j]·x[j+τ] / Σ (x[j]² + x[j+τ]²)   ∈ [−1, 1]
//
// Le numérateur (autocorrélation linéaire) est calculé par FFT en O(W log W) ;
// le dénominateur par sommes préfixes en O(W). Choix du pic : premier
// « maximum-clé » dépassant un seuil relatif au maximum global (règle
// anti-octave de McLeod), affiné par interpolation parabolique.

import { FFT } from './fft.js';

export class NsdfTracker {
  constructor(sampleRate, opts = {}) {
    this.sr = sampleRate;
    this.win = opts.win ?? 4096;            // ~85 ms à 48 kHz
    this.fMin = opts.fMin ?? 40;            // hauteur jouée (Hz)
    this.fMax = opts.fMax ?? 2200;
    this.threshold = opts.threshold ?? 0.9; // seuil relatif au max (McLeod)
    this.clarityMin = opts.clarityMin ?? 0.6;
    let n = 1;
    while (n < this.win * 2) n <<= 1;       // zéro-remplissage → autocorr linéaire
    this.fftSize = n;
    this.fft = FFT.get(n);
    this.re = new Float64Array(n);
    this.im = new Float64Array(n);
    this.buf = new Float32Array(this.win);
    this.nsdf = new Float32Array(this.win >> 1);
    this.prefix = new Float64Array(this.win + 1); // sommes préfixes des carrés
    // Tampons de maxima-clés réutilisés (aucune allocation par estimation).
    this.keyLag = new Int32Array(this.win >> 1);
    this.keyVal = new Float32Array(this.win >> 1);
  }

  // Estime f0 à partir des `win` derniers échantillons d'un ring buffer
  // (ring de taille `size`, `wpos` = prochaine position d'écriture).
  estimateFromRing(ring, wpos, size) {
    const W = this.win;
    if (size < W) return null;
    const buf = this.buf;
    const start = (((wpos - W) % size) + size) % size;
    for (let i = 0; i < W; i++) buf[i] = ring[(start + i) % size];
    return this.estimate(buf);
  }

  estimate(x) {
    const W = this.win;
    const { re, im, fftSize } = this;
    // Retrait de la composante continue (le DC fausse l'autocorrélation).
    let mean = 0;
    for (let i = 0; i < W; i++) mean += x[i];
    mean /= W;
    for (let i = 0; i < W; i++) { re[i] = x[i] - mean; im[i] = 0; }
    re.fill(0, W); im.fill(0, W);
    // Autocorrélation linéaire : acf = IFFT(|FFT(x)|²).
    this.fft.transform(re, im);
    for (let i = 0; i < fftSize; i++) {
      re[i] = re[i] * re[i] + im[i] * im[i];
      im[i] = 0;
    }
    // IFFT par conjugaison : IFFT(P) = conj(FFT(conj(P)))/N ; P étant réel,
    // la partie réelle du résultat suffit (acf réelle).
    this.fft.transform(re, im);
    const invN = 1 / fftSize;
    // acf[τ] = re[τ] * invN.

    // Sommes préfixes des carrés (signal centré) pour le dénominateur m'(τ).
    const pre = this.prefix;
    pre[0] = 0;
    for (let i = 0; i < W; i++) {
      const v = x[i] - mean;
      pre[i + 1] = pre[i] + v * v;
    }
    const SS = pre[W];
    const nsdf = this.nsdf;
    const nLag = W >> 1;
    for (let tau = 0; tau < nLag; tau++) {
      const r = re[tau] * invN;
      // m'(τ) = (SS − Σ_{0..τ-1}) + (SS − Σ_{W-τ..W-1}) = 2·SS − tête − queue.
      const head = pre[tau];
      const tail = SS - pre[W - tau];
      const m = 2 * SS - head - tail;
      nsdf[tau] = m > 1e-12 ? (2 * r) / m : 0;
    }
    return this.pick(nsdf, nLag);
  }

  pick(nsdf, nLag) {
    const tauMin = Math.max(2, Math.floor(this.sr / this.fMax));
    const tauMax = Math.min(nLag - 2, Math.ceil(this.sr / this.fMin));
    // Sauter la crête initiale (NSDF(0)=1) : avancer jusqu'au premier zéro.
    let tau = 1;
    while (tau < tauMax && nsdf[tau] > 0) tau++;
    // Maxima-clés : le plus haut entre chaque paire de passages à zéro
    // positifs. Stockés dans des tampons réutilisés (pas d'allocation).
    const keyLag = this.keyLag, keyVal = this.keyVal;
    let nk = 0, bestG = 0;
    let curVal = -Infinity, curLag = -1, inPos = false;
    for (; tau <= tauMax; tau++) {
      const v = nsdf[tau];
      if (v > 0) {
        if (!inPos) { inPos = true; curVal = -Infinity; curLag = -1; }
        if (v > curVal) { curVal = v; curLag = tau; }
      } else if (inPos) {
        if (curLag >= 0) { keyLag[nk] = curLag; keyVal[nk] = curVal; nk++; if (curVal > bestG) bestG = curVal; }
        inPos = false;
      }
    }
    if (inPos && curLag >= 0) { keyLag[nk] = curLag; keyVal[nk] = curVal; nk++; if (curVal > bestG) bestG = curVal; }
    if (!nk || bestG < this.clarityMin) return null;

    const thr = this.threshold * bestG;
    let chosenLag = -1;
    for (let i = 0; i < nk; i++) {
      if (keyVal[i] >= thr && keyLag[i] >= tauMin) { chosenLag = keyLag[i]; break; }
    }
    if (chosenLag < 0) return null;

    // Interpolation parabolique du sommet.
    const t = chosenLag;
    const a = nsdf[t - 1], b = nsdf[t], c = nsdf[t + 1];
    let d = 0;
    const denom = a - 2 * b + c;
    if (Math.abs(denom) > 1e-12) d = (0.5 * (a - c)) / denom;
    if (!isFinite(d) || Math.abs(d) > 1) d = 0;
    const period = t + d;
    if (period <= 0) return null;
    return { f0: this.sr / period, clarity: Math.min(1, b), period };
  }
}
