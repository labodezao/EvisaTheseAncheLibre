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
//   C8 accord : abandonné en v64 (retiré en v69, CERTIFICAT.md § 0C) : le traqueur n'est plus un témoin de la lecture certifiée (la lecture certifiée est la valeur affichée) ;
//   C9 répétabilité : un second ajustement indépendant (les deux moitiés de la fenêtre, ou une fenêtre décalée) donne la même lecture ;
//   C10 horloge : l'horloge du micro est connue à HORLOGE_MAX_PPM près (horloge-auto.js, calibrage par micro) ; une horloge inconnue ajoute jusqu'à
//       0,3 ¢ d'erreur systématique que rien dans le son ne trahit.
// Sinon l'écran dit pourquoi (R14) : la lecture reste affichée, « en cours », avec une marge de 1,5 ¢ qui interdit « juste » et la validation.
// v64 (PROMOTION) : une lecture certifiée est elle-même la valeur affichée et le « sûr » : le traqueur, qui ne voit pas le biais de modulation de phase des
// fenêtres courtes, n'est plus le goulot du temps de pose.
//
// Le calcul est fait par un Worker dédié (v66, cert-calcul.js / cert-worker.js) ; sans lui, il est réparti sur les images du moteur (générateur : `CERT.PAS_PAR_IMAGE` itérations par image de 85 ms).
import { lireBesselGen, lireSeuleGen, NLS_LLR_SUR, C_CENTS, NP0 } from './nls-bessel.js';
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
  JOBS_MAX: 1,               // v69 (I2, PB12 CERTIFICAT.md § 0C) : 1 ajustement de front (2 en v64-v68), avec ETIQ_COH_C 3 qui ferme le -21,5 ¢ de la v68 ; ancien commentaire :               // ajustements menés de front (v64 : 2). v68 : 1 testé en machine rapide (plan 2^3 H4, CERTIFICAT.md § 0B) et REFUSÉ : en changeant l'ordre des fenêtres essayées, il a fait poser un « sûr » à -21,5 ¢ (mauvaise étiquette, AM de 0,5 : hypercube4 plan 91 graine 32, SYNTH=h6) que le réglage de la v67 évite par hasard ; réservé aux machines lentes (LENT_JOBS_MAX)
  DECALAGE_MIN_S: 0.5,       // C9 : écart minimal des milieux des deux fenêtres confirmées
  RAFRAICHIR_S: 0.8,         // un certificat est rafraîchi par un nouvel ajustement (point de départ chaud) quand il a cet âge (v64)
  CERT_AGE_MAX_S: 4,         // un certificat qui n'a pas été rafraîchi depuis ce temps tombe
  CERT_AGE_MAX3_S: 2,        // idem pour trois anches (le traqueur n'y sert pas de témoin d'un changement de note)
  PROMOTION: true,          // v64 : la seconde lecture devient la valeur affichée quand elle est certifiée (le « sûr » ne dépend plus de l'état du traqueur)
  NDEPARTS: 2,              // v69 (I2) : 2 points de départ (5 en v64-v68). Ancien commentaire :               // ajustement : nombre de points de départ (v68 : 2 testé en machine rapide et refusé, comme JOBS_MAX 1 ; réservé aux machines lentes : LENT_NDEPARTS)
  NLIBRE: 2,                 // ajustement : nombre d'hypothèses d'étiquette qui reçoivent une raie étrangère libre (la vraie paire doit pouvoir s'en servir comme la fausse : avec 1, la fausse seule la recevait et gagnait)
  FEN_F0_S: 350,             // v64 : la fenêtre dure au moins FEN_F0_S / f (s) : en ¢, l'erreur d'une fréquence est en 1/f (banc trio : 0,05 ¢ à 1 s au-dessus de 500 Hz, 0,2 ¢ à 2,5 s vers 80 Hz)
  NB_MIN: 1,                 // v64 : la fenêtre couvre au moins ce nombre de battements (en plus de K·Ω·T ≥ KOT_MIN)
  CHAUD_DT_MAX_S: 1.2,       // un ajustement part d'un autre (à chaud) si le centre de la fenêtre a bougé de moins que cela
  CHAUD_C9: false,           // la seconde fenêtre de C9 part de la solution de la première (rapide, mais la même étiquette)
  CONFIRME_MODE: 1,          // C9 : 0 deux fenêtres décalées (DECALAGE_MIN_S) ; 1 les deux moitiés de la même fenêtre quand elles se résolvent (repli sur 0) ; 2 les deux
  CONFIRME_MOITIE_C: 0.4,    // C9 par moitiés : écart de chaque moitié à l'ajustement entier
  KOT_MOITIE: 1.0,           // C9 par moitiés : K·Ω·T/2 minimal pour que chaque moitié soit lue
  KMAX: 4,                   // ajustement : nombre de partiels
  ITER: 15,                  // ajustement : itérations de l'étape finale
  MS_LENT: 500,              // v68 (H4) : si un ajustement À FROID dure en moyenne plus que cela (ms, mesuré dans le Worker : PC de l'audit 340 ms, portable 2 fois plus lent 680 ms, téléphone 4 fois plus lent 1 400 ms), le calcul passe en mode léger (LENT_NDEPARTS, LENT_ITER, LENT_JOBS_MAX) : H6 réel ×4 1 -> 10 notes posées sur 27, ×2 7 -> 11, sans rien changer à une machine rapide (16/27)
  LENT_ITER: 8,              // v68 (H4) : itérations de l'étape finale d'une machine lente (MS_LENT)
  LENT_NDEPARTS: 2,
  LENT_JOBS_MAX: 1,          // v68 (H4) : ajustements de front sur une machine lente (MS_LENT) ; le cœur du Worker revient aux sentinelles et le premier ajustement finit deux fois plus tôt
  COUT_PAR_IMAGE: 200,      // bancs (v64) : travail par image en milliers de partiels-échantillons évalués (déterministe) ; null : PAS_PAR_IMAGE
  PAS_PAR_IMAGE: 20,         // itérations de Levenberg-Marquardt par image (bancs et tests : calcul déterministe)
  MS_PAR_IMAGE: null,        // si donné (repli de l'application sans Worker dédié : 40 ms, réglé par adapterBudget ; les bancs : COUT_PAR_IMAGE), c'est le temps qui borne le travail de chaque image, pas le nombre de pas
  CONFIRME_C: 0.3,           // C9 : deux ajustements successifs (fenêtres décalées d'au moins 0,5 s) d'accord à ce point près
  LLR_MIN: 100,              // C4
  IDENT3_ECART: 0.05,        // v66 (F10) : trois anches dont les deux écarts Δ− et Δ+ sont égaux à cette part près ET dont moins de IDENT3_KU_MAX partiels sont nets : indiscernable d'UNE anche modulée (vibrato, tirage), jamais « sûr »
  IDENT3_KU_MAX: 2,
  ABSENTE_DB: 35,            // v66 (F10) : une des trois anches à plus de ce nombre de dB sous la plus forte : elle ne sonne pas (registre fermé), le texte le dit
  KOT_MIN: 1.5,              // C3
  R_MAX: 0.05,               // C2 : résidu relatif du modèle (juste sans raie étrangère : 0,01 ; avec : jusqu'à 0,08 ; deux anches manquées : 0,085 et plus)
  PLANCHER_MAX_DB: -28,      // C2 : plancher hors modèle, partiels 1 et 2
  BETA_MAX: 0.45,           // C2 : indice de modulation de phase. Au-delà de 0,4 (audit § 1.3) la porteuse n'est plus la raie dominante aux partiels hauts (J0(kβ) < J1(kβ)) et le modèle de Bessel ne tient plus : La5 du 14/10 (β 0,46 à 1,1, raies non proportionnelles au rang) lue à +0,6 ¢ avec une borne à 0,6. La borne de l'ajustement est 0,7, où se collent les faux modèles
  M_MAX: 0.3,                // C2 (v64) : indice de modulation d'amplitude ; collé à sa borne (0,45) il est la marque d'un faux modèle où des raies latérales jouent l'anche faible (banc : trois lectures fausses de 16 ¢ sur trois, 0 sur 200 fenêtres justes)
  LLR_AFFECT_MIN: 150,       // C4 (v64) : rapport de vraisemblance minimal de l'échange de rôle entre une anche et la raie étrangère adoptée
  COUPLAGE_MIN: 0.03,        // C4 (v64) : en dessous de cet indice (phase ou amplitude) les anches ne se tirent pas assez pour qu'on lise leur rôle contre une raie étrangère
  LIBRE_VS_FAIBLE_DB: 12,    // une raie étrangère plus faible que l'anche la plus faible de plus que cela (dB) ne compte pas dans l'échange de rôle
  MARGE_ETIQ_DB: 20,         // C4 (v64) : la raie de l'anche faible n'est pas plus de ce nombre de dB sous la raie latérale que l'anche forte met au même endroit (banc : -35 dB = faux modèle ; -10 dB et moins = lectures justes)
  LAG_MAX_C: 0.3,            // v64 : |dérive| · (âge du milieu de la fenêtre) au plus ce nombre de ¢ : une valeur plus vieille que cela cesse d'être « sûre » (lecture à +0,52 ¢ d'une note qui dérive à 0,22 ¢/s, 2,4 s d'âge)
  CONTREDIT_C: 0.2,          // v66 (F1) : une lecture complète qui s'écarte du certificat de plus que max(ce seuil, CONTREDIT_SIGMA σ) + la dérive l'invalide, même si elle est elle-même refusée (0 : éteint)
  CONTREDIT_SIGMA: 3,
  CONTREDIT_DERIVE_MAX_C: 1,
  SENTINELLE: true,          // v66 (F1) : tant qu'un certificat tient, une lecture chaude courte (SENT_FEN_S) toutes les SENT_PERIODE_S vérifie que l'anche n'a pas bougé (un saut de hauteur tombe en ~0,5 s au lieu de 1,5 s)
  SENT_FEN_S: 0.6,
  SENT_PERIODE_S: 0.1,       // v68 (PB12 H2b, CERTIFICAT.md § 0B) : 0,10 s (0,15 en v67)
  SENT_PRIO: true,           // v68 (H2) : le calcul en ligne (bancs, repli sans Worker) fait passer la sentinelle AVANT les ajustements principaux, comme le fait `FileCalcul` dans le Worker : sinon elle attendait son tour (0,34 à 0,5 s au lieu de 0,1 s) et le retard après un saut montait à 0,6 s (audit n° 4)
  SENT_FEN_BAT: 0.7,           // v68 (essai) : la fenêtre de la sentinelle contient au moins ce nombre de battements (0 : éteint) : à Ω 0,64 Hz, 0,6 s ne contient pas un battement, σ de 0,5 à 1 ¢, la sentinelle ne voit un saut de 2,5 ¢ qu'après 0,5 à 0,8 s
  SENT_FEN_BAT_MAX: 1.5,
  SENT_KMIN: 1,              // v69 (I3) : rang du premier partiel lu par la sentinelle quand le battement est lent (Ω < SENT_KMIN_OMEGA) : aux rangs hauts les deux anches sont séparées de k·Ω et 0,6 s les résout ; 1 : tous les partiels (v68). Plan 2^2 SENT_KMIN × SENT_FEN_BAT sur D4 (CERTIFICAT.md § 0C)
  SENT_KMIN_OMEGA: 1.0,      // v69 (I3) : Hz
  SENT_ITER: 6,           // v68 : itérations de la sentinelle (null : ITER) ; son coût fait son retard dans le Worker (un téléphone ×4 : 0,5 s)
  SENT_KMAX: null,           // v68 : partiels de la sentinelle (null : KMAX) ; la sentinelle ne pose rien, elle ne peut qu'invalider
  SENT_SIGMA: 3,             // tolérance de la sentinelle : max(CONTREDIT_C, SENT_SIGMA σ) (fenêtre courte : plus de fausses alarmes à 3 σ). v68 : 2 testé (PB12 H2b) et refusé : la part du temps où le chiffre est certifié passe de 7 % à 3-5 % (fausses alarmes)
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
  MODELE: 'struct',             // v67 (G1) : 'am' = le modèle d'anches corrigé d'après le H6 (AM par partiel dans les amplitudes linéaires, phase de modulation par anche, K_utile par résidu de partiel) ; null = le modèle v66
  R_MAX_AM: 0.01,            // v67 (G1), modèle 'am' : C2 juge sur le résidu r (l'écart de modèle y est redevenu un bruit : 1e-4 à 1e-3 sur le H6 au lieu de 2e-3 à 3e-1) et non sur β̂ et m̂
  MARGE_ETIQ_ST_DB: 20,     // v67 (G1), modèle 'struct' : la raie de l'anche faible n'est pas plus de ce nombre de dB sous la raie latérale que la forte met au même endroit. 20 dB (v64) valait pour un modèle exact ; le modèle réel se trompe de 10 à 40 % sur ses bandes latérales (H6), la faible n'est lisible que si elle les dépasse de cette marge d'erreur
  RK_MAX_AM: 0.6,            // v67 (G1), modèle 'struct' : K_utile : un partiel dont le résidu relatif dépasse cette valeur n'est pas lu (les rangs >= 3 ou 5 quand la modulation n'est pas sinusoïdale)
  M_ST_MARGE_DB: 0,          // v67 (G1), modèle 'struct' : l'anche faible doit être au moins aussi forte que la bande latérale de l'AM de la forte (20 log10(m/2), dB sous la forte), moins cette marge : en dessous, une anche faible et une bande latérale se confondent (D3 plan 5 : 43 ¢ de faux ; planA_valid plan 5 : 48 ¢)
  M_ST_MAX: 0.6,             // v67 (G1), modèle 'struct' : AM réelle d'un partiel au-delà de laquelle la porteuse et ses deux bandes latérales imitent deux anches (étiquette décalée d'un battement) ; H6 : 0,13 à 0,59
  PRIOR_FIRST: true,         // v67 (P2) : démarrage à chaud depuis le traqueur : quand les deux anches sont suivies, leur paire passe en tête des départs de la première lecture (avec NDEPARTS petit, c'est ce qui fait gagner du temps sur un portable)
  ENTIER_NB: 2,              // v67 (G2) : battement lent (OMEGA_MIN <= Ω < OMEGA_SUR_MIN) lu sur un nombre ENTIER de battements, au moins ce nombre : tout ce que le couplage fait au son (fuite de la voisine, tirage, modulation de timbre) est périodique au battement, la moyenne sur des périodes entières l'annule quelle que soit sa forme. 0 : éteint (seuil OMEGA_SUR_MIN seul)
  ENTIER_TOL: 0.12,          // v67 (G2) : écart toléré de la fenêtre à un nombre entier de battements (|T·Ω − entier|)
  FEN_ENTIER_MAX_S: 6.5,     // v67 (G2) : fenêtre lue au plus (deux battements à 0,4 Hz : 5 s)
  PRESSION_REPLI_C_DB: 0.2,   // v67 (G5) : pente hauteur / niveau de repli (¢ par dB) quand celle de la note n'est pas significative (loi : la fréquence baisse quand la pression monte, -0,15 à -0,25 ¢/dB, AUDIT-REPETABILITE.md ; sur le H6 la pente de la note est de signe variable)
  PRESSION_T_MIN: 2.5,        // v67 (G5) : |t| de la pente propre de la note au-dessus duquel elle remplace la pente de repli
  PRESSION_MIN_C: 0.1,        // v67 (G5) : en dessous, l'incertitude de pression n'est pas affichée (sobriété)
  ETIQ_COH_C: 3,             // v68 (mécanisme trouvé par les passes finales, CERTIFICAT.md § 0B) : une lecture n'est certifiable que si aucun ajustement plausible de la note (r <= 0,05, LLR >= 25) des ETIQ_COH_S dernières secondes ne s'en écarte de plus de ce nombre de ¢ (0 : éteint). Une note dont la fenêtre donne tantôt la bonne étiquette (erreur 0), tantôt l'anche faible lue une bande latérale plus bas (-21,5 ¢, hypercube4 plan 91 graine 32) est ambiguë : refus `etiquette`
  ETIQ_COH_S: 4,
  RIVAL_MOITIE: true,        // v68 (H9) : un battement ajusté dont la moitié est sous OMEGA_MIN est confronté à son rival Ω/2 (même modèle) ; pas pire de LLR_MIN σ² : refusé `accordees` (Δ = 0,3 Hz lu à 0,6 Hz sur Linux / Node 22, test F10)
  BATTEMENT_PRINCIPAL: false, // v71 (lot C3) : le battement est la grandeur principale d'une musette : accord obligatoire avec l'enveloppe sûre, écart brut affiché seulement quand il est lu et corroboré (battement.js, BP_*), ajustements de moins d'un battement écartés (BP_NB_FIT) ; éteint : la v70 à l'identique
  BP_NB_FIT: 1,              // v71 (lot C3), avec BATTEMENT_PRINCIPAL : un ajustement n'entre dans le battement affiché que si sa fenêtre contient au moins ce nombre de battements (T · Ω̂) : en dessous deux raies ne se séparent pas et Ω̂ est celui d'un rival (mesuré sur le H6 : points de 0,8 s à 54 et 58 bat/min pour 72 et 33)
  ENV_ACCORD: 0.25,          // v68 (H9) : un Ω d'ajustement n'entre dans le battement affiché que s'il est d'accord à cette part près avec le battement de l'enveloppe, quand celle-ci en a un (c'est la définition du luthier)
  PRESENT: false,            // v68 (H2d) : la fréquence promue est ramenée de la fin de la fenêtre lue (le milieu + T/2) quand la dérive est significative (|t| >= PRESSION_T_MIN) et <= DERIVE_MAX ; éteint : la vérité des bancs est la moyenne de la fenêtre (voir CERTIFICAT.md § 0B)
  NB_MIN_POST: 1,            // v68 (H1) : APRÈS l'ajustement, la fenêtre contient au moins ce nombre de battements MESURÉS (T · Ω̂) ; la fenêtre est planifiée sur l'Ω du traqueur, qui peut le surestimer (B plan 33 : 0,7 battement mesuré, posé faux de 0,6 ¢). 0 : éteint
  DERIVE_FIT_SEUIL: 1.2,     // v68 (H1) : variante retenue : la dérive de l'ajustement ne compte que si elle dépasse ce seuil (¢/s ; 0 : éteint ; p95 des ajustements du H6 qui passent : 1,08 ; B plan 33 : 1,35)
  KC_PROPRE: false,          // v69 (I1) : le gagnant de la comparaison d'étiquettes est réajusté sur ses propres partiels (nls-bessel.js, kcPropre), l'étiquette restant jugée sur les partiels communs
  KC_MAX: false,             // v69 (I1, diagnostic des graves, CERTIFICAT.md § 0C) : les hypothèses d'étiquette sont comparées sur les partiels de la plus riche (nls-bessel.js, kcMax) au lieu de ceux que TOUTES savent décrire (v67)
  LIBRE_DOUBLON: true,       // v70 (J1, audit n° 6, RETENU : plan 2^2, CERTIFICAT.md § 0D) : une raie étrangère ajustée tout près d'une anche (DOUBLON_DIST/(K·T)) ou de sa raie latérale, et à moins de DOUBLON_DB dB sous elle, est un doublon de l'anche : non adoptée (nls-bessel.js)
  DOUBLON_DIST: 0.5,         // v70 (retenu) : distance (en 1/(K·T)) sous laquelle une raie libre est un doublon
  DOUBLON_DB: 6,             // v70 (retenu) : niveau (dB sous l'anche la plus proche) sous lequel la règle s'applique ; 99 = sans condition de niveau
  KU_SUR_MIN_GRAVE: 3,       // v68 (H3, RETENU) : sous F0_GRAVE_HZ, une lecture sûre exige au moins ce nombre de partiels décrits par le modèle (lent100 plan 82 : raie étrangère non résolue à 103 Hz avec 2 partiels, faux de 0,53 ¢). Plan 2^3 (CERTIFICAT.md § 0B) : H6 réel 16/27 inchangé, lent100 14 -> 11 posées et 1 -> 0 faux ; GLOBAL (tous les registres), 3 coûte 38 notes sur 364 (plan 2^(5-2) de l'audit n° 4)
  F0_GRAVE_HZ: 120,          // v69 (I1) : 120 au lieu de 150 (plan 2^2 x 4 graines neuves, CERTIFICAT.md § 0C) : graves posées 12 -> 29 sur 832, 0 faux, lent100 plan 82 jamais sûr
  KU_LIBRE_GRAVE: 0,         // v68 (H3, variante ciblée, mesurée équivalente et non retenue) : sous F0_GRAVE_HZ, une raie étrangère adoptée par le modèle exige au moins ce nombre de partiels décrits (H6 réel 16/27, lent100 14 -> 11 posées et 1 -> 0 faux, comme KU_SUR_MIN_GRAVE)
  // v71 (lot C2, audit « superposition » du 19/10/2026) : l'anche SEULE. Une paire dont une voix est absente depuis SEULE_ABSENTE_S se certifie comme UNE anche (nls-bessel.js, lireSeuleGen) :
  // le luthier qui bloque une anche au doigt pour lire l'autre avait un chiffre jamais certifié (refus `niveau`, 0 image « sûr » sur 10 passes seules, même 10 s).
  CERT_SEULE: true,          // allumé (lot C2, v71) : critère tenu (anche seule certifiée en 4 s au plus sur A4R, MGH-AR, BASS-A0R ; 0 « sûr » faux ; tableau de bord de CERTIFICAT.md inchangé sur lhs20 x 2 graines)
  SEULE_ABSENTE_S: 2,        // une voix absente (non suivie) depuis ce temps : la paire est une anche seule
  SEULE_PRE_S: 0.8,          // dès ce temps d'absence la lecture à une anche est calculée d'avance (affichée à SEULE_ABSENTE_S)
  SEULE_PRESENTE_S: 0.5,     // une voix est présente si elle est suivie sans interruption depuis ce temps
  SEULE_FEN_F0_S: 200,       // la fenêtre dure au moins SEULE_FEN_F0_S / f (s) : une anche seule n'a pas à séparer deux raies, seulement à lire sa hauteur (FEN_F0_S : 350 pour une paire)
  SEULE_FEN_MAX_S: 1.5,
  SEULE_KMAX: 6,             // partiels lus (une seule anche : pas d'étiquette à départager, plus de partiels pour une lecture plus juste)
  SEULE_EK_C: 0.7,           // écart type a priori du désaccord d'un partiel (¢ de sa fréquence) : une anche réelle n'est pas exactement harmonique
  SEULE_R_MAX: 0.005,        // résidu relatif d'UNE anche : une seconde raie cachée (unisson décalé 1,2 Hz) laisse 2e-2 à -20 dB, 5e-2 à -12 dB, 0,2 à -6 dB, 0,3 à 0 dB ; les échantillons réels A4R, MGH-AR, BASS-A0R : 4e-4 à 4e-3
  SEULE_BORNE_C: 0.3,        // borne du biais d'une seconde raie cachée : 1731 · √r / (π T f) ¢ (la phase d'une raie à −x dB oscille de ρ = √r rad : la moyenne de la fréquence sur T en est écartée de ρ/(π T) Hz au plus)
  SEULE_KU_MIN: 2,           // partiels décrits (S/B >= 20 dB) au moins ; sous F0_GRAVE_HZ : KU_SUR_MIN_GRAVE
  SEULE_MOITIE_S: 0.6,       // C9 par moitiés : durée minimale de chaque moitié
  AM_RHO_K: 0,               // v72 (J1) REFUSÉE PAR PLAN, éteinte : K 2 et 4 ne mordent jamais ; K 1,5 ferme le faux mais coûte 4,1 % de posées (h6 -4,5, LARGE -4,5, gen160 -2,4), K 1 coûte 12 % ; le rapport m_1/ρ des lectures justes (1,5 à 2,5) recouvre celui du faux (1,77) en synthèse. Audit n° 7 : « sûr » faux de 27,7 ¢, lhs64_valid LARGE plan 2 graine 71, CERTIFICAT.md § 0G), garde physique `ETIQ_AM` : dans une paire de rapport d'amplitude ρ (faible / forte, de l'hypothèse), l'enveloppe de la forte n'est modulée par le battement qu'à l'indice m ≈ ρ ; une hypothèse (modèle 'struct') dont l'indice d'AM au rang 1 dépasse AM_RHO_K × ρ fabrique de l'énergie (une anche et sa bande latérale prises pour deux anches) : refus `etiquette`. 0 : éteint
  AM_RHO_PORTEE: 1,          // v72 (J1), avec AM_RHO_K : 1 = la garde refuse l'étiquette seulement ; 2 = en plus, l'ajustement inadmissible n'est adopté nulle part (ni témoin de cohérence d'étiquette, ni candidat, ni Ω promu)
  OMEGA_MAX: 60,             // Hz : au-delà, hors domaine (anches « presque deux notes » ; 25 en v63 ; 50 ¢ à A6 font 51 Hz)
};

