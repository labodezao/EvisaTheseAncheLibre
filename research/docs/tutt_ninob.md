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

## 2. La bombarde d'Ewen, confrontée à TUTT — et une rétractation rétractée

### Comment obtenir les partiels

Ewen l'avait dit, et le source le confirme : TUTT sort **tous les partiels
d'un doigté**, dans `zim.out` (partie imaginaire de l'impédance normalisée
contre ω). Mais ligne 528 :

```fortran
IF(ndega.lt.1) GO TO 15
602 write(9,4201) omega, ziminorm
```

Il faut demander **un doigté précis**. Avec `ndega = 0` (tous les doigtés),
rien n'est écrit — c'est pourquoi mon `zim.out` restait vide. Les résonances
sont les passages de `Im Z` du positif au négatif.

### Sur le cylindre d'essai de TUTT

| partiel | TUTT | `tutt.py` | écart |
|---|---|---|---|
| 1 | 156,898 Hz | 157,033 Hz | +1,49 cent |
| 2 | 474,103 Hz | 474,646 Hz | +1,98 cent |

Et le rapport 2ᵉ/1ᵉ : TUTT **3,0217**, moi **3,0226**. L'**inharmonicité** de
la douzième concorde à un demi-cent — c'est elle qui décide de la justesse
inter-registre, donc c'est le chiffre qui compte.

### Sur la bombarde sol d'Ewen, doigté 1 (« fa », tous trous fermés)

| partiel | TUTT | `tutt.py` | écart |
|---|---|---|---|
| 1 | 345,23 Hz | 346,74 Hz | +7,5 cents |
| 2 | 692,88 Hz | 692,15 Hz | −1,8 cent |
| 3 | 1039,63 Hz | 1031,47 Hz | −13,6 cents |

Série harmonique des deux côtés : TUTT 1 : 2,007 : 3,011, moi 1 : 1,995 :
2,972. Sur une perce de 22 tronçons dont je ne pose toujours pas les trous
latéraux, c'est un accord que je n'espérais pas.

### La rétractation, rétractée

J'avais annoncé un peu vite que le modèle donnait le `fa` de cette bombarde à
+2 cents avec une série harmonique, puis **rétracté** en trouvant 1 : 1,651 :
2,680. Les deux étaient faux, et pour des raisons différentes :

- la première fois, un sélecteur de sommets qui retenait les plus **forts**
  au lieu des **premiers**, et sautait donc des rangs ;
- la seconde, un fichier **tronqué de 26 doigtés** (ma faute en le recopiant)
  et une chaîne de calcul qui ignorait encore `OFILIB`, lisait mal les
  nombres Fortran, et inversait les températures.

Avec le fichier complet et les formules de TUTT, la série est franche :
**1 : 1,995 : 2,972 : 3,944 : 4,958 : 6,022**. La perce d'Ewen n'a jamais été
en cause ; c'est mon outillage qui l'était, deux fois de suite.

La leçon vaut d'être écrite telle quelle : un résultat spectaculaire obtenu
d'un coup mérite plus de méfiance qu'un résultat médiocre, et une rétractation
n'est pas non plus une vérité — elle se vérifie comme le reste.

### Ce qui manque encore

Les **trous latéraux** ne sont toujours pas posés dans le calcul d'impédance.
Un doigté tous trous fermés est donc juste ; un doigté ouvert ne l'est pas.
C'est le prochain chantier, et TUTT montre la voie : chaque cheminée est un
tronc de cône avec sa propre impédance d'extrémité.

## 3. Les questions — répondues par le source

Le paquet TUTT contient **`Tutt43.for`**, 2383 lignes de Fortran. Il compile
tel quel sous Linux (`gfortran -std=legacy -O2`) et il répond lui-même à
quatre des cinq questions. Une seule reste pour Ninob.

### `OFILIB` — c'est la rugosité, et elle n'agit que sur les pertes ✅

Le commentaire du source est sans ambiguïté : « TABLEAU PERIMETRE
MICROSCOPIQUE DE LA PERCE / PERIMETRE OFFICIEL », et le calcul fait
`PERI = π·OFILIB(I)·DM`, un **périmètre**. Une perce en bois poreux ou
corrodée offre plus de paroi mouillée qu'un tube lisse de même section.

