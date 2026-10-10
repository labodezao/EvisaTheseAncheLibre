// Théorie musicale : notes, fréquences, tempéraments, transposition.
// Module pur (utilisable dans le navigateur, un Worker ou Node pour les tests).

export const NOTE_NAMES_EN = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
export const NOTE_NAMES_FR = ['Do', 'Do#', 'Ré', 'Ré#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'];

export const MIDI_MIN = 16;  // E0 ≈ 20,60 Hz
export const MIDI_MAX = 120; // C9 ≈ 8372 Hz

// Tempéraments : 12 écarts en cents par rapport au tempérament égal, indexés
// par classe de hauteur (Do = 0), tels que les sources les donnent (Do à 0).
// `midiToFreq` les ramène au La : le La4 vaut toujours `a4` (La fixe, comme
// tout accordeur). `nom` : deux mots pour l'interface ; `name` : l'ancien nom
// (v28, rapport) ; `groupe` : 'egal', 'historique', 'cordier' ou 'juste'.
// `octaveCents` (1200 par défaut) : octave étirée (Cordier), appliquée depuis La4.
// Les six premiers sont ceux de la v28, valeurs inchangées (au dixième).
// Les autres : calculés depuis la description de chaque quinte (rétrécissement
// en fraction de comma pythagoricien, PC = 23,460 c, ou syntonique,
// SC = 21,506 c), arrondis au centième ; test/music.test.mjs refait le calcul
// quinte par quinte. Railsback (étirement du piano) : pas de source chiffrée
// note par note, non codé.
const QUINTE_JUSTE = 1200 * Math.log2(3 / 2);

