import { INTERVALLES, battementIntervalle, centsBetween } from '../music.js';

// Battement et forme de la sortie du moteur : battement du trémolo
// (measureBeat), mesures par partiel pour le stroboscope (withPartials),
// spectre en échelle log pour l'affichage (logResample).
// Sorti d'engine.js (v28) sans rien changer : les méthodes sont posées sur
// Engine.prototype par engine.js (Object.assign), `this` reste le moteur.

// Joint à chaque groupe visible les mesures par partiel de ses anches, pour
// le stroboscope : `partials[k][id]` = fréquence mesurée du partiel k de
// l'anche `id` (Hz), ou absente si pas (encore) résolue. Le partiel sur lequel
// le groupe est lui-même mesuré (kTrack) y figure aussi : c'est la même
// mesure, ramenée au partiel.
// `partialAmps[k][id]` : amplitude de ce partiel (même échelle pour tous) —
// le stroboscope s'en sert pour doser chaque partiel dans le motif.
export function withPartials(groups) {
  const byBase = new Map();
  const ampsByBase = new Map();
  for (const g of groups) {
    if (!g.isPartial) continue;
    const m = byBase.get(g.baseKey) ?? {};
    const a = ampsByBase.get(g.baseKey) ?? {};
    m[g.kTrack] = {};
    a[g.kTrack] = {};
    for (const v of g.voices) {
      if (!v.tracked) continue;
      m[g.kTrack][v.def.id] = v.fMeas;
      a[g.kTrack][v.def.id] = v.amp;
    }
    byBase.set(g.baseKey, m);
    ampsByBase.set(g.baseKey, a);
  }
  return groups.filter((g) => !g.hidden).map((g) => {
    if (g.isHarmonic || g.isSub) return g;
    const partials = { ...(byBase.get(g.key) ?? {}) };
    const partialAmps = { ...(ampsByBase.get(g.key) ?? {}) };
    const k = g.kTrack || 1;
    partials[k] = {};
    partialAmps[k] = {};
    for (const v of g.voices) {
      if (!v.tracked) continue;
      partials[k][v.def.id] = v.fMeas * k;
      partialAmps[k][v.def.id] = v.amp;
    }
    return { ...g, partials, partialAmps };
  });
}