// Raisons de refus : clés de langue (ui/langues) et ordre de gravité (la plus parlante d'abord).
// v72 (J1) : l'hypothèse d'étiquette d'un ajustement de paire (modèle 'struct') est-elle inadmissible ? Indice d'AM au rang 1 (m_1, premier paramètre d'AM de la solution) contre
// AM_RHO_K × ρ, ρ = rapport d'amplitude faible / forte de l'hypothèse (niveauDb). Rend le couple { m1, rho } pour le diagnostic.
export function amHypothese(nls) {
  if (!nls?.ok || nls.modele !== 'struct' || !nls.sol || nls.niveauDb == null || nls.sol.length <= NP0) return null;
  return { m1: nls.sol[NP0], rho: 10 ** (nls.niveauDb / 20) };
}
export function amInadmissible(nls, opts) {
  if (!(opts.AM_RHO_K > 0)) return false;
  const h = amHypothese(nls);
  return !!h && h.m1 > opts.AM_RHO_K * h.rho;
}

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
  if (nls.seule) return jugerSeule(nls, moteur, { calib, zeros, opts, derive, sauterStabilite });
  const trio = Array.isArray(nls.Om);
  const f = nls.f.map((v) => v * calib);
  const cents = (a, b) => 1200 * Math.log2(a / b);
  detail.accord = Math.max(...f.map((v, j) => Math.abs(cents(moteur.f[j], v))));
  const omMin = trio ? Math.min(...nls.Om) : nls.Om, omMax = trio ? Math.max(...nls.Om) : nls.Om;
  detail.kot = (trio && Number.isFinite(nls.Ku) ? nls.Ku : nls.K) * omMin * nls.T;       // v66 (F10) : K_utile (partiels nets) pour trois anches
  detail.plancher = Math.max(...nls.plancherDb.slice(0, 2).map((v) => (v == null || Number.isNaN(v) ? 999 : v)));
  if (omMax > opts.OMEGA_MAX) raisons.push('ecartees');
  else if (omMin < opts.OMEGA_MIN) raisons.push('accordees');
  else if (omMin < opts.OMEGA_SUR_MIN) {
    // v67 (G2) : sous OMEGA_SUR_MIN la hauteur n'est sûre que si la fenêtre lue est un nombre entier (>= ENTIER_NB) de battements
    const nbB = nls.T * omMin;
    const entier = !trio && opts.ENTIER_NB > 0 && nbB >= opts.ENTIER_NB - 0.1 && Math.abs(nbB - Math.round(nbB)) <= opts.ENTIER_TOL;
    detail.battementsLus = nbB;
    if (!entier) raisons.push('lent');
  }
  const faible = trio ? Math.min(...nls.niveauxDb) : nls.niveauDb;        // niveau de l'anche la plus faible sous la plus forte (dB, négatif)
  if (trio && faible != null && faible < -opts.ABSENTE_DB) raisons.push('absente');
  else if (faible != null && faible < -opts.NIVEAU_MIN_DB) raisons.push('niveau');
  if (trio && Math.abs(nls.Om[1] - nls.Om[0]) <= opts.IDENT3_ECART * 0.5 * (nls.Om[0] + nls.Om[1]) && (nls.Ku ?? 4) <= opts.IDENT3_KU_MAX) raisons.push('ident3');
  const am = nls.modele === 'struct' || nls.modele === 'libre';
  const ms = am ? [] : [].concat(nls.m, nls.m2 ?? []).filter((v) => Number.isFinite(v));
  const bMax = Math.max(...nls.b.map(Math.abs)), mMax = Math.max(0, ...ms.map(Math.abs));
  detail.beta = bMax; detail.m = mMax;
  if (am) {
    // v67 (G1) : le modèle corrigé ne juge plus sur β̂ et m̂ (qui n'ont plus de sens physique dès que la modulation de timbre est libre) mais sur le résidu r, le plancher entre les raies
    // et la validité du peigne de Bessel (K · β̂)
    const x = nls.K * bMax;
    detail.x = x;
    detail.m = nls.modele === 'struct' ? nls.m : 0;
    if (!(nls.r <= opts.R_MAX_AM) || !(detail.plancher <= opts.PLANCHER_MAX_DB) || (nls.modele === 'struct' && (nls.m > opts.M_ST_MAX || (nls.niveauDb != null && nls.niveauDb < 20 * Math.log10(Math.max(nls.m, 1e-3) / 2) - opts.M_ST_MARGE_DB)))) {
      raisons.push('peigne');
      detail.causePeigne = !(detail.plancher <= opts.PLANCHER_MAX_DB) ? 'micro' : nls.libre ? 'etrangere' : 'micro';
    }
  } else {
    if (!(nls.r <= opts.R_MAX) || !(detail.plancher <= opts.PLANCHER_MAX_DB) || bMax > opts.BETA_MAX || mMax > opts.M_MAX) {
      raisons.push('peigne');
      // la cause, pour que l'écran dise le geste (F6) : anches presque accrochées, micro traité, autre anche qui sonne
      detail.causePeigne = bMax > opts.BETA_MAX || mMax > opts.M_MAX ? 'accrochees' : !(detail.plancher <= opts.PLANCHER_MAX_DB) ? 'micro' : nls.libre ? 'etrangere' : 'micro';
    }
  }
  detail.sigma = Math.max(...(nls.sigmaC ?? [0]).map((x) => (Number.isFinite(x) ? x : 99)));
  if (!(detail.kot >= opts.KOT_MIN)) raisons.push('resolution');
  // Rôle des raies : quand une raie étrangère notable (plus haute que −LIBRE_SIG_DB) est adoptée, l'échange de rôle avec chaque anche doit être nettement pire (trois raies
  // pures d'égale force : indécidable, rapport 37 à 120 ; les lectures justes : 360 à 10 000)
  // Sans aucun couplage ajusté (|β| et |m| presque nuls), rien dans le son ne distingue une anche d'une raie étrangère : seul le rapport de vraisemblance de l'échange de rôle
  // reste, et il est trop bas quand les trois raies se valent.
  const couplage = Math.max(0, ...(am ? [].concat(nls.b) : [].concat(nls.b, nls.m, nls.m2 ?? [])).filter((v) => Number.isFinite(v)).map(Math.abs));
  // La raie étrangère ne compte que si elle est du même ordre que l'anche la plus faible (LIBRE_VS_FAIBLE_DB) ; sinon les deux anches sont les deux raies les plus fortes, sans équivoque.
  const affect = nls.libre && faible != null && nls.libre.dB > faible - opts.LIBRE_VS_FAIBLE_DB && (!(nls.llrAffectation >= opts.LLR_AFFECT_MIN) || couplage < opts.COUPLAGE_MIN);
  if (!trio && amInadmissible(nls, opts)) raisons.push('etiquette');
  if (!(nls.llr >= opts.LLR_MIN) || affect || !(trio || nls.modele === 'libre' || (nls.margeEtiquette ?? 0) >= -(nls.modele === 'struct' ? opts.MARGE_ETIQ_ST_DB : opts.MARGE_ETIQ_DB))) raisons.push('etiquette');      // am : les bandes latérales sont libres, la « marge » contre la raie latérale n'a plus de sens ; restent le LLR des deux étiquettes et l'échange de rôle
  // v68 (H1) : après l'ajustement, la fenêtre doit contenir NB_MIN_POST battements mesurés (la fenêtre est planifiée sur l'Ω du traqueur) ; une garde à coût nul (plan 2^(5-2) de l'audit n° 4)
  if (!trio && (opts.NB_MIN_POST ?? 0) > 0 && nls.T * omMin < opts.NB_MIN_POST && !raisons.includes('lent') && !raisons.includes('accordees') && !raisons.includes('ecartees')) raisons.push('lent');
  // v68 (H9) : le rival Ω/2 d'un battement lent (ajusté dans nls-bessel.js) : pas pire de LLR_MIN σ² -> le battement est peut-être le double du vrai
  if (!trio && Number.isFinite(nls.llrOmega2) && nls.llrOmega2 < opts.LLR_MIN && !raisons.includes('accordees')) raisons.push('accordees');
  // v68 (H3) : au grave, trois partiels décrits au moins (KU_SUR_MIN_GRAVE)  (v69 : la variante ciblée KU_LIBRE_GRAVE reste ; la variante à toute hauteur KU_LIBRE_MIN, qui coûtait 5 à 9 notes du H6, est retirée)
  if (!trio && opts.KU_LIBRE_GRAVE > 0 && nls.libre && f[0] < opts.F0_GRAVE_HZ && (nls.K ?? 4) < opts.KU_LIBRE_GRAVE) raisons.push('resolution');
  if (!trio && opts.KU_SUR_MIN_GRAVE > 0 && f[0] < opts.F0_GRAVE_HZ && (nls.K ?? 4) < opts.KU_SUR_MIN_GRAVE) raisons.push('resolution');
  const dBrute = derive ?? nls.derive;
  const dFit = Math.abs(nls.derive ?? 0);
  const d = derive != null && (opts.DERIVE_FIT_SEUIL > 0 && dFit > opts.DERIVE_FIT_SEUIL) ? Math.max(Math.abs(derive), dFit) : dBrute;
  if (!sauterStabilite && (!(Math.abs(d) <= opts.DERIVE_MAX || Math.abs(d) * nls.T <= (opts.EXC_MAX ?? 0)) || !(nls.agit <= opts.AGIT_MAX))) raisons.push('stabilite');
  return { ok: raisons.length === 0, raisons, detail };
}

