// Anches d'un même ton séparées par Matrix Pencil, côté moteur : garde-fous,
// persistance d'une image à l'autre, rangement des anches dans les cases
// 8', 8'+, 8'− et alerte « plusieurs anches » (l'algorithme lui-même est
// dans subspace.js). Sorti d'engine.js (v28) sans rien changer : les
// méthodes sont posées sur Engine.prototype par engine.js (Object.assign),
// `this` reste le moteur.

import { matrixPencil } from './subspace.js';
import { assignOrdered } from './appariement.js';
import { centsBetween } from '../music.js';

// Anches d'un même ton séparées par Matrix Pencil (cf. mpReeds). Une FFT ne
// sépare deux raies qu'après ~1/Δf secondes ; Matrix Pencil, qui ajuste un
// modèle de sinusoïdes, les sépare bien plus tôt quand le son est propre.
// Mesuré sur une banque de notes musette (deux anches, 2 à 7,5 Hz d'écart) :
// les deux anches à 0,5 ¢ près en 0,5 s, là où la FFT en demande 1,7 à 2,7.
const MP_N = 48;        // échantillons de bande de base (≈ 0,5 s)
const MP_L = 12;        // paramètre du pinceau : ~1,5 ms par appel (24 : ~15 ms)
const MP_POLES = 4;     // de quoi loger 3 anches et un reste de partiel voisin
const MP_RATIO = 0.25;  // anche admise à −12 dB de la plus forte (cf. Auto-anches)
const MP_MIN_HZ = 0.8;  // écart minimal (fondamentale) : en deçà, raies latérales du soufflet
const MP_DAMP = 3;      // s⁻¹ : une anche en régime ne s'éteint ni ne croît
export const MP_MAX_CENTS = 35; // anche dans la note (comme le filtre d'Auto-anches)
const MP_HIST = 5;      // sur les 5 dernières images,
const MP_STABLE = 4;    // au moins 4 voient les mêmes anches…
const MP_CENTS = 2;     // …chacune à 2 ¢ près (une image manquée : creux de battement)
export const MP_ALERT_S = 0.3; // alerte du mode Automatique : anches vues depuis 0,3 s

