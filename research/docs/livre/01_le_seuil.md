# Partie I — Le seuil

> *La bifurcation de Hopf, et ce que veut dire « ça y est ».*

---

## Chapitre 1 — Une anche est une machine à faire du rythme avec du continu

### Le problème, posé comme il faut

Voici le fait brut, et il est plus étrange qu'il n'en a l'air.

Vous fournissez à l'instrument de l'énergie **constante**. Le soufflet
s'ouvre régulièrement, la différence de pression entre les deux faces de
l'anche s'établit et reste là. Rien dans ce que vous donnez n'est périodique.
Il n'y a pas d'horloge, pas de battement, pas de rythme.

Et il en sort un son de 440 hertz. C'est-à-dire un événement qui se répète
quatre cent quarante fois par seconde, avec une régularité telle qu'une
oreille entraînée détecte un écart d'un millième de demi-ton.

D'où vient la période ? Ce n'est pas vous qui l'apportez. Ce n'est pas non
plus, comme on le croit souvent, simplement « la fréquence propre de
l'anche », parce qu'une anche qu'on pince et qu'on lâche dans l'air libre ne
sonne pas à la même fréquence que la même anche en train de jouer — l'écart
se compte en dizaines de cents, parfois plus, et il dépend de la pression.

La période est **fabriquée**. Elle est le produit d'une machine, et cette
machine mérite qu'on la regarde de près, parce que tout le reste du livre en
découle.

### La lame qui contrôle son propre approvisionnement

Prenez une anche libre d'accordéon : une lame d'acier rivetée à un cadre,
qui oscille **dans** une lumière découpée à ses mesures. Elle ne bat pas
contre une table comme l'anche simple d'une clarinette ; elle passe à
travers. De là son nom.

Quand elle est au repos, elle bouche presque entièrement la lumière. Le
passage laissé libre est une fente de quelques centièmes de millimètre. Quand
elle s'écarte, la fente s'ouvre ; quand elle revient, la fente se ferme.

Suivons maintenant ce que fait l'air. Il y a une différence de pression
$\Delta p$ entre l'amont et l'aval. Le débit $q$ qui traverse dépend de deux
choses : de $\Delta p$, et de la **section ouverte** — c'est-à-dire de la
position de l'anche. Écrivons-le grossièrement :

$$q \;\simeq\; S(x)\,\sqrt{\frac{2\,\Delta p}{\rho}}$$

