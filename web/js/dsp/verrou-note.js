// Lecture d'UNE NOTE par le verrou de phase (prototype pour la v59, PAS branché dans le moteur) : de la note enregistrée aux
// fréquences des deux anches, ou un refus dit en clair (`raison`).
//
// Enchaînement (audit réel du 12/10/2026, docs/FREQUENCES-ANCHES.md « Verrou de phase par anche ») :
//   1. plage stable de la note (l'attaque de 12 à 16 ¢ est écartée ; fenêtres d'un nombre entier de battements) ;
//   2. battement Ω : l'enveloppe du volume lue ici (fondamental d'un peigne d'harmoniques, fond large retiré), confiance contrôlée ;
//      Ω·T < 2 : « Δ non résolu », le centre ± Δ/2 seulement ;
//   3. accrochage par ajustement de raies sur la plage, avec recherche d'une raie étrangère (recommandation 3) ;
//   4. contrôle d'entier de l'étiquette (recommandation 2) : la paire de porteuses est prise dans le peigne ajusté (produit des
//      amplitudes aux partiels 1 et 2, centroïde de puissance, lecture du moteur v58 s'il y en a une) ; ambiguë : refus ; puis
//      l'écart lu doit valoir le battement entendu, sinon décalage d'un Ω et nouvelle lecture ;
//   5. partiels utiles (recommandation 4) : seuls ceux dont le rapport signal sur bruit passe 20 dB (bruit mesuré entre les
//      partiels) ; le verrou ne calcule que ceux-là (c'est aussi ce qui coûte le moins) ;
//   6. verrou de phase sur la plage (consigne du soufflet = droite de la plage), lectures sur des battements entiers, médiane des
//      lectures ramenée au centre de la plage ;
//   7. « sûre » seulement si les contrôles passent : résidu de l'ajustement, dispersion des lectures, deux moitiés de la plage d'accord,
//      écart des deux anches égal au battement. Seuils fixés sur le banc fidèle (test/bench_reel.mjs), jamais sur la session d'Ewen.
import { plageStable, accrocherRaies, VerrouAnches, lireFrequences, etiqueterPaire, demodulerDecimer, reponseBoite, DECIM_HZ } from './verrou.js';
import { fenetreEntiere } from './battement.js';

export const NOTE_T_MIN_S = 2;          // plage stable la plus courte lue
export const NOTE_OMEGA_T = 2;          // Ω·T minimal : deux raies séparées d'au moins deux cases
export const NOTE_DERIVE_MAX = 0.5;     // ¢/s
export const NOTE_AGITATION_MAX = 2;    // ¢ rms (centroïde, battement compris)
export const NOTE_SNR_DB = 20;          // partiel utile : signal / bruit entre partiels
export const NOTE_K_MAX = 8;
export const NOTE_E_MAX = 0.05;         // résidu relatif de l'ajustement de raies au-delà duquel les raies ne sont pas comprises
export const NOTE_SIGMA_C = 0.05;       // ¢ : incertitude (MAD / √n) des lectures d'une anche au-delà de laquelle la lecture n'est pas sûre
export const NOTE_MOITIES_C = 0.15;     // ¢ : écart entre la première et la seconde moitié de la plage
export const NOTE_GAIN_AMBIGU = 0.5;      // résidu de l'ajustement libre / contraint en dessous duquel le battement est dit ambigu
export const NOTE_MARGE_CENTROIDE = 0.2;  // le centroïde est dans la paire des porteuses à cette fraction de battement près
export const NOTE_CONFIANCE_OMEGA = 1.5;  // score du battement / score du meilleur autre sommet de l'enveloppe
export const NOTE_PRIOR_PROCHE = 0.25;    // la lecture du moteur est à cette fraction de battement de la paire (somme des écarts des deux anches)
export const FE_REF = 700, FE_EXP = 2;   // seuil de résidu mis à l'échelle de la fréquence au-dessus de FE_REF (Hz)
export const NOTE_MARGE_ETIQUETTE = 0.7;  // deuxième paire / première (produit des amplitudes) : au-delà, le spectre ne décide pas l'étiquette
export const NOTE_ENV_MAX_HZ = 3.5;     // au-delà, l'enveloppe (4 Hz de portée) ne dit plus rien : le battement vient des raies
export const NOTE_ECART_ENTIER = 0.3;   // |f2 − f1 − Ω| / Ω toléré avant de décaler d'un battement

const cents = (a, b) => 1200 * Math.log2(a / b);
const mediane = (a) => { const s = [...a].sort((p, q) => p - q); return s.length ? s[s.length >> 1] : NaN; };

