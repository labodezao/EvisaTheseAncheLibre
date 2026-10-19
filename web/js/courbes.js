// Courbes du rapport : courbe de BATTEMENT (ce à quoi l'oreille est sensible,
// en premier pour les instruments à musette) et courbe de JUSTESSE (écart en
// cents de la voix juste), en fonction de la note, par rangée et par sens
// (tiré / poussé), avec la cible de la table d'accordage en bande de fond.
// Comparaison de deux rapports (banc d'accordage / en caisse) : superposition,
// différence note par note, résumé. Module pur ; le dessin est du SVG en
// texte (aucune dépendance), utilisable à l'écran et dans le rapport imprimable.

import { beatTarget, noteLabel } from './music.js';
import { analyser, enUnite, UNITES_BATT, decimalesUnite, classeBatt, TOL_BATT_PCT, TOL_BATT_MIN_HZ } from './accordage.js';

export const BANDE_PCT = 0.10; // bande de la table : cible ± 10 % (affichage)

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ---- Séries ---------------------------------------------------------------------
// type 'battement' : voix qui battent (8'+, 8'-), y = battement mesuré dans
// l'unité, cible = battement voulu ; type 'justesse' : voix justes, y = écart
// à la cible en cents. Une série par (type, rangée, sens, voix). Chaque point
// garde aussi la valeur en Hz (hz, cibleHz) pour les exports.
export function seriesDe(lignes, cfg, unite = 'bpm') {
  const liste = lignes instanceof Map ? [...lignes.values()] : lignes;
  const map = new Map();
  for (const r of liste) {
    const a = analyser(r, cfg);
    const type = a.signe ? 'battement' : 'justesse';
    const y = type === 'battement' ? enUnite(a.battMes, unite) : a.dTargetCents;
    if (y == null || !Number.isFinite(y)) continue;
    const cible = type === 'battement' ? enUnite(a.battVoulu, unite) : 0;
    const dir = r.dir || 'T';
    const cle = `${type}|${r.rang ?? '-'}|${dir}|${r.voiceId}`;
    let s = map.get(cle);
    if (!s) {
      s = { cle, type, rang: r.rang ?? null, nomRang: r.nomRang ?? null, dir, voiceId: r.voiceId, signe: a.signe,
        label: r.label ?? r.voiceId, points: new Map() };
      map.set(cle, s);
    }
    s.points.set(r.midi, { midi: r.midi, y, cible, hz: type === 'battement' ? a.battMes : null, cibleHz: type === 'battement' ? a.battVoulu : null,
      ecartHz: type === 'battement' ? a.ecartBatt : null, hors: type === 'battement' ? classeBatt(a.ecartBatt, a.battVoulu) !== 'ok' : false, bouton: r.bouton ?? null });
  }
  return [...map.values()].map((s) => ({ ...s, points: [...s.points.values()].sort((p, q) => p.midi - q.midi) }))
    .sort((a, b) => (a.type === b.type ? 0 : a.type === 'battement' ? -1 : 1)
      || (a.dir === b.dir ? 0 : a.dir === 'T' ? -1 : 1) || (a.rang ?? 0) - (b.rang ?? 0)
      || String(a.voiceId).localeCompare(String(b.voiceId)));
}

export const nomSerie = (s) => `${s.dir === 'P' ? 'poussé' : 'tiré'}${s.nomRang ? ` · ${s.nomRang}` : ''} · ${s.label}`;

