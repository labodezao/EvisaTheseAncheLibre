// Stabilité de la mesure : sortie stabilisée de chaque anche (stabilize),
// marches de hauteur (detectStep), inversion du soufflet sans silence
// (watchReversal), temps de réponse à l'attaque (measureAttack). Sorti
// d'engine.js (v28) sans rien changer : les méthodes sont posées sur
// Engine.prototype par engine.js (Object.assign), `this` reste le moteur.

import { centsBetween } from '../music.js';

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

const STEP_MAX_CENTS = 40;
const STEP_QW = 16;

// Sortie stabilisée (cf. stabilize) : une anche qui perd la mesure garde sa
// dernière valeur jusqu'à STAB_HOLD_S.
const STAB_HOLD_S = 1.0;

// Sens du soufflet (audit du 10/10/2026, docs/AUDIT-REPETABILITE.md : « le
// premier manque »). Le tiré et le poussé d'une touche sont deux anches,
// accordées à quelques cents l'une de l'autre : deux paliers d'une même note
// ne se comparent qu'à sens connu. Le son ne dit pas le sens ; il dit quand
// il CHANGE : à l'inversion, la pression passe par zéro, le son plonge net
// (creux, watchReversal) ou s'éteint un instant. Le moteur part du sens de la
// grille (cfg.sens, donné par l'interface) et bascule à chaque inversion.
// Un silence de plus de SENS_SILENCE_S n'est plus une inversion : le
// musicien s'est arrêté, il reprend dans le sens qu'il veut (mesuré, session
// d'Ewen du 25/09 : les silences entre deux paliers alternés durent 0,09 à
// 1,2 s ; après 9,9 s, le Fa#3 reprend sur la même anche). Le sens redevient
// alors celui de la grille.
export const SENS_SILENCE_S = 1.5;
export const autreSens = (s) => (s === 'tiré' ? 'poussé' : s === 'poussé' ? 'tiré' : null); // donnée

