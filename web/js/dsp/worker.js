// Worker DSP : reçoit l'audio du AudioWorklet via un MessagePort dédié
// (sans passer par le thread principal) et renvoie les analyses au thread
// principal pour l'affichage.
//
// Mode dev (session de recherche) : le Worker garde aussi le son brut et
// chaque mesure, datés sur la MÊME horloge (le compteur d'échantillons du
// moteur). À l'export, la mesure du temps t correspond exactement à l'instant
// t du WAV. Session longue (60 min par défaut, 120 au plus, Ewen 07/10/2026) :
// rien ne s'accumule ici. Le son est converti en Int16 au fil de l'eau et
// rendu au thread principal par morceaux de MORCEAU_S secondes, avec les
// lignes du CSV de ces secondes (message devMorceau) ; la page les écrit hors
// de la mémoire vive (session-stockage.js).

import { Engine } from './engine.js';
import { ExecutantWorker } from './cert-calcul.js';
import { LecteurNote } from './lecteur-note.js';
import { ControlePrise } from './prise.js';
import { RetireSecteur } from './secteur.js';
import { CompteurTrames, copierPlan, Retard } from './lecture.js';
import { SuiviRegistre } from './registre-reel.js';
import { JournalSession } from './journal-session.js';
import {
  MORCEAU_S, versInt16, rangeesTick, lignesCsv, lireEnteteWav, echantillonsWav,
} from '../session-format.js';

let engine = null;

// Moteur neuf. v66 (F4) : le calcul du certificat (ajustements des anches) tourne dans un Worker dédié ; sans Worker imbriqué, ou s'il plante, le moteur calcule en ligne
// (cfg.certificat.MS_PAR_IMAGE, réglé par adapterBudget selon le temps que l'image prend).
function nouveauMoteur(sr, cfg) {
  const e = new Engine(sr, cfg || {});
  if (typeof Worker !== 'undefined' && cfg?.certificat?.EXEC !== 'ligne' && cfg?.certificat?.actif !== false) {
    try { e.certExec = new ExecutantWorker(); } catch { e.certExec = null; }
  }
  return e;
}
function finirMoteur() {
  try { engine?.certExec?.arreter?.(); } catch { /* sans effet */ }
}
const PERIODE_IMAGE_MS = 85;
function adapterBudget(dspMs) {
  const c = engine?.cfg?.certificat;
  if (!c || engine.certExec || !c.MS_PAR_IMAGE) return;
  if (dspMs > 0.6 * PERIODE_IMAGE_MS) c.MS_PAR_IMAGE = Math.max(8, c.MS_PAR_IMAGE - 6);
  else if (dspMs < 0.4 * PERIODE_IMAGE_MS) c.MS_PAR_IMAGE = Math.min(60, c.MS_PAR_IMAGE + 2);
}

// Contrôle de la prise de son (prise.js) : regarde les échantillons et, en lecture directe, les dates des blocs.
// Chaque image du moteur porte `prise` ({ douteuse, codes }) ; la page reçoit un message `prise` quand les défauts
// changent (le texte, le geste à faire : prise-micro.js).
let controle = null, priseCle = '';
// Trames perdues du flux (lecture.js, lot F2) : compteur de la session, dans le CSV et le JSON.
let trames = null;
// Retrait du ronflement du secteur (secteur.js, v62) : ce que le moteur et le verrou reçoivent est le signal sans ronflement ;
// l'enregistrement de la session garde le signal BRUT (la preuve). Allumé par défaut dès que le contrôle détecte le ronflement.
let retire = null, retireVoulu = true;
function nouveauControle(sr, cfg = null) {
  controle = new ControlePrise(sr, cfg?.trousCourts != null ? { trousCourts: !!cfg.trousCourts } : {});
  trames = new CompteurTrames(sr);
  suiviRegistre = new SuiviRegistre();
  controle.retireSecteur = retireVoulu;
  retire = new RetireSecteur(sr);
  priseCle = '';
  return controle;
}
function priseEtat(force = false) {
  if (!controle) return null;
  const e = controle.etat();
  const cle = e.codes.join('+');
  if (force || cle !== priseCle) {
    priseCle = cle;
    self.postMessage({ type: 'prise', etat: e, resume: controle.resume(), secteur: retire?.actif ? { f0: retire.f0, harmoniques: retire.h } : null });
  }
  return e;
}