où $x$ est le déplacement de l'anche, $S(x)$ la section qu'elle laisse
libre, $\rho$ la masse volumique de l'air. C'est la relation de Bernoulli,
appliquée à un jet qui se forme dans la fente. (Elle n'est pas exacte : près
de $\Delta p = 0$ le jet ne se forme pas et l'écoulement redevient visqueux ;
on y reviendra, parce que c'est précisément là que se joue le seuil. Dans le
code du dépôt, la version employée est régularisée,
$q \propto \Delta p / \sqrt{|\Delta p| + p_{\text{visc}}}$, ce qui évite la
tangente verticale à l'origine tout en redonnant Bernoulli dès qu'on
s'éloigne de zéro.)

Voilà la boucle, et elle se dit en trois phrases :

1. la pression pousse l'anche ;
2. l'anche, en bougeant, **change la section** par laquelle l'air passe ;
3. l'air qui passe change la pression qui pousse l'anche.

La lame contrôle son propre approvisionnement. Une vanne qui commande le
robinet qui l'alimente. Si le déphasage entre son mouvement et la force
qu'elle reçoit est favorable, alors à chaque aller-retour elle reçoit un
peu plus d'énergie qu'elle n'en perd en frottements et en rayonnement — et
son amplitude grandit. Sinon, elle s'amortit et se tait.

Tout tient dans ce mot : **un peu plus**.

### Ce qu'un oscillateur auto-entretenu n'est pas

Il vaut la peine d'écarter deux images fausses, parce qu'elles sont
tenaces.

Ce n'est pas une **résonance**. Dans une résonance, on excite à une
fréquence et le système répond fort à cette fréquence-là ; il faut donc déjà
que quelque chose oscille pour entretenir l'oscillation. Ici, rien n'oscille
en entrée. Le système choisit sa fréquence tout seul.

Ce n'est pas non plus un **amplificateur**. Un amplificateur multiplie ce
qu'on lui donne ; donnez-lui zéro, il rend zéro. Ici, on donne quelque chose
de rigoureusement constant et il en sort quelque chose de rigoureusement
périodique. Le rythme n'est pas dans l'entrée, même en germe.

La bonne image, c'est l'archet sur la corde, la girouette qui se met à
battre dans un vent régulier, le robinet qui chante, le pont de Tacoma. Une
famille entière de systèmes qui convertissent un flux continu en mouvement
périodique, et qui ont tous en commun une chose : **ils ont un seuil**.

---

## Chapitre 2 — Le seuil

### En dessous, rien. Pas « peu » : rien.

C'est le point le plus important du chapitre, et celui qu'on accepte le plus
mal.

Prenez l'anche au repos. Montez la pression très lentement, à partir de
zéro. Tant que vous êtes en dessous d'une certaine valeur — appelons-la
$p_{\text{on}}$ — l'amplitude de l'oscillation périodique est **exactement
nulle**. Pas petite. Nulle.

Ce qu'on entend en dessous du seuil, et qu'on entend vraiment (un souffle,
un sifflement, un bruit de fente), n'est pas une petite oscillation de
l'anche. C'est du bruit d'écoulement : de la turbulence dans la fente,
filtrée par le tuyau. Le mode propre de l'anche, lui, est **stable**. Si une
perturbation l'écarte, il revient. Il revient de plus en plus lentement à
mesure qu'on approche de $p_{\text{on}}$ — nous y reviendrons, c'est un des
plus beaux faits de toute cette histoire — mais il revient.

Au-dessus de $p_{\text{on}}$, il ne revient plus. La position de repos
devient **instable**, et le système s'en éloigne jusqu'à se stabiliser sur
un mouvement périodique : un **cycle limite**.

Ce changement de nature d'un état d'équilibre, quand on fait varier
lentement un paramètre, porte un nom : une **bifurcation**. Et celle-ci,
où un point fixe stable perd sa stabilité au profit d'un cycle, porte le nom
de Hopf.

### Ce que dit l'algèbre, et pourquoi elle le dit si bien

Linéarisons autour du silence. Écartons l'anche d'un tout petit $x$ de sa
position d'équilibre et demandons comment cet écart évolue. Pour de très
petits écarts, la réponse est toujours de la forme

$$x(t) \;\sim\; e^{\lambda t}, \qquad \lambda = \sigma + i\,\omega$$

où $\lambda$ est une **valeur propre** du système linéarisé. Sa partie
imaginaire $\omega$ dit à quelle fréquence l'écart oscille ; sa partie réelle
$\sigma$ dit s'il grandit ou s'il s'éteint :

- $\sigma < 0$ : $e^{\sigma t}$ décroît, l'écart s'amortit, le silence est
  stable ;
- $\sigma > 0$ : $e^{\sigma t}$ croît, le silence est instable, la note
  démarre.

Le seuil, c'est donc **exactement** l'instant où $\sigma$ passe par zéro.
Rien d'autre. Toute la physique compliquée de la fente, du jet, du couplage
avec le tuyau, sert à calculer une seule chose : le signe d'un nombre réel.

Et remarquez ce que cela donne au passage. Au moment précis où $\sigma = 0$,
il reste $\lambda = i\,\omega_c$ : l'écart n'est ni amorti ni amplifié, il
oscille indéfiniment à la pulsation $\omega_c$. **C'est la fréquence de
naissance de la note.** Elle est donnée par le système tout entier — anche
*et* colonne d'air couplées — ce qui explique enfin pourquoi elle n'est pas
la fréquence de l'anche pincée à l'air libre.

La note ne naît pas quelque part et ne se propage pas ensuite. Elle naît de
l'ensemble, d'un coup, avec sa hauteur déjà décidée.

### Quelle allure prend l'amplitude juste après ?

Au-dessus du seuil, de combien ? Il y a deux réponses possibles, et
distinguer laquelle s'applique à une anche donnée est une vraie question
expérimentale — pas un détail de classification.

Appelons $\mu$ le paramètre qu'on pousse (la pression, ou la vitesse du
soufflet) et $\mu_c$ sa valeur au seuil.

**Cas supercritique.** L'amplitude $A$ du cycle limite part de zéro et
croît continûment, comme la racine carrée de l'écart au seuil :

$$A^2 \;\propto\; (\mu - \mu_c)$$

C'est la **forme normale de Stuart–Landau**, et elle n'a rien d'un ajustement
empirique : elle est ce que devient *n'importe quel* système au voisinage
d'une bifurcation de Hopf, une fois qu'on a jeté tout ce qui est négligeable.
Cette universalité est l'une des grandes leçons de la théorie des systèmes
dynamiques, et Penrose en aurait fait un chapitre : les détails sordides de
la fente, du métal, de l'humidité, disparaissent, et il ne reste qu'une
parabole.

Physiquement : le son démarre **doucement**. On peut jouer *pianissimo*
aussi bas qu'on veut.

**Cas sous-critique.** L'amplitude **saute**. Il n'existe pas de cycle
limite de petite amplitude : au moment où le silence devient instable, le
seul régime disponible est déjà gros, et le système y tombe d'un coup.

