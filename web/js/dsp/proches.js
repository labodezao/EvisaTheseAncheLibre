// Anches d'un même unisson (registre MM, MMM… : un groupe, un traqueur) :
// l'anche seule, les restes trop faibles pour être une anche, et les anches
// que la fenêtre ne sépare pas (audit d'usage pro n° 1 et 11, 10/10/2026).
// Méthodes posées sur Engine.prototype par engine.js (Object.assign), `this`
// reste le moteur.

import { centsBetween } from '../music.js';
import { MP_MAX_CENTS } from './anches-mp.js';
import { CONF_PRECISION } from './confondu.js';
const ETIQUETTE_S = 1.0;   // D2 : durée pendant laquelle une étiquette 8'/8'+ changée reste dite incertaine (appariement.js)
import { chordFromPeaks } from './chord.js';

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

// v71 (C6, cfg.deuxAnches ; audit « superposition » du 19/10/2026, § 3.4 et 6) : une anche attendue (Automatique, ou registre M) devant
// DEUX anches qui battent. La fréquence que le traqueur lit n'est plus celle d'une anche : c'est celle de leur somme (posée entre les deux,
// +2,3 à +4,1 ¢, 1,5 à 4,2 ¢ d'écart type, sauts de 1 à 5 ¢). Le moteur n'a pas à la lisser (ce qui est réel ne se lisse pas) : il dit
// qu'il y a deux anches, avec leur battement, et ne montre plus la valeur comme celle d'une anche (voix `confondue`, marge).
// Preuve d'un battement : l'enveloppe du partiel de mesure (battement.js, measureBeat : au moins deux partiels qui s'accordent sur
// des anches, confiance >= DEUX_CONF_MIN) ou l'unisson vu par Matrix Pencil (t.unison). Un battement tenu DEUX_TENUE_S après sa
// dernière preuve : l'enveloppe manque quelques images quand le volume du mélange se stabilise.
export const DEUX_CONF_MIN = 0.4;
export const DEUX_TENUE_S = 1.5;
export const DEUX_PERSISTE = 5;      // images consécutives d'un autre rythme avant de changer de référence
export const DEUX_MED = 5;           // valeurs acceptées dont on prend la médiane
export const DEUX_HZ_MAX = 14;       // le battement de l'enveloppe est cherché jusqu'à 15 Hz sur le partiel (zoom.js, beatFromEnvelope)

