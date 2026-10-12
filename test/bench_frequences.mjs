// Banc de validation générale des fréquences des anches (v57) : « une mesure précise des
// fréquences des deux anches, et ça colle dans le cas général ».   node test/bench_frequences.mjs [--json]
// Notes de Do2 à Do7, battements de 0,2 à 8 Hz, 2 et 3 anches, rapports d'amplitude, partiels réalistes,
// couplage (raies d'intermodulation à ±Δ, ±2Δ), dérive de pression, vibrato lent, bruit.
// Pour chaque cas : erreur de chaque anche (cents), du battement (Hz), cohérence f2 − f1 contre le battement
// affiché, temps de stabilisation, taux de permutation d'anches.
import { anches, at, cents, rejoue, voix, timbre, hasard, vraie, vraieEntiere } from './synthese-anches.mjs';
import { fenetreEntiere } from '../web/js/dsp/battement.js';

export const med = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[s.length >> 1] : NaN; };
export const pct = (a, p) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : NaN; };

// Un cas : { nom, midi, delta, n (2|3), rapportDb, couple, derive, vib, fv, rsb, secondes, partiels, adler, deltaM, extreme }
//   couple  : { beta (rad au fondamental), am } modulation de phase et de volume au rythme du battement
//   adler   : { kappaSurD, am } deux oscillateurs couplés (dψ/dt = 2πΔ0 − K sin ψ), κ = kappaSurD · Δ0
//   deltaM  : MMM, écart du 8'− au 8' (Δ−) quand il n'est pas égal à celui du 8'+ (Δ+ = delta)
//   extreme : couplage hors du réaliste (β > 0,3 rad ou AM > 15 % : des anches accrochées, audit du 11/10/2026)
export function fabriquer(c) {
  const F = at(c.midi, 0) * 2 ** ((c.decal ?? 0) / 1200);
  const r = hasard(c.graine ?? 11);
  const D = c.delta;
  const n = c.n ?? 2;
  // fréquences vraies : 2 anches : F, F+D ; 3 anches : F−D, F, F+D (8'−, 8', 8'+)
  const fs = n === 2 ? [F, F + D] : [F - (c.deltaM ?? D), F, F + D];
  const rap = 10 ** (-(c.rapportDb ?? 0) / 20);
  const amps = n === 2 ? [1, rap] : [rap, 1, rap];
  const pente = c.pente ?? -3.5;
  const liste = fs.map((f, i) => {
    const o = { f, a: amps[i], H: timbre(c.partiels ?? 12, r, pente, c.trous ?? {}), vib: c.vib ?? 0.1, derive: c.derive ?? 0 };
    if (c.couple) o.tire = { f: D, beta: c.couple.beta, am: c.couple.am ?? 0, ph: i * 1.3 };
    if (c.adler) {
      const kappa = c.adler.kappaSurD * D;
      o.tire = { f: Math.sqrt(D * D - kappa * kappa), am: c.adler.am ?? 0, ph: i * 1.3, signe: i === 0 ? 1 : -1, adler: { kappa, D0: D } };
    }
    return o;
  });
  // une raie sans rapport avec l'unisson (partiel d'une autre note, accompagnement) à `etranger` battements au-dessus
  const synth = c.etranger ? [...liste, { f: fs[fs.length - 1] + c.etranger * D, a: c.etrangerA ?? 0.7, H: timbre(c.partiels ?? 12, r, pente, {}), vib: c.vib ?? 0.1 }] : liste;
  const x = anches(synth, c.secondes ?? 9, { rsb: c.rsb ?? 35, graine: c.graine ?? 7, fv: c.fv ?? 0.6, phi: true });
  // ids dans l'ordre croissant des fréquences : 2 anches 8, 8+ ; 3 anches 8-, 8, 8+
  const ids = n === 2 ? ['8', '8+'] : ['8-', '8', '8+'];
  return { x, liste, ids, cfg: { mode: 'register', register: n === 2 ? 'MM' : 'MMM' } };
}

// Vérité de l'anche j à t, deux définitions :
//  - ENTIÈRE (audit du 11/10/2026, la bonne) : la fréquence moyenne de l'anche EN PLACE sur un nombre entier de périodes de
//    battement qui finit à t (modulation de phase comprise, qui se moyenne à zéro ; `fenetreEntiere`). Le battement est
//    celui que l'on entend : f2 − f1 vrai = Ω (Adler) ou Δ.
//  - ancienne (v57) : la moyenne sur 15 à 85 % de la fenêtre de l'analyse, SANS la modulation de phase : ambiguë de
//    ±β·Δ/(2π·0,7T)·... pour β ≥ 0,5 ; gardée pour la comparaison.
const verite = (x, liste, j, t, T) => vraie(x, liste, j, t, T);
export function battementVrai(c) {
  if (c.adler) return Math.sqrt(c.delta ** 2 - (c.adler.kappaSurD * c.delta) ** 2);
  return c.delta;
}
const entiere = (x, j, t, c) => vraieEntiere(x, j, t, fenetreEntiere(battementVrai(c)));

