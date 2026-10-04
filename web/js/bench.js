// Onglet « Banc » : liaison avec le firmware du banc d'accordage (ESP32-S3),
// par WebSocket (WiFi) ou Web Serial (USB). Affiche la télémétrie live, pilote
// les actionneurs, capture des rafales d'acquisition (P/Q/T) et fusionne
// chaque point de mesure avec la lecture acoustique de l'accordeur → journal
// exportable en CSV (remplace l'ancien HDF5 + plan_exp.csv).
// Carte « Seuils d'auto-entretien » : rampe de pression, démarrage,
// extinction, plaquage (calculs dans seuils.js, testés à part).

import { analyseRun, leakFlow } from './seuils.js';

const $ = (id) => document.getElementById(id);

let mode = null;            // 'ws' | 'serial' | null
let ws = null;
let serialPort = null, serialWriter = null, serialReader = null;
let rxBuf = '';
let telem = {};            // dernière trame JSON
let acq = null;            // rafale en cours : { hz, dur, rows:[[t,p,q,T],…] }
let acqResolve = null;
let logRows = [];          // points de mesure fusionnés
let getAcoustic = () => ({});

// ---- Connexion --------------------------------------------------------------
function setStatus(txt, on) {
  const el = $('bcStatus');
  if (el) { el.textContent = txt; el.className = 'bc-status' + (on ? ' on' : ''); }
}

async function connectWs() {
  const ip = ($('bcIp').value || '').trim();
  if (!ip) { setStatus('IP requise', false); return; }
  const url = ip.startsWith('ws') ? ip : `ws://${ip}:8266/ws`;
  try {
    ws = new WebSocket(url);
    mode = 'ws';
    ws.onopen = () => setStatus('connecté (WiFi)', true);
    ws.onclose = () => { setStatus('déconnecté', false); mode = null; };
    ws.onerror = () => setStatus('erreur WebSocket', false);
    ws.onmessage = (e) => feed(typeof e.data === 'string' ? e.data : '');
    setStatus('connexion…', false);
  } catch (e) { setStatus('échec : ' + e.message, false); }
}

async function connectSerial() {
  if (!navigator.serial) { setStatus('Web Serial non supporté', false); return; }
  try {
    serialPort = await navigator.serial.requestPort();
    await serialPort.open({ baudRate: 115200 });
    mode = 'serial';
    serialWriter = serialPort.writable.getWriter();
    setStatus('connecté (USB)', true);
    readSerialLoop();
  } catch (e) { setStatus('échec USB : ' + e.message, false); }
}

async function readSerialLoop() {
  const dec = new TextDecoder();
  serialReader = serialPort.readable.getReader();
  try {
    while (true) {
      const { value, done } = await serialReader.read();
      if (done) break;
      feed(dec.decode(value));
    }
  } catch { /* port fermé */ }
  setStatus('déconnecté', false); mode = null;
}

function send(cmd) {
  if (mode === 'ws' && ws?.readyState === 1) ws.send(cmd);
  else if (mode === 'serial' && serialWriter) serialWriter.write(new TextEncoder().encode(cmd + '\n'));
  else setStatus('non connecté', false);
}

// ---- Réception (lignes) -----------------------------------------------------
function feed(chunk) {
  rxBuf += chunk;
  let i;
  while ((i = rxBuf.indexOf('\n')) >= 0) {
    const line = rxBuf.slice(0, i).trim();
    rxBuf = rxBuf.slice(i + 1);
    if (line) onLine(line);
  }
  // Sur WebSocket, un message peut ne pas finir par \n : on traite le reste.
  if (mode === 'ws' && rxBuf.trim()) { onLine(rxBuf.trim()); rxBuf = ''; }
}

function onLine(line) {
  if (line[0] === '{') {
    try { telem = JSON.parse(line); renderTelem(); recordSeuil(); } catch { /* trame partielle */ }
  } else if (line.startsWith('A ')) {
    handleAcq(line.slice(2));
  } else {
    setStatus(line, mode != null);   // réponse (OK, PONG, ERR…)
  }
}

function handleAcq(rest) {
  const p = rest.split(/\s+/);
  if (p[0] === 'BEGIN') { acq = { hz: +p[1], dur: +p[2], rows: [] }; return; }
  if (p[0] === 'END') {
    if (acqResolve) { acqResolve(acq); acqResolve = null; }
    return;
  }
  if (acq) acq.rows.push([+p[0], +p[1], +p[2], +p[3]]);  // t_ms, p, q, T
}

