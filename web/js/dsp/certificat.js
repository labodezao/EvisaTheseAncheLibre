// Certificat d'une lecture « sûre » (v63, audit Fable du 15/10/2026, R6, R8, R10, R11, R13, R14 ; v64 : promotion, trois anches R3, horloge R12 ;
// docs/CERTIFICAT.md).
//
// Un accordeur professionnel ne dit « sûr » que s'il peut le prouver. La v62 disait « sûr » à partir de la seule cohérence de sa propre
// lecture (la paire colle au battement, la note a duré assez) : 61 premières lectures « sûr » fausses de plus de 0,5 ¢ sur 134 notes posées
// du plan réaliste de l'audit, 100 % de fausses à 8 Hz et 12 ¢ (une anche hors de la bande du traqueur : la faible est lue pour la forte,
// une raie du peigne pour l'autre), 30 à 50 % de fausses au grave quand les anches se tirent (modulation de phase non modélisée).
//
// Ici une SECONDE LECTURE, indépendante : le son brut des dernières secondes (anneau du moteur) est ajusté par le modèle de deux (nls-bessel.js) ou de
// trois (nls-trio.js, super musette) anches à peigne de Bessel, SANS regarder le traqueur (le moteur ne sert que de départ parmi d'autres), et la
// lecture n'est « sûre » que si TOUS les critères tiennent (audit § 3) :
//   C1 prise saine : ni plage de zéros ni trou dans la fenêtre lue (R11) — le reste de la prise (suppresseur, secteur…) est jugé par prise.js ;
//   C2 peigne sain (R10) : le son est celui d'anches seules (résidu relatif du modèle, plancher entre les raies, partiels assez nets) ;
//      refuse l'intermodulation d'un micro traité, une raie étrangère forte, des anches trop écartées ;
//   C3 résolution : K·Ω·T ≥ 1,5 (les raies des anches sont séparées au partiel le plus haut utilisé) ;
//   C4 étiquette : rapport de vraisemblance ≥ 25 entre la meilleure hypothèse et l'autre (l'anche faible n'est pas une raie latérale) ;
//   C6 stabilité : dérive ≤ 0,5 ¢/s ou excursion de la fenêtre ≤ EXC_MAX ¢, agitation bornée (une fenêtre qui contient la fin d'une attaque est refusée) ;
//   C8 accord : la lecture du traqueur et la seconde lecture s'accordent (tolérance ACCORD_C) ;
//   C9 répétabilité : un second ajustement indépendant (les deux moitiés de la fenêtre, ou une fenêtre décalée) donne la même lecture ;
//   C10 horloge : l'horloge du micro est connue à HORLOGE_MAX_PPM près (horloge-auto.js, calibrage par micro) ; une horloge inconnue ajoute jusqu'à
//       0,3 ¢ d'erreur systématique que rien dans le son ne trahit.
// Sinon l'écran dit pourquoi (R14) : la lecture reste affichée, « en cours », avec une marge de 1,5 ¢ qui interdit « juste » et la validation.
// v64 (PROMOTION) : une lecture certifiée est elle-même la valeur affichée et le « sûr » : le traqueur, qui ne voit pas le biais de modulation de phase des
// fenêtres courtes, n'est plus le goulot du temps de pose.
//
// Le calcul est fait par un Worker dédié (v66, cert-calcul.js / cert-worker.js) ; sans lui, il est réparti sur les images du moteur (générateur : `CERT.PAS_PAR_IMAGE` itérations par image de 85 ms).
import { lireBesselGen, NLS_LLR_SUR } from './nls-bessel.js';
import { lireTrioGen } from './nls-trio.js';
import { centsBetween } from '../music.js';