export function evaluer(c, opts = {}) {
  const { x, liste, ids, cfg } = fabriquer(c);
  const imgs = rejoue(cfg, x);
  const tEt = c.etab ?? Math.min(Math.max(4.5, 2 / c.delta + 1), (c.secondes ?? 9) - 1.5);   // deux périodes de battement + 1 s (le peigne, ou l'enveloppe, n'a la main qu'après)
  const par = ids.map(() => ({ err: [], derr: [], errA: [] }));
  const berr = [], coh = [], bsrc = {}, srcs = {};
  let perm = 0, nPerm = 0, nVu = 0, nImg = 0;
  const serie = ids.map(() => []);
  for (const im of imgs) {
    if (im.t < 1) continue;
    const vs = ids.map((id) => voix(im, id));
    const ok = vs.every((v) => v && v.tracked && v.fMeas != null && !v.coarse);
    nImg++;
    if (!ok) continue;
    nVu++;
    const T = vs[vs.length - 1].regressionPhase?.fenetreS ?? 2.7;
    const vrA = ids.map((_, j) => verite(x, liste, j, im.t, T));
    const vr = ids.map((_, j) => entiere(x, j + (ids.length === 3 ? 0 : 0), im.t, c));
    // permutation : l'anche mesurée est plus proche d'une autre vraie que de la sienne (écarts > 0,3 Hz)
    let p = false;
    vs.forEach((v, j) => {
      const ej = Math.abs(v.fMeas - vr[j]);
      for (let k = 0; k < ids.length; k++) if (k !== j && Math.abs(v.fMeas - vr[k]) < ej) p = true;
    });
    if (im.t > tEt) { nPerm++; if (p) perm++; }
    vs.forEach((v, j) => {
      const e = cents(v.fMeas, vr[j]);
      serie[j].push([im.t, e]);
      if (im.t > tEt) { par[j].err.push(e); par[j].errA.push(cents(v.fMeas, vrA[j])); }
    });
    if (im.t > tEt) {
      const v8p = vs[ids.length - 1], v8 = vs[ids.length - 2];
      const dBrut = v8p.fMeas - v8.fMeas;
      const aff = v8p.beatMeas;
      if (aff == null) continue;
      berr.push(aff - battementVrai(c));
      if (v8p.source) srcs[v8p.source] = (srcs[v8p.source] ?? 0) + 1;
      coh.push(dBrut - aff);
      bsrc[v8p.beatSource ?? '-'] = (bsrc[v8p.beatSource ?? '-'] ?? 0) + 1;
    }
  }
  // temps de stabilisation : dernier instant où |err| > 0,5 c pour au moins une anche, + 0
  let tSt = 0;
  serie.forEach((s) => { for (const [t, e] of s) if (Math.abs(e) > 0.5 && t > tSt) tSt = t; });
  const dernierT = imgs.length ? imgs.at(-1).t : 0;
  return {
    cas: c,
    errMed: par.map((p) => med(p.err.map(Math.abs))),
    errP95: par.map((p) => pct(p.err.map(Math.abs), 0.95)),
    errP95A: par.map((p) => pct(p.errA.map(Math.abs), 0.95)),   // vérité ancienne (v57)
    errMax: par.map((p) => Math.max(...p.err.map(Math.abs), 0)),
    battMed: med(berr.map(Math.abs)), battP95: pct(berr.map(Math.abs), 0.95),
    cohMed: med(coh.map(Math.abs)), cohP95: pct(coh.map(Math.abs), 0.95),
    stab: tSt >= dernierT - 0.6 ? null : tSt,
    perm: nPerm ? perm / nPerm : NaN,
    lu: nPerm ? nVu / Math.max(1, nImg) : 0,
    n: nPerm, bsrc, srcs,
  };
}