// ---- Comparaison de deux rapports ---------------------------------------------
// seriesA = référence (banc), seriesB = comparée (en caisse) ; différence =
// B moins A, note par note, sur les notes présentes dans les deux.
export function comparer(seriesA, seriesB) {
  const cleSans = (s) => `${s.type}|${s.dir}|${s.voiceId}`;
  const aRang = seriesA.every((s) => s.rang != null) && seriesB.every((s) => s.rang != null);
  const clef = (s) => (aRang ? s.cle : cleSans(s));
  const fusion = (liste) => {
    const m = new Map();
    for (const s of liste) {
      const k = clef(s);
      const e = m.get(k) ?? { ...s, points: new Map() };
      for (const p of s.points) e.points.set(p.midi, p);
      m.set(k, e);
    }
    return m;
  };
  const A = fusion(seriesA);
  const B = fusion(seriesB);
  const series = [];
  for (const [k, sa] of A) {
    const sb = B.get(k);
    if (!sb) continue;
    const points = [];
    for (const [midi, pa] of sa.points) {
      const pb = sb.points.get(midi);
      if (pb) points.push({ midi, a: pa.y, b: pb.y, diff: pb.y - pa.y, cible: pa.cible });
    }
    if (points.length) {
      series.push({ cle: k, type: sa.type, rang: aRang ? sa.rang : null, nomRang: aRang ? sa.nomRang : null, dir: sa.dir, voiceId: sa.voiceId, label: sa.label, points: points.sort((p, q) => p.midi - q.midi) });
    }
  }
  const resume = {};
  for (const type of ['battement', 'justesse']) {
    const pts = [];
    for (const s of series.filter((x) => x.type === type)) for (const p of s.points) pts.push({ ...p, serie: s });
    if (!pts.length) continue;
    const moy = pts.reduce((t, p) => t + p.diff, 0) / pts.length;
    const moyAbs = pts.reduce((t, p) => t + Math.abs(p.diff), 0) / pts.length;
    const tri = [...pts].sort((p, q) => Math.abs(q.diff) - Math.abs(p.diff));
    resume[type] = {
      n: pts.length, moyenne: moy, moyenneAbs: moyAbs,
      max: { midi: tri[0].midi, diff: tri[0].diff, serie: nomSerie(tri[0].serie) },
      plusMobiles: tri.slice(0, 5).map((p) => ({ midi: p.midi, diff: p.diff, serie: nomSerie(p.serie) })),
    };
  }
  return { series, resume };
}

// ---- Dessin SVG ------------------------------------------------------------------
export const PALETTE = ['#1d4ed8', '#c2410c', '#15803d', '#a21caf', '#0e7490', '#b45309', '#be123c', '#4d7c0f'];

function ticksNice(lo, hi, n = 5) {
  const span = hi - lo || 1;
  const pas0 = span / n;
  const mag = 10 ** Math.floor(Math.log10(pas0));
  const pas = [1, 2, 5, 10].map((k) => k * mag).find((p) => p >= pas0) ?? 10 * mag;
  const out = [];
  for (let v = Math.ceil(lo / pas) * pas; v <= hi + 1e-9; v += pas) out.push(Math.round(v / pas) * pas);
  return out;
}

