// Onglet « Banc » : liaison avec le firmware du banc d'accordage (ESP32-S3),
// par WebSocket (WiFi) ou Web Serial (USB). Affiche la télémétrie live, pilote
// les actionneurs, capture des rafales d'acquisition (P/Q/T) et fusionne
// chaque point de mesure avec la lecture acoustique de l'accordeur → journal
// exportable en CSV (remplace l'ancien HDF5 + plan_exp.csv).

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
    try { telem = JSON.parse(line); renderTelem(); } catch { /* trame partielle */ }
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

  on('bcCapture', 'onclick', capturePoint);
  on('bcCsv', 'onclick', exportCsv);
  on('bcClearLog', 'onclick', () => { logRows = []; renderLog(); });
}