export const TEMPERAMENTS = {
  equal: {
    name: 'Égal', nom: 'Égal', groupe: 'egal',
    description: 'Douze demi-tons égaux de 100 ¢.',
    source: 'Définition.',
    offsets: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  },
  pythagorean: {
    name: 'Pythagoricien', nom: 'Pythagoricien', groupe: 'historique',
    description: 'Onze quintes pures de Mib à Sol#, loup Sol#-Mib.',
    source: 'Barbour, Tuning and Temperament (1951), chap. 2.',
    offsets: [0, 13.7, 3.9, -5.9, 7.8, -2.0, 11.7, 2.0, 15.6, 5.9, -3.9, 9.8],
  },
  meantone4: {
    name: 'Mésotonique 1/4 comma', nom: 'Mésotonique 1/4', groupe: 'historique',
    description: 'Quintes rétrécies de 1/4 SC de Mib à Sol#, tierces majeures pures, loup Sol#-Mib.',
    source: 'Aron, Toscanello (1523) ; Barbour (1951), chap. 3.',
    offsets: [0, -24.0, -6.9, 10.3, -13.7, 3.4, -20.6, -3.4, -27.4, -10.3, 6.9, -17.1],
  },
  werckmeister3: {
    name: 'Werckmeister III', nom: 'Werckmeister III', groupe: 'historique',
    description: 'Do-Sol, Sol-Ré, Ré-La, Si-Fa# rétrécies de 1/4 PC, les autres pures (aussi dit Werckmeister I).',
    source: 'Werckmeister, Musicalische Temperatur (1691) : n° III de l\'ouvrage, I des tempéraments « corrects ».',
    offsets: [0, -9.8, -7.8, -5.9, -9.8, -2.0, -11.7, -3.9, -7.8, -11.7, -3.9, -7.8],
  },
  kirnberger3: {
    name: 'Kirnberger III', nom: 'Kirnberger III', groupe: 'historique',
    description: 'Do-Sol-Ré-La-Mi rétrécies de 1/4 SC, Fa#-Do# du schisma, les autres pures.',
    source: 'Kirnberger, lettre à Forkel (1779) ; Barbour (1951).',
    offsets: [0, -9.8, -6.8, -5.9, -13.7, -2.0, -9.8, -3.4, -7.8, -10.3, -3.9, -11.7],
  },
  vallotti: {
    name: 'Vallotti', nom: 'Vallotti', groupe: 'historique',
    description: 'Fa-Do-Sol-Ré-La-Mi-Si rétrécies de 1/6 PC, les autres pures. Young II : le même, une quinte plus haut (« Vallotti-Young »).',
    source: 'Vallotti, Della scienza teorica e pratica della moderna musica (1779).',
    offsets: [0, -5.9, -3.9, -2.0, -7.8, 2.0, -7.8, -2.0, -3.9, -5.9, 0, -9.8],
  },
  werckmeister4: {
    name: 'Werckmeister IV', nom: 'Werckmeister IV', groupe: 'historique',
    description: 'Do-Sol, Ré-La, Mi-Si, Fa#-Do#, Sib-Fa rétrécies de 1/3 PC ; Sol#-Ré# et Mib-Sib élargies de 1/3 PC.',
    source: 'Werckmeister, Musicalische Temperatur (1691) : n° IV (II des « corrects »).',
    offsets: [0, -17.6, -3.91, -5.87, -7.82, -1.96, -11.73, -5.87, -15.64, -9.78, 3.91, -13.69],
  },
  werckmeister5: {
    name: 'Werckmeister V', nom: 'Werckmeister V', groupe: 'historique',
    description: 'Ré-La, La-Mi, Fa#-Do#, Do#-Sol#, Fa-Do rétrécies de 1/4 PC ; Sol#-Ré# élargie de 1/4 PC.',
    source: 'Werckmeister, Musicalische Temperatur (1691) : n° V (III des « corrects »).',
    offsets: [0, -3.91, 3.91, 0, -3.91, 3.91, 0, 1.96, -7.82, 0, 1.96, -1.96],
  },
  kirnberger1: {
    name: 'Kirnberger I', nom: 'Kirnberger I', groupe: 'historique',
    description: 'Ré-La rétrécie d\'un comma syntonique, Fa#-Do# du schisma, les autres pures.',
    source: 'Kirnberger, Die Kunst des reinen Satzes (1771).',
    offsets: [0, -9.78, 3.91, -5.87, -13.69, -1.96, -9.78, 1.96, -7.82, -15.64, -3.91, -11.73],
  },
  kirnberger2: {
    name: 'Kirnberger II', nom: 'Kirnberger II', groupe: 'historique',
    description: 'Ré-La et La-Mi rétrécies de 1/2 SC, Fa#-Do# du schisma, les autres pures.',
    source: 'Kirnberger, Die Kunst des reinen Satzes (1771-1779).',
    offsets: [0, -9.78, 3.91, -5.87, -13.69, -1.96, -9.78, 1.96, -7.82, -4.89, -3.91, -11.73],
  },
  young1: {
    name: 'Young I', nom: 'Young I', groupe: 'historique',
    description: 'Do-Sol-Ré-La-Mi rétrécies de 3/16 SC ; Mi-Si, Si-Fa#, Sib-Fa, Fa-Do se partagent le reste (environ 1/12 SC) ; les autres pures.',
    source: 'T. Young, Philosophical Transactions 90 (1800) ; tableau de en.wikipedia « Young temperament ».',
    offsets: [0, -6.11, -4.15, -2.2, -8.31, -0.12, -8.06, -2.08, -4.15, -6.23, -0.24, -8.19],
  },
  young2: {
    name: 'Young II', nom: 'Young II', groupe: 'historique',
    description: 'Do-Sol-Ré-La-Mi-Si-Fa# rétrécies de 1/6 PC, les autres pures (Vallotti une quinte plus haut).',
    source: 'T. Young, Philosophical Transactions 90 (1800).',
    offsets: [0, -9.78, -3.91, -5.87, -7.82, -1.96, -11.73, -1.96, -7.82, -5.87, -3.91, -9.78],
  },
  kellner: {
    name: 'Kellner (Bach)', nom: 'Kellner Bach', groupe: 'historique',
    description: 'Do-Sol-Ré-La-Mi et Si-Fa# rétrécies de 1/5 PC, les autres pures.',
    source: 'H. A. Kellner, Wie stimme ich selbst mein Cembalo ? (1977).',
    offsets: [0, -9.78, -5.47, -5.87, -10.95, -1.96, -11.73, -2.74, -7.82, -8.21, -3.91, -8.99],
  },
  neidhardt: {
    name: 'Neidhardt (grande ville, 1724)', nom: 'Neidhardt ville', groupe: 'historique',
    description: 'Do-Sol, Sol-Ré, Ré-La rétrécies de 1/6 PC ; La-Mi, Si-Fa#, Fa#-Do#, Do#-Sol#, Mib-Sib, Sib-Fa de 1/12 PC ; Mi-Si, Fa-Do, Sol#-Mib pures.',
    source: 'Neidhardt, Sectio canonis harmonici (1724), « für eine große Stadt » ; hpschd.nu, Temperaments XXIII.',
    offsets: [0, -3.91, -3.91, -1.96, -5.87, -1.96, -3.91, -1.96, -3.91, -5.87, -1.96, -3.91],
  },
  rameau: {
    name: 'Rameau (1726)', nom: 'Rameau 1726', groupe: 'historique',
    description: 'Sib-Fa-Do-Sol-Ré-La-Mi-Si rétrécies de 1/4 SC, Si-Fa# et Fa#-Do# pures, Do#-Sol# de 1/6 SC ; Sol#-Mib et Mib-Sib élargies d\'autant.',
    source: 'Rameau, Nouveau système de musique théorique (1726), tempérament ordinaire, lecture de K. Lang (Auf Wohlklangswellen durch der Töne Meer).',
    offsets: [0, -13.2, -6.84, -3.99, -13.69, 3.42, -15.15, -3.42, -14.83, -10.26, 6.84, -17.11],
  },
  meantone5: {
    name: 'Mésotonique 1/5 comma', nom: 'Mésotonique 1/5', groupe: 'historique',
    description: 'Quintes rétrécies de 1/5 SC de Mib à Sol#, loup Sol#-Mib.',
    source: 'Verheijen (vers 1600) ; Barbour (1951), chap. 3.',
    offsets: [0, -16.42, -4.69, 7.04, -9.39, 2.35, -14.08, -2.35, -18.77, -7.04, 4.69, -11.73],
  },
  meantone6: {
    name: 'Mésotonique 1/6 comma', nom: 'Mésotonique 1/6', groupe: 'historique',
    description: 'Quintes rétrécies de 1/6 SC de Mib à Sol#, loup Sol#-Mib.',
    source: 'Silbermann (selon Sorge, 1748) ; Barbour (1951), chap. 3.',
    offsets: [0, -11.41, -3.26, 4.89, -6.52, 1.63, -9.78, -1.63, -13.04, -4.89, 3.26, -8.15],
  },
  meantone3: {
    name: 'Mésotonique 1/3 comma (Salinas)', nom: 'Salinas 1/3', groupe: 'historique',
    description: 'Quintes rétrécies de 1/3 SC de Mib à Sol#, tierces mineures pures, loup Sol#-Mib.',
    source: 'Salinas, De musica libri septem (1577) ; Barbour (1951), chap. 3.',
    offsets: [0, -36.5, -10.43, 15.64, -20.86, 5.21, -31.28, -5.21, -41.71, -15.64, 10.43, -26.07],
  },
  cordier: {
    name: 'Cordier (égal à quintes justes)', nom: 'Cordier', groupe: 'cordier',
    description: 'Quinte pure partagée en 7 demi-tons égaux de 100,279 c : octave étirée de 3,35 c.',
    source: 'S. Cordier, Piano bien tempéré et justesse orchestrale (1982) ; tableur d\'Ewen « Tempérament Cordier.xlsx », feuille TE5J A440.',
    offsets: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    // 12 demi-tons de (3/2)^(1/7) : 1203,3514 c. C'est la valeur du tableur
    // d'Ewen (« Décalage octave 3,3514 cents », 0,2793 c par demi-ton depuis
    // La4) et de la théorie (1/7 de PC) ; gardée exacte pour que Do-Sol fasse
    // 701,955 c (une octave de 1203,91 c donnerait une quinte de 702,28 c).
    octaveCents: (12 / 7) * QUINTE_JUSTE,
  },
  just: {
    name: 'Intonation juste', nom: 'Intonation juste', groupe: 'juste',
    description: 'Gamme de Ptolémée (diatonique intense) et ses altérations, en rapports simples sur la tonique.',
    source: 'Ptolémée, Harmoniques ; gamme juste à 5 limites : 1, 16/15, 9/8, 6/5, 5/4, 4/3, 45/32, 3/2, 8/5, 5/3, 9/5, 15/8.',
    offsets: [0, 11.73, 3.91, 15.64, -13.69, -1.96, -9.78, 1.96, 13.69, -15.64, 17.6, -11.73],
  },
};

