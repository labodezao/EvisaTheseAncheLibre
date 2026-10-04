// Seuils d'auto-entretien de l'anche (terme de Bernard Bonin) et débit de
// fuite — fonctions pures, sans DOM, testées par test/seuils.test.mjs.
// Même logique que research/banc_recherche/seuil.py (la référence) :
//   - l'anche « sonne » si le son est PÉRIODIQUE (clarté NSDF ≥ 0,8) ET
//     au-dessus du fond de souffle (+6 dB) ; un changement d'état ne compte
//     que s'il dure (anti-rebond) ;
//   - sur une rampe montée-descente : p_on (démarrage), p_choke (plaquage :
//     elle se tait alors que la pression monte), p_unchoke (reprise en
//     descente), p_off (extinction) ; plage utile p_choke − p_on.

const finite = (x) => typeof x === 'number' && Number.isFinite(x);

function median(a) {
  if (!a.length) return NaN;
  const s = [...a].sort((x, y) => x - y);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : 0.5 * (s[m - 1] + s[m]);
}

function percentile(a, q) {
  if (!a.length) return NaN;
  const s = [...a].sort((x, y) => x - y);
  const i = (s.length - 1) * q / 100;
  const lo = Math.floor(i), hi = Math.ceil(i);
  return s[lo] + (s[hi] - s[lo]) * (i - lo);
}

// Fond de souffle : médiane du niveau des instants NON périodiques.
export function noiseFloorDb(level, clarity, clarityNoise = 0.5) {
  const sel = [];
  for (let i = 0; i < level.length; i++) {
    if (finite(level[i]) && !(clarity[i] >= clarityNoise)) sel.push(level[i]);
  }
  if (sel.length >= 3) return median(sel);
  return percentile(level.filter(finite), 10);
}

// Anti-rebond : un état qui dure moins que holdS reprend l'état précédent.
export function debounce(state, t, holdS) {
  const out = state.slice();
  if (!state.length || !(holdS > 0)) return out;
  let cur = state[0];
  let i = 0;
  while (i < state.length) {
    let j = i;
    while (j < state.length && state[j] === state[i]) j++;
    const dur = j - 1 > i ? t[j - 1] - t[i] : 0;
    if (state[i] !== cur && dur < holdS) {
      for (let k = i; k < j; k++) out[k] = cur;
    } else {
      cur = state[i];
    }
    i = j;
  }
  return out;
}

export function oscillating(level, clarity, t, opts = {}) {
  const { clarityMin = 0.8, marginDb = 6, holdS = 0.15 } = opts;
  const floor = opts.floorDb ?? noiseFloorDb(level, clarity);
  const raw = level.map((L, i) => finite(L) && clarity[i] >= clarityMin && L >= floor + marginDb);
  return { osc: debounce(raw, t, holdS), floorDb: floor };
}

function smooth(x, n) {
  if (n <= 1 || x.length < n) return x.slice();
  const h = n >> 1, out = new Array(x.length);
  for (let i = 0; i < x.length; i++) {
    let s = 0, c = 0;
    for (let k = i - h; k <= i - h + n - 1; k++) {
      const j = Math.min(x.length - 1, Math.max(0, k));
      s += x[j]; c++;
    }
    out[i] = s / c;
  }
  return out;
}

function interp(x, xs, ys) {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let lo = 0, hi = xs.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
  const f = (x - xs[lo]) / (xs[hi] - xs[lo] || 1);
  return ys[lo] + f * (ys[hi] - ys[lo]);
}

// Seuils d'UNE rampe montée puis descente (t, p, osc de même longueur).
// lagS : retard du capteur de pression (la vraie pression à t est lue à t+lagS).
export function rampThresholds(t, p, osc, { lagS = 0, smoothN = 5 } = {}) {
  const res = {
    p_on: NaN, p_off: NaN, p_choke: NaN, p_unchoke: NaN, p_max: NaN,
    hysteresis: NaN, choke_hysteresis: NaN, usable_range: NaN, ratio: NaN,
    choke_reached: false,
  };
  if (t.length < 3) return res;
  let pc = lagS ? t.map((ti) => interp(ti + lagS, t, p)) : p.slice();
  pc = smooth(pc, smoothN);
  let peak = 0;
  for (let i = 1; i < pc.length; i++) if (pc[i] > pc[peak]) peak = i;
  res.p_max = pc[peak];
  // Montée.
  let iOn = -1;
  if (!osc[0]) {
    for (let i = 1; i <= peak; i++) if (osc[i] && !osc[i - 1]) { iOn = i; break; }
    if (iOn >= 0) res.p_on = pc[iOn];
  } else {
    iOn = 0;                       // sonnait déjà : démarrage sous le bas de la rampe
  }
  if (iOn >= 0) {
    for (let i = iOn + 1; i <= peak; i++) if (!osc[i] && osc[i - 1]) { res.p_choke = pc[i]; break; }
  }
  res.choke_reached = finite(res.p_choke);
  // Descente.
  let lastOff = -1;
  for (let i = peak + 1; i < pc.length; i++) {
    if (res.choke_reached && !finite(res.p_unchoke) && osc[i] && !osc[i - 1]) res.p_unchoke = pc[i];
    if (!osc[i] && osc[i - 1]) lastOff = i;
  }
  if (lastOff >= 0) res.p_off = pc[lastOff];
  res.hysteresis = res.p_on - res.p_off;
  res.choke_hysteresis = res.p_choke - res.p_unchoke;
  const top = res.choke_reached ? res.p_choke : res.p_max;
  if (finite(res.p_on)) {
    res.usable_range = top - res.p_on;
    if (res.p_on > 0) res.ratio = top / res.p_on;
  }
  return res;
}

