# Certificat des lectures « sûres » (v66, 16/10/2026)

Audit Fable du 15/10/2026 (`J:\claude\audits\2026-10-17-accordeur-fable\RAPPORT-AUDIT.md`, R1 à R14) puis ses suites du 16/10 (critères d'Ewen : niveau professionnel,
musette et super musette, Do2 à A6, tout micro USB, pose courte, refus expliqués). Règle d'Ewen : un accordeur professionnel ne dit « sûr » que s'il peut le prouver ;
zéro lecture « sûre » fausse (erreur de plus de 0,5 ¢ sur une anche), avec n'importe quel micro. Journal des versions : `docs/JOURNAL-DES-VERSIONS.md`.

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
