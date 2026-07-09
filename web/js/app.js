// Application principale : capture audio basse latence, liaison avec le
// Worker DSP, affichages (aiguille, stroboscope, spectres), contrôles et
// module rapport.

import {
  TEMPERAMENTS, REGISTER_PRESETS, noteLabel, parseNoteList,
  midiToFreq, voiceTargetFreq, beatTarget,
} from './music.js';
import { Report } from './report.js';

const $ = (id) => document.getElementById(id);

// ---- État ------------------------------------------------------------------
const CFG_KEY = 'aal.cfg';
const cfg = Object.assign({
  a4: 440,
  temperament: 'equal',
  transpose: 0,
  calibrationPpm: 0,
  mode: 'auto',
  register: 'MM',
  manualNotes: null,
  response: 'normal',
  beatCurve: { midiLow: 48, bLow: 0.8, midiHigh: 96, bHigh: 3.0, overrides: {} },
}, loadCfg());

function loadCfg() {
  try { return JSON.parse(localStorage.getItem(CFG_KEY)) || {}; } catch { return {}; }
}
function saveCfg() {
  try { localStorage.setItem(CFG_KEY, JSON.stringify(cfg)); } catch { /* ignore */ }
}

const state = {
  running: false,
  frozen: false,
  tick: null,           // dernier résultat moteur
  smoothCents: null,    // lissage de l'aiguille
  strobePhase: 0,
  lastDraw: performance.now(),
  stableTicks: 0,
  lastMidi: null,
  toneOn: false,
};

let audioCtx = null;
let worker = null;
let mediaStream = null;
let toneNodes = [];
const report = new Report();

// ---- Audio -----------------------------------------------------------------
async function startAudio() {
  if (state.running) return;
  $('btnStart').disabled = true;
  try {
    audioCtx = new AudioContext({ latencyHint: 'interactive' });
    await audioCtx.audioWorklet.addModule('js/capture-worklet.js');

    worker = new Worker('js/dsp/worker.js', { type: 'module' });
    const channel = new MessageChannel();
    worker.postMessage({ type: 'init', sampleRate: audioCtx.sampleRate, cfg: engineCfg(), port: channel.port1 }, [channel.port1]);
    worker.onmessage = (e) => { if (e.data.type === 'tick') onTick(e.data); };

    const node = new AudioWorkletNode(audioCtx, 'capture');
    node.port.postMessage({ port: channel.port2 }, [channel.port2]);
    const sink = audioCtx.createGain();
    sink.gain.value = 0;
    node.connect(sink).connect(audioCtx.destination);

    const gen = new URLSearchParams(location.search).get('gen');
    if (gen) {
      // Mode test : oscillateurs internes au lieu du micro (?gen=440.2,442.5).
      for (const f of gen.split(',').map(Number)) {
        const osc = audioCtx.createOscillator();
        osc.setPeriodicWave(reedWave(audioCtx));
        osc.frequency.value = f;
        const g = audioCtx.createGain();
        g.gain.value = 0.2;
        osc.connect(g).connect(node);
        osc.start();
      }
    } else {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: $('deviceSel').value ? { exact: $('deviceSel').value } : undefined,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          channelCount: 1,
        },
      });
      audioCtx.createMediaStreamSource(mediaStream).connect(node);
      await listDevices();
    }
    await audioCtx.resume();
    state.running = true;
    $('btnStart').textContent = '■ Arrêter';
    $('btnFreeze').disabled = false;
    const lat = ((audioCtx.baseLatency || 0) * 1000).toFixed(1);
    $('latencyInfo').textContent =
      `Échantillonnage ${audioCtx.sampleRate} Hz · latence de sortie ${lat} ms · capture par blocs de 512 (≈ ${(512000 / audioCtx.sampleRate).toFixed(0)} ms)`;
  } catch (err) {
    alert(`Impossible de démarrer l'audio : ${err.message}`);
    console.error(err);
  }
  $('btnStart').disabled = false;
}

