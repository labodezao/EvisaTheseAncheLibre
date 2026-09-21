# Partie II — Ce qui s'accroche

> *Hystérésis, bistabilité, et le prix d'un changement d'état.*

---

La Partie I s'est arrêtée sur une dette. Nous avions vu qu'une anche
sous-critique démarre à une pression $p_{\text{on}}$ et s'éteint à une
pression $p_{\text{off}}$ plus basse :

$$p_{\text{on}} \;>\; p_{\text{off}}$$

et j'avais dit qu'on y reviendrait. Nous y sommes. Cet écart est, je crois,
le fait le plus intéressant de tout ce livre, et le plus difficile à
accepter dans les deux sens du mot.

---

## Chapitre 3 — Il faut plus pour démarrer que pour continuer

### Le fait, tout simple

Faites l'expérience. Montez très lentement la pression jusqu'à ce que
l'anche démarre : notez $p_{\text{on}}$. Puis, sans interruption, redescendez
aussi lentement jusqu'à ce qu'elle se taise : notez $p_{\text{off}}$.

Vous trouverez que $p_{\text{off}}$ est **plus basse**. Parfois de quelques
pour cent, parfois de beaucoup. L'anche continue de sonner dans des
conditions où, en montant, elle n'aurait pas su commencer.

Prenez la mesure de ce que cela signifie. À une pression intermédiaire —
entre $p_{\text{off}}$ et $p_{\text{on}}$ — l'instrument a **deux**
comportements possibles, et ce n'est pas la pression qui décide lequel. La
pression, à elle seule, ne suffit pas à dire ce que fait l'anche. Il faut
savoir **d'où elle vient**.

C'est ce qu'on appelle une hystérésis, du grec *hystérein*, « être en
retard, venir après ». Le mot est bien choisi : l'état actuel traîne
derrière la cause actuelle, parce qu'il traîne aussi le passé.

Un système qui présente une hystérésis a une **mémoire**. Pas une mémoire
stockée quelque part, pas un registre ni une trace : sa mémoire *est* son
état. Il se souvient de son histoire en étant ce qu'il est devenu.

### Deux creux dans un paysage

L'image qui éclaire tout, c'est celle d'un paysage.

Représentons l'état du système — disons l'amplitude de l'oscillation — par
la position d'une bille dans un paysage vallonné, et notons $\Phi$ la
hauteur du terrain. La bille descend la pente ; elle s'immobilise au fond
d'un creux. Un creux est un **état stable**, une crête un **état instable**.

Loin du seuil, en dessous, il n'y a qu'un creux : l'anche muette. Loin
au-dessus, il n'y en a qu'un aussi : l'anche qui sonne. Mais dans
l'intervalle $[p_{\text{off}}, p_{\text{on}}]$ — et c'est tout le propos —
**il y en a deux**, séparés par une crête.

Le système est **bistable**. La bille est dans l'un des deux creux, celui où
son histoire l'a mise, et elle y reste tant que rien ne lui fait franchir la
crête.

Ce paysage n'est pas une métaphore que j'invente pour expliquer : c'est un
objet qu'on peut **reconstruire à partir d'un enregistrement**, et le dépôt
sait le faire. La méthode s'appelle la reconstruction de Kramers–Moyal, ou
approche de Friedrich–Peinke. On part d'une série temporelle $x(t)$, on
suppose qu'elle obéit à une équation de Langevin

$$dx \;=\; D_1(x)\,dt \;+\; \sqrt{2\,D_2(x)}\;dW$$

où $D_1$ est la **force déterministe** (la pente du paysage) et $D_2$
l'intensité du **bruit**, et l'on estime les deux à partir des données, bin
par bin en $x$ : $D_1(x)$ est la moyenne des petits déplacements observés
depuis $x$, $D_2(x)$ leur variance. Le potentiel s'obtient ensuite en
intégrant :

$$\Phi(x) \;=\; -\!\int \frac{D_1(x)}{D_2(x)}\,dx$$

Un creux dans $\Phi$, monostable. Deux creux, bistable — et vous tenez la
signature directe d'une bifurcation sous-critique, lue dans le signal,
sans avoir eu à supposer quoi que ce soit du mécanisme.

```python
from banc_recherche import stochastic as st

km = st.kramers_moyal(serie, dt, bins=41)      # D₁ et D₂ par bin
x, phi = st.potential_from_drift(km)           # le paysage
creux = st.potential_minima(x, phi)            # un puits, ou deux ?
```

---

## Chapitre 4 — Franchir la crête, et ce que ça coûte

### Le bruit n'est pas seulement une gêne

