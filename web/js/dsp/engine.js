// Moteur d'analyse : reçoit l'audio par blocs, identifie la note jouée
// (analyse grossière) puis mesure chaque anche avec un traqueur zoom par
// groupe d'octave. Fonctionne dans un Worker (ou dans Node pour les tests).

import { CoarseAnalyzer } from './coarse.js';
import { ZoomTracker } from './zoom.js';
import { FFT } from './fft.js';
import { NsdfTracker } from './nsdf.js';
import { matrixPencil } from './subspace.js';
import { chordFromPeaks, chordAuto, degreeLabel } from './chord.js';
import {
  midiToFreq, nearestMidi, centsBetween, voiceTargetFreq,
  MIDI_MIN, MIDI_MAX, REGISTER_PRESETS,
} from '../music.js';

// Version du moteur : doit être celle de la page et de app.js (cf. le
// contrôle de cohérence dans app.js et le test dans dsp.test.mjs).
export const ENGINE_VERSION = '23';

const HOP = 4096;             // période d'analyse (~85 ms à 48 kHz)
const MAXWIN = { fast: 128, normal: 256, precise: 512 };
// Saut de hauteur (cf. detectStep). Une fenêtre courte (STEP_QW échantillons
// décimés ≈ 0,17 s) doit s'écarter de la mesure fine de plus de STEP_CENTS en
// restant sur un palier — stable à STEP_PLATEAU près en hauteur et à
// STEP_LEVEL_DB près en niveau d'une image à l'autre. On garde alors STEP_KEEP
// échantillons de bande de base (≈ 0,43 s : une fenêtre de 32 et son décalage
// de phase). 2 ¢ : au-dessus de ce qu'un soufflet vivant fait onduler une
// anche (±1 ¢ — à 1,5 ¢ le banc test/bench_courbe.mjs se met à redémarrer).
const STEP_CENTS = 2;
const STEP_PLATEAU = 1;
const STEP_LEVEL_DB = 3;
const STEP_KEEP = 40;
// Réglages sans effet sur les cibles : les changer ne remet pas la mesure à zéro.
const NO_RETUNE = new Set(['gateDb', 'tolCents', 'autoFreeze', 'readout', 'devMode', 'bellows', '_v']);
const STEP_MAX_CENTS = 40;
const STEP_QW = 16;
// Reprise après un silence (inversion du soufflet) : on ne garde que ce qui
// suit la reprise (8 échantillons décimés ≈ une image).
const RESUME_KEEP = 8;
// Deux anches déguisées en une (mode Automatique) : partiels en désaccord de
// plus de DISAGREE_CENTS pendant plus de DISAGREE_HOLD_S.
const DISAGREE_CENTS = 1.5;
const DISAGREE_HOLD_S = 1.5;
// Sortie stabilisée (cf. stabilize) : une anche qui perd la mesure garde sa
// dernière valeur jusqu'à STAB_HOLD_S.
const STAB_HOLD_S = 1.0;

// Harmonique sur lequel mesurer un groupe d'anches à l'unisson.
//
// Deux anches à 1,6 Hz d'écart (une musette en La4) ne sont séparées par la
// FFT zoom qu'une fois sa fenêtre longue de ~2,7 s. Avant, les lobes se
// chevauchent, le raffinement de phase de chaque anche est pollué par sa
// voisine, et la courbe saute de 1 à 2 cents par image — c'est ce qui poussait
// à bloquer les anches pour en mesurer une à la fois.
//
// Or une anche libre en régime est un oscillateur entretenu : son son est
// exactement périodique, ses partiels exactement harmoniques (le modèle
// physique le confirme, et la fusion multi-harmonique du mode auto repose déjà
// dessus). Sur l'harmonique k, les anches sont k fois plus écartées — donc
// séparées k fois plus tôt — et un cent y vaut toujours un cent.
//
// On vise un écart d'au moins SEP_HZ entre anches sur l'harmonique suivi :
// ~4 cases de FFT à la première fenêtre (64 points à ~94 Hz de bande), ce que
// le fenêtrage de Hann sépare proprement. Mesuré (test/bench_gigue.mjs,
// musette La4 ±1,6 Hz) : erreur entre 1 et 2 s de ±2,5 ¢ sur H1, ±0,02 ¢
// sur H5. Deux bornes : toutes les anches doivent tenir dans la bande du
// zoom, y compris une anche désaccordée, et on ne monte pas au-delà de
// ~4 kHz, où les partiels faiblissent et où la mesure se perd.
const SEP_HZ = 6;
const BAND_HZ = 30;        // demi-bande utile du zoom (±0,45·srd ≈ ±42 Hz, avec marge)
const OUT_OF_TUNE_HZ = 1.5; // marge pour une anche encore loin de sa cible
const K_FREQ_MAX = 4000;
const K_MAX = 8;

// Garde-fou : on ne mesure sur le partiel k que s'il est RÉELLEMENT présent
// dans le spectre large bande de la note (à moins de 30 dB du plus fort de
// ses dix premiers partiels).
//
// Deux raisons. Une anche peut avoir un partiel faible — il ne faut pas la
// mesurer là où elle n'est pas. Et si la note est mal détectée (mesuré : une
// musette très ouverte en Do6 lue comme un Sol#2), la bande du zoom centrée
// sur un partiel qui n'existe pas ne contient que la fondamentale réelle
// repliée par la décimation — elle ressortait comme une « mesure » fausse de
// 4000 cents. Sans partiel présent, on redescend : l'accordeur n'affiche
// alors rien, comme avant, plutôt qu'une valeur inventée.
function partialPresent(coarse, f0, k) {
  if (!coarse?.mag || !coarse.binHz) return true;   // pas d'information : ne rien empêcher
  const peakAround = (f) => {
    const tol = Math.max(1.5 * coarse.binHz, 0.015 * f);
    const a = Math.max(0, Math.floor((f - tol) / coarse.binHz));
    const b = Math.min(coarse.mag.length - 1, Math.ceil((f + tol) / coarse.binHz));
    let m = 0;
    for (let i = a; i <= b; i++) if (coarse.mag[i] > m) m = coarse.mag[i];
    return m;
  };
  let ref = 0;
  for (let n = 1; n <= 10; n++) ref = Math.max(ref, peakAround(f0 * n));
  return ref > 0 && peakAround(f0 * k) >= ref / 31.6;
}

// Écart minimal (Hz) entre les cibles d'un groupe d'unisson ; à défaut de
// cibles distinctes (auto-anches), l'écart attendu à la note.
function targetSpacing(g) {
  if (g.voices.length < 2) return Infinity;    // anche seule : rien à séparer
  const targets = g.voices.map((v) => v.target).sort((a, b) => a - b);
  let spacing = Infinity;
  for (let i = 1; i < targets.length; i++) {
    const d = targets[i] - targets[i - 1];
    if (d > 1e-6) spacing = Math.min(spacing, d);
  }
  if (!Number.isFinite(spacing)) {
    const ref = g.center * (g.kTrack && g.voices[0]?.target > g.center * 1.5 ? g.kTrack : 1);
    spacing = Math.max(...targets.map((t) => Math.abs(t - ref)));
  }
  return spacing;
}

// Partiels mesurés pour le stroboscope par anche : ×1..×8, sauf celui déjà
// mesuré par le groupe de base, présents dans le spectre, et où toutes les
// anches tiennent dans la bande du zoom. Jusqu'à ×8 : la bande ×2 du strobe
// montre les partiels 2, 4, 6, 8, la bande ×4 les partiels 4 et 8 — comme
// sur le disque d'un vrai stroboscope, chaque bande porte aussi ses aigus.
const STROBE_PARTIALS = 8;
export function strobePartials(g, coarse = null) {
  const out = [];
  const spread = Math.max(...g.voices.map((v) => Math.abs(v.target - g.center)));
  for (let k = 1; k <= STROBE_PARTIALS; k++) {
    if (k === g.kTrack) continue;
    if (g.avoidEven && k % 2 === 0) continue;   // partagé avec l'anche à l'octave
    if (g.center * k > 6000) break;
    if (k * (spread + OUT_OF_TUNE_HZ) > BAND_HZ) break;
    if (!partialPresent(coarse, g.center, k)) continue;
    out.push(k);
  }
  return out;
}

export function unisonHarmonic(g, cfg, coarse = null) {
  const kBase = g.kTrack;
  if (cfg.polyHarmonic) return Math.max(1, cfg.polyHarmonic | 0);
  const targets = g.voices.map((v) => v.target).sort((a, b) => a - b);
  let spacing = Infinity;
  for (let i = 1; i < targets.length; i++) {
    const d = targets[i] - targets[i - 1];
    if (d > 1e-6) spacing = Math.min(spacing, d);
  }
  const spread = Math.max(...targets.map((t) => Math.abs(t - g.center)));
  // Emplacements d'unisson sans cible distincte (auto-anches) : l'écart
  // attendu est celui de la courbe de battement à cette note.
  if (!Number.isFinite(spacing)) spacing = spread;
  if (!(spacing > 0)) return kBase;
  const kSep = Math.ceil(SEP_HZ / spacing);
  const kBand = Math.floor(BAND_HZ / (spread + OUT_OF_TUNE_HZ));
  const kFreq = Math.floor(K_FREQ_MAX / g.center);
  let k = Math.max(kBase, Math.min(kSep, kBand, kFreq, K_MAX));
  // Partiel pair interdit quand une anche sonne à l'octave au-dessus (cf.
  // groupVoices) : kBase est alors impair, la boucle s'y arrête au pire.
  const ok = (kk) => !(g.avoidEven && kk % 2 === 0) && partialPresent(coarse, g.center, kk);
  while (k > kBase && !ok(k)) k--;
  return k;
}

export class Engine {
  constructor(sampleRate, cfg = {}) {
    this.sr = sampleRate;
    this.cfg = {
      a4: 440,
      temperament: 'equal',
      transpose: 0,
      calibrationPpm: 0,
      mode: 'auto',            // 'auto' | 'manual' | 'register'
      register: 'MM',
      manualNotes: null,       // [midi, ...] en mode manuel
      trackHarmonics: 0,       // suit les partiels 2..n de chaque note (hors registre)
      fuseHarmonics: true,     // fusion multi-harmonique cohérente (mode auto)
      trackSub: false,         // bandes f/2 et 3f/2 (détection de bifurcation)
      subspace: false,         // analyse paramétrique Matrix Pencil (voix de base)
      polyHarmonic: null,      // harmonique de mesure des anches à l'unisson
                               // (null = choisi pour les séparer vite, cf. unisonHarmonic)
      reedOctaves: [0],        // octaves scrutés en auto-anches (0 = octave jouée ;
                               // l'utilisateur ajoute 16'/4'/2' à la main)
      maxUnison: 3,            // nb max d'anches à l'unisson par octave (auto-anches)
      lockNote: null,          // note MIDI imposée (désactive la détection)
      gateDb: -70,             // seuil de silence : gèle traqueurs et horloge
      response: 'normal',      // 'fast' | 'normal' | 'precise'
      beatCurve: { midiLow: 48, bLow: 0.8, midiHigh: 96, bHigh: 3.0, overrides: {} },
      ...cfg,
    };
    this.coarse = new CoarseAnalyzer(sampleRate);
    // Détecteur temporel McLeod (NSDF) : identification de note robuste aux
    // erreurs d'octave et suivi faible latence d'une hauteur en mouvement.
    this.nsdf = new NsdfTracker(sampleRate);
    this.trackers = new Map();   // clé: écart d'octave → ZoomTracker
    this.acc = 0;
    this.rmsAcc = 0;
    this.rmsN = 0;
    this.peakAcc = 0;
    this.playedMidi = null;
    this.candMidi = null;
    this.candCount = 0;
    this.lastSwitchT = -1e9;    // instant de la dernière bascule de note (garde)
    this.samplesTotal = 0;
    // Détection d'attaque : enveloppe RMS par bloc (~10,7 ms à 48 kHz).
    this.env = [];
    this.quietChunks = 99;
    this.attackArmed = true;
    this.attackPending = null;
    this.lastAttack = null;
    this.steps = new Map();     // détection de saut par groupe (cf. detectStep)
    this.stab = new Map();      // sortie stabilisée par anche (cf. stabilize)
    this.lastFine = null;       // dernière mesure fine de la voix de base (maintien en creux de battement)
  }

