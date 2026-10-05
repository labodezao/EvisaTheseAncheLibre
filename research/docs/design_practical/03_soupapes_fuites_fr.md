# Soupapes et fuites

## L'air qui ne chante pas

Une fuite, c'est de l'air qui s'échappe sans faire de musique. Elle est invisible et presque silencieuse, et pourtant le musicien la reconnaît tout de suite sans savoir la nommer : l'instrument fatigue, les notes douces partent mal, l'attaque est molle, et parfois une note sonne faiblement sans que personne ne l'ait jouée. Ce chapitre demande ce qu'est une fuite, physiquement, pourquoi elle fait exactement ces choses-là et pas d'autres, à partir de quelle taille elle compte, et comment la trouver avec presque rien.

### Pourquoi une fuite gâche le jeu

Trois choses sont sûres, deux sont probables.

Chaque fuite mange de l'air. Le soufflet doit bouger davantage pour le même son, il change donc de sens plus souvent et le bras se fatigue plus tôt. C'est de l'arithmétique.

Un instrument étanche peut être mis en pression avant la note. Le musicien serre le soufflet, rien ne bouge, et la pression attend derrière les soupapes fermées ; quand une soupape s'ouvre, l'anche reçoit toute la pression d'un coup et l'attaque est franche. Avec une fuite, la pression retombe dès que le bras cesse de pousser, et à l'attaque elle repart de presque rien : le transitoire est mou.

La physique de l'anche donne la troisième certitude. Une anche démarre à une pression $p_{\mathrm{on}}$ mais, une fois partie, tient jusqu'à une pression plus basse $p_{\mathrm{off}}$ : c'est l'hystérésis étudiée dans la thèse. Le pianissimo le plus doux s'obtient en attaquant juste au-dessus de $p_{\mathrm{on}}$. Si la pression à l'attaque est incertaine, parce que l'air fuit, l'anche ne part pas ou part trop fort. Une fuite se sent d'abord au seuil, là où le musicien demande le plus de précision.

Deux choses encore sont probables. Une fuite proche d'une anche, dans la cire autour de sa plaque ou sous une valve qui ne ferme pas, est en parallèle de l'anche, derrière la soupape et le canal : elle fait baisser la pression que l'anche voit vraiment. Et une soupape ou une valve qui fuit alimente une chambre qui devrait se taire ; si une anche de cette chambre est proche de son seuil, elle sonne faiblement. C'est la note fantôme.

### Deux lois pour une fuite

Comment l'air passe-t-il par un interstice ? Cela dépend de sa forme, et il n'y a que deux formes à connaître.

La première est le trou : une ouverture courte dans une paroi mince, une fissure dans un coin, un trou d'épingle dans une peau. L'air s'y précipite en jet, et son débit suit la loi de l'orifice,

$$q = C_d\,S\,\sqrt{2\Delta p/\rho}$$

où $S$ est l'aire du trou, $\Delta p$ la différence de pression, $\rho$ la masse volumique de l'air et $C_d \approx 0{,}6$ la contraction du jet. Le débit croît avec l'aire, donc avec le carré du diamètre, et seulement avec la racine de la pression. Le tableau @tab:fr-fuite-trou en donne quelques valeurs, et donne l'habitude de ce livre : une fuite se dit en litres par minute à 500 Pa, environ 5 cm d'eau, un mezzo-forte, et se figure par le trou rond qui fuirait autant.

