// Ce que les écrans lisent d'une image du moteur (message `tick` du Worker),
// et rien d'autre. Forme de `Mesure` : docs/ARCHITECTURE.md, section C.
//
// Module pur, sans DOM : testé sous Node (test/ui.test.mjs) sur des images
// fabriquées par le vrai moteur. L'état glissant (validation, bruit) vit dans
// l'objet d'historique passé en paramètre, jamais dans une variable du module :
// deux écrans, ou deux tests, ont chacun le leur.

import { centsClass, centsBetween } from '../music.js';
import { dispersionDe } from './etabli.js';
import { partielProche } from '../dsp/secteur.js';
import { phasesDe } from './phase.js';
import { battementDe, cibleMetronome, lignesMusette } from './battement-principal.js';

// Une image du moteur = 4096 échantillons (85 ms à 48 kHz).
export const IMAGES_VALIDE = 12;     // 1,0 s : validation automatique
export const IMAGES_BRUIT = 24;      // 2 s : fenêtre du message de bruit
export const PART_BRUIT = 0.8;       // 80 % des images de la fenêtre
export const CLARTE_BRUIT = 0.6;     // NSDF : sous 0,6, pas de période franche
export const IMAGES_EFFACE = 12;     // 1 s d'anche fine efface le message
export const FILL_PLEIN = 0.999;     // fenêtre de mesure pleine (comme report.js:64)
export const CRETE_SATURE = 0.98;    // crête du micro (comme app.js:2398)
export const STAB_S = 1.2;           // « verrouillé » : 1,2 s (app.js:510)
export const STAB_CRETE = 0.2;       // ... à 0,2 ¢ crête à crête (app.js:513)
export const IMAGES_STAB = 12;       // ... sur 12 images au moins (app.js:512)

// Palier stable avant de lire ou de valider (audit du 10/10/2026,
// docs/AUDIT-REPETABILITE.md, étape 2). La validation demandait la fenêtre
// pleine (1,4 s en rapide, 2,7 s en normal) puis 1 s dans la tolérance :
// 24 paliers de soufflet sur 27 de la session d'Ewen étaient plus courts, il
// lisait donc à l'œil, à un instant quelconque, parfois pendant la dérive
// d'une attaque (0,5 à 0,8 ¢ sur Fa#3). Or la valeur du moteur est à 0,1 ¢
// de celle du palier dès 1 s : la fenêtre pleine n'est pas nécessaire ; un
// palier, si. Palier = les PALIER_S dernières secondes, toutes fines (ni
// maintenue, ni marche, même note, même sens), le niveau de l'anche dans
// ±PALIER_DB (la hauteur suit la pression : −0,15 à −0,25 ¢/dB mesurés,
// soit ±0,2 ¢), et la pente de la hauteur sous PALIER_PENTE (une anche qui
// dérive de 0,1 ¢/s bouge de 0,1 ¢ pendant la lecture). Pourquoi 1,5 s : les
// images du moteur sont des moyennes sur environ 1 s de son, elles sont
// corrélées sur ~1 s ; une pente lue sur 1 s n'a qu'une ou deux valeurs
// indépendantes, son bruit (gigue 0,05 à 0,1 ¢) dépasse 0,1 ¢/s. Essayé sur
// la session d'Ewen : avec 1 s, 14 paliers sur 27 validés au lieu de 10, mais
// le Fa#3 qui dérive après l'attaque (+0,13 ¢/s) l'était 0,67 ¢ trop bas, et
// un son qui enfle de 2 dB/s passait pour un palier ; avec 1,5 s, écart au
// palier 0,34 ¢ au plus (5,1 ¢ avec l'ancienne règle, en rapide). Un palier
// de moins de 1,9 s (1,5 s plus les 0,4 s de la première valeur fine) ne
// montre pas qu'il ne dérive pas : il faut tenir la note 2 s.
// Le niveau est celui de l'anche visée (son amplitude, v.amp), pas celui du
// son entier : deux anches qui battent font battre le son entier de
// plusieurs dB, pas chaque anche.
export const PALIER_S = 1.5;
export const PALIER_DB = 1;
export const PALIER_PENTE = 0.1;

const ETATS = { ok: 'juste', warn: 'proche', bad: 'loin' };

// La série de validation repart de zéro (main.js, en arrivant sur un écran
// qui valide : sequence.js, ECRANS_VALIDATION).
export function recommencerSerie(hist) {
  hist.serie = 0;
  hist.noteSerie = null;
}

export function nouvelHistorique() {
  return {
    cle: null,          // cible suivie par la série de validation
    serie: 0,           // images bonnes d'affilée
    noteSerie: null,    // note de la série (une note qui change la coupe)
    images: [],         // dernières images : bruyante ou non
    bruit: false,       // message affiché
    fines: 0,           // images d'affilée avec une anche fine
    silences: 0,        // images d'affilée sous le seuil
    stab: [],           // 1,2 s de cents de l'anche visée (stabilité, app.js:508-512)
    palier: null,       // images fines d'affilée de l'anche visée (palierDe)
    fen: null,          // images fines de l'anche visée sur sa fenêtre (etabli.js, dispersionDe)
  };
}