export const CERT = {
  AGE_MIN_S: 0.9,            // la note doit durer au moins ça avant le premier contrôle
  DEBUT_S: 0.35,             // l'établissement de la note (premières 350 ms) n'est jamais dans la fenêtre
  FEN_MAX_S: 1.5,            // fenêtre visée (plus longue si le besoin de séparation ou de justesse l'exige)
  FEN_ABS_MAX_S: 4,          // fenêtre lue au plus, quoi qu'il arrive
  FEN_MIN_S: 0.6,
  REESSAI_S: 0.4,            // nouvelle tentative quand 0,5 s de son de plus est arrivé
  ESSAIS_MAX: 40,
  JOBS_MAX: 2,               // ajustements menés de front (v64 : 2)
  DECALAGE_MIN_S: 0.5,       // C9 : écart minimal des milieux des deux fenêtres confirmées
  RAFRAICHIR_S: 0.8,         // un certificat est rafraîchi par un nouvel ajustement (point de départ chaud) quand il a cet âge (v64)
  CERT_AGE_MAX_S: 4,         // un certificat qui n'a pas été rafraîchi depuis ce temps tombe
  CERT_AGE_MAX3_S: 2,        // idem pour trois anches (le traqueur n'y sert pas de témoin d'un changement de note)
  PROMOTION: true,          // v64 : la seconde lecture devient la valeur affichée quand elle est certifiée (le « sûr » ne dépend plus de l'état du traqueur)
  NDEPARTS: 5,               // ajustement : nombre de points de départ
  NLIBRE: 2,                 // ajustement : nombre d'hypothèses d'étiquette qui reçoivent une raie étrangère libre (la vraie paire doit pouvoir s'en servir comme la fausse : avec 1, la fausse seule la recevait et gagnait)
  FEN_F0_S: 350,             // v64 : la fenêtre dure au moins FEN_F0_S / f (s) : en ¢, l'erreur d'une fréquence est en 1/f (banc trio : 0,05 ¢ à 1 s au-dessus de 500 Hz, 0,2 ¢ à 2,5 s vers 80 Hz)
  NB_MIN: 1,                 // v64 : la fenêtre couvre au moins ce nombre de battements (en plus de K·Ω·T ≥ KOT_MIN)
  FENETRE_ADAPTIVE: false,   // v64 : la fenêtre se raccourcit après un échec de stabilité ou de peigne
  CHAUD_DT_MAX_S: 1.2,       // un ajustement part d'un autre (à chaud) si le centre de la fenêtre a bougé de moins que cela
  CHAUD_C9: false,           // la seconde fenêtre de C9 part de la solution de la première (rapide, mais la même étiquette)
  CONFIRME_MODE: 1,          // C9 : 0 deux fenêtres décalées (DECALAGE_MIN_S) ; 1 les deux moitiés de la même fenêtre quand elles se résolvent (repli sur 0) ; 2 les deux
  CONFIRME_MOITIE_C: 0.4,    // C9 par moitiés : écart de chaque moitié à l'ajustement entier
  KOT_MOITIE: 1.0,           // C9 par moitiés : K·Ω·T/2 minimal pour que chaque moitié soit lue
  KMAX: 4,                   // ajustement : nombre de partiels
  ITER: 15,                  // ajustement : itérations de l'étape finale
  COUT_PAR_IMAGE: 200,      // bancs (v64) : travail par image en milliers de partiels-échantillons évalués (déterministe) ; null : PAS_PAR_IMAGE
  PAS_PAR_IMAGE: 20,         // itérations de Levenberg-Marquardt par image (bancs et tests : calcul déterministe)
  MS_PAR_IMAGE: null,        // si donné (repli de l'application sans Worker dédié : 40 ms, réglé par adapterBudget ; les bancs : COUT_PAR_IMAGE), c'est le temps qui borne le travail de chaque image, pas le nombre de pas
  ACCORD_SUR_C: 1e9,         // C8 (v64, éteint) : quand le traqueur se dit LUI AUSSI sûr, les deux lectures ne se contredisent pas de plus que cela (essayé à 1 ¢ : 48 % de notes posées au lieu de 63 %, le traqueur étant sûr et faux sur 30 % des notes favorables ; le cas qu'il attrapait, trois raies pures, l'est par LLR_AFFECT_MIN)
  ACCORD_C: 1e9,             // C8 : abandonné en v64 (3 ¢ refuse toute note que le traqueur lit mal, et il en lit mal beaucoup : PB12, +51 notes posées sans lui) ; la vérification de l'étiquette est interne (rival des deux côtés, raie étrangère jamais latérale, deux moitiés)
  CONFIRME_C: 0.3,           // C9 : deux ajustements successifs (fenêtres décalées d'au moins 0,5 s) d'accord à ce point près
  LLR_MIN: NLS_LLR_SUR,      // C4
  IDENT3_ECART: 0.05,        // v66 (F10) : trois anches dont les deux écarts Δ− et Δ+ sont égaux à cette part près ET dont moins de IDENT3_KU_MAX partiels sont nets : indiscernable d'UNE anche modulée (vibrato, tirage), jamais « sûr »
  IDENT3_KU_MAX: 2,
  ABSENTE_DB: 35,            // v66 (F10) : une des trois anches à plus de ce nombre de dB sous la plus forte : elle ne sonne pas (registre fermé), le texte le dit
  SIGMA_TOL_C: 99,           // v66 (C7 de l'audit du 15/10) : marge de précision : 3 σ + 0,02 ¢ de l'ajustement au plus ce nombre de ¢ (99 : éteint ; réglé par plan d'expériences)
  KOT_MIN: 1.5,              // C3
  R_MAX: 0.05,               // C2 : résidu relatif du modèle (juste sans raie étrangère : 0,01 ; avec : jusqu'à 0,08 ; deux anches manquées : 0,085 et plus)
  PLANCHER_MAX_DB: -28,      // C2 : plancher hors modèle, partiels 1 et 2
  BETA_MAX: 0.45,           // C2 : indice de modulation de phase. Au-delà de 0,4 (audit § 1.3) la porteuse n'est plus la raie dominante aux partiels hauts (J0(kβ) < J1(kβ)) et le modèle de Bessel ne tient plus : La5 du 14/10 (β 0,46 à 1,1, raies non proportionnelles au rang) lue à +0,6 ¢ avec une borne à 0,6. La borne de l'ajustement est 0,7, où se collent les faux modèles
  BETA_FORT: 0.45,           // v66 (F8) REFUSÉ, éteint : au-dessus de cet indice de phase estimé, exiger en plus LLR_BETA_FORT, une modulation d'amplitude ≤ M_FORT et des moitiés d'accord à CONFIRME_MOITIE_FORT_C
                             // attrape la note à β vrai 0,48 (β̂ 0,36, m̂ 0,23) que le plan B laisse passer hors du domaine, mais coûte 90 % des notes posées du plan J (β 0,38-0,45, DANS le domaine : 24 sur 50 -> 1 à 5) ;
                             // réglages essayés (plans DOE1, DOE2 et confirmation, docs/CERTIFICAT.md § v66) : 0,35 / 0,15 / 100 / 0,2 et M_FORT 0,2.
  LLR_BETA_FORT: 100,
  M_FORT: 0.15,
  CONFIRME_MOITIE_FORT_C: 0.2,
  M_MAX: 0.3,                // C2 (v64) : indice de modulation d'amplitude ; collé à sa borne (0,45) il est la marque d'un faux modèle où des raies latérales jouent l'anche faible (banc : trois lectures fausses de 16 ¢ sur trois, 0 sur 200 fenêtres justes)
  LLR_AFFECT_MIN: 150,       // C4 (v64) : rapport de vraisemblance minimal de l'échange de rôle entre une anche et la raie étrangère adoptée
  COUPLAGE_MIN: 0.03,        // C4 (v64) : en dessous de cet indice (phase ou amplitude) les anches ne se tirent pas assez pour qu'on lise leur rôle contre une raie étrangère
  LIBRE_VS_FAIBLE_DB: 12,    // une raie étrangère plus faible que l'anche la plus faible de plus que cela (dB) ne compte pas dans l'échange de rôle
  MARGE_ETIQ_DB: 20,         // C4 (v64) : la raie de l'anche faible n'est pas plus de ce nombre de dB sous la raie latérale que l'anche forte met au même endroit (banc : -35 dB = faux modèle ; -10 dB et moins = lectures justes)
  LAG_MAX_C: 0.3,            // v64 : |dérive| · (âge du milieu de la fenêtre) au plus ce nombre de ¢ : une valeur plus vieille que cela cesse d'être « sûre » (lecture à +0,52 ¢ d'une note qui dérive à 0,22 ¢/s, 2,4 s d'âge)
  CONTREDIT_C: 0.3,          // v66 (F1) : une lecture complète qui s'écarte du certificat de plus que max(ce seuil, CONTREDIT_SIGMA σ) + la dérive l'invalide, même si elle est elle-même refusée (0 : éteint)
  CONTREDIT_SIGMA: 3,
  CONTREDIT_DERIVE_MAX_C: 1,
  SENTINELLE: true,          // v66 (F1) : tant qu'un certificat tient, une lecture chaude courte (SENT_FEN_S) toutes les SENT_PERIODE_S vérifie que l'anche n'a pas bougé (un saut de hauteur tombe en ~0,5 s au lieu de 1,5 s)
  SENT_FEN_S: 0.6,
  SENT_PERIODE_S: 0.25,
  SENT_SIGMA: 4,             // tolérance de la sentinelle : max(CONTREDIT_C, SENT_SIGMA σ) (fenêtre courte : plus de fausses alarmes à 3 σ)
  SAUT_C: 0.5,               // v64 : un nouvel ajustement qui s'écarte de plus que cela du certificat en cours l'invalide ; il faut deux fenêtres décalées d'accord pour en poser un autre
  REFUS_RAISONS: ['niveau'], // les refus qui comptent pour REFUS_RECENTS
  REFUS_RECENTS: 3,          // v64 : une lecture n'est posée que si moins de REFUS_RECENTS des 4 ajustements précédents ont été refusés pour le niveau (une anche à plus de 22 dB : le modèle prend alors une raie latérale pour l'anche faible ; 0 = éteint). Banc : plan A, 1 lecture fausse hors domaine (25 dB, Ω 0,3 Hz, β 0,4) devenue 0 ; plans de validation inchangés (116/280 et 223/384 posées) ; avec le peigne et l'étiquette en plus : 9 points de notes posées perdus
  NIVEAU_MIN_DB: 22,         // une anche à plus de ce nombre de dB sous la plus forte n'est pas lue sûrement (banc : deux lectures fausses de 3 et 4 ¢ à 25 dB, Ω = 0,3 Hz ; trois anches : même limite)
  DERIVE_MAX: 0.5,           // C6 : ¢/s
  EXC_MAX: 0.6,              // C6 (v64) : ou une excursion de la hauteur sur la fenêtre (|dérive| · T) d'au plus ce nombre de ¢ (0 : seule la dérive compte)
  AGIT_MAX: 2.5,             // C6 : ¢ (garde-fou seulement : sur les prises réelles le warp suit aussi la modulation au rythme du battement, 0,5 à 1,6 ¢)
  ZERO_MAX_S: 0.0004,        // C1 : plage de zéros exacts de plus de 0,4 ms
  HORLOGE_MAX_PPM: 100,      // C10 : incertitude maximale de l'horloge du micro (100 ppm = 0,17 ¢) ; cfg.horlogeIncertPpm l'annonce (0 : horloge exacte, fichier)
  MARGE_REFUS_C: 1.5,        // marge posée sur une lecture non certifiée
  TENUE_C: 0.25,              // le certificat tient tant que le moteur reste à ce point de lui
  OMEGA_MIN: 0.4,            // Hz : en dessous, pas de battement à lire (v66, F2 : 0,2 en v65 ; sous 0,4 Hz 5 lectures « sûr » fausses sur 51, jusqu'à 0,9 ¢, audit Fable final)
  OMEGA_SUR_MIN: 0.8,        // Hz : la HAUTEUR de chaque anche n'est dite « sûre » qu'au-dessus (raison `lent`, le battement reste mesuré dès 0,4 Hz). EXCEPTION à la règle « seuils sur la synthèse » : la synthèse (450 notes à Ω 0,45-1 Hz, désaccord 2-8 ¢) ne donne AUCUNE lecture fausse (max 0,37 ¢), mais le rejeu des prises H6 du 14/10 au budget de l'application en donne trois à 0,50-0,63 ¢ (Ω vrai 0,40, 0,55 et 0,58 Hz) ; 0,8 laisse la marge du bruit sur Ω ; à reprendre quand la synthèse saura reproduire ce biais (audit Fable final, § 10)
  OMEGA_MAX: 60,             // Hz : au-delà, hors domaine (anches « presque deux notes » ; 25 en v63 ; 50 ¢ à A6 font 51 Hz)
};

