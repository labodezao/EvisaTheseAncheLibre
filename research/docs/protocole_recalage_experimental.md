# Protocole de recalage : une vraie anche, puis son sommier

Écrit le 04/10/2026. Trois gestes, dans cet ordre : (a) l'anche seule pincée, (b) l'anche
pincée sur sa chambre, (c) l'anche jouée à la soufflerie. Chacun recale une partie du modèle,
et le suivant s'appuie sur le précédent. La version de thèse (en anglais) est dans
`design_practical.lyx`, chapitre « Static and modal analysis », section « Experimental model
updating ».

Les outils : `banc_recherche/pince_modes.py` (les modes d'un son pincé),
`fem/comparer_pince.py` (gestes a et b contre le modèle), `fem/souffle.py` (geste c),
`fem/recalage.py` (le tableau final). Tests : `tests/test_pince_modes.py`.

---

## Les étapes, pour l'atelier

Une seule chose à la fois. Coche au fur et à mesure.

### Avant de commencer (une fois)

1. Choisis UNE anche. Donne-lui un nom (par exemple `R12-grave`). Elle doit être dans la
   banque `fem/anche/banque_anches.csv`, avec ses mesures (longueur, largeurs, épaisseurs).
2. Note sur la feuille : la date, la température de la pièce, le nom de l'anche.
3. Branche le micro sur la carte son. Gain fixe. Pas le téléphone pour ces mesures (son gain
   automatique fausse l'amortissement).
4. Règle l'enregistreur : WAV, 48 000 Hz, mono, 24 bits (16 bits va aussi).
5. Pose le micro à 15 cm de l'anche. Marque sa place au ruban adhésif. Il ne bouge plus de
   la séance.
6. Fais un essai : pince une fois, regarde le niveau. Le plus fort doit rester sous -6 dB
   (pas de saturation). Le silence doit être au moins 50 dB plus bas.

### Geste (a) : l'anche seule, pincée

7. Serre la plaque (avec son anche) dans l'étau, par un bord, loin de l'anche. Rien sous la
   fente : l'air passe des deux côtés.
8. Lance l'enregistrement. Dis le nom du fichier à voix haute.
9. Pince le bout de l'anche avec un cure-dent : petit geste, toujours le même.
   Attends que le son s'éteigne (3 s pour une grave, 1 s pour une aiguë). Fais 5 pincements.
10. Arrête. Nomme le fichier : `2026-10-05_R12-grave_seule_1.wav` (date, anche, geste, numéro).
11. Refais une série de 5, cette fois en pinçant un COIN du bout (pour la torsion) :
    `..._seule-coin_1.wav`.

### Geste (b) : l'anche sur sa chambre, pincée

12. Enlève (ou relève avec une bande de papier) la soupape de cette anche. Sinon elle bouche
    la fente côté chambre, et la chambre ne « voit » plus l'anche.
13. Pose la plaque sur sa chambre, l'anche testée côté extérieur. Le trou de table reste
    ouvert à l'air. Le micro reste à sa marque (15 cm de l'anche).
14. 5 pincements au bout, comme en (a) : `..._chambre_1.wav`.
15. Si la plaque se monte vite (vis, serre-joint) : alterne trois fois seule / chambre
    (étapes 7 à 9 puis 12 à 14), fichiers `_1`, `_2`, `_3`. Si elle est cirée : fais une
    série seule au début ET à la fin de la séance, pour voir la dérive.
16. Note sur la feuille si la soupape était enlevée ou relevée.

### Geste (c) : la soufflerie

17. Monte la plaque comme pour jouer (soupape remise). Le tube du capteur de pression va
    dans la boîte à vent, sur une paroi, loin du jet d'air.
18. Soufflerie ARRÊTÉE : lis la pression 10 fois en 30 s. Écris la plus petite et la plus
    grande. L'écart est le bruit du capteur. C'est le « zéro » (la pression de la pièce).
19. Cherche le seuil grossièrement, à l'oreille, sans rien noter : monte doucement jusqu'au son.
20. L'escalier, en montant : pars un peu sous ce seuil. Monte par petites marches (environ
    5 % du seuil, et plus que le bruit du capteur). À chaque marche : attends 3 s, lis la
    pression, écris « sonne » ou « ne sonne pas ». Continue 3 marches après le premier son.