// Anches d'une image : voix des groupes ni harmoniques ni sous-harmoniques
// (même filtre que strobeReeds, app.js:1073, et rejoue.mjs:28).
// `cents` : écart à la liste (cible avec décalage par note et battement,
// dTargetCents), qui sert à l'état, à la validation et aux pastilles.
// `lus` : le chiffre affiché, selon `lecture` (Réglages, comme Dirk's) :
// 'liste' (défaut) = `cents` ; 'echelle' = écart à l'échelle (tempérament,
// La et décalage global : dCents du moteur), on accorde jusqu'à lire l'écart voulu.
export function anchesDuTick(t, lecture = 'liste') {
  const out = [];
  const vus = new Set();
  for (const g of t?.groups ?? []) {
    if (g.isHarmonic || g.isSub) continue;
    for (const v of g.voices ?? []) {
      const id = v.def?.id;
      if (vus.has(id)) continue;
      vus.add(id);
      out.push({
        id,
        cents: v.dTargetCents ?? null,
        lus: (lecture === 'echelle' ? v.dCents : v.dTargetCents) ?? null,
        hz: v.fMeas ?? null,
        battement: v.beatMeas ?? null,
        // v64 : incertitude du battement (batt/min), tendance si le battement varie vraiment, valeur posée
        battementCert: v.beatCert ? { sigmaBpm: v.beatCert.sigmaBpm, pas: v.beatCert.pas, tendanceBpmS: v.beatCert.tendance ? v.beatCert.tendanceBpmS : null, posee: !!v.beatCert.posee } : null,
        battementVoulu: v.beat ?? 0,
        fine: !!(v.tracked && !v.coarse && !v.held),
        plein: g.fill ?? 0,
        // Niveau propre de l'anche (dB) : son amplitude dans la bande, pas le son entier.
        ampDb: v.tracked && v.amp > 0 ? 20 * Math.log10(v.amp) : null,
        marche: !!v.step,           // marche de hauteur à cette image (stabilite.js, detectStep)
        // Durée de son sur laquelle la hauteur est moyennée (s) : la fenêtre du traqueur.
        fenetreS: g.W > 0 && g.srd > 0 ? g.W / g.srd : null,
        cible: v.target ?? null,    // fréquence voulue (liste), pour la valeur voulue
        nominal: v.nominal ?? null, // note de l'échelle (tempérament, La, décalage global)
        // 16'+8' : raie partagée avec l'octave (« confondue avec l'octave »,
        // app.js:1143, aide.html:385-395 de la v28).
        confondue: !!(v.merged || v.confondu),
        marge: null,
        methode: null,
        signeConnu: null,
        // Une seule raie dans l'unisson : l'anche seule, donnée à la voix
        // visée (dsp/proches.js, uniteUnisson ; audit d'usage pro n° 1).
        seule: !!v.seule,
        // Pourquoi la lecture n'est pas certifiée (dsp/certificat.js) : 'verification', 'trous', 'peigne', 'resolution', 'etiquette', 'stabilite', 'accord', 'domaine'.
        refus: v.refus ?? null,
        // Échelons (audit du 19/10/2026) : le certificat est-il posé (phase.js : cert.ok et source « certificat »), et l'étiquette 8'/8'+ est-elle sûre (dsp/appariement.js).
        certifie: !!(v.cert?.ok && v.source === 'certificat'),
        source: v.source ?? null,
        etiquette: v.etiquette ?? null,
        // D2, cas 3 : la fréquence de cette anche a quitté la prédiction et y reste (ce n'est pas la prise de son) : à signaler au luthier, jamais lissée.
        discontinuite: v.anche === 'discontinuite',
        refusCause: v.refusCause ?? null,
        // v67 (G5) : incertitude de la hauteur certifiée due au niveau de jeu (pression du soufflet) pendant la fenêtre : { c (¢), db (étendue du niveau), propre (pente de la note) } ou null
        pression: v.pression ?? null,
        // Anches de l'unisson que la fenêtre ne sépare pas (dsp/proches.js) :
        // { avec, resHz, margeHz, justesse, cases, fenetreS, k } ou null.
        proches: v.proches ?? null,
        // Durée de son lue par le battement d'une anche confondue (s) : sa
        // marge se resserre en 1/T (« tiens la note », n° 6).
        dureeLue: v.dureeLue ?? null,
        // v71 (PROV_ENTIER) : battement Ω̂ de la paire (Hz) et amplitude (¢) de la composante de cette anche à Ω̂ sur la dernière période (dsp/battement.js, composanteOmega) ; null sans le drapeau.
        omega: v.omegaChapeau ?? null,
        // v71 (K_MESURE) : instant où le modèle à deux raies (dsp/entiere.js) a pris la main sur cette anche ; l'historique du chiffre provisoire d'avant (la fréquence de la somme) n'est plus le sien.
        depuis: v.source === 'modele2' ? v.modele2?.depuis ?? null : null,
        compOmega: v.compOmega ?? null,
      });
      // Confondue avec une estimation (dsp/confondu.js) : le chiffre est
      // l'estimation, avec sa marge (« +3,1 ¢ ±2,6 »), pas la raie commune.
      const a = out[out.length - 1];
      if (v.confondu && v.fEstimee != null && Number.isFinite(v.margeCents)) {
        a.cents = v.centsEstimesCible;
        a.lus = lecture === 'echelle' ? v.centsEstimes : v.centsEstimesCible;
        a.hz = v.fEstimee;
        a.marge = v.margeCents;
        a.methode = v.methode;
        a.signeConnu = !!v.signeConnu;
      }
      // Deux anches qui se tirent (dsp/peigne.js, `etatPaire`) : une lecture par anche n'est dite sûre qu'après T_besoin et avec un
      // σ sous 0,3 ¢ ; avant, ou sous la résolution de la fenêtre (Do6-Do7 sous 0,5 Hz), elle porte sa marge (« en cours »,
      // « au centre », « anches qui se tirent ») comme une anche confondue : la validation attend |écart| + marge < tolérance.
      else if (v.margeAnche > 0 && v.etatAnche) {
        a.marge = v.margeAnche;
        a.methode = { sur: 'peigne', centre: 'centre' }[v.etatAnche] ?? 'encours';
        a.reste = v.etatAnche === 'en cours' && v.tBesoin != null ? Math.max(1, Math.ceil(v.tBesoin - (v.ageNote ?? 0))) : null;
      }
    }
  }
  return out;
}

