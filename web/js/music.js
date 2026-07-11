// Théorie musicale : notes, fréquences, tempéraments, transposition.
// Module pur (utilisable dans le navigateur, un Worker ou Node pour les tests).

export const NOTE_NAMES_EN = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
export const NOTE_NAMES_FR = ['Do', 'Do#', 'Ré', 'Ré#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'];

export const MIDI_MIN = 16;  // E0 ≈ 20,60 Hz
export const MIDI_MAX = 120; // C9 ≈ 8372 Hz

// Écarts en cents par rapport au tempérament égal, indexés par classe de
// hauteur (Do = 0). Valeurs usuelles, référence Do.
export const TEMPERAMENTS = {
  equal: {
    name: 'Égal',
    offsets: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  },
  pythagorean: {
    name: 'Pythagoricien',
    offsets: [0, 13.7, 3.9, -5.9, 7.8, -2.0, 11.7, 2.0, 15.6, 5.9, -3.9, 9.8],
  },
  meantone4: {
    name: 'Mésotonique 1/4 comma',
    offsets: [0, -24.0, -6.9, 10.3, -13.7, 3.4, -20.6, -3.4, -27.4, -10.3, 6.9, -17.1],
  },
  werckmeister3: {
    name: 'Werckmeister III',
    offsets: [0, -9.8, -7.8, -5.9, -9.8, -2.0, -11.7, -3.9, -7.8, -11.7, -3.9, -7.8],
  },
  kirnberger3: {
    name: 'Kirnberger III',
    offsets: [0, -9.8, -6.8, -5.9, -13.7, -2.0, -9.8, -3.4, -7.8, -10.3, -3.9, -11.7],
  },
  vallotti: {
    name: 'Vallotti',
    offsets: [0, -5.9, -3.9, -2.0, -7.8, 2.0, -7.8, -2.0, -3.9, -5.9, 0, -9.8],
  },
};

// Fréquence nominale d'une note MIDI selon la configuration.
// `transpose` décale la hauteur réelle : un accordeur transposé en Sib
// (transpose = -2) fait sonner Sib quand on lui demande Do.
export function midiToFreq(midi, cfg = {}) {
  const a4 = cfg.a4 ?? 440;
  const temperament = TEMPERAMENTS[cfg.temperament ?? 'equal'] ?? TEMPERAMENTS.equal;
  const off = temperament.offsets[((midi % 12) + 12) % 12];
  return a4 * Math.pow(2, (midi - 69) / 12 + off / 1200);
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

// Fréquence cible d'une voix pour une note jouée donnée.
export function voiceTargetFreq(playedMidi, voice, cfg) {
  const midi = playedMidi + 12 * voice.oct;
  const f = midiToFreq(midi, cfg);
  const beat = voice.beatSign ? voice.beatSign * beatTarget(playedMidi, cfg.beatCurve) : 0;
  return { midi, nominal: f, beat, target: f + beat };
}
