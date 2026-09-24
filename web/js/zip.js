// Archive ZIP minimale (fichiers stockés, sans compression), sans dépendance.
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

export function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// files : [{ name, data: Uint8Array | string }] → Uint8Array (le .zip).
export function zipBytes(files, date = new Date()) {
  const enc = new TextEncoder();
  const dosTime = (date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() >> 1);
  const dosDate = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  const entries = files.map((f) => {
    const data = typeof f.data === 'string' ? enc.encode(f.data) : f.data;
    return { name: enc.encode(f.name), data, crc: crc32(data) };
  });
  let size = 22;
  for (const e of entries) size += 30 + e.name.length + e.data.length + 46 + e.name.length;
  const out = new Uint8Array(size);
  const v = new DataView(out.buffer);
  let o = 0;
  const head = (e, central, offset) => {
    v.setUint32(o, central ? 0x02014b50 : 0x04034b50, true); o += 4;
    if (central) { v.setUint16(o, 20, true); o += 2; }   // version créatrice
    v.setUint16(o, 20, true); o += 2;                     // version requise
    v.setUint16(o, 0x0800, true); o += 2;                 // noms en UTF-8
    v.setUint16(o, 0, true); o += 2;                      // stocké
    v.setUint16(o, dosTime, true); o += 2;
    v.setUint16(o, dosDate, true); o += 2;
    v.setUint32(o, e.crc, true); o += 4;
    v.setUint32(o, e.data.length, true); o += 4;
    v.setUint32(o, e.data.length, true); o += 4;
    v.setUint16(o, e.name.length, true); o += 2;
    v.setUint16(o, 0, true); o += 2;                      // champ extra
    if (central) {
      v.setUint16(o, 0, true); o += 2;                    // commentaire
      v.setUint16(o, 0, true); o += 2;                    // disque
      v.setUint16(o, 0, true); o += 2;                    // attributs internes
      v.setUint32(o, 0, true); o += 4;                    // attributs externes
      v.setUint32(o, offset, true); o += 4;
    }
    out.set(e.name, o); o += e.name.length;
  };
  for (const e of entries) {
    e.offset = o;
    head(e, false);
    out.set(e.data, o); o += e.data.length;
  }
  const cd = o;
  for (const e of entries) head(e, true, e.offset);
  const cdSize = o - cd;
  v.setUint32(o, 0x06054b50, true);                       // fin du répertoire central
  v.setUint16(o + 4, 0, true);
  v.setUint16(o + 6, 0, true);
  v.setUint16(o + 8, entries.length, true);
  v.setUint16(o + 10, entries.length, true);
  v.setUint32(o + 12, cdSize, true);
  v.setUint32(o + 16, cd, true);
  v.setUint16(o + 20, 0, true);
  return out;
}