// Battement Ω (Hz) de l'enveloppe du volume autour des partiels 1 à 4 de fc : pic du spectre de l'enveloppe, de 0,15 à 4 Hz.
// Sert quand le moteur n'en donne pas. Faux quand les raies ne sont pas séparées (Δ < 1/T) : l'appelant le sait par Ω·T.
export function battementEnveloppe(x, sr, i0, i1, fc, { fmin = 0.15, fmax = 4, ks = [1, 2, 3, 4], pas = 0.005, detail = false } = {}) {
  const fe = 100, dec = Math.round(sr / fe);
  i0 += Math.round(0.5 * sr);   // l'attaque du son (montée de l'amplitude) n'est pas un battement
  const N = i1 - i0;
  const gmax = 4 * fmax, ng = Math.round((gmax - fmin) / pas) + 1;
  const somme = new Float64Array(ng), ngMax = Math.round((fmax - fmin) / pas) + 1;
  for (const k of ks) {
    if (k * fc > 0.45 * sr) break;
    const B = 5 + 4 * k, n1 = Math.max(2, Math.round(sr / B)), w = (2 * Math.PI * k * fc) / sr;
    if (Math.floor(N / dec) < 100) return null;
    const re = new Float64Array(N), im = new Float64Array(N);
    const rr = Math.cos(w), ri = Math.sin(w);
    let cr = 1, ci = 0;   // rotation complexe au lieu de cos et sin à chaque échantillon (renormalisée toutes les 1024)
    for (let n = 0; n < N; n++) {
      const v = x[i0 + n];
      re[n] = v * cr; im[n] = -v * ci;
      const t = cr * rr - ci * ri; ci = cr * ri + ci * rr; cr = t;
      if ((n & 1023) === 1023) { const m = Math.hypot(cr, ci); cr /= m; ci /= m; }
    }
    for (let passe = 0; passe < 2; passe++) {   // deux boîtes en cascade (nulles à B Hz)
      let sr_ = 0, si_ = 0;
      const qr = new Float64Array(n1), qi = new Float64Array(n1);
      for (let n = 0; n < N; n++) { const p = n % n1; sr_ += re[n] - qr[p]; si_ += im[n] - qi[p]; qr[p] = re[n]; qi[p] = im[n]; re[n] = sr_ / n1; im[n] = si_ / n1; }
    }
    const debut = 2 * n1, Mu = Math.floor((N - debut) / dec);
    if (Mu < 100) return null;
    const env = new Float64Array(Mu);
    let moy = 0;
    for (let m = 0; m < Mu; m++) { const n = debut + m * dec; env[m] = re[n] * re[n] + im[n] * im[n]; moy += env[m]; }
    moy /= Mu;
    if (!(moy > 0)) continue;
    for (let m = 0; m < Mu; m++) env[m] = (env[m] / moy - 1) * (0.5 - 0.5 * Math.cos((2 * Math.PI * m) / Mu));
    // spectre de l'enveloppe de CE partiel, normalisé par son maximum : un partiel fort (3 à 5, +5 à +18 dB) a un indice de modulation k β
    // élevé et sa bande tronquée fait de l'enveloppe à 2 Ω ; la somme pondérée par la puissance le suivait (2 Ω pris pour Ω)
    const sp = new Float64Array(ng);
    let mk = 0;
    for (let g = 0; g < ng; g++) {
      const a = (2 * Math.PI * (fmin + g * pas)) / fe;
      let cr = 0, ci = 0;
      for (let m = 0; m < Mu; m++) { cr += env[m] * Math.cos(a * m); ci -= env[m] * Math.sin(a * m); }
      sp[g] = cr * cr + ci * ci;
      if (g < ngMax && sp[g] > mk) mk = sp[g];
    }
    if (mk > 0) for (let g = 0; g < ng; g++) somme[g] += sp[g] / mk;
  }
  // Le niveau de toutes les anches bouge avec la pression (10 à 20 % rms entre 0,3 et 1 Hz) : un fond large dans l'enveloppe, d'où sortent de
  // faux sommets à Ω/2 ou à Ω/4. Le battement est une RAIE (largeur 1/T) : on retire le fond, médiane glissante sur ± 0,4 Hz.
  const demi = Math.round(0.4 / pas), fond = new Float64Array(ng);
  for (let g = 0; g < ng; g += 4) {   // médiane tous les 4 pas, interpolée : assez fin pour un fond large
    const a = Math.max(0, g - demi), b = Math.min(ng, g + demi + 1), v = Array.from(somme.subarray(a, b)).sort((p, q) => p - q);
    fond[g] = v[v.length >> 1];
  }
  for (let g = 0; g < ng; g++) { if (g % 4) { const g0 = g - (g % 4), g1 = Math.min(ng - 1, g0 + 4); fond[g] = fond[g0] + ((g - g0) / 4) * ((g1 % 4 === 0 ? fond[g1] : fond[g0]) - fond[g0]); } }
  for (let g = 0; g < ng; g++) somme[g] = Math.max(0, somme[g] - fond[g]);
  const S = (f) => { const g = (f - fmin) / pas, g0 = Math.floor(g); return g0 < 0 || g0 + 1 >= ng ? 0 : somme[g0] + (g - g0) * (somme[g0 + 1] - somme[g0]); };
  const ng1 = Math.round((fmax - fmin) / pas) + 1;
  let mx = 0;
  for (let g = 0; g < ng1; g++) mx = Math.max(mx, somme[g]);
  if (!(mx > 0)) return null;
  // L'enveloppe de deux anches qui se tirent a des harmoniques de Ω (peigne large : parfois plus d'énergie à 2 Ω ou 3 Ω qu'à Ω), et
  // les raies étrangères y ajoutent leurs propres battements. Le battement est le candidat (sommet net) dont les harmoniques 1 à 4
  // portent le plus d'énergie (poids 1, ¾, ½, ¼) : le fondamental d'un peigne, pas son sommet le plus haut.
  const cands = [];
  for (let g = 1; g < ng1 - 1; g++) {
    if (!(somme[g] >= somme[g - 1] && somme[g] >= somme[g + 1] && somme[g] >= 0.2 * mx)) continue;
    const f = fmin + g * pas;
    cands.push({ g, f, sc: S(f) + 0.75 * S(2 * f) + 0.5 * S(3 * f) + 0.25 * S(4 * f) });
  }
  if (!cands.length) return null;
  cands.sort((a, b) => b.sc - a.sc);
  const best = cands[0].g;
  const y0 = somme[best - 1], y1 = somme[best], y2 = somme[best + 1], den = y0 - 2 * y1 + y2;
  const f = fmin + best * pas + (den < 0 ? (pas * (y0 - y2)) / (2 * den) : 0);
  if (!detail) return f;
  // confiance : score du meilleur / score du meilleur candidat qui n'est pas de sa famille harmonique (ni f, ni f/2, 2f, 3f, 2f/3, 3f/2 à 6 %
  // près) ; une raie étrangère à −16 dB bat avec les porteuses aussi fort qu'une anche faible à −17 dB : les deux sommets se valent
  const parent = (a, b) => [1, 2, 3, 0.5, 1 / 3, 2 / 3, 1.5].some((r) => Math.abs(a / b - r) < 0.06 * r);
  const autre = cands.slice(1).find((c) => !parent(c.f, f));
  return { omega: f, confiance: autre ? cands[0].sc / autre.sc : Infinity };
}