Physiquement : le son démarre **fort**, ou pas du tout. Il n'y a pas de
*pianissimo* possible. Beaucoup d'anches se comportent ainsi, et tous ceux
qui ont essayé de faire démarrer une note très doucement sur un instrument
récalcitrant le savent avec les mains avant de le savoir avec les
mathématiques.

Et le cas sous-critique apporte quelque chose de plus, qui occupera toute la
Partie II : il vient avec une **hystérésis**. La pression qu'il faut pour
démarrer n'est pas celle en dessous de laquelle ça s'éteint.

$$p_{\text{on}} \;>\; p_{\text{off}}$$

Une fois que ça sonne, ça continue de sonner plus bas que là où ça n'aurait
pas pu commencer.

### Le ralentissement critique — le plus beau fait du chapitre

Revenons à $\sigma$, la partie réelle de la valeur propre, celle qui doit
changer de signe.

Loin du seuil, $\sigma$ est franchement négatif : une perturbation s'éteint
en quelques millisecondes. Mais $\sigma$ tend vers zéro quand $\mu \to
\mu_c$, et le temps de retour à l'équilibre, qui vaut $1/|\sigma|$,
**diverge**.

Cela veut dire quelque chose de très concret, et de mesurable avec un micro à
trois euros : *plus on est proche du seuil, plus tout devient lent*. Le
transitoire d'attaque s'allonge. Une note jouée juste au-dessus de son seuil
met un temps déraisonnable à s'établir — on l'entend hésiter, chercher,
s'installer. Une note jouée bien au-dessus s'installe immédiatement.

Et le revers, plus troublant : **près du seuil, le système est infiniment
sensible**. Puisqu'il ne revient presque plus, la moindre fluctuation — un
souffle d'air, une vibration de la table, le bruit thermique — le déplace
durablement. Le seuil n'est pas seulement l'endroit où ça bascule. C'est
l'endroit où le système **n'a plus de mémoire de sa position d'équilibre**,
et où donc le hasard décide.

C'est pour cette raison que $p_{\text{on}}$ mesuré n'est jamais deux fois le
même. Il n'est pas un nombre, il est une distribution. Nous verrons en
Partie VI que ce n'est pas un défaut de la mesure mais une propriété du
vivant, et qu'on peut en tirer davantage que d'une mesure parfaite.

---

## Le mesurer soi-même, avec presque rien

Tout ce chapitre se vérifie avec une carte son, un micro, et de quoi faire
monter la pression lentement. Sur le banc décrit dans ce dépôt, c'est le
soufflet motorisé ; mais une seringue, un ballon qui se dégonfle ou un
soufflet à main font l'affaire, du moment que la montée est **lente devant
le temps d'établissement** — sinon on mesure le retard de sa propre rampe.

Le protocole est celui de `mes_seuil_autoentretien.py`, repris dans le module
`seuil` :

1. monter lentement la pression jusqu'à ce que l'oscillation démarre →
   $p_{\text{on}}$ ;
2. redescendre lentement jusqu'à ce qu'elle s'éteigne → $p_{\text{off}}$ ;
3. l'écart $p_{\text{on}} - p_{\text{off}}$ est l'hystérésis de cette anche.

Les deux grandeurs qu'on donne au code sont la **pression** et l'**amplitude
de l'oscillation** — l'enveloppe du signal, pas le signal lui-même — prises
au même instant, et `amp_thresh` est le niveau au-dessus duquel on décide
que « ça sonne ». Ce seuil-là est arbitraire et il faut le dire : il ne
change pratiquement rien tant que la montée d'amplitude est franche, et il
change tout si elle ne l'est pas. C'est une raison de plus de regarder la
courbe avant de lire le chiffre.

```python
from banc_recherche import seuil, bifurcation

s = seuil.detect(pression, amplitude, amp_thresh=0.05)
print(s.p_on, s.p_off, s.hysteresis)

d = bifurcation.diagram(p_montee, a_montee, p_descente, a_descente,
                        amp_thresh=0.05)
print(d.kind)                          # 'supercritique' ou 'souscritique'
print(d.hopf.threshold, d.hopf.r2)     # A² ∝ (μ − μc) : seuil et qualité
```

`bifurcation.hopf_amplitude_fit` ajuste $A^2 \propto (\mu - \mu_c)$ sur la
branche mesurée — c'est `d.hopf`, avec son coefficient de détermination, qui
vous dira si la parabole de Stuart–Landau décrit vraiment votre anche ou si
vous la lui imposez. `bifurcation.diagram` classe ensuite la bifurcation à
partir de cet ajustement et de l'hystérésis mesurée.

