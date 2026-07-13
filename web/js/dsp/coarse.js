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
    // Tampons réutilisés par findPeaks (aucune allocation par analyse).
    this.blockScratch = new Float32Array(256);
    this.floorArr = new Float32Array(Math.ceil(this.fftSize / 2 / 256));
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
  // `priorF0` (Hz) : note tenue courante — sert d'hystérésis pour éviter les
  // bascules d'octave/quinte sur une anche réelle riche en partiels.
  analyze(priorF0 = null) {
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
    const f0 = this.detectF0(peaks, priorF0);
    return { peaks, f0, mag, binHz: this.binHz };
  }

  findPeaks(mag) {
    const nBins = mag.length;
    const iMin = Math.max(2, Math.floor(this.fMin / this.binHz));
    const iMax = Math.min(nBins - 3, Math.ceil(this.fMax / this.binHz));

    // Plancher de bruit : médiane par blocs de 256 bins (tampons réutilisés,
    // tri numérique en place des TypedArray — pas d'allocation par tick).
    const block = 256;
    const floor = this.floorArr;
    const nFloor = Math.ceil(nBins / block);
    for (let b = 0; b < nFloor; b++) {
      const start = b * block;
      const len = Math.min(nBins, start + block) - start;
      const s = this.blockScratch;
      for (let i = 0; i < len; i++) s[i] = mag[start + i];
      const view = s.subarray(0, len);
      view.sort();
      floor[b] = view[len >> 1] || 0;
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

  detectF0(peaks, priorF0 = null) {
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
      const matched = new Set();
      const parts = [];
      let score = 0;
      for (let k = 1; k <= H; k++) {
        const target = k * c;
        // Tolérance croissante avec le rang : les anches réelles présentent
        // des partiels étirés (inharmonicité) de plus en plus loin du
        // multiple exact.
        const tolRatio = Math.pow(2, (35 + 2.5 * k) / 1200) - 1;
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
      // Hystérésis : la note tenue (à ± un quart de ton) conserve un bonus,
      // pour qu'une interprétation concurrente à l'octave ou à la quinte
      // (piège classique des anches riches en partiels) doive nettement la
      // dépasser avant de déclencher une bascule.
      if (priorF0 && Math.abs(1200 * Math.log2(c / priorF0)) < 50) score *= 1.3;
      if (!best || score > best.score) best = { c, score, parts };
    }
    if (!best) return null;

    // Raffinement robuste à l'inharmonicité : chaque partiel donne une
    // estimation f_k/k ; la médiane pondérée ignore les partiels étirés,
    // puis des moindres carrés restreints aux partiels cohérents (< ±12
    // cents de la médiane) affinent la valeur.
    const med = weightedMedian(best.parts.map((p) => ({ v: p.freq / p.k, w: p.mag })));
    let num = 0, den = 0;
    for (const p of best.parts) {
      const dev = Math.abs(1200 * Math.log2(p.freq / (p.k * med)));
      if (dev > 12) continue;
      const w = p.mag;
      num += w * p.k * p.freq;
      den += w * p.k * p.k;
    }
    const f0 = den > 0 ? num / den : med;
    return { freq: f0, score: best.score, harmonics: best.parts };
  }
}

function weightedMedian(pairs) {
  pairs.sort((a, b) => a.v - b.v);
  let tot = 0;
  for (const p of pairs) tot += p.w;
  let acc = 0;
  for (const p of pairs) {
    acc += p.w;
    if (acc >= tot / 2) return p.v;
  }
  return pairs.length ? pairs[pairs.length - 1].v : 0;
}
