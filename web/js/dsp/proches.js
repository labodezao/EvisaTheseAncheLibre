// Anches d'un même unisson (registre MM, MMM… : un groupe, un traqueur) :
// l'anche seule, les restes trop faibles pour être une anche, et les anches
// que la fenêtre ne sépare pas (audit d'usage pro n° 1 et 11, 10/10/2026).
// Méthodes posées sur Engine.prototype par engine.js (Object.assign), `this`
// reste le moteur.

import { centsBetween } from '../music.js';
import { MP_MAX_CENTS } from './anches-mp.js';
import { CONF_PRECISION } from './confondu.js';

// Une raie à plus de UNISSON_DB sous la plus forte de son unisson n'est pas
// une anche de la note : bandes latérales du soufflet (−29 à −36 dB sur la
// session d'Ewen, Ré#5 seul en MM : un 8'+ « fantôme » 2 ¢ au-dessus, 77
// images sur 227 entre 40 et 60 s), restes de partiels voisins. Les anches
// réelles d'un unisson jouent à quelques dB l'une de l'autre : la plus faible
// des passages réels (P11, 8'+ d'un MM) est à −11 à −16 dB.
export const UNISSON_DB = 20;

// Deux raies à moins de PROCHES_CASES cases de la fenêtre (1 case = 1/T) ne
// font qu'un pic : leurs lobes de Hann (±2 cases) se fondent. Deux raies
// égales ne font deux pics qu'au-delà de 2 à 2,5 cases (mesuré, 8'− et 8'
// à 0,44 Hz sur le partiel 2 en Normal : à 2,4 cases, une raie, le mélange
// 0,5 Hz à côté de la 8'−) : 3 cases. Sur la fondamentale, k fois moins.
export const PROCHES_CASES = 3;