export function grille() {
  const cas = [];
  const base = { secondes: 9 };
  // 1. propres : 2 anches, notes x battements
  for (const midi of [36, 48, 60, 72, 84, 96]) for (const delta of [0.2, 0.5, 0.8, 1.5, 3, 5, 8].filter((d) => d / at(midi, 0) < 0.02))
    cas.push({ ...base, nom: 'propre 2', midi, delta, n: 2 });
  // 2. rapports d'amplitude
  for (const midi of [48, 66, 84]) for (const delta of [0.8, 2.5]) for (const rapportDb of [3, 6, 12])
    cas.push({ ...base, nom: `rapport ${rapportDb} dB`, midi, delta, n: 2, rapportDb });
  // 3. T1, couplage RÉALISTE (audit du 11/10/2026) : β ≤ 0,3 rad au fondamental (raie latérale ≤ −16 dB), AM ≤ 15 %. Cible < 0,3 ¢.
  for (const midi of [48, 66, 84]) for (const delta of [0.5, 0.8, 1.5]) for (const beta of [0.1, 0.2, 0.3]) for (const am of [0.05, 0.15])
    cas.push({ ...base, nom: 'couplage réaliste', midi, delta, n: 2, couple: { beta, am } });
  // 3 bis. couplage EXTRÊME (v57 : β 0,5 à 1,2 rad, AM 30 % : des anches accrochées, hors tolérance, gardé pour mémoire)
  for (const midi of [48, 66, 84]) for (const delta of [0.5, 0.8, 1.5, 3]) for (const beta of [0.5, 1.2])
    cas.push({ ...base, nom: 'couplage extrême', midi, delta, n: 2, couple: { beta, am: 0.3 }, extreme: true });
  // 3 ter. T3, deux oscillateurs d'Adler : κ/Δ0 = 0,3, 0,6, 0,9 (le battement observé vaut Ω = Δ0 √(1 − (κ/Δ0)²))
  for (const midi of [48, 66, 84]) for (const delta of [0.8, 1.5]) for (const kappaSurD of [0.3, 0.6, 0.9])
    cas.push({ ...base, nom: 'Adler', midi, delta, n: 2, adler: { kappaSurD, am: 0.1 } });
  // 4. 3 anches
  for (const midi of [48, 66, 84]) for (const delta of [0.5, 0.8, 1.3, 3]) {
    cas.push({ ...base, nom: 'MMM', midi, delta, n: 3 });
    cas.push({ ...base, nom: 'MMM -6 dB', midi, delta, n: 3, rapportDb: 6 });
    cas.push({ ...base, nom: 'MMM couplé extrême', midi, delta, n: 3, couple: { beta: 0.6, am: 0.3 }, extreme: true });
    cas.push({ ...base, nom: 'MMM couplé réaliste', midi, delta, n: 3, couple: { beta: 0.2, am: 0.1 } });
  }
  // 4 ter. T4, MMM asymétrique couplé : Δ− = 0,7 Δ+
  for (const midi of [48, 66, 84]) for (const delta of [0.8, 1.5, 3])
    cas.push({ ...base, nom: 'MMM asymétrique couplé', midi, delta, deltaM: 0.7 * delta, n: 3, couple: { beta: 0.2, am: 0.1 } });
  // 4 bis. T5, une raie étrangère près de l'unisson (partiel d'une autre note, accompagnement)
  for (const midi of [48, 66, 84]) for (const delta of [0.8, 1.5]) for (const etranger of [1.7, 2.7, 3.4]) {
    cas.push({ ...base, nom: `raie étrangère à ${etranger} Δ`, midi, delta, n: 2, etranger });
    cas.push({ ...base, nom: `raie étrangère à ${etranger} Δ, couplé réaliste`, midi, delta, n: 2, etranger, couple: { beta: 0.2, am: 0.1 } });
    cas.push({ ...base, nom: `raie étrangère à ${etranger} Δ, couplé extrême`, midi, delta, n: 2, etranger, couple: { beta: 0.8, am: 0.3 }, extreme: true });
  }
  // 5. dérive, vibrato lent, bruit
  for (const midi of [48, 66, 84]) for (const delta of [0.8, 2]) {
    cas.push({ ...base, nom: 'dérive 1 ¢/s', midi, delta, n: 2, derive: 1 });
    cas.push({ ...base, nom: 'vibrato 3 ¢ 0,4 Hz', midi, delta, n: 2, vib: 3, fv: 0.4 });
    cas.push({ ...base, nom: 'bruit 20 dB', midi, delta, n: 2, rsb: 20 });
    cas.push({ ...base, nom: 'secousse du soufflet 1,2 Hz', midi, delta, n: 2, vib: 3, fv: 1.2 });
    cas.push({ ...base, nom: 'tout réaliste (couplé, -6 dB, dérive, bruit)', midi, delta, n: 2, rapportDb: 6, couple: { beta: 0.2, am: 0.1 }, derive: 1, vib: 2, fv: 0.5, rsb: 25 });
    cas.push({ ...base, nom: 'tout extrême (couplé, -6 dB, dérive, bruit)', midi, delta, n: 2, rapportDb: 6, couple: { beta: 0.8, am: 0.3 }, derive: 1, vib: 2, fv: 0.5, rsb: 25, extreme: true });
  }
  // 6. T6, Do6 sous 0,5 Hz avec le vibrato du soufflet de 2 ¢ à 0,5 Hz
  for (const delta of [0.3, 0.5])
    cas.push({ ...base, nom: 'Do6 lent, vibrato 2 ¢', midi: 84, delta, n: 2, vib: 2, fv: 0.5, secondes: 12 });
  return cas;
}