// Classe d'état d'une anche (ok, warn, bad, dim, comme centsClass). Une
// anche confondue avec l'octave n'est « juste » que si toute sa marge tient
// dans la tolérance : |écart| + marge ≤ tol ; sinon, si toute la marge est
// loin (|écart| − marge au-delà du seuil de « loin »), elle est loin ; entre
// les deux, « proche » (« juste à ±2,6 ¢ près », jamais un vert trompeur).
export function classeAnche(a, tol = 1) {
  if (!a || a.cents == null || !Number.isFinite(a.cents)) return 'dim';
  if (!(a.marge > 0)) return centsClass(a.cents, tol);
  const c = Math.abs(a.cents);
  if (c + a.marge <= tol) return 'ok';
  if (c - a.marge > Math.max(5, 2 * tol)) return 'bad';
  return 'warn';
}

// Validation automatique d'une anche : dans la tolérance ; confondue avec
// l'octave, toute sa marge dedans (|estimation| + marge < tolérance).
export function dansTolerance(a, tol = 1) {
  if (!a || a.cents == null || !Number.isFinite(a.cents)) return false;
  if (a.marge > 0) return Math.abs(a.cents) + a.marge < tol;
  return Math.abs(a.cents) <= tol;
}

// Hors de la tolérance POUR DE BON : avec une marge, toute la marge dehors
// (|estimation| − marge > tolérance). Entre les deux (« juste à ±1,8 ¢
// près »), on ne sait pas : ni validée, ni « à reprendre » (audit d'usage pro
// n° 6 : les basses 16'+8' justes passaient toutes « à reprendre »).
export function horsTolerance(a, tol = 1) {
  if (!a || a.cents == null || !Number.isFinite(a.cents)) return false;
  return Math.abs(a.cents) - (a.marge > 0 ? a.marge : 0) > tol;
}

// Durée de note qui rendrait une anche confondue validable (audit d'usage pro
// n° 6) : la marge du battement se resserre en 1/T (dsp/confondu.js, la
// limite de la durée jouée), la précision du 16' (MARGE_PLANCHER, en
// quadrature) non. Il faut |estimation| + marge(T) < tolérance :
// marge(T) = √(m_c² T₀²/T² + p²), m_c = √(marge² − p²) la part de la
// confusion lue sur T₀. Rend { totalS, resteS } (s, arrondis au-dessus) si
// c'est possible en CONF_MAX_S (8 s) au plus ; sinon null (« juste à ±m ¢
// près » reste dit, sans promesse).
export const MARGE_PLANCHER = 0.1;
export const DUREE_MAX_S = 8;
export function tenirLaNote(a, tol = 1) {
  if (!a || !(a.marge > 0) || !(a.dureeLue > 0) || a.cents == null || !Number.isFinite(a.cents)) return null;
  if (a.methode !== 'battement' && a.methode !== 'immobile') return null;
  const c = Math.abs(a.cents);
  if (c + a.marge < tol || c >= tol) return null;
  const reste = tol - c;
  const mc = Math.sqrt(Math.max(0, a.marge ** 2 - MARGE_PLANCHER ** 2));
  const dispo = reste ** 2 - MARGE_PLANCHER ** 2;
  if (!(dispo > 0) || !(mc > 0)) return null;
  const T = (a.dureeLue * mc) / Math.sqrt(dispo);
  if (T > DUREE_MAX_S) return null;
  return { totalS: Math.ceil(T), resteS: Math.max(1, Math.ceil(T - a.dureeLue)) };
}

// La touche d'à côté (audit d'usage pro n° 1) : la note entendue par le
// moteur (tick.noteEntendue, la détection libre à côté de la note imposée)
// n'est pas la note de la cible, ni une de ses octaves (une octave fausse de
// la détection ne compte pas), depuis AUTRE_NOTE_IMAGES images d'affilée.
// Rend { joue, attendu } (midi) ou null.
export const AUTRE_NOTE_IMAGES = 3;
export function autreNote(t, cible) {
  const e = t?.noteEntendue;
  if (!e || t?.quiet || cible?.midi == null || e.midi == null) return null;
  if (e.images < AUTRE_NOTE_IMAGES || ((e.midi - cible.midi) % 12 + 12) % 12 === 0) return null;
  return { joue: e.midi, attendu: cible.midi };
}

// ---- Valeur voulue (Dirk's : « en dessous, la valeur voulue ») --------------
// Ce que la liste demande à l'anche visée, écrit sous le chiffre d'Accorder
// (composants/valeur-voulue.js) :
//   hz        : fréquence voulue (cible du moteur : échelle, décalage par note,
//               battement voulu) ;
//   battement : battement voulu en Hz (0 si l'anche ne bat pas) ;
//   cents     : écart du voulu à l'échelle (nominal du moteur : tempérament, La,
//               décalage global), le nombre à lire en lecture « échelle ».
//   bat       : (battement principal, v71, `options` donnés) le battement en bat/min : mesuré, cible, fourchette, état
//               « sec / juste / ouvert » (battement-principal.js) ; absent sinon.
export function valeurVoulue(a, options = null) {
  const cible = a?.cible ?? null;
  if (!cible) return null;
  const voulu = {
    hz: cible,
    battement: Math.abs(a.battementVoulu ?? 0),
    cents: a.nominal ? centsBetween(cible, a.nominal) : null,
  };
  if (options) {
    voulu.bat = battementDe(a, options);
    if (options.metronome && voulu.bat) voulu.metronome = cibleMetronome(voulu.bat.cibleBpm);
  }
  return voulu;
}

// ---- Palier stable (audit du 10/10/2026, étape 2) -------------------------------
// Pente des moindres carrés de y sur x (null sous 3 points). Pure.
function pente(xs, ys) {
  const n = xs.length;
  if (n < 3) return null;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
  mx /= n; my /= n;
  let sxx = 0, sxy = 0;
  for (let i = 0; i < n; i++) { sxx += (xs[i] - mx) ** 2; sxy += (xs[i] - mx) * (ys[i] - my); }
  return sxx > 0 ? sxy / sxx : null;
}