// Battement par les RAIES du partiel 1 (13/10/2026, session d'Ewen : « ça marche pas dès que le battement est trop fort »). L'enveloppe ne voit pas un
// battement de plus de 4 Hz (cadence 100 Hz, 4 Hz de fmax) et, au-delà de 2 Hz, le moteur v58 l'affiche faux (jusqu'à 28 ¢ d'erreur sur les anches
// à 20 Hz d'écart). Quand les raies se séparent (plus de 3/T), elles se lisent directement : spectre de Hann du partiel 1 (±70 Hz, démodulé et décimé
// à 1 kHz), les raies à moins de 24 dB de la plus forte, puis le pas du peigne qui les explique TOUTES (au moins 90 % de la puissance) : le plus grand
// pas parmi les écarts des raies, leurs moitiés et tiers, et le battement de l'enveloppe s'il y en a un. Rend { omega, score, raies } ou null.
export function omegaSpectral(x, sr, i0, i1, fc, { candidats = [], prefere = null } = {}) {
  const pas = 2, fe0 = sr / pas, N0 = Math.floor((i1 - i0) / pas), M = Math.max(1, Math.floor(fe0 / DECIM_HZ));
  const T = N0 / fe0;
  if (T < 2) return null;
  const { zr, zi } = demodulerDecimer(x, i0, N0, pas, fe0, fc, M), N = zr.length, fe = fe0 / M, Tn = N / fe;
  const demi = Math.min(70, 0.45 * fc, 0.4 * fe), df = 1 / (3 * Tn), nb = Math.ceil((2 * demi) / df);
  const wr = new Float64Array(N), wi = new Float64Array(N);
  for (let n = 0; n < N; n++) { const h = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / N); wr[n] = zr[n] * h; wi[n] = zi[n] * h; }
  const P = new Float64Array(nb);
  for (let b = 0; b < nb; b++) {
    const d = -demi + b * df, th = (-2 * Math.PI * d) / fe, rr = Math.cos(th), ri = Math.sin(th);
    let cr = 1, ci = 0, a = 0, e = 0;
    for (let n = 0; n < N; n++) { a += wr[n] * cr - wi[n] * ci; e += wr[n] * ci + wi[n] * cr; const t = cr * rr - ci * ri; ci = cr * ri + ci * rr; cr = t; }
    const hc = reponseBoite(d, fe0, M);
    P[b] = (a * a + e * e) / (hc * hc);
  }
  const mx = Math.max(...P);
  if (!(mx > 0)) return null;
  const sep = Math.max(2, Math.round(1.5 / (Tn * df)));   // deux raies à moins de 1,5/T ne sont pas deux raies
  const raies = [];
  for (let b = sep; b < nb - sep; b++) {
    let sommet = P[b] > mx * 10 ** -2.4;
    for (let q = b - sep; q <= b + sep && sommet; q++) if (q !== b && (P[q] > P[b] || (P[q] === P[b] && q < b))) sommet = false;
    if (!sommet) continue;
    const y0 = P[b - 1], y1 = P[b], y2 = P[b + 1], den = y0 - 2 * y1 + y2;
    raies.push({ d: -demi + (b + (den < 0 ? (0.5 * (y0 - y2)) / den : 0)) * df, p: P[b] / mx });
  }
  raies.sort((a, b) => b.p - a.p);
  const fortes = raies.slice(0, 6);
  if (fortes.length < 2) return { omega: null, score: 0, raies: fortes };
  const f0 = fortes[0].d, tot = fortes.filter((r) => r.p >= 10 ** -2.4).reduce((s, r) => s + r.p, 0);
  const score = (om) => {
    const tolHz = Math.max(0.5 / Tn, 0.04 * om);
    let ex = 0;
    for (const r of fortes) if (r.p >= 10 ** -2.4) { const m = (r.d - f0) / om; if (Math.abs(m - Math.round(m)) * om <= tolHz) ex += r.p; }
    return ex / tot;
  };
  const cand = [];
  const ajoute = (o) => { if (o >= 3 / Tn && o <= 80 && !cand.some((c) => Math.abs(c - o) < 0.04 * o)) cand.push(o); };
  for (const c of candidats) { ajoute(c); ajoute(c / 2); ajoute(c * 2); }
  for (let i = 0; i < Math.min(5, fortes.length); i++) for (let j = i + 1; j < Math.min(5, fortes.length); j++) {
    const dd = Math.abs(fortes[i].d - fortes[j].d);
    ajoute(dd); ajoute(dd / 2); ajoute(dd / 3);
  }
  const bons = cand.map((o) => ({ o, s: score(o) })).filter((c) => c.s >= 0.9).sort((a, b) => b.o - a.o);
  // pas affiné : moindres carrés des raies expliquées sur m Ω
  // le battement de l'enveloppe l'emporte sur un pas plus grand ou plus petit quand il explique les raies à 88 % (une raie étrangère à −10 dB
  // n'est pas sur le peigne : elle fait 9 % de la puissance, et le demi-pas, plus dense, l'explique)
  const pref = prefere ? cand.filter((c) => Math.abs(c - prefere) <= 0.05 * prefere).map((o) => ({ o, s: score(o) })).find((c) => c.s >= 0.88) : null;
  if (pref && (!bons.length || pref.o >= 0.95 * bons[0].o)) bons.unshift(pref);   // jamais un pas plus petit que celui qui explique déjà les raies
  if (!bons.length) return { omega: null, score: 0, raies: fortes };
  const om0 = bons[0].o, pts = fortes.filter((r) => r.p >= 10 ** -2.4).map((r) => ({ m: Math.round((r.d - f0) / om0), d: r.d })).filter((q) => Math.abs(q.d - f0 - q.m * om0) <= Math.max(0.5 / Tn, 0.04 * om0));
  let sxx = 0, sxy = 0;
  for (const q of pts) { sxx += q.m * q.m; sxy += q.m * (q.d - f0); }
  return { omega: sxx > 0 ? sxy / sxx : om0, score: bons[0].s, raies: fortes };
}

