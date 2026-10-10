// Session longue : où vont les morceaux pendant l'enregistrement, comment on
// les retrouve après un plantage, et comment ils redeviennent un ZIP (WAV,
// CSV, JSON) sans jamais être chargés en entier.
//
// Un stockage par plateforme, tous avec les mêmes fonctions :
//   disque   Electron : fichiers dans le dossier de l'application
//            (electron/sessions.js, par le pont du preload : sessionEcrire...) ;
//   opfs     navigateur et Android : Origin Private File System
//            (navigator.storage.getDirectory), le plus rapide ;
//   idb      sinon IndexedDB, un Blob par morceau (Chrome les garde sur disque) ;
//   memoire  dernier recours (navigateur sans stockage) : 10 min au plus.
//
// Une session = un dossier `session-AAAA-MM-JJ-hh-mm-ss` :
//   manifeste.json   écrit avant le premier morceau, puis après chacun ;
//   000000.pcm       le son du morceau, Int16 mono (petit-boutiste) ;
//   000000.csv       les lignes du CSV de ce morceau (sans en-tête).
// Un morceau ne compte que si son .pcm ET son .csv sont là (inventaire) :
// une session coupée par un plantage se récupère au prochain lancement.

import { enteteWav, enteteCsv, nomSession, MORCEAU_S } from './session-format.js';
import { zipPlan, crc32 } from './zip.js';

export const RE_ID_SESSION = /^session-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}(-\d{1,3})?$/;
export const RE_FICHIER_SESSION = /^(\d{6}\.(pcm|csv)|manifeste\.json)$/;
export const MANIFESTE = 'manifeste.json';
export const nomMorceau = (i, ext) => `${String(i).padStart(6, '0')}.${ext}`;
// Marge laissée libre sur le disque, et durée au plus sans vrai stockage.
export const MARGE_OCTETS = 200 * 1024 * 1024;
export const MAX_S_MEMOIRE = 600;

const enc = new TextEncoder();
const octetsDe = (d) => (typeof d === 'string' ? enc.encode(d)
  : d instanceof Uint8Array ? d : new Uint8Array(d.buffer, d.byteOffset, d.byteLength));

// Octets par seconde attendus : le son (Int16) et ~10 Ko/s de CSV.
export const octetsParSeconde = (sr = 48000) => 2 * sr + 10000;

// Durée possible (s) avec `libre` octets, la marge gardée.
export const dureePossible = (libre, sr = 48000) => Math.max(0, Math.floor((libre - MARGE_OCTETS) / octetsParSeconde(sr)));

// ---- Stockages ---------------------------------------------------------------------

async function espaceNavigateur() {
  const st = globalThis.navigator?.storage;
  if (!st?.estimate) return null;
  const { quota = 0, usage = 0 } = await st.estimate();
  return { libre: Math.max(0, quota - usage), quota, utilise: usage };
}

// En mémoire (tests, navigateur sans stockage).
export function stockageMemoire() {
  const sessions = new Map();
  const de = (id, creer) => {
    if (!sessions.has(id) && creer) sessions.set(id, new Map());
    return sessions.get(id);
  };
  return {
    type: 'memoire',
    async ecrire(id, nom, d) { de(id, true).set(nom, octetsDe(d).slice()); },
    async lire(id, nom) { const o = de(id)?.get(nom); return o ? new Blob([o]) : null; },
    async ids() { return [...sessions.keys()]; },
    async fichiers(id) { return Object.fromEntries([...(de(id) ?? new Map())].map(([n, o]) => [n, o.length])); },
    async effacer(id) { sessions.delete(id); },
    async espace() { return null; },
  };
}