21. L'escalier, en descendant : même chose, jusqu'à 3 marches après la dernière note.
22. Refais 20 et 21 deux fois (3 cycles en tout).
23. Les sons de jeu : à 1,2 puis 1,5 puis 2 fois le seuil, tiens la pression et enregistre
    5 s chacun : `..._jeu-1p2_1.wav`, `..._jeu-1p5_1.wav`, `..._jeu-2_1.wav`. Écris la pression
    lue à côté du nom.
24. Soufflerie arrêtée : relis le zéro (pour la dérive).
25. Recopie la feuille dans un fichier CSV (modèle : `fem/plans/feuille_soufflerie_modele.csv`).

### Après

26. Dépose les WAV et la feuille dans `J:\multimedia à tier\INBOX`. Ne renomme rien d'autre.
27. Dis-moi que c'est fait. Je lance l'analyse (commandes plus bas) et je te rends le tableau.

---

## Le détail, geste par geste

### Ce qui est commun aux trois gestes

- **Chaîne de mesure** : carte son et micro du banc, gain fixe, 48 kHz. Le téléphone suffit
  pour une fréquence, pas pour un amortissement (gain automatique, `banc_recherche/pince.py`).
- **Température** : l'acier perd environ 2,5·10⁻⁴ de son module d'Young par degré (ordre de
  grandeur plausible pour un acier à ressort, à vérifier sur la nuance réelle), donc la
  fréquence baisse d'environ 0,2 cent par degré. Une séance de moins d'une heure dans une
  pièce stable suffit ; noter la température au début et à la fin.
- **Répétitions** : 5 pincements par fichier, 3 fichiers par configuration. L'écart-type
  entre pincements mesure la reproductibilité du geste ; l'écart entre fichiers, celle du
  montage.

### (a) L'anche seule, pincée

**Montage.** La plaque serrée par un bord, la fente libre des deux côtés : pas de chambre.
C'est le cas calculé par Elmer (la languette dans le vide, tenue au rivet).

**Ce qu'on enregistre.** Micro à 15 cm, WAV 48 kHz, 5 pincements au bout puis 5 au coin.

**Ce qu'on en extrait** (`pince_modes.py`) : pour chaque mode jusqu'à 4 kHz, la fréquence f et
l'amortissement zeta (ajustement de sinusoïdes amorties par ESPRIT, bande par bande). Les
harmoniques du mode 1 (rayonnement non linéaire de la lame qui sort de sa fente) sont
reconnus et écartés : fréquence k.f1 à 0,3 % près, et décroissance k fois plus rapide.

**Ce qu'on recale** (`comparer_pince.py --seule`) :
- l'**épaisseur** (un facteur commun) par f1, avec E de l'acier ; le E « apparent » est donné
  pour juger (hors de 190 à 215 GPa : remesurer) ;
- les **amortissements** zeta1, zeta2, qui remplacent la valeur devinée du modèle RK4
  (`ReedModel(..., zeta=[zeta1, zeta2])`) ;
- rien de plus avec f2 et f3, qui servent de **juge** : un facteur d'épaisseur ou un E faux
  multiplie toutes les fréquences par le même nombre, les rapports f2/f1, f3/f1 n'en
  dépendent pas. S'ils s'écartent du modèle de plus de 3 %, c'est la forme qui est fausse
  (masse au bout, profil, longueur libre, encastrement).