// Jugement d'une lecture à UNE anche (v71, CERT_SEULE). Mêmes critères que juger quand ils ont un sens sans battement : prise saine (C1), peigne sain (C2 : le résidu du modèle à une
// anche ne montre aucune seconde raie : c'est ce qui sépare l'anche seule de l'unisson mal suivi), partiels décrits (C3), stabilité (C6). Pas d'étiquette (C4), pas de battement.
// La borne du biais d'une seconde raie qui resterait cachée (detail.borne, ¢) s'ajoute à l'écart type annoncé (detail.sigma).
export function jugerSeule(nls, moteur, { calib = 1, zeros = false, opts = CERT, derive = null, sauterStabilite = false } = {}) {
  const raisons = [];
  const detail = {};
  if (zeros) raisons.push('trous');
  const f = nls.f[0] * calib;
  detail.accord = Math.abs(1200 * Math.log2(moteur.f[0] / f));
  detail.kot = nls.Ku; detail.beta = 0; detail.m = 0;
  detail.plancher = Math.max(...nls.plancherDb.slice(0, 2).map((v) => (v == null || Number.isNaN(v) ? 999 : v)));
  detail.borne = C_CENTS * Math.sqrt(Math.max(0, nls.r)) / (Math.PI * nls.T * f);
  detail.sigma = Number.isFinite(nls.sigmaC?.[0]) ? nls.sigmaC[0] : 99;       // statistique et borne d'une seconde raie cachée (nls-bessel.js)
  if (!(nls.r <= opts.SEULE_R_MAX) || !(detail.borne <= opts.SEULE_BORNE_C) || !(detail.plancher <= opts.PLANCHER_MAX_DB)) { raisons.push('peigne'); detail.causePeigne = 'etrangere'; }
  if (!(nls.Ku >= opts.SEULE_KU_MIN) || (opts.KU_SUR_MIN_GRAVE > 0 && f < opts.F0_GRAVE_HZ && nls.Ku < opts.KU_SUR_MIN_GRAVE)) raisons.push('resolution');
  const dBrute = derive ?? nls.derive;
  const dFit = Math.abs(nls.derive ?? 0);
  const d = derive != null && (opts.DERIVE_FIT_SEUIL > 0 && dFit > opts.DERIVE_FIT_SEUIL) ? Math.max(Math.abs(derive), dFit) : dBrute;
  if (!sauterStabilite && (!(Math.abs(d) <= opts.DERIVE_MAX || Math.abs(d) * nls.T <= (opts.EXC_MAX ?? 0)) || !(nls.agit <= opts.AGIT_MAX))) raisons.push('stabilite');
  return { ok: raisons.length === 0, raisons, detail };
}

