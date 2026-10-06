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

// Méthodes d'Engine (cf. engine.js, Object.assign).
export const methodesBattement = {
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
    const pair = base.voices.find((v) => v.tracked && v.beatMeas != null && Math.abs(v.beatMeas) > 0.01);
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
    if (pair) {
      out = { ...(out ?? {}), pairHz: Math.abs(pair.beatMeas) };
      if (out.hz == null) { out.hz = out.pairHz; out.kind = 'anches'; out.sure = true; }
    }
    return out;
  },
};
