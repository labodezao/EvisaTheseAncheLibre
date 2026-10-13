// Découpe le son en NOTES pour le verrou de phase expérimental (v59) : sans toucher au moteur. Le Worker de mesure lui donne chaque bloc
// de son et chaque image du moteur ; quand une note tenue finit (ou dure 12 s), il rend le son de la note, le centre approximatif de
// l'unisson et les lectures du moteur sur la note (pour l'étiquette), que `verrou-worker.js` lit avec `lireNote` (verrou-note.js).
// Rien ici n'écrit dans le moteur : option éteinte, ce module n'est jamais appelé (worker.js).
export const NOTE_BLOC_S = 0.05;       // durée d'un bloc de niveau
export const NOTE_SEUIL_DB = -50;      // une note commence au-dessus de ce niveau (deux blocs de suite)
export const NOTE_CHUTE_DB = 20;       // et finit quand le niveau tombe de 20 dB sous son maximum pendant NOTE_FIN_S
export const NOTE_FIN_S = 0.3;
export const NOTE_MIN_S = 3;           // plus courte : pas de lecture (la plage stable demande 2 s)
export const NOTE_MAX_S = 12;          // plus longue : lue à 12 s
const MEMOIRE_S = 14;

const mediane = (a) => { const s = [...a].sort((p, q) => p - q); return s[s.length >> 1]; };

export class LecteurNote {
  constructor(sr, surNote) {
    this.sr = sr; this.surNote = surNote;
    this.bloc = Math.round(NOTE_BLOC_S * sr);
    this.anneau = new Float32Array(Math.round(MEMOIRE_S * sr));
    this.n = 0;                 // échantillons reçus au total
    this.e = 0; this.ne = 0;    // énergie du bloc en cours
    this.note = null;           // { debut (échantillon), max (dB), bas (blocs sous le seuil de chute), images: [[t, f8, f8+]], midi }
    this.haut = 0;              // blocs de suite au-dessus du seuil
    this.attente = false;       // après une note de 12 s : on attend le silence avant d'en lire une autre
  }

  // chunk : Float32Array ; tick : l'image du moteur rendue par ce bloc, ou null.
  alimenter(chunk, tick = null) {
    const L = this.anneau.length;
    for (let i = 0; i < chunk.length; i++) {
      const v = chunk[i];
      this.anneau[(this.n + i) % L] = v;
      this.e += v * v;
      if (++this.ne === this.bloc) { this._bloc(10 * Math.log10(this.e / this.bloc + 1e-20), this.n + i + 1); this.e = 0; this.ne = 0; }
    }
    this.n += chunk.length;
    if (tick && this.note) {
      const vs = (tick.groups ?? []).filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices ?? []);
      const a = vs.find((v) => v.def?.id === '8'), b = vs.find((v) => v.def?.id === '8+');
      if (a?.tracked && b?.tracked && !a.coarse && !b.coarse && a.fMeas != null && b.fMeas != null) {
        this.note.images.push([tick.time - this.note.debut / this.sr, a.fMeas, b.fMeas]);
      }
      if (tick.playedMidi != null) this.note.midi = tick.playedMidi;
    }
  }

  _bloc(db, finBloc) {
    if (!this.note) {
      if (db > NOTE_SEUIL_DB) { if (++this.haut >= 2 && !this.attente) this.note = { debut: finBloc - 2 * this.bloc, max: db, bas: 0, images: [], midi: null }; } else { this.haut = 0; this.attente = false; }
      return;
    }
    this.note.max = Math.max(this.note.max, db);
    this.note.bas = db < this.note.max - NOTE_CHUTE_DB ? this.note.bas + 1 : 0;
    const duree = (finBloc - this.note.debut) / this.sr;
    if (this.note.bas * NOTE_BLOC_S >= NOTE_FIN_S) this._finir(finBloc - this.note.bas * this.bloc);
    else if (duree >= NOTE_MAX_S) { this._finir(finBloc); this.attente = true; }
  }

  _finir(fin) {
    const { debut, images, midi } = this.note;
    this.note = null; this.haut = 0;
    const N = fin - debut;
    if (N / this.sr < NOTE_MIN_S || N > this.anneau.length) return;
    const x = new Float32Array(N), L = this.anneau.length;
    for (let i = 0; i < N; i++) x[i] = this.anneau[(debut + i) % L];
    const tard = images.filter((q) => q[0] > 1.5);
    const fc = tard.length >= 3 ? (mediane(tard.map((q) => q[1])) + mediane(tard.map((q) => q[2]))) / 2
      : midi != null ? 440 * 2 ** ((midi - 69) / 12) : null;
    if (fc == null) return;
    this.surNote({ x, sr: this.sr, fc, moteur: images, midi, t: debut / this.sr });
  }
}

// Ce que la page garde d'une lecture de note : de petits nombres, pas le son ni les raies.
export function resumeLecture(l, { midi = null, t = null, ms = null } = {}) {
  return {
    sure: !!l.sure, raison: l.raison ?? null, f: l.f ?? null, centre: l.centre ?? null, demi: l.demi ?? null, omega: l.omega ?? null,
    sigmaC: l.sigmaC ?? null, plageS: null,
    midi, t, ms,
  };
}