  get gate() { return Math.pow(10, (this.cfg.gateDb ?? -70) / 20); }

  configure(patch) {
    const before = JSON.stringify([this.cfg.mode, this.cfg.register, this.cfg.chordDegrees, this.cfg.chordType]);
    // Réglages qui ne changent pas les cibles (seuil de silence, affichage) :
    // ils ne doivent pas remettre la mesure à zéro — sinon glisser le seuil
    // sur le vumètre effaçait la mesure à chaque mouvement.
    const changed = Object.keys(patch).filter((k) => JSON.stringify(patch[k]) !== JSON.stringify(this.cfg[k]));
    Object.assign(this.cfg, patch);
    if (JSON.stringify([this.cfg.mode, this.cfg.register, this.cfg.chordDegrees, this.cfg.chordType]) !== before) this.chord = null;
    if (patch.beatCurve) this.cfg.beatCurve = { ...patch.beatCurve };
    if (changed.every((k) => NO_RETUNE.has(k))) return;
    // Tout changement de cible invalide les traqueurs.
    this.retune(true);
  }

  // Accord en degrés (mode « Accord », ou registre Quinte = degrés 1 5) :
  // la fondamentale est reconnue dans le son (chordFromPeaks), chaque degré
  // devient une voix sur SA note, là où elle a été trouvée.
  chordDegrees() {
    const c = this.cfg;
    if (c.mode === 'chord') {
      // Type reconnu tout seul : les degrés sont ceux de l'accord trouvé.
      if (c.chordType === 'auto') return this.chord?.degrees ?? [0];
      return c.chordDegrees?.length ? c.chordDegrees : [0, 4, 7];
    }
    if (c.mode === 'register' && c.register === 'Q') return [0, 7];
    return null;
  }

  voices() {
    const c = this.cfg;
    if (this.chordDegrees()) {
      return (this.chord?.notes ?? []).map((n) => {
        const lbl = degreeLabel(n.semi);
        return { id: lbl, label: lbl, oct: 0, beatSign: 0, fixedMidi: n.midi, chordDeg: n.semi };
      });
    }
    if (c.mode === 'register') {
      const preset = REGISTER_PRESETS[c.register] ?? REGISTER_PRESETS.M;
      return preset.voices;
    }
    if (c.mode === 'manual' && c.manualNotes?.length) {
      // Chaque note manuelle devient une voix ancrée sur sa propre note.
      return c.manualNotes.map((m, i) => ({
        id: `n${i}`, label: null, oct: 0, beatSign: 0, fixedMidi: m,
      }));
    }
    if (c.mode === 'reeds') {
      // Auto-anches : on ouvre, pour chaque octave scrutée (16'..2' par
      // rapport à la note détectée), jusqu'à `maxUnison` emplacements
      // d'unisson. Seuls les emplacements réellement alimentés seront suivis
      // → le nombre d'anches se révèle tout seul. L'utilisateur peut restreindre
      // les octaves et l'unisson (fixer à la main).
      const octs = (c.reedOctaves ?? [-1, 0, 1, 2]);
      const nU = Math.min(3, Math.max(1, c.maxUnison ?? 3));
      const foot = { '-2': "32'", '-1': "16'", 0: "8'", 1: "4'", 2: "2'" };
      const out = [];
      for (const oct of octs) {
        for (let u = 0; u < nU; u++) {
          out.push({
            id: `o${oct}u${u}`,
            label: (foot[oct] ?? `${oct >= 0 ? '+' : ''}${oct}oct`) + (u > 0 ? ` ${u + 1}` : ''),
            oct, beatSign: u === 0 ? 0 : 1,
          });
        }
      }
      return out;
    }
    return [{ id: 'auto', label: null, oct: 0, beatSign: 0 }];
  }

  // (Re)centre les traqueurs sur la note jouée courante.
  retune(force = false) {
    if (force) this.plan = null;
    // Nouvelle note (ou nouveaux réglages) : la continuité par anche repart
    // de zéro — les cibles reprennent la main pour l'appariement.
    this.prevF = new Map();
    this.steps = new Map();      // détection de saut par groupe (cf. detectStep)
    this.stab = new Map();       // sortie stabilisée par anche (cf. stabilize)
    this.disagreeSince = null;
    this.unisonSince = null;
    this.retuneT = this.samplesTotal / this.sr;
    const played = this.playedMidi;
    if (played == null && this.cfg.mode !== 'manual') {
      if (force) this.trackers.clear();
      return;
    }
    const groups = this.groupVoices(played);
    const keep = new Set();
    for (const g of groups) {
      keep.add(g.key);
      let t = this.trackers.get(g.key);
      if (!t) { t = new ZoomTracker(this.sr); this.trackers.set(g.key, t); }
      if (force || t.fc !== g.fc) t.setCenter(g.fc);
    }
    for (const k of [...this.trackers.keys()]) if (!keep.has(k)) this.trackers.delete(k);
  }

  // Regroupe les voix par centre de mesure (une FFT zoom couvre ±40 Hz :
  // toutes les voix à l'unisson d'une même octave partagent un traqueur).
  // Pour les notes graves, on suit un partiel supérieur (k·f0 ≥ 150 Hz) et on
  // divise la fréquence mesurée par k : la fondamentale d'une anche grave est
  // souvent faible et sa bande encombrée de partiels voisins ; le partiel k
  // est net, et l'écart entre anches y est multiplié par k (meilleure
  // séparation des basses tremblées).
  groupVoices(playedMidi) {
    const c = this.cfg;
    const map = new Map();
    for (const v of this.voices()) {
      const base = v.fixedMidi ?? (playedMidi + 12 * v.oct + (v.semi || 0));
      if (base < MIDI_MIN - 1 || base > MIDI_MAX + 1) continue;
      const t = v.fixedMidi != null
        ? { midi: v.fixedMidi, nominal: midiToFreq(v.fixedMidi, c), beat: 0,
            target: midiToFreq(v.fixedMidi, c) }
        : voiceTargetFreq(playedMidi, v, c);
      // Accord : une clé par DEGRÉ (la courbe « 5 » reste la même d'un accord
      // à l'autre, la légende ne s'allonge pas à chaque accord joué).
      const key = v.chordDeg != null ? `c${v.chordDeg}`
        : v.fixedMidi != null ? `m${v.fixedMidi}` : `o${v.oct}${v.semi ? `q${v.semi}` : ''}`;
      let g = map.get(key);
      if (!g) {
        const kTrack = Math.max(1, Math.ceil(150 / t.nominal));
        g = { key, center: t.nominal, kTrack, voices: [] };
        map.set(key, g);
      }
      g.voices.push({ def: v, ...t });
    }
    const groups = [...map.values()];
    // Registres à l'octave (LM, LMH, auto-anches 16'/4') : les partiels PAIRS
    // d'une anche tombent pile sur la fondamentale et les partiels de l'anche
    // à l'octave au-dessus. Suivre le 16' sur son H2 revenait à mesurer le 8'
    // et à le diviser par deux — mesuré sur un vrai bandonéon (sample Ballone
    // Burini La3+La4) : un « 16' » inventé à 110,49 Hz, là où il n'y a rien.
    // Une anche qui a une voisine à l'octave au-dessus se mesure donc sur un
    // partiel IMPAIR : lui n'appartient qu'à elle.
    const octOf = (g) => (g.voices[0].def.fixedMidi == null ? g.voices[0].def.oct ?? 0 : null);
    const octs = groups.map(octOf).filter((o) => o != null);
    const maxOct = octs.length ? Math.max(...octs) : 0;
    for (const g of groups) {
      const o = octOf(g);
      g.avoidEven = o != null && o < maxOct && !groups.some((h) => h.voices[0].def.semi);
      if (g.avoidEven && g.kTrack % 2 === 0) g.kTrack++;
    }
    // Plus généralement (quinte, accord, notes définies) : le partiel de
    // mesure d'une anche ne doit tomber sur AUCUN partiel d'une autre anche
    // jouée — sinon la fenêtre voit leur somme. À la quinte Do2 + Sol2, le
    // partiel 3 de Do2 (196,2 Hz) est le partiel 2 de Sol2 (196,0 Hz) : on
    // mesure Do2 sur son partiel 4. (Les unissons ont leur propre choix, plus
    // bas : unisonHarmonic.)
    if (groups.length > 1) {
      for (const g of groups) {
        if (g.voices.length > 1 || g.avoidEven) continue;
        const clash = (k) => groups.some((h) => h !== g && Array.from({ length: 16 }, (_, j) => j + 1)
          .some((j) => Math.abs(k * g.center - j * h.center) < SEP_HZ));
        let k = g.kTrack;
        while (k < K_MAX && clash(k)) k++;
        if (!clash(k)) g.kTrack = k;
      }
    }
    // Plan harmonique FIGÉ par note. `groupVoices` est rappelé à chaque image,
    // mais les traqueurs ne sont recentrés qu'au changement de note (`retune`).
    // Si le partiel de mesure était réévalué à chaque image, un creux de
    // battement qui le fait passer sous le seuil de présence changerait k
    // sans recentrer le traqueur : la division par k deviendrait fausse. On
    // décide donc une fois par note, et on s'y tient.
    if (!this.plan || this.plan.midi !== playedMidi) {
      this.plan = { midi: playedMidi, k: new Map(), partials: new Map() };
      for (const g of groups) {
        // Anche seule dans son groupe (M, 16' d'un LM…) : pas d'unisson à
        // séparer, on garde son partiel de mesure, mais le strobe a quand
        // même ses bandes ×1..×4 — c'est là qu'on voit que ses partiels
        // disent la même chose. (Notes manuelles : non, trop de traqueurs.)
        if (g.voices.length < 2) {
          if (c.mode !== 'manual') this.plan.partials.set(g.key, strobePartials(g, this.lastCoarse));
          continue;
        }
        const k = unisonHarmonic(g, c, this.lastCoarse);
        this.plan.k.set(g.key, k);
        this.plan.partials.set(g.key, strobePartials({ ...g, kTrack: k }, this.lastCoarse));
      }
    }
    for (const g of groups) if (this.plan.k.has(g.key)) g.kTrack = this.plan.k.get(g.key);
    for (const g of groups) g.fc = g.center * g.kTrack;

    // Stroboscope par anche : chaque anche d'un groupe d'unisson est aussi
    // mesurée sur ses partiels ×1..×4, par des traqueurs cachés ancrés sur sa
    // propre mesure. Ce sont de VRAIES mesures par partiel, pas k×(f−cible) :
    // si les partiels d'une anche n'étaient pas harmoniques, ses bandes le
    // montreraient.
    for (const g of groups.slice()) {
      for (const k of this.plan.partials.get(g.key) ?? []) {
        groups.push({
          key: `${g.key}p${k}`,
          baseKey: g.key,
          center: g.center,
          kTrack: k,
          fc: g.center * k,
          isHarmonic: true,
          isPartial: true,
          hidden: true,
          voices: g.voices.map((v) => ({
            def: v.def, midi: v.midi,
            nominal: v.nominal * k, beat: v.beat * k, target: v.target * k,
          })),
        });
      }
    }

    // Suivi individuel des harmoniques : un traqueur zoom dédié par partiel
    // (2..n). Chaque partiel est mesuré à sa fréquence réelle — l'anche
    // n'étant pas parfaitement harmonique, l'écart de chaque partiel au
    // multiple exact devient une grandeur mesurée, pas une hypothèse.
    const nH = c.mode !== 'register' ? (c.trackHarmonics | 0) : 0;
    if (nH > 1) {
      for (const g of groups.slice()) {
        // Pas pour les traqueurs de partiels du strobe (ils partagent le
        // centre de leur anche) : chacun ajoutait sa propre série H2, H3…,
        // mêmes mesures en double — la légende en affichait neuf.
        if (g.isHarmonic) continue;
        for (let k = 2; k <= nH; k++) {
          if (k === g.kTrack) continue;             // déjà couvert par la voix de base
          if (g.center * k > 9500) break;
          groups.push({
            key: `${g.key}h${k}`,
            center: g.center,
            kTrack: k,
            fc: g.center * k,
            isHarmonic: true,
            voices: [{
              def: { id: `H${k}`, label: `H${k}`, oct: 0, beatSign: 0 },
              midi: g.voices[0].midi,
              nominal: g.center * k,
              beat: 0,
              target: g.center * k,
            }],
          });
        }
      }
    }

    // Bandes sous-harmoniques f/2 et 3f/2 : de l'énergie y apparaît quand
    // l'anche entre en doublement de période (bifurcation non linéaire) —
    // signal inaudible sur un accordeur classique mais décisif pour le
    // diagnostic d'une anche qui « râle ».
    if (c.trackSub && c.mode !== 'register') {
      for (const g of groups.slice()) {
        if (g.isHarmonic) continue;
        for (const [suffix, ratio, label] of [['s05', 0.5, 'f∕2'], ['s15', 1.5, '3f∕2']]) {
          const fT = g.center * ratio;
          if (fT < 15 || fT > 9500) continue;
          groups.push({
            key: `${g.key}${suffix}`,
            center: g.center,
            kTrack: 1,
            fc: fT,
            isHarmonic: true,
            isSub: true,
            voices: [{
              def: { id: suffix, label, oct: 0, beatSign: 0 },
              midi: g.voices[0].midi,
              nominal: fT,
              beat: 0,
              target: fT,
            }],
          });
        }
      }
    }

    // Fusion multi-harmonique (mode auto) : une anche libre en régime établi
    // est strictement périodique, donc ses partiels exactement harmoniques —
    // mesurer plusieurs partiels et fusionner leurs fréquences (ramenées à
    // la fondamentale) multiplie la précision, la variance d'un partiel k
    // s'améliorant en k². Des traqueurs cachés suivent les partiels 2..4
    // quand ils ne sont pas déjà affichés via « harmoniques suivies ».
    if (c.mode === 'auto' && c.fuseHarmonics !== false) {
      for (const g of groups.slice()) {
        if (g.isHarmonic || g.isSub) continue;
        for (let k = 2; k <= 4; k++) {
          if (k === g.kTrack) continue;
          if (g.center * k > 9500) break;
          const exists = groups.some((x) => x.isHarmonic && !x.isSub
            && x.center === g.center && x.kTrack === k);
          if (exists) continue;
          groups.push({
            key: `${g.key}h${k}x`,
            center: g.center,
            kTrack: k,
            fc: g.center * k,
            isHarmonic: true,
            hidden: true, // sert à la fusion, pas à l'affichage
            voices: [{
              def: { id: `H${k}`, label: `H${k}`, oct: 0, beatSign: 0 },
              midi: g.voices[0].midi,
              nominal: g.center * k,
              beat: 0,
              target: g.center * k,
            }],
          });
        }
      }
    }
    return groups;
  }