Si le paysage était tout, la bille ne bougerait jamais de son creux. Il n'y
aurait pas d'hystérésis à observer mais un simple verrou : une fois muette,
muette pour toujours, tant que le paysage ne change pas.

Ce n'est pas ce qui se passe, parce qu'il y a du **bruit**. L'air qui passe
dans la fente est turbulent, le métal a une agitation thermique, la table
vibre, et toutes ces choses secouent la bille en permanence. La plupart du
temps ces secousses ne servent à rien : la bille remonte un peu la pente et
redescend.

Mais de temps en temps — rarement — une fluctuation suffit à lui faire
franchir la crête. Et là, elle bascule dans l'autre creux et y reste.

Le taux auquel cela se produit est donné par une formule que Kramers a
établie en 1940, et qui est l'un des résultats les plus utiles de toute la
physique statistique :

$$r \;=\; \frac{1}{2\pi}\sqrt{U''(\text{creux})\,\big|U''(\text{crête})\big|}
\;\;e^{-\Delta U / D}$$

Lisez-la lentement, parce qu'elle dit trois choses distinctes.

**L'exponentielle domine tout.** $\Delta U$ est la hauteur de la barrière,
$D$ l'intensité du bruit. C'est leur **rapport** qui compte, et il est dans
une exponentielle : doublez la barrière et le temps d'attente ne double pas,
il est élevé au carré. Un système peut passer de « bascule toutes les
secondes » à « ne bascule jamais de votre vivant » pour une barrière deux
fois plus haute. Il n'y a pas de régime intermédiaire confortable.

**Le préfacteur ne dit que la vitesse d'essai.** Les courbures $U''$
donnent la fréquence à laquelle la bille se présente devant la crête —
combien de fois par seconde elle tente sa chance. C'est une correction, pas
le cœur.

**Et il n'y a pas de seuil.** La formule ne dit jamais « impossible ». Elle
dit « rare ». Un état stable n'est jamais définitif : il est seulement un
état dont on sort lentement. C'est une nuance qui change beaucoup de choses
quand on la prend au sérieux.

```python
r = st.kramers_from_potential(x, phi, D=bruit)   # taux d'échappement, /s
print(1 / r, "secondes en moyenne avant de basculer")

sejours = st.residence_times(etat_binaire, dt)   # {0: [...], 1: [...]}
```

### Un incident, qui est aussi une leçon

Il faut que je raconte ce qui s'est passé à l'instant où j'écrivais ce
chapitre, parce que c'est exactement le sujet du livre.

Je voulais donner ici un chiffre vrai. J'ai donc simulé un double puits —
la forme la plus simple qui soit, $dx = (x - x^3)\,dt + \sqrt{2D}\,dW$, dont
le potentiel $U = -x^2/2 + x^4/4$ a deux creux en $\pm 1$ séparés par une
barrière de 0,25 — et j'ai demandé à notre propre code le taux
d'échappement. Il a répondu :

$$r \;=\; 1{,}8 \times 10^{-12}\ \text{par seconde}$$

soit environ trente mille ans entre deux basculements. Or dans la
simulation, je **voyais** la bille basculer. Vingt-huit fois en vingt
minutes de temps simulé.

Douze ordres de grandeur. Il n'y a aucune interprétation charitable
possible : le code se trompait.

La cause s'est révélée petite et vicieuse. Notre estimateur du potentiel
calcule $\Phi = -\!\int D_1/D_2\,dx$ — il divise **déjà** par l'intensité du
bruit. Le potentiel reconstruit n'est donc pas $U$, c'est $U/D$. Et la
fonction qui en tirait le taux de Kramers le redonnait à la formule avec le
$D$ physique, qui divisait une seconde fois. L'exposant valait $\Delta U/D^2$
au lieu de $\Delta U/D$. Avec $D = 0{,}1$, cela fait un facteur dix dans
l'exponentielle — et l'exponentielle, on vient de le voir, ne pardonne pas.

Ce qui m'intéresse ici n'est pas le bug. C'est que **rien** ne le signalait.
Pas d'exception, pas de valeur aberrante à l'œil : un nombre, avec des
unités correctes, du bon signe, parfaitement plausible pour qui n'aurait pas
eu sous la main quelque chose à quoi le comparer. Il a fallu lui opposer un
comptage direct — combien de fois, réellement, la bille a-t-elle changé de
creux — pour que le mensonge apparaisse.

C'est le seul protocole qui vaille : **ne jamais faire confiance à un
chiffre qui n'a pas été confronté à un autre chiffre obtenu autrement.** Pas
« vérifié » — confronté. Une relecture du code n'aurait rien donné ; j'avais
déjà relu ces cinq lignes et elles étaient jolies.

