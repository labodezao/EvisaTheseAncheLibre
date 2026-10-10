// Session longue (v42) : le son en Int16 au fil de l'eau,
// écrit par morceaux de 10 s hors de la mémoire vive, le CSV aussi, l'export
// assemblé sans tout charger, la limite, la reprise après un plantage, le
// rejeu d'un WAV par morceaux. Le Worker est le vrai (web/js/dsp/worker.js,
// chargé avec un faux `self`), le moteur aussi ; stockages : mémoire et OPFS
// (imitation de l'API en mémoire).
// Exécution : node --expose-gc test/session-longue.test.mjs

import { Engine } from '../web/js/dsp/engine.js';
import {
  versInt16, enteteWav, lireEnteteWav, echantillonsWav, rangeesTick, lignesCsv, enteteCsv, COLONNES_SESSION,
  MORCEAU_S, dureeSession,
} from '../web/js/session-format.js';
import {
  Enregistreur, stockageMemoire, stockageOpfs, listerSessions, recupererSession, exporterSession, nomMorceau,
  MARGE_OCTETS,
} from '../web/js/session-stockage.js';
import { crc32, zipBytes } from '../web/js/zip.js';

const SR = 48000;
let failures = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ✓ ${msg}`);
  else { failures++; console.error(`  ✗ ÉCHEC : ${msg}`); }
}

function signal(sec, { f1 = 440, f2 = 441.4, graine = 7 } = {}) {
  let g = graine >>> 0;
  const alea = () => { g = (g + 0x6d2b79f5) >>> 0; let x = g; x = Math.imul(x ^ (x >>> 15), x | 1); x ^= x + Math.imul(x ^ (x >>> 7), x | 61); return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
  const n = Math.floor(SR * sec);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let h = 1; h <= 4; h++) s += (Math.sin(2 * Math.PI * f1 * h * i / SR) + Math.sin(2 * Math.PI * f2 * h * i / SR)) / h;
    out[i] = 0.1 * s + 1e-4 * (alea() * 2 - 1);
  }
  return out;
}

let numeroWorker = 0;
async function worker() {
  const messages = [];
  globalThis.self = { postMessage: (m) => messages.push(m) };
  await import(`../web/js/dsp/worker.js?essai=${++numeroWorker}`);
  const moi = globalThis.self;
  const port = {};
  return {
    messages, port,
    envoyer: (d) => moi.onmessage({ data: d }),
    jouer: (x) => { for (let i = 0; i + 512 <= x.length; i += 512) port.onmessage({ data: x.slice(i, i + 512) }); },
  };
}

const cfg = { mode: 'register', register: 'MM', response: 'fast' };
function images(x) {
  const e = new Engine(SR, cfg);
  const out = [];
  for (let i = 0; i + 512 <= x.length; i += 512) { const t = e.process(x.subarray(i, i + 512)); if (t) out.push(t); }
  return out;
}

// Lecteur de ZIP stocké (répertoire central), CRC vérifiés.
function lireZip(u) {
  const v = new DataView(u.buffer, u.byteOffset, u.byteLength);
  let fin = -1;
  for (let i = u.length - 22; i >= 0; i--) if (v.getUint32(i, true) === 0x06054b50) { fin = i; break; }
  const n = v.getUint16(fin + 10, true);
  let o = v.getUint32(fin + 16, true);
  const out = [];
  for (let i = 0; i < n; i++) {
    const crc = v.getUint32(o + 16, true), taille = v.getUint32(o + 24, true), ln = v.getUint16(o + 28, true);
    const local = v.getUint32(o + 42, true);
    const nom = new TextDecoder().decode(u.subarray(o + 46, o + 46 + ln));
    const debut = local + 30 + v.getUint16(local + 26, true) + v.getUint16(local + 28, true);
    const data = u.subarray(debut, debut + taille);
    out.push({ nom, data, crcJuste: crc32(data) === crc });
    o += 46 + ln + v.getUint16(o + 30, true) + v.getUint16(o + 32, true);
  }
  return out;
}
const texte = (o) => new TextDecoder('utf-8', { ignoreBOM: true }).decode(o);
const octets = async (b) => new Uint8Array(await b.arrayBuffer());
const meta = (man, inv) => ({ duree_s: inv.echantillons / man.sr, mesures: man.mesures, morceaux: inv.morceaux, interrompue: !!man.interrompue });

async function brancher(messages, stockage, { maxS = 3600, date = new Date('2026-10-07T10:00:00Z') } = {}) {
  let e = null;
  for (const m of messages) {
    if (m.type === 'devMorceau') {
      if (!e || e.gen !== m.gen) { if (e) e.finir(); e = new Enregistreur(stockage, { gen: m.gen, maxS, date }); }
      e.ajouter(m);
    } else if (m.type === 'devFin' && e) await e.finir();
  }
  if (e) await e.vider();
  return e;
}

// ---------------------------------------------------------------------------
console.log('\nL 1 — Int16 au fil de l\'eau, en-tête WAV');
{
  const y = versInt16(new Float32Array([-1.5, -1, -0.5, 0, 0.5, 1, 1.5]));
  assert([...y].join() === '-32768,-32768,-16384,0,16383,32767,32767', 'Float32 -> Int16, même règle que la v28');
  const i = lireEnteteWav(enteteWav(SR * 3600, SR), 44 + 2 * SR * 3600);
  assert(i.n === SR * 3600 && i.debut === 44 && i.bits === 16, '60 min : 345 Mo, sous 4 Go');
  assert(lireEnteteWav(enteteWav(0, SR), 2044).n === 1000, 'enregistreur coupé : taille lue sur le fichier');
  assert(dureeSession(45) === 60 && dureeSession(120) === 120, 'durées 10 / 30 / 60 / 120 min, 60 par défaut');
}

// ---------------------------------------------------------------------------
console.log('\nL 2 — le vrai Worker : morceaux de 10 s, CSV par morceaux, ZIP juste');
const sig = signal(25);
const n = Math.floor(sig.length / 512) * 512;
let zipPrise = null;
{
  const w = await worker();
  w.envoyer({ type: 'init', sampleRate: SR, cfg, port: w.port, dev: true, devMaxS: 3600 });
  w.jouer(sig);
  w.envoyer({ type: 'devFin', req: 1 });
  const morceaux = w.messages.filter((m) => m.type === 'devMorceau');
  assert(morceaux.length === 3 && morceaux[0].pcm.length === MORCEAU_S * SR, `3 morceaux de 10, 10 et ${(morceaux[2]?.pcm.length / SR).toFixed(2)} s`);
  const ref = versInt16(sig.subarray(0, n));
  const pcm = new Int16Array(n);
  let o = 0;
  for (const m of morceaux) { pcm.set(m.pcm, o); o += m.pcm.length; }
  assert(pcm.every((s, i) => s === ref[i]), 'morceaux bout à bout = le son en Int16');
  const csvRef = images(sig.subarray(0, n)).map((t) => lignesCsv({ t: t.time, midi: t.playedMidi, level: t.level, quiet: t.quiet ? 1 : 0, rows: rangeesTick(t),
    sens: t.sens ?? null, sensSource: t.soufflet?.source ?? null, inversions: t.soufflet?.inversions ?? null })).join('');
  assert(morceaux.map((m) => m.csv).join('') === csvRef, 'CSV par morceaux = CSV du moteur');
  const st = stockageMemoire();
  const e = await brancher(w.messages, st);
  const date = new Date('2026-10-07T10:30:00Z');
  const r = await exporterSession(st, e.id, { meta, date });
  zipPrise = await octets(r.blob);
  const ent = lireZip(zipPrise);
  assert(ent.length === 3 && ent.every((x) => x.crcJuste), `${r.nom} : WAV, CSV, JSON, CRC justes`);
  assert(lireEnteteWav(ent[0].data).n === n && texte(ent[1].data) === enteteCsv() + csvRef, 'WAV (en-tête écrit à la fin) et CSV identiques');
  const mem = zipBytes(ent.map((x) => ({ name: x.nom, data: x.data })), date);
  assert(mem.length === zipPrise.length && mem.every((b, i) => b === zipPrise[i]), 'octet pour octet le ZIP tout en mémoire');
  assert(COLONNES_SESSION[0] === 't_s' && texte(ent[1].data).startsWith('﻿'), 'CSV avec sa marque UTF-8');
}

// ---------------------------------------------------------------------------
console.log('\nL 3 — limite atteinte : arrêt propre');
{
  const w = await worker();
  w.envoyer({ type: 'init', sampleRate: SR, cfg, port: w.port, dev: true, devMaxS: 15 });
  w.jouer(sig);
  const morceaux = w.messages.filter((m) => m.type === 'devMorceau');
  const ticks = w.messages.filter((m) => m.type === 'tick');
  assert(morceaux.reduce((a, m) => a + m.pcm.length, 0) === 15 * SR && ticks.at(-1).dev.full, '15 s exactement, « plein », la mesure continue');
}

// ---------------------------------------------------------------------------
console.log('\nL 4 — reprise après un plantage');
{
  const st = stockageMemoire();
  const w = await worker();
  w.envoyer({ type: 'init', sampleRate: SR, cfg, port: w.port, dev: true, devMaxS: 3600 });
  w.jouer(sig);
  const morceaux = w.messages.filter((m) => m.type === 'devMorceau');
  const e = new Enregistreur(st, { date: new Date('2026-10-07T11:00:00Z') });
  e.ajouter(morceaux[0]); e.ajouter(morceaux[1]);
  await e.vider();
  await st.ecrire(e.id, nomMorceau(2, 'pcm'), new Int16Array(10));
  const l = await listerSessions(st, null);
  assert(l[0]?.interrompue && l[0].secondes === 20, 'session interrompue : 2 morceaux entiers, 20 s');
  await recupererSession(st, l[0].id);
  const ent = lireZip(await octets((await exporterSession(st, l[0].id, { meta })).blob));
  assert(lireEnteteWav(ent[0].data).n === 20 * SR && JSON.parse(texte(ent[2].data)).interrompue, 'récupérée et exportée');
}

// ---------------------------------------------------------------------------
console.log('\nL 5 — OPFS (imitation) et place libre');
{
  const racine = opfs();
  const st = await stockageOpfs(racine);
  const w = await worker();
  w.envoyer({ type: 'init', sampleRate: SR, cfg, port: w.port, dev: true, devMaxS: 3600 });
  w.jouer(sig);
  w.envoyer({ type: 'devFin', req: 1 });
  const e = await brancher(w.messages, st);
  const z = await octets((await exporterSession(st, e.id, { meta, date: new Date('2026-10-07T10:30:00Z') })).blob);
  assert(z.length === zipPrise.length && z.every((b, i) => b === zipPrise[i]), 'OPFS : même ZIP');
  const peu = { ...stockageMemoire(), type: 'idb', espace: async () => ({ libre: MARGE_OCTETS + 30 * 60 * (2 * SR + 10000) }) };
  const e2 = new Enregistreur(peu, { maxS: 3600 });
  await e2.pret;
  assert(e2.maxS === 1800, 'place pour 30 min : durée réduite à 30 min');
}

// ---------------------------------------------------------------------------
console.log('\nL 6 — rejeu par morceaux : mêmes mesures');
{
  const wav = lireZip(zipPrise)[0].data;
  const w = await worker();
  w.envoyer({ type: 'init', sampleRate: 44100, cfg, port: w.port, dev: false });
  w.envoyer({ type: 'fichier', blob: new Blob([wav]), vitesse: 64 });
  const t0 = performance.now();
  while (!w.messages.some((m) => m.type === 'fichierFin') && performance.now() - t0 < 60000) await new Promise((ok) => setTimeout(ok, 20));
  const ticks = w.messages.filter((m) => m.type === 'tick');
  const ref = images(sig.subarray(0, n));
  const v = (t) => t?.groups?.find((g) => !g.isHarmonic)?.voices.map((x) => x.dTargetCents) ?? [];
  const ecart = Math.max(...ref.map((t, i) => Math.max(0, ...v(t).map((c, k) => Math.abs(c - (v(ticks[i])[k] ?? c))))));
  assert(w.messages.find((m) => m.type === 'capture')?.sampleRate === SR && ticks.length === ref.length && ecart < 0.001,
    `WAV lu par morceaux à sa fréquence : ${ticks.length} images, écart ${ecart.toExponential(1)} ¢`);
  assert(echantillonsWav(wav.subarray(44, 48), lireEnteteWav(wav)).length === 2, 'échantillons d\'un morceau de WAV');
}

console.log(failures ? `\n${failures} échec(s).` : '\nTous les tests de la session longue passent.');
process.exit(failures ? 1 : 0);

function opfs() {
  const dossier = () => {
    const enfants = new Map();
    return {
      kind: 'directory',
      async getDirectoryHandle(nom, { create = false } = {}) { if (!enfants.has(nom)) { if (!create) throw new Error('NotFoundError'); enfants.set(nom, dossier()); } return enfants.get(nom); },
      async getFileHandle(nom, { create = false } = {}) { if (!enfants.has(nom)) { if (!create) throw new Error('NotFoundError'); enfants.set(nom, fichier()); } return enfants.get(nom); },
      async removeEntry(nom) { enfants.delete(nom); },
      async* entries() { yield* enfants.entries(); },
    };
  };
  const fichier = () => {
    let contenu = new Uint8Array(0);
    return {
      kind: 'file',
      async getFile() { return new Blob([contenu]); },
      async createWritable() { const m = []; return { async write(o) { m.push(o.slice()); }, async close() { contenu = new Uint8Array(await new Blob(m).arrayBuffer()); } }; },
    };
  };
  return dossier();
}