// --- verrou de phase expérimental (v59) : coupé par défaut ; éteint, rien de ce bloc ne tourne ------------------------------------------
// Le son et les images vont à `LecteurNote`, qui découpe les notes ; chaque note part dans un second Worker (verrou-worker.js) : le calcul
// (7 s pour une note de 9 s) ne gêne ni la mesure ni l'interface. Le moteur ne reçoit rien de plus : ses images restent celles de la v58.
let verrouOn = false, lecteur = null, verrouWorker = null, verrouOccupe = false, verrouFile = null;
function verrouLire(note) {
  if (verrouOccupe) { verrouFile = note; return; }   // une seule lecture à la fois ; la plus récente attend
  try {
    verrouWorker ??= new Worker(new URL('./verrou-worker.js', import.meta.url), { type: 'module' });
  } catch (err) {
    self.postMessage({ type: 'verrou', lecture: { sure: false, raison: 'erreur', erreur: 'Worker' } });
    return;
  }
  verrouOccupe = true;
  verrouWorker.onmessage = (e) => {
    verrouOccupe = false;
    jEcran.lectureVerrou(e.data, tSession(), note.midi);
    self.postMessage({ type: 'verrou', lecture: e.data });
    if (verrouFile) { const n = verrouFile; verrouFile = null; verrouLire(n); }
  };
  verrouWorker.onerror = () => { verrouOccupe = false; self.postMessage({ type: 'verrou', lecture: { sure: false, raison: 'erreur', erreur: 'calcul' } }); };
  verrouWorker.postMessage(note, [note.x.buffer]);
  self.postMessage({ type: 'verrou', lecture: { calcul: true, midi: note.midi, t: note.t } });
}
function verrouRegler(on) {
  if (dev && engine && !!on !== verrouOn) jEcran.caseVerrou(on, tSession());
  verrouOn = !!on;
  if (!verrouOn) { lecteur = null; verrouFile = null; }
}

// --- enregistrement de session (mode dev) ------------------------------------
let devMaxS = 3600;                 // durée maximale (s), réglée par la page
let devGen = 0;                     // numéro de la session (une nouvelle à chaque début)
let dev = null;                     // { gen, index, start, n, maxN, pcm, fill, csv, ticks, ticksM, full }

// Journal de la session (lot F2) : ce qui change en route et que le CSV seul ne dit pas. Registre réglé (mode, registre,
// accord) à chaque changement, mode léger du calcul (« calcul lent ») à chaque passage ; datés en secondes de la session.
// Rien de tout cela n'est affiché : il est écrit dans le CSV (colonnes) et le JSON.
let journal = { registre: [], calcul: [] }, journalRegistreCle = null, journalLente = null;
let suiviRegistre = null;
const jEcran = new JournalSession();   // lot G1 (D4) : La et réglages datés, chiffre affiché, sauts d'horloge, lectures du verrou (journal-session.js)
const tSession = () => (dev && engine ? Math.round((engine.samplesTotal - dev.start) / engine.sr * 1000) / 1000 : 0);
function journalRegistre() {
  if (!dev || !engine) return;
  const c = engine.cfg;
  const cle = `${c.mode}|${c.register}|${c.chordType}|${(c.chordDegrees ?? []).join(',')}`;
  if (cle === journalRegistreCle) return;
  journalRegistreCle = cle;
  journal.registre.push({ t_s: tSession(), mode: c.mode, registre: c.mode === 'register' ? c.register : null, accord: c.mode === 'chord' ? c.chordType ?? null : null });
}
function journalCalcul() {
  if (!dev || !engine) return;
  const lente = !!engine.lente;
  if (lente === journalLente) return;
  journalLente = lente;
  journal.calcul.push({ t_s: tSession(), lente, ms_froid: engine.msFroid != null ? Math.round(engine.msFroid) : null });
}

function devStart() {
  const sr = engine.sr;
  journal = { registre: [], calcul: [] }; journalRegistreCle = null; journalLente = null;
  dev = { gen: ++devGen, index: 0, start: engine.samplesTotal, n: 0, maxN: Math.round(devMaxS * sr),
    pcm: new Int16Array(MORCEAU_S * sr), fill: 0, csv: [], ticks: 0, ticksM: 0, full: false,
    debutMs: Date.now(), priseT0: controle ? controle.temps : 0 };
  dspEchantillons = [];
  journalRegistre(); journalCalcul();
  jEcran.demarrer(engine.cfg, verrouOn);
}

