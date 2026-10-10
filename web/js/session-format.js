// Session longue (Ewen, 07/10/2026 : « 60 min au lieu de 10, pour suivre tout
// l'accordage ») : formats communs au Worker, à la page, à Electron et aux
// tests sous Node. Pur, sans DOM.
//
// 60 min de son à 48 kHz : 691 Mo en Float32, 345 Mo en Int16. Rien ne reste
// en mémoire : le Worker convertit en Int16 au fil de l'eau et rend un
// « morceau » toutes les MORCEAU_S secondes (le son et les lignes du CSV de
// ces secondes) ; la page l'écrit hors de la mémoire vive (session-stockage.js).
// L'export assemble le WAV (en-tête écrit à la fin, quand la longueur est
// connue) et le CSV morceau par morceau.

import { noteLabel } from './music.js';

export const MORCEAU_S = 10;                         // un morceau : 10 s (960 Ko à 48 kHz)
export const DUREES_SESSION_MIN = Object.freeze([10, 30, 60, 120]);
export const DUREE_SESSION_DEFAUT = 60;              // minutes (mode luthier)

// Durée maximale permise (minutes), sinon la durée par défaut.
export const dureeSession = (m) => (DUREES_SESSION_MIN.includes(Number(m)) ? Number(m) : DUREE_SESSION_DEFAUT);

// Float32 [-1, 1] -> Int16 (même arrondi que la v28, worker.js:24-28).
export function versInt16(x, out = new Int16Array(x.length), o = 0) {
  for (let i = 0; i < x.length; i++) {
    const s = x[i] > 1 ? 1 : x[i] < -1 ? -1 : x[i];
    out[o + i] = s < 0 ? s * 32768 : s * 32767;
  }
  return out;
}

// En-tête WAV de 44 octets, mono 16 bits, pour `n` échantillons.
export function enteteWav(n, sr) {
  const octets = 2 * n;
  if (octets + 36 > 0xffffffff) throw new Error('WAV > 4 Go'); // interne : 120 min à 96 kHz = 1,4 Go
  const u = new Uint8Array(44);
  const v = new DataView(u.buffer);
  const str = (o, x) => { for (let i = 0; i < x.length; i++) u[o + i] = x.charCodeAt(i); };
  str(0, 'RIFF'); v.setUint32(4, 36 + octets, true); str(8, 'WAVE');
  str(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, 2 * sr, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, 'data'); v.setUint32(40, octets, true);
  return u;
}

// En-tête d'un WAV quelconque, lu sur ses premiers octets (64 Ko suffisent) :
// { codage: 'entier' | 'flottant', bits, canaux, sr, bloc, debut, taille, n }
// ou null si ce n'est pas un WAV lisible par morceaux. `tailleFichier` borne
// la taille des données (un enregistreur coupé laisse 0 ou 0xFFFFFFFF).
export function lireEnteteWav(octets, tailleFichier = octets.length) {
  const u = octets instanceof Uint8Array ? octets : new Uint8Array(octets);
  if (u.length < 12) return null;
  const v = new DataView(u.buffer, u.byteOffset, u.byteLength);
  const id = (o) => String.fromCharCode(u[o], u[o + 1], u[o + 2], u[o + 3]);
  if (id(0) !== 'RIFF' || id(8) !== 'WAVE') return null;
  let o = 12;
  let fmt = null;
  while (o + 8 <= u.length) {
    const nom = id(o);
    const taille = v.getUint32(o + 4, true);
    if (nom === 'fmt ' && o + 8 + 16 <= u.length) {
      let format = v.getUint16(o + 8, true);
      const canaux = v.getUint16(o + 10, true);
      const sr = v.getUint32(o + 12, true);
      const bloc = v.getUint16(o + 20, true);
      const bits = v.getUint16(o + 22, true);
      // WAVE_FORMAT_EXTENSIBLE : le vrai format est au début du GUID.
      if (format === 0xfffe && taille >= 40 && o + 8 + 26 <= u.length) format = v.getUint16(o + 8 + 24, true);
      fmt = { format, canaux, sr, bloc, bits };
    } else if (nom === 'data') {
      if (!fmt) return null;
      const debut = o + 8;
      const reste = Math.max(0, tailleFichier - debut);
      const t = taille === 0 || taille === 0xffffffff || taille > reste ? reste : taille;
      const { format, canaux, sr, bloc, bits } = fmt;
      const codage = format === 1 ? 'entier' : format === 3 ? 'flottant' : null;
      if (!codage || !canaux || !sr || !bloc || bloc !== canaux * bits / 8) return null;
      if (codage === 'entier' && ![8, 16, 24, 32].includes(bits)) return null;
      if (codage === 'flottant' && ![32, 64].includes(bits)) return null;
      const tailleUtile = t - (t % bloc);
      return { codage, bits, canaux, sr, bloc, debut, taille: tailleUtile, n: tailleUtile / bloc };
    }
    o += 8 + taille + (taille & 1);
  }
  return null;
}