  process(chunk) {
    this.coarse.write(chunk);
    this.samplesTotal += chunk.length;
    const gate = this.gate;

    let sum = 0, pk = 0;
    for (let i = 0; i < chunk.length; i++) {
      const a = chunk[i];
      sum += a * a;
      if (a > pk) pk = a; else if (-a > pk) pk = -a;
    }
    if (pk > this.peakAcc) this.peakAcc = pk;       // crête sur la période d'analyse (saturation)
    const rms = Math.sqrt(sum / chunk.length);
    this.rmsAcc += sum;
    this.rmsN += chunk.length;

    // Enveloppe et détection d'attaque (temps de réponse de l'anche).
    const tNow = this.samplesTotal / this.sr;
    this.env.push({ t: tNow, rms });
    if (this.env.length > 512) this.env.shift();
    // Armé par un vrai silence (≥ 8 blocs), déclenché au franchissement du
    // seuil haut. La zone intermédiaire ne désarme pas : une attaque lente
    // (croissance exponentielle douce) la traverse pendant plusieurs blocs.
    if (rms < gate * 2) {
      this.quietChunks++;
      if (this.quietChunks >= 8) this.attackArmed = true;
    } else {
      this.quietChunks = 0;
      if (rms > gate * 4 && this.attackArmed && !this.attackPending) {
        this.attackPending = { onsetT: tNow, evalAt: tNow + 1.0 };
        this.attackArmed = false;
      }
    }
    if (this.attackPending && tNow >= this.attackPending.evalAt) {
      this.measureAttack(this.attackPending);
      this.attackPending = null;
    }

    // En silence, on gèle les traqueurs : la dernière mesure reste valable
    // et le bruit ne dégrade pas la fenêtre d'analyse.
    if (rms >= gate) {
      for (const t of this.trackers.values()) t.process(chunk);
    }

    this.acc += chunk.length;
    if (this.acc >= HOP) {
      this.acc -= HOP;
      return this.tick();
    }
    return null;
  }

  // Temps de réponse 10 % → 90 % du régime établi, mesuré sur l'enveloppe
  // RMS (résolution ~10,7 ms). Le régime établi est la médiane de
  // l'enveloppe entre 0,65 et 1 s après l'attaque.
  measureAttack({ onsetT, evalAt }) {
    const seg = this.env.filter((e) => e.t >= evalAt - 0.35 && e.t <= evalAt);
    if (seg.length < 5) return;
    const sorted = seg.map((e) => e.rms).sort((a, b) => a - b);
    const steady = sorted[sorted.length >> 1];
    if (steady < this.gate * 4) return;
    let t10 = null, t90 = null;
    for (const e of this.env) {
      if (e.t < onsetT - 0.08) continue;
      if (t10 == null && e.rms >= 0.1 * steady) t10 = e.t;
      if (t10 != null && e.rms >= 0.9 * steady) { t90 = e.t; break; }
    }
    if (t10 != null && t90 != null && t90 >= t10) {
      // Taux de croissance exponentiel σ : le démarrage d'une anche est une
      // instabilité linéaire, l'amplitude croît en A·e^(σt) — σ est le
      // paramètre physique du « parler » de l'anche (ajustement de ln(RMS)
      // par moindres carrés sur la zone de montée 10 % → 90 %).
      let sigma = null;
      let n = 0, sx = 0, sy = 0, sxx = 0, sxy = 0;
      for (const e of this.env) {
        if (e.t < t10 || e.t > t90 || e.rms <= 0) continue;
        const x = e.t - onsetT;
        const y = Math.log(e.rms);
        n++; sx += x; sy += y; sxx += x * x; sxy += x * y;
      }
      const denom = n * sxx - sx * sx;
      if (n >= 4 && denom > 1e-12) sigma = (n * sxy - sx * sy) / denom;
      this.lastAttack = {
        t: onsetT,
        riseMs: (t90 - t10) * 1000,
        sigma,
        midi: this.playedMidi,
        steadyDb: 20 * Math.log10(steady + 1e-12),
      };
    }
  }

