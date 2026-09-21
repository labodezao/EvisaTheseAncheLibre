# Partie III — La naissance de chaque chose

> *Le transitoire d'attaque : rien ne commence instantanément, et le
> commencement a une forme.*

---

Nous avons regardé les états, puis leur persistance. Il reste le plus
intéressant, et le plus fugace : le **passage**. Ce qui se produit entre le
moment où le silence cesse d'être stable et celui où la note est là.

Dans la Partie I j'ai écrit que la note « apparaît », qu'il n'y a pas de
milieu entre les deux régimes. C'était vrai au niveau où je le disais — le
régime change de nature, pas d'intensité — et c'est maintenant qu'il faut le
nuancer, parce que ce passage, lui, **prend du temps**, et que ce temps a
une structure qu'on peut mesurer avec un micro.

---

## Chapitre 5 — Le transitoire d'attaque

### Ce qu'on entend quand on écoute le début

Coupez les cinquante premières millisecondes d'un enregistrement de hautbois
et de piano, et jouez-les à quelqu'un : il aura beaucoup de mal à dire
lequel est lequel. L'expérience est ancienne et elle est robuste. Ce qui
identifie un instrument à l'oreille n'est pas tant son régime établi que la
manière dont il y arrive.

C'est une bonne raison de prendre le transitoire au sérieux, mais ce n'est
pas la mienne. La mienne est que le transitoire est **le seul endroit où
l'on voie la dynamique à l'œuvre**. En régime établi, le système est sur son
cycle limite et il n'a plus rien à nous dire : il tourne. Pendant l'attaque,
il est encore en train de choisir.

### La loi de croissance, et d'où elle vient

Reprenons la valeur propre du chapitre 2, $\lambda = \sigma + i\omega$.
Au-dessus du seuil, $\sigma > 0$, et une petite perturbation croît comme
$e^{\sigma t}$. Mais elle ne peut pas croître indéfiniment : le système est
non linéaire, et à grande amplitude la saturation freine.

La manière propre d'écrire cela est de suivre non pas le signal lui-même
mais son **enveloppe** $A(t)$ — son amplitude lentement variable. On montre
(c'est encore la forme normale de Stuart–Landau, qui décidément sert
partout) que près du seuil l'enveloppe obéit à

$$\frac{dA}{dt} \;=\; \sigma A \;-\; a\,A^3$$

Deux termes, et chacun se lit sans calcul. Le premier, $\sigma A$, est la
croissance exponentielle : plus il y a d'amplitude, plus elle croît, ce qui
est la définition même de l'auto-entretien. Le second, $-aA^3$, est la
saturation : il est négligeable tant que $A$ est petit, et il prend le
dessus brutalement quand $A$ grandit, parce qu'il est cubique.

L'équilibre entre les deux donne l'amplitude finale :

$$A_\infty = \sqrt{\sigma/a}$$

et l'on retrouve exactement $A^2 \propto (\mu - \mu_c)$ — la parabole du
chapitre 2, qui n'était donc pas une loi séparée mais le point fixe de
celle-ci. C'est le genre de recoupement qui fait qu'on se sent, brièvement,
du bon côté des choses.

La courbe $A(t)$ qui en sort a une forme caractéristique : une croissance
d'abord exponentielle, puis un coude, puis un palier. Un « S ». Et surtout,
elle a une **échelle de temps** :

$$\tau \;=\; \frac{1}{\sigma}$$

Tout le transitoire se déroule en quelques $\tau$.

### Le lien avec le seuil, qui est le cœur du chapitre

Souvenez-vous maintenant de ce que fait $\sigma$ quand on approche du seuil :
il tend vers zéro. Donc

$$\tau = \frac{1}{\sigma} \;\longrightarrow\; \infty$$

**Plus on joue près du seuil, plus la note met du temps à naître.** Et pas
un peu plus : le temps d'établissement diverge. Une note attaquée juste
au-dessus de sa pression de démarrage peut mettre plusieurs centaines de
millisecondes à s'installer, là où la même note attaquée franchement est là
en vingt.