// Suit le palier de l'anche visée image par image (`hist.palier`, modifié) et
// rend { ok, dureeS, pente, niveauDb, ecartDb, n } (ok : palier stable sur les
// PALIER_S dernières secondes). Une image qui n'est pas fine (silence,
// maintenue, rapide, marche), une autre note, une autre anche ou un autre
// sens du soufflet (une inversion) le fait repartir. Pure.
export function palierDe(hist, t, visee, note) {
  const cle = `${note}|${visee?.id}|${t?.soufflet?.inversions ?? 0}`;
  const temps = t?.time;
  const bonne = !t?.quiet && note != null && !!visee?.fine && !visee.marche && visee.cents != null
    && Number.isFinite(visee.cents) && visee.ampDb != null && Number.isFinite(temps);
  let p = hist.palier;
  if (!bonne || !p || p.cle !== cle || p.debut == null) p = hist.palier = { cle, debut: bonne ? temps : null, images: [] };
  if (!bonne) return { ok: false, dureeS: 0, pente: null, niveauDb: null, ecartDb: null, n: 0 };
  p.images.push({ t: temps, c: visee.cents, db: visee.ampDb });
  while (p.images.length && p.images[0].t < temps - PALIER_S - 1e-6) p.images.shift();
  const im = p.images;
  const dureeS = temps - p.debut;
  const pc = pente(im.map((x) => x.t), im.map((x) => x.c));
  let dMin = Infinity, dMax = -Infinity, dMoy = 0;
  for (const x of im) { dMin = Math.min(dMin, x.db); dMax = Math.max(dMax, x.db); dMoy += x.db; }
  dMoy /= im.length;
  const ecartDb = Math.max(dMax - dMoy, dMoy - dMin);
  // La durée se compte d'image fine en image fine : la première image du
  // palier date d'au moins PALIER_S (une image = 85 ms de son de plus).
  const ok = dureeS >= PALIER_S - 1e-6 && pc != null && Math.abs(pc) <= PALIER_PENTE && ecartDb <= PALIER_DB;
  return { ok, dureeS, pente: pc, niveauDb: dMoy, ecartDb, n: im.length };
}

// ---- Le chiffre affiché (v66, F6, audit Fable final : « pas trop d'infos », « les valeurs fluctuent toujours ») ----
// Avant la preuve, l'écran n'a pas à montrer la lecture brute du traqueur image par image (±1 ¢ d'écart type, un saut de plus de 0,3 ¢ presque deux fois par seconde). Il montre :
//  - PROVISOIRE (rien de certifié) : la médiane de la dernière seconde, arrondie au demi-cent, qui ne bouge que d'un demi-cent et au plus toutes les 0,8 s, avec une seule bande
//    (± l'étendue de cette seconde) ; en gris et plus petit (chiffre.js) : « pas encore sûr » se lit sans un mot ;
//  - CERTIFIÉ : la valeur certifiée, au dixième de cent, qui ne bouge que d'un dixième de cent ; en grand, de la couleur de l'état.
// `hist.aff` garde l'état entre deux images (modifié). Pure.
export const AFFICHAGE = { MEDIANE_S: 1.5, MEDIANE_MAX_S: 6, PAS_PROV: 0.5, MAJ_S: 1.0, IMAGES_MIN: 6, PAS_CERT: 0.1, HYST_PROV: 0.75,
  // Chiffre continu (drapeau CHIFFRE_CONTINU, audit du 19/10/2026) : un régime n'est adopté qu'après HYST_REGIME_S ; le chiffre ne fait jamais un pas de plus de PAS_MAX_IMAGE ; un écart de GRAND_ECART ou plus avec la médiane se rattrape d'un demi-cent par image.
  HYST_REGIME_S: 0.5, PAS_MAX_IMAGE: 1.0, GRAND_ECART: 2.0 };
// Moyenne temporelle (méthode des trapèzes) de [{ t, c }] sur [t0, t1], le bord gauche interpolé linéairement entre deux images.
function moyenneEntiere(pts, t0, t1) {
  let aire = 0, duree = 0;
  for (let i = 1; i < pts.length; i++) {
    let { t: ta, c: ca } = pts[i - 1];
    const { t: tb, c: cb } = pts[i];
    if (tb <= t0 || ta >= t1) continue;
    if (ta < t0) { ca += (cb - ca) * (t0 - ta) / (tb - ta); ta = t0; }
    aire += 0.5 * (ca + cb) * (tb - ta); duree += tb - ta;
  }
  return duree > 0 ? aire / duree : pts[pts.length - 1].c;
}