// Rééchantillonnage log-fréquence du spectre large bande pour l'affichage.
export function logResample(mag, binHz, nOut, fLo = 20, fHi = 10000) {
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

// Battement affiché d'un unisson (v56 ; session d'Ewen du 11/10/2026, MM, 25 notes tenues de
// 5 à 7 s : « impossible d'avoir une valeur stable avec les battements »).
//
// L'écart des deux fréquences mesurées (beatMeas = f(8'+) − f(8')) n'est pas une grandeur
// stable : deux anches voisines se tirent l'une l'autre (leur phase et leur volume oscillent
// au rythme du battement), chaque anche devient un PEIGNE de raies à ±Δ, ±2Δ…, et la raie la
// plus forte, ou la pente de phase de l'amas, n'est plus la porteuse. Mesuré : l'écart lu
// sautait de 0,8 à 3 Hz pendant 1,6 s sur un battement de 0,8 Hz (Fa#4), 2,1 Hz affichés
// pour 1,4 Hz (Ré5), et la fenêtre, courte tant que la note est jeune (0,7 s à 2,7 s), ne
// sépare pas deux raies à moins de 1/T. L'enveloppe du volume, elle, bat exactement au rythme
// du peigne (ce que l'oreille entend) : écart-type de 0,01 à 0,05 Hz sur les mêmes notes.
//   - l'enveloppe (measureBeat, `env`) fait le battement dès qu'elle est sûre (deux partiels
//     d'accord, au moins FUS_ENV_MIN_HZ : en dessous, la fenêtre de 8 s ne voit pas deux
//     périodes) ; elle est tenue FUS_HOLD_S quand elle disparaît ;
//   - une enveloppe qui n'est que « modulation » ou « pas sûre » (partiels qui ne s'accordent
//     pas) ne remplace l'écart mesuré que s'il s'en écarte de plus de FUS_DESACCORD (40 %) : elle
//     ne sert alors qu'à écarter une paire de raies prise à côté ;
//   - sans elle (note jeune, battement trop lent, trois anches), la MÉDIANE de l'écart mesuré
//     sur FUS_PAIR_S : une image folle ne passe plus ;
//   - la valeur sort d'un dernier filtre médian sur FUS_OUT_S, pour que le changement de
//     source ne fasse pas sauter le chiffre.
// L'écart brut reste dans `beatBrut` ; `beatSource` dit d'où vient le chiffre.
export const FUS_PAIR_S = 1.0;       // médiane de l'écart mesuré
export const FUS_ENV_MIN_HZ = 0.3;   // en dessous, l'enveloppe ne fait pas deux périodes en 8 s
export const FUS_ENV_CONF = 0.4;     // confiance (autocorrélation) minimale de l'enveloppe (celle de measureBeat)
export const FUS_ENV_N = 5;          // médiane des dernières valeurs de l'enveloppe
export const FUS_DESACCORD = 0.4;    // écart relatif écart mesuré / enveloppe qui fait choisir l'enveloppe
export const FUS_HOLD_S = 1.0;       // l'enveloppe disparue est tenue ce temps
export const FUS_OUT_S = 0.7;        // dernier filtre médian

// Cohérence des hauteurs avec le battement (v57 ; « il faut vérifier qu'on a bien une mesure précise des fréquences des
// 2 anches et que ça colle »). f(8'+) − f(8') DOIT valoir le battement de l'enveloppe (celui qu'on entend). Quand deux
// anches se tirent, leur spectre est un peigne de raies à ±Δ, ±2Δ : le moteur prend parfois la raie de rang n±1 pour
// une anche (Fa#4 de la session d'Ewen, 23,5 à 25,3 s : le 8'+ à +12 ¢ pendant 1,8 s alors que l'écart lu valait 3 Hz
// pour 0,8 Hz vrai). Mesuré sur synthèse : 7 à 29 ¢ d'erreur sur l'anche prise à côté dès que le battement dépasse
// 1,5 Hz sur une note grave, 0,5 à 4 ¢ de biais quand les deux se tirent fort.
//   - une paire COHÉRENTE (écart à ±COH_TOL du battement) n'est jamais touchée : deux anches nettes gardent leur lecture ;
//   - une paire incohérente, alors que la dernière paire cohérente date de moins de COH_REF_S : celle des deux anches qui
//     reste près de sa dernière valeur (COH_SUIVI battement + COH_ABS_HZ) est la bonne raie, l'autre est replacée à un
//     battement d'elle ; si les deux restent près de la leur, l'écart est rétabli au prorata de ce dont chacune a bougé (replacer
//     autour du milieu ajoutait 0,3 ¢ à deux anches nettes dont une raie étrangère fuyait) ; si aucune ne suit, la dernière paire cohérente est tenue (la continuité d'une hauteur est une loi physique ; ce qui bouge
//     vraiment bouge ensemble et reste cohérent) ;
//   - la dernière paire cohérente suit l'anche qui suit : une raie forte de passage de 5 s est ignorée tout du long ;
//   - sans paire de référence (début de note), rien n'est changé.
export const COH_TOL = 0.1;       // écart relatif de f2 − f1 au battement qui rend la paire incohérente
export const COH_ABS_HZ = 0.02;   // …plus ce plancher (Hz)
export const COH_REF_S = 1.5;     // âge maximal de la dernière paire cohérente
export const COH_SUIVI = 0.45;    // une anche « suit » sa dernière valeur à ce nombre de battements près
export const COH_SUIVI_HZ = 0.15; // …plus ce plancher (Hz)

// Fenêtre de moyenne : un nombre ENTIER de périodes de battement (v58, audit du 11/10/2026). Sur une période entière la modulation
// de phase de chaque anche (leur tirage mutuel) se moyenne à zéro : la moyenne est « la fréquence de l'anche en place », ce
// que le luthier accorde. Au moins 1 s (de quoi lire), au plus FEN_MAX_S.
export const FEN_MAX_S = 6;
export function fenetreEntiere(delta) {
  const d = Math.abs(delta);
  if (!(d > 0)) return 1;
  return Math.min(FEN_MAX_S, Math.max(1, Math.round(d)) / d);
}

const mediane = (a) => { const s = [...a].sort((x, y) => x - y); return s[s.length >> 1]; };

// Méthodes d'Engine (cf. engine.js, Object.assign).
export const methodesBattement = {
  // Voir FUS_* ci-dessus. `env` : le battement de l'enveloppe de measureBeat (ou null).
  // Réécrit `beatMeas` des voix d'un unisson ; `beatBrut` garde l'écart mesuré.
  fuserBattement(groups, env) {
    const tNow = this.samplesTotal / this.sr;
    const etats = this.beatFus ?? (this.beatFus = new Map());
    const premier = groups.find((g) => !g.isHarmonic && !g.isSub);
    for (const g of groups) {
      if (g.isHarmonic || g.isSub || g.voices.length < 2) continue;
      let st = etats.get(g.key);
      if (!st || tNow - st.vu > 0.6) { st = { vu: tNow, brut: new Map(), sortie: new Map(), env: [], envT: -1e9 }; etats.set(g.key, st); }
      st.vu = tNow;
      const base = g.voices.find((v) => v.def.beatSign === 0) ?? g.voices[0];
      const autres = g.voices.filter((v) => v !== base);
      // L'enveloppe d'un battement ne dit une paire que s'il n'y en a qu'une : deux anches.
      if (g === premier && g.voices.length === 2 && env && env.conf >= FUS_ENV_CONF
        && env.hz >= FUS_ENV_MIN_HZ && env.hz <= 14) {
        st.env.push({ hz: env.hz, sure: env.kind === 'anches' && !!env.sure });
        if (st.env.length > FUS_ENV_N) st.env.shift();
        st.envT = tNow;
      }
      const tenue = st.env.length && tNow - st.envT <= FUS_HOLD_S;
      if (!tenue) st.env = [];
      const envHz = tenue ? mediane(st.env.map((e) => e.hz)) : null;
      const envSure = tenue && st.env[st.env.length - 1].sure;
      if (g === premier && g.voices.length === 2) {
        this.cohererPaire(g, st, tNow, envHz, envSure);
        this.etatPaire?.(g, tNow, envHz, envSure);
      }
      for (const v of autres) {
        const brut = v.beatMeas;
        v.beatBrut = brut ?? null;
        v.beatSource = null;
        const hist = st.brut.get(v.def.id) ?? [];
        const sortie = st.sortie.get(v.def.id) ?? [];
        if (brut == null || !base.tracked || !v.tracked) { st.brut.set(v.def.id, hist.filter((h) => tNow - h.t <= FUS_PAIR_S)); continue; }
        hist.push({ t: tNow, v: brut });
        const recent = hist.filter((h) => tNow - h.t <= FUS_PAIR_S);
        st.brut.set(v.def.id, recent);
        const signe = v.def.beatSign ? Math.sign(v.def.beatSign) : Math.sign(brut) || 1;
        const ecart = mediane(recent.map((h) => h.v));
        let val = ecart, src = 'ecart';
        if (envHz != null && (envSure || Math.abs(Math.abs(ecart) - envHz) > FUS_DESACCORD * envHz)) {
          val = signe * envHz; src = 'enveloppe';
        }
        sortie.push({ t: tNow, v: val });
        const rec = sortie.filter((h) => tNow - h.t <= FUS_OUT_S);
        st.sortie.set(v.def.id, rec);
        v.beatMeas = mediane(rec.map((h) => h.v));
        v.beatSource = src;
      }
    }
  },

  // Voir COH_* ci-dessus. Hauteurs des deux anches d'un unisson ramenées à l'écart de l'enveloppe quand le moteur a pris
  // une raie du peigne à côté. `st` : l'état du groupe (fuserBattement).
  cohererPaire(g, st, tNow, envHz, envSure) {
    const [v0, v1] = [...g.voices].sort((a, b) => a.target - b.target);
    const etats = this.cohEtat ?? (this.cohEtat = new Map());
    // Par note : la paire de la note d'avant n'est pas celle-ci (g.key ne dit que l'octave) ; et un silence de plus de COH_REF_S repart de zéro.
    const cle = `${g.key}:${g.center}`;
    let c = etats.get(cle);
    if (!c || tNow - c.vu > COH_REF_S) { c = { vu: tNow, t0: tNow, ref: null, hz: null, hzT: -1e9, hist: [] }; etats.set(cle, c); }
    c.vu = tNow;
    if (v0.step || v1.step) c.ref = null;       // une vraie marche (detectStep) : l'avant ne sert plus
    // Le battement vaut ce que dit l'enveloppe sûre ; une enveloppe « modulation » ne vaut que si l'écart mesuré sur 1 s
    // s'en approche (une secousse du soufflet n'est pas un battement). Perdue un instant, la dernière valeur sûre sert.
    const brut = st.brut.get(v1.def.id) ?? [];
    const ecartMed = brut.length ? mediane(brut.map((h) => Math.abs(h.v))) : null;
    if (envHz != null && (envSure || (ecartMed != null && Math.abs(ecartMed - envHz) <= FUS_DESACCORD * envHz))) { c.hz = envHz; c.hzT = tNow; }
    const ok = (v) => v.tracked && !v.held && !v.coarse && !v.merged && Number.isFinite(v.fMeas);
    // Les images lues depuis 3 s : l'enveloppe ne donne le battement qu'après 2,5 s de note ; la paire cohérente d'avant
    // (qui sert de référence) se retrouve dans cet historique.
    if (ok(v0) && ok(v1)) { c.hist.push({ t: tNow, f0: v0.fMeas, f1: v1.fMeas }); while (c.hist[0].t < tNow - 3) c.hist.shift(); }
    const hz = c.hz != null && tNow - c.hzT <= COH_REF_S ? c.hz : null;
    // Le peigne rigide (peigne.js) lit les deux anches d'un coup quand elles se tirent ; sinon la lecture d'avant, corrigée ci-dessous.
    if (this.appliquerPeigne?.(g, v0, v1, tNow, envHz, envSure, c, ok)) return;
    for (const v of [v0, v1]) if (v.tracked) { v.source = 'amas'; v.sigmaCents = null; v.peigne = null; }
    if (hz == null) return;
    if (!c.ref || tNow - c.ref.t > COH_REF_S) {
      for (let i = c.hist.length - 1; i >= 0; i--) {
        const h = c.hist[i];
        if (tNow - h.t > COH_REF_S) break;
        if (Math.abs(h.f1 - h.f0 - hz) <= COH_TOL * hz + COH_ABS_HZ) { c.ref = { t: h.t, f0: h.f0, f1: h.f1 }; break; }
      }
    }
    if (!ok(v0) || !ok(v1)) {
      // Une anche perdue une image n'efface pas la dernière paire cohérente. Et la seule qui reste, si elle est à
      // plus d'un demi-battement de sa dernière valeur, est une raie du peigne prise pour elle (Fa#4, 23,55 s : le 8'+
      // à +10,7 ¢ pendant que le 8' manquait) : sa dernière valeur est tenue.
      const un = ok(v0) ? v0 : ok(v1) ? v1 : null;
      const r = c.ref;
      if (un && r && tNow - r.t <= COH_REF_S && Math.abs(un.fMeas - (un === v0 ? r.f0 : r.f1)) > COH_SUIVI * hz + COH_SUIVI_HZ) {
        un.fMeas = un === v0 ? r.f0 : r.f1;
        un.dCents = centsBetween(un.fMeas, un.nominal);
        un.dHz = un.fMeas - un.nominal;
        un.dTargetCents = centsBetween(un.fMeas, un.target);
        un.held = true;
        un.pairRepaired = true;
      }
      return;
    }
    const sep = v1.fMeas - v0.fMeas, tol = COH_TOL * hz + COH_ABS_HZ;
    if (Math.abs(sep - hz) <= tol) { c.ref = { t: tNow, f0: v0.fMeas, f1: v1.fMeas }; return; }
    const ref = c.ref;
    if (!ref || tNow - ref.t > COH_REF_S) return;
    const suit = COH_SUIVI * hz + COH_SUIVI_HZ;
    const s0 = Math.abs(v0.fMeas - ref.f0) <= suit, s1 = Math.abs(v1.fMeas - ref.f1) <= suit;
    let f0 = v0.fMeas, f1 = v1.fMeas, tient = false;
    if (s0 && !s1) f1 = f0 + hz;
    else if (s1 && !s0) f0 = f1 - hz;
    else if (s0 && s1) {
      // Les deux restent près de la leur : l'écart manquant (ou en trop) est partagé au prorata de ce dont chacune a bougé
      // depuis la dernière paire cohérente (celle qui n'a pas bougé n'est pas la fausse).
      const e = hz - sep, a0 = Math.abs(f0 - ref.f0) + 0.02, a1 = Math.abs(f1 - ref.f1) + 0.02;
      f0 -= e * a0 / (a0 + a1); f1 += e * a1 / (a0 + a1);
    }
    else { f0 = ref.f0; f1 = ref.f1; tient = true; }
    for (const [v, f] of [[v0, f0], [v1, f1]]) {
      v.fMeas = f;
      v.dCents = centsBetween(f, v.nominal);
      v.dHz = f - v.nominal;
      v.dTargetCents = centsBetween(f, v.target);
      v.pairRepaired = true;
    }
    const base = g.voices.find((v) => v.def.beatSign === 0) ?? g.voices[0];
    for (const v of g.voices) v.beatMeas = v === base ? 0 : v.fMeas - base.fMeas;
    // la référence suit une paire rétablie sur une raie qui a suivi ; elle reste celle d'avant quand on a dû la tenir
    if (!tient) c.ref = { t: tNow, f0, f1 };
  },

  // Battements d'intervalles (audit du 10/10/2026, docs/AUDIT-REPETABILITE.md,
  // étape 5). Pour chaque paire d'anches de la note (registre Q, accord,
  // registres à l'octave) à un intervalle de INTERVALLES (music.js) : le
  // battement de leur partiel commun, b = m f_b − n f_h, MESURÉ par les deux
  // fréquences (précis à quelques mHz : il se lit dès que les deux anches
  // sont mesurées) et VOULU par leurs cibles (tempérament, La, décalages).
  // Vérification : l'enveloppe du traqueur du partiel m de la basse (sa bande
  // contient aussi le partiel n de la haute), qui bat à |b| ; elle ne se lit
  // que si la note dure deux périodes (beatFromEnvelope : 2,5 s au moins,
  // 0,2 Hz demande 10 s). Une anche confondue avec l'octave compte pour son
  // estimation (confondu.js). Les unissons (musette) ont leur propre battement.
  measureIntervals(groups) {
    const voix = [];
    for (const g of groups) {
      if (g.isHarmonic || g.isSub) continue;
      for (const v of g.voices) voix.push({ g, v });
    }
    const out = [];
    for (let i = 0; i < voix.length; i++) {
      for (let j = i + 1; j < voix.length; j++) {
        const [lo, hi] = voix[i].v.nominal <= voix[j].v.nominal ? [voix[i], voix[j]] : [voix[j], voix[i]];
        const s = Math.round(12 * Math.log2(hi.v.nominal / lo.v.nominal));
        const r = INTERVALLES[s];
        if (!r) continue;
        const f = (v) => (!v.tracked || v.coarse ? null : v.confondu && v.fEstimee != null ? v.fEstimee : v.merged ? null : v.fMeas);
        const fb = f(lo.v), fh = f(hi.v);
        let env = null;
        const tr = this.trackers.get(lo.g.kTrack === r.m ? lo.g.key : `${lo.g.key}p${r.m}`);
        if (tr) {
          const b = tr.beatFromEnvelope(1);
          if (b) env = { hz: b.hz, conf: b.conf, depth: b.depth, sure: b.conf >= 0.4 && b.hz <= 14 };
        }
        out.push({
          bas: lo.v.def.id, haut: hi.v.def.id, demiTons: s, m: r.m, n: r.n, nom: r.nom,
          fBas: fb, fHaut: fh,
          mesure: fb != null && fh != null ? battementIntervalle(fb, fh, r.m, r.n) : null,
          voulu: battementIntervalle(lo.v.target, hi.v.target, r.m, r.n),
          partiel: r.m * (fb ?? lo.v.target),
          enveloppe: env,
        });
      }
    }
    return out.length ? out : null;
  },

  // Battement du trémolo, en battements par seconde (× 60 = par minute) —
  // demande d'Ewen : « deux anches en vibrato : combien de fois par minute ça
  // bat ? ». Lu dans l'enveloppe de chaque partiel suivi de la note (cf.
  // ZoomTracker.beatFromEnvelope), puis on tranche :
  //  - deux anches d'écart Δf : le partiel k bat à k·Δf → les rythmes bruts
  //    divisés par leur rang s'accordent ; le battement est Δf ;
  //  - modulation d'ensemble (secousse du soufflet, boucle d'un sample) :
  //    tous les partiels battent au même rythme brut.
  // Mesuré sur un Mi2 Ballone Burini : 1,23 Hz sur le partiel 2 ET sur le
  // partiel 4 → modulation à 1,23 Hz, pas deux anches à 0,62 Hz.
  // En registre (deux anches séparées dans le spectre), l'écart des deux
  // fréquences mesurées est plus précis : on le donne aussi.
  measureBeat(groups) {
    const base = groups.find((g) => !g.isHarmonic && !g.isSub);
    if (!base) return null;
    const raws = [];
    for (const g of groups) {
      if (g.isSub || g.center !== base.center) continue;
      const t = this.trackers.get(g.key);
      const k = g.kTrack || 1;
      if (!t || raws.some((r) => r.k === k)) continue;
      const b = t.beatFromEnvelope(1);
      if (b && b.conf >= 0.4) raws.push({ k, hz: b.hz, conf: b.conf, depth: b.depth });
    }
    let out = null;
    // Décision robuste : pour chaque hypothèse, la médiane des estimations et
    // le nombre de partiels qui s'y accordent à 3 % près. Un partiel dont les
    // deux anches sortent de la bande analysée (k·Δf > 14 Hz) donne n'importe
    // quoi : il ne sera simplement pas « d'accord ».
    const ok = raws.filter((r) => r.hz <= 14);
    if (ok.length) {
      const judge = (vals) => {
        const sorted = [...vals].sort((x, y) => x - y);
        const med = sorted[sorted.length >> 1];
        const agree = vals.filter((v) => Math.abs(v - med) <= 0.03 * med);
        return { hz: agree.reduce((x, y) => x + y, 0) / agree.length, n: agree.length };
      };
      const reeds = judge(ok.map((r) => r.hz / r.k));
      const mod = judge(ok.map((r) => r.hz));
      const pick = mod.n > reeds.n ? { ...mod, kind: 'modulation' } : { ...reeds, kind: 'anches' };
      out = { hz: pick.hz, kind: pick.kind, conf: ok[0].conf, depth: ok[0].depth,
        sure: pick.n >= 2 && (pick.kind === 'anches' ? reeds.n > mod.n : true) };
      out.nPartials = pick.n;
    }
    // L'écart des deux anches est fusionné avec l'enveloppe (fuserBattement) avant d'être lu.
    this.fuserBattement(groups, out);
    const pair = base.voices.find((v) => v.tracked && v.beatMeas != null && Math.abs(v.beatMeas) > 0.01);
    if (pair) {
      out = { ...(out ?? {}), pairHz: Math.abs(pair.beatMeas) };
      if (out.hz == null) { out.hz = out.pairHz; out.kind = 'anches'; out.sure = true; }
    }
    return out;
  },
};