// Découpe en cycles creux → sommet → creux (zigzag avec seuil minRise en Pa).
export function splitCycles(p, { minRise = 20, smoothN = 9 } = {}) {
  const ps = smooth(p, smoothN);
  const n = ps.length;
  if (n < 3) return [];
  const piv = [];
  let trend = 0, lo = 0, hi = 0, cand = 0;
  for (let i = 1; i < n; i++) {
    if (trend === 0) {
      if (ps[i] < ps[lo]) lo = i;
      if (ps[i] > ps[hi]) hi = i;
      if (ps[i] - ps[lo] >= minRise) { piv.push([lo, 'min']); trend = 1; cand = i; }
      else if (ps[hi] - ps[i] >= minRise) { piv.push([hi, 'max']); trend = -1; cand = i; }
    } else if (trend === 1) {
      if (ps[i] > ps[cand]) cand = i;
      else if (ps[cand] - ps[i] >= minRise) { piv.push([cand, 'max']); trend = -1; cand = i; }
    } else {
      if (ps[i] < ps[cand]) cand = i;
      else if (ps[i] - ps[cand] >= minRise) { piv.push([cand, 'min']); trend = 1; cand = i; }
    }
  }
  if (trend !== 0) piv.push([cand, trend === 1 ? 'max' : 'min']);
  const cycles = [];
  for (let k = 1; k < piv.length; k++) {
    if (piv[k][1] !== 'max' || piv[k - 1][1] !== 'min') continue;
    const a = piv[k - 1][0];
    const b = k + 1 < piv.length ? piv[k + 1][0] : n - 1;
    if (b > a + 2) cycles.push([a, b + 1]);
  }
  return cycles;
}

const KEYS = ['p_on', 'p_off', 'p_choke', 'p_unchoke', 'hysteresis', 'usable_range', 'ratio'];

function meanStd(v) {
  const f = v.filter(finite);
  if (!f.length) return [NaN, NaN];
  const m = f.reduce((s, x) => s + x, 0) / f.length;
  if (f.length < 2) return [m, NaN];
  return [m, Math.sqrt(f.reduce((s, x) => s + (x - m) ** 2, 0) / f.length)];
}

// Analyse complète d'un enregistrement : rows = [{t, p, q, level, clarity}].
export function analyseRun(rows, opts = {}) {
  const t = rows.map((r) => r.t), p = rows.map((r) => r.p);
  const level = rows.map((r) => r.level), clarity = rows.map((r) => r.clarity ?? 0);
  const { osc, floorDb } = oscillating(level, clarity, t, opts);
  const cycles = splitCycles(p, opts).map(([a, b]) =>
    rampThresholds(t.slice(a, b), p.slice(a, b), osc.slice(a, b), opts));
  const mean = {}, std = {};
  for (const k of KEYS) [mean[k], std[k]] = meanStd(cycles.map((c) => c[k]));
  const pq = rows.map((r, i) => [r.p, r.q, osc[i]]).filter(([pp, qq, o]) => o && pp > 0 && qq > 0);
  const flow = powerLaw(pq.map((x) => x[0]), pq.map((x) => x[1]));
  return { osc, floorDb, cycles, mean, std, flow };
}

// q = c · p^n par moindres carrés en log-log. n ≈ 0,5 : orifice (Bernoulli) ;
// n ≈ 1 : écoulement visqueux (pores, fente longue).
export function powerLaw(p, q) {
  let n = 0, sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (let i = 0; i < p.length; i++) {
    if (!(p[i] > 0 && q[i] > 0)) continue;
    const x = Math.log(p[i]), y = Math.log(q[i]);
    n++; sx += x; sy += y; sxx += x * x; sxy += x * y;
  }
  if (n < 3) return { c: NaN, n: NaN };
  const den = n * sxx - sx * sx;
  if (!den) return { c: NaN, n: NaN };
  const slope = (n * sxy - sx * sy) / den;
  return { c: Math.exp((sy - slope * sx) / n), n: slope };
}

// ---- Fuites -----------------------------------------------------------------
const P_ATM = 101325, RHO = 1.2;

// Diamètre (mm) du trou rond qui fuirait qLpm sous pPa (Cd = 0,6).
export function equivalentHoleMm(qLpm, pPa, cd = 0.6) {
  const v = Math.sqrt(2 * Math.max(pPa, 0) / RHO);
  if (!(v > 0)) return NaN;
  const area = qLpm / 60000 / (cd * v);
  return 2 * Math.sqrt(area / Math.PI) * 1e3;
}

// Débit de fuite le long d'une chute de pression d'un volume fermé (L) :
// q = V/p_atm · |dp/dt|, puis loi q = c·p^n et débit à pRef.
// rows : [[t_ms, p_Pa, …], …] (trames « A » du firmware).
export function leakFlow(rows, volumeL, pRef = 500, pMin = 20) {
  const t = rows.map((r) => r[0] / 1000), p = smooth(rows.map((r) => r[1]), 5);
  const V = volumeL / 1000;
  const P = [], Q = [];
  for (let i = 1; i < t.length - 1; i++) {
    const dt = t[i + 1] - t[i - 1];
    if (!(dt > 0)) continue;
    const q = V / P_ATM * (-(p[i + 1] - p[i - 1]) / dt) * 60000;
    if (p[i] > pMin && q > 0) { P.push(p[i]); Q.push(q); }
  }
  const law = powerLaw(P, Q);
  const qRef = law.c * pRef ** law.n;
  return { ...law, qRef, pRef, holeMm: equivalentHoleMm(qRef, pRef), points: P.length };
}