  tick() {
    const c = this.cfg;
    const level = Math.sqrt(this.rmsAcc / Math.max(1, this.rmsN));
    this.rmsAcc = 0; this.rmsN = 0;
    const peak = this.peakAcc; this.peakAcc = 0;
    const quiet = level < this.gate;
    const calib = 1 + (c.calibrationPpm || 0) * 1e-6;

    // En silence, la détection de note n'a rien à détecter : la FFT large
    // bande (le poste de calcul dominant, ~5 ms) est sautée — l'accordeur
    // au repos ne consomme presque rien. L'affichage du spectre garde la
    // dernière image côté interface.
    const priorF0 = this.playedMidi != null ? midiToFreq(this.playedMidi, c) : null;
    const coarse = (!quiet && this.coarse.ready()) ? this.coarse.analyze(priorF0) : null;
    if (coarse) this.lastCoarse = coarse;   // sert à vérifier qu'un partiel existe (unisonHarmonic)
    let f0 = coarse?.f0 ? coarse.f0.freq * calib : null;

    // Détection temporelle McLeod (NSDF) : hauteur monophonique robuste aux
    // erreurs d'octave, à faible latence. Sert d'ancre d'octave à la
    // détection spectrale et de source au suivi continu. En mode registre
    // (plusieurs anches à l'unisson), la NSDF est moins fiable (les creux de
    // battement brouillent la période) : on ne l'y écoute que très franche.
    // Elle y est pourtant précieuse : sur un registre à l'octave dont la
    // fondamentale grave est faible (bandonéon Mi2+Mi3, Ballone Burini), la
    // FFT bascule sur Mi3 au bout de 3 s et tout le registre glisse d'une
    // octave ; la NSDF, elle, tient Mi2 (clarté 0,99).
    const poly = c.mode === 'register';
    const nsdfEst = (!quiet && this.coarse.ready())
      ? this.nsdf.estimateFromRing(this.coarse.ring, this.coarse.wpos, this.coarse.win)
      : null;
    const nf0 = nsdfEst ? nsdfEst.f0 * calib : null;
    const clarity = nsdfEst ? nsdfEst.clarity : 0;
    // Ancre NSDF : la fondamentale spectrale peut, sur un signal réel, tomber
    // sur un sous-multiple aberrant (ex. f/4 sur une voix : mesuré 38 Hz pour
    // 155 Hz réels) — la FFT « explique » alors les partiels par une
    // fondamentale trop grave. La NSDF, robuste à l'octave, ne fait pas cette
    // erreur : quand elle est franche (clarté ≥ 0,85) et qu'elle contredit
    // nettement la valeur spectrale (> 40 cents), on adopte la NSDF. Sinon on
    // garde la mesure spectrale (plus fine sur ton établi).
    if (f0 && nf0 && clarity >= (poly ? 0.95 : 0.85) && Math.abs(centsBetween(f0, nf0)) > 40) {
      f0 = nf0;
    }

    // Note verrouillée par l'utilisateur : la détection est court-circuitée.
    if (c.lockNote != null && c.mode !== 'manual' && !this.chordDegrees()) {
      if (this.playedMidi !== c.lockNote) {
        this.playedMidi = c.lockNote;
        this.retune();
      }
    } else if (this.chordDegrees()) {
      // Accord : reconnu dans les raies du spectre, confirmé sur 3 images
      // comme une note (mêmes gardes : niveau franc, 0,2 s après bascule).
      const tNow = this.samplesTotal / this.sr;
      const auto = c.mode === 'chord' && c.chordType === 'auto';
      const ch = (!quiet && coarse)
        ? (auto
          ? chordAuto(coarse.peaks, { a4: c.a4, prev: this.chord })
          : chordFromPeaks(coarse.peaks, this.chordDegrees(), { a4: c.a4, prevRoot: this.chord?.rootPc ?? null,
            prevNotes: this.chord?.notes.map((n) => n.midi) ?? null }))
        : null;
      if (ch) ch.degrees = ch.notes.map((n) => n.semi);
      if (ch) {
        const sig = ch.notes.map((n) => n.midi).join(',');
        const cur = this.chord ? this.chord.notes.map((n) => n.midi).join(',') : null;
        const need = this.chord == null ? 2 : 3;
        const held = tNow - (this.lastSwitchT ?? -1e9) < 0.2;
        const loud = level > this.gate * 4;
        if (sig === cur) {
          this.candCount = 0;
        } else if (sig === this.candChord) {
          if (++this.candCount >= need && !held && loud) {
            this.chord = ch;
            this.playedMidi = ch.rootMidi;
            this.candCount = 0;
            this.lastSwitchT = tNow;
            this.retune();
          }
        } else {
          this.candChord = sig;
          this.candCount = 1;
        }
      }
    } else if (!quiet && f0 && c.mode !== 'manual') {
      let midi = nearestMidi(f0, c);
      if (c.mode === 'register') {
        // La fondamentale détectée correspond à la voix la plus grave.
        const minOct = Math.min(...this.voices().map((v) => v.oct));
        midi -= 12 * minOct;
      }
      if (midi >= MIDI_MIN && midi <= MIDI_MAX) {
        // Première acquisition : bascule rapide (2 trames). Note déjà tenue :
        // confirmation plus longue (3 trames) + délai de garde de 0,2 s après
        // une bascule, le temps que le traqueur fin converge — sans ça, une
        // anche réelle riche en partiels fait vaciller la note (octave/quinte)
        // et re-centre les traqueurs à chaque trame (« convergence 0 % »).
        const tNow = this.samplesTotal / this.sr;
        const need = this.playedMidi == null ? 2 : 3;
        const held = tNow - (this.lastSwitchT ?? -1e9) < 0.2;
        // Une vraie note s'établit avec de l'énergie : ne pas basculer sur le
        // bruit d'un extinction (vibration libre décroissante) où la détection
        // part sur des harmoniques isolées (fausses notes très aiguës). La note
        // tenue persiste tant que le niveau est faible.
        const loud = level > this.gate * 4;
        if (midi === this.playedMidi) {
          this.candCount = 0;
        } else if (midi === this.candMidi) {
          if (++this.candCount >= need && !held && loud) {
            this.playedMidi = midi;
            this.candCount = 0;
            this.lastSwitchT = tNow;
            this.retune();
          }
        } else {
          this.candMidi = midi;
          this.candCount = 1;
        }
      }
    }
    if (c.mode === 'manual' && this.trackers.size === 0) this.retune(true);

    // Retour du son après un silence — typiquement l'inversion du soufflet :
    // ce ne sont plus les mêmes anches qui parlent (tiré / poussé), ni la
    // même hauteur. Les traqueurs, gelés pendant le silence, contiennent
    // encore l'autre sens : on les fait repartir de zéro. La courbe montre
    // alors un trou franc puis la nouvelle hauteur, au lieu de traîner
    // l'ancienne valeur puis de sauter (mesuré sur une session d'Ewen :
    // valeur figée 0,5 s après la reprise, puis saut de 4 à 6 ¢).
    {
      const tNow = this.samplesTotal / this.sr;
      if (quiet) {
        if (this.silentSince == null) this.silentSince = tNow;
      } else if (this.silentSince != null) {
        this.silentSince = null;
        for (const tr of this.trackers.values()) tr.restart(RESUME_KEEP);
        this.stab = new Map();   // pas de maintien À TRAVERS le silence : l'autre sens n'est pas celui-ci
        this.prevF = new Map();
        this.steps = new Map();
        this.lastFine = null;
        this.disagreeSince = null;
        this.resume = { t: tNow, midi: this.playedMidi };
      }
    }

    // Mesures fines par groupe, du grave vers l'aigu : les harmoniques des
    // voix déjà mesurées sont « revendiquées » pour que, par exemple, la 2e
    // harmonique du 16' ne soit pas prise pour la fondamentale du 8'.
    const maxWin = MAXWIN[c.response] ?? 256;
    const groups = [];
    const played = this.playedMidi;
    const claimed = [];
    const claimedBy = [];   // centre du groupe qui revendique chaque fréquence de `claimed`
    // Fondamentale mesurée par centre d'octave : un groupe harmonique cherche
    // son partiel autour de k·f0_mesurée plutôt que k·f0_nominale. Sans cet
    // ancrage, quand la fondamentale est décalée (ex. +9 ¢), le vrai partiel
    // (lui aussi à +9 ¢) et une raie parasite proche du nominal (0 ¢) sont
    // quasi équidistants de la cible nominale : l'appariement bascule de
    // l'un à l'autre → pics discontinus sur la courbe des harmoniques.
    const baseFByCenter = new Map();
    const baseVoicesByKey = new Map();   // voix de base par groupe (ancres des partiels)
    // Tri par centre, puis explicitement base → harmonique → sous-harmonique
    // à centre égal : garantit que le groupe de base remplit `baseFByCenter`
    // avant que ses groupes harmoniques ne le lisent (indépendant de la
    // stabilité de sort()).
    const rank = (g) => (g.isSub ? 2 : g.isHarmonic ? 1 : 0);
    const defs = this.groupVoices(played ?? 0)
      .sort((a, b) => (a.center - b.center) || (rank(a) - rank(b)));
    for (const g of defs) {
      if (played == null && c.mode !== 'manual') break;
      const t = this.trackers.get(g.key);
      if (!t) continue;
      // Raies gardées : plusieurs par anche. Sous un soufflet qui module, un
      // partiel est un amas (porteuse + raies latérales, parfois plus fortes
      // qu'elle) : avec une seule raie de plus que d'anches, les amas des
      // deux anches les plus fortes prenaient toutes les places et la
      // troisième n'avait plus de raie (MMM, soufflet ±1 ¢ : 8'+ lu à −5,7 ¢).
      const az = t.analyze(maxWin, 3 * g.voices.length + 3);
      let anchor = null;
      if (g.isPartial) {
        // Une ancre PAR anche : son partiel k est cherché autour de k fois sa
        // propre fondamentale mesurée, pas autour de celle d'une voisine.
        anchor = new Map();
        for (const bv of baseVoicesByKey.get(g.baseKey) ?? []) {
          if (bv.tracked) anchor.set(bv.def.id, bv.fMeas * g.kTrack);
        }
      } else if (g.isHarmonic && !g.isSub) {
        const bf = baseFByCenter.get(g.center);
        if (bf) anchor = bf * g.kTrack;
      }
      // Continuité temporelle de la voix de base (auto, une anche) : préférer
      // la composante la plus proche de la dernière mesure fine plutôt que la
      // plus proche du nominal, pour rester accroché à LA MÊME anche quand deux
      // anches battent (sinon la fondamentale saute de l'une à l'autre au
      // rythme du battement → discontinuités).
      let cont = null;
      if (!g.isHarmonic && !g.isSub && c.mode === 'auto' && g.voices.length === 1
          && this.lastFine && (this.samplesTotal / this.sr) - this.lastFine.t < 0.5) {
        cont = this.lastFine.f;
      }
      const voices = this.matchVoices(g, az, calib, claimed, anchor, cont);
      // Mode Automatique : deux raies franches au lieu d'une autour de la note
      // (trémolo joué en « une anche ») → on le signalera (tick.unison).
      if (c.mode === 'auto' && !g.isHarmonic && !g.isSub && !quiet && az?.components?.length > 1) {
        const k = g.kTrack || 1;
        const near = az.components.filter((cp) => Math.abs(centsBetween(cp.freq / k, g.center)) < 60);
        let mMax = 0;
        for (const cp of near) mMax = Math.max(mMax, cp.mag);
        const strongC = near.filter((cp) => cp.mag >= mMax * 0.15).sort((a, b) => b.mag - a.mag);
        const sep = strongC.length > 1 ? Math.abs(centsBetween(strongC[1].freq, strongC[0].freq)) : 0;
        if (sep > 3) {
          if (this.unisonSince == null) this.unisonSince = this.samplesTotal / this.sr;
          this.unison = { cents: sep };
        } else {
          this.unisonSince = null;
        }
      }
      if (!quiet) {
        const others = claimed.filter((_, i) => claimedBy[i] !== g.center);
        this.detectStep(g, t, voices, calib, others, az);
      }
      // Auto-anches : une octave ajoutée à la main (16', 4', 2') n'est
      // déclarée présente que sur preuve. Pas de partiel à elle dans le
      // spectre large bande → rien ; et une raie confondue avec le partiel
      // d'une autre anche ne prouve rien (en mode registre, où l'anche est
      // déclarée, on l'affiche au contraire, marquée confondue).
      if (c.mode === 'reeds' && !g.isHarmonic && (g.voices[0].def.oct ?? 0) !== 0) {
        const present = partialPresent(this.lastCoarse, g.center, g.kTrack);
        for (const v of voices) if (!present || v.merged) this.fillVoice(v, null, az?.W);
      }
      // On ne publie pas ce qui ne peut pas encore être séparé : sur ce
      // partiel, les anches doivent être écartées d'au moins 4 cases de la
      // FFT courante. Avant, la bande du strobe resterait vide plutôt que de
      // montrer une valeur polluée par la voisine.
      if (g.isPartial && az && targetSpacing(g) < 4 * (az.srd / az.W)) {
        for (const v of voices) this.fillVoice(v, null, az.W);
      }
      if (!g.isHarmonic) baseVoicesByKey.set(g.key, voices);
      if (!g.isHarmonic) {
        // Les harmoniques mesurées d'une voix de base sont « revendiquées »
        // pour les groupes plus aigus ; les groupes harmoniques, eux,
        // mesurent précisément ces fréquences-là et n'en revendiquent pas.
        for (const v of voices) {
          if (!v.tracked) continue;
          for (let m = 2; m <= 24; m++) {
            const f = m * v.fMeas;
            if (f > 9600) break;
            claimed.push(f);
            claimedBy.push(g.center);
          }
        }
        // Fondamentale de référence du groupe (voix sans battement, ou la
        // plus forte) → ancre des groupes harmoniques de même centre.
        if (!g.isSub) {
          const ref = voices.find((v) => v.def.beatSign === 0 && v.tracked)
            ?? voices.filter((v) => v.tracked).sort((a, b) => b.amp - a.amp)[0];
          if (ref) baseFByCenter.set(g.center, ref.fMeas);
        }
      }
      groups.push({
        key: g.key,
        center: g.center,
        kTrack: g.kTrack,
        fc: g.fc,
        isHarmonic: !!g.isHarmonic,
        isSub: !!g.isSub,
        hidden: !!g.hidden,
        isPartial: !!g.isPartial,
        avoidEven: !!g.avoidEven,
        baseKey: g.baseKey ?? null,
        srd: t.srd,
        W: az?.W ?? 0,
        fill: az?.fill ?? 0,
        spectrum: az ? az.mags : null,

        voices,
      });
    }

    // Mode automatique : repli « suivi continu » quand le traqueur fin n'a
    // pas (encore) accroché — voix chantée, glissando large, ou les premières
    // centaines de ms après un changement de note. La fondamentale de
    // l'analyse rapide alimente alors la mesure. Elle ne remplace PLUS une
    // mesure fine qui existe : avant, dès que la hauteur bougeait de 5 ¢ en
    // 0,5 s, elle prenait la main jusqu'à retomber à 3 ¢ de la mesure fine —
    // or sur un vrai son elle se trompe de 5 à 15 ¢ (mesuré), et la courbe
    // alternait entre les deux. C'est désormais le traqueur fin qui suit le
    // mouvement, en raccourcissant sa fenêtre (detectStep).
    if (c.mode === 'auto' && !quiet && f0 && played != null) {
      const g = groups.find((gr) => !gr.isHarmonic && !gr.isSub);
      const v = g?.voices[0];
      const tNow = this.samplesTotal / this.sr;
      // Source du suivi : la NSDF (fenêtre 85 ms, sans erreur d'octave) suit
      // une hauteur qui bouge de plus près que la FFT grossière (341 ms) ;
      // repli sur la fondamentale spectrale si la NSDF n'est pas franche.
      const followF0 = (nf0 && clarity >= 0.7) ? nf0 : f0;
      // Maintien valable si la dernière mesure fine est récente ET que la
      // hauteur n'a pas vraiment bougé (l'estimation rapide reste proche) : un
      // battement fait osciller f0 autour d'une moyenne stable (→ on tient),
      // un glissando l'en éloigne (→ suivi rapide).
      const holdOk = this.lastFine && tNow - this.lastFine.t < 0.5
        && Math.abs(centsBetween(followF0, this.lastFine.f)) < 15;
      if (v && !v.tracked && holdOk) {
        // Creux de battement : le zoom perd brièvement l'accroche quand deux
        // anches battent (amplitude qui module). La hauteur, elle, ne bouge
        // pas — on TIENT la dernière mesure fine plutôt que de sauter sur
        // l'estimation rapide, qui provoquait des discontinuités sur la courbe
        // à chaque battement (fondamentale en dents de scie, harmoniques
        // stables). Repli sur le suivi rapide seulement si la perte se prolonge.
        v.fMeas = this.lastFine.f;
        v.amp = level;
        v.dCents = centsBetween(v.fMeas, v.nominal);
        v.dHz = v.fMeas - v.nominal;
        v.dTargetCents = centsBetween(v.fMeas, v.target);
        v.tracked = true;
        v.held = true; // maintenu pendant un creux, ni fin ni rapide
        v.beatMeas = 0;
      } else if (v && !v.tracked && Math.abs(centsBetween(followF0, v.nominal)) < 120
          // Juste après une reprise sur la même note, les traqueurs se
          // remplissent (~0,4 s) : un trou vaut mieux qu'une estimation rapide
          // fausse de plusieurs cents.
          && !(this.resume && this.resume.midi === played && tNow - this.resume.t < 0.6)
          // …ni au début d'une note : la mesure fine arrive en ~0,4 s, et
          // l'estimation rapide y variait de ±4 ¢ d'une image à l'autre
          // (mesuré) — des pics sur la courbe. Elle ne sert plus qu'à suivre
          // une hauteur qui bouge trop pour la mesure fine (chant, glissando).
          && tNow - (this.retuneT ?? -1e9) >= 0.6) {
        v.fMeas = followF0;
        v.amp = level;
        v.dCents = centsBetween(followF0, v.nominal);
        v.dHz = followF0 - v.nominal;
        v.dTargetCents = centsBetween(followF0, v.target);
        v.tracked = true;
        v.coarse = true; // estimation rapide, pas la mesure fine du zoom
        v.beatMeas = 0;
      }
    }

    // Fusion multi-harmonique cohérente : les fréquences des partiels
    // (ramenées à la fondamentale) sont combinées avec des poids ∝ (A·k)² —
    // la variance d'une mesure au partiel k s'améliore en k². Seuls les
    // partiels cohérents avec le modèle harmonique (< 1,5 cent de la
    // fondamentale mesurée) participent : les partiels étirés d'une anche
    // inharmonique sont écartés d'office, la robustesse est préservée.
    if (c.mode === 'auto' && c.fuseHarmonics !== false && !quiet) {
      const base = groups.find((gr) => !gr.isHarmonic && !gr.isSub);
      const bv = base?.voices[0];
      if (bv?.tracked && !bv.coarse) {
        const wBase = (bv.amp * (base.kTrack || 1)) ** 2;
        let num = wBase * bv.fMeas;
        let den = wBase;
        let nFused = 1;
        let ampRef = bv.amp;
        for (const g of groups) if (g.isHarmonic && !g.isSub && g.voices[0]?.tracked) ampRef = Math.max(ampRef, g.voices[0].amp);
        let worst = null;                 // partiel le plus en désaccord avec la voix de base
        for (const g of groups) {
          if (!g.isHarmonic || g.isSub) continue;
          const v = g.voices[0];
          if (!v?.tracked) continue;
          const fEq = v.fMeas / g.kTrack; // fMeas en domaine du partiel
          if (!v.step && v.amp >= ampRef / 31.6) {
            const sd = centsBetween(fEq, bv.fMeas);
            if (!worst || Math.abs(sd) > Math.abs(worst.cents)) worst = { k: g.kTrack, cents: sd };
          }
          // Porte PROGRESSIVE : poids plein jusqu'à 0,5 ¢ d'écart, nul à 1,5 ¢.
          // Une porte franche faisait entrer et sortir un partiel d'une image à
          // l'autre quand il frôlait le seuil : une marche sur la courbe à
          // chaque passage.
          const dev = Math.abs(centsBetween(fEq, bv.fMeas));
          if (dev >= 1.5) continue;
          const taper = dev <= 0.5 ? 1 : (1.5 - dev);
          const w = taper * (v.amp * g.kTrack) ** 2;
          num += w * fEq;
          den += w;
          nFused++;
        }
        // Une anche seule en régime est périodique : ses partiels disent
        // EXACTEMENT la même hauteur (mesuré : à 0,1 ¢ près sur les samples
        // Ballone Burini). S'ils restent en désaccord plus de 1,5 s, ce sont
        // deux anches (octave, quinte…) que le mode Automatique fond à tort
        // en une seule valeur — on le signale (cf. app.js).
        const tNow = this.samplesTotal / this.sr;
        if (worst && Math.abs(worst.cents) > DISAGREE_CENTS) {
          if (this.disagreeSince == null) this.disagreeSince = tNow;
          this.disagree = { k: worst.k, kBase: base.kTrack || 1, cents: worst.cents };
        } else {
          this.disagreeSince = null;
        }
        if (nFused > 1) {
          bv.fMeas = num / den;
          bv.dCents = centsBetween(bv.fMeas, bv.nominal);
          bv.dHz = bv.fMeas - bv.nominal;
          bv.dTargetCents = centsBetween(bv.fMeas, bv.target);
          bv.fusedN = nFused;
        }
      }
    }

    // Mémorise la dernière mesure fine de la voix de base (ni rapide ni
    // maintenue) : elle sert à tenir la valeur pendant les creux de battement
    // plutôt que de sauter sur l'estimation rapide.
    if (c.mode === 'auto' && !quiet) {
      const bv = groups.find((gr) => !gr.isHarmonic && !gr.isSub)?.voices[0];
      if (bv?.tracked && !bv.coarse && !bv.held) {
        this.lastFine = { t: this.samplesTotal / this.sr, f: bv.fMeas };
      }
    }

    // Les bandes sous-harmoniques ne comptent comme détectées que si leur
    // niveau dépasse −55 dB par rapport à la voix la plus forte : en deçà,
    // c'est du bruit de fond, pas une bifurcation.
    let baseAmp = 0;
    for (const g of groups) {
      if (g.isSub) continue;
      for (const v of g.voices) if (v.tracked && v.amp > baseAmp) baseAmp = v.amp;
    }
    const subFloor = baseAmp * Math.pow(10, -55 / 20);
    for (const g of groups) {
      if (!g.isSub) continue;
      for (const v of g.voices) {
        if (v.tracked && v.amp < subFloor) this.fillVoice(v, null);
      }
    }

    // Plancher harmonique −42 dB : un partiel très en deçà de la fondamentale
    // est noyé dans le bruit, la zone où le traqueur zoom se verrouille sur une
    // raie parasite. Mieux vaut une lacune franche dans la courbe qu'un pic
    // discontinu — l'anche restant strictement périodique, une harmonique
    // trop faible pour être mesurée proprement n'apporte aucune information.
    const harmFloor = baseAmp * Math.pow(10, -42 / 20);
    for (const g of groups) {
      if (!g.isHarmonic || g.isSub) continue;
      for (const v of g.voices) {
        if (v.tracked && v.amp < harmFloor) this.fillVoice(v, null);
      }
    }

    // Auto-anches : ne compter que les vraies anches, pas le bruit ni les
    // harmoniques. Deux filtres :
    //   1) plancher global −25 dB (une octave vide verrouille sur du bruit) ;
    //   2) rejet harmonique — le partiel k d'une anche grave tombe pile sur la
    //      fondamentale d'une octave supérieure (le 4' est à 2× le 8') : une
    //      anche dont la fréquence coïncide (< 8 cents) avec k× une anche plus
    //      grave ET plus forte est cette harmonique, pas une anche distincte.
    //      Une vraie anche d'octave désaccordée (battement) y échappe.
    if (c.mode === 'reeds') {
      const reedFloor = baseAmp * Math.pow(10, -25 / 20);
      for (const g of groups) {
        for (const v of g.voices) {
          if (v.tracked && v.amp < reedFloor) this.fillVoice(v, null);
        }
      }
      const kept = [];
      for (const g of groups) for (const v of g.voices) if (v.tracked) kept.push(v);
      kept.sort((a, b) => a.fMeas - b.fMeas);
      for (let i = 0; i < kept.length; i++) {
        const v = kept[i];
        for (let j = 0; j < i; j++) {
          const lo = kept[j];
          if (!lo.tracked || lo.amp <= v.amp) continue;
          const k = Math.round(v.fMeas / lo.fMeas);
          if (k >= 2 && Math.abs(centsBetween(v.fMeas, k * lo.fMeas)) < 8) {
            this.fillVoice(v, null); // c'est l'harmonique k de `lo`
            break;
          }
        }
      }
    }

    // Écart rapide de la fondamentale à la note nominale : c'est la donnée
    // à utiliser pour la caractéristique pression-hauteur f(I) — la mesure
    // fine (longue fenêtre) traîne derrière un balayage de pression et
    // biaiserait la pente vers zéro.
    let f0Cents = null;
    if (f0 && played != null) {
      const bn = groups.find((g) => !g.isHarmonic && !g.isSub)?.voices[0]?.nominal;
      if (bn) {
        const cts = centsBetween(f0, bn);
        if (Math.abs(cts) < 120) f0Cents = cts;
      }
    }

    // Analyse paramétrique à sous-espaces (Matrix Pencil) sur la bande de
    // base hétérodyne de la voix de base : sépare les anches d'un unisson
    // sous la limite de Fourier (résolution en ~1 s au lieu de ~5,5 s) et
    // donne l'amortissement/croissance α de chaque composante. Optionnelle
    // (coûteuse) : n'affecte ni la mesure principale ni les autres modes.
    if (c.subspace && !quiet && played != null) {
      const bg = groups.find((g) => !g.isHarmonic && !g.isSub);
      const t = bg && this.trackers.get(bg.key);
      const bb = t ? t.baseband(48) : null;
      if (bg && bb) {
        const nExp = bg.voices.length;
        // Ordre du modèle : en registre/manuel le nombre d'anches est connu →
        // on le prend exactement (un pôle en trop s'ajusterait sur le bruit).
        // En auto (1 voix attendue) on autorise un pôle de plus pour révéler
        // une seconde composante cachée (unisson non déclaré).
        const known = c.mode === 'register' || c.mode === 'manual';
        const M = Math.max(1, Math.min(4, known ? nExp : nExp + 1));
        const k = bg.kTrack || 1;
        let comps = [];
        try { comps = matrixPencil(bb.re, bb.im, M, bb.srd); } catch { comps = []; }
        // Bruit de fond : ne garder que les composantes franches (> 5 % de la
        // plus forte) et retomber en fréquence de fondamentale (÷k).
        let aMax = 0;
        for (const cp of comps) if (cp.amp > aMax) aMax = cp.amp;
        bg.subspace = comps
          .map((cp) => {
            const fAbs = (bb.fc + cp.freq) / k;
            return {
              freq: fAbs,
              cents: centsBetween(fAbs, bg.center),
              damping: cp.damping,
              amp: cp.amp,
            };
          })
          // Franches (> 8 % de la plus forte) et dans la bande de la note
          // (± un demi-ton) : écarte les pôles ajustés sur le bruit résiduel.
          .filter((cp) => cp.amp >= aMax * 0.08 && Math.abs(cp.cents) < 120)
          .sort((a, b) => a.freq - b.freq);
      }
    }

    if (!quiet) this.stabilize(groups);
    const beat = quiet ? null : this.measureBeat(groups);

    return {
      type: 'tick',
      version: ENGINE_VERSION,
      time: this.samplesTotal / this.sr,
      level,
      peak,         // crête du signal (1 = pleine échelle) : saturation du micro si ≥ 0,98
      quiet,
      f0,
      f0Cents,
      // Mode Automatique : partiels en désaccord depuis plus de 1,5 s → sans
      // doute deux anches. { k, kBase, cents } ou null.
      beat,
      chord: this.chordDegrees() && this.chord
        ? { rootPc: this.chord.rootPc, rootMidi: this.chord.rootMidi, notes: this.chord.notes,
          type: this.chord.type ?? null } : null,
      // Mode Automatique : deux anches à l'unisson (trémolo) depuis plus de
      // 1,5 s → { cents : écart entre elles } ou null.
      unison: c.mode === 'auto' && !quiet && this.unisonSince != null
        && this.samplesTotal / this.sr - this.unisonSince >= DISAGREE_HOLD_S ? this.unison : null,
      partialsDisagree: c.mode === 'auto' && !quiet && this.disagreeSince != null
        && this.samplesTotal / this.sr - this.disagreeSince >= DISAGREE_HOLD_S ? this.disagree : null,
      clarity,
      playedMidi: played,
      transpose: c.transpose,
      lockNote: c.lockNote ?? null,
      attack: this.lastAttack,
      // Les groupes cachés (traqueurs de fusion) ne sont pas transmis :
      // ils servent au calcul, pas à l'affichage.
      groups: withPartials(groups),
      coarseSpectrum: coarse ? logResample(coarse.mag, coarse.binHz, 1024) : null,
    };
  }