// spec : { titre, unite (texte de l'axe y), series: [{ nom, points: [{midi, y}], tirets?, couleur? }],
// bande: [{ midi, lo, hi }]?, transpose?, largeur?, hauteur?, zero? }
export function courbeSvg(spec) {
  const W = spec.largeur ?? 640;
  const H = spec.hauteur ?? 260;
  const m = { g: 52, d: 14, h: 26, b: 34 };
  const pts = spec.series.flatMap((s) => s.points);
  const bande = spec.bande ?? [];
  if (!pts.length) return '';
  const xs = [...pts.map((p) => p.midi), ...bande.map((p) => p.midi)];
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs, x0 + 1);
  const ys = [...pts.map((p) => p.y), ...bande.flatMap((p) => [p.lo, p.hi])];
  if (spec.zero) ys.push(0);
  let y0 = Math.min(...ys);
  let y1 = Math.max(...ys);
  if (y1 - y0 < 1e-9) y1 = y0 + 1;
  const marge = (y1 - y0) * 0.06;
  y0 -= marge; y1 += marge;
  const X = (v) => m.g + ((v - x0) / (x1 - x0)) * (W - m.g - m.d);
  const Y = (v) => H - m.b - ((v - y0) / (y1 - y0)) * (H - m.b - m.h);
  const tr = spec.transpose || 0;
  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="system-ui,sans-serif" font-size="10">`;
  s += `<rect width="${W}" height="${H}" fill="#fff"/>`;
  s += `<text x="${m.g}" y="14" font-size="12" font-weight="bold" fill="#111">${esc(spec.titre)}</text>`;
  for (const t of ticksNice(y0, y1)) {
    s += `<line x1="${m.g}" x2="${W - m.d}" y1="${Y(t)}" y2="${Y(t)}" stroke="${t === 0 ? '#555' : '#ddd'}"/>`;
    s += `<text x="${m.g - 4}" y="${Y(t) + 3}" text-anchor="end" fill="#444">${Number(t.toFixed(2))}</text>`;
  }
  const ym = (H + m.h - m.b) / 2;
  s += `<text x="12" y="${ym}" transform="rotate(-90 12 ${ym})" text-anchor="middle" fill="#444">${esc(spec.unite)}</text>`;
  for (let n = Math.ceil(x0 / 12) * 12; n <= x1; n += 12) {
    s += `<line x1="${X(n)}" x2="${X(n)}" y1="${m.h}" y2="${H - m.b}" stroke="#eee"/>`;
    s += `<text x="${X(n)}" y="${H - m.b + 13}" text-anchor="middle" fill="#444">${esc(noteLabel(n + tr).full)}</text>`;
  }
  if (bande.length > 1) {
    const hautes = bande.map((p) => `${X(p.midi).toFixed(1)},${Y(p.hi).toFixed(1)}`);
    const basses = [...bande].reverse().map((p) => `${X(p.midi).toFixed(1)},${Y(p.lo).toFixed(1)}`);
    s += `<polygon points="${[...hautes, ...basses].join(' ')}" fill="#9ca3af" fill-opacity="0.28" stroke="none"/>`;
  }
  spec.series.forEach((se, i) => {
    const c = se.couleur ?? PALETTE[i % PALETTE.length];
    const d = se.points.map((p) => `${X(p.midi).toFixed(1)},${Y(p.y).toFixed(1)}`);
    s += `<polyline points="${d.join(' ')}" fill="none" stroke="${c}" stroke-width="1.6"${se.tirets ? ' stroke-dasharray="5 3"' : se.pointille ? ' stroke-dasharray="1 3"' : ''}/>`;
    for (const p of se.points) {
      s += `<circle data-midi="${p.midi}" cx="${X(p.midi).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="2.2" fill="${se.creux ? '#fff' : c}"${se.creux ? ` stroke="${c}"` : ''}/>`;
      if (p.hors) s += `<circle cx="${X(p.midi).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="5.5" fill="none" stroke="#dc2626" stroke-width="1.6"/>`;
    }
  });
  let lx = m.g;
  const ly = H - 5;
  spec.series.forEach((se, i) => {
    const c = se.couleur ?? PALETTE[i % PALETTE.length];
    s += `<rect x="${lx}" y="${ly - 7}" width="9" height="3" fill="${c}"/><text x="${lx + 12}" y="${ly}" fill="#222">${esc(se.nom)}</text>`;
    lx += 18 + se.nom.length * 5.2;
  });
  if (bande.length > 1) {
    const bx = Math.min(lx, W - 150);
    s += `<rect x="${bx}" y="${ly - 8}" width="9" height="6" fill="#9ca3af" fill-opacity="0.4"/><text x="${bx + 12}" y="${ly}" fill="#222">${esc(spec.bandeNom ?? `table ± ${Math.round(BANDE_PCT * 100)} %`)}</text>`;
  }
  return `${s}</svg>`;
}

// La bande de fond de la table d'accordage pour une plage de notes.
export function bandeTable(cfg, unite, de, a) {
  const out = [];
  for (let m = de; m <= a; m++) {
    const v = enUnite(beatTarget(m, cfg.beatCurve), unite);
    out.push({ midi: m, lo: v * (1 - BANDE_PCT), hi: v * (1 + BANDE_PCT) });
  }
  return out;
}