// Origin Private File System : un dossier `sessions`, un sous-dossier par
// session. `createWritable` écrit à côté puis remplace à la fermeture : un
// fichier est entier ou absent.
export async function stockageOpfs(racine) {
  const dossier = await racine.getDirectoryHandle('sessions', { create: true });
  const sous = (id, create = false) => dossier.getDirectoryHandle(id, { create });
  return {
    type: 'opfs',
    async ecrire(id, nom, d) {
      const f = await (await sous(id, true)).getFileHandle(nom, { create: true });
      const w = await f.createWritable();
      try { await w.write(octetsDe(d)); } finally { await w.close(); }
    },
    async lire(id, nom) {
      try { return await (await (await sous(id)).getFileHandle(nom)).getFile(); } catch { return null; }
    },
    async ids() {
      const out = [];
      for await (const [nom, h] of dossier.entries()) if (h.kind === 'directory' && RE_ID_SESSION.test(nom)) out.push(nom);
      return out;
    },
    async fichiers(id) {
      const out = {};
      try {
        for await (const [nom, h] of (await sous(id)).entries()) {
          if (h.kind === 'file' && RE_FICHIER_SESSION.test(nom)) out[nom] = (await h.getFile()).size;
        }
      } catch { /* session absente */ }
      return out;
    },
    async effacer(id) {
      try { await dossier.removeEntry(id, { recursive: true }); } catch { /* déjà partie */ }
    },
    espace: espaceNavigateur,
  };
}

// IndexedDB : base `aal-sessions`, un magasin `fichiers`, clé [id, nom],
// valeur un Blob (Chrome et le WebView d'Android les gardent sur disque).
export function stockageIdb(idb = globalThis.indexedDB, nomBase = 'aal-sessions', Plage = globalThis.IDBKeyRange) {
  let base = null;
  const ouvrir = () => (base ??= new Promise((ok, ko) => {
    const r = idb.open(nomBase, 1);
    r.onupgradeneeded = () => r.result.createObjectStore('fichiers');
    r.onsuccess = () => ok(r.result);
    r.onerror = () => ko(r.error);
  }));
  const requete = async (mode, faire) => {
    const db = await ouvrir();
    return new Promise((ok, ko) => {
      const tx = db.transaction('fichiers', mode);
      const r = faire(tx.objectStore('fichiers'));
      tx.oncomplete = () => ok(r?.result);
      tx.onerror = () => ko(tx.error);
      tx.onabort = () => ko(tx.error);
    });
  };
  const plage = (id) => Plage.bound([id, ''], [id, '\uffff']);
  return {
    type: 'idb',
    ecrire: (id, nom, d) => requete('readwrite', (s) => s.put(new Blob([octetsDe(d)]), [id, nom])).then(() => {}),
    lire: async (id, nom) => (await requete('readonly', (s) => s.get([id, nom]))) ?? null,
    async ids() {
      const cles = await requete('readonly', (s) => s.getAllKeys());
      return [...new Set(cles.map((k) => k[0]))].filter((id) => RE_ID_SESSION.test(id));
    },
    async fichiers(id) {
      const db = await ouvrir();
      return new Promise((ok, ko) => {
        const out = {};
        const tx = db.transaction('fichiers', 'readonly');
        const c = tx.objectStore('fichiers').openCursor(plage(id));
        c.onsuccess = () => {
          const k = c.result;
          if (!k) return;
          out[k.key[1]] = k.value?.size ?? 0;
          k.continue();
        };
        tx.oncomplete = () => ok(out);
        tx.onerror = () => ko(tx.error);
      });
    },
    effacer: (id) => requete('readwrite', (s) => s.delete(plage(id))).then(() => {}),
    espace: espaceNavigateur,
  };
}

// Electron : le preload (electron/preload.cjs) écrit dans le dossier de
// l'application ; l'export s'écrit directement sur le disque.
export function stockageDisque(pont) {
  const une = async (id) => (await pont.sessionLister(id))?.find((s) => s.id === id) ?? null;
  return {
    type: 'disque',
    ecrire: (id, nom, d) => pont.sessionEcrire(id, nom, typeof d === 'string' ? d : octetsDe(d)),
    finir: (id, json) => pont.sessionFinir(id, json),
    async lire() { return null; },
    async ids() { return (await pont.sessionLister()).map((s) => s.id); },
    async manifeste(id) { return (await une(id))?.manifeste ?? null; },
    async fichiers(id) { return (await une(id))?.fichiers ?? {}; },
    effacer: (id) => pont.sessionEffacer(id),
    espace: () => pont.sessionEspace(),
    exporter: (id, options) => pont.sessionExporter(id, options),
  };
}