  // Battement du trémolo, en battements par seconde (× 60 = par minute) —
  // demande d'Ewen : « deux anches en vibrato : combien de fois par minute ça
  // bat ? ». Lu dans l'enveloppe de chaque partiel suivi de la note (cf.
  // ZoomTracker.beatFromEnvelope), puis on tranche :
  //  - deux anches d'écart Δf : le partiel k bat à k·Δf → les rythmes bruts
  //    divisés par leur rang s'accordent ; le battement est Δf ;
  //  - modulation d'ensemble (secousse du soufflet, boucle d'un sample) :
  //    tous les partiels battent au même rythme brut.
  // Mesuré sur un Mi2 Ballone Burini : 1,23 Hz sur le partiel 2 ET sur le
  // partiel 4 → modulation à 1,23 Hz, pas deux anches à 0,62 Hz.
  // En registre (deux anches séparées dans le spectre), l'écart des deux
  // fréquences mesurées est plus précis : on le donne aussi.
  measureBeat(groups) {
    const base = groups.find((g) => !g.isHarmonic && !g.isSub);
    if (!base) return null;
    const pair = base.voices.find((v) => v.tracked && v.beatMeas != null && Math.abs(v.beatMeas) > 0.01);
    const raws = [];
    for (const g of groups) {
      if (g.isSub || g.center !== base.center) continue;
      const t = this.trackers.get(g.key);
      const k = g.kTrack || 1;
      if (!t || raws.some((r) => r.k === k)) continue;
      const b = t.beatFromEnvelope(1);
      if (b && b.conf >= 0.4) raws.push({ k, hz: b.hz, conf: b.conf, depth: b.depth });
    }
    let out = null;
    // Décision robuste : pour chaque hypothèse, la médiane des estimations et
    // le nombre de partiels qui s'y accordent à 3 % près. Un partiel dont les
    // deux anches sortent de la bande analysée (k·Δf > 14 Hz) donne n'importe
    // quoi : il ne sera simplement pas « d'accord ».
    const ok = raws.filter((r) => r.hz <= 14);
    if (ok.length) {
      const judge = (vals) => {
        const sorted = [...vals].sort((x, y) => x - y);
        const med = sorted[sorted.length >> 1];
        const agree = vals.filter((v) => Math.abs(v - med) <= 0.03 * med);
        return { hz: agree.reduce((x, y) => x + y, 0) / agree.length, n: agree.length };
      };
      const reeds = judge(ok.map((r) => r.hz / r.k));
      const mod = judge(ok.map((r) => r.hz));
      const pick = mod.n > reeds.n ? { ...mod, kind: 'modulation' } : { ...reeds, kind: 'anches' };
      out = { hz: pick.hz, kind: pick.kind, conf: ok[0].conf, depth: ok[0].depth,
        sure: pick.n >= 2 && (pick.kind === 'anches' ? reeds.n > mod.n : true) };
      out.nPartials = pick.n;
    }
    if (pair) {
      out = { ...(out ?? {}), pairHz: Math.abs(pair.beatMeas) };
      if (out.hz == null) { out.hz = out.pairHz; out.kind = 'anches'; out.sure = true; }
    }
    return out;
  }

