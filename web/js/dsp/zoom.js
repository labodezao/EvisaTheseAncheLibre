// Traqueur « zoom spectral » haute précision (mode harmonique).
//
// Principe : le signal est hétérodyné (multiplié par e^{-j2πfc·t}) autour de
// la fréquence nominale de la note, filtré et décimé par 512 (48 kHz →
// ~93,75 Hz de bande complexe). Une FFT glissante sur ce signal en bande de
// base sépare les anches d'un même ton (tremolo à quelques Hz d'écart) et un
// raffinement par différence de phase entre deux fenêtres décalées porte la
// précision bien en dessous de 0,1 cent, tout en se mettant à jour en continu.
//
// La décimation en deux moyennes glissantes (32 puis 16) place les zéros du
// second étage exactement sur les fréquences de repliement, ce qui rejette
// les partiels voisins.

import { FFT, hannWindow } from './fft.js';

const D1 = 32;
const D2 = 16;
const RING = 2048; // ~21,8 s à 48 kHz

export class ZoomTracker {
  constructor(sampleRate) {
    this.sr = sampleRate;
    this.srd = sampleRate / (D1 * D2);
    this.ringRe = new Float64Array(RING);
    this.ringIm = new Float64Array(RING);
    this.count = 0;   // échantillons décimés écrits (total)
    this.fc = 0;
    // Oscillateur local par récurrence de rotation.
    this.oscRe = 1; this.oscIm = 0;
    this.stepRe = 1; this.stepIm = 0;
    this.norm = 0;
    // Accumulateurs des deux étages de décimation.
    this.a1re = 0; this.a1im = 0; this.c1 = 0;
    this.a2re = 0; this.a2im = 0; this.c2 = 0;
    this.windows = new Map();
    this.scratch = new Map(); // tampons FFT réutilisés par taille de fenêtre
  }

  setCenter(fc) {
    if (fc === this.fc) return;
    this.fc = fc;
    const dphi = (2 * Math.PI * fc) / this.sr;
    this.stepRe = Math.cos(dphi);
    this.stepIm = -Math.sin(dphi);
    this.oscRe = 1; this.oscIm = 0;
    this.a1re = 0; this.a1im = 0; this.c1 = 0;
    this.a2re = 0; this.a2im = 0; this.c2 = 0;
    this.count = 0;
  }

  process(chunk) {
    let { oscRe, oscIm, a1re, a1im, c1, a2re, a2im, c2, count, norm } = this;
    const { stepRe, stepIm, ringRe, ringIm } = this;
    for (let i = 0; i < chunk.length; i++) {
      const s = chunk[i];
      a1re += s * oscRe;
      a1im += s * oscIm;
      // Rotation de l'oscillateur local.
      const nr = oscRe * stepRe - oscIm * stepIm;
      oscIm = oscRe * stepIm + oscIm * stepRe;
      oscRe = nr;
      if (++norm >= 512) {
        const g = 1 / Math.hypot(oscRe, oscIm);
        oscRe *= g; oscIm *= g;
        norm = 0;
      }
      if (++c1 >= D1) {
        a2re += a1re / D1;
        a2im += a1im / D1;
        a1re = 0; a1im = 0; c1 = 0;
        if (++c2 >= D2) {
          const w = count % RING;
          ringRe[w] = a2re / D2;
          ringIm[w] = a2im / D2;
          count++;
          a2re = 0; a2im = 0; c2 = 0;
        }
      }
    }
    this.oscRe = oscRe; this.oscIm = oscIm; this.norm = norm;
    this.a1re = a1re; this.a1im = a1im; this.c1 = c1;
    this.a2re = a2re; this.a2im = a2im; this.c2 = c2;
    this.count = count;
  }

  hannFor(n) {
    let w = this.windows.get(n);
    if (!w) { w = hannWindow(n); this.windows.set(n, w); }
    return w;
  }