// Raisons de refus : clés de langue (ui/langues) et ordre de gravité (la plus parlante d'abord).
export const RAISONS = ['trois', 'ident3', 'absente', 'horloge', 'trous', 'niveau', 'ecartees', 'accordees', 'lent', 'peigne', 'resolution', 'etiquette', 'stabilite', 'accord', 'verification', 'domaine'];

// Jugement d'une seconde lecture. nls : sortie de lireBessel (deux anches) ou lireTrio (trois) ; moteur : { f: [...] } (Hz, calibrés) ; calib : facteur d'horloge.
// Rend { ok, raisons: [...] , detail }.
// `derive` : la dérive (¢/s) mesurée sur les deux moitiés de la fenêtre, plus fiable que celle de l'ajustement (qui se confond avec la modulation de phase à moins de 2 battements) ;
// `sauterStabilite` : pour décider s'il faut lancer les deux moitiés (qui donneront cette dérive).
export function juger(nls, moteur, { calib = 1, zeros = false, opts = CERT, derive = null, sauterStabilite = false } = {}) {
  const raisons = [];
  const detail = {};
  if (zeros) raisons.push('trous');
  if (!nls || !nls.ok) { raisons.push('domaine'); return { ok: false, raisons, detail }; }
  const trio = Array.isArray(nls.Om);
  const f = nls.f.map((v) => v * calib);
  const cents = (a, b) => 1200 * Math.log2(a / b);
  detail.accord = Math.max(...f.map((v, j) => Math.abs(cents(moteur.f[j], v))));
  const omMin = trio ? Math.min(...nls.Om) : nls.Om, omMax = trio ? Math.max(...nls.Om) : nls.Om;
  detail.kot = (trio && Number.isFinite(nls.Ku) ? nls.Ku : nls.K) * omMin * nls.T;       // v66 (F10) : K_utile (partiels nets) pour trois anches
  detail.plancher = Math.max(...nls.plancherDb.slice(0, 2).map((v) => (v == null || Number.isNaN(v) ? 999 : v)));
  if (omMax > opts.OMEGA_MAX) raisons.push('ecartees');
  else if (omMin < opts.OMEGA_MIN) raisons.push('accordees');
  else if (omMin < opts.OMEGA_SUR_MIN) raisons.push('lent');
  const faible = trio ? Math.min(...nls.niveauxDb) : nls.niveauDb;        // niveau de l'anche la plus faible sous la plus forte (dB, négatif)
  if (trio && faible != null && faible < -opts.ABSENTE_DB) raisons.push('absente');
  else if (faible != null && faible < -opts.NIVEAU_MIN_DB) raisons.push('niveau');
  if (trio && Math.abs(nls.Om[1] - nls.Om[0]) <= opts.IDENT3_ECART * 0.5 * (nls.Om[0] + nls.Om[1]) && (nls.Ku ?? 4) <= opts.IDENT3_KU_MAX) raisons.push('ident3');
  const ms = [].concat(nls.m, nls.m2 ?? []).filter((v) => Number.isFinite(v));
  const bMax = Math.max(...nls.b.map(Math.abs)), mMax = Math.max(0, ...ms.map(Math.abs));
  detail.beta = bMax; detail.m = mMax;
  const fort = bMax > opts.BETA_FORT && (!(nls.llr >= opts.LLR_BETA_FORT) || mMax > opts.M_FORT);
  if (!(nls.r <= opts.R_MAX) || !(detail.plancher <= opts.PLANCHER_MAX_DB) || bMax > opts.BETA_MAX || mMax > opts.M_MAX || fort) {
    raisons.push('peigne');
    // la cause, pour que l'écran dise le geste (F6) : anches presque accrochées, micro traité, autre anche qui sonne
    detail.causePeigne = bMax > opts.BETA_MAX || mMax > opts.M_MAX || fort ? 'accrochees' : !(detail.plancher <= opts.PLANCHER_MAX_DB) ? 'micro' : nls.libre ? 'etrangere' : 'micro';
  }
  detail.sigma = Math.max(...(nls.sigmaC ?? [0]).map((x) => (Number.isFinite(x) ? x : 99)));
  if (!(detail.kot >= opts.KOT_MIN) || 3 * detail.sigma + 0.02 > opts.SIGMA_TOL_C) raisons.push('resolution');
  // Rôle des raies : quand une raie étrangère notable (plus haute que −LIBRE_SIG_DB) est adoptée, l'échange de rôle avec chaque anche doit être nettement pire (trois raies
  // pures d'égale force : indécidable, rapport 37 à 120 ; les lectures justes : 360 à 10 000)
  // Sans aucun couplage ajusté (|β| et |m| presque nuls), rien dans le son ne distingue une anche d'une raie étrangère : seul le rapport de vraisemblance de l'échange de rôle
  // reste, et il est trop bas quand les trois raies se valent.
  const couplage = Math.max(0, ...[].concat(nls.b, nls.m, nls.m2 ?? []).filter((v) => Number.isFinite(v)).map(Math.abs));
  // La raie étrangère ne compte que si elle est du même ordre que l'anche la plus faible (LIBRE_VS_FAIBLE_DB) ; sinon les deux anches sont les deux raies les plus fortes, sans équivoque.
  const affect = nls.libre && faible != null && nls.libre.dB > faible - opts.LIBRE_VS_FAIBLE_DB && (!(nls.llrAffectation >= opts.LLR_AFFECT_MIN) || couplage < opts.COUPLAGE_MIN);
  if (!(nls.llr >= opts.LLR_MIN) || affect || !(trio || (nls.margeEtiquette ?? 0) >= -opts.MARGE_ETIQ_DB)) raisons.push('etiquette');
  const d = derive ?? nls.derive;
  if (!sauterStabilite && (!(Math.abs(d) <= opts.DERIVE_MAX || Math.abs(d) * nls.T <= (opts.EXC_MAX ?? 0)) || !(nls.agit <= opts.AGIT_MAX))) raisons.push('stabilite');
  if (!(detail.accord <= (moteur.sur ? Math.min(opts.ACCORD_C, opts.ACCORD_SUR_C) : opts.ACCORD_C))) raisons.push('accord');
  return { ok: raisons.length === 0, raisons, detail };
}