  // Sortie stabilisée de chaque anche affichée (demande d'Ewen : « des
  // courbes avec des trous ou des pics ne sont pas exploitables »).
  //  - Pas de trou : une anche qui perd la mesure une image (fenêtre qui se
  //    remplit après une reprise, raie brièvement couverte) garde sa dernière
  //    valeur, jusqu'à STAB_HOLD_S, marquée « maintenue ».
  //  - Pas de pic : médiane des 3 dernières mesures (une image de retard,
  //    ~85 ms). Une vraie marche détectée (detectStep) remet la médiane à
  //    zéro : elle n'est pas retardée.
  // Tout repart de zéro au changement de note ou d'accord (retune).
  stabilize(groups) {
    const tNow = this.samplesTotal / this.sr;
    for (const g of groups) {
      if (g.isSub || g.isPartial || g.hidden) continue;
      for (const v of g.voices) {
        const key = `${g.key}:${v.def.id}`;
        let st = this.stab.get(key);
        if (v.tracked && !v.coarse) {
          if (!st || v.step || v.held) st = { recent: [] };
          if (!v.held) {
            st.recent.push(v.fMeas);
            if (st.recent.length > 3) st.recent.shift();
          }
          const sorted = [...st.recent].sort((a, b) => a - b);
          if (sorted.length) v.fMeas = sorted[sorted.length >> 1];
          st.f = v.fMeas; st.t = tNow; st.amp = v.amp;
          this.stab.set(key, st);
        } else if (!v.tracked && st?.f != null && tNow - st.t < STAB_HOLD_S) {
          v.fMeas = st.f;
          v.amp = st.amp;
          v.tracked = true;
          v.held = true;
        } else {
          continue;
        }
        v.dCents = centsBetween(v.fMeas, v.nominal);
        v.dHz = v.fMeas - v.nominal;
        v.dTargetCents = centsBetween(v.fMeas, v.target);
      }
    }
  }