function stopAudio() {
  stopTone();
  mediaStream?.getTracks().forEach((t) => t.stop());
  worker?.terminate();
  audioCtx?.close();
  audioCtx = null; worker = null; mediaStream = null;
  state.running = false;
  state.tick = null;
  $('btnStart').textContent = '▶ Démarrer';
  $('btnFreeze').disabled = true;
  $('convState').textContent = 'micro arrêté';
}

async function listDevices() {
  const devs = await navigator.mediaDevices.enumerateDevices();
  const sel = $('deviceSel');
  const cur = sel.value;
  sel.innerHTML = '';
  for (const d of devs.filter((d) => d.kind === 'audioinput')) {
    const o = document.createElement('option');
    o.value = d.deviceId;
    o.textContent = d.label || `Micro ${sel.length + 1}`;
    sel.appendChild(o);
  }
  if (cur) sel.value = cur;
}

function engineCfg() {
  return {
    a4: cfg.a4,
    temperament: cfg.temperament,
    transpose: cfg.transpose,
    calibrationPpm: cfg.calibrationPpm,
    mode: cfg.mode,
    register: cfg.register,
    manualNotes: cfg.manualNotes,
    response: cfg.response,
    beatCurve: cfg.beatCurve,
  };
}
function pushConfig() {
  saveCfg();
  worker?.postMessage({ type: 'config', cfg: engineCfg() });
  drawBeatCurve();
}

// ---- Réception des analyses --------------------------------------------------
function onTick(t) {
  if (state.frozen) return;
  state.tick = t;
  if (t.playedMidi === state.lastMidi) state.stableTicks++;
  else { state.stableTicks = 0; state.lastMidi = t.playedMidi; }

  // Enregistrement automatique quand la mesure est convergée et stable.
  if ($('autoRecord').checked && t.playedMidi != null && !t.quiet && state.stableTicks > 8
      && t.groups.length && t.groups.every((g) => g.fill >= 0.999)
      && t.groups.every((g) => g.voices.every((v) => v.tracked))) {
    if (report.record(t, cfg)) refreshReport();
  }
  updateVoicesTable(t);
  updateHeader(t);
}

function selectedVoice(t) {
  const want = $('gaugeVoice').value;
  let first = null;
  for (const g of t?.groups ?? []) {
    for (const v of g.voices) {
      if (!first && v.tracked) first = v;
      if (want && `${g.key}:${v.def.id}` === want && v.tracked) return v;
    }
  }
  return first;
}

function updateHeader(t) {
  const nn = $('noteName'), no = $('noteOct'), fv = $('freqVal'), cv = $('centsVal'), cs = $('convState');
  if (!t || t.playedMidi == null) {
    nn.textContent = '—'; no.textContent = ''; fv.textContent = '—'; cv.textContent = '—';
    cs.textContent = t?.quiet ? 'silence' : 'écoute…';
  } else {
    const lbl = noteLabel(t.playedMidi + (cfg.transpose || 0));
    nn.textContent = lbl.name;
    no.textContent = lbl.oct;
    const v = selectedVoice(t);
    if (v) {
      fv.textContent = v.fMeas.toFixed(v.fMeas < 100 ? 4 : 3);
      const c = v.dTargetCents;
      cv.textContent = (c >= 0 ? '+' : '') + c.toFixed(1);
      cv.style.color = Math.abs(c) < 1 ? 'var(--ok)' : Math.abs(c) < 5 ? 'var(--warn)' : 'var(--bad)';
    } else {
      fv.textContent = '—'; cv.textContent = '—';
    }
    const fill = Math.min(...t.groups.map((g) => g.fill));
    cs.textContent = t.quiet ? 'silence (mesure gelée)'
      : fill >= 0.999 ? 'convergé' : `convergence ${(fill * 100).toFixed(0)} %`;
  }
  $('levelBar').style.width = `${Math.min(100, Math.max(0, 100 + (20 * Math.log10((t?.level ?? 0) + 1e-9) + 10)))}%`;
}

