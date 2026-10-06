// Moteur d'analyse : reçoit l'audio par blocs, identifie la note jouée
// (analyse grossière) puis mesure chaque anche avec un traqueur zoom par
// groupe d'octave. Fonctionne dans un Worker (ou dans Node pour les tests).

import { CoarseAnalyzer } from './coarse.js';
import { ZoomTracker } from './zoom.js';
import { NsdfTracker } from './nsdf.js';
import { matrixPencil } from './subspace.js';
import { chordFromPeaks, chordAuto } from './chord.js';
import {
  midiToFreq, nearestMidi, centsBetween,
  MIDI_MIN, MIDI_MAX,
} from '../music.js';
// Modules du moteur (méthodes posées sur Engine.prototype en bas de fichier).
import { withPartials, logResample, methodesBattement } from './battement.js';
import { methodesAppariement, OCTAVE_SEP_BINS } from './appariement.js';
import { MP_ALERT_S, methodesAnchesMp } from './anches-mp.js';
import { methodesStabilite } from './stabilite.js';
import { partialPresent, targetSpacing, methodesPlan } from './plan.js';
import { methodesConfondu } from './confondu.js';
// Exportées par engine.js depuis la v28 (API gelée), rangées dans plan.js.
export { strobePartials, unisonHarmonic } from './plan.js';

// Version du moteur : doit être celle de la page et de app.js (cf. le
// contrôle de cohérence dans app.js et le test dans dsp.test.mjs).
export const ENGINE_VERSION = '41';