// Tolérance autour de zéro pour la différence mesure − cible (bande de fond).
export function bandeTolerance(cfg, unite, de, a) {
  const out = [];
  for (let m = de; m <= a; m++) {
    const cible = beatTarget(m, cfg.beatCurve);
    const tol = enUnite(Math.max(TOL_BATT_MIN_HZ, TOL_BATT_PCT * cible), unite);
    out.push({ midi: m, lo: -tol, hi: tol });
  }
  return out;
}

// Les graphiques d'un rapport : battement d'abord, puis justesse ; un par sens.
export function graphiquesRapport(series, cfg, unite) {
  const out = [];
  for (const type of ['battement', 'justesse']) {
    for (const dir of ['T', 'P']) {
      const ss = series.filter((x) => x.type === type && x.dir === dir);
      if (!ss.length) continue;
      const mids = ss.flatMap((x) => x.points.map((p) => p.midi));
      const de = Math.min(...mids);
      const a = Math.max(...mids);
      const sens = dir === 'P' ? 'poussé' : 'tiré';
      const nomsSeries = ss.map((x) => ({ nom: [x.nomRang, x.label].filter(Boolean).join(' · '), points: x.points }));
      if (type === 'battement') {
        const cible = bandeTable(cfg, unite, de, a).map((b) => ({ midi: b.midi, y: (b.lo + b.hi) / 2 }));
        out.push({
          type, dir, panneau: 'mesure',
          svg: courbeSvg({
            titre: `Battement des voix musette, ${sens} (${UNITES_BATT[unite]}) : mesure et cible de la table`,
            unite: UNITES_BATT[unite],
            series: [{ nom: 'cible (table)', points: cible, couleur: '#374151', tirets: true }, ...nomsSeries],
            bande: bandeTable(cfg, unite, de, a), transpose: cfg.transpose,
          }),
        });
        out.push({
          type, dir, panneau: 'difference',
          svg: courbeSvg({
            titre: `Mesure moins cible, ${sens} (${UNITES_BATT[unite]}) : les notes hors tolérance sont cerclées`,
            unite: UNITES_BATT[unite],
            series: ss.map((x) => ({ nom: [x.nomRang, x.label].filter(Boolean).join(' · '),
              points: x.points.map((p) => ({ midi: p.midi, y: enUnite(p.ecartHz, unite), hors: p.hors })) })),
            bande: bandeTolerance(cfg, unite, de, a), bandeNom: 'tolérance', transpose: cfg.transpose, zero: true, hauteur: 200,
          }),
        });
      } else {
        out.push({
          type, dir, panneau: 'mesure',
          svg: courbeSvg({ titre: `Justesse de la voix juste, ${sens} (cents)`, unite: 'cents', series: nomsSeries, transpose: cfg.transpose, zero: true }),
        });
      }
    }
  }
  return out;
}

// Superposition de deux rapports + courbe de différence.
export function graphiquesComparaison(comp, nomA, nomB, cfg, unite) {
  const out = [];
  for (const type of ['battement', 'justesse']) {
    const ss = comp.series.filter((x) => x.type === type);
    if (!ss.length) continue;
    const u = type === 'battement' ? UNITES_BATT[unite] : 'cents';
    const sup = [];
    ss.forEach((x, i) => {
      sup.push({ nom: `${nomA} · ${nomSerie(x)}`, points: x.points.map((p) => ({ midi: p.midi, y: p.a })), couleur: PALETTE[(2 * i) % PALETTE.length], tirets: true });
      sup.push({ nom: `${nomB} · ${nomSerie(x)}`, points: x.points.map((p) => ({ midi: p.midi, y: p.b })), couleur: PALETTE[(2 * i + 1) % PALETTE.length] });
    });
    const mids = ss.flatMap((x) => x.points.map((p) => p.midi));
    const nomType = type === 'battement' ? 'Battement' : 'Justesse';
    out.push({ type, kind: 'superposition', svg: courbeSvg({ titre: `${nomType} : ${nomA} et ${nomB} (${u})`, unite: u, series: sup, bande: type === 'battement' ? bandeTable(cfg, unite, Math.min(...mids), Math.max(...mids)) : [], transpose: cfg.transpose, zero: type === 'justesse', largeur: 760 }) });
    out.push({ type, kind: 'difference', svg: courbeSvg({ titre: `Différence ${nomB} moins ${nomA} (${u})`, unite: u, series: ss.map((x) => ({ nom: nomSerie(x), points: x.points.map((p) => ({ midi: p.midi, y: p.diff })) })), transpose: cfg.transpose, zero: true, largeur: 760, hauteur: 200 }) });
  }
  return out;
}