  // FFT complexe de la fenêtre de `len` échantillons décimés se terminant
  // `back` échantillons avant le présent. Retourne {re, im} dans des tampons
  // réutilisés (slot 0 ou 1) — valides jusqu'au prochain appel du même slot.
  spectrumAt(len, back, slot = 0) {
    const fft = FFT.get(len);
    const key = `${len}|${slot}`;
    let buf = this.scratch.get(key);
    if (!buf) {
      buf = { re: new Float64Array(len), im: new Float64Array(len) };
      this.scratch.set(key, buf);
    }
    const { re, im } = buf;
    const w = this.hannFor(len);
    const start = this.count - back - len;
    for (let i = 0; i < len; i++) {
      const idx = (start + i) % RING;
      re[i] = this.ringRe[idx] * w[i];
      im[i] = this.ringIm[idx] * w[i];
    }
    fft.transform(re, im);
    return { re, im };
  }

  // Analyse : renvoie les composantes (anches) résolues dans la bande.
  // maxWin contrôle le compromis réactivité / résolution.
  analyze(maxWin = 256, maxPeaks = 5) {
    const avail = Math.min(this.count, RING);
    let W = 32;
    while (W * 2 <= Math.min(avail, maxWin)) W *= 2;
    if (avail < 48) return null; // en cours d'amorçage

    const H = W >> 2; // décalage pour le raffinement de phase
    const canRefine = avail >= W + H;
    const cur = this.spectrumAt(W, 0, 0);
    const prev = canRefine ? this.spectrumAt(W, H, 1) : null;

    const mags = new Float32Array(W);
    for (let i = 0; i < W; i++) mags[i] = Math.hypot(cur.re[i], cur.im[i]);

    // Seuil : médiane des magnitudes (tampon réutilisé, tri en place —
    // `mags` reste intact car transmis à l'affichage).
    let ms = this.scratch.get(`m${W}`);
    if (!ms) { ms = { re: new Float32Array(W) }; this.scratch.set(`m${W}`, ms); }
    ms.re.set(mags);
    ms.re.sort();
    const median = ms.re[W >> 1] + 1e-30;
    const maxMag = ms.re[W - 1];

    const binHz = this.srd / W;
    const offLimit = 0.45 * this.srd;
    const comps = [];
    for (let k = 0; k < W; k++) {
      const m = mags[k];
      const km = (k - 1 + W) % W;
      const kp = (k + 1) % W;
      if (m <= mags[km] || m < mags[kp]) continue;
      if (m < median * 6 || m < maxMag / 200) continue;
      let off = k <= W / 2 ? k * binHz : (k - W) * binHz;
      if (Math.abs(off) > offLimit) continue;
      // Interpolation parabolique (log magnitude).
      const la = Math.log(mags[km] + 1e-30);
      const lb = Math.log(m + 1e-30);
      const lc = Math.log(mags[kp] + 1e-30);
      let d = (0.5 * (la - lc)) / (la - 2 * lb + lc);
      if (!isFinite(d) || Math.abs(d) > 0.5) d = 0;
      let offI = off + d * binHz;
      // Raffinement par différence de phase entre les deux fenêtres :
      // Δφ = 2π·f·H/srd (mod 2π), résolu autour de la valeur interpolée.
      if (canRefine) {
        const p1 = Math.atan2(cur.im[k], cur.re[k]);
        const p0 = Math.atan2(prev.im[k], prev.re[k]);
        const expected = (2 * Math.PI * offI * H) / this.srd;
        let dphi = p1 - p0 - expected;
        dphi -= 2 * Math.PI * Math.round(dphi / (2 * Math.PI));
        const corr = dphi / ((2 * Math.PI * H) / this.srd);
        if (Math.abs(corr) < 2 * binHz) offI += corr;
      }
      comps.push({ off: offI, freq: this.fc + offI, mag: m, bin: k });
    }
    comps.sort((a, b) => b.mag - a.mag);
    const kept = comps.slice(0, maxPeaks).sort((a, b) => a.off - b.off);
    return {
      components: kept,
      mags,
      W,
      srd: this.srd,
      fc: this.fc,
      fill: Math.min(1, avail / maxWin),
    };
  }
}