// ---- Tableau des voix --------------------------------------------------------
function updateVoicesTable(t) {
  const tbody = $('voicesTable').querySelector('tbody');
  const sel = $('gaugeVoice');
  const rows = [];
  const opts = [];
  for (const g of t?.groups ?? []) {
    for (const v of g.voices) {
      const lbl = v.def.label || (v.def.fixedMidi != null ? noteLabel(v.def.fixedMidi + (cfg.transpose || 0)).full : 'anche');
      const note = noteLabel(v.midi + (cfg.transpose || 0)).full;
      const cls = (c) => (c == null ? 'dim' : Math.abs(c) < 1 ? 'ok' : Math.abs(c) < 5 ? 'warn' : 'bad');
      const fmt = (x, d = 2) => (x == null ? '—' : x.toFixed(d));
      rows.push(`<tr><td>${lbl}</td><td>${note}</td><td>${fmt(v.target, 3)}</td>
        <td>${v.tracked ? fmt(v.fMeas, 3) : '—'}</td>
        <td class="${cls(v.dTargetCents)}">${fmt(v.dTargetCents, 1)}</td>
        <td class="${cls(v.dTargetCents)}">${fmt(v.dHz, 3)}</td>
        <td>${fmt(v.beatMeas)}</td><td>${v.beat ? v.beat.toFixed(2) : '—'}</td></tr>`);
      opts.push({ key: `${t.groups.find((gg) => gg === g).key}:${v.def.id}`, label: `${lbl} (${note})` });
    }
  }
  tbody.innerHTML = rows.join('') || '<tr><td colspan="8" class="dim">jouez une note…</td></tr>';
  // Ne reconstruit le sélecteur de voix que s'il change.
  const sig = opts.map((o) => o.key).join(',');
  if (sel.dataset.sig !== sig) {
    const cur = sel.value;
    sel.innerHTML = '';
    for (const o of opts) {
      const el = document.createElement('option');
      el.value = o.key; el.textContent = o.label;
      sel.appendChild(el);
    }
    sel.dataset.sig = sig;
    if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
  }
}

// ---- Dessins -----------------------------------------------------------------
function drawGauge() {
  const cv = $('gauge'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const range = Number($('gaugeRange').value);
  $('gaugeRangeLbl').textContent = `±${range} ¢`;
  const cx = W / 2, cy = H - 18, R = H - 44;
  const a0 = Math.PI * 1.25, a1 = Math.PI * 1.75;
  const angFor = (c) => a0 + ((clamp(c, -range, range) + range) / (2 * range)) * (a1 - a0);

  // Zones colorées.
  const zones = [[-range, -range * 0.2, '#5b2523'], [-range * 0.2, range * 0.2, '#1d4a33'], [range * 0.2, range, '#5b2523']];
  for (const [z0, z1, col] of zones) {
    ctx.beginPath();
    ctx.strokeStyle = col;
    ctx.lineWidth = 16;
    ctx.arc(cx, cy, R, angFor(z0), angFor(z1));
    ctx.stroke();
  }
  // Graduations.
  ctx.fillStyle = '#8494a9';
  ctx.font = '11px system-ui';
  ctx.textAlign = 'center';
  const step = range <= 5 ? 1 : range <= 10 ? 2 : range <= 25 ? 5 : 10;
  for (let c = -range; c <= range; c += step) {
    const a = angFor(c);
    const x1 = cx + Math.cos(a) * (R - 12), y1 = cy + Math.sin(a) * (R - 12);
    const x2 = cx + Math.cos(a) * (R + 10), y2 = cy + Math.sin(a) * (R + 10);
    ctx.strokeStyle = c === 0 ? '#dde5ef' : '#44536a';
    ctx.lineWidth = c === 0 ? 2 : 1;
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    ctx.fillText(String(c), cx + Math.cos(a) * (R + 24), cy + Math.sin(a) * (R + 24) + 4);
  }
  // Aiguille.
  const v = selectedVoice(state.tick);
  const target = v?.dTargetCents;
  if (target != null) {
    state.smoothCents = state.smoothCents == null ? target : state.smoothCents + 0.35 * (target - state.smoothCents);
    const a = angFor(state.smoothCents);
    ctx.strokeStyle = Math.abs(target) < 1 ? '#46d68c' : '#f0b943';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(a) * (R - 20), cy + Math.sin(a) * (R - 20));
    ctx.stroke();
    ctx.font = 'bold 20px var(--mono), monospace';
    ctx.fillStyle = '#dde5ef';
    ctx.fillText((target >= 0 ? '+' : '') + target.toFixed(1) + ' ¢', cx, cy - R / 2);
  }
  ctx.beginPath();
  ctx.fillStyle = '#4fc3f7';
  ctx.arc(cx, cy, 5, 0, 7);
  ctx.fill();
}

