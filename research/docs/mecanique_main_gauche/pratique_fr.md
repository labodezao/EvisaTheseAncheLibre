# Mécanique main gauche : la pratique

La théorie de la mécanique main gauche est dans la thèse, dans la partie mécanique et soupapes : d'où vient l'effort au bouton, et pourquoi le trou et la pression pèsent plus que les leviers. Cette partie en est le côté atelier : en quoi faire chaque pièce, comment l'imprimer, comment placer les soupapes quand les boutons sont plus serrés que les soupapes ne peuvent l'être, comment mettre en ressort et régler soixante-dix touches, quoi mesurer avec presque rien, et comment décider si la cinquième version vaut d'être réparée. Les chiffres viennent du calculateur du rapport d'ingénierie du Lib RT (calcul_mecanique.py).

## Construire la mécanique

### La géométrie de départ

Un levier bascule à bras égaux, côté bouton et côté soupape ($r$ = 1), par exemple 60 + 60 mm ou 80 + 80 mm, l'axe à mi-chemin entre la plaque de boutons et la table d'harmonie. Course 5 mm, levée 5 à 5,5 mm. La butée haute est la soupape sur sa portée : le bouton repose sur le levier, le levier sur la soupape, et il n'y a pas de temps mort. Un ressort acier par levier, aucun au bouton. C'est « l'idée 1 » : une rotation par touche, contre les quatre à six articulations de la v5.

### Les matières du stock, et ce qu'un achat changerait

Avec ce qu'il y a déjà à l'atelier, la règle est courte : **ASA pour tout ce qui est imprimé et chargé, PETG pour les boutons et les charnières, PLA pour rien de mécanique.** L'achat qui change le plus de choses est le polyamide chargé carbone (PA-CF) : leviers courts et équerres 2,5 fois plus raides, et peu de fluage.