C'est le **ralentissement critique** annoncé au chapitre 2, et c'est ici
qu'il devient audible. Tous les musiciens le connaissent sous un autre nom :
la note qui « ne part pas », qui hésite, qui tousse avant de se décider. Ce
n'est pas un défaut de l'instrument ni du souffle. C'est la signature d'un
système qui travaille près de sa bifurcation.

Et cela fournit, au passage, une méthode que je trouve très élégante :
**mesurer le temps d'attaque, c'est mesurer la distance au seuil**. On n'a
pas besoin de savoir où est le seuil pour savoir qu'on en est près. Il
suffit d'écouter combien de temps la note met à venir.

### Le mesurer, toujours avec presque rien

Un micro suffit. On calcule l'enveloppe d'amplitude du signal — une valeur
efficace glissante — et l'on mesure le temps qui sépare le démarrage de
l'atteinte du régime établi. C'est ce que fait `analysis.attack`, avec la
convention de Praat : de l'*onset* (le franchissement d'un seuil bas) à
**90 %** de l'amplitude établie. C'est la grandeur notée `Tresp` dans tout
le dépôt.

```python
from banc_recherche import analysis

env = analysis.envelope(signal, sr)            # valeur efficace glissante
r = analysis.attack(signal, sr, thresh=0.1)
print(r.tresp_ms, r.onset_s, r.steady_amp)
```

Le rapport entre cette grandeur et le $\tau$ de la théorie est calculable, et
il vaut la peine de le poser, parce qu'il permet de traduire une mesure en
une physique. Pour une montée en $A(t) = A_\infty\,(1 - e^{-t/\tau})$, le
temps entre 10 % et 90 % vaut

$$T_{10\to 90} \;=\; \tau\,\Big(\ln 10 - \ln\tfrac{10}{9}\Big) \;\simeq\;
2{,}20\,\tau$$

Et c'est bien ce qu'on mesure : sur des attaques synthétiques de constante
de temps connue, `attack` rend 10,7 ms pour $\tau = 5$ ms, 59 ms pour 30 ms,
116 ms pour 60 ms — le facteur ≈ 2 y est. (L'accord se dégrade aux extrêmes,
et pour une raison qu'il faut dire : l'enveloppe est lissée sur 5 ms par
défaut, ce qui gonfle les attaques très brèves, et une montée très lente
finit par sortir de la fenêtre d'analyse. Un outil a toujours une plage où
il est honnête. Connaître la sienne fait partie du travail.)

### Ce que la théorie ne dit pas, et qu'il faut dire quand même

Je viens de décrire une montée propre en « S ». Une vraie attaque d'anche ne
ressemble pas toujours à ça, et prétendre le contraire serait exactement le
genre d'arrangement que ce livre refuse.

Ce qu'on observe en vrai, souvent :

- **la hauteur glisse.** Pendant le transitoire, la fréquence n'est pas
  encore celle du régime établi ; elle monte ou descend vers elle. La note,
  pendant qu'elle naît, **n'a pas encore sa hauteur**.
- **plusieurs régimes se disputent le départ.** Il arrive que le système
  parte sur un mode, hésite, et bascule sur un autre. Une anche qui
  « couaque » fait exactement cela.
- **le bruit domine le tout début.** Aux amplitudes les plus faibles,
  l'oscillation naissante est plus petite que le bruit d'écoulement. On ne
  peut donc pas observer le vrai commencement : on observe le moment où il
  émerge du bruit, ce qui n'est pas la même chose et dépend de la qualité de
  la mesure.

Ce dernier point mérite qu'on s'y arrête. **Il n'y a pas d'instant de
naissance observable.** L'« onset » que rend le code est un seuil
conventionnel, pas un événement physique. Le vrai début est enfoui sous le
bruit, et il l'est nécessairement, parce qu'il commence à amplitude nulle.
On peut raffiner la mesure autant qu'on veut, on ne fera que repousser la
convention.