const HOP = 4096;             // période d'analyse (~85 ms à 48 kHz)
const MAXWIN = { fast: 128, normal: 256, precise: 512 };
// Réglages sans effet sur les cibles : les changer ne remet pas la mesure à zéro.
const NO_RETUNE = new Set(['gateDb', 'tolCents', 'autoFreeze', 'readout', 'devMode', 'bellows', '_v']);
// Reprise après un silence (inversion du soufflet) : on ne garde que ce qui
// suit la reprise (8 échantillons décimés ≈ une image).
const RESUME_KEEP = 8;
// Deux anches déguisées en une (mode Automatique) : partiels en désaccord de
// plus de DISAGREE_CENTS pendant plus de DISAGREE_HOLD_S.
const DISAGREE_CENTS = 1.5;
const DISAGREE_HOLD_S = 1.5;

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
    this.reedSeen = new Map();  // auto-anches : persistance des anches d'unisson
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

  // (Re)centre les traqueurs sur la note jouée courante.
  retune(force = false) {
    if (force) this.plan = null;
    // Nouvelle note (ou nouveaux réglages) : la continuité par anche repart
    // de zéro — les cibles reprennent la main pour l'appariement.
    this.prevF = new Map();
    this.steps = new Map();      // détection de saut par groupe (cf. detectStep)
    this.stab = new Map();       // sortie stabilisée par anche (cf. stabilize)
    this.reedSeen = new Map();   // auto-anches : persistance des anches d'unisson
    this.ownT = new Map();       // dernière mesure « à soi » (non confondue) par anche
    this.confT = new Map();      // dernière image « confondue avec l'octave » par anche (confondu.js)
    // La dernière mesure fine de l'ancienne note ne doit pas être « tenue »
    // sur la nouvelle (mesuré : Do3 → Do4, une image à −1201 ¢).
    this.lastFine = null;
    this.disagreeSince = null;
    this.unisonSince = null;
    this.mpHist = [];
    this.lockMiss = new Map();   // note imposée qui ne sonne pas (silentLock) : on recompte
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

    this.watchReversal(rms, tNow, chunk.length);

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
        // Registre à l'octave (16'+8'…) : quand l'une des anches se tait, la
        // détection voit l'autre seule et croit à une note une octave plus
        // haut ou plus bas — elle ré-attribuait l'anche restante à l'autre
        // voix (mesuré, session d'Ewen : Fa♯4 ↔ Fa♯5 en lâchant une anche).
        // Tant qu'une anche du registre sonne encore à sa place, on garde la
        // note : l'anche partie apparaît absente (« — »), c'est ce qu'on veut
        // voir.
        // Mais ce verrou ne vaut que dans un sens. Lâcher une anche ne fait
        // jamais apparaître une fondamentale PLUS GRAVE : si la détection
        // propose une note plus basse et que les partiels IMPAIRS de cette
        // fondamentale (1, 3, 5) ont une énergie à eux, c'est qu'une anche
        // plus grave sonne vraiment. Aucune anche du plan en cours ne peut les
        // produire : toutes sont à des multiples de 2 f0. C'est le cas d'un
        // 16'+8' dont le 8' (petite anche, croissance plus rapide) parle le
        // premier : la note se cale une octave trop haut, le 16' se pose sur
        // le 8' et le verrou refusait ensuite la note juste toute la note
        // (mesuré, session d'Ewen, Ré#2 et Ré2 en 16'+8'). Seuil : celui de
        // partialPresent (30 dB sous le plus fort des dix premiers
        // partiels), le même qui déclare une voix du registre absente.
        const lowerOwn = midi < (this.playedMidi ?? -1) && coarse
          && [1, 3, 5].some((k) => partialPresent(coarse, f0, k));
        const regOct = (c.mode === 'register' || c.mode === 'reeds')
          && this.playedMidi != null && midi !== this.playedMidi
          && (midi - this.playedMidi) % 12 === 0
          && Math.abs(midi - this.playedMidi) <= 12 * this.octSpan()
          && tNow - (this.lastVoiceT ?? -1e9) < 0.3
          && !lowerOwn;
        if (midi === this.playedMidi || regOct) {
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
        this.reversal = false;
      } else if (this.silentSince != null || this.reversal) {
        this.silentSince = null;
        this.reversal = false;
        for (const tr of this.trackers.values()) tr.restart(RESUME_KEEP);
        this.stab = new Map();   // pas de maintien À TRAVERS le silence : l'autre sens n'est pas celui-ci
        this.confT = new Map();
        this.prevF = new Map();
        this.steps = new Map();
        this.lastFine = null;
        this.disagreeSince = null;
        this.mpHist = [];
        this.reedSeen = new Map();
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
    // Note imposée qui ne sonne pas : ses anches sont « — » (plan.js, silentLock).
    const silent = this.silentLock(defs, coarse);
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
      // Partiels du 8' d'un 16'+8' : seules les raies des AUTRES anches
      // comptent comme revendiquées (cf. matchVoices, octaveClash).
      const claimFor = g.isPartial && g.octaveClash ? claimed.filter((_, i) => claimedBy[i] !== g.center) : claimed;
      const voices = this.matchVoices(g, az, calib, claimFor, anchor, cont);
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
      // Plusieurs anches vues par Matrix Pencil (image précédente) : les
      // variations de la fenêtre courte sont leur battement, pas un saut de
      // hauteur. Mesuré : sur une musette Fa3 (2 Hz d'écart) en Automatique,
      // la mesure redémarrait à chaque battement, toutes les 0,5 s.
      const beating = this.mp && !g.isHarmonic && !g.isSub && (g.voices[0].def.oct ?? 0) === 0;
      if (!quiet && !beating) {
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
      // Registre à plusieurs octaves (16'+8'…) : une anche qu'on a lâchée n'a
      // plus de raie à elle ; son traqueur s'accrochait au bruit et affichait
      // une valeur fausse (mesuré : 16' à −28 ¢ alors que seul le 8' sonnait).
      // Sans preuve de présence dans le spectre, la voix est « — ».
      if (c.mode === 'register' && !g.isHarmonic && !g.isSub && this.octSpan() > 0
          && !partialPresent(this.lastCoarse, g.center, g.kTrack)) {
        for (const v of voices) { this.fillVoice(v, null, az?.W); v.absent = true; }
      }
      // Note imposée (cible, verrou) dont le partiel le plus grave manque :
      // une autre note joue, un de ses partiels tombe dans la bande. Rien.
      if (silent.has(g.center)) {
        for (const v of voices) { this.fillVoice(v, null, az?.W); v.absent = true; }
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
        octaveClash: !!g.octaveClash,
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
      if (v && !v.tracked && holdOk && Math.abs(centsBetween(this.lastFine.f, v.nominal)) < 120) {
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
      // À plus d'un demi-ton de la note, l'estimation rapide lit déjà la note
      // SUIVANTE (mesuré, session d'Ewen : Sol4 → Fa♯4, −68 puis −101 ¢
      // pendant 3 images avant que la note affichée ne change) : pas de repli.
      } else if (v && !v.tracked && Math.abs(centsBetween(followF0, v.nominal)) < 50
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
        // Diagnostic (section recherche de L'anche, « partiels de mesure ») :
        // chaque partiel, son poids, son rôle. Rien ici ne change la mesure.
        const parts = [{ k: base.kTrack || 1, f: bv.fMeas, poids: wBase, role: 'fondu' }];
        let ampRef = bv.amp;
        for (const g of groups) if (g.isHarmonic && !g.isSub && g.voices[0]?.tracked) ampRef = Math.max(ampRef, g.voices[0].amp);
        let worst = null;                 // partiel le plus en désaccord avec la voix de base
        // Note grave (cf. plan.js, avoidEven) : ses partiels pairs peuvent être
        // ceux d'une anche à l'octave. S'il y en a un qui s'écarte des impairs
        // au-delà de la porte pleine (0,5 ¢), une anche à l'octave sonne : les
        // pairs servent alors à l'alerte, pas à la mesure. Sinon (anche seule,
        // trémolo), ils comptent comme les autres.
        let octaveVue = false;
        if (base.avoidEven) {
          for (const g of groups) {
            if (!g.isHarmonic || g.isSub || g.kTrack % 2 !== 0) continue;
            const v = g.voices[0];
            if (v?.tracked && !v.step && v.amp >= ampRef / 31.6
                && Math.abs(centsBetween(v.fMeas / g.kTrack, bv.fMeas)) > 0.5) octaveVue = true;
          }
        }
        for (const g of groups) {
          if (!g.isHarmonic || g.isSub) continue;
          const v = g.voices[0];
          if (!v?.tracked) continue;
          const fEq = v.fMeas / g.kTrack; // fMeas en domaine du partiel
          if (!v.step && v.amp >= ampRef / 31.6) {
            const sd = centsBetween(fEq, bv.fMeas);
            if (!worst || Math.abs(sd) > Math.abs(worst.cents)) worst = { k: g.kTrack, cents: sd };
          }
          if (octaveVue && g.kTrack % 2 === 0) { parts.push({ k: g.kTrack, f: fEq, poids: 0, role: 'alerte' }); continue; }
          // Porte PROGRESSIVE : poids plein jusqu'à 0,5 ¢ d'écart, nul à 1,5 ¢.
          // Une porte franche faisait entrer et sortir un partiel d'une image à
          // l'autre quand il frôlait le seuil : une marche sur la courbe à
          // chaque passage.
          const dev = Math.abs(centsBetween(fEq, bv.fMeas));
          if (dev >= 1.5) { parts.push({ k: g.kTrack, f: fEq, poids: 0, role: 'ecarte' }); continue; }
          const taper = dev <= 0.5 ? 1 : (1.5 - dev);
          const w = taper * (v.amp * g.kTrack) ** 2;
          num += w * fEq;
          den += w;
          nFused++;
          parts.push({ k: g.kTrack, f: fEq, poids: w, role: 'fondu' });
        }
        bv.partielsMesure = parts;
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

    // Registre à plusieurs octaves : une voix à plus de 30 dB sous la plus
    // forte de la note ne sonne pas — sa « raie » est le reste d'une autre
    // (mesuré, session d'Ewen : Fa4 seul joué, le 8' affichait +64 ¢ sur une
    // raie 43 dB sous le 16'). Elle est « — », sans maintien.
    if (c.mode === 'register' && this.octSpan() > 0) {
      let aMax = 0;
      for (const g of groups) if (!g.isHarmonic && !g.isSub) for (const v of g.voices) if (v.tracked) aMax = Math.max(aMax, v.amp);
      for (const g of groups) {
        if (g.isHarmonic || g.isSub) continue;
        for (const v of g.voices) {
          if (v.tracked && v.amp < aMax * Math.pow(10, -30 / 20)) { this.fillVoice(v, null); v.absent = true; }
        }
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
    // Le 8' d'un 16'+8' : lu sur ceux de ses partiels où sa raie est séparée
    // de celle du 16' (après le plancher : un partiel noyé n'y entre pas).
    this.octaveFuse(groups, claimed, claimedBy);

    // Auto-anches : ne compter que les vraies anches, pas le bruit ni les
    // harmoniques. Deux filtres :
    //   1) plancher global −25 dB (une octave vide verrouille sur du bruit) ;
    //   2) rejet harmonique — le partiel k d'une anche grave tombe pile sur la
    //      fondamentale d'une octave supérieure (le 4' est à 2× le 8') : une
    //      anche dont la fréquence coïncide (< 8 cents) avec k× une anche plus
    //      grave ET plus forte est cette harmonique, pas une anche distincte.
    //      Une vraie anche d'octave désaccordée (battement) y échappe.
    if (c.mode === 'reeds') {
      // Une anche de plus à l'unisson doit être franche : à 14 dB au plus de
      // la plus forte de son octave, et à ±35 ¢ au plus de la note. Mesuré
      // sur un trémolo La♯3 d'Ewen (232,4 + 234,4 Hz) : les emplacements
      // libres se remplissaient de raies 10 fois plus faibles (bandes
      // latérales du soufflet, restes de partiels voisins, 239,9 Hz à +50 ¢),
      // affichées comme des anches à +42 ¢.
      for (const g of groups) {
        if (g.isHarmonic || g.isSub || g.voices.length < 2) continue;
        let aMax = 0;
        for (const v of g.voices) if (v.tracked && !v.held) aMax = Math.max(aMax, v.amp);
        const tNow = this.samplesTotal / this.sr;
        for (const v of g.voices) {
          const key = `${g.key}:${v.def.id}`;
          if (!v.tracked || v.amp >= aMax) { if (!v.tracked) this.reedSeen.delete(key); continue; }
          if (v.amp < aMax * Math.pow(10, -12 / 20) || Math.abs(centsBetween(v.fMeas, v.nominal)) > 35) {
            this.fillVoice(v, null);
            this.reedSeen.delete(key);
            continue;
          }
          // Persistance : une vraie anche reste là, à la même hauteur (±2 ¢)
          // pendant 0,8 s ; une raie parasite va et vient.
          const seen = this.reedSeen.get(key);
          if (!seen || Math.abs(centsBetween(v.fMeas, seen.f)) > 2) {
            this.reedSeen.set(key, { f: v.fMeas, since: tNow });
            this.fillVoice(v, null);
          } else {
            seen.f = v.fMeas;
            if (tNow - seen.since < 0.8) this.fillVoice(v, null);
          }
        }
      }
      // Le plancher compare des ANCHES, pas des partiels : une anche a la
      // force de son partiel le plus fort (celui de mesure ou ceux du
      // stroboscope). Avant, une anche seule mesurée sur un partiel faible
      // (Fa#3 d'Ewen : partiel 5, 27 dB sous ses partiels 3 et 4) était
      // effacée parce que plus faible que… ses propres partiels.
      const force = (g, v) => {
        let a = v.amp;
        for (const p of groups) {
          if (!p.isPartial || p.baseKey !== g.key) continue;
          const pv = p.voices.find((x) => x.def.id === v.def.id);
          if (pv?.tracked && pv.amp > a) a = pv.amp;
        }
        return a;
      };
      const reedFloor = baseAmp * Math.pow(10, -25 / 20);
      for (const g of groups) {
        for (const v of g.voices) {
          if (v.tracked && (g.isHarmonic ? v.amp : force(g, v)) < reedFloor) this.fillVoice(v, null);
        }
      }
      // Rejet harmonique borné par la RÉSOLUTION de la mesure, pas par une
      // constante : dans la bande où l'anche est mesurée (partiel kv), sa
      // raie et le partiel k kv de l'anche grave sont à kv |f − k f_lo| Hz.
      // À moins de OCTAVE_SEP_BINS cases de la fenêtre (et de la tolérance
      // des partiels élevés, au-delà de 1,5 kHz), la fenêtre ne les
      // distingue pas : c'est l'harmonique. Au-delà, c'est une autre raie,
      // donc une autre anche. Avant, 8 ¢ : le 4' d'une basse, à 1,6 à 7 ¢
      // de l'octave, n'était jamais affiché (session d'Ewen, Ré#2, La#2),
      // alors que deux raies à 0,2 Hz se séparent en 2,7 s.
      const kept = [];
      for (const g of groups) for (const v of g.voices) if (v.tracked) kept.push({ v, g });
      kept.sort((a, b) => a.v.fMeas - b.v.fMeas);
      for (let i = 0; i < kept.length; i++) {
        const { v, g } = kept[i];
        const kv = g.isHarmonic ? 1 : (g.kTrack || 1);
        const fBand = v.fMeas * kv;
        const res = Math.max((OCTAVE_SEP_BINS * g.srd) / Math.max(1, g.W), fBand >= 1500 ? fBand * 0.0015 : 0);
        for (let j = 0; j < i; j++) {
          const lo = kept[j].v;
          if (!lo.tracked || lo.amp <= v.amp) continue;
          const k = Math.round(v.fMeas / lo.fMeas);
          if (k >= 2 && kv * Math.abs(v.fMeas - k * lo.fMeas) < res) {
            this.fillVoice(v, null); // c'est l'harmonique k de `lo`
            break;
          }
        }
      }
    }

    // Anches d'un même ton par Matrix Pencil (Automatique et Auto-anches).
    // Automatique : on prévient tout de suite qu'il y a deux anches, avec leur
    // hauteur. Auto-anches : tant que la FFT n'a pas encore séparé les anches
    // (elle montre une seule raie, souvent le MÉLANGE des deux : +13 ¢ pour
    // une musette +2 / +22 ¢), ce sont les valeurs de Matrix Pencil qui
    // s'affichent ; la FFT reprend la main dès qu'elle les voit toutes.
    this.mp = null;
    if ((c.mode === 'auto' || c.mode === 'reeds') && !quiet && played != null) {
      const gb = groups.find((g) => !g.isHarmonic && !g.isSub && (g.voices[0].def.oct ?? 0) === 0);
      this.mp = gb ? this.mpReeds(gb, calib) : null;
      if (this.mp && c.mode === 'reeds') this.fillFromMp(gb, this.mp);
      // Automatique : la courbe suit UNE anche. Si la FFT montre une valeur
      // qui n'est la hauteur d'aucune (le mélange des deux, +5 ¢ pour une
      // musette −3,8 / +17,2 ¢), on affiche l'anche de Matrix Pencil la plus
      // proche de la mesure précédente (au départ, la plus forte).
      if (this.mp && c.mode === 'auto') {
        const v = gb.voices[0];
        const dist = (cp, f) => Math.abs(centsBetween(cp.f, f));
        if (!v.tracked || Math.min(...this.mp.map((cp) => dist(cp, v.fMeas))) > 1.5) {
          const ref = this.lastFine?.f;
          const cp = ref != null
            ? this.mp.reduce((b, q) => (dist(q, ref) < dist(b, ref) ? q : b))
            : this.mp.reduce((b, q) => (q.amp > b.amp ? q : b));
          this.fillVoice(v, { freq: cp.f, mag: cp.amp }, 2);
          v.mp = true;
          this.lastFine = { t: this.samplesTotal / this.sr, f: cp.f };
        }
      }
    } else {
      this.mpHist = [];
    }
    if (c.mode === 'reeds') {
      for (const g of groups) {
        if (g.isHarmonic || g.isSub) continue;
        this.rankReeds(g);
        this.fuseSingleReed(g, groups, claimed, claimedBy);
      }
    }
    if (!this.mp) this.mpSince = null;
    else if (this.mpSince == null) this.mpSince = this.samplesTotal / this.sr;

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
    // Anche confondue avec l'octave : son estimation, avec sa marge (confondu.js).
    if (!quiet) this.estimerConfondues(groups);
    // Dernier instant où une anche du registre était mesurée à sa place
    // (sert à ne pas ré-attribuer les anches quand l'une d'elles se tait).
    if (!quiet && groups.some((g) => !g.isHarmonic && !g.isSub && g.voices.some((v) => v.tracked && !v.held))) {
      this.lastVoiceT = this.samplesTotal / this.sr;
    }
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
      // Avec Matrix Pencil (cf. mpReeds), tout de suite et avec la hauteur
      // de chaque anche : { cents, reeds: [¢…], beatHz }.
      unison: c.mode === 'auto' && !quiet
        ? (this.mp && this.samplesTotal / this.sr - this.mpSince >= MP_ALERT_S ? this.mpUnison(groups)
          : this.unisonSince != null && this.samplesTotal / this.sr - this.unisonSince >= DISAGREE_HOLD_S
            ? this.unison : null)
        : null,
      partialsDisagree: c.mode === 'auto' && !quiet && this.disagreeSince != null
        && this.samplesTotal / this.sr - this.disagreeSince >= DISAGREE_HOLD_S ? this.disagree : null,
      clarity,
      playedMidi: played,
      transpose: c.transpose,
      lockNote: c.lockNote ?? null,
      // Note imposée (cible, verrou) : son partiel le plus grave est-il dans le
      // spectre large bande (plan.js, silentLock) ? Diagnostic de la section
      // recherche de L'anche : { midi, groupes: [{ key, center, k, f,
      // present, hit, miss, absent }] } ou null sans note imposée.
      noteImposee: this.lockDiag ?? null,
      attack: this.lastAttack,
      // Les groupes cachés (traqueurs de fusion) ne sont pas transmis :
      // ils servent au calcul, pas à l'affichage.
      groups: withPartials(groups),
      coarseSpectrum: coarse ? logResample(coarse.mag, coarse.binHz, 1024) : null,
    };
  }
}

// Méthodes rangées dans les modules voisins, corps inchangés : `this` reste le moteur.
Object.assign(Engine.prototype, methodesBattement, methodesAppariement, methodesAnchesMp, methodesStabilite, methodesPlan, methodesConfondu);