// Ajustement d'une fenêtre : l'ajustement entier ; s'il passe C1 à C8 et que les moitiés se résolvent, les deux moitiés (point de départ chaud : la lecture
// entière) pour C9 par moitiés. Générateur : un `yield` par pas, comme lireBesselGen. n : 2 ou 3 anches.
export function* ajusterFenetre(n, x, sr, fc, optsFit, opts, calib, moteur) {
  const lire = n === 3 ? lireTrioGen : lireBesselGen;
  const main = yield* lire(x, 0, x.length, sr, fc, optsFit);
  if (main.ok && opts.CONFIRME_MODE >= 1) {
    const v = juger(main, moteur, { calib, zeros: false, opts, sauterStabilite: true });
    const omMin = n === 3 ? Math.min(...main.Om) : main.Om;
    if (v.ok && main.K * omMin * main.T / 2 >= opts.KOT_MOITIE) {
      const mid = x.length >> 1, h = [];
      for (const [a, b] of [[0, mid], [mid, x.length]]) {
        const r = yield* lire(x, a, b, sr, fc, { ...optsFit, prior: main.f, priorFirst: true, nDeparts: 1, chaud: true, pInit: main.sol, dt: ((a + b) / 2 - x.length / 2) / sr, libreInit: main.libre ? main.sol[n === 3 ? 13 : 8] : null });
        h.push(r.ok ? r.f : null);
      }
      main.moities = h;
    }
  }
  return main;
}

// Un travail complet (v66, F4) : une description sans fonctions, exécutable dans le Worker du certificat ou en ligne. Rend le résultat SANS le modèle (`mod`, lourd, non transférable).
export function* executerTravail(spec) {
  const lire = spec.n === 3 ? lireTrioGen : lireBesselGen;
  const nls = spec.sentinelle ? yield* lire(spec.x, 0, spec.x.length, spec.sr, spec.fc, spec.optsFit) : yield* ajusterFenetre(spec.n, spec.x, spec.sr, spec.fc, spec.optsFit, spec.opts, spec.calib, spec.moteur);
  if (nls && nls.ok) { const { mod, debug, ...reste } = nls; void mod; void debug; return reste; }
  return nls;
}

// Battement d'une note tenue (Ewen, 16/10/2026 : « 25, puis 27, puis 26, puis 25 battements/min : c'est quoi la vraie valeur ? »). Les battements Ω des ajustements
// successifs (`pts` : { t (milieu de la fenêtre, s), T (durée), om (Hz) }) sont moyennés sur TOUTE la plage tenue, pesés par la durée de leur fenêtre, au lieu d'une fenêtre courte
// glissante. Incertitude : écart type entre ajustements divisé par la racine du nombre d'ajustements INDÉPENDANTS (durée couverte / durée d'une fenêtre : les fenêtres se recouvrent).
// Si le battement varie vraiment (pression du soufflet : le battement d'une anche en dépend), la pente de la droite pesée est significative (> 2,5 écarts types) : la valeur est celle de
// la droite au dernier ajustement et la pente est donnée à part comme tendance (batt/min par seconde), pas comme bruit.
export function estimerBattement(pts) {
  const n = pts.length;
  if (n < 2) return null;
  const W = pts.reduce((a, p) => a + p.T, 0);
  const m = pts.reduce((a, p) => a + p.T * p.om, 0) / W;
  const t0 = Math.min(...pts.map((p) => p.t - p.T / 2)), t1 = Math.max(...pts.map((p) => p.t + p.T / 2));
  const nEff = Math.max(1, (t1 - t0) / (W / n));
  const s2 = pts.reduce((a, p) => a + p.T * (p.om - m) ** 2, 0) / W * n / (n - 1);
  let hz = m, sigma = Math.sqrt(s2 / nEff), tendanceHzS = 0, tendance = false;
  if (n >= 4) {
    const tm = pts.reduce((a, p) => a + p.T * p.t, 0) / W;
    const sxx = pts.reduce((a, p) => a + p.T * (p.t - tm) ** 2, 0);
    if (sxx > 0) {
      const b = pts.reduce((a, p) => a + p.T * (p.t - tm) * (p.om - m), 0) / sxx;
      const res2 = pts.reduce((a, p) => a + p.T * (p.om - m - b * (p.t - tm)) ** 2, 0) / W * n / (n - 2);
      const seb = Math.sqrt(res2 / sxx * (n / nEff));
      if (Math.abs(b) > 2.5 * seb && Math.abs(b) * (t1 - t0) > 0.02) {
        const tL = Math.max(...pts.map((p) => p.t));
        tendance = true; tendanceHzS = b;
        hz = m + b * (tL - tm);
        sigma = Math.sqrt(res2 / nEff + (seb * (tL - tm)) ** 2);
      }
    }
  }
  sigma = Math.max(sigma, 0.0015);                    // 0,09 batt/min : sous ce chiffre l'incertitude annoncée ne serait plus réaliste (banc d'étalonnage : erreur RMS 0,05 à 0,07 batt/min)
  return { hz, sigmaHz: sigma, bpm: hz * 60, sigmaBpm: sigma * 60, tendance, tendanceBpmS: tendanceHzS * 60, n, nEff, duree: t1 - t0 };
}

// Plus longue plage de zéros exacts (en secondes) dans x[i0, i1), et la fin de la dernière plage trop longue (indice, ou -1).
export function plagesDeZeros(x, i0, i1, sr) {
  const seuil = Math.max(8, Math.round(CERT.ZERO_MAX_S * sr));
  let run = 0, finDerniere = -1;
  for (let i = i0; i < i1; i++) {
    if (x[i] === 0) run++;
    else { if (run >= seuil) finDerniere = i; run = 0; }
  }
  if (run >= seuil) finDerniere = i1;
  return finDerniere;
}

