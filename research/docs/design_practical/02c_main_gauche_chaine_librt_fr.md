### Ce que la chaîne réelle du Lib RT a changé (octobre et novembre 2026)

Le chapitre de départ raisonne sur un levier bascule simple et conclut « $r$ au plus 1 ». La mécanique dessinée a deux étages : le bouton pousse une tige, la tige tire une biellette, la biellette tourne le levier $r$ qui lève la soupape. Chaque étage a ses bras, et six chaînes (A1 à A3, B1 à B3) n'ont pas les mêmes. Le rapport levée/course n'est donc pas un choix unique : il se calcule chaîne par chaîne. Tout ici vient de cotes CAO et d'un calcul. Rien n'a encore été mesuré sur une pièce.

**Le modèle.** Plan XY, pièces rigides, rotations autour d'axes Z. Le piston monte de la course $d$ = 5 mm ; la tige tourne jusqu'à ce que son point de contact ait monté de $d$ ; la biellette garde sa longueur ; on en déduit l'angle du levier $r$, et la levée au centre de palette. Le rapport exact est $r$ = levée / $d$. L'effort au doigt est pris à 177 g × $r$, 177 g venant du calcul de départ (trou de 300 mm², pointe de 3 kPa, $r$ = 1, mi-course). Le modèle ignore les jeux, la flexion, le frottement, le glissement au contact et les décalages en Z. Le lien entre A et le second trou de $r$ est une hypothèse. La course n'est pas cotée dans la CAO.

Table: Rapport levée/course exact sur les six chaînes, avant correction et selon la proposition (calculé sur relevé CAO, course 5 mm sauf P2 et P3) {#tab:chaines-librt}

| Cas | Rapport min / médiane / max | Levée min / médiane / max (mm) | Effort min / médiane / max (g) |
|---|---|---|---|
| Avant | 0,629 / 1,063 / 1,289 | 3,15 / 5,31 / 6,44 | 111 / 188 / 228 |
| P1 : trous de $r$ ou attaches déplacés | 1,050 partout | 5,25 | 186 |
| P2 : butée de course par rang | 0,635 / 1,062 / 1,297 | 5,06 / 5,07 / 5,12 | 112 / 188 / 230 |
| P3 : course 6,5 sur A1 et B1, tiges déplacées | 0,632 / 1,036 / 1,140 | 4,11 / 5,18 / 5,70 | 112 / 183 / 202 |
| P4 : tiges seules, ligament au moins 3 mm | 0,629 / 1,050 / 1,050 | 3,15 / 5,25 / 5,25 | 111 / 186 / 186 |
| P5 : tiges ou leviers, ligament au moins 3 mm | 1,050 partout | 5,25 | 186 |
| P5 retenue : trou sur l'axe, A1 non tranché | 0,629 / 1,050 / 1,051 | 3,15 / 5,25 / 5,25 | 111 / 186 / 186 |

**Ce que le calcul apprend.** Avant correction, le rapport va de 0,63 à 1,29 : deux fois plus d'une chaîne à l'autre, donc deux fois plus d'effort sous le doigt pour le même geste. Égaliser la levée par une butée (P2) ne règle rien : la levée devient égale, l'effort reste de 112 à 230 g, parce que c'est le rapport qui fixe l'effort. La formule aux petits angles s'écarte du calcul exact de 6 % sur B2 (1,213 contre 1,140) : c'est le rapport exact qu'il faut citer.

**Pourquoi 1,05.** La fourchette 1 à 1,1 vient du calcul de départ (course 5 mm, levée 5 à 5,5 mm). L'audit du 26/10/2026 propose d'égaliser dans cette fourchette ; 1,05 en est le milieu, 5,25 mm de levée. La décision du 26/10 : P5 validée, trou gardé sur l'axe de la mécanique, toute la tige décalable. Ce 1,05 remplace le « $r$ au plus 1 » du chapitre de départ pour le Lib RT, et coûte 186 g au lieu de 177 g.

> À confirmer. A1 reste à 0,629, non tranché. La base de 177 g suppose un trou de 300 mm² ; l'audit du 26/10 raisonne aussi sur le trou de 15 × 25 mm de la table 017 : l'effort est à refaire avec le trou de chaque chaîne. Levée et effort se mesurent au comparateur et au peson sur la première pièce. Données et calculs : `research/data/librt_leviers_20261026/`.
