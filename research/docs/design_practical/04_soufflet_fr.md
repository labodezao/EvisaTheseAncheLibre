# Soufflet

## Le poumon de l'instrument

Tout ce qui est en amont de l'anche est dans le soufflet : la pression, sa montée, sa chute, son changement de sens. Un soufflet à cadres, ce sont des plis de carton et de toile, de la peau aux coins, et un cadre en bois à chaque bout qui reçoit les deux moitiés de la caisse. Sur les instruments des stages, il est acheté tout fait ; le stagiaire colle ses cadres, perce et pose les pions, et le contrôle seul avant de le monter. Ce chapitre pose trois questions qu'un facteur rencontre avant tous ces gestes : quelle sorte de source d'air est un soufflet, quelle taille doit-il avoir, et où fuit-il.

### Une source de débit, tenue par un bras

Que règle vraiment le bras, la pression ou le débit ? Chaque musicien a la réponse dans les mains. Gardez le soufflet à vitesse constante et ouvrez un accord : la pression baisse, parce que le même débit se partage maintenant entre plus d'anches. Une source de pression, comme le grand réservoir lesté d'un orgue, tiendrait la pression et enverrait deux fois le débit dans deux anches. Un soufflet se comporte plutôt comme une source de débit, et la vérité est entre les deux idéaux : une vraie source donne moins de débit quand la pression monte. La loi la plus simple est une droite,

$$q = q_0 - p/R$$

où $q_0$ est le débit à pression nulle et $R$ la résistance interne de la source. La thèse montre ce que $R$ fait à l'anche : il change l'amplitude de la note et déplace son seuil. Ici il compte pour une raison plus simple. Un bourdon, un accord, une seconde voix, tous puisent à la même source, et la pression que reçoit chaque note dépend de ce que prennent les autres.

Le bras lui-même est l'autre moitié de la source. Une force $F$ sur un soufflet de surface efficace $S$ fait une pression

$$p = F/S$$

et une course de longueur $c$ balaie un volume $S\,c$. La surface efficace n'est pas la surface du cadre : les plis cèdent un peu sous la pression, et la force se répartit sur moins que toute la section. Elle se mesure, elle ne se calcule pas, par le test de chute de la partie fuites : une masse connue $m$ sur le soufflet, la pression lue au tube en U, et $S = mg/p$.

### Quelle taille de soufflet

Ewen a répondu à la question de la taille du soufflet en une phrase : une section minimale selon le nombre de voix ; trop petit, pas assez d'air ; trop grand, plus assez de pression ; un optimum, peut-être à calculer. Voici le calcul, et il est court.

Trop grand d'abord. Le bras a une force qu'il donne sans peine le temps d'une phrase, $F$. Pour atteindre la pression $p$ dont les anches ont besoin pour un forte, la surface ne doit pas dépasser

$$S_{\max} = F/p.$$

Trop petit ensuite. Une phrase dure un temps $t$ entre deux changements de sens ; les anches qui sonnent pendant ce temps consomment un débit $Q$, plus la fuite ; une course de longueur $c$ doit tout contenir :

$$S_{\min} = Q\,t/c.$$

Entre les deux, la fenêtre, que la figure @fig:fr-soufflet-fenetre dessine avec des chiffres ronds choisis seulement pour rendre l'arithmétique visible : un bras de 40 N, une course de 0,4 m, une phrase de 4 s, et un accord forte de neuf anches (trois notes de trois voix) à 10 L/min chacune. À 1000 Pa, la fenêtre va de 150 à 400 cm². À 2000 Pa, elle se resserre à 150 à 200 cm². Au-dessus d'environ 2700 Pa, elle se ferme : un soufflet assez grand pour tenir l'accord quatre secondes ne peut plus être poussé à cette pression par ce bras. L'optimum qu'Ewen devinait est réel, et c'est le point où les deux limites se rejoignent.