// Le meilleur stockage de la plateforme. `pont` : celui du preload d'Electron
// (avec sessionEcrire), s'il y en a un.
export async function choisirStockage({
  pont = null, navigateur = globalThis.navigator, idb = globalThis.indexedDB,
} = {}) {
  if (pont?.sessionEcrire) return stockageDisque(pont);
  try {
    if (navigateur?.storage?.getDirectory && globalThis.FileSystemFileHandle?.prototype?.createWritable) {
      return await stockageOpfs(await navigateur.storage.getDirectory());
    }
  } catch { /* OPFS refusé (navigation privée) : IndexedDB */ }
  if (idb) return stockageIdb(idb);
  return stockageMemoire();
}

// ---- Inventaire, reprise -----------------------------------------------------------

export async function lireManifeste(stockage, id) {
  try {
    if (stockage.manifeste) return await stockage.manifeste(id);
    const b = await stockage.lire(id, MANIFESTE);
    return b ? JSON.parse(await b.text()) : null;
  } catch { return null; }
}

// Ce qui est vraiment écrit : les morceaux 0..k-1 qui ont leur .pcm et leur
// .csv (au plus `limite`), leurs tailles, le nombre d'échantillons.
export async function inventaire(stockage, id, limite = Infinity) {
  const man = await lireManifeste(stockage, id);
  const f = await stockage.fichiers(id);
  const pcm = [], csv = [];
  for (let i = 0; i < limite; i++) {
    const p = f[nomMorceau(i, 'pcm')], c = f[nomMorceau(i, 'csv')];
    if (p == null || c == null) break;
    pcm.push(p - (p % 2)); csv.push(c);
  }
  const octetsPcm = pcm.reduce((a, b) => a + b, 0);
  const octetsCsv = csv.reduce((a, b) => a + b, 0);
  return { id, man, morceaux: pcm.length, pcm, csv, echantillons: octetsPcm / 2, octetsPcm, octetsCsv };
}

// Les sessions gardées, la plus récente d'abord : { id, debut, fin, secondes,
// octets, morceaux, mesures, interrompue, plein, sr }. `enCours` : l'id de la
// session qu'on enregistre (elle n'est pas « interrompue »).
export async function listerSessions(stockage, enCours = null) {
  const out = [];
  for (const id of await stockage.ids()) {
    const inv = await inventaire(stockage, id);
    const m = inv.man;
    if (!m?.sr) continue; // rien d'utilisable (coupée avant le premier morceau)
    out.push({
      id, debut: m.debut ?? null, fin: m.fin ?? null, sr: m.sr, morceaux: inv.morceaux,
      secondes: inv.echantillons / m.sr, octets: inv.octetsPcm + inv.octetsCsv, mesures: m.mesures ?? 0,
      plein: !!m.plein, interrompue: !m.fin && id !== enCours, recuperee: !!m.interrompue, exportee: m.exportee ?? null,
    });
  }
  return out.sort((a, b) => (a.id < b.id ? 1 : -1));
}

async function ecrireManifeste(stockage, id, man) {
  const json = JSON.stringify(man);
  if (stockage.finir && man.fin) await stockage.finir(id, json);
  else await stockage.ecrire(id, MANIFESTE, json);
}

// Session interrompue (plantage, page fermée) : elle est close sur ce qui est
// vraiment écrit, et devient exportable comme les autres.
export async function recupererSession(stockage, id, date = new Date()) {
  const inv = await inventaire(stockage, id);
  if (!inv.man?.sr) throw new Error('session illisible'); // interne
  const man = { ...inv.man, morceaux: inv.morceaux, echantillons: inv.echantillons,
    octets: inv.octetsPcm + inv.octetsCsv, fin: date.toISOString(), interrompue: true };
  await ecrireManifeste(stockage, id, man);
  return man;
}

// ---- Enregistrement ------------------------------------------------------------------

// Reçoit les morceaux du Worker (message devMorceau : { sr, pcm, csv,
// mesures, cfg }) et les écrit dans l'ordre, un à la fois. Le manifeste est
// écrit avant le premier morceau, puis après chacun.
export class Enregistreur {
  constructor(stockage, { maxS = 3600, contexte = {}, date = new Date(), gen = 0 } = {}) {
    this.stockage = stockage;
    this.gen = gen;
    this.maxS = stockage.type === 'memoire' ? Math.min(maxS, MAX_S_MEMOIRE) : maxS;
    this.maxVoulu = maxS;
    this.id = nomSession(date);
    this.man = {
      format: 'session-recherche', v: 1, id: this.id, debut: date.toISOString(), maj: null, fin: null,
      sr: null, morceaux: 0, echantillons: 0, mesures: 0, octets: 0, plein: false, maxS: this.maxS,
      stockage: stockage.type, contexte, cfg: null,
    };
    this.erreur = null;
    this.espace = null;
    this.historique = [];   // une ligne par morceau (carte « session » du mode recherche)
    this.file = Promise.resolve();
    this.pret = this.preparer();
  }

