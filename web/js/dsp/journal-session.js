// Journal de session (lot D4 de l'audit « échelons de justesse », 19/10/2026 ; lot G1 de la v71).
//
// Sans lui, ce que l'écran a dit ne se relit pas : le La changeait entre deux notes (442 puis 440 Hz) et le JSON n'en gardait que le dernier ; le chiffre affiché, son régime
// (instantané, provisoire, certifié, tenu) et la source de la valeur n'étaient écrits nulle part. Ce module ne mesure rien et ne change rien à l'écran : il note, pour
// le CSV (une valeur par anche et par image) et le JSON (listes datées), en secondes de la session (la même horloge que le WAV).
//
// Module pur (sans Worker ni DOM) : worker.js l'appelle, test/session.test.mjs et test/echelons-prise.test.mjs le jouent sous Node.
import { lireTick, nouvelHistorique } from '../ui/mesure.js';

// Les réglages dont un changement déplace la cible ou la lecture (le La, le registre, l'instrument, le tempérament...) : chacun est daté quand il change.
export const REGLAGES_SUIVIS = Object.freeze(['a4', 'register', 'mode', 'temperament', 'transpose', 'calibrationPpm', 'lockNote', 'reedOctaves', 'maxUnison', 'instrument', 'chordType', 'chordDegrees']);
// Au plus (garde-fou de la mémoire d'une session de plusieurs heures).
const MAX_LISTE = 2000;

const arrondi = (x, d = 3) => (Number.isFinite(x) ? Math.round(x * 10 ** d) / 10 ** d : null);
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export class JournalSession {
  constructor() { this.vider(); }

  vider() {
    this.reglages = [];       // [{ t_s, cle, avant, apres }] ; la première entrée (cle « depart ») porte l'état du début
    this.verrou = [];         // [{ t_s, midi, sure, raison, f, centre, demi, omega }] : lectures du verrou de phase (une par note, après sa fin)
    this.histAff = new Map(); // l'historique du chiffre affiché de chaque anche (ui/mesure.js)
    this.sonS = 0;            // secondes de son (hors silence) : le compteur de sauts d'horloge se compte par minute de son
    this.tPrec = null;
  }

  // Début de la session : l'état de départ (valeurs des réglages suivis présents dans le cfg, case du verrou).
  demarrer(cfg, verrouActif) {
    this.vider();
    const depart = { t_s: 0, cle: 'depart', verrou: !!verrouActif };
    for (const k of REGLAGES_SUIVIS) if (cfg?.[k] !== undefined) depart[k] = cfg[k];
    this.reglages.push(depart);
  }

  // Un message `config` du moteur (patch partiel) : ce qui change réellement est daté. `cfgAvant` : le cfg du moteur avant le patch.
  config(patch, cfgAvant, t_s) {
    for (const k of REGLAGES_SUIVIS) {
      if (!(k in (patch ?? {}))) continue;
      if (egal(patch[k], cfgAvant?.[k])) continue;
      this.reglages.push({ t_s: arrondi(t_s), cle: k, avant: cfgAvant?.[k] ?? null, apres: patch[k] ?? null });
    }
    if (this.reglages.length > MAX_LISTE) this.reglages.splice(1, this.reglages.length - MAX_LISTE);
  }

  // La case « Verrou de phase » (réglage de la page) change.
  caseVerrou(on, t_s) {
    const dernier = [...this.reglages].reverse().find((x) => x.cle === 'verrou' || (x.cle === 'depart' && 'verrou' in x));
    const avant = dernier ? (dernier.cle === 'verrou' ? dernier.apres : dernier.verrou) : null;
    if (avant === !!on) return;
    this.reglages.push({ t_s: arrondi(t_s), cle: 'verrou', avant, apres: !!on });
  }

  // Une lecture rendue par le Worker du verrou (verrou-worker.js) : une par note, pour les deux voix, ou son refus (`raison`).
  lectureVerrou(l, t_s, midi = null) {
    if (!l || l.calcul) return;     // « calcul en cours » n'est pas une lecture
    this.verrou.push({ t_s: arrondi(t_s), midi: l.midi ?? midi, sure: !!l.sure, raison: l.raison ?? null,
      f: Array.isArray(l.f) ? l.f.map((x) => arrondi(x, 4)) : null, centre: arrondi(l.centre, 4), demi: arrondi(l.demi, 4), omega: arrondi(l.omega, 4) });
    if (this.verrou.length > MAX_LISTE) this.verrou.shift();
  }

  // Le chiffre que l'écran montrerait pour chaque anche et son régime, tels que ui/mesure.js les donne à cette image : Map « groupe:voix » -> { c, regime }.
  // Le journal ne doit jamais arrêter la mesure.
  affiches(r) {
    const m = new Map();
    if (!r || r.quiet) { this.histAff.clear(); return m; }
    for (const g of r.groups ?? []) {
      if (g.isHarmonic || g.isSub) continue;
      for (const v of g.voices ?? []) {
        let h = this.histAff.get(v.def.id);
        if (!h) this.histAff.set(v.def.id, h = nouvelHistorique());
        try {
          const tk = lireTick(r, { voix: v.def.id, midi: null, sens: null }, { lecture: 'liste' }, h);
          if (tk.affiche) m.set(`${g.key}:${v.def.id}`, { c: tk.affiche.cents, regime: tk.affiche.regime ?? (tk.affiche.certifie ? 'certifie' : 'provisoire') });
        } catch { /* rien */ }
      }
    }
    return m;
  }

  // À chaque image : le temps de son (le compteur de sauts d'horloge se compte par minute de son).
  image(r) {
    if (this.tPrec != null && !r.quiet) this.sonS += Math.max(0, Math.min(1, r.time - this.tPrec));
    this.tPrec = r.time;
  }

  // Les sauts d'horloge de la prise vus par le détecteur (saut-horloge.js), en secondes de la session (`t0` : l'instant du début dans l'horloge du moteur).
  sauts(detecteur, t0 = 0) {
    return (detecteur?.evenements ?? []).slice(-MAX_LISTE).map((e) => ({ t_s: arrondi(e.t - t0), tSaut_s: arrondi(e.tSaut - t0), deltaCents: arrondi(e.deltaCents, 2), lignes: e.lignes }));
  }

  // Le compteur « sauts d'horloge par minute de son » de la prise (seuil d'alerte : 1 par minute), pour `resume` du JSON.
  compteur(detecteur) {
    if (!detecteur) return { sauts_horloge: null, sauts_horloge_par_min: null, alerte_sauts_horloge: false };   // détecteur éteint (cfg.SAUT_HORLOGE) : rien n'a été compté
    const n = detecteur.evenements.length;
    const min = this.sonS / 60;
    const parMin = min >= 0.25 ? arrondi(n / min, 2) : null;
    return { sauts_horloge: n, sauts_horloge_par_min: parMin, alerte_sauts_horloge: parMin != null && parMin >= 1 };
  }

  // Le bloc `journal` du JSON (fusionné avec celui du lot F2 par worker.js).
  json(detecteur, t0 = 0) {
    return { reglages: this.reglages, sauts_horloge: this.sauts(detecteur, t0), verrou: this.verrou };
  }
}
