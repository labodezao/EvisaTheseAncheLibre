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
