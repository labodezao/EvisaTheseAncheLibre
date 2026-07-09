// Détection de note « grossière » : spectre large bande + appariement
// harmonique. C'est l'étage qui identifie la note et l'octave (E0 → C9)
// sans erreurs d'octave ou de quinte : un candidat de fondamentale n'est
// retenu que s'il explique l'ensemble des partiels observés, avec une
// pénalité pour l'énergie spectrale qu'il laisse inexpliquée.

import { FFT, hannWindow } from './fft.js';

export class CoarseAnalyzer {
  constructor(sampleRate, opts = {}) {
    this.sr = sampleRate;
    this.win = opts.win ?? 16384;          // ~341 ms à 48 kHz
    this.fftSize = opts.fftSize ?? this.win * 2;
    this.fMin = opts.fMin ?? 18;
    this.fMax = opts.fMax ?? 9500;
    this.ring = new Float32Array(this.win);
    this.wpos = 0;
    this.filled = 0;
    this.hann = hannWindow(this.win);
    this.fft = FFT.get(this.fftSize);
    this.re = new Float64Array(this.fftSize);
    this.im = new Float64Array(this.fftSize);
    this.mag = new Float32Array(this.fftSize / 2);
    this.binHz = this.sr / this.fftSize;
  }

  write(chunk) {
    for (let i = 0; i < chunk.length; i++) {
      this.ring[this.wpos] = chunk[i];
      this.wpos = (this.wpos + 1) % this.win;
    }
    this.filled = Math.min(this.win, this.filled + chunk.length);
  }

  ready() { return this.filled >= this.win; }

  // Analyse le contenu courant : spectre, pics, fondamentale.
  analyze() {
    if (!this.ready()) return null;
    const { win, fftSize, re, im, hann, ring, wpos } = this;
    for (let i = 0; i < win; i++) {
      re[i] = ring[(wpos + i) % win] * hann[i];
      im[i] = 0;
    }
    re.fill(0, win);
    im.fill(0, win);
    this.fft.transform(re, im);
    const nBins = fftSize / 2;
    const mag = this.mag;
    for (let i = 0; i < nBins; i++) mag[i] = Math.hypot(re[i], im[i]);

    const peaks = this.findPeaks(mag);
    const f0 = this.detectF0(peaks);
    return { peaks, f0, mag, binHz: this.binHz };
  }

  findPeaks(mag) {
    const nBins = mag.length;
    const iMin = Math.max(2, Math.floor(this.fMin / this.binHz));
    const iMax = Math.min(nBins - 3, Math.ceil(this.fMax / this.binHz));

    // Plancher de bruit : médiane par blocs de 256 bins.
    const block = 256;
    const floor = new Float32Array(Math.ceil(nBins / block));
    const tmp = [];
    for (let b = 0; b < floor.length; b++) {
      tmp.length = 0;
      const end = Math.min(nBins, (b + 1) * block);
      for (let i = b * block; i < end; i++) tmp.push(mag[i]);
      tmp.sort((x, y) => x - y);
      floor[b] = tmp[tmp.length >> 1] || 0;
    }

    const peaks = [];
    for (let i = iMin; i <= iMax; i++) {
      const m = mag[i];
      if (m <= mag[i - 1] || m < mag[i + 1]) continue;
      const noise = floor[(i / block) | 0] + 1e-12;
      if (m < noise * 8) continue;
      if (m < mag[i - 2] || m < mag[i + 2]) continue;
      // Interpolation parabolique sur le log des magnitudes.
      const la = Math.log(mag[i - 1] + 1e-30);
      const lb = Math.log(m + 1e-30);
      const lc = Math.log(mag[i + 1] + 1e-30);
      let d = (0.5 * (la - lc)) / (la - 2 * lb + lc);
      if (!isFinite(d) || Math.abs(d) > 0.5) d = 0;
      peaks.push({ freq: (i + d) * this.binHz, mag: m });
    }
    peaks.sort((a, b) => b.mag - a.mag);
    return peaks.slice(0, 48);
  }

  detectF0(peaks) {
    if (!peaks.length) return null;
    const top = peaks.slice(0, 12);
    const candidates = new Set();
    for (const p of top) {
      for (let d = 1; d <= 10; d++) {
        const c = p.freq / d;
        if (c >= this.fMin && c <= this.fMax) candidates.add(Math.round(c * 100) / 100);
      }
    }

    const weight = (k) => 1 / (1 + 0.35 * (k - 1));
    let best = null;
    for (const c of candidates) {
      const H = Math.min(20, Math.floor(this.fMax / c));
      const tolRatio = Math.pow(2, 35 / 1200) - 1; // ±35 cents
      const matched = new Set();
      const parts = [];
      let score = 0;
      for (let k = 1; k <= H; k++) {
        const target = k * c;
        const tol = target * tolRatio + this.binHz;
        let bi = -1, bd = Infinity;
        for (let j = 0; j < peaks.length; j++) {
          if (matched.has(j)) continue;
          const d = Math.abs(peaks[j].freq - target);
          if (d < tol && d < bd) { bd = d; bi = j; }
        }
        if (bi >= 0) {
          matched.add(bi);
          score += Math.sqrt(peaks[bi].mag) * weight(k);
          parts.push({ k, freq: peaks[bi].freq, mag: peaks[bi].mag });
        }
      }
      if (parts.length === 0) continue;
      // Pénalité : pics forts dans la bande couverte que c n'explique pas
      // (élimine les erreurs d'octave supérieure et de quinte).
      for (let j = 0; j < Math.min(peaks.length, 20); j++) {
        if (matched.has(j)) continue;
        const f = peaks[j].freq;
        if (f < c * 0.8 || f > c * H * 1.05) continue;
        const kApprox = Math.max(1, Math.round(f / c));
        score -= 0.7 * Math.sqrt(peaks[j].mag) * weight(kApprox);
      }
      if (!best || score > best.score) best = { c, score, parts };
    }
    if (!best) return null;

    // Raffinement par moindres carrés pondérés sur les partiels appariés :
    // minimise Σ w (f_k − k·f0)².
    let num = 0, den = 0;
    for (const p of best.parts) {
      const w = p.mag;
      num += w * p.k * p.freq;
      den += w * p.k * p.k;
    }
    const f0 = den > 0 ? num / den : best.c;
    return { freq: f0, score: best.score, harmonics: best.parts };
  }
}
