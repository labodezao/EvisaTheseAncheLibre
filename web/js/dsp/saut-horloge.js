// Saut d'horloge de la prise (D3 de l'audit « échelons de justesse », 19/10/2026 ; lot G1 de la v71, drapeau cfg.SAUT_HORLOGE).
//
// Ce qu'on a vu (sessions du 13/10 et du 19/10, WAV compris) : le SIGNAL enregistré saute de 8 à 17 ¢ en 5 à 180 ms, sans saut de niveau, et TOUTES les raies du spectre
// sautent du même nombre de cents (les deux anches, tous les partiels, le ronflement du secteur s'il y est encore). Une anche ne fait pas cela : c'est la chaîne audio de la
// prise (horloge, rééchantillonneur). L'accordeur le suivait avec 0,3 à 2,8 s de retard (ses fenêtres de 0,3 à 5,5 s) et le montrait comme un désaccord entre les anches.
//
// Principe physique : changer la cadence de lecture multiplie TOUTES les fréquences par le même rapport. Le détecteur suit donc, raie par raie, la fréquence INSTANTANÉE (phase
// de la TFD d'une fenêtre de 43 ms, avancée sur le pas de 10,7 ms : précision bien meilleure que la case de 23 Hz, et temps de réponse de quelques dizaines de ms) pour les
// raies de plus de F_MIN_HZ, et compare chaque raie à elle-même quelques dizaines de ms plus tôt (pas à une autre raie, donc aucun étiquetage des anches : une anche seule, deux,
// trois ou un accord donnent le même verdict). Il y a saut d'horloge quand la quasi-totalité des raies suivies a bougé du même nombre de cents :
//   - au moins MIN_LIGNES raies suivies depuis plus longtemps que le retard comparé ;
//   - la médiane de leur variation dépasse SEUIL_C ¢ ;
//   - au moins P_MIN d'entre elles sont à moins de LARG_C ¢ de cette médiane (une seule anche qui saute, ou une note qui change, laisse l'autre moitié des raies immobiles :
//     ce n'est pas un saut d'horloge) ;
//   - le critère tient SUITE fois sur les FENETRE dernières images, dans le même sens (le battement déplace une raie de quelques cents, jamais toutes dans le même sens).
// Rien n'est réglé sur une session réelle : les seuils viennent de la physique (la médiane de N raies sur le bruit d'estimation d'une raie, le battement de deux anches :
// ±Ω/f en cents) et se jugent sur la synthèse et sur des enregistrements H6 auxquels on injecte un vrai saut (test/echelons-prise.test.mjs). Le signal est annoncé TENUE_S après
// la dernière image qui satisfait le critère : l'affichage tient sa valeur (ui/mesure.js), rien n'est certifié, l'événement est écrit dans le CSV (colonne saut_horloge) et le JSON.
//
// Module pur, sans état global : tourne dans le Worker et sous Node.

import { FFT, hannWindow } from './fft.js';

