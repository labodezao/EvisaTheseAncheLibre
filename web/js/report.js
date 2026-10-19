// Module « Enregistrement et rapport » : mémorise la mesure de chaque anche,
// affiche les tableaux des écarts (par rangée et par sens quand le protocole
// guidé est utilisé), exporte (CSV / JSON / impression), recalcule tout quand
// le La ou la table d'accordage change, et permet de copier les battements
// mesurés vers la liste de battements cible.
// Les calculs (cibles, écarts, unités) sont dans accordage.js, les courbes et
// la comparaison de deux rapports dans courbes.js.

import { noteLabel, centsClass } from './music.js';
import {
  analyser, recalculerLignes, classeBatt, formatBatt, enUnite, depuisUnite, UNITES_BATT, decimalesUnite,
} from './accordage.js';
import { seriesDe, graphiquesRapport, csvCourbes, comparer, graphiquesComparaison, texteResume, csvComparaison } from './courbes.js';
import { tableMusette } from './tables-accordage.js';

const STORE_KEY = 'aal.report';

// Échappement HTML : les noms d'instrument et étiquettes peuvent provenir
// d'un JSON importé ou du localStorage — jamais insérés bruts dans le DOM.
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

export const LIEUX = Object.freeze({ banc: 'banc d\'accordage', caisse: 'en caisse (remonté)', autre: 'autre' });

const unite = (cfg) => (cfg.uniteBatt === 'hz' ? 'hz' : 'bpm');
const sensTexte = (d) => ((d || 'T') === 'P' ? 'pousser' : 'tirer');
const signe = (x, d) => (x == null ? '—' : `${x >= 0 ? '+' : ''}${x.toFixed(d)}`);

export class Report {
  constructor() {
    this.name = '';
    // Contexte du rapport : où l'instrument a été accordé (banc, en caisse,
    // autre) et quand, pour comparer deux rapports du même instrument.
    this.contexte = { lieu: 'banc', date: '', note: '' };
    this.rows = new Map(); // "midi|voiceId|sens[|case]" → ligne
    this.load();
  }