export const methodesProches = {
  // Avant la stabilisation : retire les restes trop faibles, et donne l'anche
  // seule à la voix visée.
  //
  // Anche seule : la façon classique d'accorder un MMM est de boucher deux
  // anches et d'accorder la troisième. Le moteur rangeait l'anche qui sonne
  // dans la voix dont la CIBLE est la plus proche : une 8'− encore 25 ¢ trop
  // haute tombait en 8', et la voix visée restait « — ». Quand une seule raie
  // sonne dans l'unisson, c'est l'anche que le luthier accorde : la voix visée
  // (cfg.voix, la case de la séquence), si elle est dans la note (à
  // MP_MAX_CENTS ¢ au plus de la note, comme les anches d'Auto-anches). Plus
  // loin, c'est une autre note (la touche d'à côté, à 100 ¢) : rien ne change.
  // Limite : toutes les anches de l'unisson à moins de 2/(k T) Hz les unes
  // des autres (une musette dont les trois anches sont à la même hauteur) ne
  // font qu'une raie aussi ; on ne peut pas les distinguer d'une anche seule.
  uniteUnisson(groups) {
    if (this.cfg.mode !== 'register') return;
    for (const g of groups) {
      if (g.isHarmonic || g.isSub || g.voices.length < 2) continue;
      let aMax = 0;
      for (const v of g.voices) if (v.tracked) aMax = Math.max(aMax, v.amp);
      const plancher = aMax * Math.pow(10, -UNISSON_DB / 20);
      for (const v of g.voices) if (v.tracked && v.amp < plancher) { this.fillVoice(v, null); v.reste = true; }
      const on = g.voices.filter((v) => v.tracked);
      const id = this.cfg.voix;
      const visee = id != null ? g.voices.find((v) => v.def.id === id) : null;
      if (on.length !== 1) continue;
      const s = on[0];
      if (Math.abs(centsBetween(s.fMeas, g.center)) > MP_MAX_CENTS) continue;
      // Une seule raie dans la note : une anche seule (margesProches n'y
      // met pas de marge), donnée à la voix visée s'il y en a une.
      s.seule = true;
      // Les autres voix ne sonnent pas : rien à tenir (stabilize tenait 1 s la
      // valeur d'une anche partie, à côté de celle qui reste : deux lectures
      // d'une seule anche, session d'Ewen à 48,9 s).
      for (const v of g.voices) if (v !== s && v !== visee) v.absent = true;
      if (!visee || s === visee) continue;
      visee.seule = true;
      visee.fMeas = s.fMeas;
      visee.amp = s.amp;
      visee.tracked = true;
      visee.merged = !!s.merged;
      visee.modulation = s.modulation ?? null;
      visee.regressionPhase = s.regressionPhase ?? null;
      visee.dCents = centsBetween(visee.fMeas, visee.nominal);
      visee.dHz = visee.fMeas - visee.nominal;
      visee.dTargetCents = centsBetween(visee.fMeas, visee.target);
      // La mémoire de l'anche suit la voix (appariement de l'image suivante).
      const kS = `${g.key}:${s.def.id}`, kV = `${g.key}:${visee.def.id}`;
      if (this.prevF?.has(kS)) { this.prevF.set(kV, this.prevF.get(kS)); this.prevF.delete(kS); }
      this.stab?.delete(kS);
      this.fillVoice(s, null);
      s.seule = false;
      s.absent = true;
      const base = g.voices.find((v) => v.def.beatSign === 0);
      for (const v of g.voices) v.beatMeas = v.tracked && base?.tracked ? v.fMeas - base.fMeas : (v === base ? 0 : null);
    }
  },

  // Après la stabilisation : les anches qui peuvent être confondues avec une
  // voisine de l'unisson ont une marge (audit d'usage pro n° 11). Deux raies
  // à moins de PROCHES_CASES cases ne sont qu'un lobe : la valeur est celle
  // de leur mélange, quelque part entre les deux (mesuré, musette Si4 : 8'−
  // et 8' à 0,44 Hz, 8'− lu 2 ¢ trop haut toute la note en Rapide, « fine »).
  // Le moteur ne voit pas deux anches dans un lobe ; il voit qu'une voix
  // attendue n'a pas de raie. Si cette anche sonne, elle est dans le lobe
  // d'une voisine, à moins de 2/(k T) Hz (k : partiel de mesure, T :
  // fenêtre) : chaque raie voisine d'une voix sans raie a donc cette marge,
  // comme l'anche confondue avec l'octave (champs de confondu.js, méthode
  // « proches »). Deux voix lues à moins de cette distance l'une de l'autre
  // (le même lobe lu deux fois) aussi. Une anche seule (uniteUnisson) n'en a
  // pas : les autres sont bouchées. Sur la mauvaise touche (une autre note),
  // rien ne sonne dans la note : rien à dire.
  margesProches(groups) {
    if (this.cfg.mode !== 'register') return;
    for (const g of groups) {
      if (g.isHarmonic || g.isSub || g.voices.length < 2 || !(g.W > 0)) continue;
      const k = g.kTrack || 1;
      const resHz = PROCHES_CASES * g.srd / (g.W * k);
      const ord = [...g.voices].sort((a, b) => a.target - b.target);
      const propre = (v) => v.tracked && !v.held && !v.coarse && !v.merged && !v.confondu;
      const on = ord.filter(propre);
      if (!on.length || on.some((v) => v.seule)) continue;
      const marque = new Map();   // voix → voix avec qui elle peut être confondue
      const ajoute = (v, autre) => { if (!marque.has(v)) marque.set(v, []); marque.get(v).push(autre.def.id); };
      ord.forEach((m, i) => {
        if (propre(m)) return;
        // Voix sans raie : ses voisines dans l'ordre des cibles.
        for (const pas of [-1, 1]) {
          for (let j = i + pas; j >= 0 && j < ord.length; j += pas) {
            if (propre(ord[j])) { ajoute(ord[j], m); break; }
          }
        }
      });
      for (let i = 1; i < on.length; i++) {
        if (Math.abs(on[i].fMeas - on[i - 1].fMeas) < resHz) { ajoute(on[i], on[i - 1]); ajoute(on[i - 1], on[i]); }
      }
      // Séparées de justesse (de PROCHES_CASES à 2 PROCHES_CASES cases) : la
      // pente de phase de l'amas penche vers la voisine, d'au plus
      // asin(ρ) / (π k T) Hz, ρ = rapport des amplitudes (≤ 1 ; cf.
      // OCTAVE_SEP_BINS). Mesuré : 8'− et 8' à 1,3 Hz, la première image
      // séparée (fenêtre de 0,7 s) 0,76 ¢ à côté.
      const biais = new Map();
      for (const v of on) {
        if (marque.has(v)) continue;
        let b = 0;
        for (const o of on) {
          const d = Math.abs(o.fMeas - v.fMeas);
          if (o === v || d < resHz || d >= 2 * resHz) continue;
          const rho = Math.min(1, o.amp / Math.max(1e-12, v.amp));
          b = Math.max(b, Math.asin(rho) / (Math.PI * k * (g.W / g.srd)));
        }
        if (b > 0) { biais.set(v, b); ajoute(v, on.find((o) => o !== v && Math.abs(o.fMeas - v.fMeas) < 2 * resHz)); }
      }
      for (const [v, avec] of marque) {
        const mHz = biais.get(v) ?? resHz;
        const mc = Math.hypot(centsBetween(v.fMeas + mHz, v.fMeas), CONF_PRECISION);
        v.confondu = true;
        v.fEstimee = v.fMeas;
        v.centsEstimes = v.dCents;
        v.centsEstimesCible = v.dTargetCents;
        v.margeCents = mc;
        v.methode = 'proches';
        v.signeConnu = false;
        v.dureeLue = null;
        v.proches = { avec, resHz, margeHz: mHz, justesse: biais.has(v), cases: PROCHES_CASES, fenetreS: g.W / g.srd, k };
      }
    }
  },
};