export const HORLOGE = {
  N: 2048,           // fenêtre de la TFD (43 ms à 48 kHz)
  PAS: 512,          // pas entre deux fenêtres (10,7 ms) ; à 1024 (21 ms) la détection recule de 53 à 48 essais sur 60 (corpus de synthèse)
  F_MIN: 500,        // Hz : sous cette fréquence 10 ¢ valent moins de 2,5 Hz, noyés par le battement des deux anches
  F_MAX: 9000,       // Hz
  PIC_DB: 40,        // raies retenues : à moins de PIC_DB du pic le plus fort
  PLANCHER: 6,       // et au moins PLANCHER fois la médiane des modules
  MAX_LIGNES: 40,
  TROU_MAX: 3,       // fenêtres sans raie qu'une piste survit
  APPARIE_C: 45,     // une raie est la même raie d'une fenêtre à la suivante à moins de (¢)
  ECART_FREQ_BINS: 0.75,  // la fréquence de phase et celle des modules (parabole) s'accordent à ce point : sinon plusieurs composantes dans la case, raie écartée
  MOY: 12,           // fenêtres moyennées (x 10,7 ms = 128 ms) : la fréquence instantanée d'une raie où deux anches se mêlent oscille de ±Ω/f0 autour de sa moyenne (battement) ; la moyenne sur une durée voisine d'une période de battement la ramène à la fréquence moyenne, que le saut d'horloge décale du même nombre de cents
  LAGS: [16, 32],    // décalage entre les deux moyennes comparées (x 10,7 ms) : 171 et 342 ms ; un pas lent (180 ms) n'est vu en entier que par le plus long
  SEUIL_C: 7,        // |médiane| minimale (¢) d un saut d horloge : les pas mesurés vont de 8 à 17 ¢ ; sous 6 ¢ on lit aussi les glissements de la pression du soufflet (un enregistrement H6 sans saut d horloge en montrait de -5,5 à +5,9 en 0,3 s)
  LARG_C: 3.5,       // dispersion : les raies qui ont bougé sont à moins de LARG_C ¢ de la médiane
  P_MIN: 0.7,        // part des raies suivies qui ont bougé comme la médiane, au moins
  MIN_LIGNES: 6,     // raies suivies, au moins
  RATIO_DB: 24,      // deux observations d une même raie ont un niveau voisin (dB) : sinon une autre raie a pris la place
  FENETRE: 8,        // le critère tient SUITE fois sur les FENETRE dernières fenêtres (le pas passe par des fenêtres où l'ancienne et la nouvelle raie coexistent)
  SUITE: 4,
  ATTAQUE_S: 1.0,    // pas de verdict dans la première seconde d'un son (l'attaque glisse de quelques cents : phase.js ; un enregistrement H6 y montrait -5 ¢ en 0,7 s)
  NIVEAU_DB: 12,     // ni quand le niveau de la bande a changé de plus de NIVEAU_DB entre les deux moyennes comparées (début ou fin de note : la hauteur glisse avec la pression) ; le battement de deux anches ne le fait pas
  PAUSE_S: 0.25,     // deux marches de même sens séparées de plus de PAUSE_S s sont deux pas
  DECALAGE_S: 0.12,  // la marche est datée DECALAGE_S s avant la fenêtre qui l'a vue (les moyennes de MOY fenêtres la voient à mi-chemin)
  TENUE_S: 2,        // durée du gel après la dernière image qui satisfait le critère (s)
};

const DEUX_PI = 2 * Math.PI;

export class DetecteurHorloge {
  constructor(sr = 48000, opts = {}) {
    this.sr = sr;
    this.p = { ...HORLOGE, ...opts };
    const { N } = this.p;
    this.fft = FFT.get(N / 2);                       // TFD d'un signal réel de N points par une TFD complexe de N/2 points (pair + i impair) : la moitié du calcul
    this.W = new Float64Array(N); for (let k = 0; k < N / 2; k++) { this.W[2 * k] = Math.cos(2 * Math.PI * k / N); this.W[2 * k + 1] = -Math.sin(2 * Math.PI * k / N); }
    this.hann = hannWindow(N);
    this.re = new Float64Array(N / 2); this.im = new Float64Array(N / 2);   // pair / impair
    this.Xr = new Float64Array(N / 2); this.Xi = new Float64Array(N / 2);   // spectre (bins utiles)
    this.anneau = new Float32Array(N); this.pos = 0; this.remplis = 0; this.depuisPas = 0;
    this.kLo = Math.max(3, Math.floor(this.p.F_MIN * N / sr)); this.kHi = Math.min(N / 2 - 3, Math.ceil(this.p.F_MAX * N / sr));
    this.phasePrec = new Float64Array(N / 2); this.phaseOk = false;
    this.mag = new Float64Array(N / 2);
    this.pistes = [];              // raies suivies : { c: Float64Array (cents par fenêtre), m: Float64Array (module), i0 (première fenêtre), derniere }
    this.nf = 0;                   // numéro de la fenêtre
    this.niveau = null;            // niveau de la bande (dB) par fenêtre, anneau
    this.R = Math.max(...this.p.LAGS) + this.p.MOY + 2;
    this.sonS = 0;                 // durée du son continu (s)
    this.tEch = 0;                 // échantillons reçus
    this.jusqua = -Infinity;
    this.epi = null;               // épisode en cours (la fenêtre où l'affichage est tenu) : { t, tSaut, deltaCents, lignes, fin }
    this.evenements = [];          // les PAS vus, un par marche : { t, tSaut, deltaCents, lignes } (CSV, JSON, compteur par minute)
    this.run = null; this.dernierPas = null;
    this.fen = [];                 // les dernières évaluations : { med | null }
    this.dernier = null;           // dernière évaluation (diagnostic)
  }