// ---- Rendu télémétrie -------------------------------------------------------
function num(x, d = 2) { return (x == null || isNaN(x)) ? '—' : (+x).toFixed(d); }
function renderTelem() {
  const set = (id, v) => { const e = $(id); if (e) e.textContent = v; };
  set('bt_p', num(telem.p / 100, 2));       // Pa → hPa
  set('bt_q', num(telem.q, 3));
  set('bt_t', num(telem.T, 2));
  set('bt_bellv', telem.bellv ?? '—');
  set('bt_surf', num(telem.surf, 1));
  set('bt_clap', num(telem.clap, 1));
  set('bt_btn', telem.btn ?? '—');
  set('bt_state', telem.st ?? '—');
}

// ---- Acquisition + capture d'un point de mesure -----------------------------
async function acquire(dur, hz) {
  return new Promise((resolve) => { acqResolve = resolve; send(`ACQUIRE ${dur} ${hz}`); });
}

function mean(rows, col) {
  if (!rows.length) return null;
  let s = 0; for (const r of rows) s += r[col];
  return s / rows.length;
}

async function capturePoint() {
  const dur = +($('bcAcqDur').value || 3);
  const hz = +($('bcAcqHz').value || 100);
  setStatus('acquisition…', true);
  const a = await acquire(dur, hz);
  const ac = getAcoustic() || {};
  const pMean = mean(a.rows, 1), qMean = mean(a.rows, 2), tMean = mean(a.rows, 3);
  const impedance = (pMean != null && qMean) ? pMean / qMean : null;      // P/Q
  const puiHydro = (pMean != null && qMean != null) ? pMean * qMean : null; // P·Q
  const row = {
    n: logRows.length + 1,
    surf: telem.surf ?? null, clap: telem.clap ?? null, bellv: telem.bellv ?? null,
    p: pMean, q: qMean, T: tMean, imp: impedance, puiHydro,
    note: ac.note ?? '', f0: ac.f0 ?? null, cents: ac.cents ?? null,
    level: ac.level_db ?? null, tresp: ac.attack_ms ?? null, sigma: ac.sigma ?? null,
  };
  logRows.push(row);
  renderLog();
  setStatus(`point ${row.n} capturé (${a.rows.length} échant.)`, true);
}

function renderLog() {
  const tb = $('bcLogBody');
  if (!tb) return;
  tb.innerHTML = logRows.map((r) => `<tr>
    <td>${r.n}</td><td>${num(r.surf, 0)}</td><td>${num(r.clap, 0)}</td>
    <td>${num(r.bellv, 0)}</td>
    <td>${num(r.p, 0)}</td><td>${num(r.q, 3)}</td><td>${num(r.imp, 1)}</td>
    <td>${r.note} ${r.cents != null ? (r.cents >= 0 ? '+' : '') + num(r.cents, 1) + '¢' : ''}</td>
    <td>${num(r.f0, 2)}</td><td>${num(r.tresp, 0)}</td><td>${num(r.sigma, 1)}</td>
  </tr>`).join('');
}

// ---- Test de fuite (décroissance de pression) -------------------------------
// Ajuste p(t) = p0·e^(−t/τ) par régression linéaire sur ln(p). Renvoie τ (s).
function fitLeakTau(rows) {
  const pts = rows.filter((r) => r[1] > 0);        // t_ms, p, q, T ; p > 0
  if (pts.length < 3) return null;
  let n = 0, st = 0, sy = 0, stt = 0, sty = 0;
  for (const r of pts) {
    const t = r[0] / 1000, y = Math.log(r[1]);
    n++; st += t; sy += y; stt += t * t; sty += t * y;
  }
  const slope = (n * sty - st * sy) / (n * stt - st * st);
  if (!(slope < 0)) return { tau: Infinity, p0: Math.exp(sy / n) };
  return { tau: -1 / slope, p0: Math.exp((sy - slope * st) / n) };
}