// Rend le morceau en cours (son et lignes du CSV), s'il y a quelque chose.
function devFlush() {
  if (!dev || (dev.fill === 0 && dev.csv.length === 0)) return;
  const pcm = dev.fill === dev.pcm.length ? dev.pcm : dev.pcm.slice(0, dev.fill);
  self.postMessage({ type: 'devMorceau', gen: dev.gen, index: dev.index, sr: engine.sr, pcm,
    csv: dev.csv.join(''), mesures: dev.ticksM, cfg: dev.index === 0 ? engine.cfg : undefined,
    n: dev.n, ticks: dev.ticks, full: dev.full,
    // Le début réel de la session (et non l'arrivée du premier morceau, 10 s plus tard) ; le contrôle de la prise.
    debutMs: dev.debutMs,
    prise: controle ? { episodes: controle.episodesSession(dev.priseT0), trous: controle.trousSession(dev.priseT0), resume: { ...controle.resume(), ...(trames?.resume() ?? {}), ...jEcran.compteur(engine.detHorloge) }, calcul: calculStats() } : undefined,
    // Lot F2 : registres réglés et passages du calcul en mode léger, trames perdues datées (le dernier morceau a tout).
    journal: { ...jEcran.json(engine.detHorloge, dev.start / engine.sr), registre: journal.registre, calcul: journal.calcul, trames: trames ? { ...trames.resume(), evenements: trames.evenements.slice(-200).map((e) => ({ ...e, t_s: Math.round((e.t_s - (dev.priseT0 ?? 0)) * 1000) / 1000 })) } : null },
  }, [pcm.buffer]);
  dev.index++;
  dev.pcm = new Int16Array(MORCEAU_S * engine.sr);
  dev.fill = 0; dev.csv = []; dev.ticksM = 0;
}

function devAppend(chunk) {
  if (!dev || dev.full) return;
  let i = 0;
  while (i < chunk.length && !dev.full) {
    const n = Math.min(chunk.length - i, dev.pcm.length - dev.fill, dev.maxN - dev.n);
    versInt16(chunk.subarray(i, i + n), dev.pcm, dev.fill);
    dev.fill += n; dev.n += n; i += n;
    if (dev.n >= dev.maxN) dev.full = true;
    if (dev.fill === dev.pcm.length || dev.full) devFlush();
  }
}

// Une ligne par anche et par mesure : ce qu'il faut pour rejouer l'analyse.
function devTick(r) {
  if (!dev || dev.full) return;
  const t = r.time - dev.start / engine.sr;
  jEcran.image(r);
  dev.csv.push(lignesCsv({ t, midi: r.playedMidi, level: r.level, quiet: r.quiet ? 1 : 0, rows: rangeesTick(r),
    sens: r.sens ?? null, sensSource: r.soufflet?.source ?? null, inversions: r.soufflet?.inversions ?? null,
    prise: r.prise?.codes?.join('+') ?? '', trou: r.prise?.trou ?? '',
    registre: engine.cfg.mode === 'register' ? engine.cfg.register : engine.cfg.mode,
    perdues: trames?.perdues ?? 0, calcul: engine.lente ? 'lent' : '',
    a4: engine.cfg?.a4 ?? null, aff: jEcran.affiches(r), saut: r.prise?.sautHorloge?.actif ? r.prise.sautHorloge.deltaCents : null, verrou: verrouOn ? 1 : 0 },
    engine.cfg?.transpose || 0));
  dev.ticks++; dev.ticksM++;
}

function devStatus() {
  return dev ? { seconds: dev.n / engine.sr, ticks: dev.ticks, full: dev.full, maxS: devMaxS, morceaux: dev.index } : null;
}

// v69 (I5) : la vitesse de calcul de CETTE machine, pour la mesurer avant de régler MS_LENT (le facteur 4 d'un téléphone est une hypothèse) : durée moyenne d'un ajustement
// à froid (`msFroid`), mode léger (`lente`), temps de calcul par image de 85 ms (médiane et p99 des dernières images de la session).
const DSP_GARDE = 8000;
let dspEchantillons = [];
function calculStats() {
  const v = dspEchantillons.slice().sort((a, b) => a - b), q = (p) => (v.length ? Math.round(v[Math.min(v.length - 1, Math.floor(p * v.length))] * 100) / 100 : null);
  return { msFroid: engine?.msFroid != null ? Math.round(engine.msFroid) : null, lente: !!engine?.lente, dspMs: { n: v.length, p50: q(0.5), p99: q(0.99) } };
}