  // Saut de hauteur. La mesure fine est une moyenne sur une longue fenêtre
  // (2,7 s en « normal ») : précieuse sur un ton tenu, elle étale une marche
  // nette en une rampe de 2,7 s, en retard d'1,4 s. Une vraie marche existe
  // (anche du tiré et anche du poussé d'un même bouton, accordées un peu
  // différemment). Sur l'enregistrement d'Ewen (Do3 au téléphone,
  // 24/09/2026), le son sautait de −9 à +6 ¢ en moins de 50 ms — c'était
  // l'horloge du navigateur (cf. worker.js, readStream), mais le moteur, lui,
  // en faisait une colline lisse et fausse sur les harmoniques, et la
  // fondamentale alternait entre cette moyenne en retard et l'estimation
  // rapide (fausse de 5 à 15 ¢ sur ce son) : des « signaux carrés ».
  //
  // Ici, une fenêtre courte (~0,17 s) regarde la même raie. Si elle s'écarte
  // de la mesure fine de plus de STEP_CENTS en restant sur un palier, le
  // traqueur oublie l'avant : sa fenêtre repart courte puis regrandit. Chaque
  // traqueur (anche, H2, H3…) le fait pour son propre partiel. Une anche
  // stable n'est jamais concernée (la fenêtre courte y tombe à quelques
  // centièmes de cent de la longue) ; un soufflet qui ondule d'un cent non
  // plus.
  detectStep(g, t, voices, calib, others = [], az = null) {
    if (voices.length !== 1 || !t || g.isSub) return;   // un unisson bat : pas une marche
    const v = voices[0];
    const key = g.key;
    // Référence : la mesure fine de cette image, ou, pour l'anche de base,
    // si elle vient de se perdre (la longue fenêtre voit l'ancienne ET la
    // nouvelle hauteur, le verrou de continuité refuse les deux), la
    // dernière connue.
    const ref = v.tracked ? v.fMeas
      : g.isHarmonic ? null
        : this.prevF?.get(`${key}:${v.def.id}`)
          ?? (this.cfg.mode === 'auto' && this.lastFine
            && this.samplesTotal / this.sr - this.lastFine.t < 1.5 ? this.lastFine.f : null);
    if (ref == null) return;
    // Groupe de base : fréquences ramenées à la fondamentale ; groupe
    // harmonique : dans le domaine du partiel (cf. matchVoices).
    const div = g.isHarmonic ? 1 : (g.kTrack || 1);
    // Un partiel d'une AUTRE anche trop près (l'harmonique 2 du 16' à 1 Hz
    // du 8' d'un registre LM) : la fenêtre courte ne voit que leur somme,
    // qui bat. Seule la longue fenêtre les sépare — on ne la coupe pas.
    const fAbs = ref * div;
    const res = (2 * t.srd) / STEP_QW;                 // pouvoir séparateur de la fenêtre courte
    if (others.some((f) => Math.abs(f - fAbs) < res)) return;
    // Même chose avec une AUTRE anche du même groupe que la fenêtre longue voit
    // (trémolo joué en mode Automatique : mesuré, deux anches à 22 ¢ l'une de
    // l'autre sur un Sol♯4). La fenêtre courte voit leur somme et « saute »
    // vers la plus forte : ce n'est pas une marche.
    if (az?.components?.length > 1) {
      const fBand = fAbs / calib;
      let mine = null;
      for (const cp of az.components) if (!mine || Math.abs(cp.freq - fBand) < Math.abs(mine.freq - fBand)) mine = cp;
      if (az.components.some((cp) => cp !== mine && cp.mag > mine.mag / 10 && Math.abs(cp.freq - mine.freq) < res)) return;
    }
    const q = t.quick(fAbs / calib - t.fc, STEP_QW);
    const st = this.steps.get(key) ?? { fq: null, mag: 0 };
    this.steps.set(key, st);
    if (!q) { st.fq = null; return; }
    const fq = ((t.fc + q.off) * calib) / div;
    const d = centsBetween(fq, ref);
    // Palier atteint : la fenêtre courte ne bouge plus d'une image à l'autre,
    // ni en hauteur ni en niveau. Pendant la transition elle glisse de
    // l'ancienne hauteur à la nouvelle ; au passage d'un creux (inversion du
    // soufflet) elle peut donner n'importe quoi (mesuré : −22 ¢ au lieu de
    // −6 ¢) ; sur un partiel qui bat, hauteur et niveau y tournent sans
    // cesse (mesuré : H2 d'un Mi2 de bandonéon, −9 à +19 ¢ en 0,8 s). On
    // attend donc un palier franc.
    const plateau = st.fq != null
      && Math.abs(centsBetween(fq, st.fq)) < Math.max(STEP_PLATEAU, 0.3 * Math.abs(d))
      && Math.abs(20 * Math.log10((q.mag + 1e-30) / (st.mag + 1e-30))) < STEP_LEVEL_DB;
    st.fq = fq; st.mag = q.mag;
    // Une marche de plus de STEP_MAX_CENTS n'est pas une anche qui change de
    // hauteur (le tiré et le poussé d'une note diffèrent de quelques cents) :
    // c'est la fenêtre courte qui s'est accrochée ailleurs.
    if (Math.abs(d) <= STEP_CENTS || Math.abs(d) > STEP_MAX_CENTS || !plateau) return;
    t.restart(STEP_KEEP);
    // La mesure de cette image devient l'estimation courte : c'est elle qui
    // dit où est l'anche maintenant. La continuité suit.
    this.fillVoice(v, { freq: fq, mag: q.mag }, STEP_QW);
    v.step = true;
    if (g.isHarmonic) return;
    if (this.prevF) this.prevF.set(`${key}:${v.def.id}`, fq);
    if (this.cfg.mode === 'auto') this.lastFine = { t: this.samplesTotal / this.sr, f: fq };
  }

  // Associe les composantes mesurées aux voix attendues du groupe.
  // `claimed` : fréquences absolues (Hz) déjà expliquées comme harmoniques
  // de voix plus graves — elles ne sont utilisées qu'en dernier recours.
  matchVoices(group, az, calib, claimed = [], anchor = null, cont = null) {
    const expected = group.voices
      .map((v) => ({ ...v }))
      .sort((a, b) => a.target - b.target);
    const k = group.kTrack ?? 1;
    // Groupes de base : fréquences ramenées à la fondamentale (mesure sur le
    // partiel k). Groupes harmoniques : on reste dans le domaine du partiel,
    // sa fréquence réelle est la grandeur d'intérêt (inharmonicité).
    const div = group.isHarmonic ? 1 : k;
    // Ancrage harmonique : quand la fondamentale mesurée est connue, on
    // cherche le partiel autour de k·f0 (mt), pas autour du nominal — et dans
    // une fenêtre resserrée (±40 ¢) qui laisse passer l'inharmonicité réelle
    // mais interdit de sauter sur une raie parasite au voisinage du nominal.
    const useAnchor = anchor != null && group.isHarmonic && !group.isSub;
    for (const v of expected) v.mt = v.target;
    // Continuité par anche : chaque voix cherche d'abord là où SON anche était
    // à l'image précédente (mesure d'amas, donc sa hauteur moyenne), pas près
    // de la cible. Sinon, une raie latérale de soufflet qui tombe plus près
    // de la cible que l'anche elle-même lui était appariée. Garde-fou : la
    // mémoire n'est reprise que si elle reste dans la tolérance de la cible.
    if (!group.isHarmonic && this.prevF) {
      const tolMem = Math.max(2.5, group.center * 0.05);
      for (const v of expected) {
        const p = this.prevF.get(`${group.key}:${v.def.id}`);
        if (p != null && Math.abs(p - v.target) < tolMem) v.mt = p;
      }
    }
    if (useAnchor) {
      // Ancre par anche (Map id → fréquence du partiel) ou ancre unique.
      if (anchor instanceof Map) {
        for (const v of expected) if (anchor.has(v.def.id)) v.mt = anchor.get(v.def.id);
      } else {
        expected[0].mt = anchor;
      }
    }
    const anchorRef = anchor instanceof Map ? group.center * k : anchor;
    // Tolérance : ±85 cents en général ; ±40 cents pour un partiel ancré ;
    // ±20 cents pour les bandes sous-harmoniques (un doublement de période
    // est verrouillé sur la fondamentale — un pic éloigné est du bruit).
    const tolHz = group.isSub
      ? Math.max(1.5, group.fc * 0.012)
      : useAnchor
        ? Math.max(2.5, anchorRef * 0.023)
        : Math.max(2.5, (group.center * (group.isHarmonic ? k : 1)) * 0.05);
    let comps = az
      ? az.components.map((cp) => ({ ...cp, freq: (cp.freq * calib) / div }))
      : [];
    comps = comps.filter((cp) =>
      expected.some((v) => Math.abs(cp.freq - v.mt) < tolHz));
    // Plancher relatif : un pic à plus de 30 dB sous le plus fort du groupe
    // est une fuite spectrale ou du bruit, pas une anche — les anches d'un
    // même ton jouent à quelques dB les unes des autres. (Les bandes
    // sous-harmoniques, volontairement faibles, ne sont pas concernées.)
    if (!group.isSub && comps.length > 1) {
      let mMax = 0;
      for (const cp of comps) mMax = Math.max(mMax, cp.mag);
      comps = comps.filter((cp) => cp.mag >= mMax / 31.6);
    }
    const tolClaim = az ? Math.max(0.08, (0.6 * az.srd) / az.W) : 0.08;
    for (const cp of comps) {
      // Un groupe harmonique mesure par définition une fréquence déjà
      // « revendiquée » par sa fondamentale : pas d'exclusion ici.
      const abs = cp.freq * (div === 1 ? 1 : k);
      cp.claimed = group.isHarmonic
        ? false
        : claimed.some((f) => Math.abs(abs - f) < tolClaim);
    }
    // Anche accordée à l'octave juste : sa fondamentale tombe DANS le partiel
    // pair de l'anche grave, déjà revendiqué. Une raie libre bien plus faible
    // à côté (bande latérale, bruit de soufflet, boucle d'un sample) n'est pas
    // une anche : mesuré sur un bandonéon La3+La4, le 8' s'y accrochait et
    // affichait −7,4 ¢ au lieu de l'octave juste. On écarte donc les raies
    // libres à plus de 12 dB sous la raie revendiquée ; la voix prend alors
    // la raie commune, marquée `merged` (« confondue avec l'octave »).
    let mClaimed = 0;
    for (const cp of comps) if (cp.claimed) mClaimed = Math.max(mClaimed, cp.mag);
    if (mClaimed > 0) comps = comps.filter((cp) => cp.claimed || cp.mag >= mClaimed / 4);

    // Verrou de continuité (voix unique, mode auto sur un ton battu) : on
    // n'accepte QUE la composante proche (±3 ¢) de la dernière mesure fine —
    // rester sur la même anche. Si aucune (creux de battement où l'anche suivie
    // s'efface, remplacée par des raies parasites), on ne suit pas cette trame
    // → le maintien reprend la dernière valeur. Sans ça, la fondamentale
    // sautait sur l'autre anche à chaque battement.
    if (cont != null && expected.length === 1) {
      const tolC = Math.max(0.03, cont * (Math.pow(2, 3 / 1200) - 1));
      let best = null, bestD = Infinity;
      for (const cp of comps) {
        const dd = Math.abs(cp.freq - cont);
        if (dd < tolC && dd < bestD) { bestD = dd; best = cp; }
      }
      if (best && az) clusterRefine([best], az, calib, div);
      this.fillVoice(expected[0], best, az?.W);
      expected[0].beatMeas = 0;
      return expected;
    }

    const chosen = assignOrdered(expected, comps, tolHz);
    if (az && !group.isSub) clusterRefine(chosen, az, calib, div, expected.map((v) => v.mt));
    for (let i = 0; i < expected.length; i++) {
      this.fillVoice(expected[i], chosen[i], az?.W);
      expected[i].merged = !!chosen[i]?.claimed;
      if (!group.isHarmonic && this.prevF) {
        const key = `${group.key}:${expected[i].def.id}`;
        if (chosen[i]?.cluster) this.prevF.set(key, expected[i].fMeas);
        else if (!chosen[i]) this.prevF.delete(key);
      }
    }

    // Battements mesurés par rapport à la voix de référence du groupe.
    const base = expected.find((v) => v.def.beatSign === 0) ?? expected[0];
    for (const v of expected) {
      v.beatMeas = (v.fMeas != null && base?.fMeas != null && v !== base)
        ? v.fMeas - base.fMeas
        : (v === base ? 0 : null);
    }
    return expected;
  }