// Écart d'une classe de hauteur au tempérament égal, ramené au La (La = 0).
// `tonique` (0 = Do) transpose le tempérament : son Do devient la tonique.
export function ecartTemperament(pc, cfg = {}) {
  const T = TEMPERAMENTS[cfg.temperament ?? 'equal'] ?? TEMPERAMENTS.equal;
  const t = (((cfg.tonique ?? 0) % 12) + 12) % 12;
  const o = (k) => T.offsets[(((k - t) % 12) + 12) % 12];
  return o(((pc % 12) + 12) % 12) - o(9);
}

// Fréquence nominale d'une note MIDI : La4 = `a4`, tempérament ramené au La,
// octave étirée (Cordier, depuis La4), et décalage global `decalageCents`
// (Ewen, 06/10 : « un shift des cents vers le haut ») qui déplace toutes les
// cibles comme le La. `transpose` décale la hauteur réelle (un accordeur
// transposé en Sib fait sonner Sib quand on lui demande Do) : c'est le
// moteur qui s'en charge, pas cette fonction.
export function midiToFreq(midi, cfg = {}) {
  const a4 = cfg.a4 ?? 440;
  const temperament = TEMPERAMENTS[cfg.temperament ?? 'equal'] ?? TEMPERAMENTS.equal;
  const off = ecartTemperament(midi, cfg) + (cfg.decalageCents || 0);
  const pas = temperament.octaveCents ? ((midi - 69) * temperament.octaveCents) / 14400 : (midi - 69) / 12;
  return a4 * Math.pow(2, pas + off / 1200);
}