Une fois corrigé, les trois chemins — la formule appliquée directement, le
potentiel réduit, le potentiel en énergie physique — donnent le même taux à
0,1 % près, et il reste un écart d'un facteur 1,6 avec le comptage direct.
Celui-là est honnête et attendu : la formule de Kramers est asymptotique
pour $\Delta U/D \gg 1$, et ici ce rapport ne vaut que 2,5. La barrière
n'est pas assez haute pour que l'approximation soit bonne. C'est le genre
d'écart qu'il faut savoir garder plutôt que faire disparaître.

---

## Résonance intérieure

### Le mot juste existe depuis longtemps

Dans la langue de la pratique dont je parlais au prélude, il y a un mot
pour désigner précisément ce qui s'accroche : *saṅkhāra*. On le traduit par
« formation », « conditionnement », « construction mentale ». Ce n'est pas
un souvenir. C'est une réaction qui s'est installée, et qui se rejoue, et
qui à force de se rejouer est devenue la forme même de la manière dont on
réagit.

Ce qui me frappe, dans la rencontre entre ce mot et la physique de ce
chapitre, ce n'est pas une ressemblance vague. C'est la **structure
précise**, qui tient en trois traits, et les trois se retrouvent.

**Un : ce n'est pas une mémoire, c'est un état.** L'anche ne garde aucune
trace de $p_{\text{on}}$ quelque part ; elle est simplement, maintenant,
dans le creux où son histoire l'a mise. On ne peut pas aller effacer le
souvenir, parce qu'il n'y a pas de souvenir à effacer — il y a un état à
quitter. Je trouve que cela dit quelque chose de juste sur pourquoi
*comprendre* d'où vient une habitude ne suffit jamais à en sortir.

**Deux : il en faut plus pour entrer que pour rester.** L'écart
$p_{\text{on}} - p_{\text{off}}$ dit exactement cela, et dans les deux sens.
Pour une chose qu'on voudrait installer, le coût d'entrée est plus élevé que
le coût d'entretien : c'est une bonne nouvelle, et tous ceux qui ont tenu
une pratique quotidienne pendant trois semaines la connaissent. Pour une
chose dont on voudrait sortir, c'est l'inverse et c'est exactement la même
loi : l'état se maintient bien en dessous des conditions qui l'ont créé. Le
comportement continue longtemps après que sa raison a disparu. Ce n'est pas
de la faiblesse. C'est de la bistabilité.

**Trois : on ne sort pas d'un puits en poussant — on en sort par une
fluctuation.** Voilà le point de Kramers, et il est contre-intuitif au point
d'être désagréable. Dans un système suramorti, la bille ne franchit pas la
crête parce qu'on l'a poussée continûment : elle la franchit parce qu'une
secousse du bruit l'a portée au-dessus, un instant. Ce qui détermine le taux
d'échappement, ce n'est pas la force moyenne, c'est le rapport $\Delta U/D$
entre la hauteur de la barrière et l'agitation.

Ce qui donne deux manières, et deux seulement, d'augmenter ses chances :
**abaisser la barrière** ou **augmenter l'agitation**. Et si l'on y tient,
une troisième, qui est d'attendre : puisqu'il n'y a pas de seuil, seulement
une rareté, le temps finit par produire ce que la force ne produit pas.

Je ne pousserai pas plus loin, parce que c'est ici qu'on pourrait facilement
dire une bêtise élégante. Mais je remarque que les traditions qui savent
défaire des conditionnements ne procèdent jamais par volonté frontale. Elles
procèdent par exposition répétée et par non-réaction — ce qui, dans le
vocabulaire de ce chapitre, revient très exactement à **ne pas nourrir la
barrière** pendant que le bruit ordinaire de la vie fait son travail. La
consigne d'observer une sensation sans y réagir n'a rien d'une passivité :
c'est une manière de cesser de creuser le puits pendant qu'on est dedans.

Et l'incident du chapitre 4 vaut pour les deux côtés. Un chiffre qui n'a
été confronté à rien n'est pas un savoir. Une impression sur soi-même qui
n'a été confrontée à rien non plus. Dans les deux cas, ce qui fait la
différence n'est pas la sincérité — j'étais parfaitement sincère devant mon
$1{,}8 \times 10^{-12}$ — mais le fait d'avoir accepté de mettre à côté une
seconde mesure obtenue autrement, et de regarder l'écart.

---

⟢ **ton expérience** — une hystérésis intime : quelque chose qui a continué
bien après que la raison de le faire avait disparu. Et, si tu en es sorti :
ce qui, ce jour-là, était différent — la barrière, ou l'agitation ?

---

*Nous avons parlé des états et de leur persistance. Il est temps de regarder
ce qui se passe pendant le passage lui-même : la Partie III.*
