// Deux anches d'un unisson que la FFT du traqueur ne sépare pas : lecture par un modèle à deux raies sur un nombre ENTIER de battements
// (lot C1 de l'audit Fable « superposition » du 19/10/2026, drapeau cfg.K_MESURE ; spécification : RAPPORT-SUPERPOSITION.md, § 0 et § 7).
//
// Le défaut. Le partiel de mesure k est choisi d'après l'écart VOULU par la table (plan.js, unisonHarmonic) et la fenêtre de la FFT dure
// 1,37 s : quand k·Ω < 1,4 Hz (deux cases), l'amas ne contient qu'un pic, la fréquence lue est celle de la SOMME des deux sinus. Une somme
// a·cos(2π f t) + b·cos(2π (f + Ω) t) a une fréquence instantanée qui oscille à Ω (excursion Ω·r/(1 − r) au creux) : le chiffre suit le
// battement, se pose entre les deux raies à niveaux voisins, saute de l'une à l'autre. Aucun traitement d'amplitude n'y change rien (la phase
// d'une somme ne dépend pas de son enveloppe) : il faut SÉPARER les composantes avant de lire une fréquence.
//
// Le mécanisme. Sur une fenêtre de n/Ω secondes (n battements entiers), les deux exponentielles e^{j2π f1 t} et e^{j2π (f1 + Ω) t} sont
// ORTHOGONALES : le produit scalaire de l'une par l'autre vaut sinc(n) = 0. Chaque raie se lit alors sans l'influence de l'autre, et tout
// ce que le couplage des anches fait au premier ordre (la raie latérale d'une anche tombe exactement sur la porteuse de l'autre) change leur
// amplitude et leur phase mais pas leur fréquence : c'est la hauteur de chaque anche EN PLACE, ce que le luthier accorde. On l'obtient par
// l'ajustement à deux raies du peigne (peigne.js, ajusterPeigne avec m = 0 et 1 : positions F et F + Δ libres, amplitudes complexes éliminées
// par moindres carrés, projection de Golub et Pereyra), sur une fenêtre dont la durée est le plus petit nombre entier de battements d'au
// moins ENT.FEN_MIN_S. Mesuré sur synthèse : il converge à Δ à 1e-3 Hz près depuis presque tout point de départ, même sur une fenêtre plus
// courte qu'un battement (1,0 s pour Ω = 0,6 Hz), à tous les niveaux relatifs de 0 à −20 dB.
//
// Ce que ce n'est pas : un « sûr ». Le certificat (certificat.js) reste le seul à dire une lecture certifiée ; ici la voix est lue
// (`source` 'modele2'), avec son incertitude de Cramér-Rao (`sigmaCents`), et l'état de la paire la garde « en cours ». Garde-fous contre une
// anche seule prise pour deux : résidu relatif <= ENT.R_MAX, deuxième raie à ENT.AMP_MIN de la première au moins (UNISSON_DB de proches.js :
// −20 dB, plus bas ce sont des raies latérales du soufflet), écart dans [ENT.OMEGA_MIN, résolution de la FFT], deux ajustements d'accord
// d'affilée avant de prendre la main.

import { ajusterPeigne } from './peigne.js';
import { centsBetween } from '../music.js';
import { PROCHES_CASES } from './proches.js';