  // Un bloc d'échantillons (de n'importe quelle taille) ; `actif` : le bloc est au-dessus du seuil de silence (sinon la mémoire repart de zéro).
  ecrire(chunk, actif = true) {
    const { N, PAS } = this.p;
    for (let i = 0; i < chunk.length; i++) {
      this.anneau[this.pos] = chunk[i];
      this.pos = (this.pos + 1) % N;
      this.tEch++;
      if (this.remplis < N) this.remplis++;
      if (++this.depuisPas === PAS) {
        this.depuisPas = 0;
        if (actif && this.remplis >= N) this.fenetre(); else this.silence();
      }
    }
  }

  silence() { this.pistes.length = 0; this.phaseOk = false; this.sonS = 0; this.fen.length = 0; }

  fenetre() {
    const { N, PAS, PIC_DB, PLANCHER, MAX_LIGNES, APPARIE_C, ECART_FREQ_BINS } = this.p;
    const { re, im, hann, anneau, mag, phasePrec, kLo, kHi } = this;
    const p0 = this.pos;
    const h = N / 2;
    for (let j = 0; j < h; j++) { re[j] = anneau[(p0 + 2 * j) % N] * hann[2 * j]; im[j] = anneau[(p0 + 2 * j + 1) % N] * hann[2 * j + 1]; }
    this.fft.transform(re, im);
    // X[k] = Fe[k] + W^k Fo[k] avec Fe = (Z[k] + conj Z[h-k]) / 2 et Fo = (Z[k] - conj Z[h-k]) / 2i : seuls les bins utiles sont reconstitués
    const Xr = this.Xr, Xi = this.Xi, W = this.W;
    for (let k = kLo - 2; k <= kHi + 2; k++) {
      const a = re[k], b = im[k], c = re[(h - k) % h], d = -im[(h - k) % h];     // Z[k] et conj Z[h-k]
      const er = (a + c) / 2, ei = (b + d) / 2;
      const or = (b - d) / 2, oi = -(a - c) / 2;                                // (Z - conj Z') / 2i
      Xr[k] = er + W[2 * k] * or - W[2 * k + 1] * oi;
      Xi[k] = ei + W[2 * k] * oi + W[2 * k + 1] * or;
    }
    let pic = 0;
    for (let k = kLo - 2; k <= kHi + 2; k++) { const m = Math.hypot(Xr[k], Xi[k]); mag[k] = m; if (m > pic && k >= kLo && k <= kHi) pic = m; }
    this.sonS += PAS / this.sr;
    let e = 0;
    for (let k = kLo; k <= kHi; k++) e += mag[k] * mag[k];
    (this.niveau ??= new Float64Array(this.R))[this.nf % this.R] = 10 * Math.log10(e + 1e-30);
    const tFen = this.tEch / this.sr;
    if (!this.phaseOk) {
      // première fenêtre d'un son : pas d'avance de phase encore
      for (let k = kLo - 2; k <= kHi + 2; k++) phasePrec[k] = Math.atan2(Xi[k], Xr[k]);
      this.phaseOk = true; this.nf++;
      return;
    }
    // plancher : médiane des modules de la bande (échantillonnée : un module sur quatre)
    const tmp = [];
    for (let k = kLo; k <= kHi; k += 4) tmp.push(mag[k]);
    tmp.sort((a, b) => a - b);
    const plancher = Math.max(tmp[tmp.length >> 1] * PLANCHER, pic * 10 ** (-PIC_DB / 20));
    // raies : maxima locaux, fréquence instantanée par l'avance de phase
    const raies = [];
    for (let k = kLo; k <= kHi; k++) {
      const m = mag[k];
      if (m < plancher || !(m > mag[k - 1]) || !(m >= mag[k + 1]) || m < mag[k - 2] || m < mag[k + 2]) continue;
      const ph = Math.atan2(Xi[k], Xr[k]);
      let d = ph - phasePrec[k] - DEUX_PI * k * PAS / N;
      d -= DEUX_PI * Math.round(d / DEUX_PI);
      const bins = k + d * N / (DEUX_PI * PAS);
      const a = Math.log(mag[k - 1] + 1e-30), b = Math.log(m), c = Math.log(mag[k + 1] + 1e-30);
      const den = a - 2 * b + c;
      const parab = den < 0 ? k + 0.5 * (a - c) / den : k;
      if (Math.abs(bins - parab) > ECART_FREQ_BINS || bins <= 0) continue;
      raies.push({ c: 1200 * Math.log2(bins * this.sr / N), m });
    }
    for (let k = kLo - 2; k <= kHi + 2; k++) phasePrec[k] = Math.atan2(Xi[k], Xr[k]);
    raies.sort((x, y) => y.m - x.m);
    if (raies.length > MAX_LIGNES) raies.length = MAX_LIGNES;

    // suivi : chaque raie est rattachée à la piste vivante la plus proche (à moins de APPARIE_C de sa dernière valeur) ; une piste survit à TROU_MAX fenêtres sans raie (un creux de
    // battement, un module sous le plancher) ; les fenêtres manquées valent NaN.
    const R = this.R, nf = this.nf;
    const prises = new Set();
    for (const r of raies) {
      let best = null, bd = APPARIE_C;
      for (const pi of this.pistes) {
        if (prises.has(pi)) continue;
        const d = Math.abs(r.c - pi.dernC);
        if (d < bd) { bd = d; best = pi; }
      }
      if (best) { prises.add(best); best.c[nf % R] = r.c; best.m[nf % R] = r.m; best.derniere = nf; best.dernC += 0.4 * (r.c - best.dernC); }
      else {
        const pi = { c: new Float64Array(R).fill(NaN), m: new Float64Array(R), i0: nf, derniere: nf, dernC: r.c };
        pi.c[nf % R] = r.c; pi.m[nf % R] = r.m; prises.add(pi); this.pistes.push(pi);
      }
    }
    for (const pi of this.pistes) if (!prises.has(pi)) pi.c[nf % R] = NaN;
    this.pistes = this.pistes.filter((pi) => pi.derniere >= nf - this.p.TROU_MAX);
    this.nf = nf + 1;
    this.evaluer(tFen, nf);
  }