// Partiels utiles : pour chaque k, puissance de la bande du partiel (k fc ± (k Ω / 2 + 2 Ω)) contre la puissance par Hz de la bande
// entre partiels (k + ½) fc de même largeur, mesurées sur 1 s au milieu de la plage (fenêtre de Hann). Rend les k dont le rapport
// passe `snrDb`, avec leur rapport (dB).
export function partielsUtiles(x, sr, i0, i1, fc, omega, { snrDb = NOTE_SNR_DB, kMax = NOTE_K_MAX, fMax = 10000 } = {}) {
  const pas = 2, fe = sr / pas, Nw = Math.min(Math.floor((i1 - i0) / pas), Math.floor(fe)), base = i0 + Math.floor(((i1 - i0) - Nw * pas) / 2);
  if (Nw < fe / 4) return { ks: [], niveaux: {} };
  const han = new Float64Array(Nw);
  for (let n = 0; n < Nw; n++) han[n] = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / Nw);
  const T = Nw / fe, df = 1 / T;
  const puissance = (c, demi) => {   // puissance totale dans [c − demi, c + demi] (Hz), démodulée en c
    const w = (2 * Math.PI * c) / fe, zr = new Float64Array(Nw), zi = new Float64Array(Nw);
    for (let n = 0; n < Nw; n++) { const v = x[base + n * pas] * han[n], a = w * n; zr[n] = v * Math.cos(a); zi[n] = -v * Math.sin(a); }
    let p = 0;
    for (let d = -demi; d <= demi; d += df) {
      const th = (-2 * Math.PI * d) / fe, rr = Math.cos(th), ri = Math.sin(th);
      let cr = 1, ci = 0, a = 0, e = 0;
      for (let n = 0; n < Nw; n++) { a += zr[n] * cr - zi[n] * ci; e += zr[n] * ci + zi[n] * cr; const t = cr * rr - ci * ri; ci = cr * ri + ci * rr; cr = t; }
      p += a * a + e * e;
    }
    return { p, n: Math.floor(2 * demi / df) + 1 };
  };
  const ks = [], niveaux = {};
  for (let k = 1; k <= kMax; k++) {
    if (k * fc > Math.min(fMax, 0.45 * sr)) break;
    const demi = (k * omega) / 2 + 2 * omega + 1;
    const s = puissance(k * fc, demi), b = puissance((k + 0.5) * fc, demi);
    const snr = 10 * Math.log10(Math.max(1e-30, (s.p - b.p) / Math.max(1e-30, b.p)));
    niveaux[k] = snr;
    if (snr >= snrDb) ks.push(k);
  }
  return { ks, niveaux };
}

// Parmi des battements candidats, celui dont l'ajustement de raies (partiel 1, deux anches et latérales à ce pas) laisse le plus petit
// résidu relatif sur la plage ; les candidats qui n'ont pas de plage assez longue (Ω·T < 2) sont écartés.
function choisirOmega(x, sr, plage, fc, cands) {
  let best = null;
  // le premier candidat (l'enveloppe lue ici) garde la préférence : un autre ne gagne que si son résidu est deux fois plus petit
  // (un pas double ou moitié explique souvent presque aussi bien un peigne)
  for (const om of cands) {
    if (!(om > 0) || om * ((plage.i1 - plage.i0) / sr) < 2) continue;
    const fa = accrocherRaies(x, sr, plage.i0, plage.i1, [plage.fCentre - om / 2, plage.fCentre + om / 2], { cote: 2, origine: plage.i0, omega: om, departs: [[plage.fCentre - 0.05 * om, plage.fCentre + 0.95 * om], [plage.fCentre - 0.95 * om, plage.fCentre + 0.05 * om]] });
    if (fa && (!best || fa.E < 0.5 * best.E)) best = { om, E: fa.E };
  }
  return best ? best.om : cands[0];
}

