// Module « Enregistrement et rapport » : mémorise la mesure de chaque anche,
// affiche les tableaux des écarts (par rangée et par sens quand le protocole
// guidé est utilisé), exporte (CSV / JSON / impression), recalcule tout quand
// le La ou la table d'accordage change, et permet de copier les battements
// mesurés vers la liste de battements cible.
// Les calculs (cibles, écarts, unités) sont dans accordage.js, les courbes et
// la comparaison de deux rapports dans courbes.js.

import { activerGlisser } from './glisser.js';
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

// Identifiant d'une « unité » du rapport : un bouton dans un sens (sa case si le
// protocole l'a rangée), sinon la note et le sens.
export const uidDe = (r) => r.cas ?? `${r.midi}|${r.dir || 'T'}`;

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
    this.hist = [];   // états précédents (annuler)
    this.futur = [];  // états annulés (rétablir)
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

  // ---- Édition en un clic (Ewen, 19/10/2026) ---------------------------------------
  // Une « unité » = un bouton mesuré dans un sens : toutes les lignes (voix) qui
  // partagent sa case (`cas`), ou à défaut la même note et le même sens.
  // Chaque modification garde de quoi annuler / rétablir.
  _snap() { return JSON.stringify([...this.rows.entries()]); }
  _empiler() {
    this.hist.push(this._snap());
    if (this.hist.length > 60) this.hist.shift();
    this.futur.length = 0;
  }
  get peutAnnuler() { return this.hist.length > 0; }
  get peutRetablir() { return this.futur.length > 0; }
  annuler() {
    if (!this.hist.length) return false;
    this.futur.push(this._snap());
    this.rows = new Map(JSON.parse(this.hist.pop()));
    this.save();
    return true;
  }
  retablir() {
    if (!this.futur.length) return false;
    this.hist.push(this._snap());
    this.rows = new Map(JSON.parse(this.futur.pop()));
    this.save();
    return true;
  }

  // Applique `transforme(ligne)` aux lignes des unités données et remet les
  // clés à jour. Refuse (rien ne change) si une ligne en écraserait une autre.
  _deplacer(uids, transforme) {
    const set = new Set(uids);
    const gardees = [];
    const deplacees = [];
    for (const [k, r] of this.rows) (set.has(uidDe(r)) ? deplacees : gardees).push([k, r]);
    if (!deplacees.length) return { ok: false, raison: 'rien à modifier', n: 0 };
    const nouvelles = deplacees.map(([, r]) => transforme({ ...r }));
    const cleDe = (r) => `${r.midi}|${r.voiceId}|${r.dir || 'T'}${r.cas ? `|${r.cas}` : ''}`;
    const pris = new Set(gardees.map(([k]) => k));
    const casPris = new Set(gardees.filter(([, r]) => r.cas).map(([, r]) => r.cas));
    const vus = new Set();
    for (const r of nouvelles) {
      const k = cleDe(r);
      if (pris.has(k) || vus.has(k) || (r.cas && casPris.has(r.cas))) return { ok: false, raison: 'une mesure existe déjà à cet endroit (refaites ou effacez-la d\'abord)', n: 0 };
      vus.add(k);
    }
    this._empiler();
    this.rows = new Map([...gardees, ...nouvelles.map((r) => [cleDe(r), r])]);
    this.save();
    return { ok: true, n: set.size };
  }

  // Bascule tiré <-> poussé (une mesure, une sélection, une rangée entière).
  // `suite` (protocole) donne la case de l'autre sens pour le même bouton.
  basculerSens(uids, suite = null) {
    return this._deplacer(uids, (r) => {
      const dir = (r.dir || 'T') === 'T' ? 'P' : 'T';
      if (r.cas) {
        const c = suite?.find((x) => x.rang === r.rang && x.bouton === r.bouton && x.sens === dir);
        r.cas = c ? c.id : `${dir}-r${r.rang}-b${r.bouton}`;
        if (c) r.nomRang = c.nomRang;
      }
      r.dir = dir;
      return r;
    });
  }

  // Réaffecte un bouton mesuré à une autre case de la suite (autre bouton, autre rangée).
  reaffecter(uid, cas) {
    return this._deplacer([uid], (r) => ({ ...r, cas: cas.id, rang: cas.rang, bouton: cas.bouton, nomRang: cas.nomRang, dir: cas.sens }));
  }

  // Déplace une mesure (glisser-déposer) vers une case de la suite. Si la case est
  // déjà remplie : mode 'refuser' (rien ne change, `occupee` est rendu),
  // 'echanger' (les deux mesures se croisent) ou 'remplacer' (la mesure de la
  // case cible est effacée). Un seul pas d'annulation dans tous les cas.
  deplacerMesure(uid, cas, mode = 'refuser') {
    const src = [...this.rows.values()].filter((r) => uidDe(r) === uid);
    if (!src.length) return { ok: false, raison: 'rien à déplacer', n: 0 };
    if (src[0].cas === cas.id) return { ok: false, raison: '', n: 0 };
    const occupant = [...this.rows.values()].some((r) => r.cas === cas.id);
    if (!occupant) return this.reaffecter(uid, cas);
    if (mode === 'refuser') return { ok: false, occupee: true, raison: '', n: 0 };
    const a = src[0];
    const casA = { id: a.cas, rang: a.rang, bouton: a.bouton, nomRang: a.nomRang, sens: a.dir || 'T' };
    const vers = (r, c) => ({ ...r, cas: c.id, rang: c.rang, bouton: c.bouton, nomRang: c.nomRang, dir: c.sens });
    const cle = (r) => `${r.midi}|${r.voiceId}|${r.dir || 'T'}${r.cas ? `|${r.cas}` : ''}`;
    this._empiler();
    const nouv = [];
    for (const r of this.rows.values()) {
      if (uidDe(r) === uid) nouv.push(vers(r, cas));
      else if (r.cas === cas.id) { if (mode === 'echanger' && casA.id) nouv.push(vers(r, casA)); }
      else nouv.push(r);
    }
    this.rows = new Map(nouv.map((r) => [cle(r), r]));
    this.save();
    return { ok: true, n: src.length };
  }

  // ---- La vue « à l'instrument » : une ligne par bouton ---------------------------------
  // Sections (rangée × sens) de lignes par bouton. `suite` : la suite attendue du
  // protocole, pour montrer aussi les boutons pas encore mesurés ; `courante` : la
  // case à jouer. Rangées dans l'ordre où elles se jouent, tiré puis poussé.
  sections(cfg, suite = null, courante = null) {
    const u = unite(cfg);
    const ordreRang = new Map();
    for (const c of suite ?? []) if (!ordreRang.has(c.rang)) ordreRang.set(c.rang, ordreRang.size);
    const rangOrd = (r) => (ordreRang.has(r) ? ordreRang.get(r) : (r ?? 0));
    const secs = new Map();
    const section = (rang, nomRang, dir) => {
      const k = `${rang ?? 0}|${dir}`;
      if (!secs.has(k)) secs.set(k, { cle: k, rang: rang ?? null, nomRang: nomRang ?? null, dir, boutons: new Map() });
      return secs.get(k);
    };
    const bouton = (s, uid, base) => {
      if (!s.boutons.has(uid)) s.boutons.set(uid, { uid, bouton: base.bouton ?? null, midi: base.midi, cas: base.cas ?? null, rows: [], mesure: false });
      return s.boutons.get(uid);
    };
    for (const c of suite ?? []) {
      const b = bouton(section(c.rang, c.nomRang, c.sens), c.id, { bouton: c.bouton, midi: c.midi - (cfg.transpose || 0), cas: c.id });
      b.attendu = c;
    }
    for (const r of this.rows.values()) {
      const dir = r.dir || 'T';
      const b = bouton(section(r.rang, r.nomRang, dir), uidDe(r), r);
      b.rows.push(r);
      b.mesure = true;
      b.midi = r.midi;
      if (r.bouton != null) b.bouton = r.bouton;
    }
    const out = [];
    for (const s of secs.values()) {
      const boutons = [...s.boutons.values()].map((b) => {
        const analyses = b.rows.slice().sort((x, y) => x.voiceMidi - y.voiceMidi).map((r) => ({ r, a: analyser(r, cfg) }));
        const justes = analyses.filter((x) => !x.a.signe);
        const battantes = analyses.filter((x) => x.a.signe).sort((x, y) => x.a.signe - y.a.signe);
        const classes = [
          ...justes.map((x) => centsClass(x.a.dTargetCents, cfg.tolCents ?? 1)),
          ...battantes.map((x) => classeBatt(x.a.ecartBatt, x.a.battVoulu)),
        ];
        const etat = !b.mesure ? 'non' : classes.some((c) => c === 'warn' || c === 'bad') ? 'reprendre' : 'fait';
        return { ...b, justes, battantes, etat, courant: !!courante && b.cas === courante.id, u };
      }).sort((x, y) => (x.bouton ?? 0) - (y.bouton ?? 0) || x.midi - y.midi);
      out.push({ ...s, boutons });
    }
    return out.sort((a, b) => rangOrd(a.rang) - rangOrd(b.rang) || (a.dir === b.dir ? 0 : a.dir === 'T' ? -1 : 1));
  }

  // HTML du rapport. Fonction pure (testée sans navigateur) : `opts.sel`
  // { uid, midi, dir } met une ligne en surbrillance ; `opts.detail` ajoute les
  // Hz, l'écart nominal et l'écrasement ; `opts.imprime` retire les commandes.
  htmlRapport(cfg, opts = {}) {
    const u = unite(cfg);
    const d = decimalesUnite(u);
    const sel = opts.sel ?? null;
    const secs = this.sections(cfg, opts.suite ?? null, opts.courante ?? null);
    const ETATS = { fait: 'fait', reprendre: 'à reprendre', non: 'pas encore mesuré' };
    let html = `<p class="hint">${esc(this.enTete(cfg))}</p>`;
    if (!secs.length) return `${html}<p class="hint">aucune mesure enregistrée.</p>`;
    const edition = !opts.imprime;
    for (const s of secs) {
      const nb = s.boutons.filter((b) => b.mesure).length;
      const ouvert = nb > 0 || s.boutons.some((b) => b.courant) || opts.imprime ? ' open' : '';
      const uids = s.boutons.filter((b) => b.mesure).map((b) => b.uid);
      const voixBat = [...new Set(s.boutons.flatMap((b) => b.battantes.map((x) => x.r.voiceId)))];
      const etiqVoix = (id) => esc(s.boutons.flatMap((b) => b.battantes).find((x) => x.r.voiceId === id)?.r.label ?? id);
      const titre = `${s.nomRang ? `${esc(s.nomRang)} — ` : ''}${s.dir === 'P' ? 'poussé' : 'tiré'}`;
      html += `<details class="sec"${ouvert}><summary><b>${titre}</b> <span class="hint">${nb} / ${s.boutons.length} boutons</span>`
        + (edition && nb ? ` <button class="mini" data-act="section-sens" data-uids="${esc(uids.join(','))}" title="Basculer toute cette rangée en ${s.dir === 'P' ? 'tiré' : 'poussé'}">⇄ rangée en ${s.dir === 'P' ? 'tiré' : 'poussé'}</button>` : '')
        + `</summary><table class="par-bouton"><thead><tr>${edition ? '<th></th>' : ''}<th>Bouton</th><th>Note</th><th>Voix juste (¢)</th>`
        + voixBat.map((id) => `<th>${etiqVoix(id)} (${UNITES_BATT[u]}) / cible</th>`).join('')
        + `<th>État</th>${edition ? '<th></th>' : ''}</tr></thead><tbody>`;
      for (const b of s.boutons) {
        const lbl = noteLabel(b.midi + (cfg.transpose || 0)).full;
        const estSel = sel && ((sel.uid && sel.uid === b.uid) || (!sel.uid && sel.midi === b.midi && sel.dir === s.dir));
        const cls = `${b.etat}${b.courant ? ' courant' : ''}${estSel ? ' sel' : ''}`;
        const juste = b.justes.length
          ? b.justes.map((x) => `<span class="${centsClass(x.a.dTargetCents, cfg.tolCents ?? 1)}"><b>${signe(x.a.dTargetCents, 1)}</b>${b.justes.length > 1 ? ` <small>${esc(x.r.label)}</small>` : ''}</span>`).join(' ')
          : '—';
        const cases = voixBat.map((id) => {
          const x = b.battantes.find((y) => y.r.voiceId === id);
          if (!x) return '<td>—</td>';
          return `<td class="${classeBatt(x.a.ecartBatt, x.a.battVoulu)} gros"><b>${formatBatt(x.a.battMes, u)}</b> <small>/ ${formatBatt(x.a.battVoulu, u)} · ${x.a.ecartBatt == null ? '—' : signe(enUnite(x.a.ecartBatt, u), d)}</small></td>`;
        }).join('');
        html += `<tr class="${cls}" data-uid="${esc(b.uid)}" data-midi="${b.midi}" data-dir="${s.dir}">`
          + (edition ? `<td>${b.mesure ? `<span class="poignee" data-glisse="${esc(b.uid)}" title="Saisir et lâcher sur une autre case">⠿</span><input type="checkbox" data-sel="${esc(b.uid)}" title="Sélectionner">` : ''}</td>` : '')
          + `<td>${b.bouton ?? ''}</td><td class="gros"><b>${lbl}</b></td><td class="gros">${juste}</td>${cases}`
          + `<td class="etat-${b.etat}">${b.courant ? 'à jouer' : ETATS[b.etat]}</td>`
          + (edition ? `<td>${b.mesure ? `<button class="mini" data-act="sens" data-uids="${esc(b.uid)}" title="Basculer en ${s.dir === 'P' ? 'tiré' : 'poussé'}">⇄</button>`
            + (b.cas ? ` <button class="mini" data-refaire="${esc(b.cas)}" title="Refaire cette case">↻</button>` : '') : ''}</td>` : '')
          + '</tr>';
        if (opts.detail && b.mesure) {
          const ligne = b.rows.map((r) => {
            const a = analyser(r, cfg);
            const ovRaw = cfg.beatCurve?.overrides?.[r.midi];
            const ovHz = Number.isFinite(Number(ovRaw)) && ovRaw !== '' && ovRaw != null ? Number(ovRaw) : null;
            const ov = ovHz == null ? '' : +enUnite(ovHz, u).toFixed(d);
            return `${esc(r.label)} : cible ${a.target.toFixed(3)} Hz · mesuré ${r.fMeas == null ? '—' : r.fMeas.toFixed(3)} Hz · écart nominal ${a.dCents == null ? '—' : signe(a.dCents, 1)} ¢`
              + (a.signe && edition ? ` · écrasement battement <input type="number" step="${u === 'hz' ? 0.05 : 3}" data-midi="${r.midi}" value="${ov}" placeholder="auto"> ${UNITES_BATT[u]}` : '');
          }).join('<br>');
          html += `<tr class="detail"><td colspan="${6 + voixBat.length}">${ligne}</td></tr>`;
        }
      }
      html += '</tbody></table></details>';
    }
    return html;
  }

  // Rapport à l'écran. `opts` : { suite, courante, sel, detail, onRefaire(cas), onSelect(sel),
  // onAction(type, { uids }), onSelection(uids) }.
  renderTable(el, cfg, onOverride, opts = {}) {
    const u = unite(cfg);
    el.innerHTML = this.htmlRapport(cfg, opts);
    el.querySelectorAll('input[data-midi]').forEach((inp) => {
      inp.addEventListener('change', () => {
        onOverride(Number(inp.dataset.midi), inp.value === '' ? '' : depuisUnite(Number(inp.value), u));
      });
    });
    el.querySelectorAll('button[data-refaire]').forEach((b) => {
      b.addEventListener('click', (e) => { e.stopPropagation(); opts.onRefaire?.(b.dataset.refaire); });
    });
    el.querySelectorAll('button[data-act]').forEach((b) => {
      b.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        opts.onAction?.(b.dataset.act, { uids: b.dataset.uids.split(',').filter(Boolean) });
      });
    });
    el.querySelectorAll('tr[data-uid]').forEach((tr) => {
      tr.addEventListener('click', (e) => {
        if (e.target.closest('button,input,a')) return;
        opts.onSelect?.({ uid: tr.dataset.uid, midi: Number(tr.dataset.midi), dir: tr.dataset.dir });
      });
    });
    if (opts.onDeplacer) {
      activerGlisser(el, { source: '.poignee[data-glisse]', cible: 'tr[data-uid]', libelle: (h) => h.closest('tr').querySelector('.gros')?.textContent ?? '',
        onDepose: (h, tr) => opts.onDeplacer(h.dataset.glisse, tr.dataset.uid) });
    }
    el.querySelectorAll('input[data-sel]').forEach((c) => {
      c.addEventListener('change', () => opts.onSelection?.([...el.querySelectorAll('input[data-sel]:checked')].map((x) => x.dataset.sel)));
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
    return { comp, nomA, nomB, seriesA: a, seriesB: b, resume: texteResume(comp.resume, u, cfg), graphiques: graphiquesComparaison(comp, nomA, nomB, cfg, u) };
  }

  csvComparaison(cmp, cfg) { return csvComparaison(cmp.comp, cmp.nomA, cmp.nomB, cfg, unite(cfg)); }

  printableHtml(cfg, cmp = null, opts = {}) {
    const u = unite(cfg);
    const date = new Date().toLocaleString('fr-FR');
    const lieu = LIEUX[this.contexte.lieu] ?? this.contexte.lieu;
    const graphs = graphiquesRapport(this.series(cfg), cfg, u).map((g) => g.svg).join('');
    const tables = this.htmlRapport(cfg, { imprime: true, detail: true, suite: opts.suite ?? null });
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
 td.warn{background:#fff2cc} td.bad{background:#f8d0d0} details.sec{margin:8px 0} summary{font-size:13px} td.gros{font-size:15px} tr.detail td{font-size:11px;color:#444;text-align:left} .etat-non{color:#888}
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
