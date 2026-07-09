// Module « Enregistrement et rapport » : mémorise la mesure de chaque anche,
// affiche le tableau des écarts, exporte (CSV / JSON / impression) et permet
// de copier les battements mesurés vers la liste de battements cible.

import { noteLabel, beatTarget } from './music.js';

const STORE_KEY = 'aal.report';

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
      }
    } catch { /* stockage indisponible : mode volatil */ }
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
  record(tick, cfg) {
    if (!tick || tick.playedMidi == null) return 0;
    let n = 0;
    for (const g of tick.groups) {
      for (const v of g.voices) {
        if (!v.tracked || g.fill < 0.999) continue;
        const key = `${tick.playedMidi}|${v.def.id}`;
        this.rows.set(key, {
          midi: tick.playedMidi,
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
    return [...this.rows.values()].sort((a, b) => a.midi - b.midi || a.voiceMidi - b.voiceMidi);
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
    const cls = (c) => (c == null ? 'dim' : Math.abs(c) < 1 ? 'ok' : Math.abs(c) < 5 ? 'warn' : 'bad');
    let html = `<thead><tr><th>Note</th><th>Voix</th><th>Cible (Hz)</th><th>Mesuré (Hz)</th>
      <th>Écart nom. (¢)</th><th>Écart cible (¢)</th><th>Batt. mes. (Hz)</th><th>Batt. cible</th>
      <th>Écrasement batt.</th></tr></thead><tbody>`;
    const seenMidi = new Set();
    for (const r of rows) {
      const lbl = noteLabel(r.midi + (cfg.transpose || 0));
      const bt = r.beatTarget ? beatTarget(r.midi, cfg.beatCurve).toFixed(2) : '—';
      const firstOfMidi = !seenMidi.has(r.midi);
      seenMidi.add(r.midi);
      const ov = cfg.beatCurve?.overrides?.[r.midi] ?? '';
      html += `<tr>
        <td>${firstOfMidi ? lbl.full : ''}</td>
        <td>${r.label}</td>
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
      ['note', 'midi', 'voix', 'cible_hz', 'mesure_hz', 'ecart_nominal_cents',
       'ecart_cible_cents', 'battement_hz', 'battement_cible_hz'].join(sep),
    ];
    for (const r of this.sorted()) {
      lines.push([
        noteLabel(r.midi + (cfg.transpose || 0)).full, r.midi, r.label,
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
      body += `<tr><td>${lbl.full}</td><td>${r.label}</td><td>${fmt(r.target, 3)}</td>
        <td>${fmt(r.fMeas, 3)}</td><td>${fmt(r.dCents, 1)}</td><td>${fmt(r.dTargetCents, 1)}</td>
        <td>${fmt(r.beatMeas)}</td></tr>`;
    }
    return `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Rapport d'accordage — ${this.name || 'instrument'}</title>
<style>
 body{font:13px/1.5 system-ui,sans-serif;color:#111;margin:28px}
 h1{font-size:20px} .meta{color:#555;margin-bottom:14px}
 table{border-collapse:collapse;width:100%;font-size:12px}
 th,td{border:1px solid #999;padding:3px 8px;text-align:right}
 th:first-child,td:first-child{text-align:left}
</style></head><body>
<h1>Rapport d'accordage</h1>
<div class="meta">Instrument : <b>${this.name || '—'}</b> · ${date} ·
 La4 = ${cfg.a4} Hz · tempérament : ${cfg.temperament} · ${this.rows.size} mesures</div>
<table><thead><tr><th>Note</th><th>Voix</th><th>Cible (Hz)</th><th>Mesuré (Hz)</th>
<th>Écart nominal (¢)</th><th>Écart cible (¢)</th><th>Battement (Hz)</th></tr></thead>
<tbody>${body}</tbody></table>
<p>Généré par Accordeur Anche Libre Pro.</p>
<script>window.print()</` + `script></body></html>`;
  }
}
