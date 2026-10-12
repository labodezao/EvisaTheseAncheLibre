// Synthèse d'anches libres pour les tests polyphoniques (dsp.test.mjs,
// polyphonie.test.mjs) : timbre qui décroît avec des irrégularités, bruit
// blanc, petit vibrato de pression commun, attaque, inversion du soufflet.
// Graines fixes : chaque son est le même d'une exécution à l'autre.

import { Engine } from '../web/js/dsp/engine.js';
import { midiToFreq } from '../web/js/music.js';

export const SR = 48000;

// Hasard reproductible (Park-Miller) et gaussienne (Box-Muller).
export function hasard(graine) {
  let g = graine;
  const u = () => { g = (g * 16807) % 2147483647; return g / 2147483647; };
  const n = () => Math.sqrt(-2 * Math.log(u() + 1e-300)) * Math.cos(2 * Math.PI * u());
  return { u, n };
}

export const at = (m, c) => midiToFreq(m) * 2 ** (c / 1200);
export const cents = (f, r) => 1200 * Math.log2(f / r);

// Timbre d'anche libre : décroissance d'environ 3,5 dB par partiel, avec des
// irrégularités (chambre, forme de la lame) ; `trous` : partiels creusés
// (dB par rapport à la valeur de la pente), comme le partiel 5 du Fa#3 d'Ewen.
export function timbre(n, r, pente = -3.5, trous = {}, gigue = 2) {
  return Array.from({ length: n }, (_, i) => 10 ** ((pente * i + (trous[i + 1] ?? 0) + gigue * r.n()) / 20));
}

// Son de plusieurs anches. Chaque anche : { f, a (amplitude), H (timbre),
// debut (s), montee (s, rampe d'attaque), vib (cents crête du vibrato de
// pression commun, 0,1 c par défaut : sa moyenne sur la fenêtre du moteur
// reste sous 0,05 c, la marge des seuils à 0,1 c), saut: { t, c } (inversion du soufflet : l'anche de
// l'autre sens, c cents plus haut, à partir de t), derive (cents par seconde : la pression du
// soufflet qui monte ou descend lentement) }. Bruit blanc à `rsb` dB
// sous le signal ; `creux` : { t, db, dur } plongée du niveau à l'inversion.
// Le son rendu porte `ecart(j, t)` : l'écart (cents) de l'anche j à sa
// fréquence `f` à l'instant t (vibrato, saut, dérive), la vérité des tests.
export function anches(liste, secondes, { rsb = 40, graine = 7, fv = 0.8, creux = null, phi = false } = {}) {
  const r = hasard(graine);
  const n = Math.floor(SR * secondes), x = new Float32Array(n);
  // `phi` : garde la phase de la fondamentale de chaque anche (vibrato, dérive et modulation de phase compris), pour la
  // vérité « fréquence moyenne sur un nombre entier de périodes de battement » (vraieEntiere).
  const phases = phi ? liste.map(() => new Float64Array(n)) : null;
  // `tire.adler` : { kappa, D0 }, deux oscillateurs couplés (Adler 1946) : dψ/dt = 2πΔ0 − K sin ψ, K = 2πκ ; la phase de
  // chaque anche reçoit ±(K/2)∫sin ψ dt (signe : `tire.signe`). Battement observé Ω = √(Δ0² − κ²) ; chaque fréquence
  // moyenne est tirée de (Δ0 − Ω)/2 vers l'autre.
  const ad = liste.find((a) => a.tire?.adler)?.tire.adler;
  let sinInt = null;
  if (ad) {
    const K = 2 * Math.PI * ad.kappa, w0 = 2 * Math.PI * ad.D0;
    sinInt = new Float64Array(n);
    let psi = ad.psi0 ?? 0, acc = 0;
    for (let i = 0; i < n; i++) {
      sinInt[i] = acc;
      const sn = Math.sin(psi);
      acc += sn / SR;
      psi += (w0 - K * sn) / SR;
    }
    sinInt.K = K;
  }
  const phv = 2 * Math.PI * r.u();
  for (let jj = 0; jj < liste.length; jj++) {
    const an = liste[jj];
    const H = an.H ?? timbre(12, r);
    const ph0 = H.map(() => 2 * Math.PI * r.u());
    const debut = an.debut ?? 0, montee = an.montee ?? 0.05, vib = an.vib ?? 0.1, derive = an.derive ?? 0;
    // `tire` : { f, beta, ph, am } tirage mutuel de deux anches voisines : leur phase
    // oscille à f Hz (le battement) avec un indice beta (rad), leur amplitude de am (0 à 1).
    const tire = an.tire ?? null;
    let ph = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const saut = an.saut && t >= an.saut.t ? an.saut.c : 0;
      ph += (2 * Math.PI * an.f * 2 ** ((vib * Math.sin(2 * Math.PI * fv * t + phv) + saut + derive * t) / 1200)) / SR;
      const phT = tire?.adler ? (tire.signe ?? 1) * (sinInt.K / 2) * sinInt[i]
        : tire ? tire.beta * Math.sin(2 * Math.PI * tire.f * t + (tire.ph ?? 0)) : 0;
      if (phases) phases[jj][i] = ph + phT;
      if (t < debut) continue;
      let g = 1;
      if (creux) {
        const d = Math.abs(t - creux.t), bas = 10 ** (-creux.db / 20);
        g = d < creux.dur / 2 ? bas : d < creux.dur ? bas + (1 - bas) * (d - creux.dur / 2) / (creux.dur / 2) : 1;
      }
      const env = g * Math.min(1, (t - debut) / montee) * 0.1 * (an.a ?? 1)
        * (tire?.am ? 1 + tire.am * Math.sin(2 * Math.PI * tire.f * t + (tire.ph ?? 0) + 1) : 1);
      for (let h = 0; h < H.length; h++) {
        if (an.f * (h + 1) > 0.45 * SR) break;
        x[i] += env * H[h] * Math.sin((h + 1) * (ph + phT) + ph0[h]);
      }
    }
  }
  let p = 0;
  for (const v of x) p += v * v;
  const s = Math.sqrt(p / n / 10 ** (rsb / 10));
  for (let i = 0; i < n; i++) x[i] += s * r.n();
  if (phases) x.phi = phases;
  x.ecart = (j, t) => {
    const an = liste[j];
    return (an.vib ?? 0.1) * Math.sin(2 * Math.PI * fv * t + phv)
      + (an.saut && t >= an.saut.t ? an.saut.c : 0) + (an.derive ?? 0) * t;
  };
  return x;
}

