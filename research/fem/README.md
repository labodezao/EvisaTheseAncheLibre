# Éléments finis et recalage : de la mesure de l'anche au modèle

Commencé le 03/10/2026. Elmer 26.2 (`elmer_outils.py` le trouve ; variable `ELMER_DOSSIER`
pour un autre dossier), Gmsh 4.15 dans `J:\claude\venv`. Les calculs bruts vont dans
`J:\claude\calculs\` (hors du Drive).

## L'architecture, en 3 lignes

1. **Les éléments finis** donnent les modes de la languette (fréquences, masse, raideur et forme modales) et l'impédance de la chambre vue depuis la fente.
2. **Le modèle semi-analytique** (`banc_recherche/coupled_reeds.py`) fait l'auto-oscillation avec ces paramètres : seuil, fréquence de jeu, débit.
3. **Le recalage** (`recalage.py`) confronte les deux aux mesures (son pincé, banc des seuils) et corrige ce qui est le moins sûr (épaisseur, levée).

Ce que les éléments finis ne font PAS ici : l'air qui passe entre la languette et la plaque.
C'est un jet, non linéaire, à sens unique. Il reste dans le modèle semi-analytique. Elmer donne
seulement la réponse passive de l'air de la chambre et les modes de la languette dans le vide.

Conditions initiales : rien d'autre à mesurer. Il faut la levée du bout au repos (dans la banque)
et la rampe de pression (le modèle part au repos et suit la pression, comme le banc).

## La marche à suivre, en 5 étapes

1. **Mesurer** l'anche (le geste d'Ewen) : longueur libre, largeur au pied et au bout, épaisseur
   en 5 points, masse au bout (et ses 3 dimensions si oui), position du rivet, fente (longueur,
   largeur), épaisseur de plaque, levée au repos, note, intérieure ou extérieure, numéro de chambre.
   Et le **son pincé** au téléphone : 3 à 5 pincements, en laissant le son s'éteindre entre deux
   (3 s pour un grave).
2. **Remplir la banque** `anche/banque_anches.csv` (ou avec reedgui), puis produire le yaml :
   `J:\claude\venv\Scripts\python.exe -m banc_recherche.banque_anches fem\anche\banque_anches.csv --yaml fem\anche\anches_r12.yaml`
   (depuis `research\`). L'importeur dit les erreurs d'unités et ce qui reste à mesurer.
3. **Calculer** (depuis `research\fem\`) :
   `anche\languette_modes.py --anches` (modes de chaque languette, 10 s) ;
   `sommier\impedance_fente.py --yaml anche\anches_r12.yaml` (impédance vue par la fente, 4 à 8 min par chambre).
4. **Mesurer au banc** les seuils (module « Seuils » de l'application, PR #30) et exporter le CSV ;
   mettre son nom dans la colonne `seuils_csv` de la banque, et le son pincé dans `son_pince`.
5. **Recaler** : `recalage.py` (ou `--recaler-levee`). Il sort `resultats/recalage.csv` :
   écarts de fréquence, d'amortissement, de seuil et de fréquence de jeu, et les paramètres
   recalés (facteur d'épaisseur, E apparent, levée).

## La banque d'anches, mode d'emploi pour Ewen

1. Une ligne `anche` : le nom (id), puis ce que tu sais. Une case vide = pas encore mesuré.
2. Puis une ligne `troncon` par morceau, du rivet au bout : longueur, largeur début et fin, épaisseur début et fin, matériau.
3. Tout en mm, virgule ou point. Les 5 épaisseurs au palmer font 4 tronçons (de la 1 à la 2, etc.).
4. Une valeur avec `?` (`la3?`) est une estimation : elle sert, mais reste « à mesurer ».
5. Lancer l'importeur (étape 2) : il dit ce qui cloche, en français, ligne par ligne.

Fichiers : `anche/banque_anches.csv` (exemple : l'anche de `matrix.txt` de reedgui, Ewen 2020,
plus deux anches nominales), `anche/banque_anches_modele.csv` (modèle vide). Colonnes :
`type ; id ; longueur_mm ; largeur_debut_mm ; largeur_fin_mm ; epaisseur_debut_mm ; epaisseur_fin_mm ;
materiau ; instrument ; rang ; note ; sens ; position ; chambre ; levee_mm ; fente_longueur_mm ;
fente_largeur_mm ; plaque_mm ; masse_bout ; rivet_mm ; son_pince ; seuils_csv ; date ; source`.
Le yaml `anche/anches_r12.yaml` est PRODUIT : ne pas le modifier à la main.

## Ce qui a été vérifié (03/10/2026, Elmer 26.2)

| Vérification | Attendu | Obtenu |
|---|---|---|
| Boîte rigide 50 x 15 x 10 mm, mode 1 | c/2L = 3 430,0 Hz | 3 430,0 Hz |
| Chambre 12 du R12, modes 1 et 2 (9.0 le 03/10) | 1 574,5 et 2 016,6 Hz | 1 574,5 et 2 016,6 Hz |
| Conduit 100 mm, impédance vue du bout (Helmholtz) | i.rho.c.tan(kL)/S | écart 1,3e-5 |
| Poutre acier 30 x 3,5 x 0,3 mm, Euler-Bernoulli exact | formule de `material.py` | à 2e-6 près, 5 modes |
| Même poutre, Elmer 3D (hexaèdres 20 nœuds) | Euler-Bernoulli | +0,7 à +0,9 % (effet de plaque, attendu) |
| Anche de `matrix.txt` (4 tronçons, masse au bout), mode 1 | Euler-Bernoulli exact 67,47 Hz | Elmer 67,72 Hz (+0,4 %) ; Rayleigh-Ritz 5 modes +6 % ; km.py 2 modes +51 % |
| Poutre de section carrée 0,3 x 0,3 mm (pas d'effet de plaque) | Euler-Bernoulli 279,40 Hz | Elmer 279,76 Hz (+0,13 %) |
| Lame de la CAO 2019 (Code_Aster : 144,4 Hz) | Euler-Bernoulli 25,09 Hz | Elmer 25,23 Hz ; Code_Aster verrouillé (×5,7) |
| Déformée modale d'Elmer contre Euler-Bernoulli (masse au bout) | | 0,09 % (après correction des unités, 03/10/2026) |
| Même anche, modes 2 à 5 | Euler-Bernoulli | Elmer à 0,03 à 1,1 % |
| Maillage de la languette (3 finesses) | convergence | 67,82 / 67,72 / 67,69 Hz |
| Encastrement au rivet (talon appuyé) contre encastrement parfait | | -0,3 % |
| Chambre 1, pôles de l'impédance contre modes propres | 1 142,1 et 1 402,3 Hz | 1 139,7 et 1 402,1 Hz |
| Son pincé de synthèse (67, 440, 880 Hz), aussi après compression m4a | f, zeta | f à 1e-4, zeta à 3 % |

Détails : `anche/resultats/verification_languette.csv`, `convergence_languette.csv`,
`sommier/resultats/verification_elmer.csv`.

## Les fichiers

| fichier | rôle |
|---|---|
| `elmer_outils.py` | chemin d'Elmer, lancement, lecture des valeurs propres |
| `anche/languette_modes.py` | Gmsh + Elmer : modes de la languette (`--verif`, `--convergence`, `--anches`) |
| `anche/banque_anches.csv`, `anches_r12.yaml` | la banque (Ewen) et le yaml produit |
| `sommier/impedance_fente.py` | Elmer Helmholtz : impédance vue par la fente, résonateurs (`--verif`, `--yaml`) |
| `sommier/chambre_modes.py`, `seuils_cavite.py` | modes des 12 chambres, plan de seuils (PR #31) |
| `recalage.py` | le tableau des écarts et des paramètres recalés |
| `../banc_recherche/languette.py` | la languette : Euler-Bernoulli exact, Rayleigh-Ritz, pont vers `coupled_reeds` |
| `../banc_recherche/banque_anches.py` | la banque : importeur, contrôles, yaml |
| `../banc_recherche/pince.py` | le son pincé : fréquence et amortissement (wav, m4a par ffmpeg) |
| `../reedgui/` | l'interface pour décrire une anche |
| `recalage_rk4.py` | recalage Elmer <-> modèle RK4 (`reed_model`, `FreeReedModel`, `coupled_reeds`) |
| `../banc_recherche/pince_modes.py` | le son pincé, TOUS les modes : fréquence et amortissement (ESPRIT par bande) |
| `comparer_pince.py` | anche seule et anche sur sa chambre, pincées, contre Elmer : épaisseur, zeta, kappa, trou, pertes |
| `souffle.py`, `plans/feuille_soufflerie_modele.csv` | la soufflerie : seuils par escalier, fréquence de jeu (`recalage.py --souffle`) |
| `figures_these.py` | figures du manuscrit (maillage et verrouillage, analyse du son pincé) |
| `lot.py`, `cache.py`, `plans/` | calculs en lot avec cache (`J:\claude\calculs\cache\`) |
| `sommier/etude_impedance.py` | méthode, maillage et solveur de l'impédance : temps et précision |
| `sommier/optimisation_r12.py`, `notes_r12.csv` | proposition de cotes pour les chambres du R12 (notes hypothétiques) |

## Les anciens projets Elmer d'Ewen (2020-2021)

- `Simulations d'anche (Elmer)\bass_reed` : modes d'une anche grave (STL, Netgen, tétraèdres
  linéaires, acier 200 GPa, talon tenu par dessous sur 8,35 mm). Tourne sur 26.2 en remplaçant
  MUMPS (absent de la 26.2) par Umfpack : 140,1 / 885,9 / 1 500,2 / 2 089,9 / 6 819,3 Hz. Les
  tétraèdres linéaires raidissent une plaque mince : ces fréquences sont probablement trop hautes.
  Repris : l'idée de tenir le talon par sa face du dessous (notre encastrement « rivet »).