export const ENT = {
  R_MAX: 0.02,          // résidu relatif au-delà duquel le modèle à deux raies n'explique pas la bande (la synthèse : 2e-4 à 4e-4 ; le peigne : 0,05)
  AMP_MIN: 0.15,        // la plus faible des deux raies vaut au moins cette part de la plus forte (−16,5 dB ; les anches réelles d'un unisson : −11 à −16 dB au plus, proches.js ; UNISSON_DB = 20 pour les restes)
  R_REL: 0.1,           // le résidu est au plus cette part de l'énergie de la raie faible : une anche seule modulée (vibrato du soufflet) a deux raies latérales ÉGALES, le modèle en ajuste une et l'autre reste (résidu = l'énergie de la raie ajustée, mesuré : r = 1,0e-2 pour une raie à −20 dB) ; une vraie deuxième anche laisse 3e-4
  RAIE_LIBRE_MIN: 0.07, // une raie de la FFT à plus de cette part de la plus forte (−23 dB) que le modèle n'explique pas rend le modèle invalide : une troisième raie (la vraie deuxième anche d'un unisson plus ouvert que le modèle, mesuré : 2,5 Hz pour un modèle à 0,39 Hz, 33 ¢ de faux) ou un reste de partiel
  RAIE_LIBRE_CASES: 2.5, // …à plus de ce nombre de cases de la FFT de chacune des deux raies du modèle (les lobes de Hann valent −31 dB au-delà de 2 cases)
  OMEGA_MIN: 0.15,      // Hz (fondamentale) : en dessous, une anche seule et ses raies latérales de soufflet
  FEN_MIN_S: 1.04,      // la fenêtre entière dure au moins ça (une FFT de Hann de 128 points fait 1,37 s, la pente de l'amas lit 70 % de sa fenêtre : 0,96 s)
  FEN_MAX_S: 3.4,       // …et au plus ça (n/Ω pour Ω = 0,3 Hz) ; plus long, la fenêtre n'est plus un nombre entier de battements
  FEN_FROID_S: 1.6,     // fenêtre d'un ajustement à froid (Ω inconnu)
  ENTIERE_TOL: 0.05,    // écart toléré de la fenêtre à un nombre entier de battements (|T·Δ − entier|)
  FEN_ABS_MIN_S: 1.0,   // on ne tente rien avec moins de son que ça
  ENTREE: 2,            // ajustements d'accord d'affilée avant de prendre la main
  ACCORD: 0.15,         // deux ajustements s'accordent si leurs Δ diffèrent de moins de cette part…
  ACCORD_C: 0.5,        // …et leurs milieux de moins de ce nombre de ¢
  TENUE_S: 0.5,         // un ajustement qui échoue une fois : le précédent tient (comme le peigne)
  PAS_FROID_S: 0.17,    // un ajustement à froid toutes les 0,17 s au plus (deux images)
  PAS_CHAUD_S: 0.25,    // …et un ajustement à chaud toutes les trois images (la fenêtre lue dure 1 à 3,4 s : une lecture plus fréquente n'apporte rien, et le coût par image compte sur un téléphone)
  ITER: 12,
  ITER_CHAUD: 6,
  DEPARTS_FROID: [0.8, 0.35, 1.6],   // Δ de départ (Hz, fondamentale) d'un ajustement à froid
};

// Fenêtre entière (s) pour un battement Δ (Hz) : le plus petit nombre n de battements dont n/Δ dure au moins FEN_MIN_S, borné par FEN_MAX_S.
export function fenetreEntierePour(delta) {
  const d = Math.abs(delta);
  if (!(d > 0)) return ENT.FEN_FROID_S;
  const n = Math.max(1, Math.ceil(ENT.FEN_MIN_S * d - 1e-9));
  const T = n / d;
  return T <= ENT.FEN_MAX_S ? T : Math.min(ENT.FEN_MAX_S, Math.max(1, Math.floor(ENT.FEN_MAX_S * d)) / d);
}

const OMEGA_VIE_S = 300;    // un battement mesuré sert à choisir le partiel de mesure de la même note pendant 5 minutes