  // moyenne de la fréquence (cents) d'une piste sur les MOY fenêtres qui finissent à la fenêtre `fin` ; NaN si elle a manqué plus du tiers d'entre elles
  moyenne(pi, fin) {
    const { MOY } = this.p, R = this.R;
    let s = 0, n = 0;
    for (let q = 0; q < MOY; q++) { const v = pi.c[(fin - q) % R]; if (Number.isFinite(v)) { s += v; n++; } }
    return n >= MOY * 2 / 3 ? s / n : NaN;
  }

  evaluer(t, nf) {
    const p = this.p, R = this.R;
    const ratio = 10 ** (p.RATIO_DB / 20);
    let ok = false, med = 0, n = 0, bouge = 0;
    if (this.sonS >= p.ATTAQUE_S) {
      for (const lag of p.LAGS) {
        if (Math.abs(this.niveau[nf % R] - this.niveau[(nf - lag) % R]) > p.NIVEAU_DB) continue;   // début ou fin de note
        const ds = [];
        for (const pi of this.pistes) {
          if (pi.derniere !== nf || pi.i0 > nf - lag - p.MOY) continue;   // vue à cette fenêtre, et suivie depuis plus longtemps que le décalage et la moyenne
          const m1 = pi.m[nf % R], m0 = pi.m[(nf - lag) % R];
          if (m0 > 0 && (m1 > m0 * ratio || m0 > m1 * ratio)) continue;
          const a = this.moyenne(pi, nf), b = this.moyenne(pi, nf - lag);
          if (!Number.isFinite(a) || !Number.isFinite(b)) continue;
          ds.push(a - b);
        }
        if (ds.length < p.MIN_LIGNES) continue;
        const s = [...ds].sort((a, b) => a - b);
        const m = s.length % 2 ? s[s.length >> 1] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
        const proches = ds.filter((d) => Math.abs(d - m) <= p.LARG_C).length;
        const okl = Math.abs(m) >= p.SEUIL_C && proches >= p.P_MIN * ds.length;
        if (okl && (!ok || Math.abs(m) > Math.abs(med))) { ok = true; med = m; n = ds.length; bouge = proches; }
        else if (!ok && ds.length > n) { n = ds.length; med = m; bouge = proches; }
      }
    }
    this.dernier = { t, lignes: n, bouge, med, ok };
    this.fen.push({ med: ok ? med : null });
    if (this.fen.length > p.FENETRE) this.fen.shift();
    if (!ok) return;
    const touches = this.fen.filter((w) => w.med != null && Math.sign(w.med) === Math.sign(med)).length;
    if (touches < p.SUITE) return;
    this.jusqua = t + p.TENUE_S;
    // un PAS (une marche) : une suite de fenêtres qui satisfont le critère dans le même sens ; le retour d'un plateau (sens contraire) ou une marche venue après une pause
    // est un autre pas. Chaque pas est un événement du CSV / du JSON ; l'épisode (`epi`) est la fenêtre où l'affichage est tenu (les pas distants de moins de TENUE_S s'y fondent).
    const sens = Math.sign(med);
    const r = this.run;
    if (!r || r.sens !== sens || t - r.fin > p.PAUSE_S) {
      this.run = { sens, t, fin: t, med, lignes: bouge };
      const pas = { t, tSaut: t - p.DECALAGE_S, deltaCents: med, lignes: bouge };
      this.evenements.push(pas);
      this.dernierPas = pas;
      this.run.pas = pas;
    } else {
      r.fin = t;
      if (Math.abs(med) > Math.abs(r.med)) { r.med = med; r.pas.deltaCents = med; }
      r.lignes = Math.max(r.lignes, bouge); r.pas.lignes = r.lignes;
    }
    if (!this.epi || t > this.epi.fin + p.TENUE_S) this.epi = { t, tSaut: t - p.DECALAGE_S, deltaCents: med, lignes: bouge, fin: t };
    else {
      this.epi.fin = t;
      if (Math.sign(med) === Math.sign(this.epi.deltaCents) && Math.abs(med) > Math.abs(this.epi.deltaCents)) this.epi.deltaCents = med;   // le retour du plateau (signe contraire) ne change pas le Δ de l'épisode
      this.epi.lignes = Math.max(this.epi.lignes, bouge);
    }
  }

  // Une fois par image du moteur : { actif, t (première fenêtre qui l'a vu), tSaut (date estimée), deltaCents (le plus grand vu), lignes, jusqua (s), pas (nombre de marches vues), tPas, deltaPas (la dernière) } ; { actif: false } avant tout événement.
  observer(t, quiet) {
    if (quiet) this.silence();
    if (!this.epi) return { actif: false };
    return { actif: t < this.jusqua, t: this.epi.t, tSaut: this.epi.tSaut, deltaCents: this.epi.deltaCents, lignes: this.epi.lignes, jusqua: this.jusqua,
      pas: this.evenements.length, tPas: this.dernierPas?.t ?? null, deltaPas: this.dernierPas?.deltaCents ?? null };
  }
}