export function texteResume(resume, unite, cfg = {}) {
  const lignes = [];
  const nom = (m) => noteLabel(m + (cfg.transpose || 0)).full;
  for (const type of ['battement', 'justesse']) {
    const r = resume[type];
    if (!r) continue;
    const u = type === 'battement' ? UNITES_BATT[unite] : 'cents';
    const d = type === 'battement' ? decimalesUnite(unite) : 1;
    lignes.push(`${type === 'battement' ? 'Battement' : 'Justesse'} : écart moyen ${r.moyenne.toFixed(d)} ${u}, moyenne des écarts absolus ${r.moyenneAbs.toFixed(d)} ${u}, maximum ${r.max.diff.toFixed(d)} ${u} (${nom(r.max.midi)}, ${r.max.serie}), sur ${r.n} notes ; `
      + `notes qui bougent le plus : ${r.plusMobiles.map((p) => `${nom(p.midi)} ${p.diff >= 0 ? '+' : ''}${p.diff.toFixed(d)}`).join(', ')}.`);
  }
  return lignes;
}

// ---- CSV ---------------------------------------------------------------------------
const f = (x, d) => (x == null || !Number.isFinite(x) ? '' : x.toFixed(d));
// Données de la courbe : le battement dans les DEUX unités, la justesse en cents.
export function csvCourbes(series, cfg, sep = ';') {
  const l = [['type', 'rangee', 'sens', 'voix', 'midi', 'note', 'valeur_hz', 'valeur_batmin', 'cible_hz', 'cible_batmin', 'ecart_hz', 'ecart_batmin', 'hors_tolerance', 'ecart_cents'].join(sep)];
  for (const s of series) {
    for (const p of s.points) {
      const bat = s.type === 'battement';
      l.push([s.type, s.nomRang ?? '', s.dir === 'P' ? 'pousser' : 'tirer', s.label, p.midi,
        noteLabel(p.midi + (cfg.transpose || 0)).full,
        bat ? f(p.hz, 3) : '', bat ? f(p.hz == null ? null : p.hz * 60, 1) : '',
        bat ? f(p.cibleHz, 3) : '', bat ? f(p.cibleHz == null ? null : p.cibleHz * 60, 1) : '',
        bat ? f(p.ecartHz, 3) : '', bat ? f(p.ecartHz == null ? null : p.ecartHz * 60, 1) : '', bat ? (p.hors ? 'oui' : 'non') : '',
        bat ? '' : f(p.y, 2)].join(sep));
    }
  }
  return l.join('\n');
}
export function csvComparaison(comp, nomA, nomB, cfg, unite, sep = ';') {
  const l = [['type', 'unite', 'rangee', 'sens', 'voix', 'midi', 'note', nomA, nomB, 'difference'].join(sep)];
  for (const s of comp.series) {
    const u = s.type === 'battement' ? UNITES_BATT[unite] : 'cents';
    for (const p of s.points) {
      l.push([s.type, u, s.nomRang ?? '', s.dir === 'P' ? 'pousser' : 'tirer', s.label, p.midi,
        noteLabel(p.midi + (cfg.transpose || 0)).full, f(p.a, 3), f(p.b, 3), f(p.diff, 3)].join(sep));
    }
  }
  return l.join('\n');
}
