// Archive ZIP minimale (fichiers stockés, sans compression), sans dépendance.
// Deux formes : `zipBytes` (tout en mémoire, petites archives) et `zipPlan`
// (session longue : la liste des pièces de l'archive, en-têtes en octets et
// données laissées où elles sont : Blob, fichier sur disque ; rien n'est
// chargé en entier).
//
// Le mode dev exportait trois fichiers d'affilée (WAV, CSV, JSON). Sur
// téléphone, le navigateur n'autorise qu'un téléchargement par geste : seul
// le WAV arrivait (constaté par Ewen le 24/09/2026). Un seul fichier .zip
// les contient tous les trois.

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

// CRC-32 de `bytes` ; `prec` : le CRC des octets d'avant (calcul par morceaux).
export function crc32(bytes, prec = 0) {
  let c = (prec ^ 0xffffffff) >>> 0;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

const dosTemps = (date) => ({
  heure: (date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() >> 1),
  jour: ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate(),
});

// En-tête local (30 octets + nom) ou central (46 octets + nom) d'une entrée
// stockée, noms en UTF-8.
function entete(nom, taille, crc, dos, central, offset = 0) {
  const u = new Uint8Array((central ? 46 : 30) + nom.length);
  const v = new DataView(u.buffer);
  let o = 0;
  v.setUint32(o, central ? 0x02014b50 : 0x04034b50, true); o += 4;
  if (central) { v.setUint16(o, 20, true); o += 2; }     // version créatrice
  v.setUint16(o, 20, true); o += 2;                       // version requise
  v.setUint16(o, 0x0800, true); o += 2;                   // noms en UTF-8
  v.setUint16(o, 0, true); o += 2;                        // stocké
  v.setUint16(o, dos.heure, true); o += 2;
  v.setUint16(o, dos.jour, true); o += 2;
  v.setUint32(o, crc, true); o += 4;
  v.setUint32(o, taille, true); o += 4;
  v.setUint32(o, taille, true); o += 4;
  v.setUint16(o, nom.length, true); o += 2;
  v.setUint16(o, 0, true); o += 2;                        // champ extra
  if (central) {
    o += 10;                                              // commentaire, disque, attributs internes et externes
    v.setUint32(o, offset, true); o += 4;
  }
  u.set(nom, o);
  return u;
}

// files : [{ name, data: Uint8Array | string }] → Uint8Array (le .zip).
export function zipBytes(files, date = new Date()) {
  const enc = new TextEncoder();
  const pieces = zipPlan(files.map((f) => {
    const data = typeof f.data === 'string' ? enc.encode(f.data) : f.data;
    return { nom: f.name, taille: data.length, crc: crc32(data), parties: [data] };
  }), date);
  const out = new Uint8Array(pieces.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of pieces) { out.set(p, o); o += p.length; }
  return out;
}

// Plan d'un ZIP stocké dont les données ne sont pas en mémoire.
// `entrees` : [{ nom, taille, crc, parties: [...] }], `taille` = somme des
// tailles des parties, `crc` = leur CRC-32 (crc32 par morceaux). Rend la suite
// des pièces de l'archive, dans l'ordre : des Uint8Array (en-têtes, fin du
// répertoire central) et les parties telles quelles (Blob, chemin, octets).
// Plus de 4 Go : refusé (ZIP64 sans objet : 120 min en Int16 à 48 kHz = 691 Mo).
export function zipPlan(entrees, date = new Date()) {
  const enc = new TextEncoder();
  const dos = dosTemps(date);
  const pieces = [];
  const centraux = [];
  let o = 0;
  for (const e of entrees) {
    const nom = enc.encode(e.nom);
    const local = entete(nom, e.taille, e.crc, dos, false);
    centraux.push(entete(nom, e.taille, e.crc, dos, true, o));
    pieces.push(local, ...e.parties);
    o += local.length + e.taille;
  }
  const debutCentral = o;
  for (const c of centraux) { pieces.push(c); o += c.length; }
  if (o + 22 > 0xffffffff) throw new Error('ZIP > 4 Go'); // interne
  const fin = new Uint8Array(22);
  const v = new DataView(fin.buffer);
  v.setUint32(0, 0x06054b50, true);
  v.setUint16(8, entrees.length, true);
  v.setUint16(10, entrees.length, true);
  v.setUint32(12, o - debutCentral, true);
  v.setUint32(16, debutCentral, true);
  pieces.push(fin);
  return pieces;
}