export function afficheDe(hist, temps, visee, { provisoire, silence, note, estimation = false, continu = false, certifie = false }) {
  if (continu) return afficheContinu(hist, temps, visee, { provisoire, silence, note, estimation, certifie });
  const a = hist.aff ??= { prov: [], c: null, tMaj: -1e9, bande: null, cert: null, note: null };
  if (silence || note !== a.note || !visee || visee.masquee) { a.prov = []; a.c = null; a.bande = null; a.cert = null; a.note = note; if (silence || !visee || visee.masquee) return null; }
  if (estimation) return null;               // une anche confondue garde son estimation avec sa marge (chiffre.js)
  if (visee.cents == null || !Number.isFinite(visee.cents) || !Number.isFinite(temps)) return null;
  // La grandeur lue change quand le modèle prend la main : on repart de ses images (le chiffre ne remonte pas, un demi-cent par seconde, depuis la valeur de la somme).
  if (visee.depuis != null && a.depuis !== visee.depuis) { a.prov = a.prov.filter((x) => x.t >= visee.depuis - 1e-6); a.c = null; a.bande = null; a.depuis = visee.depuis; }
  a.prov.push({ t: temps, c: visee.cents });
  // v71 (PROV_ENTIER) : quand le battement Ω̂ de la paire est connu, la médiane couvre un nombre ENTIER de battements (au moins MEDIANE_S) : la modulation
  // à Ω̂ (tirage, AM) y a une moyenne nulle, le chiffre ne danse pas au rythme du battement.
  const entier = visee.omega > 0.1 && visee.omega < 10;
  const fen = entier ? Math.min(AFFICHAGE.MEDIANE_MAX_S, Math.ceil(AFFICHAGE.MEDIANE_S * visee.omega - 1e-9) / visee.omega) : AFFICHAGE.MEDIANE_S;
  // (fenêtre entière : on garde un point d'avant son début, pour en interpoler le bord)
  if (entier) { while (a.prov.length > 1 && a.prov[1].t <= temps - fen + 1e-6) a.prov.shift(); }
  else while (a.prov.length && a.prov[0].t < temps - fen - 1e-6) a.prov.shift();
  if (!provisoire) {
    // certifié : la valeur ne bouge que d'un dixième de cent
    if (a.cert == null || Math.abs(visee.cents - a.cert) >= AFFICHAGE.PAS_CERT) a.cert = Math.round(visee.cents / AFFICHAGE.PAS_CERT) * AFFICHAGE.PAS_CERT;
    return { cents: Math.round(a.cert * 10) / 10, certifie: true, provisoire: false, bande: null };
  }
  a.cert = null;
  if (a.prov.length < AFFICHAGE.IMAGES_MIN) return null;
  const v = a.prov.map((x) => x.c).sort((x, y) => x - y);
  // Sur des battements entiers, la MOYENNE (trapèzes, bords interpolés) annule exactement la composante à Ω̂ ; une médiane de quelques dizaines de points la
  // garde à plus ou moins un demi-rang (un rang vaut A·2π/N ≈ 0,3 A près du milieu). Le chiffre est la hauteur de l'anche en place (peigne.js).
  const med = entier ? moyenneEntiere(a.prov, temps - fen, temps) : v.length % 2 ? v[v.length >> 1] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2;
  const cible = Math.round(med / AFFICHAGE.PAS_PROV) * AFFICHAGE.PAS_PROV;
  const bande = Math.max(AFFICHAGE.PAS_PROV, Math.ceil((v[v.length - 1] - v[0]) / 2 / AFFICHAGE.PAS_PROV) * AFFICHAGE.PAS_PROV);
  if (a.c == null) { a.c = cible; a.bande = bande; a.tMaj = temps; }
  else if (temps - a.tMaj >= AFFICHAGE.MAJ_S && Math.abs(med - a.c) >= AFFICHAGE.HYST_PROV) { a.c += Math.sign(cible - a.c) * AFFICHAGE.PAS_PROV; a.bande = bande; a.tMaj = temps; }
  return { cents: Math.round(a.c * 10) / 10, certifie: false, provisoire: true, bande: a.bande };
}