- `Simulations d'anche (Elmer)\Reed_with_cav` : géométrie anche + cavité (FreeCAD, 4 corps), jamais
  calculée (aucun solveur actif). La CAO complète est sur `E:\Archives\Ingénierie et recherche\studies\bass_reed`
  (STEP, IGES, maillage Salome, Code_Aster) : ce n'est pas un doublon, à garder.

## Limites (ce qui pourrait rendre ces résultats faux)

- Les anches médium et aiguë de la banque sont NOMINALES (lames uniformes) ; celle de `matrix.txt` est réelle, sans levée ni fente mesurées.
- Le jet dans la fente est dans le modèle semi-analytique, avec ses hypothèses (`coupled_reeds.py`, `docs/audit_deux_anches.md`).
- L'impédance est sans pertes : les pics réels seront moins pointus. Seul le premier résonateur va dans le réseau ; le mode « case A contre case B » est calculé mais pas encore branché.
- La fente est centrée sur la plaque par défaut : sa vraie place (et le côté de la pointe) est à mesurer.
- L'amortissement du son pincé est celui sans souffle ; un téléphone peut le fausser (gain automatique) : comparer un pincement faible et un fort.

## Recalage expérimental : une vraie anche, puis son sommier (04/10/2026)

Le protocole complet, avec les étapes pour l'atelier : `../docs/protocole_recalage_experimental.md`.
La version de thèse : `../docs/design_theory.lyx`, chapitre « Static and modal analysis », sections
« Finite element model with fluid structure interraction »,
« Updating the time-domain model... » et « Experimental model updating... ».

