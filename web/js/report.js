// Module « Enregistrement et rapport » : mémorise la mesure de chaque anche,
// affiche le tableau des écarts, exporte (CSV / JSON / impression) et permet
// de copier les battements mesurés vers la liste de battements cible.

import { noteLabel, beatTarget, centsClass } from './music.js';

const STORE_KEY = 'aal.report';

// Échappement HTML : les noms d'instrument et étiquettes peuvent provenir
// d'un JSON importé ou du localStorage — jamais insérés bruts dans le DOM.
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

export class Report {
  constructor() {
    this.name = '';
    this.rows = new Map(); // "midi|voiceId" → ligne
    this.load();
  }

  load() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const d = JSON.parse(raw);
        this.name = d.name || '';
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
        rows: [...this.rows.entries()],
      }));
    } catch { /* ignore */ }
  }

  // Capture les voix actuellement suivies d'un tick moteur.
  // `dir` : sens du soufflet ('T' tirer, 'P' pousser) — chaque note d'un
  // accordéon a une anche par sens, mémorisées séparément.
  record(tick, cfg, dir = 'T') {
    if (!tick || tick.playedMidi == null) return 0;
    let n = 0;
    for (const g of tick.groups) {
      for (const v of g.voices) {
        if (!v.tracked || g.fill < 0.999) continue;
        const key = `${tick.playedMidi}|${v.def.id}|${dir}`;
        this.rows.set(key, {
          midi: tick.playedMidi,
          dir,
          voiceMidi: v.midi,
          voiceId: v.def.id,
          label: v.def.label || v.def.id,
          nominal: v.nominal,
          target: v.target,
          fMeas: v.fMeas,
          dCents: v.dCents,
          dTargetCents: v.dTargetCents,
          beatMeas: v.beatMeas,
          beatTarget: v.beat,
          ts: Date.now(),
        });
        n++;
      }
    }
    if (n) this.save();
    return n;
  }

  clear() { this.rows.clear(); this.save(); }

  sorted() {
    return [...this.rows.values()].sort((a, b) =>
      a.midi - b.midi || a.voiceMidi - b.voiceMidi || (a.dir || 'T').localeCompare(b.dir || 'T'));
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
        const c = r?.dTargetCents;
        const cls = r == null ? 'empty' : `g-${centsClass(c, cfg.tolCents ?? 1)}`;
        const title = `${noteLabel(m + (cfg.transpose || 0)).full}${r ? ` : ${c >= 0 ? '+' : ''}${c.toFixed(1)} ¢` : ' (non mesuré)'}`;
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

  renderTable(el, cfg, onOverride) {
    const rows = this.sorted();
    const fmt = (x, d = 2) => (x == null ? '—' : x.toFixed(d));
    const cls = (c) => centsClass(c, cfg.tolCents ?? 1);
    let html = `<thead><tr><th>Note</th><th>Voix</th><th>Soufflet</th><th>Cible (Hz)</th><th>Mesuré (Hz)</th>
      <th>Écart nom. (¢)</th><th>Écart cible (¢)</th><th>Batt. mes. (Hz)</th><th>Batt. cible</th>
      <th>Écrasement batt.</th></tr></thead><tbody>`;
    const seenMidi = new Set();
    for (const r of rows) {
      const lbl = noteLabel(r.midi + (cfg.transpose || 0));
      const bt = r.beatTarget ? beatTarget(r.midi, cfg.beatCurve).toFixed(2) : '—';
      const firstOfMidi = !seenMidi.has(r.midi);
      seenMidi.add(r.midi);
      const ovRaw = cfg.beatCurve?.overrides?.[r.midi];
      const ov = Number.isFinite(Number(ovRaw)) && ovRaw !== '' && ovRaw != null ? Number(ovRaw) : '';
      html += `<tr>
        <td>${firstOfMidi ? lbl.full : ''}</td>
        <td>${esc(r.label)}</td>
        <td>${(r.dir || 'T') === 'P' ? 'pousser' : 'tirer'}</td>
        <td>${fmt(r.target, 3)}</td>
        <td>${fmt(r.fMeas, 3)}</td>
        <td class="${cls(r.dCents)}">${fmt(r.dCents, 1)}</td>
        <td class="${cls(r.dTargetCents)}">${fmt(r.dTargetCents, 1)}</td>
        <td>${fmt(r.beatMeas)}</td>
        <td>${bt}</td>
        <td>${firstOfMidi ? `<input type="number" step="0.05" data-midi="${r.midi}" value="${ov}" placeholder="auto">` : ''}</td>
      </tr>`;
    }
    html += '</tbody>';
    el.innerHTML = html;
    el.querySelectorAll('input[data-midi]').forEach((inp) => {
      inp.addEventListener('change', () => onOverride(Number(inp.dataset.midi), inp.value));
    });
  }

  toCsv(cfg) {
    const sep = ';';
    const lines = [
      ['note', 'midi', 'voix', 'soufflet', 'cible_hz', 'mesure_hz', 'ecart_nominal_cents',
       'ecart_cible_cents', 'battement_hz', 'battement_cible_hz'].join(sep),
    ];
    for (const r of this.sorted()) {
      lines.push([
        noteLabel(r.midi + (cfg.transpose || 0)).full, r.midi, r.label,
        (r.dir || 'T') === 'P' ? 'pousser' : 'tirer',
        r.target?.toFixed(4), r.fMeas?.toFixed(4), r.dCents?.toFixed(2),
        r.dTargetCents?.toFixed(2), r.beatMeas?.toFixed(3) ?? '',
        r.beatTarget ? beatTarget(r.midi, cfg.beatCurve).toFixed(2) : '',
      ].join(sep));
    }
    return lines.join('\n');
  }

  toJson(cfg) {
    return JSON.stringify({
      app: 'accordeur-anche-libre',
      version: 1,
      name: this.name,
      date: new Date().toISOString(),
      a4: cfg.a4,
      temperament: cfg.temperament,
      beatCurve: cfg.beatCurve,
      rows: [...this.rows.entries()],
    }, null, 1);
  }

  fromJson(text, cfg) {
    const d = JSON.parse(text);
    if (d.app !== 'accordeur-anche-libre') throw new Error('fichier inconnu');
    this.name = d.name || '';
    this.rows = new Map(d.rows || []);
    if (d.beatCurve) cfg.beatCurve = d.beatCurve;
    this.save();
  }

  printableHtml(cfg) {
    const fmt = (x, d = 2) => (x == null ? '—' : x.toFixed(d));
    const date = new Date().toLocaleString('fr-FR');
    let body = '';
    for (const r of this.sorted()) {
      const lbl = noteLabel(r.midi + (cfg.transpose || 0));
      body += `<tr><td>${lbl.full}</td><td>${esc(r.label)}</td>
        <td>${(r.dir || 'T') === 'P' ? 'pousser' : 'tirer'}</td><td>${fmt(r.target, 3)}</td>
        <td>${fmt(r.fMeas, 3)}</td><td>${fmt(r.dCents, 1)}</td><td>${fmt(r.dTargetCents, 1)}</td>
        <td>${fmt(r.beatMeas)}</td></tr>`;
    }
    return `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Rapport d'accordage — ${esc(this.name) || 'instrument'}</title>
<style>
 body{font:13px/1.5 system-ui,sans-serif;color:#111;margin:28px}
 h1{font-size:20px} .meta{color:#555;margin-bottom:14px}
 table{border-collapse:collapse;width:100%;font-size:12px}
 th,td{border:1px solid #999;padding:3px 8px;text-align:right}
 th:first-child,td:first-child{text-align:left}
</style></head><body>
<h1>Rapport d'accordage</h1>
<div class="meta">Instrument : <b>${esc(this.name) || '—'}</b> · ${date} ·
 La4 = ${Number(cfg.a4)} Hz · tempérament : ${esc(cfg.temperament)} · ${this.rows.size} mesures</div>
<table><thead><tr><th>Note</th><th>Voix</th><th>Soufflet</th><th>Cible (Hz)</th><th>Mesuré (Hz)</th>
<th>Écart nominal (¢)</th><th>Écart cible (¢)</th><th>Battement (Hz)</th></tr></thead>
<tbody>${body}</tbody></table>
<p>Généré par Accordeur Anche Libre Pro.</p>
<script>window.print()</` + `script></body></html>`;
  }
}
