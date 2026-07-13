// Application principale : capture audio basse latence, liaison avec le
// Worker DSP, affichages (aiguille, stroboscope, spectres), contrôles et
// module rapport.

import {
  TEMPERAMENTS, REGISTER_PRESETS, noteLabel, parseNoteList,
  midiToFreq, voiceTargetFreq, beatTarget, centsClass, overlappingAllan,
} from './music.js';
import { Report } from './report.js';

const $ = (id) => document.getElementById(id);

// ---- État ------------------------------------------------------------------
const CFG_KEY = 'aal.cfg';
const cfg = Object.assign({
  _v: 2, // version du schéma de configuration mémorisée (migrations)
  a4: 440,
  temperament: 'equal',
  transpose: 0,
  calibrationPpm: 0,
  mode: 'auto',
  register: 'MM',
  manualNotes: null,
  trackHarmonics: 0,
  trackSub: false,
  lockNote: null,
  gateDb: -70,
  bellows: 'T',
  tolCents: 1,
  autoFreeze: false, // désactivé par défaut : surprenant pour un premier essai
  readout: null,        // clés de voix affichées en lecture numérique (null = toutes)
  response: 'normal',
  beatCurve: { midiLow: 48, bLow: 0.8, midiHigh: 96, bHigh: 3.0, overrides: {} },
}, loadCfg());

function loadCfg() {
  try {
    const stored = JSON.parse(localStorage.getItem(CFG_KEY)) || {};
    // Migration v2 : autoFreeze était activé par défaut dans une version
    // précédente — les profils mémorisés avant le changement repassent au
    // nouveau défaut (désactivé), sinon le gel « surprise » persiste.
    if (!stored._v || stored._v < 2) {
      delete stored.autoFreeze;
      stored._v = 2;
    }
    return stored;
  } catch { return {}; }
}
function saveCfg() {
  try { localStorage.setItem(CFG_KEY, JSON.stringify(cfg)); } catch { /* ignore */ }
}

const HISTORY_SPAN = 15;  // secondes de courbe affichées
const HISTORY_KEEP = 120; // secondes conservées (export CSV, diagramme de phase)

// ---- Thème (clair par défaut, sombre en option) ----------------------------
// Toutes les couleurs — y compris celles dessinées à la main sur les canvas —
// viennent des variables CSS : un seul jeu de couleurs à maintenir par thème.
const THEME_KEY = 'aal.theme';
let themeCache = null;
function theme() {
  if (!themeCache) {
    const s = getComputedStyle(document.documentElement);
    const v = (name) => s.getPropertyValue(name).trim();
    themeCache = {
      text: v('--text'), dim: v('--dim'), dim2: v('--dim2'),
      accent: v('--accent'), accentMuted: v('--accent-muted'),
      ok: v('--ok'), okStrong: v('--ok-strong'), warn: v('--warn'), bad: v('--bad'),
      canvasBg: v('--canvas-bg'), grid: v('--grid'), gridStrong: v('--grid-strong'),
      markerLine: v('--marker-line'), panel2: v('--panel2'),
      palette: [v('--accent'), v('--ok'), v('--warn'), v('--bad'),
        v('--v5'), v('--v6'), v('--v7'), v('--v8'), v('--v9')],
    };
  }
  return themeCache;
}
function currentTheme() {
  return document.documentElement.getAttribute('data-theme') || 'light';
}
function applyTheme(name) {
  document.documentElement.setAttribute('data-theme', name);
  try { localStorage.setItem(THEME_KEY, name); } catch { /* ignore */ }
  themeCache = null;
  markAllDirty();
  const b = $('themeToggle');
  if (b) { b.textContent = name === 'dark' ? '☀' : '🌙'; b.title = name === 'dark' ? 'Thème clair' : 'Thème sombre'; }
  // Barre système (Android/PWA installée) assortie au bandeau du thème actif.
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', name === 'dark' ? '#171c24' : '#f5f8fb');
  // Les cartes de lecture numérique fixent leurs couleurs en ligne (pas de
  // dépendance CSS) : sans ceci elles garderaient les couleurs de l'ancien
  // thème jusqu'à la prochaine mesure, voire indéfiniment si à l'arrêt.
  if (typeof updateReadout === 'function' && $('readoutCards')) updateReadout(state.tick);
}
function toggleTheme() { applyTheme(currentTheme() === 'dark' ? 'light' : 'dark'); }

// Couleur stable par voix : indexée par ordre de première apparition, pour
// que la courbe, les chips et les cartes de lecture partagent les couleurs.
const voiceOrder = [];
function colorFor(key) {
  let i = voiceOrder.indexOf(key);
  if (i < 0) { i = voiceOrder.length; voiceOrder.push(key); }
  const p = theme().palette;
  return p[i % p.length];
}