Table: Choix de la matière pour chaque pièce, dans le stock (PLA, PETG, ASA), puis avec un achat. {#tab:fr-matieres}
| pièce | meilleur choix du stock | pourquoi | à acheter | gain |
|---|---|---|---|---|
| leviers jusqu'à 60 + 60 mm, entraxe 5 mm | ASA 3 × 12 à chant, 6 parois | 0,23 mm sous 1,5 N, 98 °C, fluage moyen | PA-CF 3 × 12 | 0,09 mm, permet 80 + 80 mm |
| leviers jusqu'à 80 + 80 mm, entraxe 7,5 mm | ASA 5 × 12 | 0,32 mm (limite) | PA-CF 5 × 12 | 0,13 mm |
| leviers au-delà de 80 mm, barres de rappel longues | métal à chant (alu 2 × 8, acier 1,5 × 8, jet d'eau) | aucun plastique du stock ne tient 0,3 mm | - | le métal reste |
| pivots, moyeux, équerres | ASA, percé et alésé 2 H7, ou tube laiton 3 × 2 | 98 °C sous la précharge permanente | PC ou PA-CF | dérive des boutons ÷ 2 à 3 sur un an |
| guides de bouton (coulissement) | ASA + gaine PTFE ou tube laiton | les trois plastiques frottent fort sur l'acier | PA ou POM | avec une gaine PTFE le gain disparaît (× 1,1) |
| châssis, plaque de boutons | ASA (PETG si l'ASA se déforme) | une plaque PLA sous 70 ressorts se voile l'été | PC | tenue en température seulement |
| boutons | PETG ou ASA | sans charge | - | - |
| charnières souples | PETG 0,4 mm sur 5 mm (~10 000 cycles) | le PLA craquèle en 10 à 100 | PA 0,4 à 0,6 mm | plus de 10^6 cycles |
| ressorts | ressorts à boudin acier du stock | pas de fluage | - | - |

### L'impression

- Imprimer un levier **couché dans son plan de rotation** : le trou d'axe vertical (rond, pas ovale), les cordons dans le sens du levier, pour que la flexion tire sur les cordons et non sur les interfaces de couches (qui ne gardent que 50 à 70 % de la raideur).
- Buse 0,6 : un levier de 3 mm fait cinq parois, il est plein ; mettre six parois ou 100 % de remplissage, couches de 0,2 mm. Les 30 % de remplissage ne valent que pour les gros supports sans charge.
- Châssis et supports : PETG au minimum (68 °C), ASA ou PC si l'instrument peut rester dans une voiture (60 à 70 °C l'été) ; PA-CF pour ce qui porte un axe ou un ressort.
- PA et PA-CF : sécher le filament, recuire 2 h à 80 °C pour stabiliser les cotes avant d'aléser.

### Quand mettre du métal (tiges du stock : 1 ; 1,5 ; 2 ; 3 mm)

- Leviers de plus de 60 mm et barres de rappel longues : aluminium 2 mm ou acier 1,5 mm à chant, découpés au jet d'eau comme les tiges de mécanique actuelles.
- Tout ce qui est sous la charge permanente du ressort : axes, moyeux (tube laiton), attaches de ressort.
- Axes de levier individuels : 2 mm. Un axe commun traversant tous les leviers d'une bande, et les axes des barres de rappel : 3 mm, appuyé tous les 40 mm (0,02 mm de flèche sous 2 N par levier à 5 mm d'entraxe).
- Tiges de liaison : 1,5 mm en compression, 1 mm en traction. Mieux vaut la traction : attacher la tige de l'autre côté du pivot de l'équerre pour que le doigt la tire.

### Des boutons à 15 mm, des soupapes à 17,5 mm

Les boutons sont à 15 mm les uns des autres, une soupape avec sa portée demande 17,5 mm. Trois dispositions tiennent.

Table: Placer des soupapes à 17,5 mm sous des boutons à 15 mm. {#tab:fr-pas}
| disposition | effort | place | complexité |
|---|---|---|---|
| leviers en éventail (angle au plus 7 à 10°) | + 2 à 5 % de frottement | aucune | 43 leviers différents, un paramètre dans la CAO |
| soupapes sur deux rangs décalés (30 mm par rang) | + 0 % | + 25 mm de profondeur | deux longueurs de leviers, r égal par les bras |
| soupapes au pas de 15 mm avec un trou de 11 × 27 mm | + 0 % | aucune | nouvelle table et nouvelles chambres ; même aire, A/P 3,9 mm |
| bras coudés | + 0 % en métal | aucune | en plastique, la torsion ajoute 0,15 mm et un moment de basculement |

Proposé : l'**éventail** si les leviers sont en métal et font au moins 100 mm (angle de 7° ou moins, 5 % de frottement au plus) ; **deux rangs** s'ils sont courts (60 mm). Les deux se combinent (un éventail de 3°).

### Les ressorts, et soixante-dix touches pareilles

- Un ressort acier par soupape, sur le levier : précharge de 1,0 à 1,4 N à la soupape pour un trou de 300 mm² et des pointes de 2 à 3 kPa, raideur 0,06 à 0,07 N/mm (montée de 25 % sur la levée).
- Ressort de torsion sur l'axe : fil de 1,0 à 1,2 mm, diamètre 7 à 10 mm, 8 à 12 spires, précharge de 45 à 100°. Le fil de 0,8 mm est trop sollicité.
- Ressort de traction (comme sur la v5) : fil de 0,5 mm, diamètre 5 mm, 15 spires, accroché à 25 mm de l'axe, 10 mm d'allongement de précharge. Un ressort raide (1 N/mm) s'accroche près de l'axe (15 mm) et tire 5,5 N, si bien que le rail doit tenir 70 × 5,5 N = 385 N ; un souple (0,15 à 0,25 N/mm) s'accroche à 25 à 30 mm et tire 3 N.
- Les ressorts du commerce varient de 10 % ; pour 5 g d'écart au bouton, chaque touche a besoin d'un réglage : l'accroche sur une vis M3 (un quart de tour fait environ 2 g au bouton) ou une patte de torsion qu'on cambre.
- Tous les boutons se règlent au même effort, et c'est le plus gros trou qui fixe le niveau : les petites notes ont un ressort plus fort que nécessaire.

## Mesurer avec presque rien

Matériel : une balance de cuisine (1 g), des pièces de monnaie (1 c = 2,3 g, 5 c = 3,9 g, 10 c = 4,1 g, 20 c = 5,7 g, 50 c = 7,8 g, 1 € = 7,5 g, 2 € = 8,5 g), un peson de 0 à 500 g, un comparateur sur pied, des cales, un tube transparent de 1 m et une règle, un téléphone (sonomètre, enregistreur, ralenti), une perceuse pour le banc d'endurance.

1. **Pression du soufflet (tube en U).** Tube rempli à moitié, un côté relié à l'intérieur du soufflet ; jouer une basse grave du pianissimo au sforzando, au poussé et au tiré, et filmer le tube. Δp = h × 0,098 kPa par centimètre. C'est le chiffre qui fixe le ressort et l'effort.
2. **Soupape au banc.** Une soupape sur un bloc avec le trou, relié au soufflet ou à un aspirateur avec fuite réglable. Étanchéité : des pièces sur la soupape sans ressort, la plus petite masse sans sifflement à 3 kPa (eau savonneuse autour de la portée). Décollement au tiré : un peson sur la soupape, tiré lentement ; puis la force à 1, 2, 3 et 5 mm de levée.
3. **Plus petit trou pour une anche BB95.** Plaques percées de 300, 225, 144 et 100 mm², levées de 1 à 8 mm ; niveau à 50 cm, enregistrement, hauteur. Le plus petit trou et la plus petite levée sans perte audible : chaque millimètre carré en moins est de l'effort en moins au bouton.
4. **Effort au bouton, hystérésis, retour.** Un gobelet léger sur le bouton, des pièces jusqu'à ce qu'il descende, puis en retirer jusqu'à ce qu'il remonte. Hystérésis = descente − remontée = deux fois le frottement ; viser moins de 25 g. Refaire soufflet gonflé (poussé) et dégonflé (tiré). Dix touches graves, cinq rappels, cinq aiguës. La même chose sur la Maugein de référence : c'est le chiffre à battre.
5. **Temps mort et flottement.** Comparateur sur le bouton, un second sur le bord de la soupape ; descendre le bouton par pas de 0,05 mm : la course avant que la soupape ne bouge est le temps mort, viser moins de 0,2 mm. Pousser le bouton de côté avec 50 g : viser moins de 0,3 mm.
6. **Raideur d'un levier.** Levier serré à son axe, 100 g au point du bouton, comparateur ; puis tourné de 90° : le rapport doit être (h/b)².
7. **Tige qui coulisse (v5).** Peson dans l'axe, puis par le pion excentré : le rapport est le facteur tiroir. Enregistrer 20 appuis à 10 cm, compter les grincements. Refaire avec une gaine PTFE, puis un tube laiton.
8. **Fluage et chaleur.** Trois pièces identiques : au repos, sous charge une semaine, sous charge 2 h à 50 °C. Attendu : PLA − 20 à − 40 % en une semaine et effondré à 50 °C, PETG − 10 %, PA-CF − 5 %, acier 0.
9. **Endurance.** Une came sur une perceuse qui appuie une touche à 2 ou 3 Hz : 10 000 cycles en une heure ; effort, temps mort et bruit avant et après.
10. **Répétition.** Métronome ; répéter la note la plus grave et un rappel, de plus en plus vite jusqu'à ce qu'une note manque. But : 8 notes par seconde, aucune différence entre touche et rappel.
11. **Ressorts du stock.** Longueur au repos, puis avec 100 g et 200 g : k = 0,98 N / (L2 − L1). Laisser 24 h sous 300 g : s'il s'est allongé, il a été tendu au-delà de sa limite élastique.

## Sauver la v5 ?

La v5 (un bouton qui coulisse dans la plaque, un pion, une équerre imprimée, une tige de liaison, un levier en aluminium à ressort de traction) se répare en quatre gestes légers : des douilles PTFE ou laiton dans la plaque ; des axes acier de 2 mm dans des trous alésés ou des tubes laiton dans les équerres ; équerres et supports réimprimés en ASA ; tiges de liaison remises en traction. Cela ramène l'effort perdu de + 100 % à + 10 à 15 % et le jeu de 0,2 à 0,05 mm par pivot. Ce qui reste, par principe : quatre à six articulations par touche contre une ou deux pour l'idée 1, des tiges en biais qui chargent les pivots de côté, le passage des 27 rappels sous la plaque, et un coulissement résiduel au bouton.

Table: Les défauts de la v5, leur cause, et la correction la plus légère qui garde son principe. {#tab:fr-v5}
| défaut | cause | correction la plus légère | gain |
|---|---|---|---|
| la tige du bouton grince et force | µ 0,4, broutage ; pion à 5 mm d'un guide de 8 mm : effort × 2 | gaine PTFE 2 × 4 dans la plaque, portée 10 à 12 mm ; ou tube laiton huilé | × 1,1 (PTFE), × 1,2 (laiton), plus de broutage |
| le bouton branle | trou imprimé sur chant : ovale de 0,1 à 0,3 mm | la même douille ; un chanfrein d'entrée | flottement de 0,3 à 0,1 mm |
| jeu des pivots imprimés | trou brut, moyeu court | percer et aléser 2 H7 ou tube laiton pressé, axe corde à piano 2 mm | 0,02 à 0,05 mm par pivot |
| fluage du PLA | 57 °C, fort fluage sous la précharge permanente | réimprimer les mêmes fichiers en ASA, PETG pour les boutons | dérive des boutons ÷ 3 à 5 |
| tiges en biais | à 30° : 58 % de l'effort de côté, + 23 % de frottement si guidée | tourner les équerres pour que la tige parte dans le plan du levier ; ou un câble en traction | frottement de + 23 % à + 7 % |
| pas de place pour les tiges des rappels | des tiges rigides en compression doivent être droites et ne pas se toucher | rappels par deux équerres et une biellette, ou câbles en traction sur deux niveaux | croisements sans contact |
| leviers alu souples | s'ils sont à plat (8 × 2) : 2,6 mm sous 1,5 N sur 100 + 100 mm | vérifier (essai 6) ; les mettre à chant ou ajouter une nervure | de 2,6 à 0,16 mm |
| ressorts de traction sur rail | montée de 25 à 60 % selon l'accroche | accrocher à 20 à 25 mm de l'axe, vis de réglage | montée de 20 à 25 %, 2 g par quart de tour |

Ce que la réparation ne change pas, c'est le plancher de l'effort. Il est dans le trou et la pression : réparer la v5 ou construire l'idée 1 donne les mêmes 177 g pour un trou de 300 mm² à 3 kPa de pointe. Ce qui diffère, c'est ce qui s'y ajoute : + 10 à 15 % et 0,1 à 0,25 mm de flottement pour la v5 réparée, + 2 à 4 % et 0,05 mm pour l'idée 1.

Table: Critères pour décider, mesurés sur la v5 réparée (10 touches graves, 5 rappels, 5 aiguës). {#tab:fr-decision}
| critère | essai | seuil pour garder la v5 | attendu v5 réparée | idée 1 |
|---|---|---|---|---|
| effort à mi-course | 4 | plancher + 15 % (177 à 204 g pour 300 mm²) | plancher + 10 à 15 % | plancher + 2 à 4 % |
| égalité touche / rappel | 4 | écart de 10 g au plus | 5 à 15 g | 2 à 5 g |
| hystérésis | 4 | 25 g au plus | 15 à 30 g | 5 à 10 g |
| retour au poussé 3 kPa | 4 et 10 | toutes les touches remontent, 8 notes/s | juste si le retour < 40 g | même plancher |
| temps mort | 5 | 0,2 mm au plus | 0,1 à 0,25 mm | sous 0,1 mm |
| flottement latéral | 5 | 0,3 mm au plus | 0,1 à 0,2 mm | 0,2 mm |
| bruit | 7 | aucun grincement, aucun cliquetis audible à 50 cm | cliquetis possibles aux attaches | silencieux avec un peigne feutré |
| après 10 000 appuis | 9 | effort + 10 %, jeu + 0,05 mm au plus | ASA bagué laiton : tient | tient |
| 2 h à 50 °C | 8 | dérive des boutons sous 0,3 mm | ASA bon, PETG limite, PLA non | mêmes matières |
| temps de travail | estimation | réparation au plus un tiers de l'idée 1 | 3 à 6 jours | 10 à 20 jours |

Règle de décision : si deux critères ou plus restent hors seuil après la réparation (le plus probable : hystérésis, temps mort et bruit), construire l'idée 1. Si tout passe sauf le temps de travail, garder la v5 comme l'instrument qui valide le trou, la pression et les ressorts (tout ce savoir passe à l'idée 1), et construire l'idée 1 ensuite, sans rien perdre des deux mois.

> À compléter (Ewen) : les résultats des essais 1, 2, 4 et 5 sur la v5 et sur la Maugein, dans le tableau de décision, et le choix qui en découle.