function onChunk(chunk) {
  if (!engine) return;
  devAppend(chunk);
  controle?.alimenter(chunk);
  const propre = retire?.actif ? retire.traiter(chunk) : chunk;
  if (retire?.actif) controle?.alimenterNet(propre);
  const t0 = performance.now();
  const result = engine.process(propre);
  if (verrouOn) {
    if (!lecteur || lecteur.sr !== engine.sr) lecteur = new LecteurNote(engine.sr, verrouLire);
    lecteur.alimenter(propre, result);
  }
  if (result) {
    // Charge DSP : temps de calcul rapporté à la période d'analyse.
    result.dspMs = performance.now() - t0;
    adapterBudget(result.dspMs);
    dspEchantillons.push(result.dspMs);
    if (dspEchantillons.length > DSP_GARDE) dspEchantillons.shift();
    result.calcul = { msFroid: engine.msFroid != null ? Math.round(engine.msFroid) : null, lente: !!engine.lente };
    journalCalcul();
    result.registreEcart = suiviRegistre?.maj(result, engine.cfg) ?? null;
    const prise = priseEtat();
    if (prise) {
      // Le contrôle a vu un ronflement : l'annuleur se règle (fréquence réelle du secteur, harmoniques présentes).
      const dem = controle.demandeSecteur();
      if (dem) { retire.regler(dem.f0, dem.harmoniques); controle.secteurActif(true); }
      result.prise = { ...result.prise, douteuse: prise.douteuse, codes: prise.codes, secteurHz: retire.actif ? retire.frequences() : null };
      if (prise.trou !== undefined) { result.prise.ecartee = prise.ecartee; result.prise.repere = prise.repere; result.prise.trou = prise.trou; }   // v71 (F1)
    }
    devTick(result);
    if (dev) result.dev = devStatus();
    // Les spectres sont transférés (zéro copie) plutôt que clonés.
    const transfer = [];
    if (result.coarseSpectrum) transfer.push(result.coarseSpectrum.buffer);
    for (const g of result.groups) if (g.spectrum) transfer.push(g.spectrum.buffer);
    self.postMessage(result, transfer);
  }
}

// Micro lu DIRECTEMENT (MediaStreamTrackProcessor), à l'horloge du micro.
//
// Par le chemin Web Audio (AudioContext → AudioWorklet), Chrome fait passer
// le micro dans un rééchantillonneur qui rattrape la dérive entre l'horloge
// du micro et celle de la sortie son, en changeant son rapport par à-coups.
// Mesuré sur un enregistrement d'Ewen (téléphone, 24/09/2026) : TOUT le son
// — la note, mais aussi le ronflement du secteur à 50 Hz, qui lui ne bouge
// jamais — sautait de ±6 ¢ toutes les ~2 s, même dans les silences. C'était
// les « signaux carrés » de la courbe : l'anche, elle, ne sautait pas.
// Ici, chaque bloc arrive tel que le micro l'a échantillonné.
// Un bloc du micro (date en µs, fréquence, premier canal en Float32) : le moteur est créé à la fréquence réelle au premier
// bloc ; les blocs de 512 échantillons partent au moteur. Commun à la lecture dans ce Worker (readStream) et à la lecture
// par le Worker léger (lecture-worker.js, drapeau LECTURE_DECOUPLEE).
let blocTampon = new Float32Array(0), blocRempli = 0;
let charge = 0, debutIt = 0;   // durée de traitement d'un bloc, la plus forte des dernières (retard du Worker : prise.js, bloc)
function entrerBloc(ts, sr, plan, format, canaux) {
  const HOPS = 512;
  try {
    if (!engine || engine.sr !== sr) {
      const cfg = engine ? engine.cfg : pendingCfg;
      finirMoteur(); engine = nouveauMoteur(sr, cfg);
      nouveauControle(sr, cfg);
      if (dev || pendingDev) devStart();
      self.postMessage({ type: 'capture', direct: true, sampleRate: sr, format, canaux });
      priseEtat(true);
    }
    const n = plan.length;
    controle?.bloc(ts, n, charge);
    trames?.bloc(ts, n);
    debutIt = performance.now();
    if (blocTampon.length < blocRempli + n) { const b = new Float32Array(2 * (blocRempli + n)); b.set(blocTampon.subarray(0, blocRempli)); blocTampon = b; }
    blocTampon.set(plan, blocRempli);
    blocRempli += n;
    let o = 0;
    for (; o + HOPS <= blocRempli; o += HOPS) onChunk(blocTampon.slice(o, o + HOPS));
    blocTampon.copyWithin(0, o, blocRempli); blocRempli -= o;
  } finally {
    charge = Math.max(performance.now() - debutIt, charge * 0.98);
  }
}
function reprendreFlux() {
  finirMoteur();
  engine = null;
  blocTampon = new Float32Array(0); blocRempli = 0; charge = 0;
}