// Couleur hex '#rrggbb' → rgba avec transparence (pour estomper les notes
// passées sur la courbe).
function hexA(hex, a) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

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
  attacks: [],          // dernières attaques mesurées
  lastAttackT: null,
  autoFrozen: false,    // le gel courant vient du gel automatique
  frozenAtTime: 0,      // horloge moteur au moment du gel
  lastUnfreezeT: 0,     // horloge moteur au dernier dégel (délai de réarmement)
  curveCache: null,     // fenêtre visible et clés, recalculées par tick
  centerEMA: null,      // centre lissé de l'échelle auto de la courbe
  phaseCache: null,
  dspMs: 0,             // charge DSP lissée (ms par période d'analyse)
  lastSpectrum: null,   // dernier spectre large bande reçu (gardé en silence)
  // Rendu à la demande : chaque vue n'est redessinée que si ses données ont
  // changé (tick ~12 Hz, souris, réglage) ET si son onglet est visible.
  // Redessiner à 60 fps des canvas cachés ou inchangés chargeait le thread
  // principal pour rien — fluidité tactile et batterie sur mobile.
  curveDirty: true,
  phaseDirty: true,
  specDirty: true,
  zoomDirty: true,
  allanDirty: true,
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
      // Exposés sur window.__gen pour pouvoir simuler des changements de
      // note dans les tests de bout en bout.
      window.__gen = [];
      window.__genGain = [];
      for (const f of gen.split(',').map(Number)) {
        const osc = audioCtx.createOscillator();
        osc.setPeriodicWave(reedWave(audioCtx));
        osc.frequency.value = f;
        const g = audioCtx.createGain();
        g.gain.value = 0.2;
        osc.connect(g).connect(node);
        osc.start();
        window.__gen.push(osc);
        window.__genGain.push(g);
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
    $('btnLock').disabled = false;
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
  markAllDirty();
  $('btnStart').textContent = '▶ Démarrer';
  $('btnFreeze').disabled = true;
  $('btnLock').disabled = true;
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

// Le moteur reçoit la configuration complète et ignore les clés purement UI :
// une seule liste de champs à maintenir (les valeurs par défaut ci-dessus).
function engineCfg() {
  return { ...cfg };
}
function pushConfig() {
  saveCfg();
  worker?.postMessage({ type: 'config', cfg: engineCfg() });
  drawBeatCurve();
}

// ---- Réception des analyses --------------------------------------------------
function onTick(t) {
  if (state.frozen) {
    // Reprise automatique du gel auto : nouvelle attaque (soufflet remis en
    // pression) OU changement de note détecté par le moteur — indispensable
    // en jeu lié, où il n'y a aucun silence entre deux notes, donc jamais
    // d'« attaque » au sens de l'enveloppe.
    const newAttack = t.attack && t.attack.t > state.frozenAtTime;
    const newNote = t.playedMidi != null && t.playedMidi !== state.lastMidi;
    if (state.autoFrozen && (newAttack || newNote)) {
      state.lastUnfreezeT = t.time;
      setFrozen(false);
    } else {
      return;
    }
  }
  state.tick = t;
  state.curveCache = null;
  state.phaseCache = null;
  markAllDirty();
  if (t.coarseSpectrum) state.lastSpectrum = t.coarseSpectrum;
  state.dspMs = state.dspMs * 0.9 + (t.dspMs || 0) * 0.1;
  if (t.playedMidi === state.lastMidi) {
    state.stableTicks++;
  } else {
    state.stableTicks = 0;
    state.lastMidi = t.playedMidi;
    refreshReport(); // met à jour la note courante dans la grille de progression
  }

  // Historique pour la courbe, le diagramme de phase et l'export CSV.
  // Sous le seuil d'intensité, l'horloge se gèle : rien n'est ajouté, le
  // temps affiché s'arrête avec la dernière mesure.
  if (!t.quiet) {
    const vals = {};
    for (const g of t.groups) {
      for (const v of g.voices) {
        const key = `${g.key}:${v.def.id}`;
        state.voiceLabels.set(key,
          v.def.label || (v.def.fixedMidi != null ? noteLabel(v.def.fixedMidi + (cfg.transpose || 0)).full : 'anche'));
        if (v.tracked) vals[key] = { c: v.dTargetCents, f: v.fMeas, a: v.amp };
      }
    }
    state.history.push({
      t: t.time,
      midi: t.playedMidi,
      vals,
      // Paire (écart rapide, intensité) pour la caractéristique f(I).
      fast: t.f0Cents != null
        ? { c: t.f0Cents, db: 20 * Math.log10(t.level + 1e-9) }
        : null,
    });
    while (state.history.length && state.history[0].t < t.time - HISTORY_KEEP) {
      state.history.shift();
    }
  }

  // Temps de réponse de l'anche (attaques mesurées par le moteur).
  if (t.attack && t.attack.t !== state.lastAttackT) {
    state.lastAttackT = t.attack.t;
    state.attacks.unshift(t.attack);
    state.attacks.length = Math.min(state.attacks.length, 6);
    const lbl = t.attack.midi != null ? noteLabel(t.attack.midi + (cfg.transpose || 0)).full : '?';
    const sig = t.attack.sigma != null ? ` · σ ≈ ${t.attack.sigma.toFixed(0)} s⁻¹` : '';
    $('attackInfo').innerHTML = `Temps de réponse de l'anche : <b>${t.attack.riseMs.toFixed(0)} ms</b> (10→90 %, ${lbl})${sig}`;
    $('attackList').innerHTML = state.attacks
      .map((a) => `<li>${a.midi != null ? noteLabel(a.midi + (cfg.transpose || 0)).full : '?'} — ${a.riseMs.toFixed(0)} ms`
        + `${a.sigma != null ? ` · σ ${a.sigma.toFixed(0)} s⁻¹` : ''} · ${a.steadyDb.toFixed(0)} dB</li>`)
      .join('');
  }

  // Enregistrement automatique quand la mesure est convergée et stable.
  if ($('autoRecord').checked && t.playedMidi != null && !t.quiet && state.stableTicks > 8
      && t.groups.length && t.groups.every((g) => g.fill >= 0.999)
      && t.groups.every((g) => g.voices.every((v) => v.tracked || g.isSub))) {
    if (report.record(t, cfg, cfg.bellows)) { refreshReport(); beep(1318, 0.05); }
  }
  updateVoicesTable(t);
  updateReadout(t);
  updateHeader(t);

  // Gel automatique « quand c'est lisible » : mesure convergée, stable et
  // toutes les anches suivies → l'écran se fige, on peut lâcher le soufflet
  // et retourner la caisse. Le témoin reste affiché. Le délai de réarmement
  // après un dégel évite le cycle gel→dégel→regel immédiat qui n'ajoutait
  // qu'un ou deux points à la courbe par bouffée (courbe « figée », valeurs
  // de début de convergence aberrantes).
  if (cfg.autoFreeze && !state.frozen && !t.quiet && t.playedMidi != null
      && state.stableTicks > 10 && t.groups.length
      && t.time - (state.lastUnfreezeT || 0) > 3
      && t.groups.every((g) => g.fill >= 0.999)
      && t.groups.every((g) => g.isSub || g.voices.every((v) => v.tracked))) {
    state.frozenAtTime = t.time;
    setFrozen(true, true);
    beep(880, 0.06);
  }

  if ((state.stableTicks % 12) === 0) {
    $('dspLoad').textContent =
      `Charge DSP : ${state.dspMs.toFixed(1)} ms par période d'analyse de 85 ms (${(state.dspMs / 85 * 100).toFixed(0)} % d'un cœur)`;
  }
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
  updateVerdict(t);
  $('levelBar').style.width = `${Math.min(100, Math.max(0, 100 + (20 * Math.log10((t?.level ?? 0) + 1e-9) + 10)))}%`;
}

// Témoin d'accordage de la voix suivie : vert = dans la tolérance (passer à
// l'anche suivante), orange « ↑ monter » / « ↓ descendre » sinon. C'est le
// signal que le professionnel lit d'un coup d'œil depuis l'établi.
function updateVerdict(t) {
  const el = $('verdict');
  const v = selectedVoice(t);
  el.classList.remove('v-ok', 'v-up', 'v-down');
  if (!v || v.dTargetCents == null || (t && t.playedMidi == null)) {
    el.textContent = '—';
    return;
  }
  const c = v.dTargetCents;
  const tol = cfg.tolCents;
  if (Math.abs(c) <= tol) {
    el.textContent = '✔ OK';
    el.classList.add('v-ok');
  } else if (c < 0) {
    el.textContent = `↑ +${(-c).toFixed(1)} ¢`;
    el.classList.add('v-up');
  } else {
    el.textContent = `↓ −${c.toFixed(1)} ¢`;
    el.classList.add('v-down');
  }
}

// ---- Tableau des voix --------------------------------------------------------
// Le DOM du tableau n'est reconstruit que quand l'ensemble des voix change ;
// aux ticks suivants (~12 Hz), seuls les textes et classes des cellules sont
// mis à jour en place — pas de destruction/re-parse du DOM en continu.
function updateVoicesTable(t) {
  const tbody = $('voicesTable').querySelector('tbody');
  const sel = $('gaugeVoice');
  const fmt = (x, d = 2) => (x == null ? '—' : x.toFixed(d));
  const voices = [];
  const opts = [];
  for (const g of t?.groups ?? []) {
    for (const v of g.voices) {
      const lbl = v.def.label || (v.def.fixedMidi != null ? noteLabel(v.def.fixedMidi + (cfg.transpose || 0)).full : 'anche');
      const note = noteLabel(v.midi + (cfg.transpose || 0)).full;
      voices.push({ v, lbl, note, g });
      opts.push({ key: `${g.key}:${v.def.id}`, label: `${lbl} (${note})` });
    }
  }
  const sig = opts.map((o) => o.key).join(',');

  if (tbody.dataset.sig !== sig) {
    tbody.dataset.sig = sig;
    tbody.innerHTML = voices.length
      ? voices.map(() => `<tr>${'<td></td>'.repeat(8)}</tr>`).join('')
      : '<tr><td colspan="8" class="dim">jouez une note…</td></tr>';
  }
  if (voices.length) {
    const trs = tbody.rows;
    voices.forEach(({ v, lbl, note, g }, i) => {
      const c = trs[i].cells;
      const k = centsClass(v.dTargetCents, cfg.tolCents);
      c[0].textContent = lbl;
      c[1].textContent = note;
      c[2].textContent = fmt(v.target, 3);
      c[3].textContent = v.tracked ? fmt(v.fMeas, 3) : '—';
      c[4].textContent = fmt(v.dTargetCents, 1);
      c[4].className = k;
      c[5].textContent = fmt(v.dHz, 3);
      c[5].className = k;
      // Verrouillage par injection : deux anches accrochées oscillent à la
      // MÊME fréquence — une seule composante spectrale là où deux anches
      // devraient battre. Signature : voix tremblée (cible ≥ 0,4 Hz) non
      // détectée alors que la mesure est convergée et que l'anche de
      // référence est bien là. Second cas (recouvrement partiel) : les deux
      // détectées mais battement quasi nul.
      const base = g?.voices.find((x) => x.def.beatSign === 0);
      const lockedUnison = !v.tracked && v.beat != null && Math.abs(v.beat) >= 0.4
        && g && g.fill >= 0.999 && base && base !== v && base.tracked;
      const lockedBeat = v.tracked && v.beat != null && Math.abs(v.beat) >= 0.4
        && v.beatMeas != null && Math.abs(v.beatMeas) < 0.15;
      if (lockedUnison) {
        c[6].textContent = '⚠ verrouillé ?';
        c[6].className = 'bad';
        c[6].title = 'Une seule composante détectée là où deux anches devraient battre : '
          + 'verrouillage probable (couplage) ou anches non résolues — écartez-les avant de conclure.';
      } else if (lockedBeat) {
        c[6].textContent = `⚠ ${fmt(v.beatMeas)}`;
        c[6].className = 'bad';
        c[6].title = 'Battement quasi nul alors que la cible est non nulle : verrouillage probable des deux anches.';
      } else {
        c[6].textContent = fmt(v.beatMeas);
        c[6].className = '';
        c[6].title = '';
      }
      c[7].textContent = v.beat == null ? '—' : v.beat.toFixed(2);
    });
  }

  // Ne reconstruit le sélecteur de voix que s'il change.
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

// ---- Lecture numérique -------------------------------------------------------
// Panneau de justesse : cartes en grands caractères pour une sélection
// d'anches/harmoniques — la valeur exacte sans avoir à interpréter la courbe.
function updateReadout(t) {
  const chips = $('readoutChips');
  const cards = $('readoutCards');
  const voices = [];
  for (const g of t?.groups ?? []) {
    for (const v of g.voices) {
      voices.push({ key: `${g.key}:${v.def.id}`, v, g });
    }
  }

  // Chips de sélection : reconstruits seulement si l'ensemble des voix change.
  const sig = voices.map((x) => x.key).join(',');
  if (chips.dataset.sig !== sig) {
    chips.dataset.sig = sig;
    chips.innerHTML = '';
    for (const { key } of voices) {
      const lbl = state.voiceLabels.get(key) || key;
      const on = cfg.readout == null || cfg.readout.includes(key);
      const b = document.createElement('button');
      b.className = `chip${on ? ' on' : ''}`;
      b.style.color = colorFor(key);
      b.innerHTML = `<span class="dot" style="background:${colorFor(key)}"></span>${lbl}`;
      b.onclick = () => toggleReadout(key);
      chips.appendChild(b);
    }
  }

  let shown = voices.filter((x) => cfg.readout == null || cfg.readout.includes(x.key));
  // Sélection sauvegardée obsolète (aucune de ses clés n'existe ici) : on
  // affiche tout plutôt qu'un panneau vide après un changement de mode.
  if (!shown.length && cfg.readout != null && voices.length
      && !cfg.readout.some((k) => voices.some((x) => x.key === k))) {
    shown = voices;
  }
  if (!shown.length) {
    cards.innerHTML = voices.length
      ? '<p class="hint">cochez une anche ou une harmonique ci-dessus.</p>'
      : '<p class="hint">jouez une note…</p>';
    return;
  }
  const tol = cfg.tolCents;
  cards.innerHTML = shown.map(({ key, v }) => {
    const lbl = state.voiceLabels.get(key) || key;
    const note = noteLabel(v.midi + (cfg.transpose || 0)).full;
    if (!v.tracked || v.dTargetCents == null) {
      return `<div class="rcard c-off"><div class="rc-head"><b>${lbl}</b><span>${note}</span></div>
        <div class="rc-cents">—</div><div class="rc-sub">non détecté</div></div>`;
    }
    const c = v.dTargetCents;
    const cls = `c-${centsClass(c, tol)}`;
    const arrow = Math.abs(c) <= tol ? '✔' : c < 0 ? '↑' : '↓';
    const beat = (v.beatMeas != null && Math.abs(v.beatMeas) > 0.02)
      ? ` · batt ${v.beatMeas >= 0 ? '+' : ''}${v.beatMeas.toFixed(2)} Hz` : '';
    const est = v.coarse
      ? ` · suivi rapide${t.clarity ? ` (clarté ${(t.clarity * 100).toFixed(0)} %)` : ''}`
      : '';
    return `<div class="rcard ${cls}" style="border-left-color:${colorFor(key)}">
      <div class="rc-head"><b>${lbl}</b><span>${note}</span></div>
      <div class="rc-cents">${v.coarse ? '≈' : arrow} ${c >= 0 ? '+' : ''}${c.toFixed(v.coarse ? 1 : 2)} ¢</div>
      <div class="rc-sub">${v.fMeas.toFixed(v.coarse ? 2 : 3)} Hz · ${v.dHz >= 0 ? '+' : ''}${v.dHz.toFixed(v.coarse ? 2 : 3)} Hz${beat}${est}</div>
    </div>`;
  }).join('');
}

function toggleReadout(key) {
  // null = toutes affichées ; premier clic fige la sélection courante (toutes)
  // puis retire/ajoute, pour que décocher une voix garde les autres.
  if (cfg.readout == null) {
    cfg.readout = ($('readoutChips').dataset.sig || '').split(',').filter(Boolean);
  }
  const i = cfg.readout.indexOf(key);
  if (i >= 0) cfg.readout.splice(i, 1);
  else cfg.readout.push(key);
  saveCfg();
  $('readoutChips').dataset.sig = ''; // force la reconstruction des chips
  if (state.tick) updateReadout(state.tick);
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
  const pad = { l: 36, r: 8, t: 18, b: 18 };
  const plotW = W - pad.l - pad.r, plotH = H - pad.t - pad.b;

  const all = state.history;
  const T = all.length ? all[all.length - 1].t : 0;
  const rangeSel = $('gaugeRange').value;
  // La fenêtre visible, les clés de voix ET l'échelle ne changent qu'au
  // rythme des ticks (~12 Hz) ou d'un changement de réglage : tout est mis
  // en cache pour ne rien recalculer à 60 fps pendant le survol souris.
  if (!state.curveCache || state.curveCache.rangeSel !== rangeSel) {
    const hist = all.filter((e) => e.t >= T - HISTORY_SPAN - 0.2);
    const keys = [];
    for (const e of hist) for (const k of Object.keys(e.vals)) if (!keys.includes(k)) keys.push(k);

    // Note courante = celle du dernier échantillon. L'échelle auto se
    // concentre sur elle (pas sur les notes passées, qui ont chacune leur
    // propre référence et écraseraient la lecture de la note en cours).
    const curMidi = hist.length ? hist[hist.length - 1].midi : null;

    // Échelle : fixe (±5 à ±50 ¢, centrée sur 0) ou automatique — centrée
    // sur la médiane des valeurs de la NOTE COURANTE, plus petite étendue
    // qui les contient, plafonnée à ±50 ¢. Au changement de note, l'axe se
    // recale immédiatement (pas de lissage qui traînerait entre deux notes).
    let range;
    let center = 0;
    if (rangeSel === 'auto') {
      const vals = [];
      for (const e of hist) {
        if (curMidi != null && e.midi !== curMidi) continue;
        for (const k of keys) {
          const v = e.vals[k];
          if (v && isFinite(v.c)) vals.push(v.c);
        }
      }
      if (vals.length) {
        vals.sort((a, b) => a - b);
        const median = vals[vals.length >> 1];
        // EMA remis à la médiane dès que la note change (recalage immédiat).
        if (state.centerEMA == null || state.centerMidi !== curMidi) {
          state.centerEMA = median;
          state.centerMidi = curMidi;
        } else {
          state.centerEMA += 0.3 * (median - state.centerEMA);
        }
        center = Math.round(state.centerEMA * 2) / 2;
        // Étendue robuste : 90e percentile des écarts au centre (pas le max),
        // pour que les brefs pics transitoires d'attaque ne fassent pas sauter
        // l'échelle à ±50 — ils débordent en haut, la partie stable reste lisible.
        const devs = vals.map((v) => Math.abs(v - center)).sort((a, b) => a - b);
        const p90 = devs[Math.min(devs.length - 1, Math.floor(devs.length * 0.9))] || 1.5;
        const maxDev = Math.max(1.5, p90);
        const steps = [2, 5, 10, 25, 50];
        range = steps.find((s) => s >= maxDev * 1.15) || 50;
      } else {
        state.centerEMA = null;
        range = 5;
      }
      const cLbl = center === 0 ? '' : `${center > 0 ? '+' : ''}${center} `;
      $('curveRangeLbl').textContent = `auto ${cLbl}±${range} ¢ · ${HISTORY_SPAN} s`;
    } else {
      range = Number(rangeSel);
      $('curveRangeLbl').textContent = `±${range} ¢ · ${HISTORY_SPAN} s`;
    }
    state.curveCache = { hist, keys, T, rangeSel, center, range, curMidi };
  }
  const { hist, keys, center, range, curMidi } = state.curveCache;
  const xFor = (t) => pad.l + plotW * (1 - (T - t) / HISTORY_SPAN);
  const yFor = (c) => pad.t + (1 - (clamp(c - center, -range, range) + range) / (2 * range)) * plotH;

  // Grille verticale (cents) : lignes sur les multiples absolus du pas, la
  // ligne de zéro (la cible d'accordage) marquée quand elle est dans le champ.
  ctx.font = '10px system-ui';
  ctx.textAlign = 'right';
  const step = range <= 2 ? 0.5 : range <= 5 ? 1 : range <= 10 ? 2 : range <= 25 ? 5
    : range <= 50 ? 10 : range <= 100 ? 25 : range <= 200 ? 50 : 100;
  const gridStart = Math.ceil((center - range) / step) * step;
  for (let c = gridStart; c <= center + range + 1e-9; c += step) {
    const cRound = Math.round(c * 2) / 2;
    const y = yFor(cRound);
    ctx.strokeStyle = cRound === 0 ? theme().gridStrong : theme().grid;
    ctx.lineWidth = cRound === 0 ? 1.5 : 1;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = theme().dim2;
    ctx.fillText(String(cRound), pad.l - 5, y + 3);
  }

  // Grille horizontale (secondes).
  ctx.textAlign = 'center';
  for (let s = 0; s <= HISTORY_SPAN; s += 5) {
    const x = pad.l + plotW * (1 - s / HISTORY_SPAN);
    ctx.strokeStyle = theme().grid;
    ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
    ctx.fillStyle = theme().dim2;
    ctx.fillText(s ? `−${s} s` : '0', x, H - 5);
  }

  if (!hist.length) {
    ctx.fillStyle = theme().dim2;
    ctx.font = '13px system-ui';
    ctx.fillText('jouez une note…', W / 2, H / 2);
    return;
  }

  // Marqueurs de changement de note (transitions). L'étiquette n'est écrite
  // que si elle ne chevauche pas la précédente — en chant ou jeu rapide, les
  // notes changent plus vite que la place disponible pour les noms.
  ctx.textAlign = 'left';
  ctx.font = '10px system-ui';
  let lastLabelEnd = -Infinity;
  for (let i = 1; i < hist.length; i++) {
    if (hist[i].midi !== hist[i - 1].midi && hist[i].midi != null) {
      const x = xFor(hist[i].t);
      if (x < pad.l) continue;
      ctx.strokeStyle = theme().markerLine;
      ctx.setLineDash([2, 4]);
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
      ctx.setLineDash([]);
      const lbl = noteLabel(hist[i].midi + (cfg.transpose || 0)).full;
      const w = ctx.measureText(lbl).width;
      if (x + 3 > lastLabelEnd + 6) {
        ctx.fillStyle = theme().dim;
        ctx.fillText(lbl, x + 3, pad.t - 5);
        lastLabelEnd = x + 3 + w;
      }
    }
  }

  // Traces (une par anche), la voix suivie en gras. Le trait est CASSÉ à
  // chaque changement de note (chaque note a sa propre référence : les
  // relier créerait des sauts verticaux illisibles) et aux trous de temps.
  // Les segments des notes passées sont estompés pour que la note courante
  // — celle qu'on accorde — ressorte nettement.
  const selKey = $('gaugeVoice').value;
  let legendX = pad.l + 4;
  let legendY = 4;
  keys.forEach((k) => {
    const col = colorFor(k);
    const baseW = k === selKey ? 2.4 : 1.3;
    let seg = [];          // segment courant : liste de {x, y}
    let segMidi = null;
    let prevT = null;
    const flush = () => {
      if (seg.length < 1) return;
      const past = segMidi !== curMidi;
      ctx.strokeStyle = past ? hexA(col, 0.22) : col;
      ctx.lineWidth = past ? Math.max(1, baseW - 0.6) : baseW;
      ctx.beginPath();
      seg.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
      if (seg.length === 1) { ctx.arc(seg[0].x, seg[0].y, baseW / 2, 0, 7); ctx.fill(); }
      else ctx.stroke();
      seg = [];
    };
    for (const e of hist) {
      const v = e.vals[k];
      if (!v) { flush(); prevT = null; continue; }
      if (seg.length && (e.midi !== segMidi || (prevT != null && e.t - prevT > 0.5))) flush();
      const x = xFor(e.t);
      prevT = e.t;
      if (x < pad.l) continue;
      if (!seg.length) segMidi = e.midi;
      seg.push({ x, y: yFor(v.c) });
    }
    flush();
    // Légende (passe sur une deuxième ligne si nécessaire).
    const lbl = state.voiceLabels.get(k) || k;
    const wLbl = 20 + ctx.measureText(lbl).width;
    if (legendX + wLbl > W - 8) { legendX = pad.l + 4; legendY += 11; }
    ctx.fillStyle = col;
    ctx.fillRect(legendX, legendY, 8, 8);
    ctx.fillStyle = theme().dim;
    ctx.fillText(lbl, legendX + 11, legendY + 8);
    legendX += wLbl;
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
      ctx.strokeStyle = theme().dim;
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
      ctx.fillStyle = theme().text;
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
    g.addColorStop(0, theme().canvasBg);
    g.addColorStop(0.5, v?.tracked ? (Math.abs(v.dTargetCents) < 1 ? theme().okStrong : theme().accentMuted) : theme().panel2);
    g.addColorStop(1, theme().canvasBg);
    ctx.fillStyle = g;
    ctx.fillRect(x + off, 8, period, H - 16);
  }
}

function drawSpectrum() {
  const cv = $('spectrum'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  // Dernier spectre reçu : conservé pendant les silences (le moteur ne
  // recalcule plus la FFT large bande quand le niveau est sous le seuil).
  const spec = state.lastSpectrum;
  // Repères d'octaves (Do1..Do9) sur échelle log 20 Hz → 10 kHz.
  ctx.font = '10px system-ui';
  ctx.textAlign = 'left';
  for (let oct = 1; oct <= 9; oct++) {
    const f = midiToFreq(12 * oct + 12, cfg);
    if (f < 20 || f > 10000) continue;
    const x = (Math.log(f / 20) / Math.log(500)) * W;
    ctx.strokeStyle = theme().panel2;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    ctx.fillStyle = theme().dim2;
    ctx.fillText(`Do${oct}`, x + 3, 12);
  }
  if (!spec) return;
  let max = 1e-9;
  for (let i = 0; i < spec.length; i++) if (spec[i] > max) max = spec[i];
  ctx.beginPath();
  ctx.strokeStyle = theme().accent;
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
  // Groupes de base d'abord, 5 bandes au maximum (au-delà, illisible :
  // les harmoniques restent visibles sur la courbe et dans le tableau).
  const groups = (state.tick?.groups?.filter((g) => g.spectrum) ?? [])
    .sort((a, b) => (a.isHarmonic ? 1 : 0) - (b.isHarmonic ? 1 : 0))
    .slice(0, 5);
  if (!groups.length) {
    ctx.fillStyle = theme().dim2;
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
    // Groupes harmoniques/sous-harmoniques : cibles et mesures sont dans le
    // domaine du partiel (fc du traqueur) ; groupes de base : ramenées à la
    // fondamentale.
    const dispCenter = g.isHarmonic ? (g.fc ?? g.center * k) : g.center;
    const scale = g.isHarmonic ? 1 : k;
    const spec = g.spectrum;
    const binHz = g.srd / g.W;
    let max = 1e-9;
    for (let i = 0; i < spec.length; i++) if (spec[i] > max) max = spec[i];
    // Axe.
    ctx.strokeStyle = theme().panel2;
    ctx.beginPath(); ctx.moveTo(0, y0 + rowH - 14); ctx.lineTo(W, y0 + rowH - 14); ctx.stroke();
    ctx.fillStyle = theme().dim2;
    ctx.font = '10px system-ui';
    ctx.textAlign = 'center';
    for (let hz = -span; hz <= span; hz += 5) {
      const x = ((hz + span) / (2 * span)) * W;
      ctx.fillText(hz ? `${hz > 0 ? '+' : ''}${hz}` : `${dispCenter.toFixed(1)} Hz`, x, y0 + rowH - 3);
    }
    // Cibles (pointillés).
    for (const v of g.voices) {
      const dx = (v.target - dispCenter);
      if (Math.abs(dx) > span) continue;
      const x = ((dx + span) / (2 * span)) * W;
      ctx.strokeStyle = theme().warn;
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(x, y0 + 14); ctx.lineTo(x, y0 + rowH - 14); ctx.stroke();
      ctx.setLineDash([]);
    }
    // Spectre zoom (bande de base recentrée, axe ramené à la fondamentale).
    ctx.beginPath();
    ctx.strokeStyle = theme().ok;
    ctx.lineWidth = 1.4;
    let started = false;
    for (let px = 0; px < W; px++) {
      const hz = (px / W) * 2 * span - span;      // écart au centre affiché
      const offTracker = hz * scale;              // écart dans la bande du traqueur
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
    ctx.fillStyle = theme().text;
    ctx.font = '11px system-ui';
    for (const v of g.voices) {
      if (!v.tracked) continue;
      const dx = v.fMeas - dispCenter;
      if (Math.abs(dx) > span) continue;
      const x = ((dx + span) / (2 * span)) * W;
      ctx.fillText(`${v.def.label || noteLabel(v.midi + (cfg.transpose || 0)).full} ${v.dTargetCents >= 0 ? '+' : ''}${v.dTargetCents.toFixed(1)}¢`, x, y0 + 12);
    }
    if (g.isHarmonic || g.kTrack > 1) {
      ctx.fillStyle = theme().dim2;
      ctx.textAlign = 'left';
      ctx.fillText(g.isHarmonic ? `partiel ${g.kTrack}` : `mesure sur le partiel ${g.kTrack}`, 6, y0 + 12);
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
  ctx.strokeStyle = theme().accent;
  for (let m = m0; m <= m1; m++) {
    const x = ((m - m0) / (m1 - m0)) * W;
    const y = H - 12 - (beatTarget(m, c) / maxB) * (H - 24);
    m === m0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  // Écrasements.
  ctx.fillStyle = theme().warn;
  for (const [m, b] of Object.entries(c.overrides || {})) {
    const x = ((m - m0) / (m1 - m0)) * W;
    const y = H - 12 - (Number(b) / maxB) * (H - 24);
    ctx.beginPath(); ctx.arc(x, y, 3, 0, 7); ctx.fill();
  }
  ctx.fillStyle = theme().dim2;
  ctx.font = '10px system-ui';
  ctx.textAlign = 'left';
  ctx.fillText(noteLabel(m0).full, 2, H - 2);
  ctx.textAlign = 'right';
  ctx.fillText(noteLabel(m1).full, W - 2, H - 2);
  ctx.fillText(`${maxB.toFixed(1)} Hz`, W - 2, 10);
}

// ---- Diagramme de phase --------------------------------------------------------
// Trajectoire de la voix suivie dans un plan au choix (intensité, écart en
// cents, fréquence, dérivées, temps). L'outil de base de l'analyse de la
// dynamique de l'anche : caractéristique f–I, cycles, transitoires.
const PHASE_AXES = {
  time: { label: 't (s)', get: (p) => p.t },
  cents: { label: 'écart (¢)', get: (p) => p.c },
  freq: { label: 'f (Hz)', get: (p) => p.f },
  ampDb: { label: 'I (dB)', get: (p) => p.db },
  dCents: { label: 'df/dt (¢/s)', get: (p) => p.dc },
  dAmp: { label: 'dI/dt (dB/s)', get: (p) => p.dDb },
};

function phasePoints(span) {
  const key = $('gaugeVoice').value || null;
  const hist = state.history;
  if (!hist.length) return [];
  const T = hist[hist.length - 1].t;
  const pts = [];
  let prev = null;
  for (const e of hist) {
    if (e.t < T - span) continue;
    const v = key ? e.vals[key] : Object.values(e.vals)[0];
    if (!v) { prev = null; continue; }
    const p = { t: e.t, c: v.c, f: v.f, db: 20 * Math.log10((v.a ?? 0) + 1e-9) };
    if (prev && e.t - prev.t < 0.6 && e.t > prev.t) {
      p.dc = (p.c - prev.c) / (e.t - prev.t);
      p.dDb = (p.db - prev.db) / (e.t - prev.t);
      pts.push(p);
    }
    prev = p;
  }
  return pts;
}

function drawPhase() {
  const cv = $('phase'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const ax = PHASE_AXES[$('phaseX').value] || PHASE_AXES.ampDb;
  const ay = PHASE_AXES[$('phaseY').value] || PHASE_AXES.cents;
  // Les points ne dépendent que de l'historique (rythme des ticks), de la
  // voix suivie et de la fenêtre : mis en cache pour éviter de re-parcourir
  // l'historique et de réallouer à chaque image.
  const span = Number($('phaseSpan').value) || 15;
  const sig = `${span}|${$('gaugeVoice').value}`;
  if (!state.phaseCache || state.phaseCache.sig !== sig) {
    state.phaseCache = { sig, pts: phasePoints(span) };
  }
  const pts = state.phaseCache.pts;
  updatePressureFit();
  const pad = { l: 44, r: 10, t: 10, b: 26 };
  ctx.font = '10px system-ui';
  if (pts.length < 3) {
    ctx.fillStyle = theme().dim2;
    ctx.textAlign = 'center';
    ctx.fillText('pas encore assez de points — jouez une note…', W / 2, H / 2);
    return;
  }
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of pts) {
    const x = ax.get(p), y = ay.get(p);
    if (!isFinite(x) || !isFinite(y)) continue;
    x0 = Math.min(x0, x); x1 = Math.max(x1, x);
    y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  const mx = (x1 - x0) * 0.06 + 1e-6, my = (y1 - y0) * 0.06 + 1e-6;
  x0 -= mx; x1 += mx; y0 -= my; y1 += my;
  const px = (x) => pad.l + ((x - x0) / (x1 - x0)) * (W - pad.l - pad.r);
  const py = (y) => H - pad.b - ((y - y0) / (y1 - y0)) * (H - pad.t - pad.b);
  // Axes et graduations minimales.
  ctx.strokeStyle = theme().panel2;
  ctx.fillStyle = theme().dim2;
  ctx.textAlign = 'center';
  for (let i = 0; i <= 4; i++) {
    const gx = x0 + ((x1 - x0) * i) / 4;
    ctx.beginPath(); ctx.moveTo(px(gx), pad.t); ctx.lineTo(px(gx), H - pad.b); ctx.stroke();
    ctx.fillText(gx.toFixed(Math.abs(x1 - x0) < 5 ? 2 : 1), px(gx), H - pad.b + 12);
  }
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const gy = y0 + ((y1 - y0) * i) / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, py(gy)); ctx.lineTo(W - pad.r, py(gy)); ctx.stroke();
    ctx.fillText(gy.toFixed(Math.abs(y1 - y0) < 5 ? 2 : 1), pad.l - 4, py(gy) + 3);
  }
  ctx.textAlign = 'center';
  ctx.fillText(ax.label, (pad.l + W - pad.r) / 2, H - 4);
  ctx.save();
  ctx.translate(11, (pad.t + H - pad.b) / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(ay.label, 0, 0);
  ctx.restore();
  // Trajectoire : segments de plus en plus opaques vers le présent.
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (b.t - a.t > 0.6) continue;
    ctx.strokeStyle = `rgba(79,195,247,${0.12 + 0.85 * (i / pts.length)})`;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(px(ax.get(a)), py(ay.get(a)));
    ctx.lineTo(px(ax.get(b)), py(ay.get(b)));
    ctx.stroke();
  }
  // Point courant.
  const last = pts[pts.length - 1];
  ctx.fillStyle = theme().warn;
  ctx.beginPath();
  ctx.arc(px(ax.get(last)), py(ay.get(last)), 3.5, 0, 7);
  ctx.fill();
}

// Caractéristique pression–hauteur de l'anche : régression linéaire de
// l'écart (¢) sur l'intensité (dB) — à embouchure fixe, l'intensité croît
// avec la pression d'alimentation, donc la pente mesure le « flattening »
// de l'anche (elle baisse quand on pousse). Pour la mesurer : balayer la
// pression du soufflet en crescendo/decrescendo sur une note tenue.
// Déviation d'Allan σ(τ) de la voix suivie : stabilité de fréquence en
// fonction du temps d'intégration. Calculée sur la plus longue plage
// récente à note constante (une note tenue), tracée en log-log.
function drawAllan() {
  const cv = $('allan'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  const pad = { l: 46, r: 10, t: 12, b: 28 };
  ctx.font = '10px system-ui';
  ctx.textAlign = 'center';

  // Plus longue plage contiguë récente : même note, voix suivie présente,
  // pas de trou temporel > 0,4 s.
  const key = $('gaugeVoice').value || null;
  const hist = state.history;
  const seg = [];
  for (let i = hist.length - 1; i >= 0; i--) {
    const e = hist[i];
    const v = key ? e.vals[key] : Object.values(e.vals)[0];
    if (!v || e.midi == null) break;
    if (seg.length) {
      const prev = seg[seg.length - 1];
      if (prev.midi !== e.midi || prev.t - e.t > 0.4) break;
    }
    seg.push({ t: e.t, c: v.c, midi: e.midi });
  }
  seg.reverse();

  const info = $('allanInfo');
  if (seg.length < 16) {
    ctx.fillStyle = theme().dim2;
    ctx.fillText('tenez une note stable quelques secondes…', W / 2, H / 2);
    return;
  }
  // Pas d'échantillonnage médian (robuste aux trames manquantes).
  const dts = [];
  for (let i = 1; i < seg.length; i++) dts.push(seg[i].t - seg[i - 1].t);
  dts.sort((a, b) => a - b);
  const tau0 = dts[dts.length >> 1] || 0.085;
  const y = seg.map((s) => s.c);
  const pts = overlappingAllan(y, tau0);
  if (pts.length < 2) { ctx.fillStyle = theme().dim2; ctx.fillText('…', W / 2, H / 2); return; }

  const xs = pts.map((p) => Math.log10(p.tau));
  const ys = pts.map((p) => Math.log10(Math.max(p.sigma, 1e-4)));
  const x0 = Math.min(...xs), x1 = Math.max(...xs) + 1e-6;
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  if (y1 - y0 < 1) { const c = (y0 + y1) / 2; y0 = c - 0.5; y1 = c + 0.5; }
  y0 -= 0.15; y1 += 0.15;
  const px = (lx) => pad.l + ((lx - x0) / (x1 - x0)) * (W - pad.l - pad.r);
  const py = (ly) => H - pad.b - ((ly - y0) / (y1 - y0)) * (H - pad.t - pad.b);

  // Grille décades.
  ctx.strokeStyle = theme().grid;
  ctx.fillStyle = theme().dim2;
  for (let d = Math.floor(x0); d <= x1; d++) {
    const x = px(d);
    ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
    const s = d < 0 ? `${(10 ** d).toFixed(-d > 2 ? 2 : -d)} s` : `${10 ** d} s`;
    ctx.fillText(s, x, H - pad.b + 12);
  }
  ctx.textAlign = 'right';
  for (let d = Math.ceil(y0); d <= y1; d++) {
    const yy = py(d);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(W - pad.r, yy); ctx.stroke();
    ctx.fillText(`${10 ** d}¢`, pad.l - 4, yy + 3);
  }
  ctx.save();
  ctx.translate(11, (pad.t + H - pad.b) / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = 'center';
  ctx.fillText('σ(τ)', 0, 0);
  ctx.restore();

  // Courbe σ(τ).
  ctx.strokeStyle = theme().accent;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  pts.forEach((p, i) => {
    const X = px(xs[i]), Y = py(ys[i]);
    i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y);
  });
  ctx.stroke();
  ctx.fillStyle = theme().accent;
  pts.forEach((p, i) => { ctx.beginPath(); ctx.arc(px(xs[i]), py(ys[i]), 2, 0, 7); ctx.fill(); });

  // Repère : minimum de σ (meilleure stabilité) et son τ.
  let best = 0;
  for (let i = 1; i < pts.length; i++) if (pts[i].sigma < pts[best].sigma) best = i;
  const bp = pts[best];
  if (info) {
    info.classList.add('measured');
    info.textContent = `σ min ${bp.sigma.toFixed(bp.sigma < 0.1 ? 3 : 2)} ¢ à τ ≈ ${bp.tau.toFixed(bp.tau < 1 ? 2 : 1)} s `
      + `· σ(1 s) ${allanAt(pts, 1)} · ${seg.length} points sur ${(seg.length * tau0).toFixed(1)} s`;
  }
}

function allanAt(pts, tau) {
  let b = pts[0];
  for (const p of pts) if (Math.abs(p.tau - tau) < Math.abs(b.tau - tau)) b = p;
  return `${b.sigma.toFixed(b.sigma < 0.1 ? 3 : 2)} ¢`;
}

function updatePressureFit() {
  const el = $('pressureFit');
  if (!el) return;
  // Utilise l'estimateur rapide (f0, fenêtre ~341 ms) : la mesure fine
  // traîne derrière un balayage de pression et biaiserait la pente.
  const span = Number($('phaseSpan').value) || 15;
  const hist = state.history;
  const T = hist.length ? hist[hist.length - 1].t : 0;
  const xs = [], ys = [];
  for (const e of hist) {
    if (e.t < T - span || !e.fast) continue;
    if (isFinite(e.fast.db) && isFinite(e.fast.c)) { xs.push(e.fast.db); ys.push(e.fast.c); }
  }
  const n = xs.length;
  const spread = n ? Math.max(...xs) - Math.min(...xs) : 0;
  if (n < 15 || spread < 3) {
    el.classList.remove('measured');
    el.textContent = 'Balayez la pression du soufflet (crescendo/decrescendo, ≥ 3 dB de plage) pour mesurer la pente fréquence-intensité.';
    return;
  }
  let sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    sx += xs[i]; sy += ys[i];
    sxx += xs[i] * xs[i]; sxy += xs[i] * ys[i]; syy += ys[i] * ys[i];
  }
  const denomX = n * sxx - sx * sx;
  const denomY = n * syy - sy * sy;
  if (denomX < 1e-9) return;
  const slope = (n * sxy - sx * sy) / denomX;
  const r2 = denomY > 1e-12 ? ((n * sxy - sx * sy) ** 2) / (denomX * denomY) : 0;
  el.classList.add('measured');
  el.textContent = `Caractéristique f(I) : ${slope >= 0 ? '+' : ''}${slope.toFixed(2)} ¢/dB `
    + `· R² ${r2.toFixed(2)} · plage ${spread.toFixed(1)} dB · ${n} points`;
}

// Export CSV de l'historique complet (120 s) : temps, note, puis fréquence,
// écart en cents et intensité dB pour chaque voix suivie.
function exportCurveCsv() {
  const hist = state.history;
  if (!hist.length) { alert('Aucune donnée : jouez d\'abord une note.'); return; }
  const keys = [];
  for (const e of hist) for (const k of Object.keys(e.vals)) if (!keys.includes(k)) keys.push(k);
  const sep = ';';
  const head = ['t_s', 'midi', 'note'];
  for (const k of keys) {
    const lbl = (state.voiceLabels.get(k) || k).replace(/[;\n]/g, ' ');
    head.push(`${lbl} f_hz`, `${lbl} ecart_cents`, `${lbl} intensite_db`);
  }
  const lines = [head.join(sep)];
  for (const e of hist) {
    const row = [e.t.toFixed(4), e.midi ?? '',
      e.midi != null ? noteLabel(e.midi + (cfg.transpose || 0)).full : ''];
    for (const k of keys) {
      const v = e.vals[k];
      row.push(v ? v.f.toFixed(5) : '', v ? v.c.toFixed(3) : '',
        v ? (20 * Math.log10((v.a ?? 0) + 1e-9)).toFixed(2) : '');
    }
    lines.push(row.join(sep));
  }
  download(`courbe-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`,
    lines.join('\n'), 'text/csv');
}

function clamp(x, a, b) { return Math.min(b, Math.max(a, x)); }

function markAllDirty() {
  state.curveDirty = true;
  state.phaseDirty = true;
  state.specDirty = true;
  state.zoomDirty = true;
  state.allanDirty = true;
}

// Un canvas dans un onglet caché a offsetParent === null : rien à dessiner.
function canvasVisible(id) {
  const el = $(id);
  return el && el.offsetParent !== null;
}

function renderLoop(now) {
  const dt = Math.min(0.1, (now - state.lastDraw) / 1000);
  state.lastDraw = now;
  // Chaque vue n'est redessinée que si elle est visible ET marquée modifiée
  // (nouveau tick, souris, réglage). La courbe reste interactive gelée
  // (curseur de lecture) : le survol la marque modifiée.
  if (state.curveDirty && canvasVisible('pitchCurve')) {
    drawPitchCurve();
    state.curveDirty = false;
  }
  if (state.phaseDirty && canvasVisible('phase')) {
    drawPhase();
    state.phaseDirty = false;
  }
  if (!state.frozen) {
    if (state.specDirty && canvasVisible('spectrum')) {
      drawSpectrum();
      state.specDirty = false;
    }
    if (state.zoomDirty && canvasVisible('zoom')) {
      drawZoom();
      state.zoomDirty = false;
    }
  }
  if (state.allanDirty && canvasVisible('allan')) {
    drawAllan();
    state.allanDirty = false;
  }
  // Le stroboscope est une animation continue : dessiné tant qu'il est
  // visible (sa dérive de phase, elle, n'avance que hors gel).
  if (canvasVisible('strobe')) drawStrobe(dt);
  requestAnimationFrame(renderLoop);
}

function setFrozen(on, auto = false) {
  state.frozen = on;
  state.autoFrozen = on && auto;
  $('btnFreeze').classList.toggle('active', on);
  $('btnFreeze').textContent = on ? (auto ? '❄ Gelé (auto)' : '❄ Gelé') : '❄ Geler';
  // Bannière bien visible directement sur la courbe : le gel automatique ne
  // doit jamais donner l'impression que l'outil s'est arrêté de fonctionner.
  $('freezeBanner').classList.toggle('hidden', !(on && auto));
  markAllDirty();
}

function toggleFreeze() {
  if (!state.running) return;
  setFrozen(!state.frozen);
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
  report.renderGrid($('tuneGrid'), cfg, cfg.bellows, state.tick?.playedMidi ?? null, (midi) => {
    cfg.lockNote = midi;
    updateLockButton();
    pushConfig();
  });
  $('reportCount').textContent = `${report.rows.size} mesures enregistrées`;
}

// Confirmation sonore discrète (enregistrement, changement de soufflet).
function beep(freq = 1318, dur = 0.05) {
  if (!audioCtx) return;
  const o = audioCtx.createOscillator();
  const g = audioCtx.createGain();
  o.frequency.value = freq;
  g.gain.value = 0.06;
  g.gain.setTargetAtTime(0, audioCtx.currentTime + dur, 0.01);
  o.connect(g).connect(audioCtx.destination);
  o.start();
  o.stop(audioCtx.currentTime + dur + 0.08);
}

function setBellows(dir) {
  cfg.bellows = dir;
  $('btnTirer').classList.toggle('active', dir === 'T');
  $('btnPousser').classList.toggle('active', dir === 'P');
  saveCfg();
  refreshReport();
  beep(dir === 'T' ? 660 : 880, 0.04);
}

// Calibrage du micro : l'utilisateur fait sonner une fréquence connue
// (diapason, générateur étalonné) ; l'écart entre la mesure (déjà corrigée
// du ppm courant) et la référence donne la correction d'horloge à appliquer.
function calibrateFromMeasure() {
  const v = selectedVoice(state.tick);
  const ref = Number($('calRef').value);
  if (!v || !v.tracked || state.tick?.quiet) {
    alert('Faites sonner la référence et attendez « convergé » avant de calibrer.');
    return;
  }
  if (!(ref > 0)) { alert('Référence de calibrage invalide.'); return; }
  // La mesure inclut déjà le ppm courant : on compose la correction.
  const residualPpm = (ref / v.fMeas - 1) * 1e6;
  cfg.calibrationPpm = Math.round((cfg.calibrationPpm + residualPpm) * 10) / 10;
  $('calib').value = cfg.calibrationPpm;
  pushConfig();
  beep(1046, 0.08);
  alert(`Micro calibré : ${cfg.calibrationPpm} ppm `
    + `(correction de ${residualPpm >= 0 ? '+' : ''}${residualPpm.toFixed(2)} ppm, `
    + `soit ${(residualPpm * 1.2e-3).toFixed(3)} cent).`);
}

function recordNow() {
  const n = report.record(state.tick, cfg, cfg.bellows);
  if (!n) {
    alert('Aucune mesure convergée à enregistrer — laissez sonner la note jusqu\'à « convergé ».');
    return;
  }
  refreshReport();
  beep(1318, 0.05);
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
  $('harmonics').value = String(cfg.trackHarmonics || 0);
  $('response').value = cfg.response;
  $('tolCents').value = String(cfg.tolCents);
  $('autoFreeze').checked = !!cfg.autoFreeze;
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
    state.curveDirty = true;
  });
  curve.addEventListener('mouseleave', () => { state.mouse = null; state.curveDirty = true; });
  curve.addEventListener('click', toggleFreeze);
  $('phase').addEventListener('click', toggleFreeze);

  // Onglets : Accordage / Analyse / Réglages / Rapport. L'en-tête (note,
  // témoin, boutons) reste visible en permanence au-dessus, chaque onglet
  // tient sans avoir à faire défiler toute la page.
  document.querySelectorAll('#tabbar .tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('#tabbar .tab').forEach((t) => {
        t.classList.toggle('active', t === tab);
        t.setAttribute('aria-selected', String(t === tab));
      });
      document.querySelectorAll('.tabpage').forEach((p) => {
        p.classList.toggle('active', p.id === `tabpage-${tab.dataset.tab}`);
      });
      markAllDirty(); // les canvas du nouvel onglet doivent se dessiner
    });
  });

  // Les vues se redessinent quand leurs réglages changent.
  $('gaugeRange').onchange = () => { state.curveDirty = true; };
  $('gaugeVoice').onchange = () => { state.curveDirty = true; state.phaseDirty = true; };
  for (const id of ['phaseX', 'phaseY', 'phaseSpan']) {
    $(id).onchange = () => { state.phaseDirty = true; };
  }

  // Plein écran sur les panneaux marqués.
  document.querySelectorAll('.fsbtn[data-fs]').forEach((b) => {
    b.addEventListener('click', (e) => {
      e.stopPropagation();
      const panel = b.closest('.panel');
      if (document.fullscreenElement === panel) document.exitFullscreen();
      else panel.requestFullscreen?.();
      markAllDirty();
    });
  });

  // Verrouillage de la note mesurée.
  $('btnLock').onclick = () => {
    if (cfg.lockNote != null) cfg.lockNote = null;
    else if (state.tick?.playedMidi != null) cfg.lockNote = state.tick.playedMidi;
    else return;
    updateLockButton();
    pushConfig();
  };

  $('gateDb').value = cfg.gateDb;
  $('gateDbVal').textContent = String(cfg.gateDb);
  $('gateDb').oninput = () => {
    cfg.gateDb = Number($('gateDb').value);
    $('gateDbVal').textContent = String(cfg.gateDb);
    pushConfig();
  };
  $('trackSub').checked = !!cfg.trackSub;
  $('trackSub').onchange = () => { cfg.trackSub = $('trackSub').checked; pushConfig(); };
  $('btnCurveCsv').onclick = exportCurveCsv;
  updateLockButton();
  $('a4').onchange = () => { cfg.a4 = clamp(Number($('a4').value) || 440, 430, 450); $('a4').value = cfg.a4; pushConfig(); };
  tSel.onchange = () => { cfg.temperament = tSel.value; pushConfig(); };
  trSel.onchange = () => { cfg.transpose = Number(trSel.value); pushConfig(); };
  $('calib').onchange = () => { cfg.calibrationPpm = Number($('calib').value) || 0; pushConfig(); };
  $('mode').onchange = () => { cfg.mode = $('mode').value; updateModeVisibility(); pushConfig(); };
  rSel.onchange = () => { cfg.register = rSel.value; pushConfig(); };
  $('harmonics').onchange = () => { cfg.trackHarmonics = Number($('harmonics').value); pushConfig(); };
  $('response').onchange = () => { cfg.response = $('response').value; pushConfig(); };
  $('tolCents').onchange = () => { cfg.tolCents = Number($('tolCents').value); saveCfg(); };
  $('autoFreeze').onchange = () => { cfg.autoFreeze = $('autoFreeze').checked; saveCfg(); };
  $('btnCalibrate').onclick = calibrateFromMeasure;
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
  $('btnRecord').onclick = recordNow;
  $('btnTirer').onclick = () => setBellows('T');
  $('btnPousser').onclick = () => setBellows('P');
  setBellows(cfg.bellows || 'T');

  // Raccourcis clavier : les mains restent sur l'instrument.
  // Volontairement PAS sur la barre d'espace : c'est le raccourci natif de
  // défilement de page dans tous les navigateurs, et le bloquer empêchait de
  // faire défiler l'écran pendant l'accordage. « Entrée » ne défile jamais.
  document.addEventListener('keydown', (e) => {
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName) || e.ctrlKey || e.metaKey || e.altKey) return;
    switch (e.key === 'Enter' ? 'Enter' : e.key.toLowerCase()) {
      case 'Enter': e.preventDefault(); recordNow(); break;
      case 'f': toggleFreeze(); break;
      case 'l': $('btnLock').click(); break;
      case 'b': setBellows(cfg.bellows === 'T' ? 'P' : 'T'); break;
      case 't': toggleTone(); break;
      default: break;
    }
  });
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