const f2 = (v, d = 2) => (Number.isFinite(v) ? v.toFixed(d) : '—');
export const dCents = (c) => 1200 * Math.log2(1 + c.delta / at(c.midi, 0));
export const REALISTE_CENTS = 12;   // au-delà, les deux anches ne sont plus un unisson d'accordéon (musette très ouverte)
export const horsUnisson = (c) => dCents(c) > REALISTE_CENTS;
export function ligne(r) {
  const c = r.cas;
  const peigne = (r.srcs?.peigne ?? 0) / Math.max(1, r.n);
  return `| ${c.nom} | ${c.midi} | ${c.delta}${horsUnisson(c) ? ' (Δ > 12 ¢)' : ''}${c.couple ? ` β${c.couple.beta} AM${c.couple.am}` : ''}${c.adler ? ` κ/Δ${c.adler.kappaSurD}` : ''}${c.etranger ? '' : ''} | ${r.errMed.map((e) => f2(e)).join('/')} | ${r.errP95.map((e) => f2(e)).join('/')} | ${r.errP95A.map((e) => f2(e)).join('/')} | ${f2(r.battMed, 3)} | ${f2(r.cohMed, 3)} / ${f2(r.cohP95, 2)} | ${r.stab == null ? 'non' : f2(r.stab, 1)} | ${f2(100 * r.perm, 0)} % | ${f2(100 * peigne, 0)} % |`;
}
export const TETE = '| cas | midi | Δ Hz | err médiane ¢ par anche | err p95 ¢ (vérité entière) | err p95 ¢ (vérité v57) | err battement Hz | cohérence médiane / p95 Hz | stable à (s) | permutation | peigne |\n|---|---|---|---|---|---|---|---|---|---|---|';

// Résumé par famille : erreur p95 par anche (vérité entière), pire cas et médiane des cas ; « extrême » = couplage hors du réaliste
// ou Δ > 12 ¢ (hors tolérance, gardé pour mémoire).
export function resume(out) {
  const fam = new Map();
  for (const r of out) {
    const c = r.cas;
    const k = c.nom.replace(/ [0-9,]+ dB$/, '') + (horsUnisson(c) && !c.extreme ? ' [Δ > 12 ¢]' : '');
    (fam.get(k) ?? fam.set(k, []).get(k)).push(r);
  }
  const lignes = ['| famille | cas | err p95 ¢ médiane / pire | pire (vérité v57) | cohérence p95 pire Hz | cas > 0,3 ¢ | cas > 1 ¢ | peigne |', '|---|---|---|---|---|---|---|---|'];
  for (const [k, rs] of fam) {
    const pire = rs.map((r) => Math.max(...r.errP95)), pireA = rs.map((r) => Math.max(...r.errP95A));
    const co = rs.map((r) => r.cohP95).filter(Number.isFinite);
    const pg = rs.reduce((a, r) => a + (r.srcs?.peigne ?? 0), 0) / Math.max(1, rs.reduce((a, r) => a + r.n, 0));
    lignes.push(`| ${k} | ${rs.length} | ${f2(med(pire))} / ${f2(Math.max(...pire))} | ${f2(Math.max(...pireA))} | ${f2(Math.max(...co, 0))} | ${pire.filter((v) => v > 0.3).length} | ${pire.filter((v) => v > 1).length} | ${f2(100 * pg, 0)} % |`);
  }
  return lignes.join('\n');
}

if (process.argv[1]?.endsWith('bench_frequences.mjs')) {
  const filtre = process.argv.find((a) => a.startsWith('--nom='))?.slice(6);
  const out = [];
  console.log(TETE);
  for (const c of grille()) {
    if (filtre && !c.nom.includes(filtre)) continue;
    const r = evaluer(c);
    out.push(r);
    console.log(ligne(r));
  }
  console.log('\n' + resume(out));
  if (process.argv.includes('--json')) {
    const fs = await import('node:fs');
    fs.writeFileSync(process.argv.find((a) => a.startsWith('--out='))?.slice(6) ?? 'bench_frequences.json', JSON.stringify(out));
  }
}