async function leakTest() {
  const dur = +($('bcLeakDur').value || 10);
  setStatus('test de fuite…', true);
  const a = await new Promise((resolve) => { acqResolve = resolve; send(`LEAKTEST ${dur} 20`); });
  const fit = fitLeakTau(a.rows);
  const el = $('bcLeakRes');
  if (el) {
    if (!fit) el.textContent = 'données insuffisantes';
    else if (!isFinite(fit.tau)) el.textContent = 'aucune fuite décelable (τ→∞)';
    else el.textContent = `τ = ${fit.tau.toFixed(1)} s · demi-vie ${(fit.tau * Math.LN2).toFixed(1)} s`;
    // Avec le volume fermé (pièce + tuyaux + bouteille tampon), la chute de
    // pression donne le débit de fuite et le genre de fuite (n ≈ 0,5 : un
    // trou ; n ≈ 1 : pores, peau, fente longue).
    const volL = parseFloat($('bcLeakVol')?.value);
    if (fit && volL > 0) {
      const lf = leakFlow(a.rows, volL, 500);
      if (Number.isFinite(lf.qRef)) {
        el.textContent += ` · fuite ≈ ${lf.qRef.toFixed(2)} L/min à 500 Pa`
          + ` (trou de ${lf.holeMm.toFixed(2)} mm, n = ${lf.n.toFixed(2)})`;
      }
    }
  }
  setStatus(`fuite : ${a.rows.length} points`, true);
}

// ---- Plan d'expériences automatique (DOE) -----------------------------------
let doeRunning = false;

