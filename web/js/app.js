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

const HISTORY_SPAN = 15; // secondes de courbe affichées
const PALETTE = ['#4fc3f7', '#46d68c', '#f0b943', '#f0625d', '#b58cf0', '#7fd8d0'];

const state = {
  running: false,
  frozen: false,
  tick: null,           // dernier résultat moteur
  history: [],          // [{t, midi, vals: {clé de voix → {c, f}}}]
  voiceLabels: new Map(), // clé de voix → étiquette
  mouse: null,          // position du curseur sur la courbe (px canvas)
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

  // Historique pour la courbe d'accordage.
  const vals = {};
  for (const g of t.groups) {
    for (const v of g.voices) {
      const key = `${g.key}:${v.def.id}`;
      state.voiceLabels.set(key,
        v.def.label || (v.def.fixedMidi != null ? noteLabel(v.def.fixedMidi + (cfg.transpose || 0)).full : 'anche'));
      if (v.tracked && !t.quiet) vals[key] = { c: v.dTargetCents, f: v.fMeas };
    }
  }
  state.history.push({ t: t.time, midi: t.playedMidi, vals });
  while (state.history.length && state.history[0].t < t.time - HISTORY_SPAN - 0.5) {
    state.history.shift();
  }

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
// Courbe d'accordage : écart en cents de chaque anche au fil du temps
// (fenêtre glissante de 15 s), marqueurs de changement de note, lecture au
// survol. C'est l'outil de lecture des transitoires d'attaque, des dérives
// et de la stabilité d'une anche.
function drawPitchCurve() {
  const cv = $('pitchCurve'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const range = Number($('gaugeRange').value);
  $('curveRangeLbl').textContent = `±${range} ¢ · ${HISTORY_SPAN} s`;
  const pad = { l: 36, r: 8, t: 18, b: 18 };
  const plotW = W - pad.l - pad.r, plotH = H - pad.t - pad.b;
  const yFor = (c) => pad.t + (1 - (clamp(c, -range, range) + range) / (2 * range)) * plotH;

  // Grille verticale (cents).
  ctx.font = '10px system-ui';
  ctx.textAlign = 'right';
  const step = range <= 5 ? 1 : range <= 10 ? 2 : range <= 25 ? 5 : 10;
  for (let c = -range; c <= range; c += step) {
    const y = yFor(c);
    ctx.strokeStyle = c === 0 ? '#44536a' : '#1e242e';
    ctx.lineWidth = c === 0 ? 1.5 : 1;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = '#5c6b80';
    ctx.fillText(String(c), pad.l - 5, y + 3);
  }

  const hist = state.history;
  const T = hist.length ? hist[hist.length - 1].t : 0;
  const xFor = (t) => pad.l + plotW * (1 - (T - t) / HISTORY_SPAN);

  // Grille horizontale (secondes).
  ctx.textAlign = 'center';
  for (let s = 0; s <= HISTORY_SPAN; s += 5) {
    const x = pad.l + plotW * (1 - s / HISTORY_SPAN);
    ctx.strokeStyle = '#1e242e';
    ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
    ctx.fillStyle = '#5c6b80';
    ctx.fillText(s ? `−${s} s` : '0', x, H - 5);
  }

  if (!hist.length) {
    ctx.fillStyle = '#5c6b80';
    ctx.font = '13px system-ui';
    ctx.fillText('jouez une note…', W / 2, H / 2);
    return;
  }

  // Marqueurs de changement de note (transitions).
  ctx.textAlign = 'left';
  ctx.font = '10px system-ui';
  for (let i = 1; i < hist.length; i++) {
    if (hist[i].midi !== hist[i - 1].midi && hist[i].midi != null) {
      const x = xFor(hist[i].t);
      if (x < pad.l) continue;
      ctx.strokeStyle = '#3a4a60';
      ctx.setLineDash([2, 4]);
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#8494a9';
      ctx.fillText(noteLabel(hist[i].midi + (cfg.transpose || 0)).full, x + 3, pad.t - 5);
    }
  }

  // Traces (une par anche), la voix suivie en gras.
  const keys = [];
  for (const e of hist) {
    for (const k of Object.keys(e.vals)) if (!keys.includes(k)) keys.push(k);
  }
  const selKey = $('gaugeVoice').value;
  let legendX = pad.l + 4;
  keys.forEach((k, ki) => {
    const col = PALETTE[ki % PALETTE.length];
    ctx.strokeStyle = col;
    ctx.lineWidth = k === selKey ? 2.4 : 1.3;
    ctx.beginPath();
    let started = false, prevT = null;
    for (const e of hist) {
      const v = e.vals[k];
      if (!v) { started = false; continue; }
      if (prevT != null && e.t - prevT > 0.6) started = false;
      const x = xFor(e.t);
      prevT = e.t;
      if (x < pad.l) continue;
      const y = yFor(v.c);
      started ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      started = true;
    }
    ctx.stroke();
    // Légende.
    const lbl = state.voiceLabels.get(k) || k;
    ctx.fillStyle = col;
    ctx.fillRect(legendX, 4, 8, 8);
    ctx.fillStyle = '#8494a9';
    ctx.fillText(lbl, legendX + 11, 12);
    legendX += 20 + ctx.measureText(lbl).width;
  });

  // Curseur de lecture au survol (surtout utile en mode gelé).
  if (state.mouse && state.mouse.x >= pad.l && state.mouse.x <= W - pad.r) {
    const tCur = T - HISTORY_SPAN * (1 - (state.mouse.x - pad.l) / plotW);
    let best = null;
    for (const e of hist) {
      if (!best || Math.abs(e.t - tCur) < Math.abs(best.t - tCur)) best = e;
    }
    if (best) {
      const x = xFor(best.t);
      ctx.strokeStyle = '#8494a9';
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
      const parts = [`−${(T - best.t).toFixed(1)} s`];
      for (const k of keys) {
        const v = best.vals[k];
        if (v) parts.push(`${state.voiceLabels.get(k) || k} ${v.c >= 0 ? '+' : ''}${v.c.toFixed(1)}¢ (${v.f.toFixed(3)} Hz)`);
      }
      ctx.font = '11px system-ui';
      const text = parts.join('   ');
      const tw = ctx.measureText(text).width + 10;
      const bx = clamp(x - tw / 2, pad.l, W - pad.r - tw);
      ctx.fillStyle = 'rgba(16,20,26,0.92)';
      ctx.fillRect(bx, pad.t + 2, tw, 16);
      ctx.fillStyle = '#dde5ef';
      ctx.textAlign = 'left';
      ctx.fillText(text, bx + 5, pad.t + 14);
    }
  }
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
  // La courbe est redessinée même gelée : l'historique n'avance plus mais le
  // curseur de lecture doit suivre la souris.
  drawPitchCurve();
  if (!state.frozen) {
    drawSpectrum();
    drawZoom();
  }
  drawStrobe(dt);
  requestAnimationFrame(renderLoop);
}

function toggleFreeze() {
  if (!state.running) return;
  state.frozen = !state.frozen;
  $('btnFreeze').classList.toggle('active', state.frozen);
  $('btnFreeze').textContent = state.frozen ? '❄ Gelé' : '❄ Geler';
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
  $('btnFreeze').onclick = toggleFreeze;
  const curve = $('pitchCurve');
  curve.addEventListener('mousemove', (e) => {
    const r = curve.getBoundingClientRect();
    state.mouse = {
      x: ((e.clientX - r.left) * curve.width) / r.width,
      y: ((e.clientY - r.top) * curve.height) / r.height,
    };
  });
  curve.addEventListener('mouseleave', () => { state.mouse = null; });
  curve.addEventListener('click', toggleFreeze);
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
