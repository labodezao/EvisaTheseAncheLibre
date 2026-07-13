// Moteur d'analyse : reçoit l'audio par blocs, identifie la note jouée
// (analyse grossière) puis mesure chaque anche avec un traqueur zoom par
// groupe d'octave. Fonctionne dans un Worker (ou dans Node pour les tests).

import { CoarseAnalyzer } from './coarse.js';
import { ZoomTracker } from './zoom.js';
import { NsdfTracker } from './nsdf.js';
import { matrixPencil } from './subspace.js';
import {
  midiToFreq, nearestMidi, centsBetween, voiceTargetFreq,
  MIDI_MIN, MIDI_MAX, REGISTER_PRESETS,
} from '../music.js';

const HOP = 4096;             // période d'analyse (~85 ms à 48 kHz)
const MAXWIN = { fast: 128, normal: 256, precise: 512 };

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
    // Suivi continu : historique de f0 pour détecter une hauteur en
    // mouvement (chant, glissando), et verrou de préférence au suivi rapide.
    this.f0Hist = [];
    this.motionLatch = false;
  }

  get gate() { return Math.pow(10, (this.cfg.gateDb ?? -70) / 20); }

  configure(patch) {
    Object.assign(this.cfg, patch);
    if (patch.beatCurve) this.cfg.beatCurve = { ...patch.beatCurve };
    // Tout changement de cible invalide les traqueurs.
    this.retune(true);
  }

  voices() {
    const c = this.cfg;
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
    return [{ id: 'auto', label: null, oct: 0, beatSign: 0 }];
  }

  // (Re)centre les traqueurs sur la note jouée courante.
  retune(force = false) {
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
      const base = v.fixedMidi ?? (playedMidi + 12 * v.oct);
      if (base < MIDI_MIN - 1 || base > MIDI_MAX + 1) continue;
      const t = v.fixedMidi != null
        ? { midi: v.fixedMidi, nominal: midiToFreq(v.fixedMidi, c), beat: 0,
            target: midiToFreq(v.fixedMidi, c) }
        : voiceTargetFreq(playedMidi, v, c);
      const key = v.fixedMidi != null ? `m${v.fixedMidi}` : `o${v.oct}`;
      let g = map.get(key);
      if (!g) {
        const kTrack = Math.max(1, Math.ceil(150 / t.nominal));
        g = { key, center: t.nominal, kTrack, voices: [] };
        map.set(key, g);
      }
      g.voices.push({ def: v, ...t });
    }
    const groups = [...map.values()];
    for (const g of groups) g.fc = g.center * g.kTrack;

    // Suivi individuel des harmoniques : un traqueur zoom dédié par partiel
    // (2..n). Chaque partiel est mesuré à sa fréquence réelle — l'anche
    // n'étant pas parfaitement harmonique, l'écart de chaque partiel au
    // multiple exact devient une grandeur mesurée, pas une hypothèse.
    const nH = c.mode !== 'register' ? (c.trackHarmonics | 0) : 0;
    if (nH > 1) {
      for (const g of groups.slice()) {
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

    let sum = 0;
    for (let i = 0; i < chunk.length; i++) sum += chunk[i] * chunk[i];
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
    const quiet = level < this.gate;
    const calib = 1 + (c.calibrationPpm || 0) * 1e-6;

    // En silence, la détection de note n'a rien à détecter : la FFT large
    // bande (le poste de calcul dominant, ~5 ms) est sautée — l'accordeur
    // au repos ne consomme presque rien. L'affichage du spectre garde la
    // dernière image côté interface.
    const priorF0 = this.playedMidi != null ? midiToFreq(this.playedMidi, c) : null;
    const coarse = (!quiet && this.coarse.ready()) ? this.coarse.analyze(priorF0) : null;
    let f0 = coarse?.f0 ? coarse.f0.freq * calib : null;

    // Détection temporelle McLeod (NSDF) : hauteur monophonique robuste aux
    // erreurs d'octave, à faible latence. Sert d'ancre d'octave à la
    // détection spectrale et de source au suivi continu. En mode registre
    // (plusieurs anches à l'unisson), la NSDF n'est pas fiable : on l'ignore.
    const poly = c.mode === 'register';
    const nsdfEst = (!quiet && !poly && this.coarse.ready())
      ? this.nsdf.estimateFromRing(this.coarse.ring, this.coarse.wpos, this.coarse.win)
      : null;
    const nf0 = nsdfEst ? nsdfEst.f0 * calib : null;
    const clarity = nsdfEst ? nsdfEst.clarity : 0;
    // Ancre d'octave : si la NSDF est franche (clarté ≥ 0,9) et que la
    // fondamentale spectrale tombe sur un multiple/sous-multiple entier de la
    // hauteur NSDF (erreur d'octave ou de douzième), on adopte la NSDF.
    if (f0 && nf0 && clarity >= 0.9) {
      const ratio = f0 / nf0;
      for (const R of [0.5, 2, 1 / 3, 3]) {
        if (Math.abs(ratio - R) / R < 0.03) { f0 = nf0; break; }
      }
    }

    // Note verrouillée par l'utilisateur : la détection est court-circuitée.
    if (c.lockNote != null && c.mode !== 'manual') {
      if (this.playedMidi !== c.lockNote) {
        this.playedMidi = c.lockNote;
        this.retune();
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
        if (midi === this.playedMidi) {
          this.candCount = 0;
        } else if (midi === this.candMidi) {
          if (++this.candCount >= need && !held) {
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

    // Mesures fines par groupe, du grave vers l'aigu : les harmoniques des
    // voix déjà mesurées sont « revendiquées » pour que, par exemple, la 2e
    // harmonique du 16' ne soit pas prise pour la fondamentale du 8'.
    const maxWin = MAXWIN[c.response] ?? 256;
    const groups = [];
    const played = this.playedMidi;
    const claimed = [];
    // Fondamentale mesurée par centre d'octave : un groupe harmonique cherche
    // son partiel autour de k·f0_mesurée plutôt que k·f0_nominale. Sans cet
    // ancrage, quand la fondamentale est décalée (ex. +9 ¢), le vrai partiel
    // (lui aussi à +9 ¢) et une raie parasite proche du nominal (0 ¢) sont
    // quasi équidistants de la cible nominale : l'appariement bascule de
    // l'un à l'autre → pics discontinus sur la courbe des harmoniques.
    const baseFByCenter = new Map();
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
      const az = t.analyze(maxWin, Math.max(3, g.voices.length + 1));
      let anchor = null;
      if (g.isHarmonic && !g.isSub) {
        const bf = baseFByCenter.get(g.center);
        if (bf) anchor = bf * g.kTrack;
      }
      const voices = this.matchVoices(g, az, calib, claimed, anchor);
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
        srd: t.srd,
        W: az?.W ?? 0,
        fill: az?.fill ?? 0,
        spectrum: az ? az.mags : null,
        voices,
      });
    }

    // Mode automatique : repli « suivi continu » quand le traqueur fin n'a
    // pas (encore) accroché — voix chantée, glissando, vibrato large, ou les
    // premières centaines de ms après un changement de note. La fondamentale
    // affinée de l'analyse harmonique (mise à jour toutes les ~85 ms,
    // précision ~0,1–1 cent) alimente alors la mesure ; le zoom hétérodyne
    // haute précision reprend la main dès que le ton est stable. Sans ce
    // repli, la courbe est pleine de trous dès que la hauteur bouge.
    if (c.mode === 'auto' && !quiet && f0 && played != null) {
      const g = groups.find((gr) => !gr.isHarmonic && !gr.isSub);
      const v = g?.voices[0];
      // Détection de hauteur en mouvement : dérive de f0 sur ~0,5 s. Le
      // désaccord zoom/f0 seul ne suffit pas comme critère — une anche
      // inharmonique fait diverger les deux légitimement sur ton stable.
      const tNow = this.samplesTotal / this.sr;
      this.f0Hist.push({ t: tNow, f: f0 });
      while (this.f0Hist.length && this.f0Hist[0].t < tNow - 1.2) this.f0Hist.shift();
      // Référence = l'échantillon le plus récent vieux d'au moins 0,5 s
      // (recherche depuis la fin — le premier match depuis le début serait
      // le plus ancien de la fenêtre, jusqu'à 1,2 s, et biaiserait la dérive).
      let ref = null;
      for (let i = this.f0Hist.length - 1; i >= 0; i--) {
        if (this.f0Hist[i].t <= tNow - 0.5) { ref = this.f0Hist[i]; break; }
      }
      const drift = ref ? Math.abs(centsBetween(f0, ref.f)) : 0;
      if (drift > 5) {
        // La hauteur bouge : la longue fenêtre du zoom moyenne le mouvement
        // et sa valeur traîne — le suivi rapide prend la main.
        this.motionLatch = true;
      } else if (this.motionLatch && v?.tracked
          && Math.abs(centsBetween(v.fMeas, f0)) < 3) {
        // Le zoom a re-convergé sur la hauteur stabilisée : il reprend la main.
        this.motionLatch = false;
      }
      // Source du suivi : la NSDF (fenêtre 85 ms, sans erreur d'octave) suit
      // une hauteur qui bouge de plus près que la FFT grossière (341 ms) ;
      // repli sur la fondamentale spectrale si la NSDF n'est pas franche.
      const followF0 = (nf0 && clarity >= 0.7) ? nf0 : f0;
      if (v && (!v.tracked || this.motionLatch) && Math.abs(centsBetween(followF0, v.nominal)) < 120) {
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
        for (const g of groups) {
          if (!g.isHarmonic || g.isSub) continue;
          const v = g.voices[0];
          if (!v?.tracked) continue;
          const fEq = v.fMeas / g.kTrack; // fMeas en domaine du partiel
          if (Math.abs(centsBetween(fEq, bv.fMeas)) > 1.5) continue;
          const w = (v.amp * g.kTrack) ** 2;
          num += w * fEq;
          den += w;
          nFused++;
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
        const M = Math.max(1, Math.min(4, this.motionLatch ? 1 : nExp + (nExp < 3 ? 1 : 0)));
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

    return {
      type: 'tick',
      time: this.samplesTotal / this.sr,
      level,
      quiet,
      f0,
      f0Cents,
      clarity,
      playedMidi: played,
      transpose: c.transpose,
      lockNote: c.lockNote ?? null,
      attack: this.lastAttack,
      // Les groupes cachés (traqueurs de fusion) ne sont pas transmis :
      // ils servent au calcul, pas à l'affichage.
      groups: groups.filter((g) => !g.hidden),
      coarseSpectrum: coarse ? logResample(coarse.mag, coarse.binHz, 1024) : null,
    };
  }

  // Associe les composantes mesurées aux voix attendues du groupe.
  // `claimed` : fréquences absolues (Hz) déjà expliquées comme harmoniques
  // de voix plus graves — elles ne sont utilisées qu'en dernier recours.
  matchVoices(group, az, calib, claimed = [], anchor = null) {
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
    if (useAnchor) expected[0].mt = anchor;
    // Tolérance : ±85 cents en général ; ±40 cents pour un partiel ancré ;
    // ±20 cents pour les bandes sous-harmoniques (un doublement de période
    // est verrouillé sur la fondamentale — un pic éloigné est du bruit).
    const tolHz = group.isSub
      ? Math.max(1.5, group.fc * 0.012)
      : useAnchor
        ? Math.max(2.5, anchor * 0.023)
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

    const chosen = assignOrdered(expected, comps, tolHz);
    for (let i = 0; i < expected.length; i++) this.fillVoice(expected[i], chosen[i], az?.W);

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