export const methodesEntiere = {
  // Le battement Ω̂ (Hz) mesuré la dernière fois que la note `midi` a battu, ou null (plan.js, unisonHarmonic).
  omegaMesureDe(midi) {
    const e = this.omegaMesure?.get(midi);
    return e && this.samplesTotal / this.sr - e.t <= OMEGA_VIE_S ? e.hz : null;
  },

  // Retient Ω̂ pour la note jouée (appelée avec une valeur à laquelle on se fie : le modèle à deux raies, le certificat, l'enveloppe sûre).
  retenirOmega(hz) {
    if (this.playedMidi == null || !(hz >= 0.1 && hz <= 14)) return;
    (this.omegaMesure ?? (this.omegaMesure = new Map())).set(this.playedMidi, { hz, t: this.samplesTotal / this.sr });
  },

  // Appelée par tick() après octaveFuse, avant uniteUnisson et la stabilisation : pour chaque unisson de deux anches que la FFT ne sépare
  // pas, pose les fréquences des deux anches lues par le modèle à deux raies sur une fenêtre entière de battements.
  lireUnissonMesure(groups, calib, tNow) {
    const etats = this.entState ?? (this.entState = new Map());
    for (const g of groups) {
      if (g.isHarmonic || g.isSub || g.isPartial || g.voices.length !== 2 || !(g.W > 0)) continue;
      const tr = this.trackers.get(g.key);
      if (!tr) continue;
      const [v0, v1] = [...g.voices].sort((a, b) => a.target - b.target);
      const k = g.kTrack || 1;
      const resHz = (PROCHES_CASES * g.srd) / (g.W * k);          // fondamentale : au-dessus, la FFT sépare les deux raies
      const propre = (v) => v.tracked && !v.held && !v.coarse && !v.merged && Number.isFinite(v.fMeas);
      const on = [v0, v1].filter(propre);
      const fft = on.length === 2 && Math.abs(v1.fMeas - v0.fMeas) >= resHz;
      let st = etats.get(g.key);
      if (!st || tNow - st.vu > 0.6) { st = { vu: tNow, actif: false, ok: 0, last: null, tFroid: -1e9, prec: null }; etats.set(g.key, st); }
      st.vu = tNow;
      if (fft && !st.actif) { st.ok = 0; st.prec = null; continue; }   // résolues par la FFT : la voie normale
      // Une FFT qui sépare franchement ce que le modèle lisait (au-delà de la résolution) rend la main.
      const avail = Math.min(tr.count - tr.start, 2048) / tr.srd;
      if (avail < ENT.FEN_ABS_MIN_S) continue;
      if (st.actif && st.last && tNow - st.last.t < ENT.PAS_CHAUD_S - 1e-6) { this.poserDeuxRaies(g, v0, v1, st.last, k); continue; }
      const centre = on.length ? on.reduce((s, v) => s + v.fMeas, 0) / on.length : null;     // Hz, fondamentale
      const froid = !(st.last && tNow - st.last.t <= ENT.TENUE_S + 0.2);
      if (froid && tNow - st.tFroid < ENT.PAS_FROID_S) continue;
      const res = this.ajusterDeuxRaies(tr, g, k, avail, calib, centre, froid ? null : st.last);
      if (res && !this.raiesExpliquees(this.azImage?.get(g.key), res)) res.r = Infinity;     // la FFT voit une raie que le modèle ne loge pas
      if (froid) st.tFroid = tNow;
      const borne = resHz * 1.25;
      let bon = null;
      if (res && res.r <= ENT.R_MAX && res.amplitudes.min / res.amplitudes.max >= ENT.AMP_MIN && res.r <= ENT.R_REL * res.energieFaible
          && res.delta >= ENT.OMEGA_MIN && res.delta <= borne) bon = res;
      if (bon) {
        const p = st.prec;
        const accord = p && Math.abs(bon.delta - p.delta) <= ENT.ACCORD * p.delta && Math.abs(centsBetween(bon.milieu, p.milieu)) <= ENT.ACCORD_C;
        st.ok = accord || st.actif ? st.ok + 1 : 1;
        st.prec = bon;
        if (st.ok >= ENT.ENTREE || st.actif) {
          // La prise de main change la grandeur lue (la fréquence de la somme devient celle de chaque anche) : les valeurs d'avant, médianes de
          // la stabilisation et historique du battement affiché, ne sont plus celles de maintenant (comme une voix qui cesse d'être confondue).
          if (!st.actif) { this.beatFus?.delete(g.key); for (const v of g.voices) this.stab?.delete(`${g.key}:${v.def.id}`); st.tPrise = tNow; }
          st.actif = true; st.last = { ...bon, t: tNow, depuis: st.tPrise };
        }
      } else {
        st.ok = 0; st.prec = null;
        if (!(st.last && tNow - st.last.t <= ENT.TENUE_S)) { st.actif = false; st.last = null; }
      }
      if (!st.actif || !st.last) continue;
      this.poserDeuxRaies(g, v0, v1, st.last, k);
      this.retenirOmega(st.last.delta);
    }
  },

  // Pose les deux anches lues par le modèle à deux raies (L : le dernier ajustement retenu).
  poserDeuxRaies(g, v0, v1, L, k) {
    for (const [v, f, a, i] of [[v0, L.f0, L.amplitudes.bas, 0], [v1, L.f1, L.amplitudes.haut, 1]]) {
      v.fMeas = f;
      v.amp = a;
      v.tracked = true; v.held = false; v.coarse = false; v.merged = false;
      v.dCents = centsBetween(f, v.nominal);
      v.dHz = f - v.nominal;
      v.dTargetCents = centsBetween(f, v.target);
      v.source = 'modele2';
      v.sigmaCents = L.sigmaCents;
      v.modele2 = { r: L.r, delta: L.delta, fenetreS: L.T, n: L.n, entiere: L.entiere, k, rang: i, depuis: L.depuis ?? null };
      v.beatMeas = null;
    }
    const base = g.voices.find((v) => v.def.beatSign === 0) ?? g.voices[0];
    for (const v of g.voices) v.beatMeas = v === base ? 0 : v.fMeas - base.fMeas;
  },

  // Les raies de la FFT (az.components) sont-elles toutes sur l'une des deux raies du modèle (ou trop faibles pour compter) ?
  raiesExpliquees(az, res) {
    if (!az?.components?.length || !(az.W > 0)) return true;
    const mMax = Math.max(...az.components.map((c) => c.mag));
    const bin = az.srd / az.W;
    return az.components.every((c) => c.mag < ENT.RAIE_LIBRE_MIN * mMax || res.bande.some((f) => Math.abs(c.freq - f) <= ENT.RAIE_LIBRE_CASES * bin));
  },

  // Un ajustement à deux raies du traqueur `tr` : fenêtre entière pour le Δ de l'ajustement précédent (`chaud`), sinon FEN_FROID_S et
  // plusieurs Δ de départ. Rend { f0, f1 (Hz, fondamentale, ajustées), delta (Hz, fondamentale), milieu, amplitudes {bas, haut, min, max},
  // r, sigmaCents, T, n, entiere } ou null.
  ajusterDeuxRaies(tr, g, k, avail, calib, centre, chaud) {
    const cible = chaud ? fenetreEntierePour(chaud.delta) : Math.min(ENT.FEN_FROID_S, avail);
    const T = Math.min(cible, avail - 0.02);
    if (T < ENT.FEN_ABS_MIN_S) return null;
    const N = Math.round(T * tr.srd);
    const bb = tr.baseband(N);
    if (!bb || bb.re.length < N) return null;
    const off0 = centre != null ? (centre * k) / calib - bb.fc : 0;      // décalage de la raie moyenne dans la bande
    let meilleur = null;
    const departs = chaud ? [[chaud.F, chaud.Dband]] : ENT.DEPARTS_FROID.map((d) => [off0 - (d * k) / 2, d * k]);
    for (const [F0, D0] of departs) {
      const r = ajusterPeigne(bb, F0, D0, [0, 1], [], { N, iter: chaud ? ENT.ITER_CHAUD : ENT.ITER });
      if (r && (!meilleur || r.r < meilleur.r)) meilleur = r;
      if (meilleur && meilleur.r < ENT.R_MAX / 4) break;
    }
    if (!meilleur) return null;
    let { F } = meilleur;
    let D = meilleur.D[0];
    let [a0, a1] = meilleur.lignes.map((l) => l.amp);
    if (D < 0) { F += D; D = -D; [a0, a1] = [a1, a0]; }              // les raies sont rangées par fréquence
    const f0 = (calib * (bb.fc + F)) / k, f1 = (calib * (bb.fc + F + D)) / k;
    // La fenêtre lue est-elle un nombre entier de battements de CET ajustement ? (les deux exponentielles y sont orthogonales : ENT.ENTIERE_TOL de battement)
    const nb = (T * calib * D) / k;
    const entiere = Math.round(nb) >= 1 && Math.abs(nb - Math.round(nb)) <= ENT.ENTIERE_TOL;
    return {
      f0, f1, F, Dband: D, bande: [bb.fc + F, bb.fc + F + D], delta: (calib * D) / k, milieu: (f0 + f1) / 2,
      amplitudes: { bas: a0, haut: a1, min: Math.min(a0, a1), max: Math.max(a0, a1) },
      energieFaible: Math.min(a0, a1) ** 2 / (a0 * a0 + a1 * a1),
      r: meilleur.r, sigmaCents: (1731.2 * (calib * meilleur.sigmaF) / k) / ((f0 + f1) / 2), T, n: N, entiere,
    };
  },
};
