// Sons de synthèse pour le contrôle de la prise (test/prise.test.mjs, test/outils/prise_sessions.mjs) :
// un accordéon qui joue des notes et se tait, avec les défauts d'une chaîne de micro qu'on lui ajoute.

import { ControlePrise } from '../web/js/dsp/prise.js';

let graine = 0x9e3779b9;
export function alea() {
  graine = (graine + 0x6d2b79f5) >>> 0;
  let x = graine;
  x = Math.imul(x ^ (x >>> 15), x | 1);
  x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
  return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
}
export const gauss = () => Math.sqrt(-2 * Math.log(alea() + 1e-12)) * Math.cos(2 * Math.PI * alea());
export const lin = (db) => 10 ** (db / 20);

// Un accordéon de synthèse : des notes de 5 s (anche à 4 partiels) séparées de
// pauses de 2 s où il ne reste que le bruit du soufflet, plus la chaîne du
// micro (`opts`). Rend un Float32Array quantifié sur 16 bits.
//   niveaux : niveau de chaque note (dBFS, crête de la fondamentale)
//   bruitDb : bruit du soufflet dans les pauses (dBFS, écart type)
//   hum     : crête (dBFS) du ronflement à 50 Hz (et 100, 150), ou null
//   porte   : 'zeros' (porte dure : plages de zéros) | 'plancher' (atténuation à ~1,3 LSB) | null
//   agc     : force du gain automatique (0 = aucun)
//   bruitFc : fréquence de coupure (Hz) du bruit de fond (v69) ; null : blanc
//   coupure : porte réelle (v69) : niveau (dBFS, blocs de 5 ms) sous lequel elle se ferme en zéros exacts, juste après chaque note ; null : aucune
export function accordeon(sec, sr, opts = {}) {
  const { niveaux = [-32, -42, -36, -46], bruitDb = -74, hum = null, humHz = 50, porte = null, agc = 0, ampli = 1, coupure = null, bruitFc = null } = opts;
  const n = Math.floor(sec * sr);
  const x = new Float32Array(n);
  const cycle = 7 * sr, note = 5 * sr;
  const freqs = [196, 220.5, 261.9, 329.8];
  const bruitSig = lin(bruitDb);
  let bruitLP = 0;
  const aLP = bruitFc ? 1 - Math.exp(-2 * Math.PI * bruitFc / sr) : 1, gainLP = Math.sqrt((2 - aLP) / aLP);       // bruit passe-bas (le soufflet et une chaîne filtrée : des suites de petites valeurs, donc des plages de zéros après quantification), même écart type
  for (let i = 0; i < n; i++) {
    const k = Math.floor(i / cycle), j = i % cycle;
    let v;
    if (bruitFc) { bruitLP += aLP * (gauss() - bruitLP); v = bruitSig * bruitLP * gainLP; } else v = bruitSig * gauss();
    if (j < note) {
      const a = lin(niveaux[k % niveaux.length]);
      const env = Math.min(1, j / (0.05 * sr)) * Math.min(1, (note - j) / (0.05 * sr));
      const f = freqs[k % freqs.length];
      for (let h = 1; h <= 4; h++) v += env * (a / h) * Math.sin(2 * Math.PI * f * h * i / sr);
    }
    if (hum != null) for (let h = 1; h <= 3; h++) v += lin(hum) / h * Math.sin(2 * Math.PI * humHz * h * i / sr + h);
    x[i] = v;
  }
  if (agc > 0) {
    // Gain automatique : enveloppe du son (attaque 10 ms, relâchement 0,5 s), le
    // gain baisse quand le niveau monte (compression d'un rapport 1/(1+agc)).
    let e = 1e-4;
    const at = 1 - Math.exp(-1 / (0.01 * sr)), re = 1 - Math.exp(-1 / (0.5 * sr));
    for (let i = 0; i < n; i++) {
      const a = Math.abs(x[i]);
      e += (a > e ? at : re) * (a - e);
      const dbNiveau = 20 * Math.log10(e + 1e-9);
      const gainDb = -agc * (dbNiveau + 55);
      x[i] *= lin(Math.max(-30, Math.min(30, gainDb)));
    }
  }
  if (porte) {
    // Porte : enveloppe rapide ; sous -62 dBFS pendant 0,5 s, elle se ferme.
    const bloc = Math.round(0.005 * sr);
    let ferme = false, calme = 0;
    for (let o = 0; o + bloc <= n; o += bloc) {
      let s = 0;
      for (let i = o; i < o + bloc; i++) s += x[i] * x[i];
      const db = 10 * Math.log10(s / bloc + 1e-20);
      if (db < -62) calme++; else calme = 0, ferme = false;
      if (calme > 100) ferme = true;   // maintien de 0,5 s
      if (ferme) {
        // La porte flotte : fermée 15 ms, entrouverte 5 ms.
        const ouvre = porte === 'zeros' && Math.floor(o / bloc) % 4 === 0;
        for (let i = o; i < o + bloc; i++) x[i] = porte === 'zeros' ? (ouvre ? x[i] : 0) : x[i] * lin(-16);
      }
    }
  }
  if (coupure != null) {
    // v69 (I4a) : porte RÉELLE d'un suppresseur de bruit : elle se ferme (zéros exacts) dès que le niveau, par blocs de 5 ms, reste sous `coupure` dBFS
    // pendant 100 ms, c'est-à-dire juste après la fin d'une note ; les 300 premières ms elle bat (un bloc sur quatre rouvre), puis elle reste fermée.
    const bloc = Math.round(0.005 * sr), nb = Math.floor(n / bloc), niv = new Float64Array(nb);
    for (let b = 0; b < nb; b++) { let t = 0; for (let i = b * bloc; i < (b + 1) * bloc; i++) t += x[i] * x[i]; niv[b] = 10 * Math.log10(t / bloc + 1e-20); }
    let calme = 0, depuis = -1;
    for (let b = 0; b < nb; b++) {
      if (niv[b] < coupure) calme++; else { calme = 0; depuis = -1; }
      if (calme > 20) {
        if (depuis < 0) depuis = b;
        const bat = b - depuis < 60 && (b - depuis) % 4 === 0;
        if (!bat) for (let i = b * bloc; i < (b + 1) * bloc; i++) x[i] = 0;
      }
    }
  }
  for (let i = 0; i < n; i++) x[i] = Math.max(-1, Math.min(1, Math.round(x[i] * ampli * 32768) / 32768));
  return x;
}

// L'état est relu à chaque image du moteur (toutes les 4096 échantillons) : c'est lui qui date les épisodes.
export function passer(x, sr, { blocs = 512, c = new ControlePrise(sr) } = {}) {
  for (let o = 0, k = 0; o + blocs <= x.length; o += blocs) {
    c.alimenter(x.subarray(o, o + blocs));
    if (++k % 8 === 0) c.etat();
  }
  return { c, e: c.etat() };
}