async function readStream(readable) {
  const reader = readable.getReader();
  for (;;) {
    const { value: ad, done } = await reader.read();
    if (done) break;
    try {
      const plan = copierPlan(ad, new Float32Array(ad.numberOfFrames));
      entrerBloc(ad.timestamp, ad.sampleRate, plan, ad.format, ad.numberOfChannels);
    } finally {
      ad.close();
    }
  }
}

// Un enregistrement (WAV) rejoué à la place du micro, lu par morceaux : un
// WAV de 60 min (345 Mo) n'est jamais chargé en entier (decodeAudioData en
// faisait 691 Mo de Float32). Premier canal, à sa fréquence d'échantillonnage
// (sans rééchantillonnage), au rythme du temps réel × `vitesse`.
let fichierEnCours = 0;
async function lireFichier(blob, vitesse = 1) {
  const jeton = ++fichierEnCours;
  const tete = new Uint8Array(await blob.slice(0, Math.min(blob.size, 1 << 16)).arrayBuffer());
  const info = lireEnteteWav(tete, blob.size);
  if (!info) throw new Error('WAV illisible'); // interne
  finirMoteur(); engine = nouveauMoteur(info.sr, pendingCfg);
  nouveauControle(info.sr, pendingCfg);
  if (dev || pendingDev) devStart();
  self.postMessage({ type: 'capture', direct: false, sampleRate: info.sr, fichier: true, duree: info.n / info.sr });
  priseEtat(true);
  const HOPS = 512;
  const parLecture = Math.max(1, Math.round(info.sr / 2)) * info.bloc; // une demi-seconde à la fois
  let pos = info.debut;
  const fin = info.debut + info.taille;
  let file = new Float32Array(0), o = 0;   // échantillons lus, pas encore donnés au moteur
  let donnes = 0;                          // échantillons donnés au moteur
  const t0 = performance.now();
  const v = Math.min(64, Math.max(0.25, Number(vitesse) || 1));
  while (jeton === fichierEnCours) {
    if (file.length - o < HOPS) {
      if (pos >= fin) break;
      const b = Math.min(parLecture, fin - pos);
      const x = echantillonsWav(new Uint8Array(await blob.slice(pos, pos + b).arrayBuffer()), info);
      pos += b;
      const reste = file.subarray(o);
      file = new Float32Array(reste.length + x.length);
      file.set(reste); file.set(x, reste.length); o = 0;
      continue;
    }
    // Au rythme du temps réel : pas plus que le temps écoulé (+ 50 ms).
    const permis = ((performance.now() - t0) / 1000 + 0.05) * info.sr * v;
    if (donnes + HOPS > permis) { await new Promise((ok) => setTimeout(ok, 10)); continue; }
    onChunk(file.slice(o, o + HOPS));
    o += HOPS; donnes += HOPS;
  }
  if (jeton === fichierEnCours) self.postMessage({ type: 'fichierFin', secondes: donnes / info.sr });
}

let pendingCfg = null, pendingDev = false;

// Fin de session : le morceau en cours, puis « fini » (les messages
// arrivent dans l'ordre : la page a tout reçu quand elle lit devFin).
function devFin(req) {
  const gen = dev?.gen ?? null;
  const full = !!dev?.full;
  devFlush();
  dev = null;
  self.postMessage({ type: 'devFin', gen, full, req });
}