// Saut d'horloge de la prise (D3 de l'audit « échelons », 19/10/2026 ; dsp/saut-horloge.js) : toutes les raies ont sauté du même nombre de cents, ce n'est pas l'anche.
// Le chiffre est TENU (la valeur affichée juste avant, jamais une nouvelle), jamais certifié ; la médiane et le certificat affiché repartent des images d'après.
// Rien n'est lissé ni inventé : sans valeur déjà affichée, rien. `hist.aff` est modifié. Pure.
export function afficheGele(hist, temps, visee, { silence, note }) {
  const a = hist.aff ??= { prov: [], c: null, tMaj: -1e9, bande: null, cert: null, note: null };
  if (silence || note !== a.note || !visee || visee.masquee) { a.prov = []; a.c = null; a.bande = null; a.cert = null; a.note = note; hist.gelHorloge = false; return null; }
  hist.gelHorloge = true;
  const c = a.cert ?? a.c;
  if (c == null) return null;
  return { cents: Math.round(c * 10) / 10, certifie: false, provisoire: true, bande: a.cert != null ? null : a.bande, regime: 'gele', gele: true };
}
// Fin du gel : la médiane repart des images d'après le saut, et le chiffre certifié est reposé (ou non) par le certificat, pas par la mémoire.
function sortirDuGel(hist, temps) {
  const a = hist.aff;
  hist.gelHorloge = false;
  if (!a) return;
  if (a.cert != null && a.c == null) a.c = a.cert;
  a.prov = []; a.cert = null; a.tMaj = temps;
}
// Un seul chiffre, continu (D1 de l'audit « échelons de justesse », 19/10/2026). Trois régimes :
//  - 'provisoire' : médiane de 1,5 s au demi-cent (comme avant) ;
//  - 'instantane' : la valeur du moteur au dixième de cent, mais PAS dite certifiée (une raie « seule » n'est pas un certificat) ;
//  - 'certifie'   : la valeur du moteur au dixième de cent, certificat posé (v.cert.ok et source « certificat »), sinon jamais.
// Le chiffre (a.c) est le même d'un régime à l'autre : un changement de régime repart de la valeur AFFICHÉE (jamais d'un état périmé), la valeur d'un
// régime à l'autre se rejoint par pas d'au plus PAS_MAX_IMAGE, et un régime n'est adopté qu'après HYST_REGIME_S (le clignotement de « refus », « seule »,
// « confondu » ne le fait plus basculer). La perte du certificat, elle, se dit tout de suite : « certifié » n'est jamais écrit sans certificat.
function afficheContinu(hist, temps, visee, { provisoire, silence, note, estimation, certifie }) {
  const a = hist.aff ??= { prov: [], c: null, tMaj: -1e9, bande: null, cert: null, note: null };
  a.cont ??= { regime: null, cand: null };
  const k = a.cont;
  if (silence || note !== a.note || !visee || visee.masquee) {
    a.prov = []; a.c = null; a.bande = null; a.cert = null; a.note = note; k.regime = null; k.cand = null;
    if (silence || !visee || visee.masquee) return null;
  }
  if (estimation) { a.prov = []; a.c = null; a.bande = null; k.regime = null; k.cand = null; return null; }   // l'estimation (chiffre.js) a son affichage ; rien de périmé n'en reste
  if (visee.cents == null || !Number.isFinite(visee.cents) || !Number.isFinite(temps)) return null;
  // La grandeur lue change quand le modèle prend la main : on repart de ses images.
  if (visee.depuis != null && a.depuis !== visee.depuis) { a.prov = a.prov.filter((x) => x.t >= visee.depuis - 1e-6); a.c = null; a.bande = null; a.depuis = visee.depuis; }
  a.prov.push({ t: temps, c: visee.cents });
  // v71 (PROV_ENTIER) : la médiane couvre un nombre ENTIER de battements quand Ω̂ est connu (comme afficheDe).
  const entier = visee.omega > 0.1 && visee.omega < 10;
  const fen = entier ? Math.min(AFFICHAGE.MEDIANE_MAX_S, Math.ceil(AFFICHAGE.MEDIANE_S * visee.omega - 1e-9) / visee.omega) : AFFICHAGE.MEDIANE_S;
  if (entier) { while (a.prov.length > 1 && a.prov[1].t <= temps - fen + 1e-6) a.prov.shift(); }
  else while (a.prov.length && a.prov[0].t < temps - fen - 1e-6) a.prov.shift();
  // Régime voulu, puis régime tenu (hystérésis)
  const voulu = provisoire ? 'provisoire' : (certifie ? 'certifie' : 'instantane');
  if (k.regime == null) { k.regime = voulu; k.cand = null; a.tMaj = temps; }
  else if (voulu !== k.regime) {
    if (k.cand?.regime !== voulu) k.cand = { regime: voulu, depuis: temps };
    if (temps - k.cand.depuis >= AFFICHAGE.HYST_REGIME_S - 1e-6) { k.regime = voulu; k.cand = null; a.tMaj = temps; }
  } else k.cand = null;
  const x = visee.cents;
  if (k.regime === 'provisoire') {
    if (a.prov.length < AFFICHAGE.IMAGES_MIN) return a.c == null ? null : { cents: Math.round(a.c * 10) / 10, certifie: false, provisoire: true, bande: a.bande, regime: 'provisoire' };
    const v = a.prov.map((q) => q.c).sort((p, q) => p - q);
    const med = entier ? moyenneEntiere(a.prov, temps - fen, temps) : v.length % 2 ? v[v.length >> 1] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2;
    const cible = Math.round(med / AFFICHAGE.PAS_PROV) * AFFICHAGE.PAS_PROV;
    const bande = Math.max(AFFICHAGE.PAS_PROV, Math.ceil((v[v.length - 1] - v[0]) / 2 / AFFICHAGE.PAS_PROV) * AFFICHAGE.PAS_PROV);
    if (a.c == null) { a.c = cible; a.bande = bande; a.tMaj = temps; }
    else if (Math.abs(cible - a.c) >= AFFICHAGE.GRAND_ECART) { a.c += Math.sign(cible - a.c) * AFFICHAGE.PAS_PROV; a.bande = bande; a.tMaj = temps; }   // un vrai déplacement : rattrapé sans attendre la seconde
    else if (temps - a.tMaj >= AFFICHAGE.MAJ_S && Math.abs(med - a.c) >= AFFICHAGE.HYST_PROV) { a.c += Math.sign(cible - a.c) * AFFICHAGE.PAS_PROV; a.bande = bande; a.tMaj = temps; }
    return { cents: Math.round(a.c * 10) / 10, certifie: false, provisoire: true, bande: a.bande, regime: 'provisoire' };
  }
  // instantané ou certifié : la valeur du moteur au dixième de cent, par pas d'au plus PAS_MAX_IMAGE
  const but = Math.round(x / AFFICHAGE.PAS_CERT) * AFFICHAGE.PAS_CERT;
  if (a.c == null) a.c = but;
  else if (Math.abs(x - a.c) >= AFFICHAGE.PAS_CERT) a.c += Math.sign(but - a.c) * Math.min(Math.abs(but - a.c), AFFICHAGE.PAS_MAX_IMAGE);
  a.bande = null;
  const sur = k.regime === 'certifie' && certifie;
  return { cents: Math.round(a.c * 10) / 10, certifie: sur, provisoire: false, bande: null, regime: sur ? 'certifie' : 'instantane' };
}