// Ajustement d'une fenêtre : l'ajustement entier ; s'il passe C1 à C8 et que les moitiés se résolvent, les deux moitiés (point de départ chaud : la lecture
// entière) pour C9 par moitiés. Générateur : un `yield` par pas, comme lireBesselGen. n : 2 ou 3 anches.
export function* ajusterFenetre(n, x, sr, fc, optsFit, opts, calib, moteur) {
  const lire = n === 3 ? lireTrioGen : n === 1 ? lireSeuleGen : lireBesselGen;
  const main = yield* lire(x, 0, x.length, sr, fc, optsFit);
  if (main.ok && opts.CONFIRME_MODE >= 1) {
    const v = juger(main, moteur, { calib, zeros: false, opts, sauterStabilite: true });
    const omMin = n === 3 ? Math.min(...main.Om) : n === 1 ? 0 : main.Om;
    if (v.ok && (n === 1 ? main.T / 2 >= opts.SEULE_MOITIE_S : main.K * omMin * main.T / 2 >= opts.KOT_MOITIE)) {
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
  const lire = spec.n === 3 ? lireTrioGen : spec.n === 1 ? lireSeuleGen : lireBesselGen;
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
  certifierPaire(g, tNow, envHz = null) {
    const c = this.cohEtat?.get(`${g.key}:${g.center}`);
    this.certifierGroupe(g, tNow, 2, c?.t0 ?? null, envHz);
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

  // v71 (CERT_SEULE) : la paire dont toutes les voix sauf une sont absentes depuis SEULE_ABSENTE_S est UNE anche. Une voix « présente » est suivie sans interruption depuis SEULE_PRESENTE_S
  // (une anche bloquée au doigt est parfois prise un instant pour un partiel : 1 à 3 images sur 100, BASS-A0R seule). Rend { v, t0, confirmee } ou null : `confirmee` à partir de SEULE_ABSENTE_S ;
  // à partir de SEULE_PRE_S (avant) la lecture à une anche est déjà calculée (`attente`) mais pas affichée, pour qu'elle existe dès la confirmation (un échantillon de 2,9 s ne tient pas plus).
  voixSeule(g, tNow, opts) {
    const ok = (v) => v?.tracked && !v.held && !v.coarse && !v.merged && Number.isFinite(v.fMeas);
    this.seuleEtat ??= new Map();
    const cle = `${g.key}:${g.center}`;
    let se = this.seuleEtat.get(cle);
    if (!se || tNow - se.vu > 1.0) { se = { vu: tNow, t0: tNow, abs: new Map(), run: new Map() }; this.seuleEtat.set(cle, se); }
    se.vu = tNow;
    const vs = g.voices;
    const presente = (i) => se.run.has(i) && tNow - se.run.get(i) >= opts.SEULE_PRESENTE_S;
    vs.forEach((v, i) => {
      if (ok(v)) { if (!se.run.has(i)) se.run.set(i, tNow); } else se.run.delete(i);
      if (presente(i)) se.abs.delete(i); else if (!se.abs.has(i)) se.abs.set(i, tNow);
    });
    const j = vs.findIndex((v, i) => ok(v) && vs.every((w, k) => k === i || (se.abs.has(k) && tNow - se.abs.get(k) >= opts.SEULE_PRE_S)));
    if (j < 0) return null;
    const absence = Math.min(...vs.map((w, k) => (k === j ? Infinity : tNow - se.abs.get(k))));
    return { v: vs[j], t0: se.t0, confirmee: absence >= opts.SEULE_ABSENTE_S };
  },

  // Pose `refus` / `cert` sur les voix et, si la lecture n'est pas certifiée, ramène `etatAnche` à « en cours » avec une marge. v64 (`PROMOTION`) :
  // une seconde lecture certifiée devient la valeur affichée et le « sûr » (le traqueur peut être encore « en cours » ou « au centre »).
  certifierGroupe(g, tNow, n, t0Note, envHz = null) {
    const opts = { ...CERT, ...(this.cfg.certificat ?? {}) };
    if (this.cfg.certificat?.actif === false) return;
    const se = n === 2 && opts.CERT_SEULE ? this.voixSeule(g, tNow, opts) : null;
    if (!se) return this.certifierCorps(g, tNow, n, t0Note, envHz);
    // v71 (CERT_SEULE) : une voix est absente. La paire garde sa chance (une anche faible que le traqueur perd peut être lue par le modèle à deux anches) ; ce n'est que si elle ne
    // certifie rien que la lecture à UNE anche prend le relais. Avant la confirmation (SEULE_ABSENTE_S) elle est seulement calculée d'avance (`attente`), pas affichée.
    const gs = { key: `${g.key}:seule`, center: g.center, voices: [se.v] };
    if (!se.confirmee) this.certifierCorps(gs, tNow, 1, t0Note ?? se.t0, null, true);
    this.certifierCorps(g, tNow, 2, t0Note, envHz);
    const posee = (v) => v.source === 'certificat' && v.etatAnche === 'sur' && v.margeAnche === 0;
    if (se.confirmee && !posee(se.v)) {
      const v = se.v, sauve = { etat: v.etatAnche, marge: v.margeAnche, refus: v.refus, cause: v.refusCause, tBesoin: v.tBesoin, cert: v.cert };
      this.certifierCorps(gs, tNow, 1, t0Note ?? se.t0, null);
      if (posee(v)) { for (const w of g.voices) if (w !== v) { w.refus = null; w.refusCause = null; w.cert = null; } }      // la voix absente ne sonne pas : rien à certifier ni à refuser
      else { v.etatAnche = sauve.etat; v.margeAnche = sauve.marge; v.refus = sauve.refus; v.refusCause = sauve.cause; v.tBesoin = sauve.tBesoin; v.cert = sauve.cert; }      // la lecture à une anche ne certifie pas non plus : le refus de la paire reste le message
    }
  },
  certifierCorps(g, tNow, n, t0Note, envHz = null, attente = false) {
    const opts = { ...CERT, ...(this.cfg.certificat ?? {}) };
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
    st.envHz = envHz;
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
        if (!job.sentinelle && job.froid && Number.isFinite(res.ms)) this.msFroid = this.msFroid == null ? res.ms : 0.6 * this.msFroid + 0.4 * res.ms;       // v68 (H4) : la vitesse de la machine, mesurée sur les ajustements à froid
        if (res.erreur) { st.derniere = { ok: false, raisons: ['domaine'], t: tNow, erreur: String(res.erreur) }; st.cands = []; continue; }
        if (job.sentinelle) this.finirSentinelle(st, job, res.nls, tNow, calib, opts); else this.finirAjustement(st, job, res.nls, tNow, calib, opts, n);
      }
      st.jobs = st.jobs.filter((j) => tNow - j.tFin < 12);        // un travail qui ne revient jamais (Worker mort) ne bloque pas la note
    } else if (st.jobs.length) {
      const tDebut = opts.MS_PAR_IMAGE ? performance.now() : 0;
      let cout = 0;
      for (let i = 0; st.jobs.length && (opts.MS_PAR_IMAGE ? i === 0 || performance.now() - tDebut < opts.MS_PAR_IMAGE : opts.COUT_PAR_IMAGE ? cout < opts.COUT_PAR_IMAGE : i < pasI); i++) {
        const job = (opts.SENT_PRIO && st.jobs.find((j) => j.sentinelle)) || st.jobs[i % st.jobs.length];
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
    // v68 (H4) : machine lente (durée moyenne d'un ajustement à froid mesurée dans le Worker) : ajustements plus légers et un seul de front ; hystérésis (le mode léger raccourcit lui-même les ajustements : sans elle la machine passerait de l'un à l'autre)
    if (this.msFroid != null) this.lente = this.msFroid > opts.MS_LENT || (this.lente && this.msFroid > 0.7 * opts.MS_LENT);
    const lente = !!this.lente;
    if (st.jobs.filter((j) => !j.sentinelle).length < (lente ? opts.LENT_JOBS_MAX : opts.JOBS_MAX) && (!certTient || aRafraichir) && age >= opts.AGE_MIN_S && tPeut && st.essais < opts.ESSAIS_MAX) {
      const iFin = this.samplesTotal;
      // la fenêtre attend d'avoir de quoi séparer les raies (K·Ω·T ≥ KOT_MIN, au moins NB_MIN battements) et de quoi lire assez juste pour la hauteur de la note
      // (FEN_F0_S / f : en ¢, l'erreur d'une fréquence est en 1/f) ; elle vise FEN_MAX_S mais jamais moins que ce besoin, jamais plus que FEN_ABS_MAX_S
      const fm = fMoteur();
      const ecarts = fm.slice(1).map((f, j) => Math.abs(f - fm[j]));
      const om = n === 1 ? 0 : st.omega ?? Math.min(...ecarts);
      const K = Math.max(1, Math.min(opts.KMAX, Math.floor(0.42 * this.sr / (fm[n - 1] * 1.04))));
      const omOk = n !== 1 && om >= opts.OMEGA_MIN && om <= opts.OMEGA_MAX;
      // v67 (G2) : battement lent : la fenêtre est un nombre ENTIER de battements (au moins ENTIER_NB)
      const entier = n === 2 && opts.ENTIER_NB > 0 && omOk && om < opts.OMEGA_SUR_MIN;
      let besoin = n === 1 ? Math.max(opts.FEN_MIN_S, opts.SEULE_FEN_F0_S / fm[0]) : omOk ? Math.max(opts.FEN_MIN_S, (opts.NB_MIN ?? 0) / om, (opts.FEN_F0_S ?? 0) / fm[n >> 1], 1.1 * opts.KOT_MIN / (K * om)) : opts.FEN_MIN_S;
      if (entier) besoin = Math.max(besoin, opts.ENTIER_NB / om);
      const plafond = Math.min(entier ? opts.FEN_ENTIER_MAX_S : opts.FEN_ABS_MAX_S, this.anneau.length / this.sr - 0.1);
      let fen0 = Math.min(Math.min(plafond, Math.max(n === 1 ? opts.SEULE_FEN_MAX_S : opts.FEN_MAX_S, besoin)), age - opts.DEBUT_S);
      if (entier) fen0 = Math.floor(fen0 * om + 1e-6) / om;
      if (fen0 >= besoin - 1e-6) {
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
            this.lancerTravail(st, cle, tNow, { n, x, sr: this.sr, fc: g.center, optsFit: { prior, priorFirst: !!chaud || (opts.PRIOR_FIRST && n === 2 && vs.every(ok)), chaud: !!chaud, pInit: chaud?.sol ?? null, dt: chaud ? (tNow - fen / 2) - chaud.tMilieu : 0, libreInit: chaud?.sol && chaud.libre ? chaud.sol[n === 3 ? 13 : 8] : null, Kmax: opts.KMAX, iter: lente ? opts.LENT_ITER : opts.ITER, nLibre: opts.NLIBRE, nDeparts: chaud ? 1 : (lente ? opts.LENT_NDEPARTS : opts.NDEPARTS), modele: opts.MODELE, rkMax: opts.RK_MAX_AM, kcMax: !!opts.KC_MAX, kcPropre: !!opts.KC_PROPRE, libreDoublon: !!opts.LIBRE_DOUBLON, doublonDist: opts.DOUBLON_DIST, doublonDb: opts.DOUBLON_DB, omegaMin: opts.RIVAL_MOITIE && n === 2 ? opts.OMEGA_MIN : 0, ...(n === 1 ? { Kmax: opts.SEULE_KMAX, ekC: opts.SEULE_EK_C } : {}) }, opts, calib, moteur: { f: fMoteur(), sur: moteurSur } },
              { fMoteur: fMoteur(), moteurSur, tMilieu: tNow - fen / 2, tFin: tNow, T: fen, zeros, froid: !chaud });
          } else if (zeros) { st.derniere = { ok: false, raisons: ['trous'], t: tNow }; st.cands = []; }
        }
      }
    }

    // 2 bis. sentinelle (F1)
    if (opts.SENTINELLE && n !== 1 && certTient && !st.jobs.some((j) => j.sentinelle) && tNow - (st.tSent ?? -1e9) >= opts.SENT_PERIODE_S && st.cert.sol) {
      const omS = st.cert?.nls?.Om;
      const fenBat = opts.SENT_FEN_BAT > 0 && Number.isFinite(omS) && omS > 0 ? Math.min(opts.SENT_FEN_BAT_MAX, opts.SENT_FEN_BAT / omS) : 0;      // v68 : battement lent, la sentinelle voit au moins SENT_FEN_BAT battement(s)
      const fenS = Math.min(Math.max(opts.SENT_FEN_S, fenBat), age - opts.DEBUT_S);
      if (fenS >= 0.45) {
        const xs = this.extraireAnneau(this.samplesTotal - Math.round(fenS * this.sr), this.samplesTotal);
        if (xs && plagesDeZeros(xs, 0, xs.length, this.sr) < 0) {
          st.tSent = tNow;
          const ch = st.cert;
          this.lancerTravail(st, cle, tNow, { n, sentinelle: true, x: xs, sr: this.sr, fc: g.center, optsFit: { prior: ch.f.map((f) => f / calib), priorFirst: true, chaud: true, pInit: ch.sol, dt: (tNow - fenS / 2) - ch.tMilieu, libreInit: ch.sol && ch.libre ? ch.sol[n === 3 ? 13 : 8] : null, Kmax: opts.SENT_KMAX ?? opts.KMAX, kcMax: !!opts.KC_MAX, kMin: opts.SENT_KMIN > 1 && Number.isFinite(omS) && omS < opts.SENT_KMIN_OMEGA ? opts.SENT_KMIN : 1, iter: opts.SENT_ITER ?? opts.ITER, nLibre: 0, nDeparts: 1, modele: opts.MODELE, rkMax: opts.RK_MAX_AM } },
            { sentinelle: true, tMilieu: tNow - fenS / 2, tFin: tNow, T: fenS });
        }
      }
    }

    if (attente) return;       // v71 : lecture à une anche calculée d'avance (voixSeule), pas encore affichée

    // 3. verdict affiché
    const certOk = st.cert?.ok && this.certAccord(st.cert, vs, tNow, opts);
    const raisons = certOk ? [] : st.derniere && !st.derniere.ok ? st.derniere.raisons : ['verification'];
    const dernier = st.cert ?? st.derniere;
    for (const v of vs) { v.cert = dernier ? { ok: !!certOk, llr: dernier.nls?.llr ?? null, r: dernier.nls?.r ?? null, derive: dernier.nls?.derive ?? null, raisons: certOk ? [] : (st.derniere?.raisons ?? null), essais: st.essais, beta: dernier.detail?.beta ?? null, m: dernier.detail?.m ?? null, plancher: dernier.detail?.plancher ?? null, kot: dernier.detail?.kot ?? null, libre: dernier.nls?.libre ?? null, sigmaC: dernier.nls?.sigmaC ?? null, fenMilieu: dernier.tMilieu ?? null, fenT: dernier.nls?.T ?? null } : null; }
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
        let corr = Math.max(-0.5, Math.min(0.5, st.corr ?? 0));
        const dT = st.cert.nls?.deriveT, dd = st.cert.derive ?? st.cert.nls?.derive;
        if (opts.PRESENT && n === 2 && Number.isFinite(dT) && Math.abs(dT) >= opts.PRESSION_T_MIN && Math.abs(dd) <= opts.DERIVE_MAX) corr += dd * (st.cert.nls.T / 2);
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
    if (n === 2 && nls.ok && v.raisons.every((q) => ['verification', 'accord', 'stabilite', 'lent'].includes(q)) && nls.r <= opts.R_MAX && (st.envHz == null || Math.abs(nls.Om * calib - st.envHz) <= opts.ENV_ACCORD * st.envHz) && (!opts.BATTEMENT_PRINCIPAL || job.T * nls.Om * calib >= opts.BP_NB_FIT)) { (st.omegas ??= []).push({ t: job.tMilieu, T: job.T, om: nls.Om * calib }); if (st.omegas.length > 150) st.omegas.shift(); }
    st.essais++;
    st.tDernierFit = tNow;
    const refusModele = (r) => !r.ok && r.raisons?.some((q) => opts.REFUS_RAISONS.includes(q));
    const recents = (st.recents ??= []);
    const nRefusRecents = recents.filter(Boolean).length;
    recents.push(refusModele(v)); if (recents.length > 4) recents.shift();
    const amAdopte = !(n === 2 && opts.AM_RHO_PORTEE >= 2 && amInadmissible(nls, opts));      // v72 (J1), portée 2 : un ajustement dont l'AM est inadmissible n'est adopté nulle part
    if (nls.ok && amAdopte) st.omega = n === 3 ? Math.min(...nls.Om) : nls.Om;
    const ecart = (a, b) => Math.max(...a.map((x, j) => Math.abs(1200 * Math.log2(x / b[j]))));
    // les candidats (C1 à C8 passés) des 5 dernières secondes ; un échec net (autre que l'accord avec le traqueur, qui n'engage que lui) les efface
    st.cands = st.cands.filter((q) => tNow - q.t <= 5);
    const sol = nls.ok && nls.sol ? Array.from(nls.sol).slice(0, n === 3 ? 14 : nls.modele === 'struct' ? 9 + 8 : 9) : null;
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
    if (nls.ok && n === 2 && opts.ETIQ_COH_C > 0) {
      const vus = (st.vus ??= []);
      while (vus.length && tNow - vus[0].t > opts.ETIQ_COH_S) vus.shift();
      if (v.ok && vus.some((q) => ecart(f, q.f) > opts.ETIQ_COH_C)) { v.ok = false; v.raisons = ['etiquette']; st.cands = []; }
      if (amAdopte && nls.r <= 0.05 && nls.llr >= NLS_LLR_SUR) vus.push({ t: tNow, f });
    }
    if (v.ok && opts.REFUS_RECENTS > 0 && nRefusRecents >= opts.REFUS_RECENTS) { v.ok = false; v.raisons = ['niveau']; st.cands = []; }
    if (v.ok) {
      const parDecalage = st.cands.find((q) => Math.abs(job.tMilieu - q.tMilieu) >= opts.DECALAGE_MIN_S && ecart(f, q.f) <= opts.CONFIRME_C);
      const mo = nls.moities;
      const tolMoitie = opts.CONFIRME_MOITIE_C;
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
      v.modeleCert = cert.nls?.seule ? 'seule' : vs.length === 3 ? 'trio' : 'paire';       // v71 : le modèle qui a produit le chiffre (une anche, deux anches, trois anches)
      v.pression = cert.nls?.pression ? { c: cert.nls.pression.sigmaC, db: cert.nls.pression.etenduDb, propre: cert.nls.pression.propre } : null;       // v67 (G5)
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

// v67 (G5) : la hauteur d'une lecture « sûre » est celle d'un NIVEAU DE JEU (la pression du soufflet : le niveau au micro n'est pas un manomètre, la loi hauteur / pression ne se lit pas
// dans le son). Le niveau commun aux deux anches, ajusté en même temps que la hauteur (g(t) du modèle), a une étendue ΔL (dB) sur la fenêtre ; elle se convertit en incertitude (¢) par la
// pente hauteur / niveau de la note quand elle est significative (|t| > PRESSION_T_MIN, régression des nœuds du warp), sinon par la pente de repli. Rend { etenduDb, pente, propre, sigmaC }.
export function incertitudePression(nls, opts = CERT) {
  const L = nls?.niveauWarpDb, P = nls?.warpC;
  if (!Array.isArray(L) || L.length < 2) return null;
  const lv = L.map((g) => 20 * Math.log10(Math.max(1e-6, 1 + g)));
  const etenduDb = Math.max(...lv) - Math.min(...lv);
  let pente = opts.PRESSION_REPLI_C_DB, propre = false;
  if (Array.isArray(P) && P.length === lv.length && lv.length >= 4) {
    const J = lv.length, ml = lv.reduce((a, b) => a + b, 0) / J, mp = P.reduce((a, b) => a + b, 0) / J;
    const sxx = lv.reduce((a, b) => a + (b - ml) ** 2, 0), sxy = lv.reduce((a, b, j) => a + (b - ml) * (P[j] - mp), 0);
    if (sxx > 1e-6) {
      const s = sxy / sxx, rss = P.reduce((a, b, j) => a + (b - mp - s * (lv[j] - ml)) ** 2, 0), se = Math.sqrt(rss / (J - 2) / sxx);
      // pente propre bornée par la pente de repli : sur 4 à 9 nœuds du warp, une pente significative de 1 à 10 ¢/dB (H6) est un couplage de l'ajustement, pas la physique (mesures : 0,15 à 0,25 ¢/dB)
      if (se > 0 && Math.abs(s) / se > opts.PRESSION_T_MIN) { pente = Math.min(opts.PRESSION_REPLI_C_DB, Math.abs(s)); propre = true; }
    }
  }
  return { etenduDb, pente, propre, sigmaC: pente * etenduDb };
}

// v68 : t de Student de la pente du warp (dérive significative ?), même régression que incertitudePression
function tDerive(r) {
  const P = r?.warpC, T = r?.T;
  if (!Array.isArray(P) || P.length < 4 || !(T > 0)) return null;
  const J = P.length, tj = P.map((_, j) => (j / (J - 1) - 0.5) * T), mp = P.reduce((a, b) => a + b, 0) / J, sxx = tj.reduce((a, b) => a + b * b, 0);
  const b = tj.reduce((a, t, j) => a + t * (P[j] - mp), 0) / sxx, rss = P.reduce((a, v, j) => a + (v - mp - b * tj[j]) ** 2, 0), se = Math.sqrt(rss / (J - 2) / sxx);
  return se > 0 ? b / se : null;
}

function resumeNls(r) {
  if (!r?.ok) return { ok: false, raison: r?.raison ?? null };
  return { seule: !!r.seule, pression: incertitudePression(r), deriveT: tDerive(r), f: r.f, Om: r.Om, b: r.b, m: r.m, modele: r.modele, llr: r.llr, r: r.r, K: r.K, T: r.T, Ku: r.Ku, derive: r.derive, agit: r.agit, warpC: r.warpC, libre: r.libre ? { dB: r.libre.dB } : null, plancherDb: r.plancherDb, niveauxDb: r.niveauxDb ?? null, sigmaC: r.sigmaC, ms: r.ms };
}