export const methodesProches = {
  // Vrai si le spectre large bande montre DEUX notes à un demi-ton de niveaux voisins (chordFromPeaks avec les degrés [0, 1], les mêmes
  // règles que chordAuto : deux vraies raies, pas des harmoniques d'une autre, niveaux à 7 dB près) et que la fondamentale `f0` n'est
  // ni l'une ni l'autre : c'est une tierce note, qu'aucune anche ne joue. Rend false sans paire.
  tierceNote(f0, coarse) {
    if (!coarse?.peaks?.length) return false;
    const ch = chordFromPeaks(coarse.peaks, [0, 1], { a4: this.cfg.a4 });
    if (!ch || ch.harm || ch.notes.length !== 2) return false;
    const amps = ch.notes.map((n) => n.amp * n.amp);
    if (Math.min(...amps) < 0.2 * Math.max(...amps)) return false;
    const m = Math.round(69 + 12 * Math.log2(f0 / this.cfg.a4));
    return !ch.notes.some((n) => n.midi === m);
  },

  // Rend { hz, bpm, source, cents? } si deux anches battent devant la voix unique du groupe de base, et marque cette voix confondue :
  // son chiffre est la fréquence mesurée (ou le milieu des deux anches quand le Matrix Pencil les donne), avec une marge. Marge Ω/2
  // quand le chiffre est le milieu des deux raies (Matrix Pencil) ; Ω sinon (la raie lue est l'une des deux, l'autre est à Ω).
  marquerDeuxAnches(groups, beat, unison, quiet) {
    const c = this.cfg;
    const now = this.samplesTotal / this.sr;
    if (quiet) { this.deuxVu = null; this.deuxEnv = null; return null; }
    if (!(c.mode === 'auto' || (c.mode === 'register' && c.register === 'M'))) return null;
    const g = groups.find((gr) => !gr.isHarmonic && !gr.isSub);
    if (!g || g.voices.length !== 1) return null;
    const v = g.voices[0];
    let vu = null;
    // 1) l'unisson posé (Automatique : Matrix Pencil, ou deux raies franches du traqueur) : le battement vient de l'écart des deux raies
    if (unison && Number.isFinite(unison.cents)) {
      const hzU = Number.isFinite(unison.beatHz) && unison.beatHz > 0 ? unison.beatHz : Math.abs(v.nominal * (2 ** (unison.cents / 1200) - 1));
      if (hzU > 0) vu = { hz: hzU, source: 'unison', reeds: unison.reeds ?? null };
    }
    // 2) l'enveloppe : des partiels dont les rythmes divisés par leur rang s'accordent. Sa période est la première crête de l'autocorrélation ;
    // sur une note qui s'éteint (échantillon de 2 à 3 s) elle prend parfois la 2e ou la 3e (÷2, ÷3 : 36 et 24 bat/min pour 72) : on ne suit
    // que les valeurs qui s'accordent à la référence (à 8 %), on ignore ses sous-multiples, et on ne change de référence qu'après
    // DEUX_PERSISTE images d'un autre rythme. Le rythme est un fait de l'enveloppe, pas une hauteur : la médiane des DEUX_MED dernières
    // valeurs acceptées ne lisse aucune courbe de justesse.
    if (beat && beat.kind === 'anches' && beat.sure && beat.conf >= DEUX_CONF_MIN && beat.hz > 0 && beat.hz <= DEUX_HZ_MAX) {
      const e = this.deuxEnv ??= { ref: vu ? vu.hz : null, hist: vu ? [vu.hz] : [], cand: null, n: 0 };
      const h = beat.hz, proche = (x, y) => Math.abs(x / y - 1) <= 0.08;
      if (e.ref == null) { e.ref = h; e.hist = [h]; }
      else if (proche(h, e.ref)) {
        e.hist.push(h); if (e.hist.length > DEUX_MED) e.hist.shift();
        e.ref = [...e.hist].sort((x, y) => x - y)[e.hist.length >> 1];
        e.cand = null; e.n = 0;
      } else if ([2, 3, 4].some((m) => proche(h * m, e.ref))) { /* sous-multiple : la 2e ou la 3e crête de l'autocorrélation */ }
      else if (e.cand != null && proche(h, e.cand)) { if (++e.n >= DEUX_PERSISTE) { e.ref = h; e.hist = [h]; e.cand = null; e.n = 0; } }
      else { e.cand = h; e.n = 1; }
      vu = vu ? { ...vu, hz: e.ref } : { hz: e.ref, source: 'enveloppe' };     // l'enveloppe filtrée passe devant le Matrix Pencil, plus bruité sur une note courte
    }
    if (vu) this.deuxVu = { ...vu, t: now };
    else if (this.deuxVu && now - this.deuxVu.t > DEUX_TENUE_S) { this.deuxVu = null; this.deuxEnv = null; }
    const d = this.deuxVu;
    if (!d) return null;
    if (!v.tracked || !Number.isFinite(v.fMeas)) return { hz: d.hz, bpm: 60 * d.hz, source: d.source };
    // Le milieu des deux raies, quand le Matrix Pencil donne les deux anches (cents à la nominale) ; sinon la raie lue.
    let centre = v.fMeas, margeHz = d.hz;
    if (Array.isArray(d.reeds) && d.reeds.length === 2 && Number.isFinite(v.nominal)) {
      centre = v.nominal * 2 ** (((d.reeds[0] + d.reeds[1]) / 2) / 1200);
      margeHz = d.hz / 2;
    }
    const k = g.kTrack || 1;
    v.confondu = true;
    v.fEstimee = centre;
    v.centsEstimes = centsBetween(centre, v.nominal);
    v.centsEstimesCible = centsBetween(centre, v.target);
    v.margeCents = Math.hypot(centsBetween(centre + margeHz, centre), CONF_PRECISION);
    v.methode = 'proches';
    v.signeConnu = false;
    v.dureeLue = null;
    v.proches = { avec: [], resHz: d.hz, margeHz, justesse: false, cases: PROCHES_CASES, fenetreS: g.W > 0 && g.srd > 0 ? g.W / g.srd : null, k, deuxAnches: true };
    return { hz: d.hz, bpm: 60 * d.hz, source: d.source };
  },

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
      if (on.length !== 1) { this.seuleDe?.delete(g.key); continue; }
      const s = on[0];
      if (Math.abs(centsBetween(s.fMeas, g.center)) > MP_MAX_CENTS) continue;
      // Une seule raie dans la note : une anche seule (margesProches n'y
      // met pas de marge), donnée à la voix visée s'il y en a une.
      s.seule = true;
      // D2 : qui porte la raie unique ? Un changement de porteur (ou son retour après deux raies) change l'étiquette ; une raie qui reste au même porteur ne la change pas.
      const change = this.cfg.CONTINUITE && (this.seuleDe ??= new Map()).get(g.key) !== s.def.id;
      if (this.cfg.CONTINUITE) this.seuleDe.set(g.key, s.def.id);
      // Les autres voix ne sonnent pas : rien à tenir (stabilize tenait 1 s la
      // valeur d'une anche partie, à côté de celle qui reste : deux lectures
      // d'une seule anche, session d'Ewen à 48,9 s).
      for (const v of g.voices) if (v !== s && v !== visee) v.absent = true;
      if (!visee || s === visee) continue;
      visee.seule = true;
      // D2 : la raie d'une autre voix est donnée à la voix visée : l'étiquette n'est plus sûre pendant ETIQUETTE_S.
      if (change) (this.etiquetteJusqua ??= new Map()).set(g.key, this.samplesTotal / this.sr + ETIQUETTE_S);
      if (this.cfg.CONTINUITE && (this.etiquetteJusqua?.get(g.key) ?? -1) > this.samplesTotal / this.sr) for (const v of g.voices) v.etiquette = 'incertaine';
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
      if (g.voices.some((v) => v.source === 'modele2')) continue;   // v71 (K_MESURE) : séparées par le modèle à deux raies (entiere.js), pas un lobe
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