// Échantillons d'un morceau de WAV (octets alignés sur le bloc), premier
// canal, en Float32 : ce que l'AudioWorklet recevait d'un fichier rejoué
// (inputs[0][0], capture-worklet.js).
export function echantillonsWav(octets, info) {
  const u = octets instanceof Uint8Array ? octets : new Uint8Array(octets);
  const v = new DataView(u.buffer, u.byteOffset, u.byteLength);
  const n = Math.floor(u.length / info.bloc);
  const x = new Float32Array(n);
  const b = info.bloc;
  if (info.codage === 'flottant') {
    if (info.bits === 32) for (let i = 0; i < n; i++) x[i] = v.getFloat32(i * b, true);
    else for (let i = 0; i < n; i++) x[i] = v.getFloat64(i * b, true);
  } else if (info.bits === 16) {
    for (let i = 0; i < n; i++) x[i] = v.getInt16(i * b, true) / 32768;
  } else if (info.bits === 24) {
    for (let i = 0; i < n; i++) {
      const o = i * b;
      const s = (u[o] | (u[o + 1] << 8) | (u[o + 2] << 16)) << 8 >> 8;
      x[i] = s / 8388608;
    }
  } else if (info.bits === 32) {
    for (let i = 0; i < n; i++) x[i] = v.getInt32(i * b, true) / 2147483648;
  } else {
    for (let i = 0; i < n; i++) x[i] = (u[i * b] - 128) / 128;
  }
  return x;
}

// ---- CSV de la session ---------------------------------------------------------------
// Colonnes (devCsv, app.js:2012-2015) : une ligne par anche et par mesure ;
// t_s = fin de la fenêtre d'analyse, même horloge que le WAV.
export const PARTIELS_CSV = 8;
export const COLONNES_SESSION = Object.freeze([
  't_s', 'note', 'midi', 'niveau_db', 'silence', 'groupe', 'anche', 'label', 'harmonique',
  'k_suivi', 'cible_hz', 'f_hz', 'ecart_cents', 'amp_db', 'confondue_octave', 'estimation_rapide',
  'maintenue', 'fenetre_s', 'remplissage',
  ...Array.from({ length: PARTIELS_CSV }, (_, i) => `p${i + 1}_hz`),
  // Anche confondue avec l'octave (v41) : estimation, marge, méthode, signe connu.
  'estimee_hz', 'estimee_cents', 'marge_cents', 'methode', 'signe_connu',
]);

// Début du CSV : marque UTF-8 (le tableur lit les accents) et colonnes.
export const enteteCsv = () => `\ufeff${COLONNES_SESSION.join(';')}\n`;

// Une ligne par anche d'une image du moteur : ce qu'il faut pour rejouer
// l'analyse (devTick, worker.js de la v41).
export function rangeesTick(r) {
  const rows = [];
  for (const g of r.groups ?? []) {
    if (g.isSub) continue;
    for (const v of g.voices) {
      const p = {};
      if (g.partials) for (const k of Object.keys(g.partials)) {
        const f = g.partials[k]?.[v.def.id];
        if (f != null) p[k] = f;
      }
      rows.push({
        g: g.key, id: v.def.id, label: v.def.label ?? '', harm: g.isHarmonic ? 1 : 0,
        k: g.kTrack, target: v.target, f: v.tracked ? v.fMeas : null,
        c: v.tracked ? v.dTargetCents : null, amp: v.amp ?? 0,
        merged: v.merged ? 1 : 0, coarse: v.coarse ? 1 : 0, held: v.held ? 1 : 0,
        W: g.W, srd: g.srd, fill: g.fill, p,
        // Anche confondue avec l'octave (confondu.js) : estimation et marge.
        conf: v.confondu ? { f: v.fEstimee ?? null, c: v.centsEstimesCible ?? null, m: v.margeCents ?? null,
          methode: v.methode ?? '', signe: v.signeConnu ? 1 : 0 } : null,
      });
    }
  }
  return rows;
}

// Les lignes du CSV d'une mesure `tk` = { t, midi, level, quiet, rows },
// séparateur « ; », point décimal, chacune finie par « \n ».
export function lignesCsv(tk, transpose = 0) {
  const num = (x, d) => (x == null || !Number.isFinite(x) ? '' : x.toFixed(d));
  const note = tk.midi != null ? noteLabel(tk.midi + transpose).full : '';
  const db = num(20 * Math.log10((tk.level ?? 0) + 1e-9), 1);
  let s = '';
  for (const r of tk.rows ?? []) {
    const l = [num(tk.t, 4), note, tk.midi ?? '', db, tk.quiet, r.g, r.id,
      String(r.label ?? '').replace(/[;\n]/g, ' '), r.harm, r.k, num(r.target, 5), num(r.f, 5), num(r.c, 4),
      num(20 * Math.log10((r.amp ?? 0) + 1e-9), 1), r.merged, r.coarse, r.held,
      num(r.srd ? r.W / r.srd : null, 3), num(r.fill, 3)];
    for (let k = 1; k <= PARTIELS_CSV; k++) l.push(num(r.p?.[k], 5));
    l.push(num(r.conf?.f, 5), num(r.conf?.c, 4), num(r.conf?.m, 4), r.conf?.methode ?? '', r.conf ? r.conf.signe : '');
    s += `${l.join(';')}\n`;
  }
  return s;
}

// Nom de base : session-2026-10-06-14-30-00 (comme la v28).
export const nomSession = (d = new Date()) => `session-${d.toISOString().slice(0, 19).replace(/[:T]/g, '-')}`;
