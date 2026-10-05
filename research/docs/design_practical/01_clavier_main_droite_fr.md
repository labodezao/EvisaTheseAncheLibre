# Clavier main droite

## Un levier, un ressort et une porte

Sortez une touche de main droite d'un instrument et regardez-la. C'est un levier qui tourne sur un axe commun à toutes les autres. À un bout, un bouton que le doigt enfonce. À l'autre, une soupape, une petite planchette garnie de peau, couchée sur un trou de la table d'harmonie. Entre les deux, un ressort qui tient la soupape fermée quand personne ne joue. C'est tout. Trois pièces et un axe, répétés trente-trois fois sur les instruments des stages, et presque tout ce que le musicien sent sous la main droite vient de la façon dont ces trois pièces se partagent un seul travail : tenir une porte fermée contre le vent, et l'ouvrir aussitôt qu'on le demande.

À l'atelier d'Ewen, les touches sont découpées à la fraiseuse numérique et les leviers sont pliés et percés à la main : c'est la plus longue tâche de tout l'instrument (douze heures pour une main droite dans les gammes de 2026, une estimation). Le stagiaire les enfile sur l'axe dans l'ordre, graisse l'axe, ajoute des entretoises où il faut, règle chaque ressort à 90 grammes sur un gabarit, colle les soupapes avec leur gabarit et les contrôle à la lampe, puis met les boutons d'une rangée à la même hauteur avec un réglet. Chacun de ces gestes a une raison dans la physique, et ce chapitre la donne.

### La porte contre le vent

Une soupape fermée sur son trou porte la pression du soufflet sur toute sa surface : une force $\Delta p\,A$. Sur un accordéon, la soupape est posée sur la face extérieure de la table d'harmonie, si bien que les deux sens du soufflet font des choses opposées. Au poussé, l'air de dedans est au-dessus de l'atmosphère et il soulève la soupape : le ressort doit la tenir. Au tiré, l'air du dehors plaque la soupape sur sa portée : le doigt paie cette force en ouvrant la note. Le chapitre sur la mécanique main gauche suit ce second fardeau en détail ; la main droite rencontre les deux mêmes, seulement plus petits, parce que ses trous sont plus petits.

Quelle force doit avoir le ressort ? Assez pour qu'aucune soupape ne se soulève au plus fort poussé. Le critère d'atelier, une proposition encore à étalonner sur de vrais instruments, est qu'aucune soupape ne décolle sous 1,5 fois la pression de jeu la plus forte. Avec une pression de jeu de 3 kPa au plus, la force à la soupape doit valoir

$$F \ge 1{,}5\,p_{\max}\,A = 4500\,\mathrm{Pa}\times A$$

ce qui, dit dans les unités de l'établi, est une règle à retenir : environ un demi-gramme à la soupape par millimètre carré de trou (0,46 g par mm² exactement, pour 3 kPa). Le tableau @tab:fr-ressort la donne pour les trois trous d'Ewen.