![La fenêtre de section d'un soufflet, avec des chiffres ronds d'exemple à remplacer par des mesures (outils_atelier.py soufflet). Au-dessus de $F/p$, le bras ne fait plus la pression ; au-dessous de $Qt/c$, l'air manque avant la fin de la phrase. Pour un pianissimo de deux anches (tirets), la limite d'air est négligeable ; c'est le forte qui ferme la fenêtre.](figures/pratique_soufflet_fr.png){#fig:fr-soufflet-fenetre}

Deux leçons tiennent quels que soient les vrais chiffres. Au pianissimo, deux anches à 2 L/min ne demandent qu'une section de 7 cm² : le côté air ne contraint jamais, et la section est fixée par le forte. Et le nombre de voix entre directement dans le minimum, ce qui est la règle d'Ewen écrite en algèbre : une troisième voix, c'est un tiers d'air en plus pour la même phrase, et un soufflet taillé pour deux voix s'épuise plus tôt avec trois. Mais aucune des entrées de la figure @fig:fr-soufflet-fenetre n'a été mesurée. Le débit d'une anche au forte est la moins connue : les modèles de réseau de la thèse donnent 6 à 24 L/min par languette à 1000 Pa et sont connus pour être trop généreux.

> À compléter (Ewen) : les cinq nombres de la fenêtre, sur un de tes instruments. La force de ton bras pour un forte tenu, avec un peson de bagage accroché à la courroie ; la course utile du soufflet ; la durée d'une phrase typique entre deux changements de sens ; le débit d'une anche au mezzo-forte et au forte, par la descente du gazomètre ruban retiré ; et la surface efficace du soufflet par le test de chute. Ensuite outils_atelier.py soufflet dessine la vraie fenêtre.

### Où fuit un soufflet

L'atelier le sait : aux coins et aux cadres. La physique ajoute pourquoi les cadres sont si exigeants. Un cadre est un joint plat, et un long : environ un mètre de tour pour un petit instrument. Par la loi du cube de la partie fuites, un joint de cadre de 1000 mm de long, 10 mm de portée et un jeu de 0,05 mm, l'épaisseur d'un cheveu, fuit à lui seul 1,7 L/min à 500 Pa, plus que tout le budget du soufflet (moins de 1 L/min, tableau @tab:fr-budget). À 0,02 mm il fuit 0,11 L/min ; à 0,1 mm, 14 L/min. Aucune paire de cadres en bois n'est plane à deux centièmes de millimètre sur un mètre après une saison d'humidité, et c'est pourquoi le cadre a besoin de son joint : le joint ne ferme pas le jeu, il le remplit.

Les coins sont l'autre point faible : de la peau pliée et collée à l'endroit où le carton plie le plus, et où il s'use en premier. Un trou là est un trou, pas un joint, et le tableau @tab:fr-fuite-trou dit ce qu'il pèse : un millimètre, c'est presque un litre par minute.

## Faire et contrôler le soufflet

**Cadres collés, trous percés, pions posés.** Le soufflet doit entrer sur la caisse sans forcer et sans jour. Un cadre qu'il faut forcer revient en ressort et ouvre son joint ; un cadre qui laisse passer la lumière est déjà une fuite de la taille de la figure @fig:fr-joint.

**Le soufflet seul, entre deux planches.** Le fermer entre deux planches à joint, accrocher une masse connue, filmer la descente avec une règle à côté, et passer la fumée d'encens le long des coins. Chiffre proposé : moins de 1 L/min à 500 Pa. La même mesure donne la surface efficace du soufflet, $mg/p$, dont la fenêtre ci-dessus a besoin.

> À compléter (Ewen) : le soufflet est acheté, avec deux mois de délai. Que contrôles-tu à l'arrivée, et qu'est-ce qui te fait en renvoyer un ?

## À l'établi du réparateur

**L'instrument fatigue le musicien, le test de chute est court.** Fermer le soufflet seul entre deux planches : si la fuite reste, elle est dans le soufflet ; si elle part, elle est dans les caisses ou les cadres. Puis la fumée, coin par coin.

**Des trous d'épingle dans les plis.** Une petite lampe posée dans le soufflet, dans une pièce noire, montre chaque trou d'épingle comme un point de lumière ; un coin usé se voit comme une lueur.

**Une fuite à un cadre.** Regarder d'abord le joint : écrasé, durci ou déchiré, il ne remplit plus le jeu, et la loi du cube dit que quelques centièmes de millimètre suffisent à perdre le budget. Le remplacer avant de toucher au bois.

**Un soufflet devenu mou, ou raide.** Un carton qui a perdu son ressort, ou une colle durcie aux plis. Cela change le toucher plus que l'air, et sa mesure est la surface efficace : comparer $mg/p$ avec celle d'un soufflet que le musicien aime.

> À compléter (Ewen) : les réparations de soufflet que tu fais toi-même et celles que tu envoies ailleurs, et le temps de chacune.
