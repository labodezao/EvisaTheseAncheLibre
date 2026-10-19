# Certificat des lectures « sûres » (v70, 19/10/2026)

Audit Fable du 15/10/2026 (`J:\claude\audits\2026-10-17-accordeur-fable\RAPPORT-AUDIT.md`, R1 à R14) puis ses suites du 16/10 (critères d'Ewen : niveau professionnel,
musette et super musette, Do2 à A6, tout micro USB, pose courte, refus expliqués). Règle d'Ewen : un accordeur professionnel ne dit « sûr » que s'il peut le prouver ;
zéro lecture « sûre » fausse (erreur de plus de 0,5 ¢ sur une anche), avec n'importe quel micro. Journal des versions : `docs/JOURNAL-DES-VERSIONS.md`.

## TABLEAU DE BORD (règle de convergence d'Ewen, 18/10/2026) : le même pour v66, v67, v68, v69, v70

Neuf indicateurs fixes. « Publié » = chiffre écrit à l'époque (§ 0A.3, 0A.4, 0B.6, 0.1) : jeux, graines et outils ont changé d'une version à l'autre, ce n'est pas toujours comparable (dit case par case). La colonne **v68 recompté** est la seule strictement comparable à la v69 : mêmes plans, mêmes graines neuves (REP0=40, GEN 50), mêmes outils (vérité de la fenêtre lue pour toute lecture, `eval63.mjs` / `verdict.mjs` de la v69), code gelé de `origin/main` a720bdb contre la branche. Passes brutes : `J:\claude\tmp\v69\final\v68\` et `...\v69\`.

| # | indicateur | v66 (publié) | v67 (publié) | v68 (publié) | **v68 recompté** | **v69** | variation v69 / v68 recompté | **v70** | variation v70 / v69 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | lectures « sûr » fausses (> 0,5 ¢), toutes passes | 3 (h6 1, large 2) | 6 (h6 1, large 1, ancienne 4) | 1 (GEN large, 0,556 ¢, retard de la vérité) | **1** (hypercube4 plan 233 graine 43, 0,56 ¢) | **1 (la même note, 0,562 ¢)** ; confirmation hypercube4 x 3 synthèses x 4 graines neuves (3 600 notes) : **0** | aucune de plus ; voir 0C.1 | **0** : la note 233/43 est lue juste (0,01 / 0,05 ¢) ; 0 sur toutes les passes ; confirmation hypercube4 x 3 synthèses x 4 graines neuves REP0=48 (3 600 notes) : **0**, max 0,44 ¢ | le « 1 » est fermé |
| 2 | notes posées, synthèse h6 (32 plans) | 1 169 / 4 065 (28,8 %), 21 plans, non comparable | 1 059 / 4 247 (24,9 %), 22 plans | 941 / 4 247 (22,2 %) | 1 158 / 4 993 (23,2 %) | **1 486 / 4 993 (29,8 %)** | **+28 %** | **1 428 / 4 065** (même décompte que v69 : 1 424) | +0,3 % |
| 3 | notes posées, synthèse LARGE (12 plans) | 407 / 2 528 (16,1 %) | 474 (18,8 %) | 420 (16,6 %) | 437 / 2 528 (17,3 %) | **590 (23,3 %)** | **+35 %** | **584 / 2 528** (v69 : 590) | -1,0 % |
| 4 | notes posées, ancienne synthèse (5 plans) | non rejouée | 505 / 1 198 (42 %) | 451 (38 %) | 468 / 1 198 (39,1 %) | **587 (49,0 %)** | **+25 %** | **586 / 1 198** (v69 : 587) | -0,2 % |
| 5 | H6 réel x1 (27 notes, essai 1) | 6 | 16 | 16 | 16 | **17** | +1 note | **17** | 0 |
| 6 | H6 réel x4 (calcul 4 fois plus lent) | non mesuré | 1 | 10 | 10 | **10** | 0 | **10** | 0 |
| 7 | graves f0 < 150 Hz posées (synthèse h6 / LARGE / GEN) | non mesuré | non mesuré | non comparable (autres jeux) | 16 / 1 355, 1 / 759, 1 / 161 | **70 / 1 355, 23 / 759, 6 / 161** | **x 4,4, x 23, x 6** (de 1 % à 3-5 %) | **82 / 2 002, 22 / 801, 2 / 164** (v69 recompté par le même script : 82, 23, 2 ; f0 < 150 Hz) | = / -1 note / = |
| 8 | corpus Serafini : voix « sûr » justes (vérité sinus) | 1 note | 3 notes, 6 voix, max 0,16 ¢ (Python) | 2 notes, 4 voix, max 0,16 ¢ (Python) | 2 notes, 4 voix, max 0,083 ¢ (port JS) | **3 notes, 6 voix, max 0,213 ¢** | +1 note, 0 > 0,3 ¢ | **3 notes, 6 voix, max 0,213 ¢** | 0 |
| 9 | retard p90 après un saut, Worker simulé x1 (ancienne / H6 / LARGE) | non mesuré | 0,41 / 0,38 / 0,48 s | 0,32 / 0,33 / 0,39 s | 0,33 / 0,41 / 0,38 s | **0,32 / 0,41 / 0,33 s** | = / = / -0,05 s ; D4 (Ω lent) H6 0,41 -> 0,33 s, LARGE 0,50 -> 0,41 s | **0,33 / 0,41 s** (D4 h6 / LARGE, Worker simulé x1) | = |

Le « 1 » de la ligne 1 : une note de `lhs300_calib` (graine 43, f0 164 Hz, Ω 1,21 Hz, anche faible à 17,8 dB avec une raie étrangère à -15 dB, RSB 25 dB) lue à -0,56 ¢ sur la fenêtre lue (-0,40 puis -0,56 ¢ : l'anche faible entraînée par la raie étrangère). **Elle est identique dans la v68 et la v69** : ce n'est pas une régression ; elle n'apparaissait pas dans les passes de la v68 parce que celles-ci jugeaient la plupart des plans contre la moyenne des 3 dernières secondes (colonne « v67 » du verdict : 3 lectures sûres à plus de 0,5 ¢ de cette moyenne, pour les deux versions). Avec la vérité unifiée de la v69 (I7), la v68 n'a donc pas « zéro faux » non plus. Aucune rustine n'est ajoutée sans plan (I9) : le cas est livré à l'audit n° 6.

**Critère de convergence.** La v69 ne se fusionne que si (1) reste à 0 et qu'aucun des indicateurs (2) à (9) ne recule de plus de 3 % sans gain qui le justifie. Résultat : (2) à (4) montent de 25 à 35 %, (5) à (9) ne reculent pas (le seul recul chiffré est GEN large à physique très large, 9 -> 8 posées sur 176, 1 note, justifié par les +25 à +35 % des trois synthèses). (1) n'est pas à 0, mais à la même valeur que la v68 recomptée avec la même vérité, sur la même note, et à 0 sur 3 600 notes de confirmation à graines neuves. **La branche n'est donc pas fusionnée par l'agent** : la règle d'Ewen dit « (1) reste à 0 », et ce « 1 » est antérieur à la v69 ; la décision de fusion est laissée au coordinateur (PR ouverte, contrôles GitHub verts).

**Critère de convergence de la v70 (tenu).** (1) = 0 sur toutes les passes, la note 233/43 comprise ; (2) à (4) ne reculent pas de plus de 3 % (le pire : LARGE -1,0 %) ; H6 réel x1 17/27 et x4 10/27 (= v69). Passes finales aux mêmes graines que la v69 (REP0=40, GEN 50), code gelé, `J:\claude\tmp\v70\final\v70\` contre `J:\claude\tmp\v69\final\v69\`. Détail : 0D.

## 0D. La v70 (audit Fable n° 6 du 18/10/2026) : la consigne CONSIGNE-V70 appliquée (J1 et J2 ; J3 attend la session Android d'Ewen)

Audit : `J:\claude\audits\2026-10-18-accordeur-fable-6\RAPPORT-AUDIT-6.md` (§ 9). Un seul changement de code : `LIBRE_DOUBLON`. Aucun seuil réglé sur les prises du 11, 13, 14/10 ni sur le corpus.

**J1 : `LIBRE_DOUBLON`.** Mécanisme (audit n° 6, § 2) : la note 233/43 (f0 164 Hz, Ω 1,21 Hz, anche faible à 17,8 dB, raie étrangère à -15 dB à 0,32 Hz de l'anche forte) est dans la garde de la recherche à 2 partiels, la raie n'est jamais candidate ; une raie libre glisse alors en DOUBLON de l'anche forte (0,036 Hz, -3,5 dB), absorbe l'écart et tire l'anche faible (-0,56 ¢ sur la fenêtre lue). Règle (`nls-bessel.js`) : une raie libre ajustée à moins de `DOUBLON_DIST`/(K·T) d'une anche ou d'une de leurs raies latérales f_r + nΩ (n = ±1..3), et à moins de `DOUBLON_DB` dB sous l'anche la plus proche, n'est pas adoptée. Éteinte, elle ne change aucun calcul. Plan 2^2 complet (`outils/doe.py`, graine 44), graines neuves REP0=44 :

| `DOUBLON_DIST` ; `DOUBLON_DB` | posées h6 /300 | posées LARGE /300 | graves h6 /40 | H6 x1 | H6 x4 | faux | note 233/43 |
|---|---|---|---|---|---|---|---|
| v69 (règle éteinte) | 104 | 85 | 5 | 17 | 10 | 0 | doublon -3,6 dB, lue à -0,40 / -0,45 ¢ |
| **0,5 ; 6 (retenu)** | **108** | **83** | 5 | **17** | **10** | 0 | juste (0,01 / 0,05 ¢), vraie raie -15,6 dB |
| 1,0 ; 6 | 107 | 82 | 5 | 16 | 11 | 0 | juste |
| 0,5 ; 99 | 109 | 82 | 5 | 16 | 9 | 0 | juste |
| 1,0 ; 99 (prototype de l'audit) | 105 | 74 | 4 | 16 | 9 | 0 | juste |

Plan saturé (4 essais) : aucun effet significatif au sens de Lenth ; le seul écart de taille est celui du prototype (1,0 ; 99) en LARGE, -11 notes (-13 %), que la condition de niveau (6 dB) ramène à -2 (-2,4 %). Retenu : la cellule qui garde H6 17/27 et 10/27 et le plus de posées sans dépasser -3 %. **Confirmation** hypercube4 x 3 synthèses x 4 graines neuves (REP0=48, 3 600 notes) : h6 448 / 1 199 posées, LARGE 320 / 1 200, ancienne 585 / 1 200 ; **0 faux** partout, max 0,44 ¢. Passes finales contre la v69 aux mêmes graines : h6 1 424 -> 1 428, LARGE 590 -> 584, ancienne 587 -> 586, GEN 121 -> 122, Worker simulé 422 -> 419 sur 1 000 ; le « sûr » faux de la v69 (hypercube4 plan 233 graine 43) disparaît. Banc CI : la note 233/43 y est ajoutée (`ci_seuils.json`) ; elle fait échouer le banc quand `LIBRE_DOUBLON` est éteint (1 faux) et le passe allumé (0).

**J2 : diagnostic du résidu des partiels 1-4 après l'ajustement final** (`test/outils/pose/residu_h6.mjs`, aucun changement de modèle). Pour chaque note posée : dernier ajustement jugé ok rejoué, résidu complexe de chaque partiel analysé par DFT (Hann), rapporté à l'énergie du partiel et réparti entre les raies de chaque anche (k f_r + mΩ) : porteuse (m = 0, à ±1/T), ±Ω, ±2Ω et ±3Ω, ailleurs. À égalité de raie (les deux anches se recouvrent) la classe d'ordre le plus bas gagne. Dernière colonne : part qu'aurait un résidu blanc (nombre de cases).

H6 réel, essai 1 : 17 notes posées (partiels 3 et 4 : 7 et 5 notes seulement, ceux que le modèle sait décrire).

| partiel | résidu / énergie (médiane) | porteuse | ±Ω | ±2Ω, ±3Ω | ailleurs | résidu blanc : porteuse / ±Ω / ±2Ω±3Ω / ailleurs |
|---|---|---|---|---|---|---|
| 1 | 0,12 % | 8 % | 15 % | 57 % | 20 % | 4 / 5 / 10 / 81 % |
| 2 | 5,02 % | 29 % | 39 % | 23 % | 9 % | 5 / 6 / 9 / 80 % |
| 3 | 0,55 % | 10 % | 39 % | 39 % | 12 % | 5 / 9 / 10 / 76 % |
| 4 | 1,50 % | 13 % | 43 % | 36 % | 8 % | 5 / 11 / 14 / 70 % |

Synthèse h6 (20 notes posées, graine 44) : résidu 0,35 à 0,57 %, 70 à 78 % « ailleurs » (blanc : 82 à 90 %), ±Ω 12 à 19 %, ±2Ω±3Ω 6 à 8 %.

**Lecture : quelle physique manque.** (1) Sur l'instrument réel, le résidu des partiels 2 à 4 n'est pas du bruit : 90 % de son énergie tombe sur les raies de modulation (blanc : 20 à 30 %), alors que la synthèse en laisse 70 à 80 % dans le bruit. (2) Il est réparti sur les bandes latérales ±Ω (39 à 43 %, environ 4 fois la part d'un résidu blanc) et ±2Ω, ±3Ω (36 à 39 %, 3 à 4 fois), très peu sur la porteuse (10 à 13 %) : ce sont les amplitudes et phases des bandes latérales d'ordres 1 à 3 qui ne sont pas celles du peigne de Bessel d'une modulation sinusoïdale (modulation non sinusoïdale de l'anche, AM propre des bandes), pas la fréquence des anches. (3) Le profil par raie décroît avec l'ordre (environ 10 % par raie à ±Ω contre 4,5 % à ±2Ω et ±3Ω) : une simple dérive de Ω l'aurait fait croître avec m ; elle n'est pas indiquée comme cause principale. Entrée de l'audit n° 7 : une harmonique de modulation (β_k,2 sin 2Φ par anche) à essayer sur le H6 réel et la synthèse LARGE enrichie, par plan 2^2. Limites : 17 notes d'un seul instrument et d'un seul micro, partiels 3-4 sur 5 à 7 notes ; la classe « ±2Ω, ±3Ω » est ce qui reste après les raies d'ordre plus bas des deux anches.

**J3** (session Android, `calcul.msFroid`) : en attente du geste d'Ewen, rien inventé ; le facteur x4 du tableau de bord reste une hypothèse.

## 0C. La v69 (audit Fable n° 5 du 18/10/2026) : la consigne CONSIGNE-V69 appliquée

Audit : `J:\claude\audits\2026-10-18-accordeur-fable-5\RAPPORT-AUDIT-5.md` (I1 à I9, consigne § 9), résumé des plans `DOE-RESUME.md`. Verdict de l'audit sur la v68 : « niveau professionnel non atteint à l'établi, non prouvé hors du Zoom H6 » ; 11 % de notes posées en moins en synthèse (le prix des graves et d'une garde d'étiquette), sentinelle aveugle sous 1 Hz, prise 16 bits prise pour une porte, aucune mesure d'échelle, aucun enregistrement nouveau.

**Ce que cette version ne prouve toujours pas** (inchangé) : rien sous 207 Hz (aucune note réelle plus grave n'a jamais été mesurée), rien en super musette réelle, rien sur un autre micro ni sur un vrai téléphone. Tout ce qui suit est mesuré sur la synthèse (`SYNTH=h6`, `SYNTH=large`, ancienne), sur les prises H6 (vérification, jamais réglage) et, pour la robustesse, sur les sessions traitées et le corpus sf2 (jamais un seuil).

### 0C.1 I1 à I9 : fait, partiel, refusé

| I | Sujet | Statut | Résultat |
|---|---|---|---|
| I1 | graves | **fait, en partie** | `F0_GRAVE_HZ` 150 -> 120 (plan 2^2 x 4 graines neuves) : graves posées 12 -> 29 sur 832, 0 faux, `lent100` plan 82 jamais « sûr ». Le diagnostic est écrit (0C.3) : le 3e partiel n'est PAS mal décrit par le modèle ; c'est la comparaison d'étiquettes qui ramène le gagnant à 2 partiels. Le réparer (`KC_MAX`, `KC_PROPRE`) n'a pas donné de gain global : refusé, options gardées éteintes |
| I2 | pertes hors graves | **fait, mieux que prévu** | PB12 (7 facteurs) : un seul facteur compte, **2 départs et 1 ajustement de front** (+23,7 notes sur 300 en h6, +19,2 en LARGE, p < 10^-4) ; `REESSAI_S` 0,3 fait des « sûr » faux sur les prises H6 (refusé) ; les autres sont sans effet. Confirmation hypercube4 x 3 synthèses x 4 graines neuves (3 600 notes) : 0 faux |
| I3 | sentinelle sur les partiels hauts | **refusé (hypothèse réfutée)** | plan 2^2 : `SENT_KMIN` 3 allonge le retard (p90 0,33 -> 0,58 s) et l'exposition (13 -> 63 images) ; la v68 (partiels 1 à 4, fenêtre 0,7 battement) est le meilleur des quatre |
| I4 | prise | **fait** | (a) fausse alarme 16 bits corrigée (65 -> 0 s sur 211) ; (b) alerte `echelle` par le secteur ; (c) lot CI de chaînes ; (d) écran. Le critère « bande <= 10 s » n'est pas tenu (0C.4) |
| I5 | téléphone, mesurer | **fait (code), geste d'Ewen en attente** | `msFroid`, `lente`, `dspMs` (p50, p99) dans la session et la bande luthier |
| I6 | super musette, mesurer d'abord | **fait (diagnostic), pas de modèle** | `trio_diag.mjs` tourne sur les 5 notes équilibrées de Serafini md (0C.6) |
| I7 | banc et CI | **fait** | vérité unifiée (fenêtre lue) ; déterminisme CI ; lot « objectif graves » ; gardes mortes retirées ; passes gardées |
| I8 | généralisation du corpus | **fait** | `corpus_verite.mjs` (port de `verite_sinus.py`), `corpus_ecarts.mjs`, test local ; sfArk : geste d'Ewen (Polyphone) |
| I9 | le modèle | **tenu** | aucune garde nouvelle sans plan ; les trois ajouts du code (`F0_GRAVE_HZ`, départs/front, `echelle`) ont leur plan ; `KC_MAX`, `KC_PROPRE` et `SENT_KMIN` (essayés) restent éteints |

### 0C.2 Plans d'expériences (règle 12 ; plans fractionnaires quand ils suffisent, précision d'Ewen du 18/10)

**I1 : plan 2^2 complet** (`F0_GRAVE_HZ` 150 ; 120 x `KU_SUR_MIN_GRAVE` 3 ; 2, graines neuves 33, 34, 35 ; `lent100` LARGE aussi à 32). Un plan fractionnaire ne ferait pas gagner de cellule à 2 facteurs. Jeux : `lent100` LARGE (400 notes), graves (f0 < 150 Hz, 40 lignes) de `gen160b` en LARGE et en h6 (120 chacun), `lhs300_calib` h6 (900 notes). Posées / graves posées :

| `F0_GRAVE_HZ` ; `KU_SUR_MIN_GRAVE` | posées | « sûr » faux | graves posées (sur 832) | `lent100` plan 82 |
|---|---|---|---|---|
| 150 ; 3 (v68) | 296 | 0 | 12 | jamais sûr |
| 150 ; 2 | 334 | 0 | 50 | **sûr une fois, à 0,33 ¢ (vérité de la fenêtre lue)** |
| **120 ; 3 (retenu)** | 313 | 0 | 29 | jamais sûr |
| 120 ; 2 | 334 | 0 | 50 | sûr une fois |

Effets : `KU_SUR_MIN_GRAVE` 3 -> 2 rend 38 notes (la règle des graves elle-même) mais rouvre la note-piège de l'audit n° 4 ; la borne 120 rend 17 graves sans la rouvrir. `F0_GRAVE_HZ` n'a aucun effet quand la règle est à 2 (cellules identiques). Maximum d'erreur 0,365 ¢. Critère de l'audit « graves posées >= 2 x v68 sur les 4 jeux » : tenu en somme (29 contre 12, x 2,4), pas jeu par jeu (`lent100` 3 -> 5).

**I2 : Plackett-Burman 12 cellules, 7 facteurs** (graine 69 ; résolution III : les effets principaux sont confondus avec des interactions à 2 facteurs, ce que l'analyse rappelle ; 4 degrés de liberté d'erreur). L'audit proposait `CONF_SENT_SIGMA_MAX` et `CONF_FEN_BAT` : **ils ne font rien** (ils appartiennent à `CONFIRME_SENT`, refusé et éteint en v68) ; remplacés par `CONFIRME_C`, `REESSAI_S` et `CONFIRME_MOITIE_C`, qui sont actifs. Facteurs (bas ; haut) : `ETIQ_COH_C` 3 ; 4,5 - `DECALAGE_MIN_S` 0,5 ; 0,35 - départs/front 5/2 ; 2/1 - `SENT_PERIODE_S` 0,10 ; 0,15 - `CONFIRME_C` 0,3 ; 0,4 - `REESSAI_S` 0,4 ; 0,3 - `CONFIRME_MOITIE_C` 0,4 ; 0,6. Jeux par cellule : `lhs300_calib` h6 et LARGE (graine 30), `lent100` h6, D3 h6 (Worker simulé x1), H6 réel x1 et x4.

| cellule | ETIQ | DECAL | départs/front | PERIODE | CONF_C | REESSAI | MOITIE | h6 /300 | LARGE /300 | faux | retard p90 | H6 x1 | H6 x4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 4,5 | 0,35 | 5/2 | 0,15 | 0,4 | 0,3 | 0,4 | 81 | 58 | 2 | 0,33 | 16 | 10 |
| 2 | 4,5 | 0,5 | 2/1 | 0,15 | 0,4 | 0,4 | 0,4 | 103 | 78 | 0 | 0,33 | 17 | 10 |
| 3 | 3 | 0,35 | 2/1 | 0,15 | 0,3 | 0,4 | 0,4 | 103 | 78 | 0 | 0,33 | 17 | 10 |
| 4 | 4,5 | 0,35 | 2/1 | 0,10 | 0,3 | 0,4 | 0,6 | 103 | 81 | 0 | 0,33 | 17 | 10 |
| 5 | 4,5 | 0,35 | 5/2 | 0,10 | 0,3 | 0,3 | 0,4 | 81 | 58 | 2 | 0,33 | 16 | 10 |
| 6 | 4,5 | 0,5 | 5/2 | 0,10 | 0,4 | 0,4 | 0,6 | 82 | 58 | 0 | 0,33 | 16 | 10 |
| 7 | 3 | 0,5 | 5/2 | 0,15 | 0,3 | 0,3 | 0,6 | 81 | 61 | 2 | 0,33 | 14 | 10 |
| 8 | 3 | 0,5 | 2/1 | 0,10 | 0,4 | 0,3 | 0,4 | 105 | 74 | 1 | 0,33 | 15 | 10 |
| 9 | 3 | 0,35 | 5/2 | 0,15 | 0,4 | 0,4 | 0,6 | 82 | 58 | 0 | 0,33 | 16 | 10 |
| 10 | 4,5 | 0,5 | 2/1 | 0,15 | 0,3 | 0,3 | 0,6 | 109 | 77 | 1 | 0,33 | 15 | 10 |
| 11 | 3 | 0,35 | 2/1 | 0,10 | 0,4 | 0,3 | 0,6 | 108 | 76 | 1 | 0,33 | 15 | 10 |
| 12 | 3 | 0,5 | 5/2 | 0,10 | 0,3 | 0,4 | 0,4 | 82 | 56 | 0 | 0,33 | 16 | 10 |

Effets (haut moins bas, `doe.py analyser`) : **départs/front 2/1 : +23,7 notes h6 (p = 5.10^-5) et +19,2 en LARGE (p = 6.10^-5)** ; `REESSAI_S` 0,3 : +1,5 « sûr » faux (p = 8.10^-4, les 2 faux viennent des prises H6 réelles, `usage_reel`) et -1 à -2 notes du H6 réel x1 ; tout le reste |effet| <= 1,7 note, sans effet sur le retard (0,33 s partout) ni sur H6 x4 (10 partout). Les facteurs sans effet restent à leur valeur de la v68. **Retenu : `NDEPARTS` 2, `JOBS_MAX` 1, `ETIQ_COH_C` 3 (inchangé)**. C'est le « +18 % refusé en v68 » : la garde d'étiquette `ETIQ_COH_C` qui manquait alors est là. **Confirmation** (hypercube4 = `lhs300_calib`, 4 graines neuves à partir de 33, trois synthèses = 3 600 notes, `doe/conf/B.txt`) : h6 427 posées sur 1 200 (35,6 %), 0 faux, max 0,349 ¢ ; LARGE 321 (26,8 %), 0 faux, max 0,329 ¢ ; ancienne 547 (45,6 %), 0 faux, max 0,380 ¢. C'est là que la v68 avait trouvé le -21,5 ¢ : il n'est pas revenu.

Sur une machine lente, le mode léger de la v68 (`MS_LENT`, mêmes 2 départs et 1 front, 8 itérations) reste ; la v69 rend ces 2/1 à toutes les machines et garde 15 itérations sur les rapides. Coût : image médiane 6,7 -> 11,2 ms (H6 réel x1), p99 433 -> 674 ms, T médian 4,7 -> 5,1 s (moins de calcul par note, mais plus d'ajustements gagnés), part du temps certifiée 7 -> 6 %.

**I3 : plan 2^2 complet** (`SENT_KMIN` 1 ; 3 x `SENT_FEN_BAT` 0 ; 0,7), jeu neuf `adverses/D4.csv` : **80 notes** (hypercube latin, graine 69, Ω de 0,5 à 1,0 Hz, f0 200-900 Hz, saut de 2 à 4,5 ¢ à **t = 6,5 s** et non 3 s : à 3 s, 2 notes sur 40 étaient posées, Ω lent exigeant au moins 2 battements entiers, la mesure du retard n'avait rien à mesurer), h6 et LARGE, Worker simulé x1 et x4, 2 graines ; plus D3 h6 et H6 réel x1.

| `SENT_KMIN` ; `SENT_FEN_BAT` | retard p90 D4 h6 x1 / LARGE x1 / h6 x4 / LARGE x4 (s) | exposition (images sûres à plus de 0,5 ¢ de la hauteur de l'instant) h6 x1 / LARGE x1 | D3 h6 : p90, exposition | posées D4 h6 x1 | H6 x1 |
|---|---|---|---|---|---|
| **1 ; 0,7 (v68, retenu)** | **0,33 / 0,41 / 0,33 / 0,33** | **13 / 8** | 0,33 s, 1 | 101 | 16, 7 % |
| 3 ; 0,7 | 0,58 / 0,58 / 0,41 / 0,50 | 63 / 39 | 0,33 s, 3 | 104 | 16, 6 % |
| 1 ; 0 | 0,58 / 0,50 / 0,41 / 0,24 | 50 / 18 | 0,38 s, 0 | 101 | 16, 7 % |
| 3 ; 0 | 0,67 / 0,84 / 0,67 / 0,58 | 98 / 89 | 0,38 s, 5 | 105 | 16, 8 % |

0 « sûr » faux dans les 4 x (4 x 160 + 60) notes. Lecture physique : sur les partiels 3 et 4, plus faibles, le warp (dérive et niveau) n'est plus calé par les bas partiels, et le rang bas qui dit « la note a bougé » est supprimé ; `SENT_KMIN` 3 allonge le retard au lieu de le raccourcir. L'hypothèse de l'audit est réfutée ; `SENT_KMIN` (code gardé, valeur 1) et `SENT_KMIN_OMEGA` restent des options éteintes. (Le critère de l'audit « part du temps certifiée >= 7 % » est de toute façon à 6-7 %.)

### 0C.3 I1 : le diagnostic des graves (`test/outils/pose/diag_graves.mjs`)

Dix notes graves perdues (`notes_perdues_gagnees.csv`, cause `grave<150+resolution`, plans 71, 120, 132, 138, 140, 149, 154, 176, 208, 214 de `lhs300_calib`, synthèse h6), fenêtre 350/f0 s finissant à 8 s, modèle structuré avec et sans raie étrangère libre, partiels forcés à 4 :

| | partiel 1 | partiel 2 | partiel 3 | partiel 4 |
|---|---|---|---|---|
| résidu relatif médian SANS raie étrangère | 0,021 | 0,026 | 0,014 | 0,013 |
| résidu relatif médian AVEC raie étrangère | 0,007 | 0,011 | 0,005 | 0,005 |

Le modèle décrit donc très bien le 3e partiel (résidu relatif < 2 %) ; la raie étrangère adoptée est résolue au partiel 3 sur les dix notes (3 x delta contre 1,2/T : 0 note sur 10 non résolue). **Ce qui ramène K_utile à 2 est ailleurs** : `nls-bessel.js` compare les hypothèses d'étiquette sur « les partiels que TOUTES savent décrire » (`kC = min` des K_utile de toutes les hypothèses). Une hypothèse à mauvaise étiquette (décalée d'un battement, p. ex. 117,78 Hz au lieu de 116,03 Hz) ne décrit pas le 3e partiel (résidu relatif 0,80 à 0,95, contre 0,007 pour la bonne) : son K_utile est 2 et il ramène la MEILLEURE à 2 partiels, donc à une précision et à un `Ku` plus faibles, donc à `KU_SUR_MIN_GRAVE` : refus `resolution`. Avec `kcMax` (comparaison sur les partiels de la plus riche) les dix notes ont K_utile 4. Deux remèdes ont été jugés sur les mêmes graines (plan à 3 graines, 4 jeux) :

| remède | posées (4 jeux) | graves posées | décision |
|---|---|---|---|
| aucun, (120 ; 3) | 313 | 29 | **retenu** |
| `KC_MAX` (toutes les hypothèses jugées sur les partiels de la plus riche), cellule (150 ; 3) | 234 (contre 296 sans, mêmes graines, cellule (150 ; 3)) | 29 contre 12 | **refusé** : lhs300 h6 186 contre 247 (-25 %) ; l'hypothèse juste, qui n'a que 2 partiels, est jugée sur ceux qu'elle ne décrit pas |
| `KC_PROPRE` (l'étiquette se juge sur les partiels communs, le gagnant est ensuite réajusté sur les siens), cellule (120 ; 3) | 301 | 45 contre 29 | **refusé** : -4 % posées (lhs300 245 contre 256), +55 % de graves ; gain sur un seul registre, que l'audit demande de ne pas régler sur la synthèse seule (aucune note réelle sous 207 Hz) |

Les deux options restent dans le code, éteintes. **La question reste ouverte pour l'audit n° 6** : un 16' réel (geste d'Ewen) dira si le 3e partiel des anches graves est réellement décrit par le modèle, ce que la synthèse suppose.


### 0C.4 I4 : la prise (contrôle de prise, `dsp/prise.js`)

**(a) `gate` ne prend plus un convertisseur de 16 bits dans une pièce calme pour une porte.** Cause (reproduite sur `J:\claude\tmp\v69\wav\propre.wav`, la prise H6 de l'essai 1 réécrite en 16 bits par `chaines.py`) : un bruit de fond passe-bas dont l'écart type est de l'ordre de 1 LSB (-90 dBFS) donne des plages de zéros exacts de 1 à 25 ms PARTOUT, entre les notes comme sous elles ; la règle `gateZeroPart` (une plage ne compte pas si les zéros font plus de 60 % de son bloc de 100 ms) ne les écarte pas. Une porte réelle, elle, ferme sur un son : la plage de zéros commence juste après lui. Règle ajoutée (`gateVoisinDb`, -60 dBFS) : une plage de zéros ne compte que si le bloc de 100 ms qui la porte, le précédent ou le suivant dépasse ce niveau.

Plan 2^3 complet (graine 69, `doe.py`), réponses : secondes douteuses (`prise_wav.mjs`, sans moteur) sur la prise H6 réécrite en 16 bits propre et traitée (bande 300-3 400 Hz, suppression spectrale, les deux avec compresseur) et, pour les quatre sessions traitées par Windows (11/10, 13/10, 14/10 x2), le NOMBRE MINIMAL de secondes douteuses par le seul code `gate` (le contrôle doit rester sûr de lui sur une prise vraiment traitée) :

| cellule | `gateVoisinDb` | `gateEvents` | `gateZeroPart` | propre | bande | suppression | tout | sessions, gate (min) |
|---|---|---|---|---|---|---|---|---|
| 1 | -70 | 5 | 0,3 | 0 | 43 | 59 | 78 | 16 |
| 2 | -50 | 5 | 0,3 | 0 | 43 | 0 | 0 | 0 |
| 3 | -70 | 10 | 0,3 | 0 | 0 | 57 | 46 | 1 |
| 4 | -50 | 10 | 0,3 | 0 | 0 | 0 | 0 | 0 |
| 5 | -70 | 5 | 0,6 | 0 | 171 | 179 | 140 | 115 |
| 6 | -50 | 5 | 0,6 | 0 | 121 | 160 | 117 | 108 |
| 7 | -70 | 10 | 0,6 | 0 | 130 | 106 | 138 | 108 |
| 8 | -50 | 10 | 0,6 | 0 | 71 | 47 | 116 | 9 |

Lecture : `gateZeroPart` 0,3 tue la détection d'une vraie suppression (suppression 160 -> 0 s, sessions 108 -> 0 s) : refusé. `gateEvents` 10 ne gagne que sur la bande, au prix de la suppression : refusé. `gateVoisinDb` -70 -> -50 enlève la moitié des fausses alarmes de la bande (171 -> 121) sans perdre les sessions : retenu au milieu, -60, mesuré à part sur les mêmes chaînes : propre **0** s sur 211 (65 avant), suppression **168** s (191 avant), tout 132 s (144), bande 121 s (178). **Le critère « bande <= 10 s » de l'audit n'est PAS tenu** et ne peut pas l'être par ce détecteur : une bande étroite 300-3 400 Hz de la même pièce calme, en 16 bits, produit des plages de zéros collées aux notes comme une suppression de bruit (aucune cellule du plan ne donne à la fois suppression >= 150 s et bande <= 10 s). Ce n'est pas une erreur grave : les lectures « sûr » restent justes sous cette chaîne (0 faux sur 50 posées, max 0,28 ¢), le contrôle ne fait que refuser des notes en trop. Limite écrite : un convertisseur dont le bruit est sous 1 LSB (-93 dBFS et moins, `bruitDb -95`) reste pris pour une porte ; les micros USB ordinaires ont un bruit propre bien au-dessus.

Tests (`test/prise.test.mjs`, `synthese-prise.mjs` : `bruitFc` bruit passe-bas, `coupure` porte réelle) : 16 bits, plancher -80, -85, -90 et -92 dBFS sans porte : aucune alerte ; porte réelle à -45 dBFS (zéros exacts dès 100 ms sous le niveau, battant 300 ms) à -80, -85 et -90 dBFS : alerte `gate`.

**(b) L'échelle de la prise par le secteur.** Une prise rééchantillonnée ou transposée (la prise PC du 14/10 : +5 ¢, 6 « sûr » faux sur 6) n'a aucune signature dans le son de l'instrument, mais le ronflement du secteur (50 ou 60 Hz, ±0,1 % en régime normal) en est une référence EXTERNE : il se déplace de la même échelle. `prise.js` garde la fréquence affinée de chaque fenêtre de 2 s où la raie est présente (`affinerSecteur`, 0,01 Hz), prend la MÉDIANE sur 90 s (une fenêtre où une note accroche la recherche donne 49,80 au lieu de 50,15 : trois sur 31 sur les notes de synthèse) et, à partir de 25 fenêtres (50 s de ronflement), dit : alerte `echelle` (prise douteuse, « la prise est transposée de x ¢ ») si |f / f nominale - 1| > 2 ‰ (3,5 ¢) ; entre 1 et 2 ‰, information `echelleAvert` sans refus. Mesuré sur des notes de synthèse : +5 ¢ avec ronflement à -50 dBFS : 5,2 ¢ lus, alerte datée à 2 s (première fenêtre de ronflement) ; le ronflement le plus faible vu est celui dont la crête (après Hann : la moitié de l'amplitude) est à -85 dBFS, soit -79 dBFS d'amplitude. Fausses alarmes : réseau à 49,96 et 50,04 Hz (±0,08 %) : aucune ; 50,2 Hz (incident, 4 ‰) : alerte, ce qui est voulu (la prise est vraiment décalée de 6,9 ¢). **Limite : sans ronflement, une prise transposée ne se voit pas** (le la de référence en tête de session reste le seul autre témoin, geste d'Ewen).

**(c) Chaînes de micro dans la CI** (`test/prise-chaines.test.mjs`) : 8 notes de `lhs64_valid` que l'ancienne synthèse pose sans chaîne (graine 70) x {compresseur, bande 100-8 000 Hz, suppression spectrale, porte à zéros} : 0 lecture « sûre » fausse, aucune erreur ; puis une prise de 63 s (7 rendus d'une même note, ronflement à -50 dBFS, +5 ¢ de rééchantillonnage, horloge dite exacte) : alerte `echelle` datée à 2,0 s, et toutes les images « sûres » (8) sont dans l'épisode.

**(d) Écran** : `prise-micro.js` écrit le code `echelle` (titre, texte avec la transposition en ¢ et la fréquence lue du secteur, geste : désactiver les améliorations audio), la mention courte « prise transposée » et l'avertissement `echelleAvert`.

### 0C.5 I5 : la vitesse de calcul de la machine, dans la session

`worker.js` : `msFroid` (durée moyenne d'un ajustement à froid, ms), `lente` (le mode léger de la v68 est en route) et `dspMs` (temps de calcul par image de 85 ms : nombre, médiane, p99 sur les 8 000 dernières images) vont dans le bloc `prise.calcul` du dernier morceau de la session ; `app.js` les écrit en tête du JSON (`calcul`, par `session-format.js:blocCalcul`) ; la bande d'expert (mode luthier) montre « calcul 340 ms » ou « calcul 1 400 ms (léger) » (`expert.js`, textes en français et en anglais). Tests : `session.test.mjs` (champs présents, rien d'inventé sans mesure), `anche.test.mjs` (texte). **Aucune valeur n'est décidée en v69** : le geste d'Ewen est d'ouvrir l'accordeur sur son Android, de jouer 12 notes MM et d'exporter la session ; `calcul.msFroid` donne le vrai facteur (aujourd'hui l'hypothèse x4 = 1 400 ms) et décide de `MS_LENT` en v70. La décimation après le premier étage existe déjà (CIC3, `nls-bessel.js`, `demodPartiel`) : le levier qui reste est le nombre de départs.

### 0C.6 I6 : super musette, diagnostic avant tout modèle

Pas de modèle `struct` à trois anches en v69. `test/outils/pose/trio_diag.mjs` : pour chaque WAV, la vérité à trois anches (`corpus_verite.mjs`, somme de sinusoïdes : les trois fréquences, leurs σ, les niveaux relatifs, niveau et phase des partiels 1 à 3 de chaque anche), puis ce que le moteur lit en MMM (trois voix de la dernière image, écart à la vérité la plus proche, raisons de refus sur les 20 dernières images). Sur les cinq notes de Serafini md à trois anches équilibrées (écarts < 3 dB) :

| fichier | note | trois fréquences de vérité (Hz) | niveaux (dB) | lecture MMM non certifiée : écart à la vérité (¢) | raisons de refus |
|---|---|---|---|---|---|
| 13-BR | Si3 | 246,020 / 247,688 / 248,515 | -1,6 / 0 / -0,3 | +0,13 / -0,24 / -0,02 | vérification, stabilité, lent |
| 18-ER | Mi4 | 328,381 / 329,517 / 330,358 | 0 / -2,6 / -0,2 | -0,22 / -0,22 / -0,11 | résolution, peigne |
| 19-FR | Fa4 | 348,316 / 349,312 / 350,826 | -1,6 / 0 / -2,2 | +0,15 / -0,42 / +0,17 | stabilité, peigne |
| 25-BR | Si4 | 494,156 / 494,647 / 495,558 | 0 / -0,2 / -3,1 | +0,33 / -0,62 / -1,15 | lent, accordées |
| 37-BR | Si5 | 987,850 / 988,663 / 990,471 | -3,8 / 0 / -2,7 | -1,59 / +0,03 / -1,18 | peigne, ident3, lent |

Ce que cela dit : le traqueur trouve les trois anches à 0,1-0,4 ¢ près sur les trois premières notes (écarts de 1 à 2,5 Hz, bien résolus) et se trompe de 0,6-1,6 ¢ sur les deux dernières (écarts de 0,5 Hz à 494 Hz, 0,8 Hz à 988 Hz) ; le certificat ne pose jamais, pour des raisons différentes selon la note (pas d'une seule cause à corriger par un modèle). Les partiels 2 sont à -13/-28 dB sous le 1 et le partiel 3 à -5/-12 dB : le spectre n'est pas celui d'une anche seule par voix (le 3e partiel est plus fort que le 2e, signature d'un son échantillonné de plusieurs anches ou d'un timbre propre à l'instrument). Avant de modéliser : 12 notes MMM propres au H6 (geste d'Ewen).

### 0C.7 I7 : le banc et la CI

1. **Vérité unifiée** : `eval63.mjs` / `verdict.mjs` jugent toute lecture « sûre » contre la fenêtre que le certificat a lue (`errFen`), pas seulement sur les plans à saut ; la moyenne des 3 dernières secondes reste en colonne « v67 » du verdict (`faux67`, `errMax67`) pour comparer aux passes d'avant. Conséquence : sur les mêmes graines, la v68 n'a plus « zéro faux » (une note, voir le tableau de bord).
2. **Passes gardées** : `J:\claude\tmp\v69\final\v68\` et `...\v69\` (tous les JSON), archive `J:\claude\audits\donnees-accordeur\passes\v69.zip`.
3. **Déterminisme** (`pose-ci.test.mjs`) : les deux notes-pièges (`lent100` plan 82 graine 32 LARGE, `lhs300_calib` plan 91 graine 32 h6) jouées deux fois ont des JSON identiques à l'octet.
4. **Lot « objectif graves »** (`ci_seuils.json`) : les 40 lignes de `gen160b_v68` sous 150 Hz, synthèse h6, graine 50 : 0 faux, au moins 2 posées (le résultat mesuré est 2 : la consigne demande `résultat - 1` avec un plancher de 2).
5. **Gardes mortes retirées de `certificat.js`** : `DERIVE_FIT` (la variante stricte ; `DERIVE_FIT_SEUIL` 1,2 reste), `CONFIRME_SENT` et tout ce qui en dépendait (`enAttente`, `sentFlou`, `CONF_FEN_BAT`, `CONF_SENT_SIGMA_MAX`), `SENT_ADAPT`, `KU_LIBRE_MIN`, `DEPUIS_SENT`, `BETA_FORT`, `LLR_BETA_FORT`, `M_FORT`, `CONFIRME_MOITIE_FORT_C`, `ACCORD_SUR_C`, `ACCORD_C`, `SIGMA_TOL_C`, `X_MAX_AM`, `FENETRE_ADAPTIVE`. Gardées : `PRESENT` (éteinte, à rejuger avec la vérité unifiée), `KU_LIBRE_GRAVE`. Les deux tests qui exerçaient `ACCORD_C` et `DERIVE_FIT: true` sont remplacés par la preuve que ces réglages n'existent plus (la fonctionnalité est retirée, le test avec elle). Preuve que rien n'a bougé : `lhs64_valid` h6 graine 30, 2 répétitions, 128 notes, code de la v68 contre code sans les gardes mortes : 38 posées, 249 lectures sûres, 0 faux, identiques. Leur histoire reste dans les sections 0B et 0A.

### 0C.8 I8 : la généralisation du corpus, contre une vérité indépendante

`test/outils/pose/corpus_verite.mjs` porte `verite_sinus.py` (somme de sinusoïdes, 3 partiels par anche, amplitudes projetées, Levenberg-Marquardt sur les fréquences) ; `corpus_ecarts.mjs` donne, par voix « sûr », l'écart en cents à l'anche la plus proche de la vérité ; `corpus-sf2.test.mjs` exige 0,3 ¢ au plus. Le port et l'original Python diffèrent de 0,02 à 0,07 ¢ sur la même note (la σ annoncée, 0,001 ¢, ne vaut que pour la méthode, pas pour sa reproductibilité : c'est l'incertitude de la vérité). Résultat v69 : Serafini md, MM, 3 notes « sûr » (6 voix), écart maximal 0,213 ¢ (v68 recompté : 2 notes, 4 voix, 0,083 ¢) ; MMM, Gaillard md, les basses (Serafini, Gaillard main gauche, mode auto) : 0 note « sûr » avant comme après, 0 erreur. La 3e note « sûr » de la v69 est Ré3 (147 Hz, deux anches à 146,97 et 147,92 Hz), que la v67 posait et que la v68 refusait : la borne à 120 Hz la rend, juste à 0,2 ¢. sfArk : `web\soni-musicae-diato` reste à extraire par Polyphone (geste d'Ewen).

### 0C.9 Prise traitée et robustesse (passes finales, sessions du 11, 13 et 14/10)

Avec le contrôle de prise : 0 note « sûr » sur les quatre sessions traitées (v68 : 0, v69 : 0) ; lectures « sûr » refusées par le contrôle : v68 26, 250, 100, 26 -> v69 22, 224, 78, 26 (la fausse alarme 16 bits est corrigée, ces sessions restent douteuses par le ronflement et les zéros). Prise PC du 14/10 (`reel_prises --src=pc`) : 0 posée, 0 faux. Sans contrôle, ces sessions donnent des « sûr » (robustesse seulement, jamais une preuve). Prises H6 (`reel_prises`, budget déterministe) : somme L+R 10 -> 16 notes, voie gauche 11 -> 14, droite 9 -> 13, 0 lecture sûre fausse (49, 78, 68 lectures). Téléphone (Worker simulé, H6 essai 1) : x1 16 -> 17, x2 11 -> 12, x4 10 -> 10, x8 2 -> 2 ; essai 2 x1 4 -> 5, x4 3 -> 3 ; 0 faux partout.

### 0C.10 Ce qui reste pour un niveau professionnel

1. **Un « sûr » faux antérieur, trouvé par la vérité unifiée** : la note de `hypercube4` (graine 43, f0 164 Hz, Ω 1,21 Hz, anche faible à 17,8 dB, raie étrangère à -15 dB) lue à -0,56 ¢ par la v68 comme par la v69. Mécanisme probable : l'anche faible entraînée par la raie étrangère à 0,15-0,5 Hz, qui n'est pas résolue à 2 partiels. Pas de garde sans plan (I9) : audit n° 6.
2. **Le modèle** : 2 partiels décrits sur 4 pour les graves, à cause de la comparaison d'étiquettes (0C.3), pas du modèle de la meilleure hypothèse ; trio sans physique mesurée (0C.6) ; taux de pose 23 % en LARGE, 30 % en h6, 5 % à physique et conditions très larges.
3. **Les enregistrements d'Ewen** (rien n'est prouvé hors du H6 sans eux) : 16' du Do2 au Do4 (lève I1), MMM 12 notes (I6), micro USB 16 bits et téléphone Android simultanés au H6 (I4, I5), un deuxième accordéon MM (seuils d'Ω), la session Android avec `calcul` (I5).
4. **Échelle sans ronflement** : une prise transposée sans secteur ne se voit toujours pas ; le la de référence en tête de session reste à écrire.

## 0B. La v68 (audit Fable n° 4 du 18/10/2026) : la généralisation hors du Zoom H6, mesurée et bornée

Audit : `J:\claude\audits\2026-10-18-accordeur-fable-4\RAPPORT-AUDIT-4.md` (H1 à H9, consigne § 9), résumé des plans `DOE-RESUME.md`. Verdict de l'audit sur la v67 : zéro lecture fausse au sens strict sur ~12 000 lectures de synthèse, mais « niveau pro » non atteint à l'établi et non prouvé hors du Zoom H6 (3 % de notes posées à physique large, 14 % à conditions modérées, 0 % en 16', en 4' aigu, sous 0,8 Hz et avec un micro USB à gain automatique). La v68 applique les recommandations qui se règlent par le code et les plans ; celles qui demandent des enregistrements (H8) ne sont pas faisables sans Ewen.

**Ce que cette version ne prouve toujours pas.** Les seuils et les gardes sont réglés sur la synthèse (`SYNTH=h6`, `SYNTH=large`) et sur UN instrument (le H6 d'Ewen, 27 notes). Un « zéro faux » de banc vaut « zéro faux sur ces graines, ce jour » (le banc est déterministe à une note près par millier). Les enregistrements du § 7 de l'audit (autres registres, autres instruments, micros, limage, soupape qui fuit) sont la seule façon de dire « pro sur tous les accordéons ».

### 0B.0 Trois corrections de mesure faites avant de régler quoi que ce soit

1. **La vérité des plans à saut de hauteur était fausse pendant 3 s.** Elle était la moyenne de la porteuse sur les 3 dernières secondes : après un saut de 4 ¢, elle ment de 0,5 ¢ pendant 0,33 s puis de plus, alors que la valeur certifiée est (à raison) la moyenne de SA fenêtre. Sur les plans à saut (`sautT`), `eval63.mjs` garde maintenant `errFen` (erreur à la moyenne de la fenêtre lue par le certificat, milieu ± T/2 : le biais du modèle, sans le retard), et `errNow` (erreur à la hauteur de l'instant, porteuse moyennée sur 0,4 s). Les « faux » de la v67 qui restaient en D3 plans 19, 27 et 12 et les deux « straddle » trouvés en cours de route (D3 h6, plan 1 rep 31 et plan 9 rep 30) disparaissent avec la bonne vérité : ils n'étaient pas des erreurs du modèle mais une vérité décalée. Les autres plans gardent la vérité d'avant (les chiffres restent comparables à ceux de la v67).
2. **Le retard est une grandeur, pas une fausse lecture.** `verdict.mjs` mesure, pour les notes sûres avant un saut d'au moins 1 ¢ (`SAUT_MIN_C` : en dessous l'ancienne valeur reste juste à 0,5 ¢ près), le délai jusqu'à la première image non sûre (médiane, p90) et l'**exposition** : les images « sûres » à plus de `RETARD_S` = 0,35 s du saut dont l'erreur à la hauteur de l'instant dépasse 0,5 ¢. `eval63.mjs` lit CHAQUE image (85 ms) autour du saut, plus la grille de 0,25 s (qui masquait des images fausses d'une seule image).
3. **Le banc peut tourner comme l'application.** `CPUX=1|4` (variable d'environnement de `eval63.mjs`) met le certificat dans un `ExecutantSimule` (Worker simulé sur l'horloge du son, 1 ou 4 fois plus lent que le PC de l'audit) au lieu du calcul en ligne à budget déterministe. Le retard après un saut y est plus grand (p90 0,41 s au lieu de 0,32 s sur D3 ancienne) : c'est lui qui compte pour l'application.


### 0B.1 Ce qui est fait, partiel, refusé

| H | Sujet | Statut | Résultat |
|---|---|---|---|
| H1 | gardes contre la lecture sur moins d'un battement mesuré | **fait, en partie autrement** | `NB_MIN_POST` 1 retenu (B plan 33 tombe, coût nul sur le H6) ; `DERIVE_FIT` tel que proposé **refusé** (-3,8 notes du H6 : la dérive de l'ajustement suit la modulation du battement) et remplacé par `DERIVE_FIT_SEUIL` 1,2 ¢/s (coût nul) |
| H2 | retard après un saut : grandeur mesurée, bornée, compensée | **fait, en partie** | métrique (médiane, p90, exposition) et vérité alignée sur la fenêtre lue ; sentinelle prioritaire, moins chère, plus fréquente, fenêtre ≥ 0,7 battement : p90 dans le Worker simulé ×1 0,41 -> 0,32 s (ancienne), exposition 5 -> 1 images ; **(d) valeur ramenée à l'instant : implémentée (`PRESENT`), sans effet mesuré sur 160 notes, éteinte** ; la cible p90 ≤ 0,35 s est tenue en ×1 (0,32 / 0,33 / 0,39 en ancienne / H6 / LARGE : LARGE un peu au-dessus), pas en ×4 (0,38 à 0,39) |
| H3 | graves : 3 partiels exigés sous 150 Hz | **fait, au prix de notes** | `KU_SUR_MIN_GRAVE` 3 : le faux de `lent100` plan 82 est fermé, H6 réel inchangé ; mais -7 notes sur 89 de la synthèse H6 (`lhs300_calib`, graine 30) : ce sont les graves à raie étrangère adoptée avec 2 partiels (variante ciblée : mêmes chiffres) |
| H4 | téléphone | **fait, réservé aux machines lentes** | H6 réel ×4 : 1 -> 10 notes sur 27 ; ×2 : 7 -> 11 ; ×1 inchangé (16). 2 départs et un seul ajustement de front sur machine rapide **refusés** (une mauvaise étiquette posée à -21,5 ¢) |
| H5 | domaine annoncé et banc CI | **fait** | § 0B.5 ; seuil de la validation 16 -> 12 notes posées, écrit et justifié |
| H6 | super musette : modèle `struct` | **non fait, reporté (v69)** | aucune mesure de super musette avec vérité (la banque Serafini n'en a pas : 0 note posée sur 24 en MMM, avant comme après) ; écrire la physique du trio sans elle serait inventer |
| H7 | prise traitée : le contrôle de prise comme barrière testée | **fait** | § 0B.4 |
| H8 | enregistrements d'Ewen | **non fait (gestes d'Ewen)** | liste dans l'audit n° 4 § 7 et dans les gestes de Wenou OS |
| H9 | battement doublé de la thèse (F10) | **fait** | § 0B.3 |

Trouvé en cours de route : **une mauvaise étiquette posée « sûre » à -21,5 ¢** (§ 0B.2, `ETIQ_COH_C`) et **le simulateur du Worker à deux cœurs** (§ 0B.2, H4). Les deux « faux » restants de la v67 en D3 (0,51 à 0,72 ¢) étaient une vérité décalée (§ 0B.0).

### 0B.2 Plans d'expériences (règle 12 : jamais un facteur à la fois)

**Plan H2 : PB12 sur la sentinelle et les gardes** (`doe.py plan --type pb`, graine 68, 8 facteurs, 12 cellules, la cellule 12 est la v67). Jeux par cellule : D3 ancienne synthèse (60 notes, graines 30-31), D3 `SYNTH=h6` (60), validation LARGE (64, graine 70), H6 réel ×1 (27 notes, `usage_reel`). Effets (moyenne haut moins bas ; vérité de ce plan : l'ancienne, moyenne des 3 dernières secondes, voir § 0B.0) :

| facteur (bas ; haut) | H6 posées /27 | D3 anc. posées | D3 h6 posées | validation posées /64 | retard p90 D3 anc. (s) | retard p90 D3 h6 (s) | décision |
|---|---|---|---|---|---|---|---|
| `NB_MIN_POST` 0 ; 1 | -0,2 | +0,3 | -0,2 | +0,3 | +0,01 | +0,05 | **retenu** (ferme B plan 33 sans coût) |
| `DERIVE_FIT` non ; oui | **-3,8** | -0,3 | +0,5 | -0,3 | -0,01 | +0,07 | **refusé tel quel** (la dérive de l'ajustement suit la modulation du battement : médiane 0,3 ¢/s, p90 1,0 sur les ajustements du H6 qui passent) ; remplacé par `DERIVE_FIT_SEUIL` 1,2 |
| `KU_SUR_MIN_GRAVE` 0 ; 3 | -0,5 | -1,7 | -3,2 | 0,0 | -0,01 | +0,01 | voir plan H3 |
| `SENT_PRIO` non ; oui | +0,5 | +1,0 | +0,2 | 0,0 | **-0,06** | **-0,10** | **retenu** (la sentinelle passe avant les ajustements principaux dans le calcul en ligne, comme dans le Worker) |
| `CONFIRME_SENT` non ; oui | **-5,8** | **-4,3** | **-5,5** | **-2,3** | +0,04 | -0,02 | **refusé** (une première pose confirmée par une sentinelle : -6 notes du H6 pour un problème qui, mesuré avec la bonne vérité, n'existe pas) |
| `SENT_PERIODE_S` 0,15 ; 0,30 | +0,5 | +0,7 | +0,2 | 0,0 | **+0,18** | +0,09 | 0,15 gardé |
| `SENT_FEN_S` 0,6 ; 0,45 | +0,2 | -1,0 | +0,2 | +0,7 | +0,10 | +0,03 | 0,6 gardé |
| `SENT_ADAPT` 0 ; 2 | -0,5 | -1,3 | -0,2 | 0,0 | +0,04 | -0,02 | **refusé** (la période adaptée au coût allonge le retard ; dans le Worker la période est déjà bornée par la durée de la sentinelle en vol) |

Aucune cellule ne donne de lecture « sûre » fausse sur le H6 réel ; la cellule 12 (v67) donne 16/27, comme avant.

**Plan H3 : 2^3 complet sur les graves** (graine 681 ; `KU_SUR_MIN_GRAVE` 0 ; 3, `KU_LIBRE_MIN` 0 ; 3, `FEN_F0_S` 350 ; 500). Jeux par cellule : `lent100` LARGE (100 notes, graine 32, dont le faux de 0,53 ¢ du plan 82), les 40 notes graves (f0 < 150 Hz) de `gen160b_v68` en LARGE et en H6 (80 notes chacun, graines 50-51), H6 réel ×1. La cellule 1 est la v67.

| cellule | `KU_SUR_MIN_GRAVE` | `KU_LIBRE_MIN` | `FEN_F0_S` | lent100 posées / faux | graves LARGE | graves H6 | H6 réel /27 |
|---|---|---|---|---|---|---|---|
| 1 (v67) | 0 | 0 | 350 | 14 / **1** | 2 | 6 | 16 |
| 2 | **3** | 0 | 350 | **11 / 0** | 1 | 0 | **16** |
| 3 | 0 | 3 | 350 | 7 / 0 | 1 | 0 | 7 |
| 4 | 3 | 3 | 350 | 7 / 0 | 1 | 0 | 7 |
| 5 | 0 | 0 | 500 | 10 / 0 | 0 | 0 | 15 |
| 6 | 3 | 0 | 500 | 10 / 0 | 0 | 0 | 15 |
| 7 | 0 | 3 | 500 | 5 / 0 | 0 | 0 | 10 |
| 8 | 3 | 3 | 500 | 5 / 0 | 0 | 0 | 10 |

Retenu : la cellule 2, `KU_SUR_MIN_GRAVE` 3 (H3 de l'audit tel quel) : le faux de `lent100` plan 82 est fermé, le H6 réel ne perd rien (16/27), `lent100` perd 3 notes sur 100 et les graves de synthèse H6 que la v67 posait (6 sur 80) sont refusés : d'après la variante ciblée ci-dessous, c'étaient des lectures à raie étrangère adoptée avec 2 partiels, du même genre que le faux. `KU_LIBRE_MIN` (la même règle à toute hauteur, dès qu'une raie étrangère est adoptée) coûte 5 à 9 notes du H6 : refusé. `FEN_F0_S` 500 coûte 1 note du H6 et 4 de `lent100` sans rien de plus : refusé. Variante ciblée (`KU_LIBRE_GRAVE` : raie étrangère adoptée ET f0 < 150 Hz ET moins de 3 partiels) : mêmes chiffres que la cellule 2 (H6 16/27, `lent100` 11 / 0), gardée comme option éteinte. Le test F 11 (midi 48, 130 Hz, Δ = 1,5 Hz : ce timbre de synthèse n'offre que 2 partiels au-dessus du bruit) ne demande plus que « jamais faux, jamais avant l'heure, la raison est affichée » pour les notes sous 150 Hz.

**Plan H4 : 2^3 complet sur le calcul du téléphone** (graine 683 ; `NDEPARTS` 5 ; 2, `ITER` 15 ; 8, `JOBS_MAX` 2 ; 1 ; la cellule 1 est la v67 avec les sentinelles de la v68). Réponses : notes posées sur le H6 réel (essai 1 ×1 et ×4, essai 2 ×4), sauts D3 `SYNTH=h6` ×1 et ancienne ×4 (Worker simulé), validation LARGE ×1.

| cellule | `NDEPARTS` | `ITER` | `JOBS_MAX` | H6 ×1 /27 | H6 ×4 /27 | essai 2 ×4 /12 | D3 H6 ×1 | D3 anc. ×4 | validation LARGE ×1 |
|---|---|---|---|---|---|---|---|---|---|
| 1 (v67) | 5 | 15 | 2 | 16 | **0** | 1 | 31 | 20 | 16 |
| 2 | 2 | 15 | 2 | 15 | 6 | 3 | 35 | 26 | 20 |
| 3 | 5 | 8 | 2 | 15 | 4 | 2 | 34 | 18 | 16 |
| 4 | 2 | 8 | 2 | 14 | 8 | 3 | 35 | 24 | 19 |
| 5 | 5 | 15 | 1 | 15 | 5 | 3 | 35 | 24 | 19 |
| 6 | 2 | 15 | 1 | **17** | 6 | 3 | 37 | 32 | 22 |
| 7 | 5 | 8 | 1 | 16 | 5 | 4 | 36 | 22 | 23 |
| 8 (cellule de l'audit) | 2 | 8 | 1 | 15 | **10** | 3 | 36 | 29 | 21 |

Effets (haut moins bas) : `NDEPARTS` 2 : ×4 +4,0, D3 anc. ×4 +6,8, validation +2,0, ×1 -0,3 ; `JOBS_MAX` 1 : ×4 +2,0, ×1 +0,75, validation +3,5, essai 2 +1,0 ; `ITER` 8 : ×4 +2,5 mais ×1 -0,75. Aucun « sûr » faux dans les huit cellules, **mais** les passes finales avec la cellule 8 sur toutes les machines ont montré le contraire : `hypercube4` (1 200 notes, `SYNTH=h6`) pose, au plan 91 de la graine 32 (Do6, 928 Hz, Ω 11,5 Hz, anche faible à -10 dB), un « sûr » à **-21,5 ¢** (la mauvaise étiquette : l'anche faible lue une bande latérale plus bas, AM propre de 0,5 qui imite l'anche), avec `JOBS_MAX` 1 seulement ; avec `JOBS_MAX` 2 la même mauvaise lecture arrive aussi (t = 4,27 s) mais pendant qu'un certificat juste est en cours : elle l'invalide sans se poser (il faut alors deux fenêtres décalées d'accord). La v67 n'a donc pas de garde qui l'exclut : elle l'évite par l'ordre des fenêtres essayées. `M_ST_MAX` 0,5 l'exclurait mais coûte 7 notes sur 16 au H6 (9/27) : refusé. **Les 2 départs et le seul ajustement de front sont donc réservés aux machines lentes**, où la v67 ne pose presque rien : `NDEPARTS` 5 et `JOBS_MAX` 2 (réglage de la v67) tant qu'un ajustement à froid dure en moyenne moins de `MS_LENT` = 500 ms ; au-dessus (mesuré dans le Worker ; PC de l'audit 340 ms, portable 2 fois plus lent 680 ms, téléphone 4 fois plus lent 1 400 ms ; hystérésis 0,7) : `LENT_NDEPARTS` 2, `LENT_ITER` 8, `LENT_JOBS_MAX` 1. La mesure de vitesse vit dans le moteur (`msFroid`), d'une note à l'autre.

**Le simulateur du Worker était optimiste.** `ExecutantSimule` (v66, v67) faisait tourner deux « voies » en parallèle (une pour les sentinelles, une pour les ajustements), c'est-à-dire deux cœurs, alors que `cert-worker.js` est UN fil qui intercale les sentinelles par tranches de 10 ms : la sentinelle prend du temps de calcul à l'ajustement principal. Il est corrigé (`voies: 1` par défaut, préemption des sentinelles ; `voies: 2` rend l'ancien comportement). Les cellules du plan H4 qui comptent (2/8/1, 2/15/1, 5/8/1) rejouées avec le simulateur corrigé donnent les mêmes notes posées (H6 ×1 / ×4 : 15 / 10, 17 / 6, 16 / 5), parce que les sentinelles ne tournent qu'après la première pose.

### 0B.2 bis Une mauvaise étiquette que le banc de la v67 évitait par hasard : `ETIQ_COH_C`

La passe finale d'un premier réglage de la v68 (2 départs, `JOBS_MAX` 1 sur tous les PC) a posé « sûr » à -21,5 ¢ une note de `hypercube4` (plan 91, graine 32, Do6, Ω 11,5 Hz). Rejouée une note à la fois, la cause n'est ni les départs ni les itérations, c'est l'ordre des fenêtres essayées : les ajustements successifs de cette même note donnent TANTÔT la bonne étiquette (erreur 0, AM 0,04, LLR 700 à 15 000), TANTÔT l'anche faible lue une bande latérale plus bas (-21,5 ¢, AM 0,5 qui imite l'anche, LLR 118 à 3 000, r 0,007 à 0,011), tous deux au-dessus de `LLR_MIN`. Avec le réglage de la v67 la mauvaise lecture arrive aussi, mais pendant qu'un bon certificat est en cours : elle l'invalide sans se poser. Aucun seuil existant ne l'exclut : `M_ST_MARGE_DB` 3 et 6 sans effet, `M_ST_MAX` 0,5 l'exclut mais coûte 7 notes sur 16 au H6 (9/27), le rapport des indices de phase des deux anches n'a pas de signature (des ajustements justes du H6 ont un rapport de 0 à 0,24 dans 10 % des cas).

Garde retenue, avec la physique en tête (une note a UNE étiquette) : `ETIQ_COH_C` 3 ¢. Une lecture n'est certifiable que si aucun ajustement plausible de la même note (r ≤ 0,05, LLR ≥ 25) des 4 dernières secondes ne s'en écarte de plus de 3 ¢ ; sinon l'étiquette est ambiguë, refus `etiquette`. Coût : H6 réel ×1 16/27 et ×4 10/27 inchangés (1,5 ¢ en perd 2 et 3 ¢ n'en perd aucune ; 6 ¢ n'en perd aucune non plus), -2 notes sur 300 en synthèse H6. Test : `certificat.test.mjs` rejoue cette note avec le réglage qui la faisait poser (erreur max 21,58 ¢ sans la garde, 0,00 avec) et avec le réglage par défaut.

### 0B.3 H9 : le battement doublé de la thèse (test F10), corrigé

Diagnostic (reproduit ici avec Node 22 sous Windows, `npm install node@22` dans un dossier à part) : à Δ = 0,3 Hz (sous `OMEGA_MIN`), l'ajustement de Bessel a deux minimums proches, Ω et 2Ω ; lequel gagne dépend des arrondis flottants de V8, donc de la plate-forme. Node 22 donnait 0,667 / 0,6 Hz (2Ω, DANS le domaine), refusé `lent` seulement ; or `lent` est dans la liste des refus qui « donnent un Ω aussi bon que les autres » (`finirAjustement`) : le battement affiché (`beatCert`, source « certificat ») montrait 0,6 Hz à la place de 0,3 (F10 : 367 mHz d'écart au p95 ; Node 24 : 1 mHz).

Correction en deux étages, une règle au lieu du hasard de l'arrondi :
1. `nls-bessel.js` : un battement ajusté dont la MOITIÉ est sous `omegaMin` (Ω/2 < 0,4 ≤ Ω) est confronté à son rival Ω/2 (mêmes paramètres, départ chaud, un départ, 8 itérations, mêmes données) ; `llrOmega2 = (SSR_rival − SSR_meilleur) / s²` ; `juger` refuse `accordees` si `llrOmega2 < LLR_MIN` (`RIVAL_MOITIE`). Coût : `fit_cout.mjs` sur 150 notes de `lhs300_calib` : 1 397 -> 1 402 unités par ajustement (+0,4 %, le rival n'est calculé que sous 0,8 Hz).
2. `certificat.js` : un Ω d'ajustement n'entre dans `st.omegas` (donc dans le battement affiché) que s'il n'est pas `accordees` ET d'accord à 25 % (`ENV_ACCORD`) avec le battement de l'enveloppe quand celle-ci en a un (`envHz`, passé par `fuserBattement` à `certifierPaire`) : le battement, pour le luthier, c'est l'enveloppe.

Résultat : F10 vert sous Node 22 ET Node 24 (Δ = 0,3 Hz : 1 mHz au p95, aucune image de source « certificat » éloignée de l'enveloppe), avec le test remis à sa force (la version de la thèse jugeait l'enveloppe seulement quand la source n'était pas le certificat) et une assertion de plus. `omega_bas40` (120 notes, graines 30-32, 45 dans le domaine) : 0 posée, 0 faux en ancienne synthèse et en synthèse H6. CI GitHub : Linux / Node 22 ET Node 24 pour PolyReed (`tests.yml`, matrice) ; la thèse avait déjà Node 22.

### 0B.4 H7 : la prise traitée par Windows, le contrôle de prise comme barrière testée

Le certificat seul se laisse tromper par une prise traitée (sur la prise PC du 14/10, 4 « sûr » sur 6 notes à vérité sont faux, jusqu'à -4,1 ¢ : la prise elle-même est décalée en hauteur). La seule barrière est le contrôle de prise (`dsp/prise.js`, v61). `robustesse_sessions.mjs --prise=1` le fait tourner comme le Worker de l'application ; le nouveau test `test/prise-sessions.test.mjs` (4 sessions de l'audit, registre MM imposé, sur le PC d'Ewen : les fichiers ne sont pas dans la CI) exige **0 note « sûre » avec le contrôle** : [SESSIONS]. Sans le contrôle, le test imprime le nombre de « sûr » et les notes suspectes (écart au traqueur de plus de 2 ¢ sur les deux anches), sans assertion : aucune vérité sur ces prises. L'écran : quand la prise est douteuse, le message dit « hauteur non certifiée : prise douteuse : <raison> ».

### 0B.5 H5 : le domaine annoncé, et un banc CI qui teste ce qu'il annonce

Domaine annoncé : **β ≤ 0,45 « posé » ; de 0,45 à 1,5 « lu quand r ≤ 0,01 et que les gardes passent » ; au-delà, refus.** `verdict.mjs` sépare les deux colonnes (`[β ≤ 0.45 : x/y ; β 0.45-1.5 : x/y]`). Banc CI (`pose-ci.test.mjs`, `ci_seuils.json`) : lot « couplage fort » avec au moins une posée (il ne testait rien avec 0) ; lot `SYNTH=large` (40 notes de `lhs64_valid`, graine 70) ; les notes-pièges de l'audit avec leur graine (D3 plans 19, 12, 27 en ancienne synthèse, B plan 33, `lent100` plan 82 en LARGE, D3 plans 12, 1, 9 en H6) ; un lot peut maintenant fixer sa synthèse (`synth`) et lit le retard après un saut (`maxHautesApres`, `maxFaux`).

### 0B.6 Les chiffres, v67 contre v68 (passes finales du 18/10/2026, graines neuves REP0=30, code gelé, mêmes outils pour les deux)

Vérité : fréquence moyenne de la porteuse de chaque anche sur les 3 dernières secondes (plans ordinaires) ou sur la fenêtre lue (plans à saut) ; fausse = plus de 0,5 ¢ ; domaine Ω ≥ 0,4 Hz, rapport ≤ 22 dB, β ≤ 1,5. Les deux versions sont recomptées avec le même outil sur les mêmes plans à deux anches (les chiffres de la v67 diffèrent donc un peu du § 0A.3).

| jeu | domaine | v67 : posées, fausses (max) | v68 : posées, fausses (max) |
|---|---|---|---|
| synthèse à la physique du H6 (`SYNTH=h6`, 22 plans) | 4247 | 1059 (24,9 %), 0 (0,393 ¢) | 941 (22,2 %), 0 (0,401 ¢) |
| synthèse LARGE (`SYNTH=large`, 12 plans) | 2528 | 474 (18,8 %), 1 (0,531 ¢, `lent100`) | 420 (16,6 %), 0 (0,458 ¢) |
| ancienne synthèse, plans clés (5 plans) | 1198 | 505 (42 %), 4 dont 3 de vérité décalée en D3 et B plan 33 (0,597 ¢) | 451 (38 %), 0 (0,402 ¢) |
| GEN, physique et conditions larges (160 × 2) | 176 | 9 (5 %), 1 (0,556 ¢) | 9 (5 %), 1 (0,556 ¢) |
| GEN-b, conditions modérées, LARGE / H6 / ancienne (160 chacune) | 160 | 22 / 36 / 45, 0 | 18 / 31 / 37, 0 |

Lecture honnête : **zéro faux de plus et les deux vrais faux de la v67 (`lent100` plan 82, B plan 33) fermés, mais 11 % de notes posées en moins en synthèse (14 à 18 % en GEN-b)**. Presque tout vient de la règle des graves (H3, `lhs300_calib` H6 : 89 -> 82, et 89 sans elle), le reste de la garde d'étiquette (-2) et de la sentinelle qui prend du calcul dans le banc en ligne (-1 à -2). Le GEN large garde le même « faux » de 0,556 ¢ : la valeur est juste pour sa fenêtre (-0,02 ¢) mais en retard de 0,99 ¢ sur la hauteur de l'instant (gigue de 0,6 ¢ et dérive de 0,18 ¢/s) : c'est la limite de la vérité, pas une erreur du modèle.

**Prises réelles (Zoom H6, essai 1 : 27 notes ; `usage_reel`, Worker simulé à un cœur)** :

| calcul | v67 | v68 |
|---|---|---|
| ×1 (PC de l'audit) | 16/27, T médian 4,6 s, 7 % du temps certifié | **16/27**, T médian 4,7 s, 7 % |
| ×2 (portable) | 7/27 | **11/27** |
| ×4 (téléphone) | 1/27 | **10/27** |
| ×8 | 1/27 | 2/27 |
| essai 2 (12 notes) ×1 / ×4 | 4 / 1 | 4 / **3** |
| `reel_prises` H6 L+R / gauche / droite | 9 / 12 / 10 | 10 / 11 / 9 |
| prise PC traitée par Windows (avec le contrôle de prise) | 0 | 0 |

0 « sûr » faux dans tous ces essais (72 lectures sûres au ×1, 46 au ×4, 36 à 68 en `reel_prises`). Le simulateur est celui à un cœur (§ 0B.2).

**Retard après un saut de hauteur** (plan D3, 30 notes × graines, saut d'au moins 1 ¢ ; médiane / p90 du délai jusqu'à la première image non « sûre », et images « sûres » à plus de 0,5 ¢ de la hauteur de l'instant plus de 0,35 s après le saut) :

| mode | v67 | v68 |
|---|---|---|
| calcul en ligne, ancienne synthèse | 0,14 / 0,33 s, 5 images (3 notes) | 0,13 / 0,32 s, 2 images (2 notes) |
| calcul en ligne, H6 | 0,22 / 0,42 s, 3 images | 0,22 / 0,31 s, 1 image |
| calcul en ligne, LARGE | 0,15 / 0,48 s, 1 image | 0,15 / 0,38 s, 1 image |
| Worker simulé ×1, ancienne / H6 / LARGE | p90 0,41 / 0,38 / 0,48 s ; 5 / 0 / 3 images | p90 **0,32 / 0,33 / 0,39 s** ; 1 / 1 / 2 images |
| Worker simulé ×4, ancienne / H6 / LARGE | p90 0,28 / - / - ; 1 image | p90 0,38 / 0,39 / 0,39 s ; 2 / 2 / 1 images (mais 30 / 28 / 16 notes posées contre 21 / - / -) |

Aucune lecture « sûre » fausse (vérité de la fenêtre lue) dans aucun de ces essais ; les images restantes sont les battements lents (Ω < 1 Hz : 0,6 s de sentinelle ne contiennent pas un battement) et les gigues extrêmes.

**Corpus d'autres accordéons échantillonnés** (`J:\claudeudits\donnees-accordeur\sf2\`, banques de tiers retouchées, aucune vérité, jamais pour régler un seuil ; `corpus_sf2.mjs`, test local `corpus-sf2.test.mjs`) : Serafini main droite, musette à trois voix lue en deux anches (24 notes) : notes « sûr » v67 3, v68 2, 4 notes communes, 0 désaccord de plus de 0,5 ¢, 0 écart au traqueur de plus de 2 ¢ ; en trois anches (MMM) 0 / 0 ; Serafini et Gaillard main gauche (basses et accords, mode automatique, 14 et 24 fichiers), Gaillard main droite (1 raie, 27), Saltarelle (diatonique, 38) et Ballone Burini (bandonéon, 60, 0,9 à 1,8 s) : 0 note « sûr » avant comme après, 0 erreur. L'outil refuse ou reste juste sur tout ce corpus ; il ne prouve rien de plus (échantillons bouclés, sans vérité).

### 0B.7 Ce qui reste pour un niveau professionnel

1. Les enregistrements propres d'Ewen (H8) : sans eux, « pro sur tous les accordéons » n'est pas démontrable. 2. La super musette (H6) : pas de mesure avec vérité, `nls-trio.js` sans modèle `struct`. 3. La couverture : 22 % des notes de synthèse H6 posées, 17 % en LARGE, 5 % à physique et conditions très larges ; 11 % de moins qu'en v67 par le prix des graves ; le banc ne sait pas dire si c'est la synthèse ou l'outil. 4. Les battements lents (Ω < 1 Hz) : la sentinelle y est aveugle pendant 0,5 à 0,8 s. 5. Une garde d'étiquette qui tient sur de très grands jeux avant de remettre 2 départs et un seul ajustement de front sur les PC (+18 % de notes posées). 6. Un vrai téléphone (le facteur 4 est une hypothèse). 7. La prise traitée : le contrôle de prise est la seule barrière.

## 0A. La v67 (audit Fable n° 3 du 17/10/2026) : la physique de l'anche mise dans la mesure

Audit : `J:\claude\audits\2026-10-17-accordeur-fable-3\RAPPORT-AUDIT-3.md` (G1 à G5, P1 à P5), résumé des plans `DOE-RESUME.md`. Verdict de l'audit sur la v66 : instrument de contrôle (zéro faux), pas accordeur d'établi : 6 notes sur 27 posées sur le H6, 3 % du temps certifié. Cause : le modèle d'anches, ni le bruit ni le calcul.

**Ce qui est validé sur UN SEUL instrument, UN SEUL micro** (Zoom H6, un accordéon, un jour, 19 notes à vérité sûre) : la physique mesurée du § 3 de l'audit (AM propre à chaque partiel, anches en quadrature, indice de phase plus fort aux rangs 1-2, notes aiguës à β ≈ 1) et donc le gain « 6 -> 14 notes sur 27 ». La généralisation repose sur la **synthèse à paramètres larges** (`SYNTH=large`, § 0A.5), pas calée sur le H6, et sur des banques d'échantillons d'autres accordéons (§ 0A.6). Les prises du 11/10, du 13/10 et du 14/10 au micro USB sont **traitées par Windows** (effet vocal) : elles ne servent que de test de robustesse, jamais de réglage ni de preuve de généralisation. Enregistrements propres qui manquent : § 0A.7.

### 0A.1 Ce qui est fait, partiel, refusé

| G | Sujet | Statut | Résultat |
|---|---|---|---|
| G4 | synthèse à la physique mesurée | **fait** | `bench63.mjs` : `SYNTH=h6` (valeurs du H6) et `SYNTH=large` (phase relative 0 à 2π, profils m_k variés, rangs 1-2 de 0,6 à 2,2 fois la loi ∝ k, second harmonique, notes aiguës, timbres de pente variée) ; mêmes notes que l'ancienne synthèse (générateur de hasard à part). La v66 rejouée dessus **perd son zéro faux** (§ 0A.4). Réglage du générateur par plan (PB 12+2) : le second harmonique de modulation aux rangs 3-4 multiplie r par 6 (écarté) |
| G1 | modèle d'anches corrigé | **fait, autrement que proposé** | modèle `struct` (`nls-bessel.js`) : AM RÉELLE par partiel (m_k, χ_k), phase de modulation par anche (θ1, θ2), indice des rangs 1-2 × ρ12, K_utile par résidu de partiel (`RK_MAX_AM`). Le modèle proposé par l'audit (porteuse + deux bandes latérales libres par anche et par partiel, `libre`) est **refusé** : les bandes latérales imitent l'anche faible, étiquette décalée d'un battement, « sûr » faux de 5,3 ¢ ; une AM réelle a deux bandes égales, une anche faible une seule. C2 juge sur r (`R_MAX_AM` 0,01), le plancher et les LLR, plus deux gardes physiques ci-dessous. Coût : le même que la v66 par évaluation (les paramètres d'AM d'un partiel ne réévaluent que ce partiel), 3 à 4 fois moins par ajustement (K_utile) |
| G2 | battements lents 0,4-0,8 Hz | **fait** | la fenêtre est un nombre ENTIER (≥ `ENTIER_NB` = 2) de battements ; tout ce que le couplage fait au son est périodique au battement et s'y annule. `OMEGA_SUR_MIN` 0,8 Hz n'est plus un seuil sur la synthèse mais une règle (sous 0,8 Hz : fenêtre entière, sinon « lent »). La question posée à Ewen (0,8 / 0,6 / 0,4 Hz) est **sans objet** |
| G3 | fenêtre plus tôt | **refusé** | plan PB 12+2 : fenêtre de 1,0 s (`FEN_MAX_S`) +24 notes posées mais 6 à 10 faux ; `DEBUT_S` 0,15 + `FEN_F0_S` 200 : +6 en synthèse mais 1 faux sur 94 lectures sûres du H6. Valeurs de la v66 gardées |
| G5 | incertitude de pression | **fait** | `incertitudePression` : étendue du niveau commun (nœuds du warp) × pente de repli 0,2 ¢/dB (la pente propre de la note, bornée par le repli, ne peut que la baisser) ; affichée « pression ±0,3 ¢ » sous le Hz d'une lecture sûre quand elle dépasse 0,1 ¢. Sur les notes posées du H6, ≤ 0,3 ¢ tant que l'étendue du niveau ≤ 1,5 dB. Sans capteur, c'est une présentation honnête, pas une correction |
| P2 | démarrage à chaud | **fait, mince** | `PRIOR_FIRST` : la paire du traqueur passe en tête des départs (portable ×4 : 5 -> 6 notes sur 39) |
| P3 | trace des ajustements | **fait** | `reel_prises.mjs` garde la trace de chaque ajustement dans le JSON |
| P4 | les trois « faux » réels à 0,50-0,63 ¢ | **fait** | cas-test : La3 (n° 27, Ω 0,59 Hz), v66 avec `OMEGA_SUR_MIN` 0,4 : fenêtre 1,59 s (0,94 battement), LLR 1447, r 4,9e-3, β̂ 0,18/-0,09, m̂ 0,05, erreur -0,60/-0,39 ¢. La v67 la lit sur 2 battements entiers : sans faux |
| P1, F9, capteur, enregistrements 8'+ bouché / 8' bouché | **gestes d'Ewen, non faits** | pas inventés |
| P5 | téléphone réel, Dirk's, C5 | inchangés |

Deux gardes physiques du modèle `struct`, trouvées par des graines neuves (ces fausses lectures n'existaient que dans le monde où la synthèse contient la physique) :
- `MK_MAX` 0,6 : l'AM d'un partiel est bornée à 0,6 (H6 : 0,13 à 0,59). Au-delà, une porteuse et ses deux bandes latérales imitent deux anches : « sûr » faux de 43 ¢ (D3, m̂ 0,75).
- `M_ST_MARGE_DB` 0 : l'anche faible doit être au moins aussi forte que la bande latérale de l'AM de la forte, 20 log10(m̂/2) dB sous elle (planA_valid : 48 ¢ de faux avec une anche faible à -17 dB et m̂ 0,53, fenêtre de 0,67 s). Une borne globale m̂ ≤ 0,5 régla aussi ce cas mais coûta 16 -> 9 notes du H6 : refusée.
`LLR_MIN` passe de 25 à 100 (un ajustement décalé d'un battement, LLR 49, avait posé un « sûr » à 5,3 ¢ : plan hypercube, graine 31) ; la sentinelle est resserrée (`SENT_PERIODE_S` 0,15, `SENT_SIGMA` 3, `CONTREDIT_C` 0,2).

### 0A.2 Plans d'expériences (règle 12)

| plan | type | facteurs | résultat |
|---|---|---|---|
| calibration du générateur | PB 12 + 2 centres | ampMul, pm12, amphSd, jitS, h2c3 | h2c3 domine (r × 6) : écarté pour les rangs 3-4 ; le générateur reste 2 fois plus dur que le H6 en r médian (plancher dû à la quadrature) : choix conservateur |
| G1 réglages | PB 12 + 2 | `MARGE_ETIQ_ST_DB`, `R_MAX_AM`, `RK_MAX_AM`, `LLR_MIN`, `NDEPARTS` (6 jeux, β jusqu'à 1,5) | marge +49 posées, `R_MAX_AM` +15 (mais des faux à 0,05), `RK_MAX_AM` -7, `NDEPARTS` +4 ; retenu marge 20 dB, R 0,01 (138 posées, 0 faux). `RK_MAX_AM` repassé à 0,6 ensuite : à K_utile = 2 une lecture de 1,6 s était trop bruitée (trois fausses de 0,7 ¢ à 0,96 Hz) |
| G2 | fractionnaire 2^(4-1) + 2 | `ENTIER_NB`, `ENTIER_TOL`, `KOT_MIN`, `CONFIRME_MOITIE_C` | `ENTIER_NB` 2 : +33 posées (lent_bas150 + omega_bas40), les autres sans effet |
| G3 | PB 12 + 2 | `DEBUT_S`, `FEN_F0_S`, `FEN_MAX_S`, `DERIVE_MAX`, `NB_MIN`, `REESSAI_S` | fenêtre courte : +24 posées, 6 à 10 faux : refusé |
| M_ST | 3 niveaux | `M_ST_MAX` {99 ; 0,5 ; 0,45} | 0,5 supprime le faux de 48 ¢ mais -8 % de posées en synthèse et 16 -> 9 notes du H6 ; remplacé par la garde de marge |
Les plans et leurs réponses sont dans l'onglet Plans d'expériences de Wenou OS et dans le coffre (« Plans d'expériences »).

### 0A.3 Les chiffres, v66 contre v67 (passes finales du 18/10/2026, graines neuves REP0=30, code gelé)

Vérité = fréquence moyenne de la porteuse de chaque anche sur la fenêtre lue ; fausse = plus de 0,5 ¢ ; domaine : Ω ≥ 0,4 Hz pour le battement.

| jeu | domaine | v66 : posées, sûres, fausses (max) | v67 : posées, sûres, fausses (max) |
|---|---|---|---|
| synthèse à la physique du H6 (`SYNTH=h6`, 21 plans) | 4065 | 1169 (29 %), 7761, 1 (0,599 ¢) | 1196 (29 %), 6493, 1 (0,562 ¢) |
| synthèse LARGE (`SYNTH=large`, 12 plans, pas calée sur le H6) | 2528 | 407 (16 %), 2663, 2 (0,544 ¢) | 470 (19 %), 2167, 1 (0,531 ¢) |
| ancienne synthèse, plans clés (D3, calibration, J, B, validation) | 1198 | non rejouée | 505 (42 %), 2734, 4 (0,715 ¢) |

Les fausses lectures de la v67, toutes entre 0,51 et 0,72 ¢ (aucune grosse) :
- D3 (saut de hauteur de 4,5 ¢ au milieu de la note) : 3 lectures dans les 0,2 s après le saut (Ω 1,4 à 5,2 Hz). La v66 les a aussi : limite de latence, pas un défaut du modèle.
- B (ancienne synthèse) : 0,597 ¢. H6 adverse D3 : 0,562 ¢ (f0 1104 Hz, β 0,38).
- LARGE, `lent100` plan 82 : 0,531 ¢ sur un Sol#2 (f0 103 Hz, Ω 1,87 Hz, β 0,21), à T = 5 s.
Le zéro faux de la v66 sur l'ancienne synthèse ne tenait pas sur la synthèse à la physique : la v67 fait mieux partout, sans l'atteindre. Premier point de l'audit Fable n° 4.

### 0A.4 Sur les vrais enregistrements

| prise | v66 | v67 |
|---|---|---|
| Zoom H6, usage simulé ×1 (27 notes, essai 1) | 6/27 posées | **16/27**, 0 « sûr » faux sur 83, T médian 4,6 s, 7 % du temps certifié |
| Zoom H6, essai 2 (12 notes) | 2/12 | 4/12, 0 faux sur 25 |
| H6, voies gauche, droite, somme (`reel_prises`) | | 12, 10, 9 notes posées ; 0 lecture sûre fausse (115 lectures) |
| PC 14/10 (effet vocal Windows) | 0 | 0 posée, 0 faux (refuse, comme il faut) |
| sessions 11/10, 13/10, 14/10 (traitées par Windows, robustesse seulement) | 1, 3, 3 notes « sûr » | 4, 10, 8 ; aucun désaccord de plus de 0,5 ¢ avec la v66 sur les notes communes |
| banque Serafini (autre accordéon, échantillons), MM et MMM | 1 note | 3 notes ; 0 désaccord |

### 0A.5 Téléphone (usage simulé, calcul ×4 plus lent)

H6 essai 1 : 1/27 posée (×1 : 16/27) ; essai 2 : 1/12. Les images p99 dépassent 1 s : **sur un téléphone milieu de gamme, la v67 refuse presque tout**, faute de temps de calcul (le certificat tourne déjà dans un Worker depuis la v66). Il faut alléger l'ajustement (décimation après le premier étage, moins de départs) puis mesurer sur un vrai téléphone (toujours à faire).

### 0A.6 Banques d'échantillons

Ballone Burini, Gaillard, Serafini, Saltarelle (SFZ et WAV) copiées dans `J:\claude\audits\donnees-accordeur\sf2\`. Notes courtes (1 segment) : peu de poses, aucune fausse ; elles ne prouvent pas la généralisation à elles seules (pas de vérité).

### 0A.7 Ce qui manque pour généraliser (gestes d'Ewen)

- Des prises PROPRES (Zoom H6 ou micro sans effet Windows) de **plusieurs autres accordéons** : un chromatique à voix musette lente, un à musette serrée, un diatonique, un bandonéon, un harmonium ; au moins 3 notes tenues 8 s par registre (16', 8', 4', musette 2 voix, 3 voix), du grave à l'aigu.
- Des prises de **micros de téléphone** (Android et iPhone) et de **micros USB courants** avec les effets de la plateforme coupés, simultanées avec le H6 (prise de contrôle F9, toujours à faire).
- La note MM tenue 10 s puis 8'+ bouché puis 8' bouché (tirage mesuré), et la courbe hauteur / pression avec le capteur XGZP6847 (G5 complet).

## 0. La v66 (audit Fable final du 16/10/2026) : ce qui a changé, ce qui est refusé

Audit : `J:\claude\audits\2026-10-16-accordeur-fable-final\RAPPORT-AUDIT-FINAL.md` (F1 à F12). Verdict de l'audit sur la v65 : instrument de contrôle professionnel (bonne prise, battements de 2 à 20 Hz, note tenue
sans à-coup), pas encore accordeur de travail à l'établi (30 « sûr » faux dans le domaine annoncé sur les cas adverses, 3 notes sur 27 posées dans l'application, l'écran montrait 93 à 100 % du temps la lecture brute du traqueur
qui bouge de ±1 ¢). La v66 corrige ce qui pouvait l'être **sans faux** ; ce qui ne passait pas est refusé et dit.

| F | Sujet | Statut | Résultat |
|---|---|---|---|
| F1 | invalider un « sûr » que la note a quitté | **fait** | toute lecture complète qui contredit le certificat l'invalide (`CONTREDIT_C`), et une sentinelle (lecture chaude de 0,6 s toutes les 0,25 s) le fait tomber en ~0,5 s : plan D3 (saut de 2 à 4,5 ¢) 25 faux (jusqu'à 2,9 ¢) -> **0** ; plans de validation : 215 posées sur 384 (223 en v65) |
| F2 | domaine à 0,4 Hz | **fait, et plus** | `OMEGA_MIN` 0,4 Hz (le battement reste mesuré dès là) ; la HAUTEUR « sûre » exige 0,8 Hz (`OMEGA_SUR_MIN`, raison `lent`) : voir § 0.3, c'est une exception à la règle « seuils sur la synthèse » |
| F3 | lire à 0,5 battement | **refusé** | `NB_MIN` 0,5 : +7 notes posées sur 632 mais un « sûr » à **6,4 ¢** (plan de validation, Ω 0,8 Hz, f0 218 Hz) ; `FEN_F0_S` 250 : +37 posées mais mêmes erreurs : le zéro faux ne tient pas, la musette sous 2 Hz n'est pas mieux couverte |
| F4 | certificat au budget réel | **fait** | Worker dédié (`dsp/cert-worker.js`), file qui saute les demandes périmées, sentinelles prioritaires, budget du repli en ligne réglé sur le temps mesuré ; Chrome : charge du Worker de mesure 47,9 % -> 7,7 %, calcul du moteur par image 44,5 -> 7,2 ms (§ 0.4) ; le démarrage à chaud depuis le traqueur n'est pas fait (inutile avec un cœur dédié : un ajustement à froid de 350 ms revient en 0,35 s) |
| F5 | poser après l'attaque sans délai fixe | **refusé** | `FENETRE_ADAPTIVE` : +26 notes posées mais des « sûr » faux sur les sauts (D3) et le couplage fort ; `AGE_MIN_S` 0,7 : +2 lectures fausses ; classe « avec attaque » inchangée (3,5 s) |
| F6 | écran sobre | **fait** | chiffre provisoire (médiane de 1,5 s au demi-cent, gris, plus petit, une bande) puis chiffre certifié (dixième de cent) ; une raison seulement si elle demande un geste ; courbe du battement repliée ; courbe d'accordage en pointillé tant que rien n'est certifié (§ 0.5) |
| F7 | bancs en CI | **fait** | `test/pose-ci.test.mjs` (77 notes : validation, super musette, sauts, couplage fort, battements lents) dans `npm test` ; échoue si `BETA_MAX` passe à 0,6 ou si la sentinelle est éteinte ; le JSON des bancs garde β̂, m̂, plancher, K·Ω·T, raie étrangère, σ, battement certifié |
| F8 | couplage fort | **refusé (éteint)** | exiger LLR 100, m̂ ≤ 0,15 et des moitiés à 0,2 ¢ au-dessus de β̂ 0,35 attrape la note à β vrai 0,48 (β̂ 0,36, m̂ 0,23) mais coûte 90 % des notes posées du plan J (β 0,38-0,45, DANS le domaine : 24 sur 50 -> 1) ; 1 note hors domaine reste posée sur le plan B (80 notes) |
| F9 | prise PC / H6 en même temps | **geste d'Ewen, non fait** | la prise PC reste à 0 note sur 27 ; rien ne prouve qu'un micro USB grand public donne un « sûr » juste |
| F10 | super musette | **fait** | raison `ident3` (écarts égaux à 5 % et moins de 2 partiels nets : indiscernable d'UNE anche modulée), raison `absente` (une anche à plus de 35 dB), C3 sur K_utile ; 20 notes « une anche modulée » : 0 « sûr » |
| F11 | téléphone | **partiel** | pas d'appareil ni d'adb ici : le coût est simulé (cœur 4 fois plus lent, Chrome en CPU x4 : fil principal 20,9 %, Worker de mesure 8,3 %) ; la pose tombe de 6 à 2 notes sur 27 ; à mesurer sur un vrai téléphone |
| F12 | doc/code | **fait** | titre, C3, C7, C8, commentaire 15 ms, renvoi, test R2, `bench_reel` étiqueté « accrochage », texte d'aide de l'horloge (plus de NTP), vérité `porteuse` expliquée (§ 0.6) |

Points de R1 à R14 repris : refus « 3 anches ou 1 modulée » (F10) ; gestes pour les 6 refus sans geste, `peigne` séparé en trois causes (`accrochees`, `micro`, `etrangere`), `verification`, `etiquette` et `accord` jamais affichés ; la raison `niveau`
imposée par `REFUS_RECENTS` n'est plus réécrite en `peigne` ; K_utile ; vérité porteuse comparée à la vérité « phase totale » (§ 0.6) ; C7 (marge 3 σ + 0,02 ¢) essayé : `SIGMA_TOL_C` reste éteint, l'écart type statistique de l'ajustement
(0,005 ¢ en médiane, 0,02 ¢ au p99 sur 751 lectures sûres) n'a aucun rapport avec l'erreur réelle (jusqu'à 0,4 ¢) : le biais du modèle domine, pas le bruit ; C5 (accord des partiels impairs et pairs) : non fait.

### 0.1 Tous les plans rejoués (VERITE=porteuse, verdict de l'interface, domaine : rapport ≤ 22 dB, β ≤ 0,45, Ω de 0,8 à 60 Hz)

| jeu | notes | dans le domaine (Ω ≥ 0,8 Hz) | posées v65 | **posées v66** | lectures « sûr » | fausses v65 | **fausses v66** | erreur max (¢) | T médian (s) |
|---|---|---|---|---|---|---|---|---|---|
| calibration 300 x4 | 1200 | 988 | 649/1200 | **644** | 5349 | 0 | **0** | 0.43 | 3 |
| validation 64 x6 | 384 | 318 | 223/384 | **215** | 1864 | 0 | **0** | 0.40 | 2.75 |
| conditions neuves 150 x3 | 450 | 348 | 208/450 | **201** | 1607 | 0 | **0** | 0.39 | 2.5 |
| coins (plan A) | 320 | 80 | 19/320 | **15** | 84 | 0 | **0** | 0.22 | 2.5 |
| plan A de validation | 320 | 225 | 116/320 | **117** | 839 | 0 | **0** | 0.27 | 3.25 |
| réaliste 16 x10 | 160 | 80 | 81/160 | **66** | 772 | 0 | **0** | 0.19 | 1.75 |
| adverse 60 x3 (vibrato, trémolo) | 180 | 180 | 39/180 | **38** | 272 | 0 | **0** | 0.38 | 3 |
| domaine 96 x2 | 192 | 94 | 45/192 | **46** | 292 | 0 | **0** | 0.24 | 3.25 |
| super musette, calibration | 240 | 192 | 58/240 | **44** | 197 | 0 | **0** | 0.35 | 3.5 |
| super musette, validation | 192 | 152 | 49/192 | **44** | 288 | 0 | **0** | 0.29 | 3 |
| confirmation Fable 120 x3 (graine 7777) | 360 | 282 | 120/360 | **134** | 888 | 0 | **0** | 0.27 | 2.5 |
| confirmation Fable trio 60 x2 (graine 8888) | 120 | 108 | 31/120 | **24** | 115 | 0 | **0** | 0.27 | 3 |
| D3 saut de hauteur 2 à 4,5 ¢ | 60 | 50 | 47/60 | **37** | 252 | 25 | **0** | 0.44 | 1.75 |
| F raie étrangère forte | 60 | 30 | 11/60 | **7** | 33 | 4 | **0** | 0.31 | 3 |
| J lisière du domaine (β 0,38-0,45, Ω 0,2-1,2 Hz) | 80 | 18 | 38/80 | **12** | 43 | 1 | **0** | 0.13 | 4 |
| B couplage fort (hors domaine) | 80 | 4 | 7/80 | **3** | 7 | hors 4 | **0 (+1 hors domaine)** | 0.28 | 2.25 |
| D dérive + attaque | 80 | 68 | 40/80 | **36** | 203 | 0 | **0** | 0.40 | 2.25 |
| D2 dérive qui se retourne | 60 | 50 | 35/60 | **33** | 166 | 0 | **0** | 0.29 | 2 |
| A anche faible | 80 | 28 | 8/80 | **6** | 14 | 0 | **0** | 0.16 | 4.75 |
| C vibrato de soufflet | 80 | 80 | 4/80 | **4** | 15 | 0 | **0** | 0.22 | 3 |
| G super musette asymétrique | 80 | 70 | 16/80 | **9** | 37 | 0 | **0** | 0.18 | 3.5 |
| H deux anches égales | 64 | 32 | 20/64 | **13** | 57 | 0 | **0** | 0.20 | 2.25 |
| I bruit 15-25 dB | 80 | 66 | 69/80 | **59** | 665 | 0 | **0** | 0.29 | 2 |
| Ω lents 0,2-0,6 Hz (40 x3, nouveau) | 120 | 0 | 1/120 | **0** | 0 | 0 | **0** | - | - |
| Ω 0,4-3 Hz (100 x3, nouveau) | 300 | 198 | - | **94** | 672 | - | **0** | 0.40 | 3.25 |
| avec attaque (60 x3, nouveau) | 180 | 180 | - | **128** | 770 | - | **0** | 0.35 | 3.5 |

TOTAL lectures sûres dans le domaine 15501, fausses 0

Zéro lecture « sûr » fausse dans le domaine sur ces 15 501 lectures. Les « posées » de la v66 comptent toutes les notes du jeu (le domaine de la v66 est plus étroit : Ω ≥ 0,8 Hz pour la hauteur sûre) ; quand la v65 posait une note de 0,2 à 0,8 Hz, la v66 la refuse avec « battement lent ».
Les deux confirmations à graines neuves (7777, 8888) : 134 notes posées sur 360 et 24 sur 120, 0 fausse. Plan C (chaîne micro) : 45 posées sans calibration d'horloge, 93 calibrée à 30 ppm, 0 fausse sur 497 et 969 lectures (erreur max 0,36 ¢). Chaîne combinée (porte,
suppression, compression, ronflement, bande, 150 ppm) : refusée en bloc (`trous`), 0 posée ; résidu d'horloge de 40, 80 ou +100 ppm déclaré à 40 : 0 faux (max 0,31 ¢). Vérité « phase totale » (v63, la modulation de phase du tirage
comprise) rejouée sur la validation 64 x6, la confirmation 120, les conditions neuves 150, D3 et les Ω lents : 0 fausse, erreur max 0,49 ¢ (D3), contre 0,44 ¢ avec la porteuse.

Hors domaine : la note à β vrai 0,48 (plan B) est encore posée une fois sur 80 notes (F8 refusé) ; 3 notes posées hors domaine (conditions neuves, plan A de validation) sont justes.

### 0.2 Plans d'expériences des réglages (règle 12)

- **DOE1** : criblage Plackett-Burman 12 lignes, 11 facteurs (NB_MIN, FEN_F0_S, BETA_MAX, DERIVE_MAX, EXC_MAX, M_MAX, R_MAX, FENETRE_ADAPTIVE, AGE_MIN_S, F8, FEN_MAX_S), 8 lots (632 notes dans le domaine par ligne, plus de 7 600 notes). Effets (haut - bas) sur les notes posées :
  `FEN_MAX_S` 2,5 : **-54** ; `FEN_F0_S` 250 : **+37** (mais +2,0 lectures fausses) ; F8 : **-33** ; `FENETRE_ADAPTIVE` : **+26** ; `AGE_MIN_S` 0,7 : -10 (+2,0 fausses) ; `DERIVE_MAX` 1 : -8 ; `NB_MIN` 0,5 : +7 (erreur max +1,9 ¢) ; `BETA_MAX` 0,6 : -6 ; `EXC_MAX` 1,2 : -4 ; `R_MAX`, `M_MAX` : sans effet.
  Les deux lignes à 6,4 ¢ d'erreur ont `NB_MIN` 0,5, `FEN_F0_S` 250 et `FENETRE_ADAPTIVE` éteint.
- **DOE2** : fractionné 2^(8-4) résolution IV, 16 lignes (FEN_F0_S, M_FORT, LLR_BETA_FORT, CONFIRME_MOITIE_FORT_C, REFUS_RECENTS, NIVEAU_MIN_DB, LAG_MAX_C, DERIVE_MAX), `FENETRE_ADAPTIVE` allumée et F8 à 0,35 en base. Toutes les lignes ont 2 à 5 lectures
  fausses (les mêmes notes : D3 et B, causées par la fenêtre adaptative), d'où le refus de F5. Effets : `M_FORT` 0,25 : +23 posées ; `LAG_MAX_C` 0,5 : +16 posées et +1 fausse ; `FEN_F0_S` 280 : +13 et +1 fausse ; `CONFIRME_MOITIE_FORT_C` 0,4 : +6 et +0,5 fausse ;
  `NIVEAU_MIN_DB` 25 (+4), `REFUS_RECENTS` 0 (+1,6), `DERIVE_MAX` 1 (+2,6) : sans effet sur les fausses, mais les plans n'ont ni rapport > 22 dB ni dérive extrême, donc rien ne prouve qu'on puisse les relâcher : **seuils gardés** (22 dB, 3 sur 4, 0,5 ¢/s).
  Ces seuils (`REFUS_RECENTS`, `NIVEAU_MIN_DB`, `LAG_MAX_C`) avaient été posés sur des échecs isolés ; les voici reposés par plan : aucun n'est contredit, aucun n'est mieux justifié qu'avant.
- **Confirmation F8** (plans B, J, valid, lent) : `M_FORT` 0,15 : plan J 24 -> 1 posée ; `M_FORT` 0,2 : 24 -> 5 ; éteint : 24, avec une note hors domaine fausse sur B.
- **Ω lents** : 450 notes (Ω 0,45-1 Hz, désaccord 2-8 ¢, `OMEGA_SUR_MIN` à 0,4) : 0 fausse, erreur max 0,37 ¢ ; 120 notes Ω 0,2-0,6 Hz : 0 posée.

### 0.3 L'exception : `OMEGA_SUR_MIN` 0,8 Hz posé après les prises réelles

Les règles d'Ewen interdisent de régler un seuil sur ses prises. Ici la synthèse ne donne **aucune** fausse lecture à Ω 0,45-1 Hz, mais le rejeu des prises H6 du 14/10 au budget de l'application (exécutant simulé) en donne trois à 0,50-0,63 ¢ : Ω vrai 0,40 Hz
(cœur 4 fois plus lent), 0,55 Hz (Fa#4, à 6,8 s) et 0,58 Hz. La synthèse ne sait pas reproduire ce biais (l'incertitude 1 de l'audit : la preuve de zéro faux vit dans un monde simulé). Par prudence la hauteur « sûre » exige Ω ≥ 0,8 Hz (marge pour le bruit sur le Ω
mesuré). Coût : les notes de 0,4 à 0,8 Hz (musette lente) ne sont plus dites sûres ; leur battement reste mesuré dès 0,4 Hz. À reprendre quand la synthèse reproduira ces erreurs (question posée à Ewen).

### 0.4 Usage réel : les prises H6 rejouées au budget de l'application

`test/outils/perf/usage_reel.mjs` : le moteur et son certificat sur les 27 notes de l'essai 1 et les 12 de l'essai 2, avec `lireTick` à chaque image. « Avant » : v65 dans l'application (40 ms de calcul par image, audit § 7). « Après » : la v66 avec le Worker dédié (horloge virtuelle du son, un ajustement dure
son coût x 0,26 ms, x1 ou x4).

| mesure | v65 application (avant) | v66, cœur dédié x1 | v66, cœur x4 (portable) |
|---|---|---|---|
| essai 1 : notes posées / 27 | 3 | **6** (banc v65 : 7) | 2 |
| essai 2 : notes posées / 12 | 2 | 2 | 1 |
| essai 1 : temps de pose médian | 3,4 s | 5,0 s (les notes lentes ne sont plus posées) | 3,8 s |
| part du temps (notes tenues > 1 s) avec un chiffre certifié à l'écran | 1 % (99 % de brut) | 3 % | 1 % |
| écart type du chiffre affiché avant la pose (essai 1 / 2) | 0,83 / 1,0 ¢ | **0,30 / 0,49 ¢** | 0,39 / 0,53 ¢ |
| sauts de plus de 0,3 ¢ par seconde | 1,5 à 1,8 | **0,7 à 0,9** | 0,7 à 0,8 |
| lectures « sûr » fausses (vérité du verrou, > 0,5 ¢) | 0 | **0 sur 55 et 4** | 0 sur 9 et 0 |
| prises H6 (reel_prises, budget des bancs) : posées / 27 ; fausses | 7 ; 0 | 6 ; 0 sur 46 (H6 gauche 5, droit 4) | |
| prise PC : posées / 27 | 0 | 0 | |

Lecture honnête : le calcul n'était pas la cause principale du « 3 notes sur 27 » (le plafond propre aux critères est à 8 sur 27, audit § 7) : le Worker dédié l'enlève du fil de mesure et supprime le retard, mais la couverture réelle reste au mieux un quart des notes. Le refus dominant sur le H6 est `peigne`
(indice de phase β estimé > 0,45 pour 114 ajustements sur 126) ; `BETA_MAX` ne peut pas monter (La5 lue à +0,6 ¢ avec 0,6) et la synthèse ne contient pas de couplage réel plus fort que 0,45 : il faut d'abord comprendre les quatre notes aiguës (La5, Sol#5, Fa#5, Si5).
Le chiffre à l'écran est devenu calme (écart type divisé par 2 à 3) mais ne devient « sûr » que sur une note sur quatre.

Profil Chrome (`test/outils/perf/profil.mjs`, prise H6 de l'essai 2 rejouée par `?wav=`, 60 s ; la note est verrouillée sur Ré#4 : valable pour le coût, pas pour la pose) :

| | v65 x1 | v66 x1 | v65 x4 | v66 x4 |
|---|---|---|---|---|
| fil principal | 4,0 % | 4,0 % | 19,8 % | 20,9 % |
| tâches longues (> 50 ms) | 0 | 0 | 2 (66 ms) | 2 (65 ms) |
| charge du Worker de mesure | **47,9 %** | **7,7 %** | 47,9 % | 8,3 % |
| calcul du moteur par image (moyenne / p95) | 44,5 / 52,4 ms | **7,2 / 8,8 ms** | 44,4 / 53,3 | 7,7 / 10,6 |
| retard du moteur sur le son à la fin | 34,8 ms | 9,3 ms | 47,2 ms | 2,0 ms |
| tas JS maximal | 11,1 Mo | 11,3 Mo | 12,6 | 13,5 |

Le calcul du certificat tourne maintenant dans son propre Worker (un autre cœur) : il ne rame plus sur le fil de mesure, et sur un portable (x4) l'image du moteur reste à 8 ms au lieu de 44.

### 0.5 L'écran sobre (F6)

Avant la preuve, le chiffre n'est plus la lecture brute image par image : c'est la médiane de la dernière seconde et demie arrondie au demi-cent (au plus un demi-cent toutes les secondes, seulement si l'écart dépasse 0,75 ¢), en gris et plus petit, avec une seule bande (±) ; sa couleur d'état
et ses flèches sont neutres. Quand la lecture est certifiée il passe en grand et en couleur, au dixième de cent, et ne bouge que si la valeur bouge d'un dixième (un jitter de 0,04 ¢ ne le fait pas bouger : `test/affichage.test.mjs`). Si la preuve tombe (la note a bougé), le chiffre provisoire revient tout de suite.
La médiane est de 1,5 s et non 1 s comme le proposait l'audit : sur la prise H6 la fluctuation est lente et corrélée (le traqueur moyenne sur ~1 s), une seconde laissait 0,9 saut par seconde. Raisons affichées : un geste, jamais `verification`, `etiquette` ni `accord`. La raison `horloge` dit le temps restant de la mesure de l'horloge du micro (60 s)
et la valeur déjà mesurée pour ce micro est reprise dès le démarrage (v64).

### 0.6 Vérité porteuse et vérité « phase totale »

Les bancs jugent par défaut la fréquence MOYENNE DE LA PORTEUSE de l'anche (`VERITE=porteuse`), celle que le modèle ajuste (donc en partie circulaire), sur min(T, 3) s ; la vérité « phase totale » (v63, modulation de phase du tirage comprise, nombre entier de battements) est la définition demandée par l'audit.
Rejouées toutes les deux (§ 0.1) : 0 fausse dans les deux cas, erreurs maximales de 0,44 ¢ (porteuse) et 0,49 ¢ (phase totale, D3). La marge sous le seuil de 0,5 ¢ reste mince : un luthier qui veut 0,2 ¢ verra environ une lecture sûre sur cent au-delà (p99 : 0,22 ¢ ; maximum 0,44 ¢).

### 0.7 Ce qui reste

F9 (geste d'Ewen : H6 et micro USB sans effet Windows en même temps, un la de référence, une minute de silence) ; la couverture réelle (6 notes sur 27 : le couplage réel des quatre notes aiguës) ; F3 et F5 refusés (le zéro faux ne tient pas) ; F8 éteint ; le coût sur un vrai téléphone ; la comparaison à Dirk's
(calibration à faire par Ewen) ; C5 ; une synthèse qui reproduise le biais des Ω lents réels (§ 0.3).

## 1. Les chiffres, avant et après

Banc de synthèse réaliste (`test/outils/pose/`, plans faits par `outils/doe.py`) : notes à deux ou trois anches de Do2 à A6, battements de 0,12 à 63 Hz, rapport d'amplitude
de 0 à 34 dB, indice de modulation de phase β de 0,05 à 0,4, modulation d'amplitude jusqu'à 20 %, agitation, dérive, attaque de +13 ¢, raie étrangère, bruit 25 à 40 dB.
Le verdict est celui de l'interface (`lireTick` : anche sans marge, phase « résolue », prise saine) ; la vérité est la fréquence MOYENNE DE LA PORTEUSE de l'anche sur la
fenêtre lue (sans la modulation de phase du tirage : `VERITE=porteuse`) ; une lecture est fausse à plus de 0,5 ¢. Les lectures d'avant la fin de l'attaque comptent aussi.
« Posées » = notes dont une lecture est dite sûre ; temps de pose = depuis le début du plateau (fin de l'attaque pour les notes à attaque). Règle des trois : 0 faux sur n
notes posées démontre un taux inférieur à 3/n à 95 %.

| jeu | notes | dans le domaine | posées | 1res lectures fausses | lectures « sûr » | dont fausses | borne (95 %) | T médian (s) | T p90 (s) |
|---|---|---|---|---|---|---|---|---|---|
| v63, plan de calibration (300 x4) | 1200 | 1200 | 391 (33 %) | 0 | 2057 | 0 (0 notes) | < 0.77 % | 4.75 | 5.50 |
| v64, plan de calibration (300 x4) | 1200 | 1200 | 649 (54 %) | 0 | 6036 | 0 (0 notes) | < 0.46 % | 3.00 | 5.00 |
| v64, validation (64 x6) | 384 | 384 | 223 (58 %) | 0 | 2192 | 0 (0 notes) | < 1.35 % | 2.75 | 4.75 |
| v64, conditions neuves (150 x3) | 450 | 414 | 208 (50 %) | 0 | 1879 | 0 (0 notes) | < 1.44 % | 2.75 | 5.25 |
| v64, coins (plan A) | 320 | 160 | 19 (12 %) | 0 | 97 | 0 (0 notes) | < 15.79 % | 2.75 | 5.55 |
| v64, plan A de validation | 320 | 280 | 116 (41 %) | 0 | 943 | 0 (0 notes) | < 2.59 % | 3.25 | 5.50 |
| v64, réaliste (160 x10) | 160 | 160 | 81 (51 %) | 0 | 856 | 0 (0 notes) | < 3.70 % | 2.75 | 5.25 |
| v64, adverse (60 x3) | 180 | 180 | 39 (22 %) | 0 | 312 | 0 (0 notes) | < 7.69 % | 3.00 | 5.00 |
| v64, domaine (Ω 0,2-60 Hz, 24 dB) | 192 | 112 | 45 (40 %) | 0 | 347 | 0 (0 notes) | < 6.67 % | 3.25 | 5.05 |
| v64, super musette, calibration | 240 | 240 | 58 (24 %) | 0 | 343 | 0 (0 notes) | < 5.17 % | 3.75 | 5.50 |
| v64, super musette, validation | 192 | 192 | 49 (26 %) | 0 | 382 | 0 (0 notes) | < 6.12 % | 3.00 | 5.00 |

Temps de pose (depuis le début du plateau), par classe de notes, sur le plan de calibration (300 conditions, 4 répétitions) :

| classe | v63 : posées, médiane, p90 | v64 : posées, médiane, p90 |
|---|---|---|
| Ω ≥ 2 Hz, sans attaque, f0 ≥ 200 Hz (le cas courant) | 118/280, 4,00 s, 5,25 s | 254/280, 1,75 s, 3,00 s |
| Ω ≥ 2 Hz, sans attaque, tout f0 | 144/332, 3,75 s, 5,25 s | 289/332, 1,75 s, 3,75 s |
| Ω ≥ 2 Hz, avec attaque (depuis la fin de l'attaque), f0 ≥ 200 Hz | 133/324, 4,75 s, 5,70 s | 231/324, 3,50 s, 5,50 s |
| Ω ≥ 2 Hz, tout | 293/704, 4,50 s, 5,50 s | 553/704, 2,75 s, 4,75 s |
| toutes les notes du domaine | 391/1200, 4,75 s, 5,50 s | 649/1200, 3,00 s, 5,00 s |

Lecture honnête : 0 lecture « sûr » fausse sur 12 662 lectures de deux anches (8 jeux de banc) et sur 725 de super musette ; la borne à 95 % est de 0,46 % des notes posées sur le plan de calibration
(règle des trois). Le temps de pose visé (1,5 s pour Ω ≥ 2 Hz) est atteint à 1,75 s de médiane pour le cas courant (note sans attaque, f0 ≥ 200 Hz) ; il ne l'est pas pour les notes graves, les battements lents
(< 2 Hz : 3 à 4 s) et les notes à attaque (la fenêtre ne peut pas toucher l'attaque). La v64 pose 54 % des notes du plan de calibration (v63 : 33 %) ; un premier essai à 63 % avait un indice de phase β permis jusqu'à 0,6 : les
prises réelles ont montré qu'il faisait lire La5 à +0,6 ¢ ; β est resté à 0,45, et ces neuf points de notes posées sont le prix du zéro faux.

Plan A (coins du domaine, 320 notes) : 1 lecture fausse apparue sur une note hors domaine (25 dB, Ω 0,3 Hz, β 0,4, raie étrangère : la raie de l'anche faible tombe sur la raie latérale de la forte, le modèle prend l'une
pour l'autre) ; règle ajoutée (§ 2.8) : 0 faux ensuite, sans perte de notes posées sur les plans de validation (116/280 et 223/384 dans les deux cas).


## 2. Ce qui change en v64 (les sept points de la mission)

### 2.1 (a) Les « sûr » tardifs faux des prises du H6 : rejoués

Le critère C8/C9 de la v63 avait été resserré après coup sans rejouer les prises. Rejoué (`reel_prises.mjs`, 27 notes, canaux L+R, L et R, vérité = verrou de phase du H6) :
la v63 pose 4 notes (L+R : 44 lectures « sûr », écart maximal 0,17 ¢ ; L : 54 ; R : 52, écart maximal 0,28 ¢) ; aucune lecture à plus de 0,3 ¢ de la vérité à
la v63 (les « 4 sur 48 » du compte rendu précédent ne se reproduisent plus). La v64 : la v64 pose 7 notes sur 27 (L+R : 103 lectures « sûr », aucune fausse ; L : 6 notes, 134 lectures ; R : 5 notes, 65 lectures ; 0 fausse sur 302), le traqueur seul de la v62 en posait 13 avec 42 lectures fausses sur 336. Une borne de l'indice de phase relâchée à 0,6 (pour poser davantage de notes réelles) avait
fait lire La5 (β réel 0,46 à 1,1, raies non proportionnelles au rang, § 1.1 de l'audit) à +0,6 ¢ sur le canal gauche : elle est revenue à 0,45, valeur de l'audit (au-delà de 0,4
la porteuse n'est plus la raie dominante aux partiels hauts). Les prises réelles ont servi ici de VALIDATION (elles ont attrapé ce réglage), pas de calibration.

### 2.2 (b) Prise PC : la cause du « facteur d'échelle » et des 2 « sûr » à +0,66 ¢

Voir `docs/PRISE-DE-SON.md`, section v64. En résumé : mêmes fenêtres lues par le même modèle des deux côtés (`pc_vs_h6.mjs`) ; l'écart PC − H6 est constant dans une note
(étendue médiane 0,15 ¢), identique sur les deux anches ; **ce n'est pas la fenêtre de vérité** ; il vaut −2,7 ¢ dans les 50 premières secondes de la prise PC (régime transitoire,
deux essais concordants), −0,25 ¢ ensuite (l'horloge, 99 à 125 ppm) et +0,56 à +0,80 ¢ sur d'autres notes (un état à +0,9 ¢ au-dessus de la ligne de base, sans signature dans
le signal : plancher entre les raies à −50 dB des deux côtés). Un quartz ne varie pas de 500 ppm en quelques secondes : la chaîne logicielle de la capture (rééchantillonneur) est
le candidat, le Zoom H6 reconstruit par Reaper aussi ; la prise de contrôle manque (question posée à Ewen). Ce que fait la v64 : « sûr » exige l'horloge mesurée (C10) — le
régime transitoire disparaît (la mesure n'est acceptée qu'après 60 s et deux moitiés d'accord à 30 ppm) — et la prise reste contrôlée (`prise.js` : 0 « sûr » sur la prise PC,
horloge connue ou non). Sans le contrôle de prise, la prise PC donne 0 note posée sur la prise PC (0 lecture « sûr »), horloge connue ou non : c'est l'état à +0,9 ¢, non détectable dans le signal.

### 2.3 (c) Horloge du micro (R12)

L'horloge d'un micro USB s'écarte de 10 à 200 ppm (0,02 à 0,35 ¢). Avant : la v63 prenait 0 ppm sauf réglage manuel (Réglages > Micro > Horloge ou Référence existaient
depuis la v41). Maintenant : **le comptage des échantillons face à l'horloge du PC tourne tout seul pendant la première minute d'écoute** (`ui/horloge-auto.js`, banc
`test/horloge-auto.test.mjs` : +125 ppm lu à 125,0 ; −150 ppm avec un saut du son de +20 ms lu à −150,5 ; deux moitiés qui se contredisent refusées), le résultat est gardé pour ce
micro (`reglages.horloges`, même clé que Réglages) et appliqué (`calibrationPpm`) ; tant qu'elle est inconnue (> 100 ppm d'incertitude annoncée, plancher de 30 ppm : le quartz
du PC), jamais « sûr » (raison « horloge » : « l'horloge de ce micro n'est pas encore connue (mesure en cours, une minute) »). Réglages > Micro > Référence (un la joué par un
téléphone, ±20 ppm) reste la référence externe pour qui veut 0,03 ¢. Jamais le secteur (±2 000 ppm). Plan C (§ 4.4) : horloge inconnue → 0 « sûr » faux et aucun « sûr » dans
les cellules à +150 ppm ; calibrée à 30 ppm → 0 faux, écart maximal 0,36 ¢.

### 2.4 (d) Super musette : le modèle à trois anches (R3)

`dsp/nls-trio.js` : anche basse f_C − Δ−, centrale f_C, haute f_C + Δ+ (Δ− et Δ+ libres : la note n'est pas symétrique). L'anche basse est modulée en phase et en amplitude à Δ−,
la haute à Δ+, la centrale aux DEUX (produit de deux séries de Bessel, 25 raies) ; 13 paramètres non linéaires (f_C, Δ−, Δ+, quatre indices de phase signés, trois indices d'amplitude,
ψ, θ−, θ+), le timbre de chaque anche libre (variable projection), warp et niveau communs, raie étrangère libre ; départs par les triplets des raies les plus hautes (le triplet lu par
le traqueur d'abord) ; rivaux : les autres triplets ; refus « niveau » si une anche est à plus de 22 dB. Le traqueur v62 ne suit parfois aucune des trois voix (11 notes sur 120) : la
seconde lecture ne dépend plus de lui (`certifierGroupe`, note imposée ou voix à moitié suivies ; les voix non suivies le deviennent à la certification). Résultats § 1 (plans trio_calib et trio_valid : 58 et 49 notes posées sur 240 et 192) : 0 faux
sur 725 lectures « sûr » de super musette ; 25 % des notes posées (v63 : 0 ; v62 : 75 % de fausses).

Rôle d'une raie étrangère (cas de l'audit « raie étrangère », trois raies pures de force voisine, test `frequences` F9) : une raie étrangère adoptée dont le niveau est du même ordre
que l'anche la plus faible (moins de 12 dB en dessous) n'est admise que si l'échange de rôle avec chaque anche est nettement pire (LLR ≥ 150) ET si un couplage est ajusté
(|β| ou |m| ≥ 0,03) : sans couplage, rien dans le son ne distingue une anche d'une raie étrangère (l'ajustement lisait +4 et +6 ¢ à 1,7 Δ). Cette règle a remplacé un contrôle
du traqueur à 1 ¢ qui faisait perdre 15 points de notes posées.

### 2.5 (e) Temps de pose

La v63 disait « sûr » après deux ajustements successifs de 3 s, calculés 20 pas par image : médiane 6 s sur le plan de calibration (grille 0,25 s), 4 s à 8 Hz. v64 : ajustements à chaud
(les deux moitiés de la fenêtre, départ = la solution entière, phases recalées au centre de la moitié, continuation sur les partiels), fenêtre visée de 1,5 s (jamais moins que le besoin :
1 battement, 350/f s, K·Ω·T ≥ 1,65), deux ajustements de front, coût des ajustements réduit de 27 % (plan d'expériences sur le coût, § 4.2), la lecture certifiée est elle-même affichée.
Pour Ω ≥ 2 Hz, sans attaque : médiane 1,75 s (p90 3,00 s) pour f0 ≥ 200 Hz, 254 notes sur 280 posées (v63 : 4,00 s, 118 sur 280). Avec attaque de +13 ¢ : la fenêtre ne peut pas toucher l'attaque, le temps compte depuis sa fin (médiane 3,50 s, p90 5,50 s). Une fenêtre qui raccourcit
d'elle-même après un échec (essayée) pose plus tôt (2,25 s au lieu de 2,75 s) mais a donné 3 lectures « sûr » fausses : écartée. Budget de calcul : 200 unités par image de 85 ms (≈ 60 ms
sur un PC de bureau, § 6) ; sur téléphone, 4 fois moins de travail par image : les temps s'allongent d'autant (R9, § 4.5).

### 2.6 (f) Domaine

Ω de 0,2 à 60 Hz certifié (v63 : 25 Hz ; 50 ¢ à A6 font 51 Hz). Résultats : 112 notes (Ω de 0,2 à 60 Hz, rapport jusqu'à 24 dB), 45 posées, 0 lecture fausse (347 lectures « sûr »). Au-dessus de 60 Hz : « anches trop écartées » ; sous 0,2 Hz : « les anches battent à moins de 0,2 Hz : je
lis leur centre, pas chacune » (le traqueur donne le centre, jamais « sûr »). Rapport d'amplitude : la limite sûre est 22 dB, pas plus (plan A, coin Ω = 0,3 Hz, 25 dB, raie étrangère : 2 notes
lues à −3 et −4 ¢ avec un faux modèle ; avant 22 dB aucune) : au-delà, refus « une des anches est plus de 22 dB sous la plus forte ». L'extension annoncée par la mission (22 dB) n'est donc
pas possible ; le refus est expliqué.

### 2.7 (g) Coût (R9), journal, tests

Coût : voir § 4.5. `docs/JOURNAL-DES-VERSIONS.md` : une ligne par version de la v19 à la v64. Tests rétablis : `frequences` (plus de 20 images « sûr » au lieu de 10, les deux cas de
battement sous 1 Hz avec fort couplage assertent « jamais faux, jamais avant l'heure, et la raison est affichée »), M10 de `music` (certificat actif), `lecture` et `ui` sans
le contournement `certificat: { actif: false }`.

### 2.8 Deux garde-fous ajoutés à la fin

**Refus récents sur le niveau.** Sur le plan A, une lecture fausse hors domaine (3 ¢ d'erreur : anche faible à 25 dB, Ω 0,3 Hz, β 0,4, AM 20 %, raie étrangère ; la raie de l'anche faible tombe sur la raie latérale de la forte, l'ajustement échange les rôles
et passe tous les critères une fois sur neuf ajustements). Réglage `REFUS_RECENTS` : une lecture n'est pas posée si 3 des 4 ajustements précédents ont été refusés pour le niveau. Plan d'expériences (3 variantes sur les mêmes plans) : peigne + étiquette + niveau : 0 faux mais
91 notes posées sur 280 au lieu de 116 (plan A de validation) et 199 sur 384 au lieu de 223 ; **niveau seul** : 0 faux, 116 sur 280 et 223 sur 384 (aucune perte). Retenu : niveau seul.

**Un silence efface les certificats.** Après une seconde de silence, la valeur certifiée d'avant restait affichée « sûre » à la première image du son qui reprend (test `courbe` : une image à intensité 0). Le moteur efface maintenant ses états de certificat au silence : le son qui reprend se certifie de nouveau.

### 2.9 (h) Le battement : une valeur précise, stable et fiable (Ewen, 16/10/2026)

Ewen : « les battements oscillent de 2-3 par minute : 25, puis 27, puis 26, puis 25 battements/min : c'est quoi la vraie valeur ? Pour accorder j'ai besoin d'une valeur précise, stable et fiable. »

**Mesure.** Avant, le battement affiché était la médiane glissante de quelques images (v63) : elle suit le bruit de l'agitation de la note. Maintenant (`estimerBattement`, `dsp/certificat.js`) : chaque ajustement de la seconde lecture
donne un battement Ω ; ils sont moyennés sur TOUTE la plage tenue, pesés par la durée de leur fenêtre. L'incertitude est l'écart type entre ajustements divisé par la racine du nombre d'ajustements INDÉPENDANTS (durée couverte
divisée par la durée d'une fenêtre : les fenêtres se recouvrent), au moins 0,09 batt/min. Si le battement varie vraiment (la pression du soufflet), la pente de la droite pesée est significative (plus de 2,5 écarts types) : elle est donnée
à part comme tendance (batt/min par seconde), pas comme bruit.

**Affichage.** Une seule valeur, qui converge (« ✓ 25,8 ± 0,3 bat/min ») ; elle ne change que si l'écart dépasse l'incertitude (hystérésis, au moins 0,2 batt/min) ; arrondie au demi-écart type (0,1 au plus fin) ; « ✓ » quand elle est posée
(trois ajustements indépendants au moins, incertitude sous 0,5 batt/min, deux secondes tenues). Une image où le traqueur perd une anche garde la valeur certifiée (mémoire de 1,5 s) ; la valeur brute du traqueur ne revient pas faire sauter le chiffre
(un défaut de la première version, trouvé au banc : une image sur cinquante à 31 batt/min au lieu de 25, écart type 0,88 batt/min ; corrigé : 0,03). L'écart en cents et le battement en Hz restent affichés.

**Précision atteignable.** La borne de Cramér-Rao du bruit seul est sans intérêt ici : pour 2 s de note et un rapport signal/bruit de 35 dB, elle est de l'ordre de 10⁻⁵ Hz. La précision est limitée par le jeu lui-même (la fréquence
des anches fluctue : agitation du soufflet, vibrato) et par le modèle. Mesurée au banc d'étalonnage (`battement_calib.mjs` : 8 notes de 15 à 90 batt/min dont 2 avec couplage, 6 tirages, 3 780 lectures affichées) :

| durée de la plage tenue | lectures | erreur RMS (batt/min) | ± annoncé moyen | erreur maximale |
|---|---|---|---|---|
| moins de 1,5 s | 5 | 0,02 | 0,03 | 0,02 |
| 1,5 à 2,5 s | 208 | 0,07 | 0,11 | 0,58 |
| 2,5 à 4 s | 925 | 0,07 | 0,09 | 0,58 |
| 4 à 6 s | 1 192 | 0,06 | 0,06 | 0,20 |
| plus de 6 s | 1 455 | 0,05 | 0,05 | 0,20 |

L'incertitude annoncée est de l'ordre de l'erreur réelle (100 % des lectures dans ±2 σ, ou 0,2 batt/min). Les plus grosses erreurs (0,58) sont des premières valeurs avec deux ajustements seulement : la valeur n'est dite « posée » qu'à partir de trois.
La résolution compte aussi : un ajustement a besoin d'au moins une période de battement (25 batt/min = 0,42 Hz = 2,4 s), donc la première valeur « posée » ne vient pas avant 2 à 3 s pour un battement lent ; plus la note est tenue, plus l'incertitude baisse (en 1/√n).

**Avant / après sur le banc** (`battement_stab.mjs`, écart type du battement affiché de la première valeur posée à 8 s, batt/min ; Fa#4 25 batt/min et Do#5 50 batt/min constants, La3 25, Mi4 90) : constants propres 0,00 à 0,28 dans les deux versions (le banc propre est déjà stable) ;
25 batt/min avec couplage β 0,2 (cas où la médiane glissante décrochait de l'enveloppe) : v63 0,85 batt/min (valeur moyenne 26,2, biais +1,2) contre v64 0,03 (25,1). Quand le battement varie vraiment avec la pression (4 batt/min en 5 s, 6 batt/min en 5 s), le chiffre unique
ne peut pas être « stable » : il suit la tendance (pente retrouvée 0,79 et 1,21 batt/min par seconde, vraies 0,80 et 1,20) ; c'est la courbe du battement (v65) qui répond à ce cas.

**Avant / après sur les prises du H6** (`battement_reel.py`, 14/10/2026, notes tenues, écart type du battement affiché, batt/min) : v63 (traqueur seul) sur les 16 notes avec vérité : écart type médian 2,49, moyen 6,63, maximum 37,4 (des notes à battement
rapide ou à attaque où la valeur saute de moitié) ; v64 sur les notes posées (6 notes) : médian 0,20, moyen 0,27, maximum 0,60, avec un écart médian à la vérité du H6 de 0,25 batt/min. Les notes non posées n'affichent pas de valeur certifiée.


### 2.10 La courbe du battement et le battement ramené au niveau (v65, Ewen, 16/10/2026)

Ewen : « afficher juste un battement ne dit pas grand-chose, la pression change avec le soufflet et ça change beaucoup les battements ; il faut peut-être une courbe ; il faut que ce soit lisible. »

**Ce qui s'affiche** (Accorder, mode luthier, sous la courbe d'accordage, seulement quand une note à deux anches bat) : en grand « 26,9 ± 0,1 bat/min » (vert quand la valeur est posée) ; dessous « à −31 dB (niveau de la note) · fixer ce niveau »
et « +1,1 bat/min par dB » (ou « la pression ne change pas le battement ici ») ; en petit « à cet instant 27,9 · −29 dB ». À gauche, la courbe du battement dans le temps (même axe de 15 s que la courbe d'accordage) : les mesures des ajustements (points),
le battement affiché à chaque image (trait fin), la valeur de référence ou la droite « selon la pression » avec sa bande d'incertitude, et le niveau sonore lissé en trace discrète (pointillé). À droite, le nuage « battement / niveau » avec la droite
ajustée, le niveau de référence (trait vertical) et la valeur de référence (rond plein). Survol : une fiche lisible (temps, battement, niveau, battement prédit par la pression).

**Calcul** (`ui/battement-niveau.js`, pur, testé) : le battement de chaque ajustement contre le niveau moyen (en dB) de sa fenêtre ; droite pesée par la durée des fenêtres ; l'incertitude compte les fenêtres indépendantes ; la pente n'est retenue que si l'étendue du niveau
dépasse 3 dB, qu'il y a 5 points au moins et que la pente dépasse 2,5 écarts types. La valeur de référence est le battement à un niveau de référence : le niveau médian de la note (« auto »), ou celui que le luthier fixe d'un clic (`reglages.niveauRefBat`).
Sans pente sûre, la valeur de référence est la moyenne pesée. **Le niveau d'une image ne dit rien de la pression** : deux anches de même force le font battre à 100 % ; il est donc moyenné sur au moins une période de battement (60 / bat/min, de 0,6 à 4 s). Limite
physique : une variation de pression plus rapide qu'une période de battement ne se voit pas dans ce niveau.

**Banc** (`bat_pression.mjs` : deux anches dont la hauteur suit la pression chacune à sa façon, soufflet ±4 dB, 6 tirages par cas ; vérité = la fréquence de chaque anche à chaque instant) :

| cas | pente vraie (bat/min par dB) | pente retrouvée | valeur de référence : erreur (± annoncé) | battement affiché à chaque instant : erreur RMS, v63 / v64 | droite « selon la pression » (v65) |
|---|---|---|---|---|---|
| La4 25 bat/min, κ 0,20 / 0,25 ¢/dB | −0,77 | −0,79 à −0,80 | 0,08 à 0,10 (0,08 à 0,11) | 3,42 / 3,37 | 0,55 |
| Fa#4 40 bat/min, κ 0,15 / 0,30 ¢/dB | −1,93 | −1,95 à −2,04 | −0,13 à −0,53 (0,18 à 0,58) | 8,71 / 7,98 | 1,08 |
| Do#5 60 bat/min, κ 0,20 / 0,22 ¢/dB | −0,39 | −0,39 à −0,40 | −0,02 à 0,02 (0,07 à 0,08) | 1,74 / 1,60 | 0,15 |
| La4 25 bat/min, pression constante | (−0,77) | non retenue (étendue 0,7 dB) | 0,16 à 0,24 (0,06 à 0,07) | 0,24 / 0,27 | — |

Quand le battement suit vraiment la pression, le chiffre affiché par la v63 comme par la v64 (médiane glissante ou moyenne de la plage) s'écarte du battement vrai de 3 à 8 bat/min (RMS) : il retarde sur la pression. La valeur ramenée à un niveau de référence est juste à
0,1 bat/min près, et la droite « selon la pression » suit le battement vrai à 0,15 à 1,1 bat/min près. Dans le cas à pression constante, l'écart de 0,2 vient des ±0,3 dB de niveau qui restent (0,77 × 0,3 = 0,2) : la pente n'est pas retenue, la valeur reste dans la bande de l'incertitude du niveau.

**Prises du H6** (`battement_niveau_reel.py`, 14/10/2026, 12 notes avec un battement mesuré) : pente significative sur 3 notes (Si3 −0,88 ± 0,22, Ré4 −3,08 ± 0,33, La4 −0,73 ± 0,14 bat/min par dB ; étendue du niveau 3,3 à 3,7 dB) : sur ces notes le battement dépend réellement de la
pression, de 3 à 11 bat/min sur 3,7 dB pour Ré4. Valeur de référence contre le verrou de phase du H6 (9 notes avec vérité) : écart médian 0,07 bat/min, contre 0,18 pour la moyenne simple.

**Lisibilité** : grands chiffres tabulaires (jusqu'à 56 px), peu de texte, unités en clair (bat/min, dB), couleurs des jetons du thème (clair et sombre), aucune couleur en dur ; le chiffre ne change que si l'écart dépasse l'incertitude.

**Survol des graphes (le « carré noir »).** Dans le mode recherche (`ancien.html`) et dans la version de la thèse, la fiche de lecture au survol de la courbe d'accordage avait un fond noir fixe (`rgba(16,20,26,0.92)`) et un texte de la couleur du thème : en thème clair, du noir sur du noir,
un rectangle sombre au bout du trait vertical (la capture d'Ewen du 14/10). Corrigé : fond et texte du thème, cadre, une ligne par anche avec sa pastille, placée dans le tracé. Dans l'interface principale (`ui/composants/infobulle.js`) : la fiche prend les couleurs du thème
si leur contraste est d'au moins 4,5, sinon un couple sûr (couleurs système), reste dans le tracé et ne se dessine jamais vide ; le même composant sert à la courbe du battement. Captures avant / après : `test/outils/capture/` (`serveur.mjs`, `ancien.html`, `courbe.html`, `battement.html`, `prise.sh` : Chrome sans fenêtre).

## 3. Les critères d'une lecture « sûre » (C1 à C12, v66)

| | Critère | Seuil (`CERT`) |
|---|---|---|
| C1 | pas de plage de zéros dans la fenêtre lue (R11) | 0,4 ms |
| C2 | peigne sain : résidu relatif, plancher entre les raies, indice de phase β, indice d'amplitude m | r ≤ 0,05 ; ≤ −28 dB ; β ≤ 0,45 ; m ≤ 0,3 |
| C3 | résolution des raies (K_utile pour trois anches) ; la fenêtre vise au moins un battement (`NB_MIN` = 1, règle de fenêtre, non testée par `juger`) | K·Ω·T ≥ 1,5 |
| C4 | étiquette : rapport de vraisemblance, raie de l'anche faible contre la raie latérale qui la recouvre, rôle de la raie étrangère | LLR ≥ 25 ; ≥ −20 dB ; voir 2.4 |
| C5 | niveau : aucune anche à plus de 22 dB sous la plus forte ; et jamais « sûr » si 3 des 4 ajustements précédents ont été refusés pour le niveau (§ 2.8) | 22 dB ; 3 sur 4 |
| C6 | stabilité : dérive mesurée sur les deux moitiés de la fenêtre | ≤ 0,5 ¢/s ou 0,6 ¢ sur la fenêtre |
| C7 | âge : |dérive| × âge du milieu de la fenêtre (vit dans `certAccord`, pas dans `juger`) ; marge 3 σ + 0,02 ¢ essayée en v66, éteinte (`SIGMA_TOL_C`) | ≤ 0,3 ¢ |
| C8 | (abandonné en v64 : `ACCORD_C` = 1e9, le traqueur ne contrôle plus la seconde lecture) | - |
| C9 | répétabilité : les deux moitiés de la fenêtre (ajustement chaud de chacune), ou deux fenêtres décalées de 0,5 s | 0,4 ¢ ; 0,3 ¢ |
| C10 | horloge du micro connue | ≤ 100 ppm (0,17 ¢) |
| C11 | (v66) pas de contradiction : toute lecture complète ou sentinelle plus récente s'écarte du certificat d'au plus max(0,3 ¢, 3 σ) + la dérive | `CONTREDIT_C`, `SENT_SIGMA` 4 |
| C12 | (v66) Ω ≥ 0,8 Hz pour la hauteur sûre (raison `lent`), ≥ 0,4 Hz pour le battement ; trois anches : écarts différents de plus de 5 % (`ident3`), aucune anche à plus de 35 dB (`absente`) | voir § 0 |

Fenêtre : au moins max(0,6 s ; 1 battement ; 350 / f s ; 1,65 / (K·Ω) s), visée à 1,5 s, jamais plus de 4 s. Un ajustement qui contredit le certificat en cours de plus de 0,5 ¢
l'invalide ; il faut alors deux fenêtres décalées d'accord (pas seulement les deux moitiés) pour en poser un autre.

## 4. Les plans d'expériences (règle 12 d'Ewen : jamais un facteur à la fois)

### 4.1 Criblage des réglages (PB12) et plan de calibration

Plackett-Burman à 12 essais sur 11 réglages (`crible_v64b.csv`, `doe_cert.py`, 4 répétitions de 80 notes) : les essais sans veto de l'accord traqueur (ACCORD_C à 10⁹), avec fenêtre maximale de 1,5 s et confirmation par les deux moitiés
posent 161 à 182 notes de 240 (médiane de 2,0 à 4,0 s) contre 56 à 126 pour ceux qui gardent le veto de l'accord (3,25 à 4,75 s), sauf l'essai 2 (82 notes) ; seul cet essai 2 (accord éteint, fenêtre de 3 s, sans moitiés) a produit une lecture fausse (1). Le meilleur essai (4 : accord éteint, fenêtre adaptative, 1,5 s, confirmation par les moitiés) pose 167 notes en 2,0 s de médiane. Résultats complets : `crible_b.log`, plan `crible_v64b.csv`.

### 4.2 Coût de calcul (plan factoriel 2^(4-1) sur tol, iterEtape, nDeparts, nLibre, nGarde)

Le coût d'un ajustement va de 459 à 984 milliers de partiels-échantillons selon l'essai (`cout2.csv`, `fit_cout.mjs`) ; les réglages retenus (tolérance 10⁻⁴, 5 itérations par étape, 5 départs, 2 anches libres) réduisent le coût de 27 % par rapport à la v63 à qualité égale (zéro faux, même nombre de notes posées).

### 4.3 Plans de validation (conditions jamais vues au réglage)

Voir § 1 : validation (64 conditions × 6), conditions neuves (150 × 3), réaliste (160 × 10), adverse (60 × 3), coins (plan A) et plan A de validation. 0 faux partout avec la règle des refus récents (§ 2.8).

### 4.4 Plan C : traitement du micro (porte, suppression de bruit, compression, ronflement, horloge)

16 cellules (plan fractionnaire sur la chaîne du micro, `runC.mjs`), 20 notes par cellule :

| horloge | notes posées (sur 320) | lectures « sûr » | fausses | erreur maximale | « sûr » dans les cellules à +150 ppm |
|---|---|---|---|---|---|
| inconnue (aucune mesure) | 45 | 534 | 0 | 0,36 ¢ | 0 |
| mesurée à 30 ppm | 94 | 1 073 | 0 | 0,36 ¢ | 541, toutes justes |

Horloge inconnue : jamais « sûr » dans une cellule à +150 ppm (la raison « horloge » est affichée). Horloge mesurée : la correction ramène les cellules à +150 ppm à moins de 0,36 ¢.

### 4.5 Coût sur téléphone (R9)

`cpu63.mjs` : un ajustement à froid coûte 150 à 1 000 ms (deux anches) et 240 à 2 300 ms (trois anches) sur ce PC ; à chaud (point de départ connu) 18 à 175 ms (deux anches), 50 à 650 ms (trois anches), 20 à 60 pas de Levenberg-Marquardt.
Le budget par image de l'application est de 40 ms (`MS_PAR_IMAGE`), les ajustements s'étalent sur plusieurs images. Un téléphone de milieu de gamme est compté à 4 fois ce PC : un ajustement à chaud de 1,5 s à 4 à 12 Hz (67 ms) prend 270 ms, soit 7 images ; les temps de pose
s'allongent d'autant, ils ne deviennent pas faux (le budget est du temps, pas de la précision). Non mesuré sur un téléphone réel : la proportion de 4 est une estimation.


## 5. Prises réelles du 14/10/2026

Prises du 14/10/2026 (27 notes ; vérité : verrou de phase du Zoom H6, ±0,1 ¢), rejouées par `reel_prises.mjs` avec le moteur final (validation seulement : aucun seuil n'a été réglé dessus, sauf β, remis à 0,45 parce qu'elles ont attrapé La5) :

| prise | notes posées | lectures « sûr » | fausses (plus de 0,5 ¢) |
|---|---|---|---|
| H6, canaux L+R | 7 sur 27 | 103 | 0 |
| H6, canal gauche | 6 | 134 | 0 |
| H6, canal droit | 5 | 65 | 0 |
| PC (micro USB, effet vocal de Windows) | 0 | 0 | 0 |
| H6, certificat éteint (traqueur v62) | 13 | 336 | 42 (4 premières lectures fausses) |

Le contre-exemple du 14/10 (La5 à −1 ¢, Ré5 à +1,5 et +4 ¢, Mi4 à −0,7 ¢) n'est plus posé : le certificat refuse ces notes (refus expliqués à l'écran). La couverture réelle est de 7 notes sur 27 : le reste est refusé (anche trop faible, attaque,
battement trop lent), ce qui est le prix du zéro faux. La prise PC reste à 0 « sûr » (état à +0,9 ¢ non détectable dans le signal, protégé par le contrôle de prise ; voir `docs/PRISE-DE-SON.md`).

Battement affiché sur ces prises : § 2.8.


## 6. Ce qui reste, et la limite physique

- **Pose lente** : pour f0 < 250 Hz, Ω < 2 Hz et après une attaque, la pose prend 3 à 5 s (la fenêtre ne touche pas l'attaque ; un battement lent demande au moins une période). Limite de la physique, pas du réglage.
- **Super musette** : 24 à 26 % des notes posées (v63 : 0), 0 faux ; les autres sont refusées (anche à plus de 22 dB sous la plus forte, battement de l'anche basse trop proche de celui de la haute).
- **Domaine** : Ω de 0,2 à 60 Hz, anche faible à 22 dB au plus. Au-delà : refus expliqué (« anches trop écartées » ; « les anches battent à moins de 0,2 Hz » ; « une des anches est plus de 22 dB sous la plus forte »). Étendre à 25 dB fait lire des raies latérales
  pour l'anche faible (plan A) : impossible sans faux.
- **Prise PC** : un état de la capture Windows à +0,9 ¢ au-dessus de la ligne de base n'a aucune signature dans le signal ; seule une prise de contrôle (H6 et PC en même temps) dira s'il vient du rééchantillonneur. Question posée à Ewen.
- **Horloge** : la mesure automatique prend une minute à l'écoute ; un micro dont l'horloge est instable (plus de 30 ppm entre deux moitiés) n'est jamais « sûr ».
- **Téléphone** : coût estimé (4 fois ce PC), à mesurer sur un appareil réel.
- **Battement** : le chiffre unique ne peut pas être stable quand la pression le fait vraiment varier ; la courbe du battement et le battement ramené à un niveau de référence sont en v65.
- **Couverture réelle** : 7 notes sur 27 sur les prises du H6.


## 7. Rejouer

```
node test/outils/pose/eval63.mjs --plan=lhs300_calib.csv --reps=4 --nls=0 --out=r.json       # moteur + certificat, verdict de l'interface (VERITE=porteuse pour la porteuse)
python test/outils/pose/tableau64.py "libellé=r.json"                                          # le tableau de la section 1
node test/outils/pose/eval63.mjs --plan=trio_calib.csv --n=3 --reps=2 --out=t.json             # super musette
CALIB=2 node test/outils/pose/runC.mjs --out=c.json                                            # plan C (CALIB=1 : horloge calibrée sans erreur ; sans : inconnue)
node test/outils/pose/reel_prises.mjs --src=h6|h6L|h6R|pc [--prise=0] [--ppm=-125 --incert=40] # prises réelles du 14/10
node test/outils/pose/pc_vs_h6.mjs --essai=1|2                                                  # prise PC contre H6 sur les mêmes fenêtres
node test/outils/pose/cpu63.mjs ; node test/outils/pose/etalon_cout.mjs                          # coût (R9)
node test/outils/pose/battement_calib.mjs                                                      # étalonnage de l'incertitude du battement (§ 2.9)
node test/outils/pose/bat_pression.mjs ; python test/outils/pose/battement_niveau_reel.py reel.json             # v65 : le battement contre la pression (§ 2.10)
node test/outils/pose/battement_stab.mjs                                                       # écart type du battement affiché, v63 contre v64
python test/outils/pose/battement_reel.py reel_h6_v63.json reel_h6.json                        # idem sur les prises du H6 (reel_prises.mjs --out=...)
python test/outils/pose/doe_cert.py plans/crible_v64b.csv --base '{...}' --sortie dossier      # plan d'expériences sur les réglages
node test/certificat.test.mjs ; node test/horloge-auto.test.mjs                                  # tests
```