  fillVoice(v, comp, w) {
    if (comp) {
      v.fMeas = comp.freq;
      // Amplitude ramenée à l'échelle du signal (pic Hann complexe ≈ A·W/2).
      v.amp = comp.mag / ((w || 2) / 2);
      v.dCents = centsBetween(comp.freq, v.nominal);
      v.dHz = comp.freq - v.nominal;
      v.dTargetCents = centsBetween(comp.freq, v.target);
      v.tracked = true;
    } else {
      v.fMeas = null; v.amp = 0; v.dCents = null; v.dHz = null;
      v.dTargetCents = null; v.tracked = false;
    }
  }
}

// Joint à chaque groupe visible les mesures par partiel de ses anches, pour
// le stroboscope : `partials[k][id]` = fréquence mesurée du partiel k de
// l'anche `id` (Hz), ou absente si pas (encore) résolue. Le partiel sur lequel
// le groupe est lui-même mesuré (kTrack) y figure aussi : c'est la même
// mesure, ramenée au partiel.
// `partialAmps[k][id]` : amplitude de ce partiel (même échelle pour tous) —
// le stroboscope s'en sert pour doser chaque partiel dans le motif.
function withPartials(groups) {
  const byBase = new Map();
  const ampsByBase = new Map();
  for (const g of groups) {
    if (!g.isPartial) continue;
    const m = byBase.get(g.baseKey) ?? {};
    const a = ampsByBase.get(g.baseKey) ?? {};
    m[g.kTrack] = {};
    a[g.kTrack] = {};
    for (const v of g.voices) {
      if (!v.tracked) continue;
      m[g.kTrack][v.def.id] = v.fMeas;
      a[g.kTrack][v.def.id] = v.amp;
    }
    byBase.set(g.baseKey, m);
    ampsByBase.set(g.baseKey, a);
  }
  return groups.filter((g) => !g.hidden).map((g) => {
    if (g.isHarmonic || g.isSub) return g;
    const partials = { ...(byBase.get(g.key) ?? {}) };
    const partialAmps = { ...(ampsByBase.get(g.key) ?? {}) };
    const k = g.kTrack || 1;
    partials[k] = {};
    partialAmps[k] = {};
    for (const v of g.voices) {
      if (!v.tracked) continue;
      partials[k][v.def.id] = v.fMeas * k;
      partialAmps[k][v.def.id] = v.amp;
    }
    return { ...g, partials, partialAmps };
  });
}

// Rééchantillonnage log-fréquence du spectre large bande pour l'affichage.
function logResample(mag, binHz, nOut, fLo = 20, fHi = 10000) {
  const out = new Float32Array(nOut);
  const r = Math.log(fHi / fLo);
  for (let i = 0; i < nOut; i++) {
    const fa = fLo * Math.exp((r * i) / nOut);
    const fb = fLo * Math.exp((r * (i + 1)) / nOut);
    let ia = Math.floor(fa / binHz);
    let ib = Math.max(ia + 1, Math.ceil(fb / binHz));
    ia = Math.min(mag.length - 1, Math.max(0, ia));
    ib = Math.min(mag.length, ib);
    let m = 0;
    for (let j = ia; j < ib; j++) if (mag[j] > m) m = mag[j];
    out[i] = m;
  }
  return out;
}

// Hauteur moyenne d'une anche = pente de la PHASE de son amas de raies.
//
// Le soufflet module la pression, donc la hauteur : chaque partiel d'une
// anche devient un amas — la porteuse et des raies latérales à ±f_soufflet,
// d'autant plus fortes que le partiel est haut (indice de modulation ∝ k).
// Mesuré (test/bench_courbe.mjs, MMM, soufflet ±1 ¢ à 1,5 Hz, suivi sur H5) :
// la raie latérale n'est qu'à −4 dB de la porteuse, et le traqueur sautait
// de l'une à l'autre d'une image à l'autre — +1,2 ¢, 0, +1,2 ¢… : des dents
// de scie sur la courbe, sur un son parfaitement régulier.
//
// On ne choisit donc plus UNE raie : on garde tout l'amas de l'anche (jusqu'à
// mi-chemin de ses voisines, au plus CLUSTER_HZ dans le domaine du partiel),
// on revient dans le temps par FFT inverse, et la pente de la phase déroulée
// donne la fréquence MOYENNE DANS LE TEMPS de l'anche sur la fenêtre. Un
// barycentre de puissance a été essayé et écarté : quand on pousse plus fort,
// l'anche est à la fois plus forte et plus haute, et un barycentre de
// puissance penche vers les instants forts (+0,1 ¢ biais, soufflet calme ;
// +0,56 ¢, soufflet vivant). La phase, elle, ne pèse pas le son.
const CLUSTER_HZ = 5;
// Les bornes d'amas sont prises à mi-chemin des positions ATTENDUES des
// anches voisines (`expectedMt` : leur mesure précédente, sinon leur cible),
// pas des raies choisies : une raie choisie peut être une raie latérale, et
// des bornes qui sautent avec elle refont des dents de scie.
function clusterRefine(chosen, az, calib, div, expectedMt = null) {
  const { W, srd, fc, re, im } = az;
  if (!re || W < 64) return;                      // fenêtre trop courte : on garde la raie
  const binHz = srd / W;
  const offOf = (b) => (b <= W / 2 ? b : b - W) * binHz;
  const toOff = (f) => (f * div) / calib - fc;    // fondamentale → décalage dans la bande
  const centre = (i) => (expectedMt?.[i] != null ? toOff(expectedMt[i]) : chosen[i].off);
  const idx = chosen.map((c, i) => (c ? i : -1)).filter((i) => i >= 0)
    .sort((a, b) => centre(a) - centre(b));
  const fft = FFT.get(W);
  const zr = new Float64Array(W), zi = new Float64Array(W);
  idx.forEach((i, r) => {
    const c = chosen[i];
    if (c.off == null || c.cluster) return;
    const m = centre(i);
    const lo = Math.max(m - CLUSTER_HZ, r > 0 ? (centre(idx[r - 1]) + m) / 2 : -Infinity);
    const hi = Math.min(m + CLUSTER_HZ, r < idx.length - 1 ? (centre(idx[r + 1]) + m) / 2 : Infinity);
    // La raie choisie doit être dans l'amas, avec son lobe principal.
    if (c.off - lo < 2 * binHz || hi - c.off < 2 * binHz || hi - lo < 6 * binHz) return;
    const half = Math.max(c.off - lo, hi - c.off);
    // Masque : l'amas seul (spectre conjugué → FFT directe = FFT inverse conjuguée).
    zr.fill(0); zi.fill(0);
    const b0 = Math.floor(lo / binHz), b1 = Math.ceil(hi / binHz);
    for (let bb = b0; bb <= b1; bb++) {
      const b = ((bb % W) + W) % W;
      const f = offOf(b);
      if (f < lo || f > hi) continue;
      zr[b] = re[b]; zi[b] = -im[b];
    }
    fft.transform(zr, zi);                        // z[n] = conj(résultat)/W — le signe se règle ci-dessous
    // Démodulation par la raie choisie : la phase résiduelle tourne lentement,
    // le déroulement est sans ambiguïté.
    const w0 = (2 * Math.PI * c.off) / srd;
    const n0 = Math.floor(W * 0.15), n1 = Math.ceil(W * 0.85);
    let last = null, acc = 0;
    let sw = 0, sn = 0, sp = 0, snn = 0, snp = 0;
    for (let n = n0; n < n1; n++) {
      const pr = zr[n], pi = -zi[n];              // z = conj(FFT(conj X)) (à 1/W près)
      const cr = Math.cos(w0 * n), ci = -Math.sin(w0 * n);
      const dr = pr * cr - pi * ci, di = pr * ci + pi * cr;
      let ph = Math.atan2(di, dr);
      if (last != null) {
        let d = ph - last;
        d -= 2 * Math.PI * Math.round(d / (2 * Math.PI));
        acc += d;
      }
      last = ph;
      // Pente par moindres carrés NON pondérés : ni par l'amplitude du son
      // (biais vers les instants forts), ni par la fenêtre de Hann (mesuré :
      // ±0,044 ¢ d'écart lisse sous un soufflet qui ondule, contre ±0,019 ¢
      // sans pondération — la pente non pondérée est plus proche de la
      // moyenne uniforme de la hauteur sur la fenêtre).
      const w = 1;
      sw += w; sn += w * n; sp += w * acc; snn += w * n * n; snp += w * n * acc;
    }
    const den = sw * snn - sn * sn;
    if (!(den > 0)) return;
    const slope = (sw * snp - sn * sp) / den;     // rad / échantillon décimé
    const off = c.off + (slope * srd) / (2 * Math.PI);
    if (!Number.isFinite(off) || Math.abs(off - c.off) > half) return;
    c.off = off;
    c.freq = ((fc + off) * calib) / div;
    c.cluster = true;
  });
}

// Appariement voix ↔ composantes préservant l'ordre fréquentiel (alignement
// de séquences par programmation dynamique). Une voix peut rester non
// appariée (coût = tolHz) ; une composante revendiquée par une harmonique
// grave coûte presque autant que l'abandon, elle n'est donc retenue que si
// aucune composante libre ne convient.
function assignOrdered(voices, comps, tolHz) {
  const nV = voices.length;
  const nC = comps.length;
  const skip = tolHz;
  const claimPenalty = tolHz * 0.9;
  const INF = 1e15;
  const cost = (i, j) => {
    const d = Math.abs(comps[j].freq - (voices[i].mt ?? voices[i].target));
    if (d >= tolHz) return INF;
    return d + (comps[j].claimed ? claimPenalty : 0);
  };
  const dp = [];
  const bt = [];
  for (let i = 0; i <= nV; i++) {
    dp.push(new Float64Array(nC + 1));
    bt.push(new Uint8Array(nC + 1));
  }
  for (let i = 1; i <= nV; i++) { dp[i][0] = i * skip; bt[i][0] = 2; }
  for (let i = 1; i <= nV; i++) {
    for (let j = 1; j <= nC; j++) {
      let best = dp[i][j - 1], which = 1;            // composante ignorée
      const s = dp[i - 1][j] + skip;                 // voix non appariée
      if (s < best) { best = s; which = 2; }
      const m = dp[i - 1][j - 1] + cost(i - 1, j - 1); // appariement
      if (m < best) { best = m; which = 3; }
      dp[i][j] = best; bt[i][j] = which;
    }
  }
  const out = new Array(nV).fill(null);
  let i = nV, j = nC;
  while (i > 0) {
    const w = j > 0 ? bt[i][j] : 2;
    if (w === 1) j--;
    else if (w === 2) i--;
    else { out[i - 1] = comps[j - 1]; i--; j--; }
  }
  return out;
}