Le module `ramp` répète l'opération. Sur le banc à soufflet, **pousser** est
une rampe montante et **tirer** une rampe descendante, de sorte qu'une seule
course donne un seuil et que quelques dizaines de courses donnent une
distribution.

Une remarque de méthode, qui vaut pour tout le livre. Ne mesurez pas
$p_{\text{on}}$ une fois. Mesurez-le vingt fois. Le premier chiffre est une
anecdote ; c'est la vingtaine qui est un résultat. Et si l'écart-type est
grand, ce n'est pas votre montage qui est mauvais : c'est le seuil qui est
comme ça.

---

## Résonance intérieure

Je voudrais maintenant dire l'autre côté, et le dire avec précaution.

Quand on s'assoit pour observer ses sensations, il se passe très souvent
ceci. Pendant un long moment — dix minutes, vingt, parfois la séance
entière — il n'y a *rien*. Pas « peu de sensations » : rien. Des zones
entières du corps sont muettes. On le sait, on nous l'a dit, on attend, et il
n'y a rien, et l'esprit commence à trouver que cette pratique est absurde.

Et puis à un moment il y a quelque chose. Pas progressivement. Ce n'est pas
qu'une sensation faible a grandi jusqu'à devenir audible : c'est qu'il n'y
avait rien, et qu'il y a maintenant tout un champ — un fourmillement, une
chaleur, un courant. Et en général on n'a rien fait de plus juste avant. On a
continué à faire exactement la même chose, un peu plus.

La structure est la même que celle de l'anche, et je crois qu'il faut le
prendre au sérieux sans en faire trop. Trois points, et trois seulement.

**Premier point : en dessous du seuil, l'effort supplémentaire ne produit
rien.** C'est une phrase physiquement exacte pour l'anche — sous
$p_{\text{on}}$, l'amplitude du cycle limite vaut rigoureusement zéro, et
pousser plus fort n'y change rien tant qu'on n'a pas franchi — et je la
trouve d'une dureté salutaire appliquée à autre chose. Forcer n'ouvre pas ce
qui n'est pas ouvert. Ce qui franchit le seuil, ce n'est pas la force, c'est
le fait d'avoir continué. Ce n'est pas une consolation pour ceux qui
n'avancent pas : c'est une description de la manière dont certains systèmes
changent d'état, et il se trouve que nous en sommes.

**Deuxième point : la lenteur près du seuil n'est pas un échec, c'est le
signe qu'on y est.** Le ralentissement critique est mesurable sur une anche :
le transitoire s'allonge à l'approche du seuil, parce que $1/|\sigma|$
diverge. C'est peut-être le plus utile de tout le chapitre. Quand quelque
chose devient très lent à revenir à son état habituel — une émotion qui met
des heures à se ranger là où elle mettait des minutes — la lecture spontanée
est : *je vais mal, je régresse*. La lecture dynamique est : *le paramètre a
bougé, l'état où je me tenais n'est plus stable, et je suis en train d'en
approcher la limite*. Ce n'est pas la même chose du tout. Le système ne se
détraque pas ; il est en train de bifurquer.

**Troisième point : au seuil, le hasard décide, et c'est pour cela qu'il ne
faut pas y mettre de volonté.** Près du point critique, le système n'est plus
tenu par son équilibre ; la moindre fluctuation compte. En pratique, sur le
banc, cela veut dire que $p_{\text{on}}$ n'est pas reproductible et qu'il
faut le mesurer plusieurs fois. En pratique, assis, cela veut dire que la
question « est-ce que j'y suis ? » est la seule chose qui garantisse qu'on
n'y sera pas : se la poser, c'est réintroduire dans le système une
perturbation exactement à l'endroit où il y est le plus sensible.

Il faut continuer et laisser faire. Ce n'est pas de la sagesse orientale,
c'est le comportement d'une valeur propre dont la partie réelle traverse
zéro.

Voilà. Je ne dis pas plus, et surtout pas que la physique *prouve* quoi que
ce soit ici. Elle ne prouve rien. Elle **donne une forme** — une forme assez
précise pour qu'on la reconnaisse, et assez générale pour qu'on la retrouve
ailleurs. Les systèmes dynamiques ont cette qualité étrange : leurs résultats
sont universels justement parce qu'ils ne parlent d'aucune substance
particulière. Une bifurcation de Hopf ne sait pas qu'elle est en acier.

---

⟢ **ton expérience** — un seuil franchi. Pas celui que tu racontes
d'habitude : celui où tu peux dire ce que tu faisais juste avant, et
combien de temps tu avais continué sans rien voir venir.

---

*Mais une fois franchi, pourquoi est-il si difficile de revenir en arrière ?
C'est la question de la Partie II.*