self.onmessage = (e) => {
  const d = e.data;
  if (d.type === 'init') {
    finirMoteur(); engine = nouveauMoteur(d.sampleRate, d.cfg);
    nouveauControle(d.sampleRate, d.cfg);
    pendingCfg = d.cfg || {}; pendingDev = !!d.dev;
    verrouRegler(d.verrou);
    if (d.devMaxS > 0) devMaxS = d.devMaxS;
    if (d.dev) devStart();
    if (d.port) d.port.onmessage = (ev) => onChunk(ev.data);
  } else if (d.type === 'stream') {
    // Le moteur est recréé à la fréquence réelle du micro au premier bloc.
    reprendreFlux();
    readStream(d.readable).catch((err) => self.postMessage({ type: 'capture', error: String(err) }));
  } else if (d.type === 'lecture') {
    // Lecture découplée (lecture-worker.js) : les blocs arrivent par le port, déjà copiés en Float32.
    reprendreFlux();
    const retard = new Retard();
    d.port.onmessage = (ev) => {
      const m = ev.data;
      // Le bloc a attendu (m.t : l'heure où le lecteur l'a posté) ; trop de retard : écarté (lecture.js, Retard).
      if (m.pcm) { if (retard.garder(Date.now() - m.t)) entrerBloc(m.ts, m.sr, m.pcm, m.format, m.canaux); }
      else if (m.erreur) self.postMessage({ type: 'capture', error: m.erreur });
    };
  } else if (d.type === 'fichier') {
    lireFichier(d.blob, d.vitesse).catch((err) => self.postMessage({ type: 'capture', error: String(err?.message ?? err) }));
  } else if (d.type === 'verrou') {
    verrouRegler(d.on);
  } else if (d.type === 'priseMuet') {
    // Mesure coupée voulue (annonce vocale, son de référence) : des zéros, mais pas une porte.
    controle?.suspendre(d.muet);
  } else if (d.type === 'retireSecteur') {
    // Réglage : retirer (true, par défaut) ou laisser le ronflement.
    retireVoulu = d.on !== false;
    if (controle) controle.retireSecteur = retireVoulu;
    if (!retireVoulu) { retire?.arreter(); controle?.secteurActif(false); }
  } else if (d.type === 'priseMicro') {
    // Ce que la page sait du micro par son nom (prise-micro.js) : Bluetooth, mains libres.
    for (const code of ['bluetooth']) { if (d.codes?.includes(code)) controle?.declarer(code, d.detail ?? {}); else controle?.retirer(code); }
  } else if (d.type === 'config') {
    pendingCfg = { ...(pendingCfg || {}), ...d.cfg };
    if (dev && engine) jEcran.config(d.cfg, engine.cfg, tSession());   // D4 : le La, le registre, l'instrument changent en route : datés
    engine?.configure(d.cfg);
    journalRegistre();
    if (controle && d.cfg?.trousCourts != null) controle.s.trousCourts = !!d.cfg.trousCourts;
  } else if (d.type === 'dev') {
    // { on, maxS } : marche ou arrêt, durée maximale (réduite si le disque
    // ne suffit pas). Arrêt : le morceau en cours part avant (devFin).
    if (d.maxS > 0) {
      devMaxS = d.maxS;
      if (dev) {
        dev.maxN = Math.round(devMaxS * engine.sr);
        if (dev.n >= dev.maxN && !dev.full) { dev.full = true; devFlush(); }
      }
    }
    pendingDev = !!d.on;
    if (d.on) { if (!dev && engine) devStart(); } else if (dev) devFin(null);
    self.postMessage({ type: 'devStatus', dev: devStatus() });
  } else if (d.type === 'devFlush') {
    // Export pendant l'enregistrement : le morceau en cours part tout de suite.
    devFlush();
    self.postMessage({ type: 'devFlushOk', req: d.req, gen: dev?.gen ?? null });
  } else if (d.type === 'devFin') {
    devFin(d.req);
  } else if (d.type === 'devClear') {
    // Effacer : la session en cours est abandonnée (la page l'efface), une
    // nouvelle commence.
    if (dev) { const gen = dev.gen; dev = null; self.postMessage({ type: 'devAbandon', gen }); devStart(); }
    self.postMessage({ type: 'devStatus', dev: devStatus() });
  }
};
