// Plan de mesure : quelles anches attendre (voices, chordDegrees), comment
// les grouper par traqueur et sur quel partiel les mesurer (groupVoices,
// unisonHarmonic, strobePartials, partialPresent, targetSpacing), étendue
// du registre (octSpan). Sorti d'engine.js (v28) sans rien changer : les
// méthodes sont posées sur Engine.prototype par engine.js (Object.assign),
// `this` reste le moteur. strobePartials et unisonHarmonic restent
// exportées par engine.js.

import { degreeLabel } from './chord.js';
import { midiToFreq, voiceTargetFreq, MIDI_MIN, MIDI_MAX, REGISTER_PRESETS } from '../music.js';
import { MP_MAX_CENTS } from './anches-mp.js';

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
export function partialPresent(coarse, f0, k) {
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
export function targetSpacing(g) {
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
  let spread = Math.max(...targets.map((t) => Math.abs(t - g.center)));
  // Auto-anches : les anches ne sont pas déclarées, elles peuvent être
  // n'importe où dans les ±35 ¢ admis — toutes doivent tenir dans la bande.
  // Mesuré (session d'Ewen, Ré6) : suivi sur le partiel 3 pour séparer des
  // anches supposées à ±2,5 Hz, l'anche du tiré à +24 ¢ (+49 Hz sur ce
  // partiel) tombait hors de la bande : jamais vue, l'ancienne restait.
  if (cfg.mode === 'reeds') spread = Math.max(spread, g.center * (2 ** (MP_MAX_CENTS / 1200) - 1));
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

// Note imposée (cible de la séquence, verrou à la main) qui ne sonne pas.
// Verrouillé sur une note, le moteur ne la cherche plus : il mesure ce qui
// tombe dans la bande de son partiel de mesure. Si une AUTRE note joue et
// qu'un de ses partiels y tombe, il le lit comme une anche de la note
// imposée. Mesuré (générateur 440 et 442 Hz, cible Do#5 au lieu de La4) : le
// partiel 5 du La4 (2200 et 2210 Hz) est à 13,7 ¢ du partiel 4 du Do#5,
// dans la bande : Do#5 lu à 550,00 et 552,50 Hz, les fréquences jouées
// multipliées par 5/4, données pour fines ; en mésotonique ou en juste sur La,
// où la tierce est pure, à 0,00 ¢, et la case du Do#5 validée sans qu'il ait
// sonné.
// Une anche qui sonne a TOUS ses partiels, et d'abord le plus grave que le
// moteur sait mesurer (le premier au-dessus de 150 Hz, comme kTrack) ; un
// partiel d'une autre note qui tombe au bon endroit est seul. Sans ce
// partiel dans le spectre large bande (même seuil que partialPresent : 30 dB
// sous le plus fort des dix premiers), la note imposée ne sonne pas : ses
// anches sont « — ». À chaque nouvelle note, il faut LOCK_HIT images où ce
// partiel est là avant la première lecture (0,26 s, moins que le temps de
// remplir la fenêtre du traqueur : la lecture juste n'arrive pas plus tard) ;
// puis LOCK_MISS images d'affilée sans lui pour la retirer (un creux de
// battement ne dure pas si longtemps : 0,1 s à 0,2 Hz de battement). La note
// entendue est autre : on ne mesure rien plutôt que d'inventer une valeur.
export const LOCK_MISS = 8;
export const LOCK_HIT = 3;
export const lowestPartial = (center) => Math.max(1, Math.ceil(150 / center));

// Méthodes d'Engine (cf. engine.js, Object.assign).
export const methodesPlan = {
  // Centres des groupes dont la note imposée ne sonne pas (cf. LOCK_MISS),
  // d'après le spectre large bande de l'image (`coarse`, null en silence :
  // rien ne change). Groupes de base seulement ; leurs partiels et leurs
  // harmoniques partagent leur centre.
  silentLock(defs, coarse) {
    const c = this.cfg;
    const out = new Set();
    if (c.lockNote == null || c.mode === 'manual' || this.chordDegrees()) {
      this.lockMiss = new Map();
      this.lockDiag = null;
      return out;
    }
    this.lockMiss ??= new Map();
    // Diagnostic (tick.noteImposee, section recherche de L'anche) : rien ici
    // ne change la décision.
    const diag = { midi: c.lockNote, groupes: [] };
    for (const g of defs) {
      if (g.isHarmonic || g.isSub) continue;
      let e = this.lockMiss.get(g.key);
      if (!e) { e = { miss: 0, hit: 0, absent: true }; this.lockMiss.set(g.key, e); }
      let present = null;
      if (coarse) {
        present = partialPresent(coarse, g.center, lowestPartial(g.center));
        if (present) {
          e.miss = 0;
          if (++e.hit >= LOCK_HIT) e.absent = false;
        } else {
          e.hit = 0;
          if (++e.miss >= LOCK_MISS) e.absent = true;
        }
      }
      if (e.absent) out.add(g.center);
      const k = lowestPartial(g.center);
      diag.groupes.push({ key: g.key, center: g.center, k, f: k * g.center, present, hit: e.hit, miss: e.miss, absent: e.absent });
    }
    this.lockDiag = diag;
    return out;
  },

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
  },

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
          // Trois emplacements aux cibles DISTINCTES — la note, au-dessus,
          // au-dessous (comme 8', 8'+, 8'− d'une musette). Avec deux cibles
          // identiques, la même anche sautait d'un emplacement à l'autre
          // d'une image à l'autre (deux courbes en alternance).
          const sign = [0, 1, -1][u];
          const f = foot[oct] ?? `${oct >= 0 ? '+' : ''}${oct}oct`;
          out.push({
            id: `o${oct}u${u}`,
            label: f + ['', '+', '−'][u],
            oct, beatSign: sign,
          });
        }
      }
      return out;
    }
    return [{ id: 'auto', label: null, oct: 0, beatSign: 0 }];
  },

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
      // Automatique, note grave (mesurée sur un partiel k ≥ 2) : rien ne dit
      // qu'une anche à l'octave ne sonne pas avec elle (une basse fait presque
      // toujours sonner deux ou trois anches à l'octave). Ses partiels pairs
      // seraient alors partagés avec cette anche ; les impairs n'appartiennent
      // qu'à la plus grave. Mesuré (session d'Ewen, Ré#2 en 16'+8') : lue sur
      // son partiel 2, qui EST la fondamentale du 8', la note affichait leur
      // mélange (+10,1 ¢ pour +8,9 et +10,6), sans alerte. Elle se mesure donc
      // sur ses partiels impairs ; les pairs ne servent qu'à l'alerte « deux
      // anches ? » (engine.js, fusion multi-harmonique).
      if (c.mode === 'auto' && g.kTrack > 1) g.avoidEven = true;
      if (g.avoidEven && g.kTrack % 2 === 0) g.kTrack++;
    }
    // Plus généralement (quinte, accord, notes définies) : le partiel de
    // mesure d'une anche ne doit tomber sur AUCUN partiel d'une autre anche
    // jouée — sinon la fenêtre voit leur somme. À la quinte Do2 + Sol2, le
    // partiel 3 de Do2 (196,2 Hz) est le partiel 2 de Sol2 (196,0 Hz) : on
    // mesure Do2 sur son partiel 4. (Les unissons ont leur propre choix, plus
    // bas : unisonHarmonic.)
    // Accords (main gauche) : une note de basse fait sonner plusieurs anches
    // à l'octave (La♯2 ET La♯3…). Son partiel pair tombe sur la fondamentale
    // de l'anche à l'octave : la fenêtre voit leur somme, qui bat. Mesuré
    // (session d'Ewen, quintes de la main gauche) : le « 1 » de La♯2, suivi
    // sur son partiel 2, basculait de +10 à +17 ¢ au rythme de ce battement.
    // Comme pour un registre 16'+8', on le mesure sur un partiel IMPAIR.
    const chordOdd = c.mode === 'chord';
    if (groups.length > 1) {
      for (const g of groups) {
        if (g.voices.length > 1 || g.avoidEven) continue;
        // Partiels de l'autre anche jusqu'à la fréquence étudiée (pas
        // seulement 16) : à la douzième (Fa4 sur La♯2), le partiel 6 de Fa4
        // tombe sur le 18 de La♯2.
        const clash = (k) => groups.some((h) => h !== g
          && Array.from({ length: Math.ceil((k * g.center) / h.center) + 1 }, (_, j) => j + 1)
            .some((j) => Math.abs(k * g.center - j * h.center) < SEP_HZ));
        const bad = (k) => clash(k) || (chordOdd && k > 1 && k % 2 === 0);
        let k = g.kTrack;
        while (k < K_MAX && bad(k)) k++;
        if (!bad(k)) g.kTrack = k;
        else if (chordOdd && g.kTrack % 2 === 0) g.kTrack = Math.max(1, g.kTrack - 1);
        // Aucun partiel libre en fréquences nominales : l'anche est un
        // multiple exact d'une autre (le 8' d'un 16'+8' : son partiel k tombe
        // sur le partiel 2k du 16'). Le choix se fera sur les fréquences
        // MESURÉES, partiel par partiel (cf. appariement.js, octaveFuse).
        else if (!chordOdd) g.octaveClash = true;
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
          octaveClash: !!g.octaveClash,
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
  },

  // Étendue du registre en octaves (16'+8' : 1 ; 16'+8'+4' : 2 ; unisson : 0).
  octSpan() {
    const octs = this.voices().map((v) => v.oct ?? 0);
    return octs.length ? Math.max(...octs) - Math.min(...octs) : 0;
  },
};
