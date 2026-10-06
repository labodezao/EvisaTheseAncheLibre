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
export function anches(liste, secondes, { rsb = 40, graine = 7, fv = 0.8, creux = null } = {}) {
  const r = hasard(graine);
  const n = Math.floor(SR * secondes), x = new Float32Array(n);
  const phv = 2 * Math.PI * r.u();
  for (const an of liste) {
    const H = an.H ?? timbre(12, r);
    const ph0 = H.map(() => 2 * Math.PI * r.u());
    const debut = an.debut ?? 0, montee = an.montee ?? 0.05, vib = an.vib ?? 0.1, derive = an.derive ?? 0;
    let ph = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const saut = an.saut && t >= an.saut.t ? an.saut.c : 0;
      ph += (2 * Math.PI * an.f * 2 ** ((vib * Math.sin(2 * Math.PI * fv * t + phv) + saut + derive * t) / 1200)) / SR;
      if (t < debut) continue;
      let g = 1;
      if (creux) {
        const d = Math.abs(t - creux.t), bas = 10 ** (-creux.db / 20);
        g = d < creux.dur / 2 ? bas : d < creux.dur ? bas + (1 - bas) * (d - creux.dur / 2) / (creux.dur / 2) : 1;
      }
      const env = g * Math.min(1, (t - debut) / montee) * 0.1 * (an.a ?? 1);
      for (let h = 0; h < H.length; h++) {
        if (an.f * (h + 1) > 0.45 * SR) break;
        x[i] += env * H[h] * Math.sin((h + 1) * ph + ph0[h]);
      }
    }
  }
  let p = 0;
  for (const v of x) p += v * v;
  const s = Math.sqrt(p / n / 10 ** (rsb / 10));
  for (let i = 0; i < n; i++) x[i] += s * r.n();
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