// Lecture d'une note [i0, i1) de x. fc : centre approximatif de l'unisson (Hz, au partiel 1). Rend
//   { sure, raison, f: [f1, f2] | null (Hz au centre de la plage), centre, omega, plage, sigmaC: [..], ... }
// `raison` quand sure est faux : 'plage' (aucune), 'courte', 'instable', 'non-resolu' (Δ non résolu : seuls `centre` et `demi` valent),
// 'battement', 'raies' (résidu trop gros), 'lecture' (verrou sans lecture), 'dispersion', 'ecart'.
export function lireNote(x, sr, i0, i1, fc, { omega = null, moteur = null, tol = 3, derMax = NOTE_DERIVE_MAX, agitMax = NOTE_AGITATION_MAX,
  recos = {}, kMax = NOTE_K_MAX, pasLecture = 0.05, debug = null, eMax = NOTE_E_MAX } = {}) {
  const R = { entier: true, etrangeres: true, utiles: true, ambigu: true, spectral: true, ...recos };
  const out = { sure: false, raison: null, f: null, centre: null, demi: null, omega: null, plage: null };
  // Battement. Une première plage (fenêtre de 0,5 s) borne l'analyse de l'enveloppe à la partie tenue ; l'enveloppe lue ici et celle
  // du moteur (`omega`) sont comparées : d'accord à 10 %, on garde la lue ici ; sinon l'ajustement de raies tranche (le résidu
  // le plus bas). Sur le banc fidèle le moteur v58 lit la moitié du battement quand les anches se tirent fort (β ≥ 0,9) ; sur la
  // session l'enveloppe lue ici prend parfois 2 Ω pour Ω : aucune des deux n'est sûre seule.
  const plage0 = plageStable(x, sr, i0, i1, fc, { tol: 6, omega: omega ?? 0, W: 0.5 });
  const env = plage0 ? battementEnveloppe(x, sr, plage0.i0, plage0.i1, plage0.fCentre, { detail: true })
    : battementEnveloppe(x, sr, Math.min(i1, i0 + Math.round(0.8 * sr)), i1, fc, { detail: true });
  const mien = env?.omega ?? null;
  let om = mien ?? omega;
  // Les raies du partiel 1 (battement > 4 Hz hors de portée de l'enveloppe ; au-dessous, elles contrôlent l'enveloppe : un battement lu qui n'est pas
  // le pas du peigne des raies est refusé, jamais un chiffre faux)
  const regD = plage0 ? plage0.i0 : Math.min(i1, i0 + Math.round(0.8 * sr)), regF = plage0 ? plage0.i1 : i1;
  const spec = R.spectral ? omegaSpectral(x, sr, regD, regF, plage0 ? plage0.fCentre : fc, { candidats: [mien, omega].filter((q) => q > 0), prefere: mien }) : null;
  out.omegaSpectral = spec?.omega ?? null;
  // Les raies tranchent quand elles expliquent tout le peigne : hors de portée de l'enveloppe, ou quand l'enveloppe se trompe (2 Ω, Ω/2)
  const hors = !!spec?.omega && (spec.omega > NOTE_ENV_MAX_HZ || !mien || Math.abs(spec.omega - mien) > 0.15 * mien);
  if (hors) { om = spec.omega; }
  // deux sommets de l'enveloppe qui se valent (anche faible + raie étrangère) : le battement n'est sûr que si le moteur dit la même chose
  out.confianceOmega = env?.confiance ?? null;
  if (!hors && mien && env.confiance < NOTE_CONFIANCE_OMEGA && !(omega && Math.abs(omega - mien) <= 0.1 * mien)) { out.raison = 'battement'; return out; }
  if (!hors && mien && omega && Math.abs(mien - omega) > 0.1 * omega && plage0) om = choisirOmega(x, sr, plage0, fc, [mien, omega]);
  if (!(om > 0)) { out.raison = 'battement'; return out; }
  const plage = plageStable(x, sr, i0, i1, fc, { tol, omega: om });
  if (!plage) { out.raison = 'plage'; return out; }
  out.plage = plage;
  const T = (plage.i1 - plage.i0) / sr;
  // le moteur v58 sur la plage seulement (pas l'attaque) : médiane de ses deux anches ; on ne le croit que si leur écart colle au
  // battement entendu (à un quart près)
  let prior = null;
  if (moteur) {
    // le moteur v58 lit sur des fenêtres de 1,2 à 3 s : il ne parle de la partie tenue qu'après 2 s (ses lectures de l'attaque la
    // dépassent de 5 ¢ pendant 1,5 s : vu sur la session, Sol#5) ; plage courte : sa fin seulement
    const ta0 = plage.t0 - i0 / sr, tb = plage.t1 - i0 / sr, ta = tb - ta0 > 3.5 ? ta0 + 2 : tb - 0.4 * (tb - ta0), g = moteur.filter((q) => q[0] >= ta && q[0] <= tb);
    if (g.length >= 3) {
      const pr = [mediane(g.map((q) => q[1])), mediane(g.map((q) => q[2]))];
      if (Math.abs(Math.abs(pr[1] - pr[0]) - om) <= 0.25 * om) prior = pr;
    }
  }
  out.prior = prior;
  out.omega = om;
  out.centre = plage.fCentre;
  if (Math.abs(plage.derive) > 3 * derMax || plage.agitation > agitMax) { out.raison = 'instable'; return out; }
  if (T < NOTE_T_MIN_S) { out.raison = 'courte'; return out; }
  if (om * T < NOTE_OMEGA_T) { out.raison = 'non-resolu'; out.demi = om / 2; return out; }
  if (T < 2 / om) { out.raison = 'courte'; return out; }

  // 3. accrochage. Départs : le centroïde de la plage au milieu, sur l'une, sur l'autre (la faible n'est pas au milieu du
  // centroïde) ; avec `prior` (les deux anches lues par le moteur v58 sur la note) : leur milieu ± Ω/2 d'abord.
  const c = plage.fCentre, dep = (a) => [c - a * om, c + (1 - a) * om];
  const pc = prior ? (prior[0] + prior[1]) / 2 : null;
  const premier = prior ? [pc - om / 2, pc + om / 2] : dep(0.5);
  const autres = prior ? [dep(0.5), dep(0.05), dep(0.95), [Math.min(...prior), Math.max(...prior)]] : [dep(0.05), dep(0.95)];
  const cache = new Map();   // les spectres du partiel 1 servent l'ajustement, le test du battement ambigu, puis le partiel 2 ne les partage pas
  const fit = () => accrocherRaies(x, sr, plage.i0, plage.i1, premier, { k: 1, cote: 2, origine: plage.i0, departs: autres, chercherEtrangeres: R.etrangeres, omega: om, cache, deriveDepart: plage.droite.pente });
  let fa = fit();
  if (!fa) { out.raison = 'raies'; return out; }
  out.E = fa.E; out.etrangeres = fa.etrangeres; out.derive = fa.derive; out.lignes = fa.lignes;
  // Le résidu E croît avec la fréquence à agitation égale en cents (0,1 ¢ de la main font 0,1 Hz à 1,3 kHz : des raies plus larges que 1/T) : seuil mis à l'échelle
  // à partir de 700 Hz (banc de plage et banc fort, 13/10/2026)
  const eMaxF = eMax * Math.max(1, (plage0 ? plage0.fCentre : fc) / FE_REF) ** FE_EXP;
  out.eMax = eMaxF;
  if (fa.E > eMaxF) { out.raison = 'raies'; return out; }
  // battement ambigu : le même ajustement SANS borne sur l'écart trouve-t-il un autre pas, nettement meilleur ? (Fa#4 de la session :
  // 0,54 ou 0,8 Hz, les deux expliquent le spectre ; l'ajustement de raies ne tranche pas, la lecture ne le peut pas non plus)
  if (R.ambigu) {
    const lib2 = accrocherRaies(x, sr, plage.i0, plage.i1, premier, { k: 1, cote: 2, origine: plage.i0, departs: autres, chercherEtrangeres: false, libres: fa.etrangeres.map((e) => e.f), cache, deriveDepart: plage.droite.pente });
    out.omegaLibre = lib2 ? lib2.omega : null;
    if (lib2 && Math.abs(lib2.omega - fa.omega) > 0.15 * fa.omega && lib2.E < NOTE_GAIN_AMBIGU * fa.E) { out.raison = 'ambigu'; return out; }
  }

  // 4a. étiquette. Le peigne de l'ajustement (porteuses et latérales, à l'écart du battement) offre plusieurs paires voisines.
  // Recommandation 2 de l'audit : la paire de porteuses la plus forte aux partiels 1 et 2 (produit des amplitudes). Mesuré au banc :
  // le produit seul se trompe d'un battement quand le couplage est fort (β1 ≥ 0,9, latérales à −3 dB), et une fois sur deux quand
  // l'anche faible est à −17 dB ; la paire doit donc aussi contenir le centroïde de puissance de la plage (NOTE_MARGE_CENTROIDE) et,
  // quand le moteur a lu les deux anches de près, être celle qu'il désigne.
  let decalage = 0;
  if (R.entier) {
    const peigne = (f) => f.lignes.filter((l) => l.role !== 'etrangere').sort((p, q) => p.f - q.f);
    const p1 = peigne(fa);
    let fa2 = null;
    try { fa2 = accrocherRaies(x, sr, plage.i0, plage.i1, fa.f, { k: 2, cote: 2, origine: plage.i0, derives: [], libres: fa.etrangeres.map((e) => e.f) }); } catch { fa2 = null; }
    const produits = (p) => p.slice(0, -1).map((l, m) => l.a * p[m + 1].a);
    const pr1 = produits(p1), mx1 = Math.max(...pr1) || 1;
    const scores = pr1.map((v2) => v2 / mx1);
    out.scoresK1 = [...scores];
    if (fa2) {
      const p2 = peigne(fa2);
      if (p2.length === p1.length) { const pr = produits(p2), mx = Math.max(...pr) || 1; out.scoresK2 = pr.map((v2) => v2 / mx); pr.forEach((v2, m) => { scores[m] = (scores[m] + v2 / mx) / 2; }); }
    }
    const nominal = p1.findIndex((l) => l.role === 'porteuse');
    const marge = NOTE_MARGE_CENTROIDE * fa.omega;
    const contient = p1.slice(0, -1).map((l, m) => c >= l.f - marge && c <= p1[m + 1].f + marge);
    // Le centroïde de puissance de la plage est le centre de symétrie du peigne : il est dans la paire des porteuses. Quand l'une des
    // anches est faible (−17 dB), il est tout près d'une porteuse, donc dans DEUX paires voisines (et un peu décalé par les latérales
    // d'un seul côté) ; alors la lecture du moteur tranche, ou, sans elle, le produit des amplitudes s'il est net, sinon refus.
    const C = contient.map((c2, m) => (c2 ? m : -1)).filter((m) => m >= 0);
    let mPrior = -1;
    if (prior) {
      const d = p1.slice(0, -1).map((l, m) => Math.abs(l.f - Math.min(...prior)) + Math.abs(p1[m + 1].f - Math.max(...prior)));
      const mi = d.indexOf(Math.min(...d));
      out.distancesPrior = d;
      // la lecture du moteur colle à la paire (à un quart de battement pour la somme des deux anches)
      if (d[mi] < NOTE_PRIOR_PROCHE * fa.omega) mPrior = mi;
    }
    if (!C.length) { out.raison = 'etiquette'; out.f = null; return out; }
    const trie = [...C].sort((u, v2) => scores[v2] - scores[u]);
    const mProd = trie[0];
    out.margeEtiquette = trie.length > 1 ? scores[trie[1]] / (scores[mProd] || 1) : 0;
    let best = -1;
    if (mPrior >= 0) {
      // le moteur désigne une paire : elle doit contenir le centroïde (sinon le moteur ou le spectre se trompe : refus) ; si deux paires le
      // contiennent (anche faible), le moteur tranche : le produit des amplitudes se trompe une fois sur deux à −17 dB
      if (!C.includes(mPrior)) { out.raison = 'etiquette'; out.f = null; return out; }
      // deux paires possibles : le moteur et le produit des amplitudes doivent désigner la même, et le produit doit la distinguer de la voisine
      // (sa marge : la deuxième paire à moins de 70 % de la première, sinon le spectre ne décide pas : cas 90.1 du banc de plage, le moteur et le
      // produit d'accord sur la mauvaise paire à 0,91, fausse d'un battement)
      if (C.length > 1 && (mPrior !== mProd || out.margeEtiquette > NOTE_MARGE_ETIQUETTE)) { out.raison = 'etiquette'; out.f = null; return out; }
      best = mPrior;
    } else if (C.length === 1) best = C[0];
    // deux paires contiennent le centroïde et le moteur n'a rien dit de sûr : le produit des amplitudes seul ne tranche pas (faux à 1 ¢ près d'un
    // battement sur le cas 73.1 du banc de plage, marge 0,38 ; juste sur d'autres de même marge) : refus
    else { out.raison = 'etiquette'; out.f = null; return out; }
    decalage = best - nominal;
    out.scoresPaires = scores;
  }
  const pair = (() => { const p = fa.lignes.filter((l) => l.role !== 'etrangere').sort((a, b) => a.f - b.f); const n0 = p.findIndex((l) => l.role === 'porteuse'); return [p[n0 + decalage].f, p[n0 + decalage + 1].f]; })();
  let f = R.entier ? pair : fa.f;
  out.decalage = decalage;
  const omFit = fa.omega;
  const ampPorteuses = fa.lignes.filter((l) => l.role === 'porteuse').sort((p, q) => p.f - q.f).map((l) => l.a);

  // 5. partiels utiles
  let partiels = null;
  if (R.utiles) {
    const u = partielsUtiles(x, sr, plage.i0, plage.i1, c, om, { kMax });
    partiels = u.ks; out.partiels = u.ks; out.snr = u.niveaux;
    if (!partiels.length) { out.raison = 'bruit'; return out; }
  }
  const etr = fa.etrangeres.map((e) => e.f);

  // 6. verrou et lectures ; si l'écart lu ne vaut pas le battement entendu (à 0,3 Ω), décalage d'un battement et nouvelle lecture
  const L = fenetreEntiere(omFit);
  let lectures = null;
  const iForte = ampPorteuses[1] > ampPorteuses[0] ? 1 : 0;
  for (let passes = 0; passes < 3; passes++) {
    // la consigne du soufflet : la droite de la plage stable (pente du centroïde, ¢/s, depuis le début de la plage). Lue sur les phases
    // elle se laissait tirer par les latérales d'un peigne plein (les partiels disaient tous Ω/2 de trop, 6 notes sur 72 au banc fidèle).
    const pente = plage.droite.pente, Tp = (plage.i1 - plage.i0) / sr;   // les raies de l'ajustement sont les fréquences MOYENNES de la plage : l'écart est nul à son milieu
    const v = new VerrouAnches(sr, f, { omega: omFit, partiels, etrangeres: etr, kMax, consigneExterne: (t) => (pente * (t - Tp / 2)) / 1731.234 });
    v.traiter(x.subarray(plage.i0, plage.i1));
    lectures = lirePlage(v.vue(), (plage.i1 - plage.i0) / sr, L, omFit, pasLecture, iForte);
    if (debug) debug({ ph: v.vue(), L, f, omFit, partiels, plage });
    if (!R.entier || !lectures.n) break;
    const gap = lectures.f[1] - lectures.f[0], n = Math.round((gap - om) / om);
    if (Math.abs(gap - om) <= NOTE_ECART_ENTIER * om || n === 0) break;
    // la faible déplacée de n battements (comme etiqueterPaire)
    const e = etiqueterPaire(lectures.f.map((v2, j) => ({ f: v2, a: ampPorteuses[j] })), om, omFit);
    if (!e.etiquette) break;
    f = [e.lus[0].f, e.lus[1].f];
    out.decalageLecture = (out.decalageLecture ?? 0) + e.etiquette;
  }
  if (!lectures || lectures.n < 4) { out.raison = 'lecture'; return out; }
  out.lectures = lectures;
  const tc = (plage.i0 + plage.i1) / 2 / sr;
  const tPlage0 = plage.i0 / sr;
  // dérive commune (¢/s) lue sur les lectures des deux anches (la pression du soufflet déplace les deux du même rapport), puis
  // lectures ramenées au centre de la plage
  const cr = lectures.valeurs.map((a2) => a2.map((v2) => cents(v2, mediane(a2))));
  let num = 0, den = 0;
  const tm = lectures.t.reduce((p, r) => p + r, 0) / lectures.t.length;
  cr.forEach((a2) => { const ma = a2.reduce((p, r) => p + r, 0) / a2.length; a2.forEach((v2, q) => { num += (lectures.t[q] - tm) * (v2 - ma); den += (lectures.t[q] - tm) ** 2; }); });
  const derive = den > 0 ? num / den : 0;
  out.derive = derive;
  if (Math.abs(derive) > derMax) { out.raison = 'instable'; return out; }
  const corr = lectures.t.map((t) => 2 ** ((derive / 1200) * (tPlage0 + t - tc)));
  const q = [0, 1].map((j) => lectures.valeurs[j].map((v2, k2) => v2 / corr[k2]));
  const fm = q.map(mediane);
  out.f = fm;
  out.demi = null;
  // incertitude de chaque anche : dispersion robuste des lectures (MAD, ¢) autour de leur tendance, divisée par la racine du nombre
  // de lectures indépendantes (une par battement), et écart entre la première et la seconde moitié de la plage (¢)
  out.sigmaC = []; out.moitiesC = [];
  [0, 1].forEach((j) => {
    const a = q[j].map((v2) => cents(v2, fm[j])), t = lectures.t, n = a.length;
    const mt = t.reduce((p, r) => p + r, 0) / n, ma = mediane(a);
    let sxx = 0, sxy = 0;
    for (let k2 = 0; k2 < n; k2++) { sxx += (t[k2] - mt) ** 2; sxy += (t[k2] - mt) * (a[k2] - ma); }
    const pente = sxx > 0 ? sxy / sxx : 0;
    const res = a.map((v2, k2) => v2 - ma - pente * (t[k2] - mt));
    const mad = mediane(res.map((r) => Math.abs(r - mediane(res)))) * 1.4826;
    const Tl = t.at(-1) - t[0] + L, neff = Math.max(1, Tl / L);
    out.sigmaC.push(mad / Math.sqrt(neff));
    const h = Math.floor(n / 2);
    out.moitiesC.push(Math.abs(cents(mediane(q[j].slice(0, h)), mediane(q[j].slice(h)))));
  });
  if (out.sigmaC.some((s2) => !(s2 <= NOTE_SIGMA_C)) || out.moitiesC.some((s2) => !(s2 <= NOTE_MOITIES_C))) { out.raison = 'dispersion'; return out; }
  if (Math.abs(fm[1] - fm[0] - om) > NOTE_ECART_ENTIER * om) { out.raison = 'ecart'; return out; }
  out.sure = true;
  return out;
}

