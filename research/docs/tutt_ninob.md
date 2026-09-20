# TUTT et les travaux de B.B. Ninob — ce que j'en ai tiré, et ce que je n'ai pas tiré

> B.B. Ninob (http://la.trompette.online.fr/Ninob/) est le mentor d'Ewen depuis
> une dizaine d'années. Son logiciel **TUTT** calcule la hauteur de chaque
> doigté d'un instrument à vent à partir des longueurs et diamètres de ses
> tronçons — cuivres comme bois — et sert à concevoir des instruments réels.
> Les bombardes bretonnes d'Ewen ont été dessinées avec.

Ce document sépare ce qui est **acquis et vérifié** de ce qui est **supposé**,
et liste les questions que je n'ai pas su trancher seul.

---

## 1. Ce qui est acquis

### La lecture des fichiers

`banc_recherche/tutt.py` lit les `.dat` (géométrie, trous, embouchure,
doigtés) et les `.out` (par doigté : pulsation visée `OREF`, obtenue `OTUBE`,
écart en `CENTS`, facteur `Q`).

Un piège tenu par test : `OREF` et `OTUBE` sont des **pulsations**, pas des
fréquences. 3100,9 rad/s = 493,5 Hz, soit do5 au diapason 415. Les lire comme
des fréquences coûterait près de cinq octaves.

### Le sens de lecture des tableaux

Le manuel tranche : « pour le **tronçon N+1 décrivant l'embouchure** ». Les
tableaux vont donc du **pavillon** (indice 0) vers l'**embouchure** (indice N),
`DL` est le côté pavillon et `D0` le côté embouchure, et la continuité se lit
`DL[i] = D0[i−1]`.

Lire à l'envers ne donne pas un résultat « un peu faux » mais un instrument qui
n'existe pas.

### L'impédance d'entrée, validée sur le cas analytique

Matrices de transfert, tronçons découpés en tranches cylindriques, pertes
visco-thermiques de couche limite, charge de rayonnement au bout ouvert.
Convergence atteinte dès 16 tranches par tronçon.

Sur un cylindre Ø 15 mm de 500 mm fermé à l'anche :

| résonance | calculé | rapport |
|---|---|---|
| 1 | 167,2 Hz | 1,000 |
| 2 | 505,0 Hz | 3,020 |
| 3 | 843,5 Hz | 5,045 |
| 4 | 1182,3 Hz | 7,071 |

Série impaire exacte, aucun sommet parasite. Le premier mode est 2,5 % sous
`c/4L`, écart entièrement expliqué par la charge de rayonnement et le
ralentissement visco-thermique de l'onde (1,71 %, recalculé séparément).

**Et les rapports ne sont pas exactement 1:3:5:7** — la douzième sort 12,5
cents trop haute. C'est cette inharmonicité-là qui manquait au modèle, et elle
compte : la hauteur du registre suit la deuxième résonance au cent près.

---

## 2. Ce qui n'est pas acquis — et une erreur que j'ai commise

### La bombarde sol d'Ewen n'est pas reproduite

J'ai d'abord annoncé que le modèle donnait le `fa` tous trous fermés à
**+2 cents** avec une série harmonique. **C'était faux.** Mon sélecteur de
sommets retenait les plus *forts* au lieu des *premiers*, sautait des rangs, et
tombait par hasard sur un sous-ensemble d'allure harmonique.

À résolution fine, les vrais sommets de |Z| de cette perce, telle que je
l'assemble, valent :

    317,0 · 523,5 · 849,6 · 1246,1 · 1631,5 · 2046,1 Hz
    rapports 1 : 1,651 : 2,680 : 3,931 : 5,146 : 6,454

Ce n'est pas une série harmonique, donc **mon assemblage de cette perce est
incomplet**. Trois causes nommées, aucune encore levée :

1. **Les trous latéraux ne sont pas posés** dans le calcul. La bombarde en a
   huit ; même « tous fermés », leurs cheminées ajoutent du volume.
2. **`OFILIB` n'est pas appliqué du tout.** Ce champ (« surface libre de la
   perce / surface officielle ») vaut **1,49775** sur toute cette bombarde et
   1,6 sur le hautbois baroque. Un facteur 1,5 en surface n'est pas un détail.