Table: Les trois trous de soupape des instruments d'Ewen : levée utile, pression à laquelle décolle une soupape tenue par 90 g, et force qui la tient jusqu'à 1,5 fois 3 kPa (force à la soupape ; outils_atelier.py ressort et levee). {#tab:fr-ressort}
| trou (mm) | aire (mm²) | levée utile A/P (mm) | 90 g décollent à (Pa) | force pour 4,5 kPa (g) |
|---|---|---|---|---|
| 8 × 12 | 96 | 2,4 | 9 200 | 44 |
| 15 × 15 | 225 | 3,75 | 3 900 | 103 |
| 20 × 15 | 300 | 4,3 | 2 900 | 138 |

Le tableau cache une petite surprise. Les 90 grammes de l'atelier n'ont jamais été calculés ; la main les a trouvés, comme la force qui donne un bouton agréable, et ils sont les mêmes pour toutes les touches. L'air ne voit pas les choses ainsi. Sur le petit trou, 8 sur 12 mm, 90 g tiennent la soupape fermée jusqu'à 9,2 kPa, deux fois ce que demande le critère : là, c'est le doigt qui règle le ressort, pas le vent. Sur le trou de 15 sur 15 mm, les mêmes 90 g tiennent jusqu'à 3,9 kPa, un peu en dessous des 4,5 kPa du critère. Sur le trou de 20 sur 15 mm, ils ne tiennent que jusqu'à 2,9 kPa, sous la plus forte pression de jeu elle-même. Une seule force pour tous les trous est trop pour les petits ou trop peu pour les grands ; la physique demande un ressort qui suit le trou, environ un demi-gramme par millimètre carré. Le livret du stage connaît déjà la conséquence : un ressort réglé plus faible que les autres donne un bouton mou, et sa soupape peut se soulever au fortissimo. Une note qui sonne faiblement toute seule quand on pousse fort, c'est très souvent cela.

Au tiré, le trou coûte au doigt $\Delta p\,A$ au moment d'ouvrir, en plus du ressort : à 2 et 3 kPa, 20 et 29 g pour le trou de 8 sur 12 mm, 46 et 69 g pour le 15 sur 15, 61 et 92 g pour le 20 sur 15. Un bouton de 90 g au poussé devient un bouton de 110 à 180 g tout au début d'un tiré fort, et la marche disparaît dès que la soupape a décollé et que la pression est passée dans l'anche. Les musiciens le sentent, et savent rarement pourquoi.

> À compléter (Ewen) : où exactement se lisent les 90 g sur le gabarit, au bouton ou à la soupape, et les deux bras du levier de main droite (axe-bouton, axe-soupape). Si les bras sont inégaux, la force à la soupape est la force au bouton multipliée par leur rapport, et le tableau @tab:fr-ressort se lit avec. Et lequel des trois trous va où (main droite, basses, accords), modèle par modèle. Si les soupapes de 20 sur 15 mm sont tenues par un ressort de 90 g à bras égaux, chuchotent-elles sur un poussé fort ?

### De combien lever

De combien la soupape doit-elle monter ? Moins qu'on ne croit. L'air ne traverse pas la soupape ; il sort par les côtés, par la fente mince qui s'ouvre entre le bord du trou et la peau. Cette fente fait tout le tour du trou, comme un rideau pendu à la soupape : sa hauteur est la levée $h$, sa longueur est le périmètre $P$ du trou, et son aire vaut $P\,h$. Tant que le rideau est plus petit que le trou, c'est lui qui étrangle l'air, et lever davantage aide. Quand le rideau égale le trou, à

$$h = A/P$$

le trou lui-même devient le passage le plus étroit, et lever plus ne donne plus d'air (@fig:fr-levee). Pour le trou de 8 sur 12 mm, $A$ = 96 mm² et $P$ = 40 mm : 2,4 mm. Pour 15 sur 15 mm, 3,75 mm ; pour 20 sur 15 mm, 4,3 mm. Pour un trou rond de diamètre $d$, c'est simplement $d/4$. Le modèle de la thèse supposait 4 mm pour toutes les soupapes : deux tiers de plus que ce dont le petit trou a besoin.

![La levée utile d'une soupape. (a) L'air sort par le rideau qui fait le tour du trou, périmètre fois levée. (b) Le passage d'air est le plus petit du rideau et du trou ; il cesse de croître à la levée utile A/P : 2,4 mm pour le trou de 8 sur 12 mm, 3,75 mm pour 15 sur 15 mm, 4,3 mm pour 20 sur 15 mm.](figures/pratique_levee_fr.png){#fig:fr-levee}

Chaque millimètre au-dessus de la levée utile est une course de bouton payée pour rien : un trajet plus long du doigt, une répétition plus lente, et sur un levier court plus d'angle et plus de frottement. Un peu de marge reste sage, 10 à 20 %, parce que la peau est molle et que le rideau n'est pas une fente parfaite. Une règle de conception en sort : dessiner le trou d'abord, calculer $A/P$, ajouter un cinquième, et c'est la levée ; la course du bouton est la levée multipliée par le rapport des bras.

### Ce que fait la vitesse de la touche

Une touche n'est pas seulement ouverte ou fermée ; elle s'ouvre en un temps, et la note répond à ce temps. Les simulations de la thèse font monter la pression sous l'anche en ligne droite en 20 ms, une hypothèse sans mesure derrière. Une touche lente donne à la languette une montée lente et une attaque douce, une touche rapide une marche. Le temps de réponse de la note, de l'ouverture au son établi, est déjà mesuré par la chaîne d'analyse du banc de recherche ; ce qui manque, c'est la position de la touche en fonction du temps à côté.

Il y a un point plus fin, et c'est une prédiction du réseau à deux anches de la thèse. La masse d'air du chemin au-dessus de la languette, trou et soupape ensemble, participe au démarrage de la note : avec cette masse divisée par dix la languette ne démarre pas, multipliée par trois elle démarre moins bien, et entre les deux il y a un optimum. Une soupape à peine ouverte est un passage long et mince, une grosse masse d'air ; une soupape grande ouverte, une petite. Si la prédiction tient, la profondeur à laquelle le musicien enfonce la touche change la facilité du démarrage, et pas seulement la nuance. L'expérience E2 de la thèse est faite pour le voir : la pression de démarrage d'une languette, lue au tube en U, pour cinq levées de sa soupape réglées avec des cales.

> À compléter (Ewen) : la force et la course d'une touche en fonction du temps, avec un petit capteur de force et un capteur d'angle magnétique au banc ; et l'expérience E2. Y a-t-il une levée optimale pour le démarrage, comme le dit le modèle, et où tombe-t-elle par rapport à $A/P$ ?

### Deux touches qui en font plus

Deux dispositifs d'Ewen demandent davantage à une touche, et la physique ci-dessus dit ce que chacun coûte.

Le premier tient une note ouverte comme le bouton d'un stylo à bille tient sa pointe sortie : un appui pour enclencher, un pour relâcher, pour qu'un bourdon continue de sonner pendant que les doigts sont libres. Une soupape enclenchée est une ouverture constante, et la languette derrière elle ne dépend plus que d'une chose, la pression du soufflet, qu'elle partage avec toutes les autres notes jouées. Le soufflet se comporte plutôt comme une source de débit avec une résistance interne que comme une source de pression (la partie soufflet de ce livre y revient) : à vitesse de soufflet constante, ouvrir une note de plus fait baisser la pression. Un bourdon coûte donc de la pression à la mélodie, son propre débit multiplié par la résistance de la source. Et une note enclenchée sur une plaque à deux languettes fait sonner l'une au poussé et l'autre au tiré ; sur l'instrument d'Ewen, l'accordeur a trouvé 15 à 25 cents entre poussé et tiré sur les mêmes notes. Un bourdon qui doit rester juste à travers le changement de sens demande que les deux languettes de sa plaque soient accordées ensemble plus soigneusement que la mélodie.

Le second est une touche à course prolongée : enfoncée au-delà du fond de sa course ordinaire, elle fait plier la note. Sur quoi peut agir cette course en plus ? Pas sur la pression, qui appartient au bras. Elle peut refermer en partie la soupape, ou ouvrir un second petit passage, ce qui change la masse d'air au-dessus de la languette ; l'effet sur la hauteur n'est pas connu et pourrait être sous ce que l'oreille remarque. Ou elle peut ouvrir une cellule à côté de la chambre et changer son volume. La thèse montre que la chambre n'est un levier fort que si sa résonance est proche de la note, à un rapport d'environ 1,1, et qu'une telle chambre est dure à faire parler (1322 Pa de seuil contre 208 Pa à un rapport de 1,3, pour la même lame, dans le modèle). Un bend en fin de course est donc un compromis entre la profondeur du bend et la facilité de la note.

> À compléter (Ewen) : les deux mécanismes tels que tu les vois, et une mesure avant de construire le second : réduire le volume d'une chambre à la pâte à modeler en deux ou trois pas, et lire la hauteur de sa languette à l'accordeur à pression fixe. Si la hauteur bouge de moins de quelques cents, la chambre n'est pas le levier pour cette note, et c'est la soupape qu'il faut essayer.

## Construire et régler la main droite

Chaque pas de la gamme a sa raison. Les voici dans l'ordre du stage, la raison à côté du geste.

**Les ressorts à 90 g, sur le gabarit.** Le gabarit met chaque levier dans la même position, pour que les 90 g veuillent dire la même précharge pour tous. Le ressort décide de deux choses à la fois, le toucher du bouton et la pression à laquelle la soupape décolle (tableau @tab:fr-ressort) ; un ressort réglé « à peu près » donne un bouton plus mou que ses voisins et une soupape qui peut chuchoter au fortissimo. Contrôle : chaque ressort fait 90 g sur le gabarit.

**Les touches sur l'axe, graissé, avec des entretoises où il faut.** Une touche doit tourner librement et ne pas glisser de côté. Tourner librement garde le bouton léger et le retour sûr ; un flottement latéral fait poser la soupape décentrée sur son trou. La graisse change un frottement sec en frottement lubrifié, et un levier qui tourne sur un axe perd bien moins au frottement qu'une tige qui coulisse dans un guide (le chapitre main gauche chiffre cette différence). Contrôle : chaque touche tourne librement, sans jeu sur le côté.

> À compléter (Ewen) : ta gamme demande « entretoises de 6,33 ou 5,833 mm si nécessaire : quand est-ce nécessaire ? » Qu'est-ce qui te dit qu'il faut une entretoise, et laquelle choisis-tu ?

**Les soupapes avec leur gabarit, collées côté peau, contrôlées à la lampe.** Une soupape décentrée laisse un croissant du trou découvert : une fuite à chaque note, et le trou vu contre la lampe la montre tout de suite. La mousse silicone sous les soupapes les rend silencieuses quand elles retombent. Contrôle : chaque soupape est centrée et ferme sans jour.

**Les boutons d'une rangée à la même hauteur, une course régulière, rien qui frotte.** La hauteur d'un bouton est le départ de sa course ; une rangée de boutons à la même hauteur est une rangée de notes qui s'ouvrent à la même profondeur du doigt. Contrôle au réglet posé le long de la rangée, puis appuyer sur chaque bouton en écoutant.

## À l'établi du réparateur

Ce qu'apporte le musicien, ce que cela veut dire le plus souvent, et comment le vérifier.

**Une note qui sonne toute seule, faiblement, quand on pousse fort.** Sa soupape décolle sous la pression de jeu : un ressort plus faible que la règle du tableau @tab:fr-ressort, une peau tassée ou durcie, ou une soupape qui ne porte plus à plat. Contrôle : le ressort au gramme-mètre contre ses voisins ; la soupape à la lampe. Une soupape qui laisse passer la lumière fuit à toute pression ; une soupape sombre mais qui se soulève au poussé a un ressort faible.

**Un bouton lourd au début du tiré, léger au poussé.** C'est la physique de la porte, pas un défaut : la pression plaque la soupape au tiré. Cela ne devient un défaut que si un bouton est bien plus lourd que ses voisins pour le même trou, ce qui désigne un frottement sur l'axe ou un levier qui touche son voisin.

**Un bouton qui reste enfoncé, ou qui revient lentement.** Un frottement (axe sec, bois gonflé, levier qui frotte sur le voisin ou sur la grille) ou un ressort décroché. Contrôle : la touche seule, ressort ôté, doit retomber par son propre poids quand on retourne l'instrument ; si elle ne le fait pas, le coupable est le frottement, pas le ressort.

**Des boutons inégaux, ou une touche qui claque.** Des hauteurs perdues par une butée déplacée ou un feutre écrasé ; un claquement est un atterrissage sans mousse ni feutre. Contrôle au réglet, et remplacer le feutre ou la mousse.

> À compléter (Ewen) : ta propre liste de ce que les musiciens apportent pour la main droite, de la plus fréquente à la plus rare, pour que cette liste suive le vrai établi et non la théorie.