**Plan d'expérience.** Facteur : aucun (mesure de référence). Réponse : f et zeta par mode.
Répétitions : 5 x 3. **Ce qui prouverait le contraire** : des rapports f2/f1 à plus de 3 % du
modèle avec une épaisseur bien mesurée. Ordre de grandeur attendu pour l'anche de
`matrix.txt` : f1 = 67,5 Hz, f2 = 842 Hz, torsion 1 677 Hz, f3 = 2 699 Hz (Elmer). L'air autour
de la lame (absent d'Elmer) devrait abaisser f1 d'environ 0,1 à 0,3 % (masse d'air ajoutée
d'une lame large, estimation) : moins que l'incertitude d'épaisseur (0,01 mm au palmer sur
0,25 mm fait 2 % sur f1).

### (b) L'anche sur sa chambre, pincée

**Montage.** La plaque sur sa chambre, l'anche testée à l'extérieur, sa soupape enlevée ou
relevée, le trou de table ouvert. Pourquoi l'anche extérieure : l'intérieure n'est plus
accessible une fois montée. Le réseau acoustique « vu par la fente » est le même des deux
côtés ; c'est celui qu'Elmer a calculé.

**Ce qu'on enregistre.** Comme en (a), en alternant seule et chambre si possible.

**Ce qu'on en extrait.** La fréquence et l'amortissement de la languette sur la chambre, et le
**résonateur d'air** de la chambre (Q de 10 à 50 : il s'éteint en quelques dizaines de
millisecondes ; l'analyse le cherche sur une fenêtre de 30 ms).

**Le modèle.** La languette (masse m, raideur k, aire balayée gamma) pousse un débit dans le
réseau de la chambre (inertance de la fente L_f, du trou L_t, compliance C du volume) :

    k - w² m - w² (kappa.gamma)² [ L_f + L_t / (1 - w²/w_H²) ] = 0

En mots : sous la résonance de la chambre, l'air que la languette pousse dans la chambre et
par le trou ajoute de la masse, la note baisse un peu ; kappa (de 0 à 1) dit quelle part de
ce volume passe vraiment par la chambre au lieu de contourner la lame par le jeu de la fente.

**Prédictions (kappa = 1, réseau d'Elmer, 04/10/2026)** :

| Anche | f1 seule (Hz) | décalage sur la chambre | résonateur (Hz) |
|---|---|---|---|
| R12-grave (chambre 1) | 67,53 | -1,2 cent | 1 140 |
| R12-medium (chambre 6, nominale) | 437,5 | -2,8 cents | 1 453 |
| R12-aigu (chambre 12, nominale) | 873,5 | -3,5 cents | 1 574 |

Ces décalages sont petits. Le pincement donne f à mieux que 0,3 cent, mais remonter la plaque
peut déplacer f davantage : d'où l'alternance seule / chambre trois fois.

**Ce qu'on recale** (`comparer_pince.py --seule ... --cavite ...`) :
- **kappa²** = décalage mesuré / décalage prédit ;
- la **longueur effective du trou de table** par la fréquence du résonateur (le volume vient de
  la CAO, la correction de bout du trou est la cote la moins sûre) ;
- la **résistance de pertes** R du résonateur par son amortissement (Elmer est sans pertes) :
  R = 2 zeta_H racine(L_t / C).

**Plan d'expérience.** Facteur : chambre (2 niveaux : seule, sur chambre). Réponse : f1, zeta1,
f_H, zeta_H. Répétitions : 3 montages x 5 pincements, en alternance. **Ce qui prouverait le
contraire** : un décalage de signe opposé (la note qui monte sur la chambre) ou plus de 3 fois
la prédiction, ou un résonateur à plus de 10 % d'Elmer : alors c'est la description du couplage
par la fente qu'il faut reprendre, pas un paramètre.

### (c) La soufflerie

**Montage.** La plaque comme pour jouer (soupape remise), sur la boîte à vent. Le capteur de
pression (XGZP6847 qui lit la pression absolue, environ 101 kPa) est branché sur une prise de
pression statique de la boîte, loin du jet.

**Le capteur.** Il lit la pression absolue : la surpression est la lecture moins le zéro
(soufflerie arrêtée), lu avant et après. Deux contrôles bon marché :
1. le bruit : 10 lectures soufflerie arrêtée ; l'écart max - min borne la marche de l'escalier ;
2. l'échelle (une fois) : un tube en U transparent avec de l'eau, en parallèle sur la boîte
   (1 mm d'eau = 9,81 Pa). Si le capteur et le tube diffèrent de plus de 5 %, le facteur
   d'échelle du capteur est à corriger (voir `legacy/mesanche-xgzp6847d-2023/README.md`).
Attention : un capteur absolu de 100 kPa de pleine échelle peut avoir un bruit de plusieurs
pascals ; le seuil d'une anche grave est prédit entre 10 et 50 Pa (selon le modèle). Si le
bruit dépasse 2 Pa, le tube en U lu à la loupe est plus juste pour les graves.

**Pourquoi un escalier noté à la main.** Le capteur et le micro n'ont pas la même horloge.
L'escalier ne demande aucune synchronisation : le seuil est entre deux marches, l'incertitude
est la demi-marche. Monter PUIS descendre est indispensable : monter seul ne distingue pas une
bifurcation sous-critique d'une super-critique (`experiences_a_mener.md`, E3).

**Ce qu'on enregistre.** La feuille (zéros, marches, sonne ou non), et 3 sons de jeu de 5 s à
1,2 / 1,5 / 2 fois le seuil.

**Ce qu'on en extrait** (`souffle.py`) : p_on et p_off par cycle, le rapport p_on / p_off
(l'hystérésis), la fréquence de jeu et le niveau à chaque pression.

**Ce qu'on recale, et ce qu'on garde pour juger.**
- Recalé : la **levée au repos** (la cote la moins sûre au pied à coulisse), pour retrouver
  p_on (`recalage.py --souffle ID feuille.csv --recaler-levee`).
- Jugé, pas recalé : p_off / p_on, la fréquence de jeu, la loi d'amplitude. Ce sont des
  **prédictions** du modèle recalé : si on les ajustait aussi, plus rien ne pourrait le
  contredire.
- Le test le plus net : la fréquence de jeu comparée à la fréquence pincée sur la chambre (b).
  Les modèles à cavité fermée font jouer la note AU-DESSUS de la lame (+33 à +43 cents pour
  le grave) ; le réseau d'Elmer avec le trou, EN DESSOUS (-4 à -8 cents)
  (`fem/README.md`, recalage RK4, étape 3).

**Plan d'expérience.** Facteur : pression (escalier, montée et descente). Réponses : sonne ou
non, f_jeu, niveau. Répétitions : 3 cycles. **Ce qui prouverait le contraire** : p_off = p_on
aux marches près (pas d'hystérésis : bifurcation super-critique), ou une note de jeu au-dessus
de la lame pincée.

---

## Les commandes (depuis `research\fem\`)

```
J:\claude\venv\Scripts\python.exe comparer_pince.py R12-grave --seule "J:\multimedia à tier\INBOX\2026-10-05_R12-grave_seule_1.wav" --cavite "J:\multimedia à tier\INBOX\2026-10-05_R12-grave_chambre_1.wav"
J:\claude\venv\Scripts\python.exe souffle.py "J:\multimedia à tier\INBOX\feuille_R12-grave.csv"
J:\claude\venv\Scripts\python.exe recalage.py --ids R12-grave --pince R12-grave "J:\...\seule_1.wav" --souffle R12-grave "J:\...\feuille_R12-grave.csv" --recaler-levee
```

Les fichiers restent où Ewen les a déposés : les scripts les lisent, ils ne les déplacent pas.
Les résultats vont dans `fem/resultats/` (`comparaison_pince_<id>.csv`, `recalage.csv`).

## Ce qui n'est pas encore fait

- Le modèle de chambre est sans pertes et à un résonateur ; la résistance R recalée en (b)
  n'est pas encore branchée dans `coupled_reeds` (l'`Orifice` n'a pas de terme résistif
  linéaire séparé).
- La soupape est un facteur à part entière (elle bouche la fente côté chambre) : elle n'est
  dans aucun modèle. Le geste (b) l'enlève pour isoler la chambre.
- La loi d'amplitude (E5) demande l'excursion du bout, pas le niveau du micro : à faire avec la
  photo stroboscopique (E6).