function parseGrid(str) {
  return (str || '').split(',').map((s) => parseFloat(s.trim())).filter((x) => !isNaN(x));
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function settleFor(sec) {   // attend, en restant interruptible
  const end = Date.now() + sec * 1000;
  while (Date.now() < end) {
    if (!doeRunning) return false;
    await sleep(100);
  }
  return true;
}

async function runDoe() {
  if (doeRunning || mode == null) { if (mode == null) setStatus('non connecté', false); return; }
  const sections = parseGrid($('doeSection').value);
  const presses = parseGrid($('doePress').value);
  const claps = parseGrid($('doeClap').value);
  const btn = parseInt($('doeBtn').value, 10);
  const settle = +($('doeSettle').value || 4);
  const dur = +($('doeDur').value || 3);
  if (!sections.length || !presses.length || !claps.length) {
    setStatus('DOE : grille incomplète', false); return;
  }
  const total = sections.length * presses.length * claps.length;
  doeRunning = true;
  $('doeRun').disabled = true; $('doeStop').disabled = false;
  if (btn >= 0) send(`PRESS ${btn} 1`);
  let k = 0;
  try {
    for (const s of sections) {
      if (!doeRunning) break;
      send(`SECTION ${s}`);
      for (const c of claps) {
        if (!doeRunning) break;
        send(`CLAP ${c}`);
        for (const p of presses) {
          if (!doeRunning) break;
          k++;
          $('doeProgress').textContent =
            `point ${k}/${total} — S=${s} C=${c}° P=${p} Pa`;
          send(`PRESSURE ${p}`);
          if (!(await settleFor(settle))) break;   // interrompu
          await capturePoint();
        }
      }
    }
  } finally {
    if (btn >= 0) send(`PRESS ${btn} 0`);
    send('PRESSURE 0');
    doeRunning = false;
    $('doeRun').disabled = false; $('doeStop').disabled = true;
    $('doeProgress').textContent = k >= total ? `terminé (${k} points)` : `arrêté (${k}/${total})`;
  }
}

function stopDoe() { doeRunning = false; setStatus('DOE arrêté', mode != null); }

function exportCsv() {
  const cols = ['n', 'surf', 'clap', 'bellv', 'p', 'q', 'T', 'imp', 'puiHydro',
    'note', 'f0', 'cents', 'level', 'tresp', 'sigma'];
  const head = ['point', 'surface_mm2', 'clapet_deg', 'soufflet_pas_s',
    'pression_Pa', 'debit_slm', 'temp_C', 'impedance', 'pui_hydro',
    'note', 'f0_Hz', 'cents', 'niveau_dB', 'tresp_ms', 'sigma_s-1'];
  const lines = [head.join(',')];
  for (const r of logRows) lines.push(cols.map((c) => r[c] ?? '').join(','));
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'banc_plan_exp.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- Seuils d'auto-entretien (rampe de pression) ----------------------------
// À chaque trame de télémétrie : pression, débit, et ce que l'accordeur
// entend (niveau brut, clarté, f0). La rampe est faite à la main (soufflerie,
// soufflet joué lentement) ou asservie (PRESSURE). À l'arrêt : démarrage,
// extinction, plaquage, reprise, plage utile, par cycle.
let su = null;              // { t0, rows, timer, auto, res }

function suNum(id, def) { const v = parseFloat($(id)?.value); return Number.isFinite(v) ? v : def; }

function suOpts() {
  return {
    clarityMin: suNum('suClar', 0.8), marginDb: suNum('suMarge', 6),
    holdS: suNum('suHold', 0.15), lagS: suNum('suLag', 0), minRise: suNum('suMinRise', 20),
  };
}

function recordSeuil() {
  if (!su || su.done) return;
  const a = getAcoustic() || {};
  if (a.age_s != null && a.age_s > 1) {
    $('suProgress').textContent = 'micro arrêté ? Aucune analyse depuis 1 s : lance l’accordeur.';
  }
  su.rows.push({
    t: performance.now() / 1000 - su.t0,
    p: telem.p, q: telem.q, sp: telem.sp ?? null,
    level: a.level_raw_db ?? NaN, clarity: a.clarity ?? 0, f0: a.f0_raw ?? NaN,
  });
  if (su.rows.length % 10 === 0) drawSeuils();
}

function suStart() {
  if (mode == null) { setStatus('non connecté', false); return; }
  su = { t0: performance.now() / 1000, rows: [], timer: null, auto: $('suMode').value === 'auto' };
  send('STREAM 1 50');                         // télémétrie au plus vite (50 Hz)
  const btn = parseInt($('suBtn').value, 10);
  if (btn >= 0) send(`PRESS ${btn} 1`);
  $('suStart').disabled = true; $('suStop').disabled = false;
  if (su.auto) {
    // Rampe en triangle pMin → pMax → pMin, répétée ; consigne mise à jour
    // toutes les 100 ms (assez lisse pour l'asservissement du soufflet).
    const pMin = suNum('suPmin', 0), pMax = suNum('suPmax', 800);
    const rate = Math.max(0.5, suNum('suRate', 10)), cycles = Math.max(1, Math.round(suNum('suCycles', 3)));
    const half = (pMax - pMin) / rate, total = 2 * half * cycles, t0 = performance.now() / 1000;
    su.timer = setInterval(() => {
      const e = performance.now() / 1000 - t0;
      if (e >= total) { suStop(); return; }
      const ph = e % (2 * half);
      const sp = ph < half ? pMin + rate * ph : pMax - rate * (ph - half);
      send(`PRESSURE ${sp.toFixed(1)}`);
      $('suProgress').textContent = `cycle ${Math.floor(e / (2 * half)) + 1}/${cycles} · consigne ${sp.toFixed(0)} Pa · ${su.rows.length} points`;
    }, 100);
  } else {
    $('suProgress').textContent = 'enregistrement : monte lentement la pression, puis redescends';
  }
}

function suStop() {
  if (!su || su.done) return;
  if (su.timer) { clearInterval(su.timer); su.timer = null; send('PRESSURE 0'); }
  const btn = parseInt($('suBtn').value, 10);
  if (btn >= 0) send(`PRESS ${btn} 0`);
  send('STREAM 1 20');
  $('suStart').disabled = false; $('suStop').disabled = true;
  su.done = true;
  suAnalyse();
}

function fmt(x, d = 0) { return Number.isFinite(x) ? x.toFixed(d) : '—'; }

function suAnalyse() {
  if (!su || su.rows.length < 10) { $('suProgress').textContent = 'trop peu de points'; return; }
  const rows = su.rows.filter((r) => Number.isFinite(r.p));
  su.res = analyseRun(rows, suOpts());
  su.rowsUsed = rows;
  const { cycles, mean, std, flow, floorDb } = su.res;
  const line = (k, c) => `<tr><td>${k}</td><td>${fmt(c.p_on)}</td><td>${fmt(c.p_off)}</td>
    <td>${fmt(c.p_choke)}</td><td>${fmt(c.p_unchoke)}</td><td>${fmt(c.hysteresis)}</td>
    <td>${fmt(c.usable_range)}</td><td>${fmt(c.ratio, 2)}</td></tr>`;
  let html = cycles.map((c, i) => line(i + 1, c)).join('');
  if (cycles.length > 1) {
    const ms = (k, d = 0) => `${fmt(mean[k], d)} ± ${fmt(std[k], d)}`;
    html += `<tr><td>moy.</td><td>${ms('p_on')}</td><td>${ms('p_off')}</td>
      <td>${ms('p_choke')}</td><td>${ms('p_unchoke')}</td><td>${ms('hysteresis')}</td>
      <td>${ms('usable_range')}</td><td>${ms('ratio', 2)}</td></tr>`;
  }
  $('suBody').innerHTML = html;
  $('suProgress').textContent = `${rows.length} points, ${cycles.length} cycle(s), fond ${fmt(floorDb, 1)} dB`
    + (Number.isFinite(flow.n) ? ` · débit q = ${flow.c.toPrecision(3)}·p^${flow.n.toFixed(2)} L/min` : '');
  drawSeuils();
}

// Niveau (dB, échelle de gauche) et débit (L/min, échelle de droite) en
// fonction de la pression : rouge = montée, bleu = descente, pâle = l'anche
// ne sonne pas, vert = débit ; traits = seuils du premier cycle.
function drawSeuils() {
  const cv = $('suPlot');
  if (!cv) return;
  const g = cv.getContext('2d'), W = cv.width, H = cv.height, m = 36;
  g.clearRect(0, 0, W, H);
  if (!su) return;
  const rows = su.rows.filter((r) => Number.isFinite(r.p));
  if (rows.length < 2) return;
  const ps = rows.map((r) => r.p), ls = rows.map((r) => r.level).filter(Number.isFinite);
  const qs = rows.map((r) => r.q).filter((x) => Number.isFinite(x) && x > 0);
  const pMin = Math.min(0, ...ps), pMax = Math.max(...ps, 1);
  const lMin = ls.length ? Math.min(...ls) : -90, lMax = ls.length ? Math.max(...ls) : 0;
  const qMax = qs.length ? Math.max(...qs) : 1;
  const X = (p) => m + (W - 2 * m) * (p - pMin) / (pMax - pMin || 1);
  const YL = (l) => H - m - (H - 2 * m) * (l - lMin) / (lMax - lMin || 1);
  const YQ = (q) => H - m - (H - 2 * m) * q / (qMax || 1);
  const css = getComputedStyle(document.documentElement);
  const dim = css.getPropertyValue('--dim').trim() || '#888';
  g.strokeStyle = css.getPropertyValue('--line').trim() || '#888';
  g.fillStyle = dim;
  g.font = '11px sans-serif';
  g.strokeRect(m, m / 2, W - 2 * m, H - 1.5 * m);
  g.fillText(`${fmt(pMin)} Pa`, m, H - m / 3);
  g.fillText(`${fmt(pMax)} Pa`, W - m - 50, H - m / 3);
  g.fillText(`${fmt(lMax)} dB`, 2, m);
  g.fillText(`${fmt(lMin)} dB`, 2, H - m);
  if (qs.length) g.fillText(`${fmt(qMax, 1)} L/min`, W - m + 2, m);
  const osc = su.res?.osc?.length === rows.length ? su.res.osc : null;
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i], up = r.p >= rows[i - 1].p;
    if (Number.isFinite(r.level)) {
      g.fillStyle = up ? '#d0453a' : '#2f6fd0';
      g.globalAlpha = osc && !osc[i] ? 0.3 : 1;
      g.fillRect(X(r.p) - 1, YL(r.level) - 1, 2.5, 2.5);
    }
    if (Number.isFinite(r.q) && r.q > 0) {
      g.globalAlpha = 0.6; g.fillStyle = '#2e9a4c';
      g.fillRect(X(r.p) - 1, YQ(r.q) - 1, 2, 2);
    }
  }
  g.globalAlpha = 1;
  const c = su.res?.cycles?.[0];
  if (c) {
    const vline = (p, col, lab, dy) => {
      if (!Number.isFinite(p)) return;
      g.strokeStyle = col; g.beginPath(); g.moveTo(X(p), m / 2); g.lineTo(X(p), H - m); g.stroke();
      g.fillStyle = col; g.fillText(lab, X(p) + 2, m / 2 + 10 + dy);
    };
    vline(c.p_on, '#d0453a', 'démarre', 0); vline(c.p_off, '#2f6fd0', 's’éteint', 12);
    vline(c.p_choke, '#8a3ad0', 'se plaque', 0); vline(c.p_unchoke, '#8a3ad0', 'repart', 12);
  }
}