C'est un fait technique. Je le trouve aussi extraordinairement intéressant.

---

## Résonance intérieure

### Le mot, encore, existe déjà

*Anicca* : l'impermanence. C'est le premier des trois caractères de toute
chose dans la tradition dont ce livre emprunte la seconde ligne, et on le
traduit d'ordinaire par « tout est impermanent », ce qui est vrai et un peu
plat. La formulation opératoire est meilleure : **tout ce qui apparaît a
une durée d'apparition, une durée de séjour, et une durée de
disparition.** Rien ne surgit tout fait.

Or c'est très exactement ce que dit le chapitre, et il le dit avec une
courbe et une constante de temps.

**Premier point : le commencement a une durée, même quand il paraît
instantané.** Nous vivons nos pensées et nos émotions comme si elles
apparaissaient d'un bloc : à un moment il n'y avait rien, et maintenant je
suis en colère. La physique de l'attaque dit qu'un système non linéaire ne
peut pas faire ça. Il y a nécessairement une croissance exponentielle, avec
un taux $\sigma$, et donc un intervalle pendant lequel la chose est déjà là
mais encore petite. Si on ne l'a pas vue, ce n'est pas qu'elle n'y était
pas : c'est qu'elle était sous le seuil de détection. Toute la pratique de
l'observation fine consiste à baisser ce seuil.

**Deuxième point, et c'est le plus utile : plus c'est délicat, plus c'est
lent.** Le ralentissement critique dit que près du seuil, $\tau$ diverge. Ce
qui naît tout juste met un temps déraisonnable à s'établir. La tentation,
devant quelque chose qui met si longtemps à venir, est de conclure qu'il ne
vient pas. C'est le contresens exact. La lenteur **est** la proximité du
seuil. Une chose qui s'installe très vite est une chose qui était déjà loin
au-dessus.

**Troisième point : pendant la naissance, ce n'est pas encore ce que ce
sera.** La hauteur glisse. Le système peut partir sur un mode et basculer
sur un autre. L'identité de la note n'est pas donnée au départ, elle est un
**résultat**. Je ne tire aucune métaphysique de là, mais je note que c'est
une description assez précise de ce qu'on voit quand on regarde une émotion
se former : au début ce n'est pas encore de la colère, c'est une chaleur
sans nom qui deviendra de la colère si on la laisse s'établir. Et qu'à ce
moment-là, le système est encore en train de choisir.

**Quatrième point, qui est le plus dur : il n'y a pas d'instant de
naissance.** On ne peut pas dire *quand* la note a commencé. Le début est
sous le bruit, par construction, et tout « onset » est une convention. Je
trouve cela vertigineux et curieusement apaisant. La question « à quel
moment exact est-ce que ça a commencé ? » — qu'on se pose à propos d'une
douleur, d'une rupture, d'une maladie, d'un amour — n'a peut-être pas de
réponse parce qu'elle n'a pas d'objet. Il n'y a pas d'instant. Il y a un
taux de croissance, et un seuil à partir duquel on s'en aperçoit.

Là encore, je m'arrête. La physique ne démontre rien de tout cela. Elle
fournit une **forme** — ici : croissance exponentielle, saturation cubique,
constante de temps qui diverge au seuil, pas d'origine observable — assez
nette pour qu'on la reconnaisse ailleurs, et assez honnête pour qu'on sache
où elle cesse de valoir.

---

⟢ **ton expérience** — un commencement observé de l'intérieur, pendant
qu'il avait lieu et non après coup. Combien de temps a-t-il duré, et à quel
moment as-tu su ce que c'était ?

---

*Nous savons maintenant comment ça naît. La Partie IV demande : comment
regarde-t-on une chose en train de bouger sans la saisir ?*