function updateLockButton() {
  const b = $('btnLock');
  b.disabled = !state.running && cfg.lockNote == null;
  if (cfg.lockNote != null) {
    b.textContent = `🔒 ${noteLabel(cfg.lockNote + (cfg.transpose || 0)).full}`;
    b.classList.add('active');
  } else {
    b.textContent = '🔓 Auto';
    b.classList.remove('active');
  }
}

function updateModeVisibility() {
  $('modeRegister').classList.toggle('hidden', cfg.mode !== 'register');
  $('modeManual').classList.toggle('hidden', cfg.mode !== 'manual');
  // Le suivi d'harmoniques ne s'applique pas au mode registre (les voix
  // couvrent déjà les octaves et leurs harmoniques se recouvrent).
  $('harmonicsCtl').classList.toggle('hidden', cfg.mode === 'register');
  $('harmonicsHint').classList.toggle('hidden', cfg.mode === 'register');
  $('subCtl').classList.toggle('hidden', cfg.mode === 'register');
}

// ---- Démarrage -----------------------------------------------------------------
// App installable (PWA) : fonctionne hors ligne une fois visitée, s'ajoute à
// l'écran d'accueil. Chemin relatif : valide aussi si servi depuis un
// sous-dossier (ex. GitHub Pages de projet).
if ('serviceWorker' in navigator) {
  // Rechargement unique quand un nouveau service worker prend la main : la
  // mise à jour du code arrive sans manipulation, sans boucle de rechargement.
  let swReloaded = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (swReloaded) return;
    swReloaded = true;
    location.reload();
  });
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js')
      .then((reg) => reg.update())
      .catch(() => { /* hors ligne indisponible, l'app reste utilisable en ligne */ });
  });
}

$('themeToggle').onclick = toggleTheme;
applyTheme(currentTheme()); // synchronise le libellé du bouton avec l'attribut posé au chargement
bindControls();
drawBeatCurve();
refreshReport();
updateReadout(null);
requestAnimationFrame(renderLoop);
if (new URLSearchParams(location.search).get('gen')) startAudio();