| geste | outil | ce qu'on recale | ce qui juge le modèle |
|---|---|---|---|
| (a) anche seule pincée | `comparer_pince.py ID --seule son.wav` | épaisseur (ou E), zeta1 et zeta2 | rapports f2/f1, f3/f1 (à 3 %) |
| (b) anche pincée sur sa chambre | `comparer_pince.py ID --seule ... --cavite son.wav` | kappa (part du volume balayé qui passe par la chambre), longueur effective du trou, pertes R | signe et taille du décalage, fréquence du résonateur |
| (c) soufflerie | `souffle.py feuille.csv`, puis `recalage.py --souffle ID feuille.csv --recaler-levee` | levée au repos (par p_on) | p_on/p_off, fréquence de jeu contre fréquence pincée sur la chambre |

Prédictions avant mesure (kappa = 1, réseau d'Elmer) : sur sa chambre, la languette pincée est plus
grave de 1,2 cent (grave), 2,8 (médium), 3,5 (aigu) ; résonateurs à 1 140, 1 453 et 1 574 Hz.
Vérifié sur des sons de synthèse (`tests/test_pince_modes.py`) : f à 1e-4, zeta à 3 %, résonateur
de chambre à Q = 20 à 5 %, harmonique 2 reconnu, 50 Hz écarté ; kappa², trou et pertes retrouvés.
`ReedModel` accepte maintenant un zeta par mode (`zeta=[z1, z2]`).

## Recalage entre Elmer et le modèle Runge-Kutta 4 (`recalage_rk4.py`)

Une commande : `J:\claude\venv\Scripts\python.exe recalage_rk4.py --amplitude` (depuis
`research\fem\`, 5 à 10 min ; les calculs Elmer sont en cache). Sorties :
`resultats/recalage_rk4_languette.csv`, `_cavite.csv`, `_couple.csv`, `recalage_rk4.png`.
Tests : `tests/test_recalage_rk4.py`.

Le modèle RK4 de référence est `banc_recherche/reed_model.py` (port du MATLAB
`RK4ode45cavity_reed_socket`). Le MATLAB calculait des moyennes (`bmoy`, `hmoy`, `Emoy`,
`romoy`) divisées par le nombre de colonnes (5) au lieu du nombre de tronçons : son modèle
à 1 degré de liberté (raideur 3EI/L³, pulsation estimée, pas de temps) en était faussé.
Le port Python ne reprend pas ce calcul (test `test_largeur_moyenne_sur_les_troncons`).
`reed_model` lui-même n'auto-oscille pas (loi de cavité inversée, `docs/audit_modele_anche.md` ;
surpression moyenne simulée -71,5 kPa) : le couplé se compare avec son successeur RK4
`reed_oscillator.FreeReedModel`, et avec `coupled_reeds`.

**1. La languette.** `reed_model` projette sur 2 modes de poutre uniforme (`modal.assemble`).
Option ajoutée : `ReedModel(..., modal_params=p)` et `FreeReedModel(..., modal_params=p)`,
avec `p` = masse, raideur et projection modales du mode 1 ramenées au bout, tirées d'Elmer
(`languette.parametres_modaux` avec la déformée d'Elmer).

| Languette | f1 reed_model (2 modes) | f1 Euler-Bernoulli | f1 Elmer | masse au bout : écart | raideur au bout : écart | MAC mode 1 |
|---|---|---|---|---|---|---|
| `SECTIONS_DEFAULT` (charnière 45 µm) | 102,1 Hz | 15,6 Hz | 15,9 Hz | +43 % | ×59 | 0,816 |
| `matrix.txt` (R12-grave) | 102,1 Hz | 67,4 Hz | 67,7 Hz | +4,7 % | ×2,4 | 0,995 |
| médium nominal (uniforme) | 439,9 Hz | 439,9 Hz | 444,0 Hz | +0,4 % | -1,4 % | 1,0000 |
| aigu nominal (uniforme) | 880,4 Hz | 880,4 Hz | 891,7 Hz | +0,6 % | -2,0 % | 1,0000 |
| CAO 2019 (« grande masse ») | 61,5 Hz | 25,1 Hz | 25,2 Hz | +5,3 % | ×6,3 | 0,992 |

Après recalage (paramètres d'Elmer injectés), l'écart est nul par construction. Ce que dit
le tableau : 2 modes de poutre uniforme suffisent pour une lame uniforme (écart d'Elmer à
Euler-Bernoulli : effet de plaque, +0,9 à +1,3 %), pas pour une anche grattée. L'erreur est
dans la RAIDEUR (la charnière mince ne peut pas plier), pas dans la masse.

La référence Code_Aster de 2019 (144,4 Hz) est elle-même fausse : son maillage (le même que
`bass_reed`, tétraèdres linéaires, une couche dans 0,10 mm d'épaisseur) se verrouille en
cisaillement. Sur la même géométrie, relue sur ce maillage : Euler-Bernoulli 25,1 Hz, Elmer
en hexaèdres quadratiques 25,2 Hz ; Code_Aster est 5,7 fois trop haut (rigidité ×33).
`bass_reed` tourne sur Elmer 26.2 (Umfpack) : 140,1 Hz avec ses E et rho (200 GPa,
7850), soit 144,0 Hz ramené à ceux de Code_Aster : même maillage, même erreur.

**2. La cavité.** `reed_model` : cavité fermée de 7,875 cm³ (35 x 15 x 15 mm), vue de l'anche
une pure compliance. Elmer : la chambre du R12 et son trou de table, vus depuis la fente.

| Anche (chambre) | bande | écart de Z, avant | écart, 1 résonateur | écart, 2 résonateurs | V : avant → calé | trou l_eff |
|---|---|---|---|---|---|---|
| grave (1) | 50-271 Hz | 12 400 % | 0,0 % | 0,5 % | 7,875 → 17,79 cm³ | 25,8 mm |
| médium (6) | 222-1673 Hz | 494 % | 8,9 % | 0,07 % | 7,875 → 12,45 cm³ | 22,7 mm |
| aigu (12) | 446-1816 Hz | 232 % | 4,4 % | 0,11 % | 7,875 → 7,93 cm³ | 30,4 mm |

(écarts médians de |Z| dans la bande de l'anche, [f1/2 ; 4 f1] bornée sous le 2e pôle)

Ce qui change : à la fréquence de l'anche, la chambre réelle, ouverte par son trou de table,
se comporte comme une MASSE d'air (phase +90°), la cavité fermée de `reed_model` comme un
RESSORT (phase -90°). Le 2e résonateur est le mode « case A contre case B » ; c'est le
premier (volume effectif, longueur effective du trou) qui va dans le réseau de `coupled_reeds`.

**3. Le couplé.** Voir `resultats/recalage_rk4_couple.csv`. Le seuil, la fréquence de jeu
(écart à la lame, en cents) et l'amplitude à 1,5 fois le seuil, pour : `FreeReedModel` avec
ses ingrédients d'origine, le même recalé (languette et volume d'Elmer), et `coupled_reeds`
avec le réseau d'Elmer. Les modèles à cavité fermée font jouer la note AU-DESSUS de la lame
(+33 à +43 cents pour le grave), le réseau avec le trou EN DESSOUS (-4 à -8 cents). C'est la
mesure au banc (module Seuils, son pincé) qui tranchera ; la colonne `mesure_banc` attend.

À 1,5 fois le seuil (pression), demi-course du bout : grave 0,14 / 0,16 / 0,13 mm, médium
0,22 / 0,22 / 0,63 mm, aigu 0,34 / 0,35 / 0,76 mm (FreeReedModel d'origine / recalé /
coupled_reeds). Seuils : grave 52 / 9 / 44 Pa, médium 188 / 181 / 130 Pa, aigu 2 932 /
3 126 / 367 Pa. Les deux familles de modèles divergent surtout pour l'aigu : c'est là que le
trou de table (absent des modèles à cavité fermée) pèse le plus.

## Des calculs Elmer plus justes et plus rapides (03/10/2026)

**La languette.** Hexaèdres quadratiques (20 nœuds), maillage structuré (`languette_modes.py`).

| Cas | nœuds | temps de résolution | f1 de `matrix.txt` | écart à Euler-Bernoulli |
|---|---|---|---|---|
| `bass_reed` 2020 (tétraèdres linéaires, autre lame) | 19 408 | 123 s | (lame CAO : 144 Hz au lieu de 25) | ×5,7 (verrouillage) |
| hexaèdres 20, maille 1 mm (rapide) | 1 442 | 0,8 s | 67,82 Hz | +0,5 % |
| hexaèdres 20, maille 0,5 mm (défaut) | 5 973 | 3,0 s | 67,72 Hz | +0,4 % |
| hexaèdres 20, maille 0,25 mm (référence) | 20 269 | 18 s | 67,69 Hz | +0,3 % |

L'écart restant à Euler-Bernoulli n'est pas une erreur de maillage : c'est l'effet de plaque
(une lame large raidit un peu en flexion, coefficient de Poisson). Preuve : sur une section
carrée (0,3 x 0,3 mm), Elmer = Euler-Bernoulli à 0,13 % ; sur la lame de 3,5 mm de large,
+0,77 %. La plaque ou la coque n'apportent rien de plus ici : le 3D quadratique est déjà
rapide (moins de 4 s) et donne aussi la torsion et la flexion dans le plan.

**Les chambres et l'impédance** (`sommier/etude_impedance.py`, chambre 1, fente du grave).
Méthode « rapide » : les pôles viennent des modes propres (un seul calcul), les résidus de 14
fréquences harmoniques loin des pôles, puis Z(f) par la forme de Foster.

| Variante | nœuds | temps | f1 (Hz) | V effectif (cm³) | écart de Z au balayage (médiane) |
|---|---|---|---|---|---|
| AVANT : balayage de 70 fréquences, maille 2 mm, direct | 25 086 | 487 s | 1 139,71 | 17,79 | référence |
| rapide, maille 3 mm, itératif | 9 455 | 20 s | 1 140,64 | 17,69 | 0,35 % |
| rapide, maille 2 mm, direct | 25 086 | 106 s | 1 139,73 | 17,70 | 0,017 % |
| rapide, maille 2 mm, itératif (défaut) | 25 086 | 53 s | 1 139,73 | 17,70 | 0,017 % |
| rapide, maille adaptée 3 → 0,8 mm (fente, trou), itératif | 55 175 | 164 s | 1 138,80 | 17,69 | 0,38 % |
| rapide, maille 1,2 mm, itératif | 96 091 | 304 s | 1 139,01 | 17,69 | 0,30 % |

Sur le même maillage, la méthode rapide redonne le balayage à 0,017 % : elle est juste.
Convergence : f1 se stabilise vers 1 138,8 à 1 139,0 Hz ; la maille de 2 mm est à +0,06 %, celle
de 3 mm à +0,15 %, le volume effectif bouge de moins de 0,1 %. Le maillage adapté près de la
fente et du trou n'apporte pas plus que la maille uniforme et coûte plus (la fente occupe une
grande surface). Le solveur itératif (BiCGStab(l), ILU1) divise le temps par deux à résultat
identique, avec repli automatique sur le direct. Plus fin que 0,8 mm : Umfpack manque de
mémoire (140 000 nœuds). Gain : 487 s → 53 s (×9) à précision égale, 20 s (×24) à 0,15 %.

**Le lot avec cache** (`lot.py`, `cache.py`) : un plan JSON (exemple : `plans/exemple_trou_ch12.json`)
fait cotes → maillage → calcul → CSV, et ne recalcule que ce qui a changé (empreinte des
entrées et de la version d'Elmer). Exemple : 13,8 s au premier passage, 1,3 s au second.

## Optimisation des chambres du R12 (`sommier/optimisation_r12.py`) : une PROPOSITION

Une commande (depuis `research\fem\sommier\`) : `J:\claude\venv\Scripts\python.exe optimisation_r12.py`
(10 à 15 min, Elmer en cache). Sorties : `resultats/optimisation_r12.csv`,
`resultats/proposition_cotes_R12.json` (ProfCase pour `sommier.py --set`, trou de table, cale).
Rien n'est changé dans ZW3D ni dans `sommier.py`.

Le but par chambre, la méthode et les bornes sont dans l'en-tête du script. Les NOTES SONT UNE
HYPOTHÈSE (`sommier/notes_r12.csv` : un rang diatonique en sol) ; les bornes (trou de 100 à
325 mm², longueur 4 à 12 mm, ProfCase de -1,5 à +3 mm, cale de 0 à 6 mm) aussi. Dès que les
vraies notes sont dans `notes_r12.csv`, tout se relance seul.

| Ch. | notes (hyp.) | f_H : actuel → proposé (Elmer) | f_H / note | trou, longueur, ProfCase, cale | seuil p_on (Pa) : actuel → proposé | but |
|---|---|---|---|---|---|---|
| 1 | ré2 fa#2 | 1 143 → inchangé | 7,8 6,2 | inchangé | 10 16 | fenêtre hors d'atteinte ; déjà à 51 c des harmoniques |
| 2 | sol2 la2 | 1 169 → 1 134 | 5,8 5,2 | 8x25, 9,5 mm | 19 24 → 18 23 | s'écarter des harmoniques (10 → 52 c) |
| 3 | si2 do3 | 1 267 → 1 201 | 4,9 4,6 | 8x25, 10,5 mm | 32 37 → 30 34 | idem (45 → 49 c) ; mode A-B à 19 c d'un harmonique |
| 4 | ré3 mi3 | 1 233 → inchangé | 4,2 3,7 | inchangé | 45 59 | mode A-B à 13 c d'un harmonique |
| 5 | sol3 fa#3 | 1 357 → inchangé | 3,5 3,7 | inchangé | 95 84 | déjà loin des harmoniques |
| 6 | si3 la3 | 1 454 → 1 437 | 2,9 3,3 | 8x25, 8,5 mm | 164 129 → 160 125 | s'écarter des harmoniques (32 → 53 c) |
| 7 | ré4 do4 | 1 379 → inchangé | 2,4 2,6 | inchangé | 213 172 | mode A-B à 11 c d'un harmonique |
| 8 | sol4 mi4 | 1 386 → 1 020 | 1,30 1,55 | 4x25, 12 mm | 318 255 → 281 177 (-12 %, -30 %) | dans la fenêtre |
| 9 | si4 fa#4 | 1 437 → 1 235 | 1,25 1,67 | 6x25, 11 mm | 407 312 → 429 232 (+5 %, -26 %) | dans la fenêtre |
| 10 | ré5 la4 | 1 488 → 1 455 | 1,24 1,65 | 8x25, 9 mm | 572 396 → 604 375 (+6 %, -5 %) | dans la fenêtre |
| 11 | sol5 do5 | 1 540 → 1 943 | 1,24 1,86 | 13x25, 4 mm, ProfCase 1,75 → 1, cale 1 | ne démarre pas, 471 → 1 596, 970 | la note haute démarre ; do5 +106 % |
| 12 | si5 mi5 | 1 576 → 2 074 | 1,05 1,57 | 13x25, 4 mm, cale 6 | ne démarre pas, 967 → ne démarre pas, 1 057 | HORS D'ATTEINTE : il faut une chambre plus petite |

Lecture : avec ces notes supposées, la zone favorable n'est atteignable que pour les chambres
8 à 10 ; les graves (1 à 7) restent loin au-dessus de leur fenêtre, quoi qu'on fasse dans des
cotes usinables (on se contente d'éloigner f_H des harmoniques) ; les deux plus aiguës ont une
note au-dessus de la résonance, qui ne démarre pas dans le modèle ; la 12 demande un volume
plus petit que les bornes. Trois chambres (3, 4, 7) ont leur mode A-B à moins de 20 cents
d'un harmonique. Les seuils sont ceux de `coupled_reeds` avec des lames d'acier uniformes :
des tendances, pas des pascals (voir le rapport du sommier).
