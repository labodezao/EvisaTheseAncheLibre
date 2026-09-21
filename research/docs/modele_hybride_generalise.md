# Un modèle physique pour tous les instruments — et qui tienne sur un STM32

> De l'anche libre seule à la famille entière : clarinette, saxophone,
> bombarde, cornemuse, violon, vielle à roue. Puis du modèle au code C
> temps réel, sans ordinateur, pour le live.

---

## 1. Ce qui rend la généralisation possible

`reed_oscillator.py` modélisait **une** chose : l'anche libre. Passer au
reste n'a pas demandé d'écrire six modèles, parce que McIntyre, Schumacher et
Woodhouse ont montré en 1983 que l'anche, l'archet et le jet de flûte ne sont
pas trois problèmes mais un seul :

    un excitateur non linéaire  ⟷  un résonateur linéaire

L'excitateur ne sait rien faire d'autre que transformer, instantanément, ce
que le résonateur lui présente. Le résonateur ne sait rien faire d'autre que
se souvenir. Le seuil, le cycle limite, l'hystérésis, le timbre — tout naît
de leur boucle, et de rien d'autre.

| famille | excitateur | résonateur | couple |
|---|---|---|---|
| accordéon, harmonica | anche libre | chambre (ressort d'air) | (p, q) |
| clarinette, saxophone | anche simple battante | perce | (p, q) |
| bombarde, cornemuse | anche double | perce conique étroite | (p, q) |
| violon, vielle à roue | frottement d'archet | corde | (v, F) |

Les deux dernières colonnes disent tout. Un tuyau rend une **pression** quand
on lui injecte un **débit** ; une corde rend une **vitesse** quand on lui
applique une **force**. Effort et flux échangent leurs rôles, mais la
structure mathématique est identique — d'où un seul `Resonator` pour les
quatre familles.

**L'accordéon est le cas dégénéré, et c'est ce qui le distingue.** Son
résonateur n'a aucun mode : juste une compliance, le ressort d'air. Un tuyau
ouvert ne garde aucune pression statique ; une cavité fermée, si. C'est pour
cette raison, et pour elle seule, qu'une anche libre **impose** sa hauteur là
où une anche de clarinette la **reçoit**.

---

## 2. Ce que le modèle prédit sans qu'on le lui demande

Les tests qui valent quelque chose sont ceux qu'on aurait pu rater. Voici
ceux-là.

### La perce décide du timbre, pas l'anche

Même excitateur des deux côtés — `SingleReedExciter`, mêmes équations, mêmes
paramètres d'anche. Seule la perce change.

| | écart impairs − pairs |
|---|---|
| clarinette (perce cylindrique) | **+36,8 dB** |
| saxophone (perce conique) | **+3,7 dB** |

Le son « creux » de la clarinette n'est pas une métaphore, et son registre
qui saute à la douzième au lieu de l'octave en est la même conséquence.

### La loi de Helmholtz sur les cordes frottées

Le mouvement de Helmholtz prédit une vitesse de glissement de
`v_archet·(1−β)/β`, où β est la position d'archet. Rien dans le code ne
contient cette formule.

| | β | v_archet | prédit | mesuré |
|---|---|---|---|---|
| violon | 1/7 | 0,20 m/s | 1,20 m/s | **1,41** |
| vielle à roue | 1/9 | 0,35 m/s | 2,80 m/s | **2,85** |

### La borne haute de l'archet (diagramme de Schelleng)

À 2,5 N, le violon décroche sur un sous-harmonique à f0/6 : c'est le
craquement de l'archet trop appuyé. Et mesuré autrement : au-delà de 0,5 N,
le modèle devient **chaotique** — deux simulations identiques à 10⁻⁷ près
divergent complètement en quelques dizaines d'échantillons, alors qu'en
dessous de 0,3 N elles restent superposables à 0,97. Le régime raucous est un
régime chaotique, et le modèle le montre.

### L'étouffement, et le rapport cyclique

La bombarde s'étouffe à 12 kPa — l'analogue exact de l'étouffement de l'anche
libre, quand la pression plaque l'anche et qu'elle ne module plus rien.

Plus surprenant : l'équilibre pair/impair fait des allers-retours avec la
pression de souffle (17 → 5 → 27 → 6 dB), et il suit le **rapport cyclique**.
Une anche fermée près de la moitié du temps produit un signal quasi
symétrique, dont les harmoniques paires s'éteignent — **même sur une perce
conique**. La pression de souffle ne change donc pas seulement la nuance : elle
change la nature du timbre.

### Une perce étroite oppose une impédance élevée

`Z_c = ρc/S`. Une bombarde (Ø 5 mm) présente **8 fois** l'impédance d'une
clarinette (Ø 14,6 mm). D'où son anche minuscule et raide, sa pression de jeu
en milliers de pascals, et le fait qu'elle porte par-dessus un fest-noz
entier. Le paramètre n'est pas un réglage : c'est lui qui décide si
l'instrument parle. En dessous du seuil `|∂q/∂Δp| > 1/z_peak`, on n'obtient
qu'une sinusoïde anémique.

---

## 3. L'identification : ce qui se mesure, ce qui se suppose

La question honnête n'est pas « peut-on retrouver un modèle physique complet
à partir d'un enregistrement ? ». La réponse est non, et `extract_multi` le
démontrait déjà : sur une note unique le problème est sous-déterminé.

La question utile est : **qu'est-ce qui se mesure, et qu'est-ce qui se
suppose ?** `identify.py` tient les deux colonnes séparées et les imprime
dans son rapport.

### Ce qui se mesure vraiment

| descripteur | comment | vérifié par bouclage |
|---|---|---|
| hauteur f0 | autocorrélation | 146,97 pour 147,0 |
| conicité de perce | écart impairs/pairs | cylindrique ✓ / conique ✓ |
| position d'archet β | creux dans la série harmonique | **1/7 et 1/9 exacts** |
| décroissance spectrale | pente dB/octave de rang | −6,3 (Helmholtz : −6) |
| nuance de jeu | ajustement 1-D sur le spectre | — |
| corps de l'instrument | `extract_multi`, **plusieurs notes** | — |

La position d'archet est la plus jolie : l'archet posé à la fraction β annule
les modes dont il touche un nœud. Le partiel le plus faible de la série donne
donc directement le dénominateur. Bouclage sur synthèse : 1/7 pour le violon,
1/9 pour la vielle, exacts tous les deux.

### Ce qui reste supposé

La famille d'excitateur, les dimensions de l'anche, la masse de la corde. On
ne les déduit pas d'un son : on les prend d'un a priori d'instrument. Le
rapport les liste comme telles, parce qu'un paramètre supposé qu'on prend
pour mesuré est la façon la plus sûre de se tromper longtemps.

---

## 4. Le moteur temps réel : du modèle au STM32

### Pourquoi le modèle continu ne suffit pas

`hybrid.py` intègre en RK4 : quatre évaluations de dérivée par pas, huit pas
par échantillon. **114 MFLOP/s par voix** — une voix et demie sur un STM32F4.
Inutilisable en concert.

### Ce qu'on fait à la place

La partie linéaire — le résonateur, la dynamique de l'anche — devient un banc
de **biquads**, qui est la forme exacte d'un oscillateur amorti en temps
discret. Seule la non-linéarité (Bernoulli, frottement) reste évaluée pas à
pas, et elle seule a besoin d'être suréchantillonnée.

| | MFLOP/s par voix | STM32F4 (168 MHz) | STM32H7 (480 MHz) |
|---|---|---|---|
| RK4 continu | 114 | 1,5 voix | 4 voix |
| biquads + NL | **32** | **5 voix** | **15 voix** |

### Ce que le portage préserve

| instrument | continu | temps réel | écart |
|---|---|---|---|
| clarinette | 147,0 Hz | 147,0 Hz | −0,0 cent |
| saxophone | 232,0 | 231,9 | −0,5 |
| bombarde | 293,9 | 293,8 | −0,1 |
| cornemuse | 232,8 | 232,9 | +0,2 |
| vielle | 195,3 | 195,4 | +0,8 |
| violon | 438,8 | 437,1 | −6,7 |

Et le C compilé produit exactement le même calcul que la référence Python :
corrélation **1,000000** sur les premiers échantillons pour la clarinette, le
saxophone et l'accordéon. Ce qui les sépare ensuite n'est que la dérive
float32 dans une boucle non linéaire — musicalement sans conséquence,
puisqu'un oscillateur auto-entretenu n'a pas de référence de phase.

### Le retard d'un échantillon

Un modèle physique est une boucle : l'excitateur lit ce que le résonateur
présente, et le résonateur reçoit ce que l'excitateur produit, au même
instant. En temps discret, ça se mord la queue. On casse la boucle avec un
retard d'un échantillon **interne** — 5 µs à 192 kHz — comme tout guide
d'ondes numérique.

**L'archet en demande deux fois plus que l'anche.** Mesuré, pas supposé : à
K = 4, le violon décroche et part à 91 Hz au lieu de 440 ; à K = 8 il retrouve
437,6 Hz. Sa courbe de frottement varie sur 0,05 m/s alors que la corde
atteint 1,4 m/s — une pente bien plus raide que Bernoulli.

On aurait pu résoudre le couplage implicitement (Newton) et suréchantillonner
moins. On ne le fait pas : en audio temps réel, un coût **fixe** par
échantillon vaut mieux qu'un coût moyen plus bas mais variable. Un nombre
d'itérations qui dépend du signal, c'est une échéance qu'on rate un jour de
concert.

### Contraintes tenues dans le C généré

- `float32` partout (FPU simple précision des Cortex-M4F / M7) ;
- aucune allocation dynamique, aucun `printf` dans le chemin audio ;
- de `libm`, uniquement `sqrtf` — instruction câblée `VSQRT`, ~14 cycles ;
- taille d'état fixe, connue à la compilation ;
- compile sans **aucun** avertissement en `-Wall -Wextra -Wpedantic`.

Le moteur (`hybrid_voice.c/h`) est **fixe** : seules les tables de paramètres
changent d'un instrument à l'autre. Un seul code à relire, un seul à porter.

### Pourquoi pas le Dream SAM5716

Parce que ce n'est pas la bonne puce, et autant le dire. Les SAM5xxx sont des
moteurs de **lecture d'échantillons** : leur force est de lire beaucoup de
voix depuis une ROM, pas d'exécuter une boucle de rétroaction non linéaire
échantillon par échantillon. Un STM32 + un codec audio, c'est la même boîte,
le même prix, et ça calcule vraiment un modèle physique.

---

## 5. Ce que ce modèle ne fait pas

À dire avant qu'on le découvre en jouant :

- **l'anche double** est traitée comme une anche simple avec d'autres
  réglages. Une vraie anche double a une dynamique de jet confiné entre les
  lames qui ajoute une perte dépendant du débit. Le modèle rend la hauteur,
  le seuil et l'allure du spectre ; il ne rend pas le grain propre du
  hautbois ;
- **l'archet** utilise un modèle à courbe de frottement, qui ignore
  l'hystérésis thermique du collophane. Les modèles thermiques rendent mieux
  le grincement et les transitions ;
- **le corps de l'instrument** (table du violon, pavillon) n'est pas dans le
  résonateur ; il faut le rapporter de `extract_multi` sur plusieurs notes ;
- **les préréglages sont des points de départ**, pas des mesures. `z_peak`,
  les géométries d'anche, les masses de corde sont des ordres de grandeur.
  C'est l'identification sur des sons réels, et la paillasse, qui les recalent.

---

## 6. Pour aller plus loin

Les expériences qui recaleraient tout ça sont dans
`docs/experiences_a_mener.md`. Deux ajouts pour la famille élargie :

- **E14. Impédance d'entrée d'une perce réelle.** `transfer.py` sait la
  mesurer à deux micros. Elle donne `z_peak`, les Q et les fréquences de mode
  — c'est-à-dire tout le résonateur, mesuré au lieu de supposé.
- **E15. Matrice force × position d'archet.** Sur une vielle, balayer la
  pression du chien et la position du point de contact. Le modèle prédit la
  zone de Helmholtz stable (F ≤ 0,3 N pour les paramètres actuels) et le
  décrochage chaotique au-dessus. C'est le diagramme de Schelleng, et il est
  mesurable avec une roue, un dynamomètre et un micro.

---

## 7. La perce réelle — et le pont vers un calcul de perce

Trois corrections au résonateur, toutes remplaçant un réglage au jugé par de
la physique.

### Les pertes visco-thermiques ne sont pas ce qu'on croit

Le modèle faisait décroître les sommets en `1/rang`. C'était un paramètre
libre déguisé. L'air qui frotte contre la paroi perd son énergie dans une
couche limite d'épaisseur `∝ 1/√f`, d'où, sans rien à régler :

    Q_n = q·√(f_n/f_0)        Z_n = z_peak/√(f_n/f_0)

Les résonances aiguës sont donc **plus sélectives** et bien moins faibles
qu'on ne le supposait : au rang 9 d'une clarinette, +4,4 dB d'écart avec
l'ancienne loi.

### Ce n'est donc pas la viscosité qui éteint les aigus

C'était l'erreur de mécanisme du modèle précédent. Le vrai responsable est le
**réseau de trous latéraux** : sous sa fréquence de coupure il réfléchit
l'onde et fabrique des résonances, au-dessus il devient transparent et
l'énergie s'échappe (Benade). C'est une grandeur propre à l'instrument, et
mesurable :

| instrument | `cutoff_hz` |
|---|---|
| basson | ~450 |
| saxophone alto | ~700 |
| hautbois, cornemuse | ~1100 |
| clarinette | ~1500 |

Effet immédiat, non recherché : la **bombarde** donne enfin +2,7 dB d'écart
impairs/pairs, c'est-à-dire la série complète d'un cône. Elle était coincée
sur un régime dégénéré à ~50 % de rapport cyclique. Et les modes devenus
négligeables sont écartés — un biquad de moins sur la carte.

### Le registre, que le modèle retrouve seul

`register_vent` étouffe la première résonance, comme le fait une clé de
registre. L'oscillation se rabat sur la suivante disponible, et la perce
décide laquelle :

| perce | résonances | registre obtenu |
|---|---|---|
| cylindrique | f0, 3f0, 5f0… | **×2,997** — la douzième |
| conique | f0, 2f0, 3f0… | **×2,000** — l'octave |

Rien dans le code ne l'impose. C'est ce qui sépare le doigté d'une clarinette
de celui d'un saxophone, et il sort de la structure modale.

### Aucune perce réelle n'est harmonique

`bore_modes` fabrique une série idéale. Aucun tuyau ne fait ça : la perce, le
bec, les trous ouverts et le pavillon écartent les résonances de la série
exacte, et c'est cet écart qui décide si l'instrument est **juste** d'un
registre à l'autre. Un facteur passe sa vie dessus.

D'où trois fonctions qui n'inventent rien :

- `modes_from_partials(freqs)` — les résonances telles qu'elles sortent d'un
  calcul de perce ou d'une mesure d'impédance. Accepte aussi les `Q` et les
  sommets mesurés, auquel cas **plus rien n'est supposé** ;
- `modes_from_cents(f0, cents)` — la forme sous laquelle on parle justesse :
  « la douzième est 12 cents trop basse » ;
- `inharmonicity_cents(modes)` — la relecture, pour confronter le modèle au
  calcul.

### Pourquoi ce pont vaut la peine : le modèle y est maximalement sensible

Mesuré, en désaccordant la **deuxième** résonance d'une clarinette :

| désaccord de r2 | note au grave | note au registre |
|---|---|---|
| −20 cents | −0,4 cent | **−19,9 cents** |
| +20 cents | +2,1 cents | **+19,8 cents** |
| +40 cents | +1,5 cent | **+40,2 cents** |

Au registre, la hauteur suit la deuxième résonance **au cent près** : c'est
elle qui fait la note. Au grave elle bouge à peine, mais pas de zéro — la
douzième *tire* la fondamentale, exactement le phénomène que connaît un
facteur. L'écart impairs/pairs bouge aussi de 3 dB : le timbre suit.

Le modèle est donc maximalement sensible à la grandeur qu'un calcul de perce
produit. Ce n'est pas un raffinement cosmétique : sans les vraies résonances,
tout ce qui touche à la justesse d'un registre à l'autre est faux.

---

## 8. TUTT — des vraies perces dans le modèle

[TUTT](http://la.trompette.online.fr/Ninob/Ninob.php) est le logiciel de
B.B. Ninob : à partir des longueurs et diamètres des tronçons d'un instrument
à vent, il calcule la hauteur de chaque doigté et simule l'effet d'une
modification. Cuivres et bois. Il vient avec une bibliothèque de perces
réelles — Stanesby, Martinlot, Van Eyck, Kynsecker, traversos, chalumeaux.

`banc_recherche/tutt.py` lit ses fichiers et calcule l'impédance d'entrée de
la perce, dont les sommets alimentent `hybrid.modes_from_partials`.

### Ce que le module lit

- **`.dat`** — géométrie des tronçons, trous latéraux, embouchure (dont les
  volumes `V0`/`V1` et la masse et la raideur de l'anche), table des doigtés ;
- **`.out`** — par doigté : la pulsation visée `OREF`, la pulsation obtenue
  `OTUBE`, l'écart en `CENTS`, le facteur `Q`.

Un piège vérifié par test : `OREF` et `OTUBE` sont des **pulsations**, pas des
fréquences. 3100,9 rad/s = 493,5 Hz, soit do5 au diapason 415 — les lire comme
des fréquences coûterait près de cinq octaves.

### Ce que le module calcule

L'impédance d'entrée par matrices de transfert : chaque tronçon est découpé en
tranches cylindriques, avec pertes visco-thermiques de couche limite et charge
de rayonnement au bout ouvert. Le découpage plutôt qu'une matrice conique
analytique, parce qu'on peut le **vérifier** en affinant jusqu'à stabilité,
sans formule à se tromper.

Contrôle sur un cylindre de 50 cm : quarts d'onde, structure impaire exacte,
premier mode à 6 % près de `c/4L` — l'écart venant de la charge de
rayonnement et du ralentissement visco-thermique de l'onde, tous deux
légitimes.

### Le résultat qui justifie tout le module

Sur le tube d'essai de TUTT (cylindre de 52 cm, Ø 15 mm) :

| résonance | fréquence | rang réel | idéal | écart |
|---|---|---|---|---|
| 1 | 156,84 Hz | 1,000 | 1 | 0 |
| 2 | 473,94 Hz | 3,022 | 3 | **+12,5 cents** |
| 3 | 791,65 Hz | 5,047 | 5 | +16,3 |
| 4 | 1109,62 Hz | 7,075 | 7 | +18,4 |
| 5 | 1427,75 Hz | 9,103 | 9 | +19,7 |

La série idéale donnait des zéros partout. Or la hauteur du registre suit la
deuxième résonance **au cent près** (§7) : le modèle idéal jouait donc sa
douzième 12,5 cents faux, sans aucun moyen de le savoir.

### Ce qui reste à faire

Les **trous latéraux** ne sont pas encore posés dans le calcul d'impédance :
seule la colonne principale l'est. Un doigté tous trous fermés est donc juste,
un doigté ouvert ne l'est pas. TUTT, lui, les traite. Le module le dit dans
son rapport (`trous_latéraux: NON POSÉS`) plutôt que de laisser croire.

Et le **volume équivalent d'anche** — Ninob montre (*Modes propres d'un tronc
de cône*) qu'une anche solide au petit bout d'un cône se comporte comme une
cavité ajoutée, qui abaisse les fréquences et **corrige les octaves**. C'est
ce qui permet à un saxophone, un hautbois ou un basson d'avoir des octaves
justes. Mon `SingleReedExciter` n'a aucun volume : c'est le prochain manque à
combler, et les champs `V0`/`V1`/`MREED`/`KREED` sont déjà lus.

---

## 9. Le jouer — et ce que le clavier a révélé

`live.py` compile le C destiné au STM32 en bibliothèque partagée et le pilote
par `ctypes`. Rien n'est réécrit pour l'occasion : c'est le code de la carte,
à vitesse native, ce qui en fait aussi une vérification permanente de ce qui
part sur la carte. Mesuré à 48 kHz : ×137 le temps réel à une voix, ×26 à
six.

Jouer, c'est mettre le modèle à une épreuve qu'aucune simulation ponctuelle
ne fait subir : **toutes** les notes, pas une, et jusqu'au relâchement.
Trois choses fausses sont apparues en trois heures.

### L'anche libre ne suit pas la note si ses cotes ne suivent pas

Au-dessus de 185 Hz, l'accordéon devenait muet. Pas faible : muet. La sortie
n'était qu'une pression continue — la languette se couchait dans le courant
d'air et y restait. J'avais gardé les cotes de l'anche du la grave et changé
la seule fréquence.

C'était prévisible en regardant la force motrice, `p·A/m` : à cotes fixes,
l'amplitude qu'une pression donnée obtient décroît en `1/ω²`. À 622 Hz la
languette bouge trente fois moins qu'à 110 Hz, pour un jeu de fente
inchangé — elle ne module plus rien.

Le facteur d'accordéon ne fait pas autrement : il a une languette **par
note**. On applique donc une similitude géométrique, la plus simple des lois
et celle qu'approchent les jeux réels dans un registre :

    L ∝ 1/f,  largeur ∝ 1/f,  épaisseur ∝ 1/f     →  m ∝ 1/f³

ce qui redonne bien `f ∝ e/L²` pour une poutre encastrée.

Le volume de chambre, lui, n'est pas un choix. Pour que le couplage
anche↔chambre garde la même force d'une note à l'autre, il faut le rapport
`A²/(C·m·ω²)` constant. En y portant `A ∝ L·l` et `m ∝ L·l·e` avec une
similitude quelconque `L ∝ f^−λ`, **λ s'élimine** et il ne reste que :

    V ∝ 1/f³

40 cm³ pour le la grave, un dixième de centimètre cube dans l'aigu : l'ordre
de grandeur des cellules d'un vrai sommier. Un résultat qu'on n'a pas choisi
est toujours plus solide qu'un paramètre qu'on ajuste.

### Un modèle physique ne joue pas la fréquence qu'on lui dessine

Correction de pavillon, tirage de l'anche, raideur de la chambre : selon la
note et la famille, l'écart entre la cote dessinée et la hauteur jouée va de
1 à 40 cents. Sur un clavier, ça s'entend immédiatement.

`_accorder` fait ce que fait un facteur : il mesure ce que la note donne,
corrige la **cote**, remesure. Deux passes suffisent, l'écart étant presque
proportionnel à la correction. Ce qu'on corrige est la géométrie, pas la
sortie — le timbre, le transitoire et le seuil restent ceux de l'instrument
accordé, et non ceux d'un instrument faux qu'on transposerait.

Sur trois octaves et les sept instruments : écart médian **0,1 à 0,6 cent**,
aucun au-delà de 7.

### Le silence ne vient pas tout seul

Une note relâchée ne s'éteignait jamais. La cause est dans le débit de
Bernoulli : `q ∝ √|Δp|` a une pente **infinie** en zéro, donc le modèle
s'auto-entretient à pression nulle. Le débit est maintenant régularisé,
`q ∝ Δp/√(|Δp| + p_visc)` — linéaire (visqueux) sous `p_visc`, en racine
au-dessus, ce qui est la physique d'une fente étroite à très faible vitesse.
La voix se libère alors en ~350 ms, par extinction physique.

### Mesurer l'échelle de sortie, deux fois plutôt qu'une

La sortie du moteur est une grandeur physique — des pascals dans une perce,
des mètres par seconde sur une corde — et rien ne la met entre −1 et 1. Le
facteur est donc mesuré. Deux pièges s'y sont succédé : le mesurer **après**
l'écrêtage de `Synth` (on lit 1,0 pour tout le monde), puis l'arrêter dès que
la crête cesse de monter. Une corde frottée monte par paliers — 0,87 puis
0,98, puis un faux plateau à 0,99, puis 1,5 : le critère s'y laissait
prendre, sous-estimait la vielle de 25 %, et la saturait ensuite en jeu. On
rend désormais la durée entière, sur cinq notes de la tessiture, et
`Synth.render` finit au limiteur doux plutôt qu'au `clip`.

---

## 9. TUTT comme moteur du résonateur — et une erreur retrouvée dans son source

« TUTT est une référence ultime en tant que modèle physique » — c'est le
mandat. En allant le chercher dans le Drive, c'est le **source Fortran** qui a
tranché une question que trois jours de mesures n'avaient pas réussi à
trancher.

### L'échec d'abord : le cône idéalisé ne donnait pas l'octave

Première version du moteur : une perce idéalisée à un tronçon, cylindre ou
cône, passée dans la chaîne d'impédance du module (matrices de transfert,
pertes de Kirchhoff/Mason, rayonnement). Le **cylindre** sortait juste — série
impaire exacte, registre à la douzième. Le **cône** sortait faux d'un demi-ton :
au lieu de l'octave attendue (rapports 1 : 2 : 3), il donnait 1 : 1,72 : 2,42,
jusqu'à 330 cents d'écart.

Trois hypothèses éliminées par la mesure, dans l'ordre :

1. *un manque de finesse de découpage* — non, le sous-découpage convergeait
   déjà ;
2. *une question d'échelle* — non, réduire le rayon tronqué de 0,5 mm à 0,5 µm
   ne change rien ;
3. *une question de longueur virtuelle manquante* — non, pousser le rapport
   pavillon/anche de 4,5 à 100 ne bouge pas le motif des rapports.

Le motif, lui, était identifiable : les rapports 1 : 1,719 : 2,427 : 3,130
sont les racines de `tan(kL) = kL`, la signature d'un cône **fermé** à son
petit bout. Le calcul faisait donc quelque chose de cohérent — mais pas ce
qu'on lui demandait. Conclusion prudente de l'époque : garder les trois
instruments coniques sur la série postulée, écrire le résultat négatif, et
poser un test qui **échouerait exprès** si quelqu'un corrigeait un jour le
modèle sans mettre l'avertissement à jour.

### Le source de TUTT donne la réponse en trois lignes

`Perce2.for` caractérise chaque tronçon par une seule grandeur :

    DELTA = (DL − D0) / (D0 · L)        « CARACTERISE LA CONICITE DU TRONCON »

et la passe à `LTRANS`. `Ltran9.for` dit alors ce que sont les champs dans un
tronçon tronconique — et ce ne sont **pas** des ondes planes :

    p(x) = (A·e^(jkx) + B·e^(−jkx)) / (1 + Δx)
    w(x) = −S₀/(jωρ) · [A·(jk + Δ(jkx−1))·e^(jkx) − B·(jk + Δ(jkx+1))·e^(−jkx)]

Le `1/(1 + Δx)` sur la pression est la décroissance sphérique du cône ; les
termes en `Δ` sur le débit en sont la contrepartie. **Ce sont eux qui font
qu'un cône est un cône.** Un empilement de cylindres — ce que faisait ce
module — les perd tous : chaque tranche est un tuyau droit, la section change
d'une tranche à l'autre mais l'onde à l'intérieur reste plane. D'où un
résultat qui se comporte comme un tube **fermé** au petit bout, et le
`tan(kL) = kL`.

L'erreur n'était donc ni dans TUTT, ni dans le cône, ni dans la troncature :
elle était dans mon approximation.

### Ce que ça donne une fois corrigé

`tutt._z_troncon` implémente la formule telle quelle — un tronçon en **un
seul pas**, si long soit-il, au lieu d'un découpage à convergence surveillée.
Plus juste *et* plus rapide, ce qui n'arrive pas si souvent. TUTT le dit
d'ailleurs lui-même : « LES TRONCONS SONT SUPPOSES TRONCONIQUES ; ILS PEUVENT
ETRE LONGS CAR ON TIENT COMPTE DES VARIATIONS SPATIALES DE PRESSION ET DE
DEBIT ».

| perce | avant (cylindres empilés) | après (tronçon conique exact) |
|---|---|---|
| cylindre Ø 15 mm, 500 mm | 167,4 / 505,9 / 845,1 Hz | 167,3 / 505,9 / 845,0 Hz |
| cône, rapport 10 | 1 : 8,55 : 14,7 | **1 : 2,02 : 3,06 : 4,12** |
| cône, rapport 4,5 | 1 : 5,83 : 9,98 | **1 : 2,11 : 3,30 : 4,52** |

Le cylindre ne bouge pas (la formule y dégénère exactement), et le cône donne
enfin l'octave. Le test négatif a été retourné en test positif, comme prévu.

### Et la cavité d'anche de Ninob referme la boucle

Il reste, sur le cône à rapport 4,5, une octave trop haute de **+95 cents** :
c'est la troncature — il manque le bout pointu. Ninob l'a traitée dans *Modes
propres d'un tronc de cône* : une anche solide au petit bout se comporte comme
une **cavité ajoutée**, qui abaisse les modes graves plus que les aigus et
corrige l'octave. C'est ce qui permet à un saxophone ou à un hautbois
d'octavier juste.

Vérifié ici, sur la perce ci-dessus (volume de cône manquant : 1,12 cm³) :

| cavité d'anche | octave |
|---|---|
| aucune | +95,1 cents |
| 0,5 cm³ | +66,8 |
| 1,12 cm³ (le cône manquant) | +27,0 |
| **1,50 cm³** | **+1,8** |
| 2,0 cm³ | −29,9 |

Le volume qui corrige vaut environ 1,3 fois le cône géométriquement manquant.
Le paramètre existait déjà dans le module (`reed_volume_m3`) et n'était
« jamais appliqué automatiquement » faute de savoir à quoi il servait
vraiment. Maintenant on sait, et on sait le mesurer.

### Ce qui reste, et pourquoi les coniques ne passent pas encore en jeu

La physique est juste ; c'est la **géométrie idéalisée** qui ne l'est pas
assez. Une perce conique à un seul tronçon a un fondamental trop faible : son
deuxième sommet d'impédance sort **3 dB au-dessus** du premier, et l'anche s'y
accroche — au clavier, la note sort une octave trop haut sur une partie de la
tessiture. La cavité d'anche corrige la justesse de l'octave, pas ce
déséquilibre-là (elle l'accentue même : +5,4 dB).

C'est d'ailleurs un trait réel des perces coniques étroites — une bombarde est
réputée difficile à faire parler dans le grave. Mais ici il vient surtout de la
troncature. Deux choses le lèveraient, et aucune n'est un réglage :

- une **vraie perce**, dont le profil complet renforce le fondamental — et
  `tutt.scale_bore` sait déjà en couvrir un clavier entier ;
- un modèle d'**embouchure** : le pincement des lèvres, ce par quoi un sonneur
  choisit son registre. Notre excitateur n'a rien de tel.

D'ici là : `clarinette` passe par `engine='tutt'` (0,3 cent d'écart médian sur
la tessiture), les trois coniques gardent la série postulée, et le calcul
conique exact sert à tout ce qui passe par une **vraie** perce.

### Ce que le source a donné d'autre, et qui n'est pas encore exploité

`Ltran9.for` contient deux choses de plus, lues et notées :

- **les trous latéraux** — tableau `CP` (0 = ouvert, 1 = fermé), branches
  latérales `AP`/`BP` avec leur propre constante de propagation et leur
  impédance de bout. C'est l'algorithme exact du chantier « trous latéraux »,
  qui n'a plus besoin d'être inventé ;
- **la définition même de la résonance** : TUTT ne cherche pas les sommets de
  |Z| du tube nu, mais les **zéros de la partie imaginaire** de
  `Z = Z_anche + (Z_tube + Z_bouche)/FC`, anche comprise
  (`Z_anche = j(M·ω − K/ω)/A²`). D'où cette remarque de Ninob, qui vaut pour
  toute la suite : avec une anche **solide** on joue près des *antirésonances*
  du tube, avec une anche **aérienne** (flûte) près de ses *résonances*.
