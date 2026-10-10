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
export function partialPresent(coarse, f0, k, rapport = 31.6) {
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
  return ref > 0 && peakAround(f0 * k) >= ref / rapport;
}

// Le partiel est-il un PIC du spectre large bande, à ±45 ¢ de `f` (le
// maximum de la fenêtre à l'intérieur, pas sur un bord) ? Le pied d'une raie
// voisine monte vers le bord de la fenêtre : ce n'est pas un partiel. Audit
// d'usage pro n° 1 (10/10/2026) : partialPresent compare le partiel aux dix
// premiers de la MÊME note ; quand elle ne sonne pas, ils ne sont que des
// pieds de raies, et le pied du Mi5 joué, à 100 ¢ du Ré#5 visé, passait pour
// le partiel du Ré#5 : la note voisine était lue « Ré#5 −27,7 ¢ », fine.
// ±45 ¢ : une anche encore loin de sa cible (jusqu'à ±35 ¢, comme Auto-anches)
// y tient ; la note voisine (100 ¢) n'y entre pas.
export function partielEnPic(coarse, f) {
  if (!coarse?.mag || !coarse.binHz) return true;
  const tol = Math.max(2 * coarse.binHz, f * (2 ** (45 / 1200) - 1));
  const a = Math.max(1, Math.floor((f - tol) / coarse.binHz));
  const b = Math.min(coarse.mag.length - 2, Math.ceil((f + tol) / coarse.binHz));
  let im = -1, m = -1;
  for (let i = a; i <= b; i++) if (coarse.mag[i] > m) { m = coarse.mag[i]; im = i; }
  // …et qui domine les bords d'au moins 6 dB : un lobe secondaire du pied d'une
  // voisine peut faire un maximum à l'intérieur, juste après un zéro du bord.
  return im > a && im < b && m >= 2 * Math.max(coarse.mag[a], coarse.mag[b]);
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

// Anches de chaque note d'un accord (mode accord, registre Q exclu) : ce que
// l'instrument dit de son sommier des accords. Ewen (11/10/2026) : « à chaque
// ouverture de soufflet, 3 anches » ; une main gauche Stradella a deux voix à
// l'octave (16'+8') sur chaque note de l'accord, un diato la fondamentale, la
// quinte et l'octave de la fondamentale. Le moteur lisait la plus grave de
// chaque note et ignorait l'autre. `cfg.chordVoices` : liste de modèles
// { oct (octaves au-dessus de la plus grave anche de la note, 0 à 3),
// beatSign (unisson battant : −1, 0, 1), pied (« 16' », « 8' »… : le nom de la
// voix, ou rien), semi (seulement pour ce degré ; rien : tous) }. Une note sans
// modèle a une anche, la plus grave (comme avant). Pure.
const OTTAVA = { 1: '8va', 2: '15ma', 3: '22ma' };
export function chordVoiceTemplates(c) {
  const out = [];
  for (const t of Array.isArray(c?.chordVoices) ? c.chordVoices : []) {
    const oct = Math.round(Number(t?.oct ?? 0));
    if (!(oct >= 0 && oct <= 3)) continue;
    const beatSign = Math.sign(Number(t?.beatSign) || 0);
    const semi = t?.semi == null ? null : Math.round(Number(t.semi));
    if (semi != null && !(semi >= 0 && semi < 24)) continue;
    const pied = typeof t?.pied === 'string' && t.pied.length && t.pied.length <= 8 ? t.pied : null;
    if (out.some((u) => u.oct === oct && u.beatSign === beatSign && u.semi === semi)) continue;
    out.push({ oct, beatSign, semi, pied });
  }
  return out;
}
// Identifiant (et étiquette) d'une anche d'accord : le degré, puis la voix
// (« 1 16' », « 5 8' ») ; sans nom de voix, l'octave (« 1 8va ») ; la plus
// grave seule garde le degré nu (« 1 », comme avant).
export function chordVoiceId(lbl, t) {
  if (t.pied) return `${lbl} ${t.pied}`;
  const sgn = t.beatSign > 0 ? '+' : t.beatSign < 0 ? '−' : '';
  return `${lbl}${t.oct ? ` ${OTTAVA[t.oct]}` : ''}${sgn}`;
}

// Voisine d'une anche d'accord dans la même note, `d` octaves plus haut
// (d = 1) ou plus bas (d = −1) ; null sinon (ou hors du mode accord).
const degOct = (g) => {
  const v = g.voices[0]?.def;
  return v?.chordDeg != null ? [v.chordDeg, v.chordOct ?? 0] : null;
};
function chordSibling(groups, g, d) {
  const a = degOct(g);
  if (!a) return null;
  return groups.find((h) => { const b = degOct(h); return b && b[0] === a[0] && b[1] === a[1] + d; }) ?? null;
}
// Le partiel k de `g` tombe-t-il (à SEP_HZ près) sur un partiel d'une AUTRE
// note de l'accord ? Partiels jusqu'à la fréquence étudiée.
function chordForeignClash(groups, g, k) {
  const a = degOct(g);
  const f = k * g.center;
  return groups.some((h) => {
    const b = degOct(h);
    if (h === g || !b || b[0] === a[0]) return false;
    for (let j = 1; j <= Math.ceil(f / h.center) + 1; j++) if (Math.abs(f - j * h.center) < SEP_HZ) return true;
    return false;
  });
}

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
        const kl = lowestPartial(g.center);
        present = partialPresent(coarse, g.center, kl) && partielEnPic(coarse, kl * g.center);
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

  // Accord dont chaque note a plusieurs anches à l'octave (cfg.chordVoices) :
  // chordFromPeaks prend, pour chaque note, la raie la plus grave de sa classe
  // à moins de 20 dB de la plus forte. Le 16' d'une note peut avoir un
  // fondamental plus faible (mesuré sur synthèse : à −15 dB, tout l'accord était
  // lu une octave trop haut ; le 16' sur le 8', le 8' sur des partiels du 8').
  // Comme la garde d'octave d'un registre (engine.js, D4) : une anche plus
  // grave d'une octave a des partiels IMPAIRS à elle, qu'aucune anche de
  // l'octave au-dessus ne fait. On descend la note d'une octave si l'un de ses
  // partiels impairs (1 à 9) qui ne tombe sur aucun partiel d'une autre anche
  // de l'accord (±35 ¢) : il en faut DEUX (une anche a une série de partiels ;
  // une raie seule, un reste après une inversion du soufflet, faisait
  // descendre une quinte réelle d'une octave, session d'Ewen, P13), présents
  // (partialPresent : à moins de 30 dB du plus fort des dix premiers partiels
  // de cette note plus grave) et en pic (partielEnPic). Dans un accord majeur,
  // les partiels 3 et 5 de la fondamentale une octave plus bas tombent sur la
  // quinte et la tierce : restent 1, 7 et 9. Modifie `ch` ; jusqu'à deux octaves.
  abaisserOctaves(ch, coarse) {
    const c = this.cfg;
    if (c.mode !== 'chord') return;
    const tpls = chordVoiceTemplates(c);
    if (!tpls.length) return;
    const octsDe = (n) => {
      const t = tpls.filter((x) => x.semi == null || x.semi === n.semi);
      return t.length ? t.map((x) => x.oct) : [0];
    };
    let change = false;
    for (const n of ch.notes) {
      if (Math.max(...octsDe(n)) < 1) continue;
      for (let pas = 0; pas < 2; pas++) {
        const bas = n.midi - 12;
        if (bas < MIDI_MIN) break;
        const fBas = midiToFreq(bas, c);
        const autres = [];
        // Les autres notes à leur hauteur, et une octave plus bas (elles
        // peuvent elles aussi descendre : leurs huit premiers partiels ne
        // prouvent rien ici).
        for (const m of ch.notes) {
          for (const o of octsDe(m)) {
            for (const d of m === n ? [0] : [0, -12]) {
              const f = midiToFreq(m.midi + 12 * o + d, c);
              for (let k = 1; k * f < 12 * fBas && (d === 0 || k <= 8); k++) autres.push(k * f);
            }
          }
        }
        const libre = (k) => !autres.some((f) => Math.abs(1200 * Math.log2((k * fBas) / f)) < 35);
        const siens = [1, 3, 5, 7, 9].filter((k) => libre(k) && partialPresent(coarse, fBas, k) && partielEnPic(coarse, k * fBas));
        const sienne = siens.length >= 2;
        if (!sienne) break;
        n.midi = bas;
        change = true;
      }
    }
    if (change) ch.rootMidi = ch.notes.find((n) => n.semi === 0)?.midi ?? ch.notes[0].midi;
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
      // Chaque note de l'accord fait sonner les anches que l'instrument dit
      // (cfg.chordVoices, cf. chordVoiceTemplates) : 16'+8' d'une main
      // gauche Stradella, fondamentale et son octave d'un accord de diato...
      // Sans rien dit, une anche par note, la plus grave (comme avant).
      const tpls = c.mode === 'chord' ? chordVoiceTemplates(c) : [];
      return (this.chord?.notes ?? []).flatMap((n) => {
        const lbl = degreeLabel(n.semi);
        const siens = tpls.filter((t) => t.semi == null || t.semi === n.semi);
        return (siens.length ? siens : [{ oct: 0, beatSign: 0, pied: null }]).map((t) => {
          const id = chordVoiceId(lbl, t);
          return { id, label: id, oct: t.oct, beatSign: t.beatSign, fixedMidi: n.midi + 12 * t.oct,
            chordDeg: n.semi, chordOct: t.oct, pied: t.pied };
        });
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
      // Anche d'accord d'un unisson battant (cfg.chordVoices, beatSign) : sa
      // cible suit la courbe de battement, comme dans un registre.
      const t = v.fixedMidi != null && v.chordDeg != null && v.beatSign
        ? voiceTargetFreq(v.fixedMidi, { ...v, oct: 0, semi: 0 }, c)
        : v.fixedMidi != null
          ? { midi: v.fixedMidi, nominal: midiToFreq(v.fixedMidi, c), beat: 0,
              target: midiToFreq(v.fixedMidi, c) }
          : voiceTargetFreq(playedMidi, v, c);
      // Accord : une clé par DEGRÉ (la courbe « 5 » reste la même d'un accord
      // à l'autre, la légende ne s'allonge pas à chaque accord joué), et par
      // octave quand la note a plusieurs anches à l'octave (« c0o1 »).
      const key = v.chordDeg != null ? `c${v.chordDeg}${v.chordOct ? `o${v.chordOct}` : ''}`
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
      // Accord dont chaque note a plusieurs anches à l'octave (cfg.chordVoices) :
      // les mêmes règles qu'un registre 16'+8'. L'anche qui a une voisine de la
      // même note une octave au-dessus se mesure sur un partiel impair ; celle
      // du dessus (`chordUpper`) a tous ses partiels sur ceux de sa voisine du
      // dessous : elle est lue sur ses partiels séparés (octaveFuse) et, tant
      // que la fenêtre ne la sépare pas, estimée avec sa marge (confondu.js,
      // l'octave qui ne bat pas comprise).
      if (chordSibling(groups, g, 1)) g.avoidEven = true;
      if (chordSibling(groups, g, -1)) g.chordUpper = true;
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
        // L'anche du dessus d'une note d'accord à l'octave : comme le 8' d'un
        // registre (octaveClash), mais son partiel de mesure évite ceux des
        // AUTRES notes de l'accord (la quinte, la tierce), qui ne sont pas
        // sa voisine du dessous : leur raie ne serait ni elle, ni l'octave.
        if (g.chordUpper) {
          if (g.voices.length !== 1) continue;
          g.octaveClash = true;
          const bad = (k) => chordForeignClash(groups, g, k) || (g.avoidEven && k % 2 === 0);
          let k = g.kTrack;
          while (k < K_MAX && bad(k)) k++;
          if (!bad(k)) g.kTrack = k;
          continue;
        }
        // Accord : l'anche du dessous d'une note à l'octave (avoidEven) passe
        // aussi ici ; la règle des partiels impairs y est déjà (chordOdd).
        if (g.voices.length > 1 || (g.avoidEven && !chordOdd)) continue;
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
    // Accord : la même fondamentale peut porter un autre accord (Do, puis Do m) :
    // le plan suit aussi les notes jouées.
    const sig = this.chordDegrees() ? (this.chord?.notes ?? []).map((n) => n.midi).join(',') : '';
    if (!this.plan || this.plan.midi !== playedMidi || (this.plan.sig ?? '') !== sig) {
      this.plan = { midi: playedMidi, sig, k: new Map(), partials: new Map() };
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