Conséquence rassurante : `OFILIB = 1,49775` sur la bombarde ne décale pas ses
résonances de 50 %, il abaisse son Q d'autant. J'avais craint une erreur de
section ; c'était une erreur de pertes, bien moins grave.

### `V0`/`V1` — des **vitesses de jet**, pas des volumes ✅

```fortran
V = V0 + V1*(OMEGA/omegac - 1.)
C...V EST LA VITESSE DU JET
```

Les 26 du fichier de flûte à bec sont **26 m/s**, une vitesse de souffle
ordinaire — et non 26 cm³ comme je l'avais lu. Ma prudence à ne jamais
l'appliquer par défaut a évité exactement le résultat faux qu'elle visait.

### `IFLUTE` dit l'inverse de son nom ✅

```fortran
IF(IFLUTE.EQ.1) GO TO 2
IF(IFLUTE.EQ.2) GO TO 2
...
2  CONTINUE
C...ON A AFFAIRE A UNE ANCHE SOLIDE
```

`IFLUTE ∈ {1, 2}` désigne une **anche solide** ; toute autre valeur une anche
**aérienne** (un jet de flûte). Ma propriété `is_flute` disait exactement le
contraire — corrigée en `solid_reed` / `air_reed`.

### Les sentinelles `1.e10` ✅

Simplement **jamais lues** : pour une anche solide, TUTT saute le calcul du
jet et prend `MREED`/`KREED`. Aucun volume infini, aucun court-circuit.

### L'anche, chez TUTT, est un oscillateur — pas une cavité ✅

`MA = MREED`, `KA = KREED` : masse et raideur couplées au tube. La « cavité
équivalente » de *Modes propres d'un tronc de cône* est un résultat
analytique séparé, pas la façon dont le logiciel calcule.

### Reste pour Ninob ❓

**TUTT sait-il sortir les partiels d'un doigté**, et pas seulement la note
jouée ? Le `.out` donne un `OTUBE` par doigté. `zim.out` existe dans le code
(unité 9) mais reste vide dans mes essais — y a-t-il un réglage pour l'écrire ?
C'est la série des résonances qui alimenterait le modèle.

---

## 3 bis. Validation croisée contre TUTT lui-même

TUTT compilé et exécuté sur son propre cylindre d'essai (Ø 15 mm, 532 mm) :

| | fréquence | Q |
|---|---|---|
| TUTT (`OTUBE = 985,8` rad/s) | 156,895 Hz | 26 |
| `tutt.py` | 157,033 Hz | 26,5 |
| **écart** | **+1,52 cent** | — |

Deux implémentations indépendantes — la sienne en Fortran, la mienne en
matrices de transfert — se rejoignent à un cent et demi, amortissement
compris. C'est la meilleure garantie que j'aie sur cette partie du modèle.

Trois formules reprises du source au passage :

- **pertes de Kirchhoff/Mason** : `γ' = (1 + 1,581(√γ − 1/√γ))·√η`, puis
  `P = périmètre·γ'/(2·section·√(2ωρ))` et `k = (ω/c)[(1+P) − jP]`. `P` est à
  la fois l'atténuation **et** le ralentissement de l'onde ;
- **profil de température exponentiel**, constante 0,25 m : le souffle chaud
  ne pénètre pas loin dans le tuyau. Une interpolation linéaire réchaufferait
  tout le corps de l'instrument ;
- **célérité `329,95 + 0,69·T`**, pour de l'air saturé d'humidité à 2,5 % de
  CO₂ (Coltman, JASA 65, 1979, 499) — l'air du musicien, pas celui de la
  pièce.

### Un bug de lecture trouvé au passage

Fortran écrit `10.e-3` et `1.e10` — un point sans décimale derrière. Ma regex
l'ignorait, découpait `10.e-3` en `10` puis `-3`, décalait toutes les colonnes
du tableau d'embouchure, et me faisait lire `V0 = 1,0` là où le fichier dit
`1.e10`. Pas d'erreur levée : juste un paramètre pris pour un autre. Corrigé,
avec test de non-régression.

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
