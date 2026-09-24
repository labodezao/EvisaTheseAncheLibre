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
    // Début du régime en cours (index décimé) : l'analyse ne regarde pas
    // avant. Un saut de hauteur (cf. restart) le déplace : la fenêtre ne
    // mélange plus l'avant et l'après, elle repart courte et regrandit.
    this.start = 0;
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
    this.start = 0;
  }

  // La hauteur a sauté : on oublie ce qui précède les `keep` derniers
  // échantillons décimés. Sans ça, la longue fenêtre (2,7 s en « normal »)
  // étalait une marche nette en une rampe de 2,7 s, en retard d'1,4 s.
  restart(keep = 40) {
    this.start = Math.max(this.start, this.count - keep);
  }

  // Battement lu dans l'ENVELOPPE de la bande (demande d'Ewen : « combien de
  // fois par minute bat mon trémolo ? »). Deux anches proches font monter et
  // descendre le volume de leur somme au rythme de leur écart de fréquence ;
  // la période de cette enveloppe se lit par autocorrélation, même quand les
  // deux anches sont trop proches pour que le spectre les sépare. Sur le
  // partiel k, l'enveloppe bat k fois plus vite : on divise par k.
  // Fenêtre : les `maxS` dernières secondes depuis le dernier redémarrage
  // (au moins 2,5 s, et deux périodes). Retourne { hz, conf } ou null.
  beatFromEnvelope(k = 1, maxS = 8) {
    // Toute la mémoire de la bande depuis le changement de note (les
    // redémarrages de la fenêtre de mesure n'y changent rien : le son est
    // continu). 8 s : un battement lent (0,5 Hz, 30/min) y fait 4 périodes.
    const avail = Math.min(this.count, RING);
    const N = Math.min(avail, Math.round(maxS * this.srd));
    if (N < 2.5 * this.srd) return null;
    let M = 1;
    while (M < 2 * N) M <<= 1;
    const fft = FFT.get(M);
    // 1) Isoler l'amas de l'anche suivie : FFT de la bande, on ne garde que
    //    ±BW Hz autour de la raie la plus forte (les deux anches d'un trémolo
    //    y sont ; les restes des autres partiels repliés par la décimation,
    //    qui faisaient « battre » une anche seule à 9 Hz, n'y sont pas).
    const re = new Float64Array(M), im = new Float64Array(M);
    for (let i = 0; i < N; i++) {
      const idx = (((this.count - N + i) % RING) + RING) % RING;
      re[i] = this.ringRe[idx]; im[i] = this.ringIm[idx];
    }
    fft.transform(re, im);
    let pk = 0, pm = -1;
    for (let i = 0; i < M; i++) { const m = re[i] * re[i] + im[i] * im[i]; if (m > pm) { pm = m; pk = i; } }
    const BW = Math.min(16, 0.45 * this.srd), binHz = this.srd / M;
    const half = Math.round(BW / binHz);
    for (let i = 0; i < M; i++) {
      let d = Math.abs(i - pk); d = Math.min(d, M - d);
      if (d > half) { re[i] = 0; im[i] = 0; }
    }
    // FFT inverse par conjugaison : x = conj(FFT(conj(X))) / M.
    for (let i = 0; i < M; i++) im[i] = -im[i];
    fft.transform(re, im);
    // 2) Enveloppe, sans les bords (transitoires du filtre).
    const e0 = Math.round(0.1 * this.srd), n = N - 2 * e0;
    const env = new Float64Array(n);
    let mean = 0;
    for (let i = 0; i < n; i++) { env[i] = Math.hypot(re[i + e0], im[i + e0]); mean += env[i]; }
    mean /= n;
    let v = 0;
    for (let i = 0; i < n; i++) { env[i] -= mean; v += env[i] * env[i]; }
    if (!(mean > 0) || Math.sqrt(v / n) < 0.03 * mean) return null;   // volume stable : pas de battement
    // 3) Autocorrélation de l'enveloppe (FFT), première crête franche.
    re.fill(0); im.fill(0);
    re.set(env);
    fft.transform(re, im);
    for (let i = 0; i < M; i++) { re[i] = re[i] * re[i] + im[i] * im[i]; im[i] = 0; }
    fft.transform(re, im);
    const r0 = re[0];
    const r = (t) => (re[t] / r0) * (n / (n - t));   // non biaisée
    const tMin = Math.max(2, Math.floor(this.srd / 15));   // battement ≤ 15 Hz sur le partiel
    const tMax = Math.floor(n / 2);                        // au moins deux périodes vues
    // La première crête APRÈS le premier passage sous zéro (cherché dès le
    // début : pour un battement rapide, le creux tombe avant tMin).
    let dipped = false, best = -1;
    for (let t = 1; t < tMax; t++) {
      const x = r(t);
      if (x < 0) dipped = true;
      if (t >= tMin && dipped && x > 0.3 && x >= r(t - 1) && x >= r(t + 1)) { best = t; break; }
    }
    if (best < 0) return null;
    const a = r(best - 1), b = r(best), c = r(best + 1);
    let d = (0.5 * (a - c)) / (a - 2 * b + c);
    if (!isFinite(d) || Math.abs(d) > 0.5) d = 0;
    return { hz: this.srd / (best + d) / k, conf: b, depth: Math.sqrt(v / n) / mean };
  }

  // Estimation RAPIDE (fenêtre courte de `W` échantillons, ~0,34 s) de la
  // raie la plus proche du décalage `off` (Hz dans la bande) : sert à voir
  // qu'une hauteur a bougé, pas à la mesurer finement. Ignore `start`.
  quick(off, W = 32) {
    const H = W >> 2;
    if (Math.min(this.count, RING) < W + H) return null;
    const cur = this.spectrumAt(W, 0, 2);
    const prev = this.spectrumAt(W, H, 3);
    const binHz = this.srd / W;
    const mag = (b) => Math.hypot(cur.re[(b + W) % W], cur.im[(b + W) % W]);
    const b0 = Math.round(off / binHz);
    let k = null, best = 0;
    for (let b = b0 - 2; b <= b0 + 2; b++) {
      const m = mag(b);
      if (m > best && m >= mag(b - 1) && m >= mag(b + 1)) { best = m; k = b; }
    }
    if (k == null) return null;
    const la = Math.log(mag(k - 1) + 1e-30), lb = Math.log(best + 1e-30), lc = Math.log(mag(k + 1) + 1e-30);
    let d = (0.5 * (la - lc)) / (la - 2 * lb + lc);
    if (!isFinite(d) || Math.abs(d) > 0.5) d = 0;
    let o = (k + d) * binHz;
    const i = (k + W) % W;
    const p1 = Math.atan2(cur.im[i], cur.re[i]);
    const p0 = Math.atan2(prev.im[i], prev.re[i]);
    let dphi = p1 - p0 - (2 * Math.PI * o * H) / this.srd;
    dphi -= 2 * Math.PI * Math.round(dphi / (2 * Math.PI));
    const corr = dphi / ((2 * Math.PI * H) / this.srd);
    if (Math.abs(corr) < 2 * binHz) o += corr;
    return { off: o, mag: best };
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

  // Les `maxLen` derniers échantillons de la bande de base complexe (I/Q),
  // dans l'ordre chronologique — entrée de l'analyse paramétrique à
  // sous-espaces (Matrix Pencil). `srd` : fréquence d'échantillonnage
  // décimée ; `fc` : porteuse hétérodyne.
  baseband(maxLen = 48) {
    const avail = Math.min(this.count, RING);
    const len = Math.min(maxLen, avail);
    if (len < 6) return null;
    const re = new Float64Array(len);
    const im = new Float64Array(len);
    const start = this.count - len;
    for (let i = 0; i < len; i++) {
      const idx = (((start + i) % RING) + RING) % RING;
      re[i] = this.ringRe[idx];
      im[i] = this.ringIm[idx];
    }
    return { re, im, srd: this.srd, fc: this.fc };
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
    const avail = Math.min(this.count - this.start, RING);
    let W = 32;
    while (W * 2 <= Math.min(avail, maxWin)) W *= 2;
    if (avail < 40) return null; // en cours d'amorçage (fenêtre + décalage de phase)

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
    // Une raie à 3 cases ou moins d'une raie 12 dB plus forte n'est pas une
    // anche : c'est l'épaule du lobe principal (±2 cases) ou le premier lobe
    // secondaire de la fenêtre de Hann, déformés par la modulation lente du
    // soufflet (±0,15 ¢ à 0,6 Hz suffit : pic parasite à −20 dB, 3 cases).
    // Son raffinement de phase est en plus tiré vers la raie forte. Il était
    // apparié à la place de la vraie anche dès qu'il tombait plus près de la
    // cible : la courbe plongeait de 0,6 ¢ pendant trois images puis
    // remontait — les « dents de scie ». Deux vraies anches sont, elles,
    // écartées d'au moins 4 cases (cf. SEP_HZ dans engine.js).
    const isSideband = (c) => comps.some((s) => s !== c && s.mag > 4 * c.mag
      && Math.min(Math.abs(s.bin - c.bin), W - Math.abs(s.bin - c.bin)) <= 3);
    const clean = comps.filter((c) => !isSideband(c));
    clean.sort((a, b) => b.mag - a.mag);
    const kept = clean.slice(0, maxPeaks).sort((a, b) => a.off - b.off);
    return {
      components: kept,
      mags,
      // Spectre complexe de la fenêtre courante (tampon réutilisé : valable
      // jusqu'au prochain analyze() de CE traqueur) — sert à isoler l'amas
      // d'une anche et à suivre sa phase (engine.js, clusterFreq).
      re: cur.re,
      im: cur.im,
      W,
      srd: this.srd,
      fc: this.fc,
      fill: Math.min(1, avail / maxWin),
    };
  }
}