function drawStrobe(dt) {
  const cv = $('strobe'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const v = selectedVoice(state.tick);
  if (v?.dTargetCents != null && !state.frozen) {
    // La bande dérive à une vitesse proportionnelle à l'écart (comme un
    // stroboscope mécanique) : immobile = juste.
    state.strobePhase += v.dTargetCents * dt * 60;
  }
  ctx.clearRect(0, 0, W, H);
  const period = 46;
  const off = ((state.strobePhase % period) + period) % period;
  for (let x = -period; x < W + period; x += period) {
    const g = ctx.createLinearGradient(x + off, 0, x + off + period, 0);
    g.addColorStop(0, '#10141a');
    g.addColorStop(0.5, v?.tracked ? (Math.abs(v.dTargetCents) < 1 ? '#2b8f5f' : '#3a6d8f') : '#232a35');
    g.addColorStop(1, '#10141a');
    ctx.fillStyle = g;
    ctx.fillRect(x + off, 8, period, H - 16);
  }
}

function drawSpectrum() {
  const cv = $('spectrum'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const spec = state.tick?.coarseSpectrum;
  // Repères d'octaves (Do1..Do9) sur échelle log 20 Hz → 10 kHz.
  ctx.font = '10px system-ui';
  ctx.textAlign = 'left';
  for (let oct = 1; oct <= 9; oct++) {
    const f = midiToFreq(12 * oct + 12, cfg);
    if (f < 20 || f > 10000) continue;
    const x = (Math.log(f / 20) / Math.log(500)) * W;
    ctx.strokeStyle = '#232a35';
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    ctx.fillStyle = '#5c6b80';
    ctx.fillText(`Do${oct}`, x + 3, 12);
  }
  if (!spec) return;
  let max = 1e-9;
  for (let i = 0; i < spec.length; i++) if (spec[i] > max) max = spec[i];
  ctx.beginPath();
  ctx.strokeStyle = '#4fc3f7';
  ctx.lineWidth = 1.2;
  for (let i = 0; i < spec.length; i++) {
    const db = 20 * Math.log10((spec[i] + 1e-12) / max);
    const y = H - 4 - Math.max(0, (db + 80) / 80) * (H - 12);
    const x = (i / spec.length) * W;
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.stroke();
}

function drawZoom() {
  const cv = $('zoom'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const groups = state.tick?.groups?.filter((g) => g.spectrum) ?? [];
  if (!groups.length) {
    ctx.fillStyle = '#5c6b80';
    ctx.font = '13px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText('jouez une note pour voir chaque anche…', W / 2, H / 2);
    return;
  }
  const rowH = H / groups.length;
  const span = 25; // ± Hz affichés (à la fondamentale)
  groups.forEach((g, gi) => {
    const y0 = gi * rowH;
    const k = g.kTrack || 1;
    const spec = g.spectrum;
    const binHz = g.srd / g.W;
    let max = 1e-9;
    for (let i = 0; i < spec.length; i++) if (spec[i] > max) max = spec[i];
    // Axe.
    ctx.strokeStyle = '#232a35';
    ctx.beginPath(); ctx.moveTo(0, y0 + rowH - 14); ctx.lineTo(W, y0 + rowH - 14); ctx.stroke();
    ctx.fillStyle = '#5c6b80';
    ctx.font = '10px system-ui';
    ctx.textAlign = 'center';
    for (let hz = -span; hz <= span; hz += 5) {
      const x = ((hz + span) / (2 * span)) * W;
      ctx.fillText(hz ? `${hz > 0 ? '+' : ''}${hz}` : `${g.center.toFixed(1)} Hz`, x, y0 + rowH - 3);
    }
    // Cibles (pointillés).
    for (const v of g.voices) {
      const dx = (v.target - g.center);
      if (Math.abs(dx) > span) continue;
      const x = ((dx + span) / (2 * span)) * W;
      ctx.strokeStyle = '#f0b943';
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(x, y0 + 14); ctx.lineTo(x, y0 + rowH - 14); ctx.stroke();
      ctx.setLineDash([]);
    }
    // Spectre zoom (bande de base recentrée, axe ramené à la fondamentale).
    ctx.beginPath();
    ctx.strokeStyle = '#46d68c';
    ctx.lineWidth = 1.4;
    let started = false;
    for (let px = 0; px < W; px++) {
      const hz = (px / W) * 2 * span - span;      // écart à la fondamentale
      const offTracker = hz * k;                  // écart dans la bande du traqueur
      let bin = Math.round(offTracker / binHz);
      if (bin < 0) bin += g.W;
      if (bin < 0 || bin >= g.W) { started = false; continue; }
      const m = spec[bin] / max;
      const yv = y0 + rowH - 16 - m * (rowH - 36);
      started ? ctx.lineTo(px, yv) : ctx.moveTo(px, yv);
      started = true;
    }
    ctx.stroke();
    // Étiquettes des voix mesurées.
    ctx.fillStyle = '#dde5ef';
    ctx.font = '11px system-ui';
    for (const v of g.voices) {
      if (!v.tracked) continue;
      const dx = v.fMeas - g.center;
      if (Math.abs(dx) > span) continue;
      const x = ((dx + span) / (2 * span)) * W;
      ctx.fillText(`${v.def.label || noteLabel(v.midi + (cfg.transpose || 0)).full} ${v.dTargetCents >= 0 ? '+' : ''}${v.dTargetCents.toFixed(1)}¢`, x, y0 + 12);
    }
    if (g.kTrack > 1) {
      ctx.fillStyle = '#5c6b80';
      ctx.textAlign = 'left';
      ctx.fillText(`mesure sur le partiel ${g.kTrack}`, 6, y0 + 12);
      ctx.textAlign = 'center';
    }
  });
}

function drawBeatCurve() {
  const cv = $('beatCurve'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const c = cfg.beatCurve;
  const m0 = 36, m1 = 108;
  let maxB = 0.1;
  for (let m = m0; m <= m1; m++) maxB = Math.max(maxB, beatTarget(m, c));
  ctx.beginPath();
  ctx.strokeStyle = '#4fc3f7';
  for (let m = m0; m <= m1; m++) {
    const x = ((m - m0) / (m1 - m0)) * W;
    const y = H - 12 - (beatTarget(m, c) / maxB) * (H - 24);
    m === m0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  // Écrasements.
  ctx.fillStyle = '#f0b943';
  for (const [m, b] of Object.entries(c.overrides || {})) {
    const x = ((m - m0) / (m1 - m0)) * W;
    const y = H - 12 - (Number(b) / maxB) * (H - 24);
    ctx.beginPath(); ctx.arc(x, y, 3, 0, 7); ctx.fill();
  }
  ctx.fillStyle = '#5c6b80';
  ctx.font = '10px system-ui';
  ctx.textAlign = 'left';
  ctx.fillText(noteLabel(m0).full, 2, H - 2);
  ctx.textAlign = 'right';
  ctx.fillText(noteLabel(m1).full, W - 2, H - 2);
  ctx.fillText(`${maxB.toFixed(1)} Hz`, W - 2, 10);
}

function clamp(x, a, b) { return Math.min(b, Math.max(a, x)); }

function renderLoop(now) {
  const dt = Math.min(0.1, (now - state.lastDraw) / 1000);
  state.lastDraw = now;
  if (!state.frozen) {
    drawGauge();
    drawSpectrum();
    drawZoom();
  }
  drawStrobe(dt);
  requestAnimationFrame(renderLoop);
}

// ---- Générateur de sons -------------------------------------------------------
function reedWave(ctx) {
  // Timbre d'anche libre : riche en harmoniques, décroissance douce.
  const n = 16;
  const re = new Float32Array(n + 1);
  const im = new Float32Array(n + 1);
  for (let k = 1; k <= n; k++) im[k] = 1 / Math.pow(k, 1.3);
  return ctx.createPeriodicWave(re, im);
}

function toggleTone() {
  if (state.toneOn) { stopTone(); return; }
  if (!audioCtx) { alert("Démarrez d'abord l'audio."); return; }
  const t = state.tick;
  const midi = t?.playedMidi ?? 69;
  const targets = [];
  if (cfg.mode === 'register') {
    const preset = REGISTER_PRESETS[cfg.register] ?? REGISTER_PRESETS.M;
    for (const v of preset.voices) targets.push(voiceTargetFreq(midi, v, cfg).target);
  } else if (cfg.mode === 'manual' && cfg.manualNotes?.length) {
    for (const m of cfg.manualNotes) targets.push(midiToFreq(m, cfg));
  } else {
    targets.push(midiToFreq(midi, cfg));
  }
  const master = audioCtx.createGain();
  master.gain.value = Number($('toneVol').value) / 300;
  master.connect(audioCtx.destination);
  for (const f of targets) {
    const osc = audioCtx.createOscillator();
    osc.setPeriodicWave(reedWave(audioCtx));
    osc.frequency.value = f;
    osc.connect(master);
    osc.start();
    toneNodes.push(osc);
  }
  toneNodes.push(master);
  state.toneOn = true;
  $('btnTone').classList.add('active');
  $('btnTone').textContent = '■ Arrêter le son';
}

function stopTone() {
  for (const n of toneNodes) { try { n.stop?.(); n.disconnect(); } catch { /* déjà arrêté */ } }
  toneNodes = [];
  state.toneOn = false;
  $('btnTone').classList.remove('active');
  $('btnTone').textContent = '♪ Jouer la cible';
}

// ---- Rapport -------------------------------------------------------------------
function refreshReport() {
  report.renderTable($('reportTable'), cfg, (midi, val) => {
    if (val === '' || val == null) delete cfg.beatCurve.overrides[midi];
    else cfg.beatCurve.overrides[midi] = Number(val);
    pushConfig();
    refreshReport();
  });
  $('reportCount').textContent = `${report.rows.size} mesures enregistrées`;
}

function download(name, text, mime) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: mime }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- Liaison des contrôles -------------------------------------------------------
function bindControls() {
  // Sélecteurs statiques.
  const tSel = $('temperament');
  for (const [k, v] of Object.entries(TEMPERAMENTS)) {
    const o = document.createElement('option');
    o.value = k; o.textContent = v.name;
    tSel.appendChild(o);
  }
  const rSel = $('register');
  for (const [k, v] of Object.entries(REGISTER_PRESETS)) {
    const o = document.createElement('option');
    o.value = k; o.textContent = v.name;
    rSel.appendChild(o);
  }
  const trSel = $('transpose');
  const names = ['Do (ut, réel)', 'Réb', 'Ré', 'Mib', 'Mi', 'Fa', 'Solb', 'Sol', 'Lab', 'La', 'Sib', 'Si'];
  for (let s = -6; s <= 6; s++) {
    const o = document.createElement('option');
    o.value = s;
    o.textContent = s === 0 ? names[0] : `${s > 0 ? '+' : ''}${s} demi-tons (${names[((s % 12) + 12) % 12]})`;
    trSel.appendChild(o);
  }

  // Valeurs initiales.
  $('a4').value = cfg.a4;
  tSel.value = cfg.temperament;
  trSel.value = String(cfg.transpose);
  $('calib').value = cfg.calibrationPpm;
  $('mode').value = cfg.mode;
  rSel.value = cfg.register;
  $('response').value = cfg.response;
  $('bLow').value = cfg.beatCurve.bLow;
  $('bHigh').value = cfg.beatCurve.bHigh;
  $('instrName').value = report.name;
  if (cfg.manualNotes) $('manualNotes').value = cfg.manualNotes.map((m) => noteLabel(m).full).join(' ');
  updateModeVisibility();

  $('btnStart').onclick = () => (state.running ? stopAudio() : startAudio());
  $('btnFreeze').onclick = () => {
    state.frozen = !state.frozen;
    $('btnFreeze').classList.toggle('active', state.frozen);
    $('btnFreeze').textContent = state.frozen ? '❄ Gelé' : '❄ Geler';
  };
  $('a4').onchange = () => { cfg.a4 = clamp(Number($('a4').value) || 440, 430, 450); $('a4').value = cfg.a4; pushConfig(); };
  tSel.onchange = () => { cfg.temperament = tSel.value; pushConfig(); };
  trSel.onchange = () => { cfg.transpose = Number(trSel.value); pushConfig(); };
  $('calib').onchange = () => { cfg.calibrationPpm = Number($('calib').value) || 0; pushConfig(); };
  $('mode').onchange = () => { cfg.mode = $('mode').value; updateModeVisibility(); pushConfig(); };
  rSel.onchange = () => { cfg.register = rSel.value; pushConfig(); };
  $('response').onchange = () => { cfg.response = $('response').value; pushConfig(); };
  $('applyManual').onclick = applyManual;
  $('manualNotes').onkeydown = (e) => { if (e.key === 'Enter') applyManual(); };
  $('bLow').onchange = () => { cfg.beatCurve.bLow = Number($('bLow').value) || 0.8; pushConfig(); };
  $('bHigh').onchange = () => { cfg.beatCurve.bHigh = Number($('bHigh').value) || 3.0; pushConfig(); };
  $('deviceSel').onchange = () => { if (state.running) { stopAudio(); startAudio(); } };
  $('btnTone').onclick = toggleTone;
  $('toneVol').oninput = () => {
    const m = toneNodes[toneNodes.length - 1];
    if (state.toneOn && m?.gain) m.gain.value = Number($('toneVol').value) / 300;
  };

  $('instrName').onchange = () => { report.name = $('instrName').value; report.save(); };
  $('btnRecord').onclick = () => {
    const n = report.record(state.tick, cfg);
    if (!n) alert('Aucune mesure convergée à enregistrer — laissez sonner la note jusqu\'à « convergé ».');
    refreshReport();
  };
  $('btnReport').onclick = () => {
    const w = window.open('', '_blank');
    w.document.write(report.printableHtml(cfg));
    w.document.close();
  };
  $('btnCsv').onclick = () => download(`rapport-${report.name || 'accordeon'}.csv`, report.toCsv(cfg), 'text/csv');
  $('btnSaveJson').onclick = () => download(`accordage-${report.name || 'accordeon'}.json`, report.toJson(cfg), 'application/json');
  $('btnLoadJson').onclick = () => {
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.accept = '.json';
    inp.onchange = async () => {
      try {
        report.fromJson(await inp.files[0].text(), cfg);
        $('instrName').value = report.name;
        pushConfig();
        refreshReport();
      } catch (e) { alert(`Chargement impossible : ${e.message}`); }
    };
    inp.click();
  };
  $('btnCopyBeats').onclick = () => {
    const n = report.copyBeatsTo(cfg.beatCurve);
    pushConfig();
    refreshReport();
    alert(`${n} battements copiés vers la liste cible.`);
  };
  $('btnClear').onclick = () => {
    if (confirm('Effacer toutes les mesures enregistrées ?')) { report.clear(); refreshReport(); }
  };
  $('aboutLink').onclick = (e) => { e.preventDefault(); $('aboutDlg').showModal(); };

  navigator.mediaDevices?.enumerateDevices?.().then(listDevices).catch(() => {});
}

function applyManual() {
  const notes = parseNoteList($('manualNotes').value);
  if (!notes) { alert('Notes non reconnues. Exemple : Do4 Mi4 Sol4 ou C4 E4 G4'); return; }
  // La saisie est en notes écrites : conversion vers les hauteurs réelles.
  cfg.manualNotes = notes.map((m) => m - (cfg.transpose || 0));
  pushConfig();
}

function updateModeVisibility() {
  $('modeRegister').classList.toggle('hidden', cfg.mode !== 'register');
  $('modeManual').classList.toggle('hidden', cfg.mode !== 'manual');
}

// ---- Démarrage -----------------------------------------------------------------
bindControls();
drawBeatCurve();
refreshReport();
requestAnimationFrame(renderLoop);
if (new URLSearchParams(location.search).get('gen')) startAudio();