function suCsv() {
  if (!su || !su.rows.length) return;
  const label = ($('suLabel').value || 'anche').replace(/[^\w-]+/g, '_');
  const o = suOpts(), res = su.res;
  const lines = [
    `# seuils d'auto-entretien ; ${label} ; ${new Date().toISOString()}`,
    `# mode ${su.auto ? 'rampe asservie' : 'manuel'} ; clarte >= ${o.clarityMin} ; marge ${o.marginDb} dB ; maintien ${o.holdS} s ; retard capteur ${o.lagS} s`,
  ];
  (res?.cycles ?? []).forEach((c, i) => lines.push(`# cycle ${i + 1} ; p_on ${fmt(c.p_on, 1)} ; p_off ${fmt(c.p_off, 1)} ; p_plaquage ${fmt(c.p_choke, 1)} ; p_reprise ${fmt(c.p_unchoke, 1)} ; plage ${fmt(c.usable_range, 1)} Pa`));
  lines.push('t_s,p_Pa,q_slm,consigne_Pa,level_db,clarity,f0_Hz,sonne');
  const used = su.rowsUsed ?? su.rows, osc = res?.osc;
  used.forEach((r, i) => lines.push([r.t.toFixed(3), Number.isFinite(r.p) ? r.p.toFixed(1) : '',
    Number.isFinite(r.q) ? r.q.toFixed(3) : '', r.sp ?? '',
    Number.isFinite(r.level) ? r.level.toFixed(2) : '', (r.clarity ?? 0).toFixed(3),
    Number.isFinite(r.f0) ? r.f0.toFixed(2) : '', osc ? (osc[i] ? 1 : 0) : ''].join(',')));
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `seuils_${label}_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- Câblage des contrôles --------------------------------------------------
export function initBench(acousticFn) {
  if (acousticFn) getAcoustic = acousticFn;
  const on = (id, ev, fn) => { const e = $(id); if (e) e[ev] = fn; };

  on('bcConnectWs', 'onclick', connectWs);
  on('bcConnectSerial', 'onclick', connectSerial);

  on('bcHome', 'onclick', () => send('HOME'));
  on('bcTare', 'onclick', () => send('TARE'));
  on('bcStop', 'onclick', () => send('STOP'));

  const bell = $('bcBell');
  if (bell) bell.oninput = () => { $('bcBellVal').textContent = bell.value; send(`BELLOWS ${bell.value}`); };
  on('bcStrokePush', 'onclick', () => send(`STROKE 1 ${$('bcStrokeSpeed').value || 800}`));
  on('bcStrokeDraw', 'onclick', () => send(`STROKE -1 ${$('bcStrokeSpeed').value || 800}`));
  on('bcPressGo', 'onclick', () => send(`PRESSURE ${$('bcPress').value || 0}`));
  on('bcSectionGo', 'onclick', () => send(`SECTION ${$('bcSection').value || 0}`));
  on('bcClapGo', 'onclick', () => send(`CLAP ${$('bcClap').value || 0}`));
  on('bcValveOpen', 'onclick', () => send('VALVE 1'));
  on('bcValveClose', 'onclick', () => send('VALVE 0'));
  on('bcValvePulse', 'onclick', () => send(`VALVE PULSE ${$('bcPulseMs').value || 500}`));
  on('bcClamp', 'onchange', () => send(`CLAMP ${$('bcClamp').checked ? 1 : 0}`));

  // Électro-aimants (boutons) : presse/relâche un canal (0..70).
  on('bcBtnPress', 'onclick', () => send(`PRESS ${$('bcBtnCh').value || 0} 1`));
  on('bcBtnRelease', 'onclick', () => send(`PRESS ${$('bcBtnCh').value || 0} 0`));
  on('bcAllOff', 'onclick', () => send('ALLOFF'));

  on('doeRun', 'onclick', runDoe);
  on('doeStop', 'onclick', stopDoe);

  on('bcLeak', 'onclick', leakTest);

  on('suStart', 'onclick', suStart);
  on('suStop', 'onclick', suStop);
  on('suRedo', 'onclick', suAnalyse);
  on('suCsv', 'onclick', suCsv);
  on('suClear', 'onclick', () => {
    su = null; $('suBody').innerHTML = ''; $('suProgress').textContent = '—'; drawSeuils();
  });

  on('bcCapture', 'onclick', capturePoint);
  on('bcCsv', 'onclick', exportCsv);
  on('bcClearLog', 'onclick', () => { logRows = []; renderLog(); });
}