// Méthodes d'Engine (engine.js, Object.assign).
export const methodesCertificat = {
  // Anneau du son brut (8 s), alimenté par process().
  initAnneau() {
    this.anneau = new Float32Array(Math.round(8 * this.sr));
    this.certEtat = new Map();
  },
  alimenterAnneau(chunk) {
    if (!this.anneau) return;
    const L = this.anneau.length, n = chunk.length, p = this.samplesTotal - n;     // samplesTotal est déjà incrémenté
    const a = ((p % L) + L) % L;
    if (a + n <= L) this.anneau.set(chunk, a);
    else { const k = L - a; this.anneau.set(chunk.subarray(0, k), a); this.anneau.set(chunk.subarray(k), 0); }
  },
  // Copie contiguë de [i0, i1) (indices absolus en échantillons), ou null si trop ancien.
  extraireAnneau(i0, i1) {
    const L = this.anneau.length;
    if (i1 > this.samplesTotal || i0 < this.samplesTotal - L || i1 <= i0) return null;
    const out = new Float32Array(i1 - i0);
    for (let i = i0, o = 0; i < i1; ) {
      const a = ((i % L) + L) % L, k = Math.min(L - a, i1 - i);
      out.set(this.anneau.subarray(a, a + k), o); o += k; i += k;
    }
    return out;
  },

  // Appelée par fuserBattement après etatPaire pour le groupe à deux anches.
  certifierPaire(g, tNow) {
    const c = this.cohEtat?.get(`${g.key}:${g.center}`);
    this.certifierGroupe(g, tNow, 2, c?.t0 ?? null);
  },
  // Super musette : le groupe à trois voix. L'âge de la note est compté ici (le traqueur de paire n'en suit pas).
  certifierTrio(g, tNow) {
    if (this.cfg.certificat?.actif === false) return;
    if (g.voices.length !== 3) {
      // quatre voix ou plus : pas de modèle ; une lecture « sûre » du traqueur devient « en cours », raison 'trois'
      for (const v of g.voices) {
        v.refus = null;
        if (v.tracked && (v.etatAnche === 'sur' || v.etatAnche == null || v.margeAnche === 0)) {
          v.etatAnche = 'en cours'; v.margeAnche = Math.max(v.margeAnche || 0, CERT.MARGE_REFUS_C); v.refus = 'trois'; v.tBesoin = null;
        }
      }
      return;
    }
    this.certifierGroupe(g, tNow ?? this.samplesTotal / this.sr, 3, null);
  },

  // Pose `refus` / `cert` sur les voix et, si la lecture n'est pas certifiée, ramène `etatAnche` à « en cours » avec une marge. v64 (`PROMOTION`) :
  // une seconde lecture certifiée devient la valeur affichée et le « sûr » (le traqueur peut être encore « en cours » ou « au centre »).
  certifierGroupe(g, tNow, n, t0Note) {
    const opts = { ...CERT, ...(this.cfg.certificat ?? {}) };
    if (this.cfg.certificat?.actif === false) return;
    const cle = `${g.key}:${g.center}`;
    const vs = [...g.voices].sort((a, b) => a.target - b.target);
    const ok = (v) => v?.tracked && !v.held && !v.coarse && !v.merged && Number.isFinite(v.fMeas);
    if (!this.anneau) this.initAnneau();
    for (const v of vs) if (v) { v.refus = null; v.refusCause = null; v.cert = null; }
    // le battement affiché ne saute pas quand l'état de la note est perdu un instant (le traqueur change de note, une anche manque une image) : 1,5 s de mémoire
    this.batMemo ??= new Map();
    const memo = this.batMemo.get(cle);
    if (n === 2 && memo && tNow - memo.t <= 1.5) for (const v of vs) v.beatCert = memo.b;
    // v64 : la seconde lecture ne dépend pas du traqueur. Il lit mal les trios (il n'en suit parfois aucune des trois voix : 11 notes sur 120 du plan B) et perd les paires
    // trop battantes ; elle part de ce qu'il donne, sinon des fréquences visées, dès que la note sonne et qu'elle est connue (note imposée) ou, pour trois anches, à moitié suivie.
    const connue = this.cfg.lockNote != null;
    if (n === 3 ? !(connue || vs.some(ok)) : !(vs.every(ok) || connue)) { this.certEtat.delete(cle); return; }
    let st = this.certEtat.get(cle);
    if (st && tNow - st.vu > 1.0) st = null;                                // un silence : une autre note
    if (st && st.t0Src === 'moteur' && t0Note != null && st.t0 !== t0Note) st = null;      // le traqueur a vu une autre note
    if (!st) {
      st = { t0: t0Note ?? tNow, t0Src: t0Note != null ? 'moteur' : 'propre', jobs: [], cands: [], cert: null, essais: 0, tFenFin: -1e9, tDernierFit: -1e9, vu: tNow, omega: null, derniere: null };
      this.certEtat.set(cle, st);
    }
    st.vu = tNow;
    const calib = 1 + (this.cfg.calibrationPpm || 0) * 1e-6;
    const age = tNow - st.t0;
    const pasI = opts.PAS_PAR_IMAGE ?? CERT.PAS_PAR_IMAGE;
    const fMoteur = () => vs.map((v) => (ok(v) ? v.fMeas : v.target));       // ce que le traqueur donne, sinon la fréquence visée (note imposée)
    const moteurSur = n === 2 && vs.every((v) => ok(v) && v.etatAnche === 'sur');       // le traqueur se dit sûr (avant que la seconde lecture ne s'en mêle)

    // 1. les calculs en cours se partagent le travail de cette image (un pas chacun à tour de rôle). Le travail se compte en temps réel dans l'application
    //    (MS_PAR_IMAGE), en unités de coût déterministes dans les bancs (COUT_PAR_IMAGE : milliers de partiels-échantillons évalués, ~ 0,35 ms sur un PC de bureau),
    //    à défaut en nombre de pas (PAS_PAR_IMAGE, v63).
    if (this.certExec) {
      // v66 (F4) : les ajustements se font dans un Worker dédié ; ici on ne fait que recevoir ce qui est fini
      for (const res of this.certExec.recuperer(cle, tNow)) {
        const i = st.jobs.findIndex((j) => j.id === res.id);
        if (i < 0) continue;                                       // la note a changé entre-temps : résultat périmé
        const job = st.jobs.splice(i, 1)[0];
        job.msCalcul = res.ms;
        if (res.erreur) { st.derniere = { ok: false, raisons: ['domaine'], t: tNow, erreur: String(res.erreur) }; st.cands = []; continue; }
        if (job.sentinelle) this.finirSentinelle(st, job, res.nls, tNow, calib, opts); else this.finirAjustement(st, job, res.nls, tNow, calib, opts, n);
      }
      st.jobs = st.jobs.filter((j) => tNow - j.tFin < 12);        // un travail qui ne revient jamais (Worker mort) ne bloque pas la note
    } else if (st.jobs.length) {
      const tDebut = opts.MS_PAR_IMAGE ? performance.now() : 0;
      let cout = 0;
      for (let i = 0; st.jobs.length && (opts.MS_PAR_IMAGE ? i === 0 || performance.now() - tDebut < opts.MS_PAR_IMAGE : opts.COUT_PAR_IMAGE ? cout < opts.COUT_PAR_IMAGE : i < pasI); i++) {
        const job = st.jobs[i % st.jobs.length];
        let r;
        try { r = job.gen.next(); } catch (e) { st.jobs.splice(st.jobs.indexOf(job), 1); st.derniere = { ok: false, raisons: ['domaine'], t: tNow, erreur: String(e?.message ?? e) }; st.cands = []; continue; }
        cout += typeof r.value === 'number' && !r.done ? r.value : 0.5;
        if (r.done) {
          st.jobs.splice(st.jobs.indexOf(job), 1);
          if (job.sentinelle) this.finirSentinelle(st, job, r.value, tNow, calib, opts); else this.finirAjustement(st, job, r.value, tNow, calib, opts, n);
        }
      }
    }

    // 2. démarrage d'un calcul
    const certTient = st.cert?.ok && this.certAccord(st.cert, vs, tNow, opts);
    const aRafraichir = certTient && tNow - st.cert.t >= opts.RAFRAICHIR_S;
    const tPeut = tNow - st.tFenFin >= opts.REESSAI_S;
    if (st.jobs.filter((j) => !j.sentinelle).length < opts.JOBS_MAX && (!certTient || aRafraichir) && age >= opts.AGE_MIN_S && tPeut && st.essais < opts.ESSAIS_MAX) {
      const iFin = this.samplesTotal;
      // la fenêtre attend d'avoir de quoi séparer les raies (K·Ω·T ≥ KOT_MIN, au moins NB_MIN battements) et de quoi lire assez juste pour la hauteur de la note
      // (FEN_F0_S / f : en ¢, l'erreur d'une fréquence est en 1/f) ; elle vise FEN_MAX_S mais jamais moins que ce besoin, jamais plus que FEN_ABS_MAX_S
      const fm = fMoteur();
      const ecarts = fm.slice(1).map((f, j) => Math.abs(f - fm[j]));
      const om = st.omega ?? Math.min(...ecarts);
      const K = Math.max(1, Math.min(opts.KMAX, Math.floor(0.42 * this.sr / (fm[n - 1] * 1.04))));
      const omOk = om >= opts.OMEGA_MIN && om <= opts.OMEGA_MAX;
      const besoin = omOk ? Math.max(opts.FEN_MIN_S, (opts.NB_MIN ?? 0) / om, (opts.FEN_F0_S ?? 0) / fm[n >> 1], 1.1 * opts.KOT_MIN / (K * om)) : opts.FEN_MIN_S;
      const plafond = Math.min(opts.FEN_ABS_MAX_S, this.anneau.length / this.sr - 0.1);
      const fen0 = Math.min(Math.min(plafond, Math.max(Math.min(st.fenCap ?? opts.FEN_MAX_S, opts.FEN_MAX_S), besoin)), age - opts.DEBUT_S);
      if (fen0 >= besoin) {
        let x = this.extraireAnneau(iFin - Math.round(fen0 * this.sr), iFin);
        if (x) {
          // R11 : une fenêtre qui contient une plage de zéros (porte du micro) ou un trou est exclue ; on ne lit que ce qui la suit
          const zFin = plagesDeZeros(x, 0, x.length, this.sr);
          let zeros = false;
          if (zFin >= 0) { x = x.subarray(zFin); zeros = true; }
          const fen = x.length / this.sr;
          st.tFenFin = tNow;
          if (fen >= Math.min(besoin, opts.FEN_MIN_S) && fen >= 0.3) {
            // point de départ chaud : après un certificat (rafraîchissement) ou, si CHAUD_C9, pour la seconde fenêtre de C9
            const dernierCand = st.cands[st.cands.length - 1];
            let chaud = st.cert?.ok && st.cert.sol ? st.cert : opts.CHAUD_C9 && dernierCand?.sol ? dernierCand : null;
            // à chaud seulement si la fenêtre n'a pas trop bougé depuis l'ajustement d'où l'on part (au-delà, les paramètres faibles — indices de modulation, phases — ne sont plus un bon départ)
            if (chaud && Math.abs((tNow - fen / 2) - chaud.tMilieu) > opts.CHAUD_DT_MAX_S) chaud = null;
            const prior = chaud ? chaud.f.map((f) => f / calib) : fMoteur().map((f) => f / calib);
            this.lancerTravail(st, cle, tNow, { n, x, sr: this.sr, fc: g.center, optsFit: { prior, priorFirst: !!chaud, chaud: !!chaud, pInit: chaud?.sol ?? null, dt: chaud ? (tNow - fen / 2) - chaud.tMilieu : 0, libreInit: chaud?.sol && chaud.libre ? chaud.sol[n === 3 ? 13 : 8] : null, Kmax: opts.KMAX, iter: opts.ITER, nLibre: opts.NLIBRE, nDeparts: chaud ? 1 : opts.NDEPARTS }, opts, calib, moteur: { f: fMoteur(), sur: moteurSur } },
              { fMoteur: fMoteur(), moteurSur, tMilieu: tNow - fen / 2, tFin: tNow, T: fen, zeros });
          } else if (zeros) { st.derniere = { ok: false, raisons: ['trous'], t: tNow }; st.cands = []; }
        }
      }
    }

    // 2 bis. sentinelle (F1)
    if (opts.SENTINELLE && certTient && !st.jobs.some((j) => j.sentinelle) && tNow - (st.tSent ?? -1e9) >= opts.SENT_PERIODE_S && st.cert.sol) {
      const fenS = Math.min(opts.SENT_FEN_S, age - opts.DEBUT_S);
      if (fenS >= 0.45) {
        const xs = this.extraireAnneau(this.samplesTotal - Math.round(fenS * this.sr), this.samplesTotal);
        if (xs && plagesDeZeros(xs, 0, xs.length, this.sr) < 0) {
          st.tSent = tNow;
          const ch = st.cert;
          this.lancerTravail(st, cle, tNow, { n, sentinelle: true, x: xs, sr: this.sr, fc: g.center, optsFit: { prior: ch.f.map((f) => f / calib), priorFirst: true, chaud: true, pInit: ch.sol, dt: (tNow - fenS / 2) - ch.tMilieu, libreInit: ch.sol && ch.libre ? ch.sol[n === 3 ? 13 : 8] : null, Kmax: opts.KMAX, iter: opts.ITER, nLibre: 0, nDeparts: 1 } },
            { sentinelle: true, tMilieu: tNow - fenS / 2, tFin: tNow, T: fenS });
        }
      }
    }

    // 3. verdict affiché
    const certOk = st.cert?.ok && this.certAccord(st.cert, vs, tNow, opts);
    const raisons = certOk ? [] : st.derniere && !st.derniere.ok ? st.derniere.raisons : ['verification'];
    const dernier = st.cert ?? st.derniere;
    for (const v of vs) { v.cert = dernier ? { ok: !!certOk, llr: dernier.nls?.llr ?? null, r: dernier.nls?.r ?? null, derive: dernier.nls?.derive ?? null, raisons: certOk ? [] : (st.derniere?.raisons ?? null), essais: st.essais, beta: dernier.detail?.beta ?? null, m: dernier.detail?.m ?? null, plancher: dernier.detail?.plancher ?? null, kot: dernier.detail?.kot ?? null, libre: dernier.nls?.libre ?? null, sigmaC: dernier.nls?.sigmaC ?? null } : null; }
    // Battement affiché (deux anches) : une valeur qui converge, qui ne change que si l'écart dépasse son incertitude, arrondie à la précision réelle
    if (n === 2 && st.omegas?.length >= 2) {
      const e = estimerBattement(st.omegas);
      if (e) {
        const pas = Math.max(0.1, Math.round(e.sigmaBpm * 5) / 10);                    // arrondi au demi-écart type (0,1 batt/min au plus fin)
        const seuil = Math.max(e.sigmaBpm, 0.2);
        if (!st.bat || Math.abs(e.bpm - st.bat.bpm) > seuil) st.bat = { bpm: Math.round(e.bpm / pas) * pas };
        const posee = e.n >= 3 && e.sigmaBpm <= 0.5 && e.duree >= 2;
        const b = { serie: st.omegas.slice(-30).map((p) => ({ t: p.t, T: p.T, bpm: p.om * 60 })), bpm: st.bat.bpm, hz: st.bat.bpm / 60, sigmaBpm: e.sigmaBpm, sigmaHz: e.sigmaHz, pas, tendance: e.tendance, tendanceBpmS: e.tendanceBpmS, n: e.n, duree: e.duree, posee };
        for (const v of vs) v.beatCert = b;
        this.batMemo.set(cle, { b, t: tNow });
      }
    }
    // C10 : l'horloge du micro n'est pas connue assez bien : la lecture est peut-être juste, rien ne le prouve
    const horlogeMal = (this.cfg.horlogeIncertPpm ?? 0) > opts.HORLOGE_MAX_PPM;
    if (certOk && !horlogeMal) {
      if (opts.PROMOTION) {
        // La valeur affichée suit la hauteur qui bouge depuis l'ajustement : le mouvement COMMUN du traqueur depuis ce moment (lissé), jamais son biais (qui s'annule).
        // Sans cela, 0,3 ¢/s de dérive et 1,5 s d'âge font 0,5 ¢ d'erreur (plan PB12, la seule lecture « sûr » fausse sur 14 000).
        const fit = st.cert.moteurAuFit, suivies = vs.map((v, j) => ok(v) && Number.isFinite(fit?.[j]));
        if (suivies.some(Boolean)) {
          const moy = vs.reduce((a, v, j) => a + (suivies[j] ? 1200 * Math.log2(v.fMeas / fit[j]) : 0), 0) / suivies.filter(Boolean).length;
          st.corr = st.corr == null ? moy : 0.5 * st.corr + 0.5 * moy;
        }
        const corr = Math.max(-0.5, Math.min(0.5, st.corr ?? 0));
        this.promouvoir(vs, st.cert, tNow, corr);
      }
      return;
    }
    // pas certifiée : si le traqueur la disait « sûre » (ou ne disait rien), elle devient « en cours » avec une marge qui interdit « juste »
    const etat = vs[0].etatAnche;
    if (etat === 'sur' || etat == null || vs[0].margeAnche === 0 || (certOk && horlogeMal && opts.PROMOTION)) {
      const motif = horlogeMal ? 'horloge' : RAISONS.find((r) => raisons.includes(r)) ?? 'verification';
      for (const v of vs) {
        v.etatAnche = 'en cours';
        v.margeAnche = Math.max(v.margeAnche || 0, opts.MARGE_REFUS_C);
        v.refus = motif;
        v.refusCause = motif === 'peigne' ? (st.derniere?.detail?.causePeigne ?? null) : null;
        v.tBesoin = null;
      }
    }
  },

  // Met un travail en route : dans le Worker du certificat (`this.certExec`, v66) ou, à défaut, en ligne par tranches (bancs, tests).
  lancerTravail(st, cle, tNow, spec, meta) {
    if (this.certExec?.mort) this.certExec = null;                  // le Worker du certificat a planté : calcul en ligne
    if (this.certExec) {
      const id = (this.certSeq = (this.certSeq ?? 0) + 1);
      if (spec.x.byteOffset !== 0 || spec.x.buffer.byteLength !== spec.x.byteLength) spec.x = Float32Array.from(spec.x);
      this.certExec.soumettre({ id, cle, ...spec }, tNow);
      st.jobs.push({ ...meta, id });
    } else st.jobs.push({ ...meta, gen: executerTravail(spec) });
  },

  // Un ajustement est fini : jugement C1 à C8, puis C9 (les deux moitiés, ou deux fenêtres décalées d'au moins DECALAGE_MIN_S, d'accord à CONFIRME_C).
  finirAjustement(st, job, nls, tNow, calib, opts, n = 2) {
    const ecartM = (a, b) => 1200 * Math.log2(a / b);
    const hs = nls.ok ? nls.moities : null;
    // dérive sur les deux moitiés : la hauteur de la seconde moitié contre celle de la première, par seconde de décalage de leurs centres (T/2)
    const deriveM = hs && hs.every(Boolean) ? Math.abs(hs[1].reduce((a, x, j) => a + ecartM(x, hs[0][j]), 0) / hs[1].length) / (nls.T / 2) : null;
    const v = juger(nls, { f: job.fMoteur, sur: job.moteurSur }, { calib, zeros: false, opts, derive: deriveM });
    const f = nls.ok ? nls.f.map((x) => x * calib) : null;
    // battement de la note : les ajustements dont seule la confirmation ou l'accord manque donnent un Ω aussi bon que les autres
    if (n === 2 && nls.ok && v.raisons.every((q) => ['verification', 'accord', 'stabilite', 'lent'].includes(q)) && nls.r <= opts.R_MAX) { (st.omegas ??= []).push({ t: job.tMilieu, T: job.T, om: nls.Om * calib }); if (st.omegas.length > 150) st.omegas.shift(); }
    st.essais++;
    st.tDernierFit = tNow;
    const refusModele = (r) => !r.ok && r.raisons?.some((q) => opts.REFUS_RAISONS.includes(q));
    const recents = (st.recents ??= []);
    const nRefusRecents = recents.filter(Boolean).length;
    recents.push(refusModele(v)); if (recents.length > 4) recents.shift();
    if (nls.ok) st.omega = n === 3 ? Math.min(...nls.Om) : nls.Om;
    const ecart = (a, b) => Math.max(...a.map((x, j) => Math.abs(1200 * Math.log2(x / b[j]))));
    // fenêtre adaptative (v64) : un ajustement que la hauteur qui bouge ou un modèle qui ne tient pas (attaque dans la fenêtre) fait échouer raccourcit la suivante,
    // qui ne garde que la fin du son ; un ajustement qui passe (ou qui manque de résolution) rend sa longueur.
    if (opts.FENETRE_ADAPTIVE) {
      const rr = v.raisons ?? [];
      if (v.ok || rr.includes('resolution')) st.fenCap = opts.FEN_MAX_S;
      else if (rr.includes('stabilite') || (rr.includes('peigne') && (nls.r ?? 1) > 0.15)) st.fenCap = Math.max(opts.FEN_MIN_S, 0.6 * job.T);
    }
    // les candidats (C1 à C8 passés) des 5 dernières secondes ; un échec net (autre que l'accord avec le traqueur, qui n'engage que lui) les efface
    st.cands = st.cands.filter((q) => tNow - q.t <= 5);
    const sol = nls.ok && nls.sol ? Array.from(nls.sol).slice(0, n === 3 ? 14 : 9) : null;
    // Un ajustement qui contredit le certificat en cours (écart > SAUT_C) alors que la note n'a pas changé : l'un des deux est faux (étiquette échangée, raie latérale
    // prise pour une anche). Le certificat tombe et il faut deux fenêtres décalées d'accord (pas seulement les deux moitiés d'une même fenêtre) pour en poser un autre.
    let exigeDecalage = !!st.saut;
    if (st.cert?.ok && st.cert.f && f && tNow - st.cert.t <= opts.CERT_AGE_MAX_S) {
      const e = ecart(f, st.cert.f);
      // v66 (F1, audit Fable final : saut de hauteur en cours de note, 25 « sûr » faux jusqu'à 2,9 ¢) : une lecture COMPLÈTE qui contredit le certificat l'invalide, qu'elle passe les
      // critères ou non (une fenêtre qui chevauche le saut échoue en `peigne` ou en `stabilite` : c'est justement le signe du saut). Tolérance : max(CONTREDIT_C, k σ) plus la
      // dérive connue sur l'écart des centres des deux fenêtres.
      const sig = Math.max(...(nls.sigmaC ?? [0]).map((x) => (Number.isFinite(x) ? x : 0)));
      const tolC = Math.max(opts.CONTREDIT_C, opts.CONTREDIT_SIGMA * sig) + Math.min(opts.CONTREDIT_DERIVE_MAX_C, Math.abs(st.cert.derive ?? 0) * Math.abs(job.tMilieu - st.cert.tMilieu));
      if ((v.ok && e > opts.SAUT_C) || (opts.CONTREDIT_C > 0 && nls.ok && e > tolC)) { st.cert = null; st.saut = true; st.cands = []; exigeDecalage = true; st.invalides = (st.invalides ?? 0) + 1; }
    }
    if (v.ok && opts.REFUS_RECENTS > 0 && nRefusRecents >= opts.REFUS_RECENTS) { v.ok = false; v.raisons = ['niveau']; st.cands = []; }
    if (v.ok) {
      const parDecalage = st.cands.find((q) => Math.abs(job.tMilieu - q.tMilieu) >= opts.DECALAGE_MIN_S && ecart(f, q.f) <= opts.CONFIRME_C);
      const mo = nls.moities;
      const tolMoitie = Math.max(...nls.b.map(Math.abs)) > opts.BETA_FORT ? Math.min(opts.CONFIRME_MOITIE_C, opts.CONFIRME_MOITIE_FORT_C) : opts.CONFIRME_MOITIE_C;
      const parMoities = mo && mo.every(Boolean) && mo.every((h) => ecart(h.map((x) => x * calib), f) <= tolMoitie);
      const ami = exigeDecalage || opts.CONFIRME_MODE === 0 ? parDecalage : opts.CONFIRME_MODE === 1 ? (mo ? parMoities : parDecalage) : (parDecalage && (!mo || parMoities));
      st.cands.push({ f, tMilieu: job.tMilieu, t: tNow, sol, libre: !!nls.libre });
      if (ami) {
        st.cert = { ...v, t: tNow, tMilieu: job.tMilieu, nls: resumeNls(nls), f, moteurAuFit: job.fMoteur, sol, libre: !!nls.libre, derive: deriveM ?? nls.derive };
        st.derniere = st.cert; st.corr = null; st.saut = false;
        return;
      }
      v.ok = false; v.raisons = ['verification'];
    } else if (!v.raisons.every((q) => q === 'accord')) st.cands = [];
    st.derniere = { ...v, t: tNow, tMilieu: job.tMilieu, nls: resumeNls(nls), f };
  },

  // La sentinelle (F1) : une lecture chaude sur la fin du son seulement. Elle ne pose rien et ne compte pas parmi les essais : elle invalide un certificat que la note a quitté.
  finirSentinelle(st, job, nls, tNow, calib, opts) {
    const ch = st.cert;
    if (!nls?.ok || !ch?.ok || !ch.f || nls.Om == null) return;
    const f = nls.f.map((x) => x * calib);
    const e = Math.max(...f.map((x, j) => Math.abs(1200 * Math.log2(x / ch.f[j]))));
    const sig = Math.max(...(nls.sigmaC ?? [0]).map((x) => (Number.isFinite(x) ? x : 0)));
    const tol = Math.max(opts.CONTREDIT_C, opts.SENT_SIGMA * sig) + Math.min(opts.CONTREDIT_DERIVE_MAX_C, Math.abs(ch.derive ?? 0) * Math.abs(job.tMilieu - ch.tMilieu));
    if (e > tol) { st.cert = null; st.saut = true; st.cands = []; st.invalides = (st.invalides ?? 0) + 1; st.sentinelles = (st.sentinelles ?? 0) + 1; }
  },

  // v64 : la seconde lecture certifiée est la valeur affichée.
  promouvoir(vs, cert, tNow, corrC = 0) {
    for (let j = 0; j < vs.length; j++) {
      const v = vs[j], f = cert.f[j] * 2 ** (corrC / 1200);
      v.fBrute = v.fMeas;
      v.fMeas = f;
      v.dCents = centsBetween(f, v.nominal);
      v.dHz = f - v.nominal;
      v.dTargetCents = centsBetween(f, v.target);
      v.tracked = true; v.coarse = false; v.held = false; v.merged = false;       // la seconde lecture a trouvé l'anche que le traqueur n'a pas suivie
      // « anches proches » / « confondue avec l'octave » : la marge du traqueur (fenêtre qui ne sépare pas les anches) ne vaut plus, la seconde lecture les sépare
      v.confondu = false; v.fEstimee = null; v.margeCents = null; v.proches = null; v.seule = false;
      v.etatAnche = 'sur'; v.margeAnche = 0; v.refus = null; v.tBesoin = null; v.source = 'certificat';
      v.sigmaCert = cert.nls?.sigmaC?.[j] ?? null;
      v.corrCert = corrC;
    }
    void tNow;
  },

  // Le certificat tient-il encore ? Le traqueur reste là où il était, par rapport à la seconde lecture, à la dérive près (son écart fixe, son biais de
  // modulation de phase, n'est pas un mouvement de la note). Un certificat de plus de CERT_AGE_MAX_S sans rafraîchissement tombe.
  certAccord(cert, vs, tNow, opts) {
    if (!cert?.ok || !cert.f) return false;
    if (tNow - cert.t > (vs.length === 3 ? opts.CERT_AGE_MAX3_S : opts.CERT_AGE_MAX_S)) return false;
    const dt = Math.max(0, tNow - (cert.tMilieu ?? cert.t));
    // âge de la valeur affichée : la hauteur qui dérive de d ¢/s l'a quittée de d · (âge du milieu de la fenêtre) ; au-delà de LAG_MAX_C la valeur ne dit plus « maintenant »
    const deriv = Math.abs(cert.derive ?? cert.nls?.derive ?? 0);
    if (deriv * dt > opts.LAG_MAX_C) return false;
    const tol = opts.TENUE_C + Math.min(0.1, deriv * dt);
    const e = (a, b) => 1200 * Math.log2(a / b);
    const fit = cert.moteurAuFit ?? cert.f;
    // seules les voix que le traqueur suit servent de témoin (trois anches : parfois aucune)
    return vs.every((v, j) => !(v.tracked && !v.held && !v.coarse && !v.merged && Number.isFinite(v.fMeas)) || Math.abs(e(v.fMeas, cert.f[j]) - e(fit[j], cert.f[j])) <= tol);
  },
};

function resumeNls(r) {
  if (!r?.ok) return { ok: false, raison: r?.raison ?? null };
  return { f: r.f, Om: r.Om, b: r.b, m: r.m, llr: r.llr, r: r.r, K: r.K, T: r.T, Ku: r.Ku, derive: r.derive, agit: r.agit, warpC: r.warpC, libre: r.libre ? { dB: r.libre.dB } : null, plancherDb: r.plancherDb, niveauxDb: r.niveauxDb ?? null, sigmaC: r.sigmaC, ms: r.ms };
}