  // Stockage persistant (le navigateur ne vide pas la session pour faire de
  // la place), espace libre, durée réduite si le disque ne suffit pas.
  async preparer() {
    try { await globalThis.navigator?.storage?.persist?.(); } catch { /* refusé : on continue */ }
    try {
      const ids = new Set(await this.stockage.ids());
      for (let k = 2; ids.has(this.id); k++) this.id = `${nomSession(new Date(this.man.debut))}-${k}`;
      this.man.id = this.id;
    } catch (e) { this.erreur = String(e?.message ?? e); return; }
    try { this.espace = await this.stockage.espace(); } catch { this.espace = null; }
    if (this.espace?.libre != null) {
      const possible = dureePossible(this.espace.libre);
      if (possible < this.maxS) {
        this.maxS = possible;
        this.man.maxS = possible;
        this.limiteEspace = true;
      }
      if (possible < 60) this.erreur = 'espace';
    }
  }

  // Durée maximale changée en cours de route : bornée par le disque (ce qui
  // est déjà écrit, plus ce que l'espace libre permet encore).
  changerMax(maxS) {
    this.maxVoulu = maxS;
    let m = this.stockage.type === 'memoire' ? Math.min(maxS, MAX_S_MEMOIRE) : maxS;
    if (this.espace?.libre != null) {
      const sr = this.man.sr ?? 48000;
      m = Math.min(m, this.man.echantillons / sr + dureePossible(this.espace.libre, sr));
      this.limiteEspace = m < maxS;
    }
    this.maxS = m;
    this.man.maxS = m;
  }

  ajouter(m) {
    this.file = this.file.then(() => this.ecrireMorceau(m));
    return this.file;
  }

  async ecrireMorceau(m) {
    await this.pret;
    if (this.erreur || this.man.plein || this.man.fin) return;
    try {
      const man = this.man;
      if (!man.sr) {
        man.sr = m.sr;
        man.cfg = m.cfg ?? null;
        await this.stockage.ecrire(this.id, MANIFESTE, JSON.stringify(man));
      }
      const maxN = Math.round(this.maxS * man.sr);
      let pcm = m.pcm ?? new Int16Array(0);
      if (man.echantillons + pcm.length >= maxN) {
        pcm = pcm.subarray(0, Math.max(0, maxN - man.echantillons));
        man.plein = true;
      }
      const csv = enc.encode(m.csv ?? '');
      if (pcm.length || csv.length) {
        const i = man.morceaux;
        await this.stockage.ecrire(this.id, nomMorceau(i, 'pcm'), pcm);
        await this.stockage.ecrire(this.id, nomMorceau(i, 'csv'), csv);
        man.morceaux++;
        man.echantillons += pcm.length;
        man.mesures += m.mesures ?? 0;
        man.octets += pcm.byteLength + csv.length;
      }
      if (m.cfg) man.cfg = m.cfg;
      man.maj = new Date().toISOString();
      await this.stockage.ecrire(this.id, MANIFESTE, JSON.stringify(man));
      // Espace libre relu toutes les minutes (6 morceaux).
      if (man.morceaux % 6 === 1) { try { this.espace = await this.stockage.espace(); } catch { /* garde l'ancien */ } }
      this.historique.push({ morceau: man.morceaux - 1, t: man.echantillons / man.sr, echantillons: man.echantillons,
        mesures: man.mesures, octets: man.octets, libre: this.espace?.libre ?? null });
      if (this.historique.length > 1000) this.historique.shift();
    } catch (e) {
      this.erreur = String(e?.message ?? e);
    }
  }

  // Attend que tout ce qui est reçu soit écrit.
  vider() { return this.file; }

  // Clôt la session : plus rien n'y entre.
  finir(date = new Date()) {
    this.file = this.file.then(async () => {
      await this.pret;
      if (this.man.fin) return;
      this.man.fin = date.toISOString();
      if (!this.man.sr) return; // rien reçu : rien sur le disque d'utile
      try { await ecrireManifeste(this.stockage, this.id, this.man); } catch (e) { this.erreur = String(e?.message ?? e); }
    });
    return this.file.then(() => this.man);
  }