// Lectures du verrou sur toute la plage : toutes les `pas` s, deux passes. La seconde donne à chaque anche sa référence de l'ambiguïté
// entière : la médiane de la première pour l'anche forte (ses porteuses dominent), et pour l'autre l'anche forte ± le battement
// (`omega`, celui de l'ajustement) : la faible, dont les partiels sont dominés par la forte, se levait sinon d'un demi-battement
// (vu au banc : 0,4 Hz de faux sur la faible à −17 dB). Rend { n, t (s depuis le début de la plage, centre de la fenêtre),
// valeurs: [[f ...], [f ...]], f (médiane) }.
function lirePlage(ph, T, L, omega, pas, iForte) {
  const lire = (prec) => {
    const lig = [];
    for (let t = L; t <= T + 1e-9; t += pas) {
      const lus = lireFrequences(ph, t, L, { omega, prec });
      if (!lus.every((l) => l && l.n >= 2)) continue;
      lig.push({ t: lus[0].tLu - L / 2, f: lus.map((l) => l.f) });
    }
    return lig;
  };
  let lig = lire(null);
  if (lig.length) {
    const fS = mediane(lig.map((l) => l.f[iForte]));
    const refs = [0, 1].map((j) => (j === iForte ? fS : j > iForte ? fS + omega : fS - omega));
    lig = lire(refs);
  }
  const R = ph.parAnche.length;
  if (!lig.length) return { n: 0, t: [], valeurs: Array.from({ length: R }, () => []), f: [] };
  const valeurs = Array.from({ length: R }, (_, j) => lig.map((l) => l.f[j]));
  return { n: lig.length, t: lig.map((l) => l.t), valeurs, f: valeurs.map(mediane) };
}