Table: Fuite d'un trou rond, loi de l'orifice avec $C_d$ = 0,6 (outils_atelier.py trou). {#tab:fr-fuite-trou}
| diamètre du trou (mm) | à 100 Pa (L/min) | à 500 Pa (L/min) | à 1500 Pa (L/min) |
|---|---|---|---|
| 0,3 | 0,03 | 0,07 | 0,13 |
| 0,5 | 0,09 | 0,20 | 0,35 |
| 1 | 0,37 | 0,82 | 1,4 |
| 2 | 1,5 | 3,3 | 5,7 |

Un trou d'un millimètre laisse déjà passer presque un litre par minute.

La seconde forme est le joint plat : deux surfaces qui devraient se toucher et ne se touchent pas tout à fait, une plaque sur sa cire, un sommier sur son joint, un cadre sur un cadre, une tirette de registre sur son lit. Ici l'air ne jaillit pas ; il se faufile dans une fente bien plus mince que longue, et c'est la viscosité qui commande. Entre deux faces planes écartées de $h$, sur une longueur de joint $w$ et à travers une portée de largeur $L$, le débit suit la loi de Poiseuille,

$$q = \frac{w\,h^{3}\,\Delta p}{12\,\mu\,L}$$

avec $\mu$ la viscosité de l'air. Deux traits font de cette loi la plus utile de tout le livre. Le débit est proportionnel à la pression, pas à sa racine, si bien qu'on distingue un joint d'un trou en mesurant à deux pressions : une fuite qui double quand la pression double est un joint ; une fuite qui ne croît que de 1,4 fois est un trou. Et le débit croît comme le cube du jeu. Divisez le jeu par deux, la fuite est divisée par huit. Un joint n'est pas un peu pire quand il est un peu ouvert ; il est énormément pire.

![Fuite d'un joint plat de 100 mm de tour et 5 mm de portée, à 500 Pa, en fonction de son jeu (loi de Poiseuille). Les points marquent le jeu qui donne chaque chiffre d'atelier proposé. Doubler le jeu multiplie la fuite par huit.](figures/pratique_joint_fr.png){#fig:fr-joint}

La figure @fig:fr-joint chiffre cela pour un joint de la taille d'une plaque ou d'un petit sommier : 100 mm de tour, 5 mm de bois à traverser. Pour rester sous 0,05 L/min, le jeu doit être sous 0,026 mm, l'épaisseur d'une feuille de papier fin. À 0,05 mm, l'épaisseur d'un cheveu, le même joint fuit 0,35 L/min, sept fois l'objectif. Voilà pourquoi un sommier doit être plan et une plaque bien assise, et pourquoi la cire marche : elle comble un jeu qu'aucun rabot ne fermerait. La loi tient tant que l'écoulement dans la fente reste lent et ordonné, ce que outils_atelier.py vérifie par le nombre de Reynolds : moins de 4 jusqu'à un jeu de 0,05 mm, environ 30 à 0,1 mm. L'écoulement reste laminaire sur toute la figure ; ce n'est qu'aux plus grands jeux que les pertes à l'entrée de la fente, que la loi ignore, commencent à compter, et là la loi surestime un peu la fuite.

> À compléter (Ewen) : deux ou trois vrais joints mesurés à 250 et 500 Pa (une plaque, un sommier, un cadre), pour voir s'ils se comportent en joints (débit doublé) ou en trous (débit fois 1,4). Le protocole du chapitre suivant le fait avec le même gazomètre.

### À partir de quelle taille

Les chiffres d'atelier, tirés du livret du stage, sont des propositions, pas encore mesurées sur les instruments d'Ewen. Le tableau @tab:fr-budget les donne avec ce statut, étape par étape, dans l'ordre où l'instrument se construit.

Table: Chiffres de fuite proposés à 500 Pa, par étape de fabrication (livret du stage ; à étalonner). {#tab:fr-budget}
| étape | pièce testée | chiffre proposé |
|---|---|---|
| table d'harmonie | chaque soupape, à la cloche | moins de 0,02 L/min ; aucune soupape ne décolle sous 1,5 fois la plus forte pression de jeu |
| soufflet | le soufflet seul, entre deux planches | moins de 1 L/min |
| sommier | collé, nu, puis garni de ses plaques (fentes au ruban) | moins de 0,05 L/min |
| caisse | caisse fermée avec mécanique et tirettes de registres | moins de 0,5 L/min |
| instrument complet | test de chute, poussé et tiré | temps à fixer par Ewen |

D'où viennent ces chiffres, et que devrait valoir le dernier ? Ici un peu d'arithmétique vaut mieux qu'une tradition. Une anche aiguë jouée pianissimo consomme probablement de l'ordre de 1 à 2 L/min (une ouverture efficace de 1 à 3 mm² sous 100 Pa ; à mesurer, le chapitre suivant dit comment). Le test de chute que l'atelier trouve bon, un soufflet de 10 litres qui met une minute à tomber, est une fuite de 10 L/min : plus que l'anche elle-même. Un tel instrument joue, mais son pianissimo part dans la fuite. Deux niveaux en sortent, à confirmer sur deux ou trois instruments qu'Ewen connaît, un qu'il trouve excellent et un médiocre : un niveau atelier, sous environ 10 L/min (les 10 litres tombent en plus d'une minute), et un niveau pianissimo, sous 2 à 3 L/min (la chute prend trois à cinq minutes).

> À compléter (Ewen) : le temps de chute et le pianissimo le plus doux d'une note aiguë, sur un instrument que tu trouves excellent et un que tu trouves médiocre. Le seuil de l'instrument complet est entre les deux.

## Mesurer une fuite avec presque rien

### Les outils du banc

Quatre outils font presque tout, et trois ne coûtent rien.

**Le tube en U.** Un tuyau transparent plié en U, à moitié rempli d'eau avec une goutte de liquide vaisselle, sur une planchette avec une règle. L'écart des deux niveaux, en millimètres, fois 9,81, donne la pression en pascals ; en gros, 1 mm fait 10 Pa. C'est la référence contre laquelle on vérifie tous les autres capteurs.

**Le gazomètre de cuisine.** Une boîte en plastique retournée qui flotte dans un seau d'eau, guidée par deux tiges et lestée. Son poids fixe la pression, $p = mg/S$ : pour une boîte de 150 cm² et 500 Pa, environ 0,77 kg, boîte comprise. Un tuyau passe sous l'eau et relie l'air de la boîte à la pièce testée. Si la pièce fuit, la boîte descend, et le débit est la surface multipliée par la vitesse de descente : avec 150 cm², 1 L/min fait 6,7 cm par minute, et 0,1 L/min fait 6,7 mm par minute. Il donne une pression constante et un débit absolu, sans aucune électronique.

**La cloche.** Un petit pot d'environ 0,4 L au bord garni de mousse, posé côté extérieur sur une soupape fermée pendant que l'instrument est sous pression dedans. La fuite remplit la cloche et sa pression monte ; un tuyau la mène au tube en U. Pour une fuite de type orifice, le temps pour atteindre la moitié de la pression vaut environ $0{,}59\,V\,P/(p_{\mathrm{atm}}\,Q)$ : avec 0,4 L et 500 Pa, 3,5 s pour 0,02 L/min et 35 s pour 0,002 L/min. Une soupape qui amène la cloche à mi-pression en moins de 3 s fuit plus que l'objectif. Une soupape à la fois, sans rien démonter.

**La chute de pression.** On ferme la pièce avec un volume tampon connu, une bouteille de 1,5 L par exemple, on gonfle vers 600 Pa, on ferme, et on enregistre la pression qui tombe (commande LEAKTEST du banc, analyse par banc_recherche/leak.py). Le tampon est nécessaire parce que l'air d'un petit volume est un ressort très raide : une petite pièce se vide en une fraction de seconde. Une règle simple : avec une bouteille de 1,5 L, si la pression met plus de 2 s pour passer de 500 à 400 Pa, la pièce fuit moins de 0,05 L/min, à 30 % près ; à vérifier sur une fuite étalon. Pour un instrument entier, la chute est bien trop rapide, et c'est le gazomètre, ou le soufflet lui-même, qui prend le relais.

Avant de croire l'un d'eux, on teste le banc lui-même : une plaque d'obturation posée sur une vitre ne doit pas fuir ; puis le banc doit lire juste les fuites étalons d'une plaque percée de trous de 0,3, 0,5 et 1 mm, dont les débits sont au tableau @tab:fr-fuite-trou.

Deux règles de sécurité vont avec tout test de fuite : jamais de flamme pour chercher une fuite (celluloïd, bois, colle et peau brûlent), et pas d'eau savonneuse sur le bois, la peau ou le carton ; le savon seulement sur le métal, le plastique et le caoutchouc.

### L'ordre des contrôles

Une fuite se trouve bien plus facilement sur une pièce seule que dans l'instrument fini. Les contrôles suivent donc la fabrication, chacun sur une pièce encore ouverte à l'œil : le banc d'abord, puis le sommier collé nu, le sommier garni de ses plaques avec leurs fentes au ruban (dans les deux sens, pression et aspiration), puis le débit de chaque anche, ruban retiré (une mesure, pas un examen : l'air que consomme cette anche à 100, 300 et 500 Pa), puis la table d'harmonie avec ses soupapes sous la cloche, en montant la pression jusqu'à ce qu'une soupape décolle, puis la caisse fermée, le soufflet seul, et l'instrument complet par le test de chute. Le tableau @tab:fr-budget donne le chiffre proposé de chacun.

### Le test de chute, en chiffres

Le test de chute se fait déjà dans tous les ateliers ; il suffit de le chiffrer. L'instrument est suspendu, une masse connue tire le soufflet, la soupape d'air est fermée et aucune touche n'est enfoncée. On lit la pression au tube en U par la soupape d'air, et l'ouverture du soufflet en fonction du temps avec une règle et la vidéo d'un téléphone. Deux nombres en sortent. La surface efficace du soufflet, $S = mg/p$. Et la fuite, $Q = S \times$ vitesse. Deux masses différentes donnent deux pressions, et disent donc si c'est un joint ou un trou.

Table: Test de chute d'un soufflet qui balaie environ 10 litres sous 600 Pa : fuite et trou équivalent (outils_atelier.py chute). {#tab:fr-chute}
| chute complète en | fuite (L/min) | trou équivalent (mm) |
|---|---|---|
| 30 s | 20 | 4,7 |
| 1 min | 10 | 3,3 |
| 2 min | 5 | 2,4 |
| 5 min | 2 | 1,5 |

Ce que disent les praticiens, dans les guides de réparation et les forums plutôt que dans des études, va avec le tableau @tab:fr-chute : sous 20 à 30 secondes, il y a une fuite franche à chercher ; un bon instrument tient au moins 30 secondes ; un très bon, une minute ou plus. L'arithmétique du chapitre précédent dit qu'une minute est encore une fuite plus grosse qu'une anche au pianissimo.

## Trouver une fuite

Une fois qu'on sait qu'une pièce fuit, où ? Les gestes vont du moins cher au plus malin.

**La fumée.** Un bâton d'encens promené lentement le long des joints, pièce sous pression : la fumée est chassée là où l'air sort. Ou pièce en aspiration : la fumée est aspirée. **Un tuyau à l'oreille**, un stéthoscope de mécanicien fait d'un tuyau, promené à 5 mm des joints avec la pièce à 1500 Pa ou plus : le bruit d'un jet turbulent croît très vite avec sa vitesse, si bien que tripler la pression rend le sifflement 14 à 19 dB plus fort.

**Faire chanter une fuite.** Un jet à travers un petit trou est turbulent et siffle, d'un bruit qui monte haut, jusqu'à l'ultrason, là où la voix des anches et le bruit de la pièce sont faibles. Le sifflement reste noyé dans la pièce. La méthode proposée dans ce travail le fait ressortir en lui donnant un rythme : le soufflet module lentement la pression, en sinus à une fréquence connue de 2 à 10 Hz, et chaque fuite siffle alors plus fort et plus doux à cette fréquence. Un micro bon marché promené sur la surface enregistre ; le programme garde la bande du sifflement, environ 4 à 20 kHz, prend son enveloppe, et ne garde que ce qui bat exactement à la fréquence du soufflet, avec la bonne phase. C'est la détection synchrone, l'amplificateur à verrouillage du laboratoire de physique : tout ce qui ne bat pas à notre rythme est rejeté, et la fuite apparaît sur une carte (banc_recherche/leak.py : lockin, acoustic_leak_strength, leak_map). Deux micros fixes peuvent aussi situer une fuite sans bouger : son sifflement leur arrive avec un petit retard qui dépend de sa position, et la corrélation des deux signaux donne ce retard.

**Rendre une fuite visible.** Deux autres méthodes sont proposées, non construites. La strioscopie sur fond (BOS) filme un fond moucheté imprimé à travers le jet : un air de densité différente dévie un peu la lumière, et un programme qui compare les images révèle le jet invisible, d'autant mieux que l'air est chaud et humide comme un souffle. Ou bien on remplit le soufflet de gaz carbonique et on balaie la surface avec un petit capteur de gaz de quelques euros : la concentration monte aux fuites.

**Laisser chaque anche signer sa fuite.** Une fuite près d'une anche lui vole une part de son air : l'anche démarre plus tard, sonne plus doux, et se désaccorde à sa façon. L'accordeur de ce travail mesure déjà l'écart, le niveau et le temps de réponse de chaque anche ; une fuite locale y laisse sa trace, sans aucun micro promené.

> À compléter (Ewen) : celles de ces méthodes que tu utilises déjà, et les deux que tu voudrais essayer d'abord. Et la surface de la boîte de ton gazomètre.

## À l'établi du réparateur

**Toutes les notes molles à l'attaque, l'instrument fatigant.** Une fuite globale. Chiffrer le test de chute, poussé et tiré ; s'il est sous une minute, fermer l'instrument pièce par pièce (soufflet entre deux planches, puis chaque demi-caisse) et trouver où part l'air avant de chercher l'endroit.

**Une note fantôme au fortissimo.** Soit une soupape qui décolle (la partie main droite donne la force qu'il faut à son ressort), soit la valve de la languette muette qui ne ferme pas. La cloche sur la soupape suspecte répond à la première ; la seconde se trouve par l'anche elle-même : une anche qui sonne faiblement dans le mauvais sens a une valve à remplacer.

**Une note en retard et faible, les autres bien.** Une fuite près de cette anche : la cire autour de sa plaque, sa valve, sa chambre. Fermer la fente de sa languette au ruban et tester le sommier au gazomètre ; une fuite qui disparaît quand on appuie la plaque est une plaque à recirer.

**La cire et les joints.** Un joint qui fuit ne se guérit pas en appuyant plus fort dessus mais en réduisant le jeu : recirer la plaque d'un cordon continu, dresser la face d'un sommier sur un papier abrasif posé sur une vitre, remplacer un joint écrasé. La loi du cube dit pourquoi un jeu divisé par deux est une fuite divisée par huit.

> À compléter (Ewen) : les gestes que tu utilises pour réparer une valve qui fuit, une soupape qui fuit et une plaque qui fuit, avec leurs matériaux, pour que cette liste soit celle de ton établi.