// Méthodes d'Engine (cf. engine.js, Object.assign).
export const methodesStabilite = {
  // Sens de la grille (cfg.sens), ou null.
  sensGrille() {
    return this.cfg.sens === 'tiré' || this.cfg.sens === 'poussé' ? this.cfg.sens : null; // donnée
  },

  // Le sens repart de celui de la grille (constructeur, silence long, « non »
  // à « poussé ? » : cfg.sensN).
  sensDeLaGrille(tNow) {
    const s = this.sensGrille();
    this.souffletEtat = { sens: s, source: s ? 'grille' : null, inversions: this.souffletEtat?.inversions ?? 0,
      depuis: tNow, silenceS: null, grille: s, grilleT: tNow };
  },

  // La grille change de sens (cfg.sens). En silence, ou si le moteur n'en
  // avait aucun, il la prend. Pendant que le son tient, elle vaut pour la
  // PROCHAINE inversion : la séquence passe au poussé quand le tiré est
  // validé, avant que le luthier n'inverse le soufflet ; prise tout de suite,
  // l'inversion qui suit l'aurait remise au tiré.
  grilleChange(tNow) {
    const e = this.souffletEtat;
    const s = this.sensGrille();
    if (this.lastQuiet !== false || e.sens == null || s == null) { this.sensDeLaGrille(tNow); return; }
    this.souffletEtat = { ...e, grille: s, grilleT: tNow };
  },

  // Une inversion vue (`source` : 'creux' ou 'silence') : le sens bascule.
  basculerSens(source, tNow, silenceS = null) {
    const e = this.souffletEtat;
    this.souffletEtat = { ...e, sens: autreSens(e.sens), source, inversions: e.inversions + 1, depuis: tNow, silenceS };
  },

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
  },

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
          // Une voix qui cesse d'être confondue avec l'octave (cf. octaveFuse)
          // change de grandeur : ses valeurs d'avant étaient la raie commune.
          if (!st || v.step || v.held || (st.merged && !v.merged)) st = { recent: [] };
          if (!v.held) {
            st.recent.push(v.fMeas);
            if (st.recent.length > 3) st.recent.shift();
          }
          const sorted = [...st.recent].sort((a, b) => a - b);
          if (sorted.length) v.fMeas = sorted[sorted.length >> 1];
          st.f = v.fMeas; st.t = tNow; st.amp = v.amp; st.merged = !!v.merged;
          this.stab.set(key, st);
        } else if (!v.tracked && !v.absent && st?.f != null && tNow - st.t < STAB_HOLD_S
            // …sauf si une autre voix du groupe mesure déjà cette hauteur :
            // l'anche a changé d'emplacement (auto-anches), la « tenir » ici
            // l'afficherait deux fois (mesuré : un trémolo La♯3 lu à 3 anches).
            && !g.voices.some((o) => o !== v && o.tracked && !o.held
              && Math.abs(centsBetween(o.fMeas, st.f)) < 3)) {
          v.fMeas = st.f;
          v.amp = st.amp;
          v.tracked = true;
          v.held = true;
          v.merged = !!st.merged;   // une valeur confondue tenue reste dite confondue
        } else {
          continue;
        }
        v.dCents = centsBetween(v.fMeas, v.nominal);
        v.dHz = v.fMeas - v.nominal;
        v.dTargetCents = centsBetween(v.fMeas, v.target);
      }
    }
  },

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
    // Inversion du soufflet sans silence : TOUTES les anches de la note
    // changent (poussé → tiré), pas seulement celle qui l'a vu. Les autres
    // traqueurs repartent aussi, et oublient leur mémoire. Mesuré (session
    // d'Ewen, 16'+8' sur Fa4 + Fa5) : le 8', trop près du partiel 2 du 16'
    // pour voir sa propre marche, affichait encore 1,3 s l'anche du poussé
    // (+2 ¢) quand celle du tiré (+22 ¢) sonnait.
    for (const [k2, t2] of this.trackers) if (t2 !== t) t2.restart(STEP_KEEP);
    if (this.prevF) {
      for (const k2 of [...this.prevF.keys()]) if (!k2.startsWith(`${key}:`)) this.prevF.delete(k2);
    }
    if (this.stab) {
      for (const k2 of [...this.stab.keys()]) if (!k2.startsWith(`${key}:`)) this.stab.delete(k2);
    }
    if (this.prevF) this.prevF.set(`${key}:${v.def.id}`, fq);
    if (this.cfg.mode === 'auto') this.lastFine = { t: this.samplesTotal / this.sr, f: fq };
  },

  // Inversion du soufflet SANS silence : le son ne passe pas sous le seuil,
  // mais il plonge net — 13 à 22 dB en 50 à 100 ms, pendant 0,1 à 0,2 s
  // (mesuré, session d'Ewen, Ré6 et Si5 joués sur une anche : le poussé à
  // +3,5 ¢, le tiré à +24 ¢). L'anche qui parle ensuite n'est plus la même ;
  // sans rien voir, Auto-anches gardait l'ancienne à l'écran à côté de la
  // nouvelle — « deux anches » pour une seule. On traite ce creux comme un
  // silence (cf. tick : reprise). Pas pour un trémolo : ses creux reviennent
  // à chaque battement (on ignore un creux si un autre a eu lieu dans les
  // 1,5 s), et ceux d'un battement lent (< 0,7 Hz) descendent trop lentement.
  // Suivi par bloc reçu (512 échantillons, ~11 ms, en général).
  watchReversal(rms, tNow, n = 512) {
    const db = 20 * Math.log10(rms + 1e-12);
    const w = this.rev ?? (this.rev = { ref: null, fallT: null, dipT: null, lastDip: -1e9 });
    // (Le creux peut passer un instant sous le seuil — mesuré, Ré6 : un bloc
    // de 11 ms à −80 dB. On le suit quand même ; un vrai silence, lui, dure
    // et remet la référence à zéro — cf. plus bas, 0,6 s.)
    if (w.ref == null) { w.ref = db; return; }
    if (w.dipT == null) {
      if (db > w.ref - 3) w.fallT = tNow;                 // encore au niveau : départ de la chute
      if (db < w.ref - 10) {
        w.dipT = tNow;
        w.steep = w.fallT != null && tNow - w.fallT <= 0.12;
      } else {
        const a = Math.min(1, (n / this.sr) / 0.5);       // référence lente (~0,5 s)
        w.ref += a * (db - w.ref);
      }
      return;
    }
    // Dans le creux : on attend la remontée.
    if (db >= w.ref - 4) {
      const dur = tNow - w.dipT;
      const isolated = tNow - w.lastDip >= 1.5;
      // (Pas de test « plusieurs anches » ici : juste avant l'inversion, la
      // fenêtre de Matrix Pencil voit l'anche du poussé ET celle du tiré.)
      if (w.steep && dur >= 0.02 && dur <= 0.4 && isolated) {
        this.reversal = true;
        this.reversalDipT = w.dipT;   // début du creux (sens du soufflet : un silence dedans l'a déjà compté)
      }
      w.lastDip = tNow;
      w.dipT = null; w.fallT = tNow;
    } else if (tNow - w.dipT > 0.6) {
      w.ref = db; w.dipT = null; w.fallT = null;          // pas un creux : le son a baissé pour de bon
    }
  },
};