3. **Les deux derniers tronçons** (tudel et anche) rompent la continuité
   `DL[i] = D0[i−1]` ; je ne sais pas encore comment TUTT les raccorde.

La leçon, et elle vaut d'être écrite : un sélecteur de sommets un peu trop
malin a produit pendant une heure un résultat spectaculaire et faux. Les
sommets sont désormais rendus dans l'ordre des fréquences, et un test de
non-régression le tient.

### Le volume équivalent d'anche est lu mais **pas appliqué**

Ninob montre (*Modes propres d'un tronc de cône*) qu'une anche solide au petit
bout d'un cône se comporte comme une **cavité ajoutée** : elle abaisse les
fréquences de jeu et **corrige les octaves**. C'est ce qui permet à un
saxophone, un hautbois ou un basson d'avoir des octaves justes, et ce qui fait
qu'un changement d'anche les dérègle.

Le code sait poser cette cavité — en **parallèle** au nœud du bec, pas en
série — et le sens est vérifié : elle abaisse bien les fréquences. Mais
`V0` n'est **jamais** appliqué automatiquement, parce que son unité n'est pas
confirmée. Testé : `V0 = 26` lu en cm³ traîne la fondamentale d'un tube de
50 cm de 167 à 131 Hz. Une hypothèse d'unité fausse ne décale pas un peu.

C'est aussi ce qui a cassé quatre tests d'un coup quand je l'avais branché par
défaut — un bon rappel que brancher d'office une interprétation incertaine
fabrique des résultats faux qui ont l'air justes.

---

## 3. Les questions pour Ninob

Elles me feraient gagner beaucoup, et il y répondrait en une phrase.

1. **`OFILIB`** — que corrige exactement ce rapport « surface libre / surface
   officielle », et comment entre-t-il dans le calcul ? C'est le champ dont
   l'effet serait le plus grand et que je comprends le moins.
2. **`V0` / `V1`** — quelle unité, et comment se rapportent-ils au volume de
   cavité équivalente de l'article sur le tronc de cône ? Le hautbois
   d'exemple existe en « model MK » et « model Veff » : sont-ce les deux
   manières de poser l'anche ?
3. **Les valeurs sentinelles** `1.e10` sur `V0` — « pas de cavité », ou un
   volume réellement infini ?
4. **TUTT sait-il sortir les partiels d'un doigté**, et pas seulement la note
   jouée ? Le `.out` que j'ai lu donne un `OTUBE` par doigté ; c'est la série
   des résonances qui alimenterait le modèle.
5. **Le raccordement tudel/anche** — les deux derniers tronçons d'une bombarde
   ne suivent pas la continuité des autres. Convention particulière ?

---

## 4. Les articles, et ce qu'ils changent

Lus ou repérés sur le site. Ceux marqués **appliqué** sont dans le code.

| article | ce qu'il apporte | état |
|---|---|---|
| *Dissipation viscothermique… rugosité de la paroi* (2006) | `Q ∝ √f`, `Z ∝ 1/√f` ; la corrosion interne altère l'acoustique | **appliqué** (paroi lisse) |
| *Modes propres d'un tronc de cône* (2007/2013) | l'anche = cavité équivalente ; corrige les octaves des coniques | codé, **non activé** (unités) |
| *Inharmonicité et dispersion… tuyaux étroits* (2009) | l'encrassement altère les rapports de partiels, donc la justesse **et** le timbre | à lire |
| *Paramètres des anches doubles* | comblerait la limite assumée du `DoubleReedExciter` | à lire |
| *Influence de la cavité buccale* | le conduit vocal comme second résonateur — un axe d'expression | à lire |
| *Conception d'une bombarde bretonne géante* | directement le monde d'Ewen | à lire |

---

## 5. Provenance et droits

Ni le logiciel TUTT, ni ses fichiers d'exemple, ni les articles de Ninob ne
sont versionnés ici : ils ne m'appartiennent pas. TUTT est librement
téléchargeable sur le site de l'auteur, avec son guide d'utilisation.

Les tests de `tutt.py` fabriquent eux-mêmes leurs fichiers d'exemple, de sorte
que la suite tourne sans aucune donnée extérieure.

Les perces d'Ewen (bombarde sol, bombarde basse) sont sa propre conception et
lui appartiennent ; c'est à lui de décider si elles entrent dans le dépôt.