// Méthodes d'Engine (cf. engine.js, Object.assign).
export const methodesAnchesMp = {
  // Anches d'un même ton résolues par Matrix Pencil sur la bande de base du
  // traqueur de la voix de base (≈ 0,5 s). Retourne les anches [{ f, amp }]
  // (2 ou 3, par fréquence croissante) une fois vues MP_STABLE fois sur les
  // MP_HIST dernières images, sinon null. Garde-fous, contre les fausses anches : chaque pôle
  // doit être en régime (ni amorti ni croissant), dans la note (±50 ¢), à
  // −12 dB au plus de la plus forte, et les anches écartées d'au moins
  // MP_MIN_HZ. Rejoué sur les sessions d'Ewen (anches seules, soufflet
  // vivant, inversions) : moins de 0,3 % d'images signalées à tort.
  mpReeds(g, calib) {
    const nom = g.voices[0].nominal;
    // Pôles d'un traqueur ramenés à la fondamentale (÷ son partiel k), en
    // régime et dans la note ; null si le traqueur n'a pas encore 0,5 s de
    // son. (Les redémarrages de la fenêtre FFT n'y font rien : Matrix Pencil
    // a sa propre fenêtre, et un vrai saut de hauteur rompt la stabilité.)
    // Pas à cheval sur une reprise après silence (inversion du soufflet).
    const tNow = this.samplesTotal / this.sr;
    if (this.resume && tNow - this.resume.t < 0.6) { this.mpHist = []; return null; }
    const poles = (t, k) => {
      if (!t || Math.min(t.count, 2048) < MP_N) return null;
      const bb = t.baseband(MP_N);
      if (!bb || bb.re.length < MP_N) return null;
      let comps = [];
      try { comps = matrixPencil(bb.re, bb.im, MP_POLES, bb.srd, MP_L); } catch { comps = []; }
      return comps
        .map((cp) => ({ f: ((bb.fc + cp.freq) * calib) / k, amp: cp.amp, damping: cp.damping }))
        .filter((cp) => Math.abs(cp.damping) < MP_DAMP && Math.abs(centsBetween(cp.f, nom)) < MP_MAX_CENTS);
    };
    // Traqueurs de la note : celui de la voix de base (partiel k) et les
    // traqueurs cachés du stroboscope (partiels ×1..×6). On mesure sur le
    // partiel le plus haut dont la bande contient encore toutes les anches
    // (±35 ¢ ≤ ±40 Hz, soit m·f ≤ 2 kHz) : l'écart entre anches y est m fois
    // plus grand, donc mieux résolu (Fa3 à 2 Hz d'écart : 0,7 ¢ d'erreur
    // sur la fondamentale, 0,1 ¢ sur le partiel 6).
    const cands = [[g.kTrack || 1, this.trackers.get(g.key)]];
    for (const [key, t] of this.trackers) {
      const m = key.startsWith(`${g.key}p`) ? Number(key.slice(g.key.length + 1)) : NaN;
      if (m > 0 && m !== cands[0][0]) cands.push([m, t]);
    }
    const usable = cands.filter(([m, t]) => t && m * nom <= 2000).sort((a, b) => b[0] - a[0]);
    if (!usable.length) return null;
    const comps = poles(usable[0][1], usable[0][0]);
    if (!comps) return null;
    // Le soufflet module la hauteur : sur une demi-seconde, une anche peut
    // sortir en DEUX pôles voisins (0,1 à 0,2 Hz d'écart). Ce n'est qu'une
    // anche : les pôles à moins de MP_MIN_HZ de plus fort qu'eux sont fondus
    // dans celui-ci.
    const merged = [];
    for (const cp of [...comps].sort((a, b) => b.amp - a.amp)) {
      const host = merged.find((q) => Math.abs(q.f - cp.f) < MP_MIN_HZ);
      if (host) host.amp += cp.amp; else merged.push({ ...cp });
    }
    let aMax = 0;
    for (const cp of merged) aMax = Math.max(aMax, cp.amp);
    let strong = merged.filter((cp) => cp.amp >= MP_RATIO * aMax)
      .sort((a, b) => b.amp - a.amp).slice(0, 3);
    // Une anche est périodique : ses partiels disent tous la même hauteur.
    // Une anche de plus n'est retenue que si un AUTRE partiel de la note la
    // montre aussi, à 3 ¢ près. Rejoué sur les sessions d'Ewen : sans ce
    // contrôle, des restes de partiels voisins passaient pour des anches à
    // +30, +60 ou −43 ¢.
    if (strong.length >= 2) {
      const seen = [];
      for (const [m, t] of usable.slice(1, 3)) {
        const cs = poles(t, m);
        if (!cs?.length) continue;
        let a2 = 0;
        for (const cp of cs) a2 = Math.max(a2, cp.amp);
        seen.push(...cs.filter((cp) => cp.amp >= 0.1 * a2));
      }
      strong = strong.filter((cp, i) => i === 0
        || seen.some((q) => Math.abs(centsBetween(q.f, cp.f)) < 3));
    }
    strong.sort((a, b) => a.f - b.f);
    const ok = strong.length >= 2 && strong.every((cp, i) => i === 0 || cp.f - strong[i - 1].f >= MP_MIN_HZ);
    const h = this.mpHist ?? (this.mpHist = []);
    h.push(ok ? strong : null);
    if (h.length > MP_HIST) h.shift();
    const seen = h.filter(Boolean);
    const last = seen[seen.length - 1];
    const stable = seen.length >= MP_STABLE && seen.every((x) => x.length === last.length
      && x.every((cp, i) => Math.abs(centsBetween(cp.f, last[i].f)) < MP_CENTS));
    return stable ? last : null;
  },

  // Auto-anches : les anches de Matrix Pencil dans les emplacements 8', 8'+,
  // 8'−, si la FFT en voit moins — attribuées par la MÊME règle que les
  // raies de la FFT (assignOrdered : ordre des fréquences, cible ou mémoire
  // la plus proche), pour qu'une anche ne change pas de case quand la FFT
  // reprend la main. La mémoire par anche (prevF) est posée sur ces valeurs.
  fillFromMp(g, mp) {
    const fine = g.voices.filter((v) => v.tracked);
    if (fine.length >= mp.length) return;
    const voices = [...g.voices].sort((a, b) => a.target - b.target);
    const tolHz = Math.max(2.5, g.center * 0.05);
    const chosen = assignOrdered(voices, mp.map((cp) => ({ freq: cp.f, mag: cp.amp })), tolHz);
    if (chosen.filter(Boolean).length < mp.length) return;
    for (let i = 0; i < voices.length; i++) {
      const v = voices[i];
      this.fillVoice(v, chosen[i], 2);
      if (chosen[i]) {
        v.mp = true;
        this.prevF?.set(`${g.key}:${v.def.id}`, chosen[i].freq);
      }
    }
    const base = g.voices.find((v) => v.def.beatSign === 0);
    for (const v of g.voices) v.beatMeas = v.tracked && base?.tracked ? v.fMeas - base.fMeas : null;
  },

  // Auto-anches : les cases disent l'ordre des anches, pas leur distance à
  // une cible. Une anche seule est « 8' », quelle que soit sa hauteur ; deux
  // anches : la plus proche de la note en 8', l'autre en 8'+ ou 8'− selon
  // qu'elle est au-dessus ou au-dessous ; trois : 8'−, 8', 8'+. Avant, une
  // anche seule à +3 ¢ tombait en « 8'+ » (plus près de la cible du 8'+ que
  // de la note) et, d'un sens du soufflet à l'autre, changeait de case.
  rankReeds(g) {
    if (g.voices.length < 2) return;
    const on = g.voices.filter((v) => v.tracked).sort((a, b) => a.fMeas - b.fMeas);
    if (!on.length) return;
    const bySign = (s) => g.voices.find((v) => v.def.beatSign === s);
    const nom = g.voices[0].nominal;
    // Rangement déjà valable (ordre respecté, une anche en 8') : on n'y touche
    // pas — sinon deux anches à égale distance de la note (−2 / +2 ¢) se
    // disputeraient la case 8' d'une image à l'autre.
    const cur = on.map((v) => v.def.beatSign).join(',');
    if ((on.length === 1 && cur === '0') || (on.length === 2 && (cur === '0,1' || cur === '-1,0'))
      || (on.length >= 3 && cur === '-1,0,1')) return;
    let signs;
    if (on.length >= 3) signs = [-1, 0, 1];
    else if (on.length === 2) {
      signs = Math.abs(centsBetween(on[0].fMeas, nom)) <= Math.abs(centsBetween(on[1].fMeas, nom)) ? [0, 1] : [-1, 0];
    } else signs = [0];
    const plan = on.slice(0, 3).map((v, i) => [v, bySign(signs[i])]);
    if (plan.some(([, dst]) => !dst) || plan.every(([src, dst]) => src === dst)) return;
    const data = plan.map(([v]) => ({ f: v.fMeas, amp: v.amp, mp: v.mp, step: v.step, merged: v.merged }));
    for (const v of g.voices) { this.fillVoice(v, null); v.mp = false; v.step = false; v.merged = false; }
    // Une case qui change d'anche repart de zéro : ni médiane ni maintien de
    // l'anche d'avant (elle s'afficherait deux fois).
    for (const v of g.voices) this.stab?.delete(`${g.key}:${v.def.id}`);
    plan.forEach(([, dst], i) => {
      const d = data[i];
      this.fillVoice(dst, { freq: d.f, mag: d.amp }, 2);
      dst.mp = d.mp; dst.step = d.step; dst.merged = !!d.merged;
      this.prevF?.set(`${g.key}:${dst.def.id}`, d.f);
    });
    for (const [, src] of plan) if (!plan.some(([, dst]) => dst === src)) this.prevF?.delete(`${g.key}:${src.def.id}`);
    const base = bySign(0);
    for (const v of g.voices) v.beatMeas = v.tracked && base?.tracked ? v.fMeas - base.fMeas : null;
  },

  // Alerte « plusieurs anches » du mode Automatique, d'après Matrix Pencil.
  mpUnison(groups) {
    const g = groups.find((gr) => !gr.isHarmonic && !gr.isSub);
    const nom = g?.voices[0]?.nominal;
    if (!nom) return null;
    const reeds = this.mp.map((cp) => centsBetween(cp.f, nom));
    return {
      cents: reeds[reeds.length - 1] - reeds[0],
      reeds,
      beatHz: this.mp[this.mp.length - 1].f - this.mp[0].f,
    };
  },
};