// Note MIDI (fractionnaire, tempérament égal) la plus proche d'une fréquence.
export function freqToMidiEqual(freq, a4 = 440) {
  return 69 + 12 * Math.log2(freq / a4);
}

// Note MIDI entière la plus proche en tenant compte du tempérament.
export function nearestMidi(freq, cfg = {}) {
  const approx = Math.round(freqToMidiEqual(freq, cfg.a4 ?? 440));
  let best = approx;
  let bestAbs = Infinity;
  for (let m = approx - 1; m <= approx + 1; m++) {
    if (m < 0 || m > 127) continue;
    const c = Math.abs(centsBetween(freq, midiToFreq(m, cfg)));
    if (c < bestAbs) { bestAbs = c; best = m; }
  }
  return best;
}

export function centsBetween(freq, ref) {
  return 1200 * Math.log2(freq / ref);
}

// Classe de couleur d'un écart en cents, pilotée par la tolérance choisie
// par l'utilisateur — partagée par le tableau des anches, les cartes de
// lecture, la grille de progression et le rapport, pour que « vert » ait
// partout le même sens.
export function centsClass(c, tol = 1) {
  if (c == null || !isFinite(c)) return 'dim';
  const a = Math.abs(c);
  if (a <= tol) return 'ok';
  if (a <= Math.max(5, 2 * tol)) return 'warn';
  return 'bad';
}

// Déviation d'Allan « overlapping » d'une série de valeurs (ici l'écart en
// cents, proportionnel à la fréquence fractionnaire). σ(τ) caractérise la
// stabilité de fréquence selon le temps d'intégration τ = m·τ0, et sépare
// les types de bruit (pente −½ : bruit blanc de fréquence ; plancher puis
// remontée : marche aléatoire / dérive). Estimateur overlapping standard :
//   ȳ_j(m) = moyenne de m échantillons consécutifs
//   σ²(m) = 1/(2(N−2m+1)) Σ_j (ȳ_{j+m}(m) − ȳ_j(m))²
// Retourne [{ tau, sigma }] pour des m en progression ~logarithmique.
export function overlappingAllan(y, tau0) {
  const N = y.length;
  if (N < 8 || !(tau0 > 0)) return [];
  // Sommes cumulées pour des moyennes glissantes en O(1).
  const cum = new Float64Array(N + 1);
  for (let i = 0; i < N; i++) cum[i + 1] = cum[i] + y[i];
  const avg = (j, m) => (cum[j + m] - cum[j]) / m; // moyenne de y[j..j+m-1]
  const out = [];
  const mMax = Math.floor((N - 1) / 2);
  let m = 1;
  let lastM = 0;
  while (m <= mMax) {
    if (m !== lastM) {
      const K = N - 2 * m + 1;
      let s = 0;
      for (let j = 0; j < K; j++) {
        const d = avg(j + m, m) - avg(j, m);
        s += d * d;
      }
      const variance = s / (2 * K);
      out.push({ tau: m * tau0, sigma: Math.sqrt(variance) });
      lastM = m;
    }
    // Progression logarithmique (~1,3×) pour un tracé lisible et léger.
    m = Math.max(m + 1, Math.floor(m * 1.3));
  }
  return out;
}

export function noteLabel(midi, lang = 'fr') {
  const pc = ((midi % 12) + 12) % 12;
  const oct = Math.floor(midi / 12) - 1;
  const name = (lang === 'fr' ? NOTE_NAMES_FR : NOTE_NAMES_EN)[pc];
  return { name, oct, full: `${name}${oct}` };
}