// Hauteur vraie (Hz) de l'anche j sur la partie de la fenêtre que la pente de
// phase du moteur regarde (15 à 85 % de la fenêtre, cf. clusterRefine) : la
// fenêtre de T secondes qui finit à t.
export function vraie(x, liste, j, t, T) {
  let s = 0, n = 0;
  for (let u = t - 0.85 * T; u <= t - 0.15 * T; u += 0.001) { s += x.ecart(j, Math.max(0, u)); n++; }
  return liste[j].f * 2 ** (s / Math.max(1, n) / 1200);
}

// Fréquence moyenne (Hz) de la fondamentale de l'anche j sur la fenêtre de L secondes qui finit à t : (phase(t) − phase(t − L)) /
// (2π L), vibrato, dérive et modulation de phase compris. Avec L = un nombre ENTIER de périodes de battement, la modulation
// de phase se moyenne à zéro : c'est « la fréquence de l'anche en place » (audit couplage du 11/10/2026). Demande `phi: true`.
export function vraieEntiere(x, j, t, L) {
  const i1 = Math.min(x.length - 1, Math.round(t * SR)), i0 = Math.max(0, Math.round((t - L) * SR));
  return (x.phi[j][i1] - x.phi[j][i0]) / (2 * Math.PI * ((i1 - i0) / SR));
}

// Rejoue un son dans le moteur ; rend les images (temps, note, voix visibles).
export function rejoue(cfg, x) {
  const e = new Engine(SR, cfg);
  const imgs = [];
  for (let i = 0; i + 512 <= x.length; i += 512) {
    const r = e.process(x.subarray(i, i + 512));
    if (!r) continue;
    const vs = r.groups.filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices);
    imgs.push({ t: r.time, m: r.playedMidi, vs, r });
  }
  return imgs;
}
export const voix = (im, id) => im.vs.find((v) => v.def.id === id);
export const fmt = (c) => (c == null ? '—' : `${c >= 0 ? '+' : ''}${c.toFixed(2)}`);