  load() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const d = JSON.parse(raw);
        this.name = d.name || '';
        this.contexte = { ...this.contexte, ...(d.contexte || {}) };
        this.rows = new Map(d.rows || []);
        this.migrate();
      }
    } catch { /* stockage indisponible : mode volatil */ }
  }

  // Anciennes clés « midi|voix » (sans sens de soufflet) → tirer par défaut.
  migrate() {
    for (const [k, r] of [...this.rows.entries()]) {
      if (k.split('|').length === 2) {
        this.rows.delete(k);
        r.dir = r.dir || 'T';
        this.rows.set(`${k}|${r.dir}`, r);
      }
    }
  }

  save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        name: this.name,
        contexte: this.contexte,
        rows: [...this.rows.entries()],
      }));
    } catch { /* ignore */ }
  }

  // Capture les voix actuellement suivies d'un tick moteur.
  // `dir` : sens du soufflet ('T' tirer, 'P' pousser) — chaque note d'un
  // accordéon a une anche par sens, mémorisées séparément. `cas` (protocole
  // guidé) : { id, rang, bouton, nomRang } — la mesure est rangée à sa case.
  record(tick, cfg, dir = 'T', cas = null) {
    if (!tick || tick.playedMidi == null) return 0;
    let n = 0;
    for (const g of tick.groups) {
      for (const v of g.voices) {
        if (!v.tracked || g.fill < 0.999) continue;
        const key = `${tick.playedMidi}|${v.def.id}|${dir}${cas ? `|${cas.id}` : ''}`;
        this.rows.set(key, {
          midi: tick.playedMidi,
          dir,
          voiceMidi: v.midi,
          voiceId: v.def.id,
          label: v.def.label || v.def.id,
          beatSign: v.def.beatSign || 0,
          nominal: v.nominal,
          target: v.target,
          fMeas: v.fMeas,
          dCents: v.dCents,
          dTargetCents: v.dTargetCents,
          beatMeas: v.beatMeas,
          beatTarget: v.beat,
          a4Mesure: cfg?.a4 ?? 440,
          ...(cas ? { cas: cas.id, rang: cas.rang, bouton: cas.bouton, nomRang: cas.nomRang } : {}),
          ts: Date.now(),
        });
        n++;
      }
    }
    if (n) this.save();
    return n;
  }

  // Efface les mesures d'une case du protocole (pour la refaire).
  retirerCase(casId) {
    let n = 0;
    for (const [k, r] of [...this.rows.entries()]) if (r.cas === casId) { this.rows.delete(k); n++; }
    if (n) this.save();
    return n;
  }

  clear() { this.rows.clear(); this.save(); }

  // Recalcule toutes les valeurs enregistrées depuis la configuration courante
  // (La, tempérament, table d'accordage, décalages). Les fréquences mesurées
  // ne changent jamais : rien n'est perdu.
  recalculer(cfg) {
    const n = recalculerLignes(this.rows, cfg);
    if (n) this.save();
    return n;
  }

  sorted() {
    return [...this.rows.values()].sort((a, b) =>
      (a.rang ?? 0) - (b.rang ?? 0) || (a.bouton ?? 0) - (b.bouton ?? 0)
      || a.midi - b.midi || a.voiceMidi - b.voiceMidi || (a.dir || 'T').localeCompare(b.dir || 'T'));
  }

  // Grille de progression : une cellule par (voix × note) pour un sens de
  // soufflet — vert accordé, orange proche, rouge à reprendre, vide non
  // mesuré. Cliquer verrouille la note pour la mesurer.
  renderGrid(el, cfg, dir, currentMidi, onSelect) {
    const rows = this.sorted().filter((r) => (r.dir || 'T') === dir);
    const voiceIds = [...new Set(rows.map((r) => r.voiceId))];
    if (!voiceIds.length) { el.innerHTML = '<p class="hint">aucune mesure pour ce sens de soufflet — jouez et enregistrez.</p>'; return; }
    let lo = Math.min(48, ...rows.map((r) => r.midi));
    let hi = Math.max(84, ...rows.map((r) => r.midi));
    if (currentMidi != null) { lo = Math.min(lo, currentMidi); hi = Math.max(hi, currentMidi); }
    const byKey = new Map(rows.map((r) => [`${r.midi}|${r.voiceId}`, r]));
    let html = '<table class="tune-grid"><thead><tr><th></th>';
    for (let m = lo; m <= hi; m++) {
      const l = noteLabel(m + (cfg.transpose || 0));
      html += `<th class="${m === currentMidi ? 'cur' : ''}">${l.name === 'Do' ? l.full : (m % 12 === 0 ? l.full : '')}</th>`;
    }
    html += '</tr></thead><tbody>';
    for (const vid of voiceIds) {
      html += `<tr><th>${esc(rows.find((r) => r.voiceId === vid)?.label || vid)}</th>`;
      for (let m = lo; m <= hi; m++) {
        const r = byKey.get(`${m}|${vid}`);
        const a = r ? analyser(r, cfg) : null;
        // voix qui bat : couleur selon l'écart de battement ; voix juste : selon les cents
        const c = a?.dTargetCents;
        const cls = r == null ? 'empty' : (a.signe && a.ecartBatt != null
          ? `g-${classeBatt(a.ecartBatt, a.battVoulu)}` : `g-${centsClass(c, cfg.tolCents ?? 1)}`);
        const txt = a?.signe && a.ecartBatt != null
          ? ` : ${signe(enUnite(a.ecartBatt, unite(cfg)), decimalesUnite(unite(cfg)))} ${UNITES_BATT[unite(cfg)]}`
          : (r ? ` : ${c >= 0 ? '+' : ''}${c.toFixed(1)} ¢` : ' (non mesuré)');
        const title = `${noteLabel(m + (cfg.transpose || 0)).full}${txt}`;
        html += `<td class="${cls}${m === currentMidi ? ' cur' : ''}" data-midi="${m}" title="${title}"></td>`;
      }
      html += '</tr>';
    }
    html += '</tbody></table>';
    el.innerHTML = html;
    el.querySelectorAll('td[data-midi]').forEach((td) => {
      td.addEventListener('click', () => onSelect(Number(td.dataset.midi)));
    });
  }

  // Copie les battements mesurés (voix « + ») vers les écrasements de la
  // liste de battements — pour reproduire l'accord d'un instrument existant.
  copyBeatsTo(beatCurve) {
    const overrides = { ...(beatCurve.overrides || {}) };
    let n = 0;
    for (const r of this.sorted()) {
      if (r.beatMeas != null && r.beatMeas > 0.05 && /\+/.test(r.voiceId)) {
        overrides[r.midi] = Math.round(Math.abs(r.beatMeas) * 100) / 100;
        n++;
      }
    }
    beatCurve.overrides = overrides;
    return n;
  }

  // Phrase d'en-tête : la table d'accordage et le La utilisés.
  enTete(cfg) {
    const t = cfg.beatCurve?.table ? tableMusette(cfg.beatCurve.table) : null;
    return `Table d'accordage : ${t ? t.nom : 'courbe personnelle'} · La4 = ${Number(cfg.a4).toFixed(1)} Hz · tempérament ${cfg.temperament} · battements en ${UNITES_BATT[unite(cfg)]}`;
  }

  // Groupes du rapport : un par sens et par rangée (protocole), sinon un par sens.
  groupes() {
    const g = new Map();
    for (const r of this.sorted()) {
      const k = `${r.dir || 'T'}|${r.rang ?? 0}`;
      if (!g.has(k)) g.set(k, { dir: r.dir || 'T', rang: r.rang ?? null, nomRang: r.nomRang ?? null, rows: [] });
      g.get(k).rows.push(r);
    }
    return [...g.values()].sort((a, b) => (a.dir === b.dir ? 0 : a.dir === 'T' ? -1 : 1) || (a.rang ?? 0) - (b.rang ?? 0));
  }

  // Une ligne de tableau (HTML) pour le rapport à l'écran ou imprimé.
  _ligne(r, cfg, firstOfMidi, editable) {
    const u = unite(cfg);
    const d = decimalesUnite(u);
    const a = analyser(r, cfg);
    const fmt = (x, n = 2) => (x == null ? '—' : x.toFixed(n));
    const lbl = noteLabel(r.midi + (cfg.transpose || 0));
    const cls = (c) => centsClass(c, cfg.tolCents ?? 1);
    const ecart = a.signe
      ? `<td class="${classeBatt(a.ecartBatt, a.battVoulu)}">${a.ecartBatt == null ? '—' : `${signe(enUnite(a.ecartBatt, u), d)} ${UNITES_BATT[u]}`}</td>`
      : `<td class="${cls(a.dTargetCents)}">${a.dTargetCents == null ? '—' : `${signe(a.dTargetCents, 1)} ¢`}</td>`;
    const ovRaw = cfg.beatCurve?.overrides?.[r.midi];
    const ovHz = Number.isFinite(Number(ovRaw)) && ovRaw !== '' && ovRaw != null ? Number(ovRaw) : null;
    const ov = ovHz == null ? '' : +enUnite(ovHz, u).toFixed(d);
    return `<tr>
        <td>${firstOfMidi ? lbl.full : ''}</td>
        ${r.bouton != null ? `<td>${r.bouton}</td>` : ''}
        <td>${esc(r.label)}</td>
        <td>${fmt(a.target, 3)}</td>
        <td>${fmt(r.fMeas, 3)}</td>
        <td class="${cls(a.dCents)}">${fmt(a.dCents, 1)}</td>
        ${ecart}
        <td>${a.signe ? formatBatt(a.battMes, u) : '—'}</td>
        <td>${a.signe ? formatBatt(a.battVoulu, u) : '—'}</td>
        ${editable ? `<td>${firstOfMidi && a.signe ? `<input type="number" step="${u === 'hz' ? 0.05 : 3}" data-midi="${r.midi}" value="${ov}" placeholder="auto">` : ''}</td>
        <td>${r.cas ? `<button class="mini" data-refaire="${esc(r.cas)}" title="Refaire cette case">↻</button>` : ''}</td>` : ''}
      </tr>`;
  }

  // Tableaux à l'écran : un par sens et par rangée. `opts.onRefaire(casId)`.
  renderTable(el, cfg, onOverride, opts = {}) {
    const u = unite(cfg);
    const groupes = this.groupes();
    let html = `<p class="hint">${esc(this.enTete(cfg))}</p>`;
    for (const g of groupes) {
      const avecBouton = g.rows.some((r) => r.bouton != null);
      html += `<h3>${g.dir === 'P' ? 'Poussé' : 'Tiré'}${g.nomRang ? ` — ${esc(g.nomRang)}` : ''}</h3>
        <table><thead><tr><th>Note</th>${avecBouton ? '<th>Bouton</th>' : ''}<th>Voix</th><th>Cible (Hz)</th><th>Mesuré (Hz)</th>
        <th>Écart nom. (¢)</th><th>Écart à la cible</th><th>Batt. mes. (${UNITES_BATT[u]})</th><th>Batt. voulu (${UNITES_BATT[u]})</th>
        <th>Écrasement batt. (${UNITES_BATT[u]})</th><th></th></tr></thead><tbody>`;
      const seen = new Set();
      for (const r of g.rows) {
        const k = r.cas ? `${r.cas}` : `${r.midi}`;
        html += this._ligne(r, cfg, !seen.has(k), true);
        seen.add(k);
      }
      html += '</tbody></table>';
    }
    if (!groupes.length) html += '<p class="hint">aucune mesure enregistrée.</p>';
    el.innerHTML = html;
    el.querySelectorAll('input[data-midi]').forEach((inp) => {
      inp.addEventListener('change', () => {
        const v = inp.value === '' ? '' : depuisUnite(Number(inp.value), u);
        onOverride(Number(inp.dataset.midi), v);
      });
    });
    el.querySelectorAll('button[data-refaire]').forEach((b) => {
      b.addEventListener('click', () => opts.onRefaire?.(b.dataset.refaire));
    });
  }

  // Séries et graphiques du rapport courant (battement d'abord).
  series(cfg) { return seriesDe(this.rows, cfg, unite(cfg)); }

  toCsv(cfg) {
    const sep = ';';
    const f = (x, n) => (x == null || !Number.isFinite(x) ? '' : x.toFixed(n));
    const lieu = LIEUX[this.contexte.lieu] ?? this.contexte.lieu;
    const t = cfg.beatCurve?.table ?? '';
    const lines = [
      ['instrument', 'contexte', 'date', 'la4_hz', 'table', 'note', 'midi', 'rangee', 'bouton', 'voix', 'soufflet', 'cible_hz', 'mesure_hz',
        'ecart_nominal_cents', 'ecart_cible_cents', 'battement_mesure_hz', 'battement_mesure_batmin',
        'battement_cible_hz', 'battement_cible_batmin', 'ecart_battement_hz', 'ecart_battement_batmin'].join(sep),
    ];
    for (const r of this.sorted()) {
      const a = analyser(r, cfg);
      lines.push([
        this.name, lieu, this.contexte.date, f(cfg.a4, 2), t,
        noteLabel(r.midi + (cfg.transpose || 0)).full, r.midi, r.nomRang ?? '', r.bouton ?? '', r.label, sensTexte(r.dir),
        f(a.target, 4), f(r.fMeas, 4), f(a.dCents, 2), f(a.dTargetCents, 2),
        a.signe ? f(a.battMes, 3) : '', a.signe ? f(a.battMes == null ? null : a.battMes * 60, 1) : '',
        a.signe ? f(a.battVoulu, 3) : '', a.signe ? f(a.battVoulu * 60, 1) : '',
        a.signe ? f(a.ecartBatt, 3) : '', a.signe ? f(a.ecartBatt == null ? null : a.ecartBatt * 60, 1) : '',
      ].join(sep));
    }
    return lines.join('\n');
  }

  csvCourbes(cfg) { return csvCourbes(this.series(cfg), cfg); }

  toJson(cfg) {
    return JSON.stringify({
      app: 'accordeur-anche-libre',
      version: 2,
      name: this.name,
      contexte: this.contexte,
      date: new Date().toISOString(),
      a4: cfg.a4,
      temperament: cfg.temperament,
      uniteBatt: cfg.uniteBatt ?? 'bpm',
      beatCurve: cfg.beatCurve,
      rows: [...this.rows.entries()],
    }, null, 1);
  }

  // Lit un fichier de rapport sans toucher au rapport courant (comparaison).
  static lireJson(text) {
    const d = JSON.parse(text);
    if (d.app !== 'accordeur-anche-libre') throw new Error('fichier inconnu');
    return {
      name: d.name || '', contexte: { lieu: 'autre', date: (d.date || '').slice(0, 10), ...(d.contexte || {}) },
      a4: d.a4, beatCurve: d.beatCurve, rows: (d.rows || []).map(([, r]) => r),
    };
  }

  fromJson(text, cfg) {
    const d = Report.lireJson(text);
    this.name = d.name;
    this.contexte = { lieu: 'banc', date: '', note: '', ...d.contexte };
    this.rows = new Map(JSON.parse(text).rows || []);
    if (d.beatCurve) cfg.beatCurve = d.beatCurve;
    // Le rapport chargé est recalculé avec le La et le tempérament courants.
    recalculerLignes(this.rows, cfg);
    this.save();
  }

  // Comparaison de ce rapport (banc) et d'un autre (en caisse, ...) : rend
  // { comp, nomA, nomB, resume (texte), graphiques }.
  comparerAvec(autre, cfg) {
    const u = unite(cfg);
    const copie = autre.rows.map((r) => ({ ...r }));
    recalculerLignes(copie, cfg);
    const a = seriesDe(this.rows, cfg, u);
    const b = seriesDe(copie, cfg, u);
    const comp = comparer(a, b);
    const nom = (c, n) => `${LIEUX[c.lieu] ?? c.lieu}${c.date ? ` ${c.date}` : ''}${n ? ` (${n})` : ''}`;
    const nomA = nom(this.contexte, '');
    const nomB = nom(autre.contexte, '');
    return { comp, nomA, nomB, resume: texteResume(comp.resume, u, cfg), graphiques: graphiquesComparaison(comp, nomA, nomB, cfg, u) };
  }

  csvComparaison(cmp, cfg) { return csvComparaison(cmp.comp, cmp.nomA, cmp.nomB, cfg, unite(cfg)); }

  printableHtml(cfg, cmp = null) {
    const u = unite(cfg);
    const date = new Date().toLocaleString('fr-FR');
    const lieu = LIEUX[this.contexte.lieu] ?? this.contexte.lieu;
    const graphs = graphiquesRapport(this.series(cfg), cfg, u).map((g) => g.svg).join('');
    let tables = '';
    for (const g of this.groupes()) {
      const avecBouton = g.rows.some((r) => r.bouton != null);
      tables += `<h3>${g.dir === 'P' ? 'Poussé' : 'Tiré'}${g.nomRang ? ` — ${esc(g.nomRang)}` : ''}</h3>
<table><thead><tr><th>Note</th>${avecBouton ? '<th>Bouton</th>' : ''}<th>Voix</th><th>Cible (Hz)</th><th>Mesuré (Hz)</th>
<th>Écart nominal (¢)</th><th>Écart à la cible</th><th>Batt. mesuré (${UNITES_BATT[u]})</th><th>Batt. voulu (${UNITES_BATT[u]})</th></tr></thead><tbody>`;
      const seen = new Set();
      for (const r of g.rows) {
        const k = r.cas ?? r.midi;
        tables += this._ligne(r, cfg, !seen.has(k), false);
        seen.add(k);
      }
      tables += '</tbody></table>';
    }
    let comparaison = '';
    if (cmp) {
      comparaison = `<h2>Comparaison : ${esc(cmp.nomA)} et ${esc(cmp.nomB)}</h2>
<p>Différence = ${esc(cmp.nomB)} moins ${esc(cmp.nomA)}, note par note.</p>
<ul>${cmp.resume.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>${cmp.graphiques.map((g) => g.svg).join('')}`;
    }
    return `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Rapport d'accordage — ${esc(this.name) || 'instrument'}</title>
<style>
 body{font:13px/1.5 system-ui,sans-serif;color:#111;margin:28px}
 h1{font-size:20px} h2{font-size:16px;margin-top:22px} h3{font-size:13px;margin:14px 0 4px} .meta{color:#555;margin-bottom:14px}
 table{border-collapse:collapse;width:100%;font-size:12px}
 th,td{border:1px solid #999;padding:3px 8px;text-align:right}
 th:first-child,td:first-child{text-align:left}
 svg{max-width:100%;height:auto;margin:6px 0;display:block}
 td.warn{background:#fff2cc} td.bad{background:#f8d0d0}
</style></head><body>
<h1>Rapport d'accordage</h1>
<div class="meta">Instrument : <b>${esc(this.name) || '—'}</b> · ${esc(lieu)}${this.contexte.date ? ` ${esc(this.contexte.date)}` : ''} · ${date} ·
 ${esc(this.enTete(cfg))} · ${this.rows.size} mesures</div>
${graphs}
${tables}
${comparaison}
<p>Généré par Accordeur Anche Libre Pro.</p>
<script>window.print()</` + `script></body></html>`;
  }
}