// Analyse d'une liste de notes saisies par l'utilisateur, ex. « C4 E4 G4 »
// ou « do4 mi4 sol4 ». Retourne une liste de numéros MIDI (ou null si vide).
export function parseNoteList(text) {
  if (!text) return null;
  const out = [];
  const rx = /([a-gA-G]|do|ré|re|mi|fa|sol|la|si)\s*(#|b)?\s*(-?\d)/giu;
  const fr = { do: 0, re: 2, 'ré': 2, mi: 4, fa: 5, sol: 7, la: 9, si: 11 };
  const en = { c: 0, d: 2, e: 4, f: 5, g: 7, a: 9, b: 11 };
  const norm = text.normalize('NFC');
  let m;
  while ((m = rx.exec(norm)) !== null) {
    const name = m[1].toLowerCase();
    let pc = name.length > 1 ? fr[name] : en[name];
    if (pc === undefined) continue;
    if (m[2] === '#') pc += 1;
    if (m[2] === 'b') pc -= 1;
    const midi = (parseInt(m[3], 10) + 1) * 12 + pc;
    if (midi >= 0 && midi <= 127) out.push(midi);
  }
  return out.length ? out : null;
}

// ---- Registres d'accordéon -------------------------------------------------
// Une voix = { id, label, oct (écart d'octave vs note jouée), beatSign }.
// beatSign multiplie la courbe de battement (−1, 0, +1). Les voix d'une même
// octave sont mesurées par le même traqueur zoom.

export const REGISTER_PRESETS = {
  M: {
    name: "Flûte 8'",
    voices: [{ id: '8', label: "8'", oct: 0, beatSign: 0 }],
  },
  MM: {
    name: "Tremolo 8'+8'",
    voices: [
      { id: '8', label: "8'", oct: 0, beatSign: 0 },
      { id: '8+', label: "8'+", oct: 0, beatSign: 1 },
    ],
  },
  MMM: {
    name: "Musette 8'−/8'/8'+",
    voices: [
      { id: '8-', label: "8'−", oct: 0, beatSign: -1 },
      { id: '8', label: "8'", oct: 0, beatSign: 0 },
      { id: '8+', label: "8'+", oct: 0, beatSign: 1 },
    ],
  },
  LM: {
    name: "Bandonéon 16'+8'",
    voices: [
      { id: '16', label: "16'", oct: -1, beatSign: 0 },
      { id: '8', label: "8'", oct: 0, beatSign: 0 },
    ],
  },
  LMM: {
    name: "16'+8'+8'+",
    voices: [
      { id: '16', label: "16'", oct: -1, beatSign: 0 },
      { id: '8', label: "8'", oct: 0, beatSign: 0 },
      { id: '8+', label: "8'+", oct: 0, beatSign: 1 },
    ],
  },
  LMH: {
    name: "16'+8'+4'",
    voices: [
      { id: '16', label: "16'", oct: -1, beatSign: 0 },
      { id: '8', label: "8'", oct: 0, beatSign: 0 },
      { id: '4', label: "4'", oct: 1, beatSign: 0 },
    ],
  },
  LMMH: {
    name: "16'+8'+8'+4'",
    voices: [
      { id: '16', label: "16'", oct: -1, beatSign: 0 },
      { id: '8', label: "8'", oct: 0, beatSign: 0 },
      { id: '8+', label: "8'+", oct: 0, beatSign: 1 },
      { id: '4', label: "4'", oct: 1, beatSign: 0 },
    ],
  },
  Q: {
    // Basse et sa quinte, comme la basse fondamentale d'un chromatique :
    // deux anches à la quinte juste au-dessus, mesurées chacune.
    name: 'Quinte (fondamentale + quinte)',
    voices: [
      { id: '1', label: 'fond.', oct: 0, beatSign: 0 },
      { id: '5', label: 'quinte', oct: 0, semi: 7, beatSign: 0 },
    ],
  },
  LMMMH: {
    name: "16'+musette+4' (5 anches)",
    voices: [
      { id: '16', label: "16'", oct: -1, beatSign: 0 },
      { id: '8-', label: "8'−", oct: 0, beatSign: -1 },
      { id: '8', label: "8'", oct: 0, beatSign: 0 },
      { id: '8+', label: "8'+", oct: 0, beatSign: 1 },
      { id: '4', label: "4'", oct: 1, beatSign: 0 },
    ],
  },
};

// Courbe de battement (« liste de battements ») : battement cible en Hz pour
// une note MIDI, interpolé exponentiellement entre deux points d'ancrage,
// avec écrasements ponctuels (overrides) par note.
export function beatTarget(midi, curve) {
  const c = curve ?? {};
  const ov = c.overrides?.[midi];
  if (ov !== undefined && ov !== null && ov !== '') return Number(ov);
  const mLow = c.midiLow ?? 48;   // Do3
  const mHigh = c.midiHigh ?? 96; // Do7
  const bLow = Math.max(0.01, c.bLow ?? 0.8);
  const bHigh = Math.max(0.01, c.bHigh ?? 3.0);
  if (mHigh === mLow) return bLow; // configuration dégénérée (JSON importé)
  const t = (midi - mLow) / (mHigh - mLow);
  return bLow * Math.pow(bHigh / bLow, t);
}

// Décalage par note (« sweetener » des accordeurs de piano ; le mot de
// l'interface est « décalage par note ») : cents par note JOUÉE, comme le
// battement voulu (les anches d'une même touche gardent leurs octaves pures).
// `d` = { voix: 'toutes' | 'battantes', cents: { [midi]: cents } } :
// 'toutes' décale chaque anche ; 'battantes' (listes de trémolo de Dirk's)
// ne décale que les voix qui battent, multiplié par leur signe (8'+ : +c,
// 8'- : -c). Données pures : le cfg passe par postMessage, pas de fonction.
export function decalageDeVoix(playedMidi, voice, d) {
  if (!d || !d.cents) return 0;
  const c = Number(d.cents[playedMidi]);
  if (!Number.isFinite(c) || c === 0) return 0;
  if (d.voix === 'battantes') return voice.beatSign ? voice.beatSign * c : 0;
  return c;
}

// Fréquence cible d'une voix pour une note jouée donnée.
// nominal : l'échelle (tempérament, La, décalage global) ; target : la liste
// (nominal décalé par note, plus le battement voulu en Hz). Le moteur rend
// les deux écarts : dCents (échelle) et dTargetCents (liste).
export function voiceTargetFreq(playedMidi, voice, cfg) {
  const midi = playedMidi + 12 * voice.oct + (voice.semi || 0);   // semi : quinte, tierce…
  const f = midiToFreq(midi, cfg);
  const beat = voice.beatSign ? voice.beatSign * beatTarget(playedMidi, cfg.beatCurve) : 0;
  const d = decalageDeVoix(playedMidi, voice, cfg.decalageParNote);
  if (!d) return { midi, nominal: f, beat, target: f + beat };
  return { midi, nominal: f, beat, decalage: d, target: f * Math.pow(2, d / 1200) + beat };
}

// ---- Battements d'intervalles (audit du 10/10/2026, docs/AUDIT-REPETABILITE.md) ----
// Deux anches f_b (basse) et f_h (haute) à l'intervalle m:n (f_h / f_b ≈ m / n)
// ont un partiel commun : le partiel m de la basse et le partiel n de la
// haute. Le battement entendu est b = m·f_b − n·f_h (Hz). Signe gardé :
// b > 0, l'intervalle est plus étroit que le pur (rétréci) ; b < 0, plus
// large. Quinte en tempérament égal : b = f_b (3 − 2·2^(7/12)) = +0,003386 f_b
// (rétrécie de 1,955 ¢, +0,886 Hz à Do4) ; quinte pure (Cordier) : 0. Le
// battement voulu se tire des cibles du moteur (m·cible_b − n·cible_h) : il
// suit le tempérament, le La, les décalages par note.
// Clé : écart en demi-tons entre les deux notes (de 1 à 24).
export const INTERVALLES = Object.freeze({
  3: { m: 6, n: 5, nom: 'tierce mineure' }, // donnée
  4: { m: 5, n: 4, nom: 'tierce' }, // donnée
  5: { m: 4, n: 3, nom: 'quarte' }, // donnée
  7: { m: 3, n: 2, nom: 'quinte' }, // donnée
  12: { m: 2, n: 1, nom: 'octave' }, // donnée
  19: { m: 3, n: 1, nom: 'douzieme' }, // donnée
  24: { m: 4, n: 1, nom: 'double octave' }, // donnée
});

// Battement de l'intervalle m:n entre f_b et f_h (Hz, signe gardé).
export const battementIntervalle = (fb, fh, m, n) => m * fb - n * fh;