  // État pour l'interface : durée, taille, morceaux, espace.
  etat() {
    const m = this.man;
    return {
      id: this.id, secondes: m.sr ? m.echantillons / m.sr : 0, mesures: m.mesures, octets: m.octets,
      morceaux: m.morceaux, plein: m.plein, maxS: this.maxS, maxVoulu: this.maxVoulu, limiteEspace: !!this.limiteEspace,
      stockage: this.stockage.type, libre: this.espace?.libre ?? null, erreur: this.erreur, morceauS: MORCEAU_S,
      historique: this.historique,
    };
  }
}

// ---- Export ------------------------------------------------------------------------

// Le plan du ZIP d'une session (zip.js) : WAV (en-tête puis morceaux .pcm),
// CSV (en-tête puis morceaux .csv), JSON. `partie(nom)` rend une partie
// (Blob, chemin...) ; `crcDe(partie, prec)` son CRC-32 ajouté à `prec`.
export async function planSession({ inv, json, date = new Date(), partie, crcDe }) {
  const sr = inv.man.sr;
  const tetes = { wav: enteteWav(inv.echantillons, sr), csv: enc.encode(enteteCsv()), json: enc.encode(json) };
  const pcm = [], csv = [];
  for (let i = 0; i < inv.morceaux; i++) {
    pcm.push(await partie(nomMorceau(i, 'pcm')));
    csv.push(await partie(nomMorceau(i, 'csv')));
  }
  let crcWav = crc32(tetes.wav);
  for (const p of pcm) crcWav = await crcDe(p, crcWav);
  let crcCsv = crc32(tetes.csv);
  for (const p of csv) crcCsv = await crcDe(p, crcCsv);
  return zipPlan([
    { nom: `${inv.id}.wav`, taille: tetes.wav.length + inv.octetsPcm, crc: crcWav, parties: [tetes.wav, ...pcm] },
    { nom: `${inv.id}.csv`, taille: tetes.csv.length + inv.octetsCsv, crc: crcCsv, parties: [tetes.csv, ...csv] },
    { nom: `${inv.id}.json`, taille: tetes.json.length, crc: crc32(tetes.json), parties: [tetes.json] },
  ], date);
}

// CRC d'un Blob, lu par tranches de 4 Mo.
export async function crcBlob(blob, prec = 0) {
  let c = prec;
  for (let o = 0; o < blob.size; o += 4 << 20) c = crc32(new Uint8Array(await blob.slice(o, o + (4 << 20)).arrayBuffer()), c);
  return c;
}

// Exporte une session : Electron l'écrit sur le disque (rend { nom, chemin,
// octets }) ; ailleurs, un Blob composé des morceaux gardés (rend { nom,
// blob, octets }), que le navigateur enregistre sans le charger.
// `meta(man, inv)` : l'objet du JSON. `limite` : morceaux au plus (une
// session en cours s'exporte telle qu'elle est à cet instant).
export async function exporterSession(stockage, id, { meta = () => ({}), date = new Date(), limite = Infinity } = {}) {
  const inv = await inventaire(stockage, id, limite);
  if (!inv.man?.sr || !inv.echantillons) throw new Error('vide'); // interne : l'interface le dit avec ses mots
  const json = JSON.stringify(meta(inv.man, inv), null, 2);
  const nom = `${id}.zip`;
  let r;
  if (stockage.exporter) {
    const e = await stockage.exporter(id, { nomZip: nom, json, morceaux: inv.morceaux, date: date.toISOString() });
    r = { nom, chemin: e.chemin, octets: e.octets };
  } else {
    const pieces = await planSession({ inv, json, date, partie: (n) => stockage.lire(id, n), crcDe: crcBlob });
    const blob = new Blob(pieces, { type: 'application/zip' });
    r = { nom, blob, octets: blob.size };
  }
  // Marque « exportée » dans le manifeste (la liste le montre).
  try {
    const man = await lireManifeste(stockage, id);
    if (man) {
      man.exportee = date.toISOString();
      if (man.fin) await ecrireManifeste(stockage, id, man);
    }
  } catch { /* la marque n'est qu'une aide */ }
  return r;
}