// `cible` : { midi, sens, voix } (voix = id de la voix du registre) ou null.
// `reglages` : { tolCents, validationAuto: { dureeS }, lecture } (1 ¢, 1 s, 'liste' par défaut).
// `hist` : objet de nouvelHistorique(), modifié à chaque appel.
export function lireTick(t, cible, reglages = {}, hist = nouvelHistorique()) {
  const tol = reglages.tolCents ?? 1;
  const anches = anchesDuTick(t, reglages.lecture);
  const silence = !!t?.quiet;

  // Anche visée : celle de la cible ; sans cible, la première suivie
  // (comme selectedVoice, app.js:471).
  let visee = null;
  // Version gratuite : le moteur est en mode auto, sa seule anche s'appelle
  // 'auto' ; c'est elle que vise la séquence.
  // Autre mode de mesure (auto-anches, notes, accord : modes.js) : les anches
  // du moteur ne portent pas les voix du registre ; la visée suit alors la
  // règle sans cible.
  const libre = () => anches.find((a) => a.fine) ?? anches.find((a) => a.cents != null) ?? null;
  if (cible?.voix != null) {
    visee = anches.find((a) => a.id === cible.voix) ?? anches.find((a) => a.id === 'auto') ?? null;
    if (!visee && anches.length) visee = libre();
  } else visee = libre();

  // La touche d'à côté : le chiffre est masqué, rien n'est validé ni noté
  // (« Mi5 joué, Ré#5 attendu », composants/message.js).
  const autre = autreNote(t, cible);
  if (visee && autre) visee = { ...visee, cents: null, lus: null, fine: false, marge: null, masquee: true };
  // Battement principal (v71, réglage `battementPrincipal`, éteint par défaut) : la grandeur d'une musette est le battement ; la voix juste se lit en cents.
  const bp = reglages.battementPrincipal === true ? { reglage: reglages.fourchetteBat ?? null, table: reglages.toleranceTable ?? null, asymetrie: reglages.asymetrie8moins ?? 1, metronome: reglages.metronome === true } : null;
  if (visee) visee.voulu = valeurVoulue(visee, bp);
  if (visee) visee.tenir = tenirLaNote(visee, tol);

  // Prise douteuse (contrôle de la prise, dsp/prise.js : suppresseur de bruit, blocs perdus, écrêtage, ronflement,
  // 8-16 kHz, Bluetooth) : la valeur reste lisible mais n'est jamais dite « juste » ni « loin », ni validée, ni
  // comptée dans la série de validation : l'accordeur ne garantit pas ce que la chaîne a pu déformer.
  // Un partiel de l'anche à moins de 1 Hz d'une harmonique du secteur que l'accordeur retire est abîmé par le retrait
  // (dsp/secteur.js) : la lecture n'est pas dite sûre, la raison est dite (« partiel près du secteur »).
  const secteurProche = !!(t?.prise?.secteurHz && visee?.hz && [1, 2].some((k) => partielProche(visee.hz * k, t.prise.secteurHz)));
  const codesPrise = secteurProche ? [...(t?.prise?.codes ?? []), 'secteurProche'] : (t?.prise?.codes ?? []);
  const douteuse = !!t?.prise?.douteuse || secteurProche;
  // v71 (F1, TROUS_COURTS) : l'image dont la fenêtre contient un trou de prise n'a pas de verdict, sans le dire (pas de « prise douteuse ») ; un trou de plus de 0,4 s laisse un repère discret.
  const ecartee = !!t?.prise?.ecartee, repere = !!t?.prise?.repere;
  const sansVerdict = douteuse || ecartee;
  // Attaque ou lecture pas encore résolue (phase.js) : la courbe est en pointillé, le chiffre n'est pas dit juste.
  // Début de la note : la première image de la suite de même note (hist.noteT0).
  if (silence || t?.playedMidi == null) hist.noteM = null;
  else if (hist.noteM !== t.playedMidi) {
    // Une image isolée sur une autre note n'est pas une nouvelle note : il en faut 3 de suite.
    const c = hist.noteCand?.m === t.playedMidi ? hist.noteCand : (hist.noteCand = { m: t.playedMidi, n: 0, t0: t.time });
    if (hist.noteM == null || ++c.n >= 3) { hist.noteM = t.playedMidi; hist.noteT0 = c.t0; hist.noteCand = null; }
  } else hist.noteCand = null;
  const ph = visee && !silence ? phasesDe(t, hist.noteT0 ?? null).voix.get(visee.id) ?? null : null;
  const enCours = !!ph && ph.phase !== 'resolue';
  // Provisoire : rien de certifié (en cours, prise douteuse, ou une marge que le certificat n'a pas levée) ; une anche confondue garde son estimation avec sa marge (chiffre.js).
  const estimation = !!visee && !!visee.confondue && ['octave', 'battement', 'raie', 'immobile'].includes(visee.methode);
  const etiquetteIncertaine = !!visee && visee.etiquette === 'incertaine';   // D2 : dsp/appariement.js
  const provisoire = !!visee && !estimation && (enCours || sansVerdict || visee.marge > 0 || visee.refus != null);
  const continu = (reglages.chiffreContinu ?? t?.chiffreContinu) === true;   // D1 : drapeau CHIFFRE_CONTINU du moteur (cfg), ou le réglage
  // D3 (cfg.SAUT_HORLOGE) : saut d'horloge de la prise en cours -> chiffre tenu, pas de certification, pas de validation (message.js, courbe.js).
  const sautHorloge = t?.prise?.sautHorloge?.actif ? t.prise.sautHorloge : null;
  if (!sautHorloge && hist.gelHorloge) sortirDuGel(hist, t?.time);
  const affiche = visee && !silence ? (sautHorloge ? afficheGele(hist, t?.time, visee, { silence, note: t?.playedMidi ?? null }) : afficheDe(hist, t?.time, visee, { provisoire, silence, estimation, note: t?.playedMidi ?? null, continu, certifie: !!visee.certifie })) : (hist.aff = null, hist.gelHorloge = false, null);
  const k = visee && visee.cents != null && !sansVerdict && !enCours && !provisoire ? classeAnche(visee, tol) : 'dim';   // D3 : l'état (juste, proche, loin) ne dépend pas du saut d'horloge : mesuré v71, le retirer coûtait 12 % de notes posées
  const etat = ETATS[k] ?? null;

  // Validation : 12 images d'affilée, toutes fines et dans la tolérance, à
  // note constante (et sur la note de la cible), ET un palier stable (palierDe :
  // 1,5 s fines, niveau à ±1 dB, pente sous 0,1 ¢/s). La fenêtre pleine
  // n'est plus demandée (audit du 10/10/2026, étape 2).
  // Même structure que la stabilité d'app.js:508-512.
  const cle = cible ? `${cible.midi}|${cible.sens}|${cible.voix}` : '';
  if (hist.cle !== cle) {
    hist.cle = cle;
    hist.serie = 0;
    hist.noteSerie = null;
  }
  const note = t?.playedMidi ?? null;
  const palier = palierDe(hist, t, visee, note);
  // Dispersion de l'anche visée sur la durée que le moteur moyenne (étape 4).
  const dispersion = dispersionDe(hist, t, visee, note);
  // D3 : le saut d'horloge tient le chiffre, le dit et le journalise ; il ne retire PAS la coche du verdict (la sentinelle et le certificat invalident déjà une lecture que le saut a changée ; mesuré v71 : sa levée coûtait 12 % de notes posées sur les saut de pression de la synthèse)
  const bonne = !silence && !sansVerdict && !enCours && !etiquetteIncertaine && note != null && !!visee && visee.fine
    && dansTolerance(visee, tol)
    && (cible?.midi == null || note === cible.midi);
  if (!bonne) {
    hist.serie = 0;
    hist.noteSerie = null;
  } else if (note === hist.noteSerie) {
    hist.serie++;
  } else {
    hist.serie = 1;
    hist.noteSerie = note;
  }
  // Durée réglable dans Réglages (0,5 à 3 s) : 12 images par seconde.
  const n = Math.max(1, Math.round((reglages.validationAuto?.dureeS ?? 1) * IMAGES_VALIDE));
  const valide = hist.serie >= n && palier.ok;

  // Bruit : sur les 24 dernières images, au moins 80 % au-dessus du seuil,
  // sans période franche (clarté < 0,6) et sans aucune anche fine. Une
  // musette qui bat fait baisser la clarté, mais ses anches sont fines.
  const fine = anches.some((a) => a.fine);
  const bruyante = !silence && (t?.clarity ?? 0) < CLARTE_BRUIT && !fine;
  hist.images.push(bruyante);
  if (hist.images.length > IMAGES_BRUIT) hist.images.shift();
  hist.fines = fine ? hist.fines + 1 : 0;
  hist.silences = silence ? hist.silences + 1 : 0;
  const nb = hist.images.reduce((n, b) => n + (b ? 1 : 0), 0);
  if (hist.images.length >= IMAGES_BRUIT && nb >= PART_BRUIT * IMAGES_BRUIT) hist.bruit = true;
  // Effacé après 1 s d'anche fine, ou 1 s sans son (plus rien à mesurer).
  else if (hist.bruit && (hist.fines >= IMAGES_EFFACE || hist.silences >= IMAGES_EFFACE)) hist.bruit = false;

  // Convergence et stabilité (updateHeader, app.js:504-516) : fenêtre
  // d'analyse remplie (plus petit g.fill), et « verrouillé » quand l'anche
  // visée n'a pas bougé de plus de 0,2 ¢ crête à crête depuis 1,2 s (au moins
  // 12 images, même note).
  const groupes = t?.groups ?? [];
  const plein = groupes.length ? Math.min(...groupes.map((g) => g.fill ?? 0)) : 0;
  hist.stab ??= [];
  if (!silence && visee?.fine && visee.cents != null && t?.time != null) hist.stab.push({ t: t.time, c: visee.cents, m: note });
  while (hist.stab.length && (hist.stab[0].t < (t?.time ?? 0) - STAB_S || hist.stab[0].m !== note)) hist.stab.shift();
  const etendue = hist.stab.length >= IMAGES_STAB
    ? Math.max(...hist.stab.map((h) => h.c)) - Math.min(...hist.stab.map((h) => h.c)) : Infinity;
  const convergence = {
    plein: silence || !t ? 0 : Math.max(0, Math.min(1, plein)),
    stable: !silence && etendue <= STAB_CRETE,
    ecart: Number.isFinite(etendue) ? Math.max(0.01, etendue / 2) : null,
  };

  return {
    note,
    silence,
    tol,
    convergence,
    // Battement lu dans l'enveloppe (t.beat), pour la ligne du battement en
    // mode auto (2.3 ; showBeat, app.js:2554-2573).
    onde: silence ? null : t?.beat ?? null,
    niveauDb: 20 * Math.log10((t?.level ?? 0) + 1e-9),
    // Sens du soufflet que le moteur suit (dsp/stabilite.js) : 'tiré', 'poussé'
    // ou null ; `soufflet` : d'où il vient (grille, creux, silence), inversions.
    sens: t?.sens ?? null,
    soufflet: t?.soufflet ?? null,
    sature: (t?.peak ?? 0) >= CRETE_SATURE,
    anches,
    visee,
    // trois lignes d'une musette (battement-principal.js), seulement avec le réglage `battementPrincipal` et au moins une voix décalée
    ...(bp && anches.some((a) => a.id === '8+' || a.id === '8-') ? { musette: lignesMusette(anches, bp) } : {}),
    affiche,
    etat,
    bruit: hist.bruit,
    valide,
    // Défaut de la prise de son pendant cette image : { douteuse, codes } du contrôle (dsp/prise.js).
    douteuse,
    // D3 : { actif, t, tSaut, deltaCents, lignes, jusqua } pendant un saut d'horloge de la prise (le chiffre est tenu), sinon null.
    sautHorloge,
    // D2 : l'étiquette 8'/8'+ de l'anche visée vient de changer d'attribution (pointillé + mention).
    etiquetteIncertaine,
    // D2, cas 3 : id de l'anche visée dont la fréquence a fait une discontinuité propre (dsp/appariement.js), ou null.
    discontinuite: visee?.discontinuite ? visee.id ?? null : null,
    ecartee,
    repere,
    prise: codesPrise,
    // Où en est la mesure (phase.js) : 'attaque', 'encours' ou 'resolue' ; `resteS` : ce qu'il faut encore de son.
    phase: ph ? ph.phase : null,
    // Lecture résolue mais non certifiée : la raison (message.js) ; null si l'anche visée est certifiée ou si le moteur ne contrôle pas ce groupe.
    refus: visee?.refus ?? null,
    refusCause: visee?.refusCause ?? null,
    resteS: enCours ? Math.max(0.5, Math.ceil((Math.max(ph.besoin, 1) - ph.age) * 2) / 2) : 0,
    // Palier stable de l'anche visée (palierDe) : témoin « palier » d'Accorder.
    palier,
    // Écart type et étendue de l'anche visée sur sa fenêtre (etabli.js) : « ±0,04 ¢ (0,12) ».
    dispersion,
    // La touche d'à côté sonne : { joue, attendu } (midi) ou null.
    autreNote: autre,
    transpose: t?.transpose ?? 0,
  };
}
