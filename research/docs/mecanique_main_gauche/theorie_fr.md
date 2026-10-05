## La mécanique main gauche : ce que le doigt paie pour une soupape

Appuyez sur un bouton de basse d'accordéon pendant qu'on tire le soufflet, et le doigt rencontre quelque chose avant le ressort : une petite résistance tout au début, une marche, puis une course plus douce jusqu'en bas. Appuyez sur le même bouton au poussé, et la marche a disparu. Rien n'a changé dans la mécanique entre les deux gestes. Ce qui a changé, c'est l'air, et le doigt est en train de le lire. Ce chapitre remonte cette petite marche jusqu'à sa cause, et de là jusqu'à chaque gramme que le musicien paie au bouton de la main gauche : la soupape, le ressort qui la tient, le levier qui la soulève, la façon dont les pièces glissent ou tournent, et le plastique ou le métal dont elles sont faites.

L'occasion était pratique. Ewen construit la mécanique main gauche du Lib RT, un basses chromatiques à grosses basses, pour un jazzman dont l'instrument actuel demande trop à ses doigts ; le but donné est 80 à 100 grammes au bouton. Quatre versions imprimées ont été faites, la cinquième (v5) joue mais grince, et la question est devenue : l'effort est-il dans la mécanique, ou ailleurs ? La réponse de ce chapitre est qu'il est surtout ailleurs, et qu'on peut le calculer avant de fabriquer quoi que ce soit. Les chiffres viennent d'un petit calculateur écrit pour l'occasion (calcul_mecanique.py, rangé avec le rapport d'ingénierie du Lib RT) ; chacun se recalcule avec les vraies cotes, une fois mesurées.

### Une porte contre le vent

Une soupape est une porte. Elle couvre un trou de la table d'harmonie, côté mécanique, et derrière le trou il y a l'air du soufflet. Porte fermée, l'air pousse dessus, et il ne pousse que là où est le trou : autour, sur la portée, la peau voit la même pression sur ses deux faces. La force est donc la plus simple de la physique, une pression fois une surface,

$$F = \Delta p \, A_{\mathrm{trou}}$$

et pour les grosses basses du Lib RT, un trou de 20 sur 15 mm (300 mm²), elle vaut 0,60 N à 2 kPa de jeu et 0,90 N à 3 kPa de pointe. En grammes, puisque c'est ce que le doigt connaît, 61 et 92 g. Le tableau @tab:fr-force la donne pour les autres trous envisagés.

Table: Force de la pression du soufflet sur une soupape fermée, Δp × A (1 N = 102 g). La levée critique A/P est la levée à laquelle le rideau autour de la soupape égale le trou. {#tab:fr-force}
| trou (mm) | aire (mm²) | levée critique A/P (mm) | 1 kPa | 2 kPa | 3 kPa | 5 kPa |
|---|---|---|---|---|---|---|
| 20 × 15 | 300 | 4,3 | 0,30 N (31 g) | 0,60 N (61 g) | 0,90 N (92 g) | 1,50 N (153 g) |
| 18 × 15 | 270 | 4,1 | 0,27 N | 0,54 N | 0,81 N | 1,35 N |
| 15 × 15 | 225 | 3,8 | 0,23 N | 0,45 N | 0,68 N | 1,12 N |
| 11 × 27 | 297 | 3,9 | 0,30 N | 0,59 N | 0,89 N | 1,49 N |
| 12 × 12 | 144 | 3,0 | 0,14 N (15 g) | 0,29 N (29 g) | 0,43 N (44 g) | 0,72 N |

Dans quel sens pousse-t-elle ? Cela dépend du côté de la table où est la porte. Sur un accordéon, la soupape est sur la face extérieure, côté atmosphère : au poussé, l'air du soufflet la soulève ; au tiré, l'air extérieur la plaque. L'orgue met sa soupape de l'autre côté, dans la laye, et les signes s'inversent. Il n'y a pas de côté gratuit. Là où la pression aide à ouvrir, il faut un ressort assez fort pour tenir la porte fermée contre le plus fort poussé du musicien ; là où elle résiste, le doigt la paie à l'ouverture. La somme des deux charges est la même des deux côtés. Seule une porte poussée également dans les deux sens échappe au marché, et nous la rencontrerons plus bas.

Sur le Lib RT, la charge tombe sur le ressort. Il doit tenir la soupape fermée contre la pointe du poussé, avec une marge pour les à-coups du soufflet, et aussi appuyer assez la peau pour qu'elle étanche :

$$F_{0} = 1{,}2 \, \Delta p_{\mathrm{pointe}} \, A + F_{\mathrm{\acute{e}tanch}}$$

Avec 3 kPa de pointe et 0,3 N d'étanchéité, cela fait 1,38 N (141 g) à la soupape. Un ressort plus faible fuit au forte poussé : la note parle sans qu'on appuie, vieux défaut des accordéons aux ressorts fatigués.

Que sent le doigt pendant que la porte s'ouvre ? Trois choses s'ajoutent : la précharge, la raideur du ressort, et la pression. La dernière ne reste pas. Dès que la soupape décolle, l'air passe par deux orifices en série, le rideau entre soupape et portée (périmètre fois levée) et l'anche elle-même, et la part de pression qui reste sur la soupape tombe comme $1/(1+(P x / A_{\mathrm{anche}})^{2})$. Pour une anche grave de section efficace 20 mm² environ, il reste un quart de la poussée à 0,5 mm de levée, 8 % à 1 mm, presque rien à 2 mm. Voilà la marche du premier paragraphe : au tiré, le doigt paie d'abord 1,38 + 0,60 = 1,98 N au décollement, puis 1,50 N à un millimètre, puis le ressort seul, 1,56 N à mi-course. Les facteurs d'orgue appellent cela le « pluck ». Au poussé, la pression aide au départ (0,78 N) et les deux sens se rejoignent après un millimètre. L'inégalité entre poussé et tiré vit dans le premier millimètre, et nulle part ailleurs.

### Le prix de la levée

Pourquoi la levée de la soupape regarderait-elle le doigt ? Parce que l'énergie n'a nulle part où se cacher. Si le bouton descend d'une course $c$ et que la soupape monte d'une levée $x$, alors sans pertes $F_{b} c = F_{s} x$, et

$$F_{b} = F_{s} \, \frac{x}{c} \, \frac{1}{\eta} = F_{s} \, \frac{r}{\eta}$$

avec $\eta$ le rendement de la chaîne, 0,9 environ avec des pivots acier. Le rapport $r$ de la levée à la course n'est pas un détail du dessin : il multiplie tout. Une levée de 10 mm pour une course de 5 mm double l'effort au bouton.

Et de combien de levée l'air a-t-il besoin ? La soupape cesse de brider le débit quand le rideau autour d'elle, périmètre $P$ fois levée $x$, égale l'aire du trou. Pour 20 sur 15 mm, $A/P$ = 300 / 70 = 4,3 mm ; avec 20 % de marge, 5,1 mm. Au-delà, une soupape qui s'ouvre davantage ne donne pas plus d'air, et la pression sur elle a déjà disparu après le premier millimètre. Un centimètre de levée n'achète rien au son et coûte 60 à 100 % d'effort en plus au doigt. Savoir si le son de l'anche est plus ouvert au-delà de $A/P$ est une question pour l'oreille, et le banc peut y répondre (essai du trou, plus bas) ; rien dans la physique ne l'attend.

Le tableau @tab:fr-bouton réunit les deux pour le grand trou : le mieux que puisse faire une mécanique, $r$ proche de 1, donne 160 à 180 g à mi-course et 200 à 225 g au décollement au tiré. Le but de 80 à 100 g est hors d'atteinte avec ce trou et cette pointe, quelle que soit la mécanique.

Table: Effort au bouton pour le trou 20 × 15 mm (jeu 2 kPa, pointe 3 kPa, η = 0,9). La dernière colonne est la force qui ramène le bouton au pire moment, poussé à 3 kPa, soupape fermée. {#tab:fr-bouton}
| course (mm) | levée (mm) | r | décollement (tiré) | mi-course | fin de course | retour au poussé 3 kPa |
|---|---|---|---|---|---|---|
| 5 | 4,5 | 0,90 | 202 g | 159 g | 176 g | 40 g |
| 5 | 5,0 | 1,00 | 224 g | 177 g | 196 g | 44 g |
| 5 | 6,0 | 1,20 | 269 g | 212 g | 235 g | 53 g |
| 5 | 8,0 | 1,60 | 359 g | 282 g | 313 g | 70 g |
| 5 | 10,0 | 2,00 | 449 g | 352 g | 391 g | 88 g |
| 4 | 5,0 | 1,25 | 280 g | 221 g | 245 g | 55 g |

La dernière colonne mérite un instant. Au forte poussé, la pression soulève la soupape fermée et mange la précharge du ressort ; ce qui reste pour remonter le bouton, c'est la marge, 44 g. Sous 35 à 40 g, une touche qui frotte un peu reste en bas. C'est très probablement le défaut de l'instrument actuel du musicien : des ressorts tout juste assez forts, et un peu de frottement.

Où est donc l'effort ? Le tableau @tab:fr-leviers classe les leviers d'action, et les deux premiers ne sont pas du tout dans la mécanique.

Table: Effort à mi-course au tiré (décollement entre parenthèses), pour r = 1,2. {#tab:fr-leviers}
| trou | aire (mm²) | jeu 1 kPa, pointe 1,5 kPa | jeu 2 kPa, pointe 3 kPa | jeu 3 kPa, pointe 5 kPa |
|---|---|---|---|---|
| 20 × 15 | 300 | 129 g (155 g) | 212 g (269 g) | 322 g (408 g) |
| 15 × 15 | 225 | 108 g (126 g) | 170 g (212 g) | 253 g (316 g) |
| 12 × 12 | 144 | 86 g (96 g) | 126 g (150 g) | 179 g (217 g) |
| d 10 | 79 | 68 g (71 g) | 90 g (101 g) | 119 g (137 g) |

1. **Le trou.** Une anche a besoin de trois à cinq fois sa section efficace pour respirer, 60 à 100 mm². Le reste du trou sert à l'acoustique de la chambre et à la sortie du son. Un trou de 12 sur 12 mm divise par deux la poussée de la pression ; avec $r$ = 1 et 1,5 kPa de pointe, il donne 72 g à mi-course et 80 g au décollement.
2. **La vraie pointe de pression.** Entre 1,5 et 3 kPa, la précharge passe de 0,84 à 1,38 N. Un jazzman qui joue doux ne dépasse peut-être jamais 1,5 kPa ; un manomètre en U le dit en un après-midi.
3. **r au plus 1.** Course 5 mm, levée 5 à 5,5 mm.
4. **Un ressort long et souple**, qui monte de 15 à 25 % sur la levée, pas de 100 %.
5. **Le rendement** : tourner, pas glisser (plus bas).
6. **La portée** : une portée plane et une peau souple étanchent avec 0,3 N ; une portée gauche demande 0,6 N, que le doigt paie.

### Quatre façons de tricher avec le vent, et pourquoi trois échouent

Peut-on compenser la poussée de la pression, comme on équilibre une fenêtre à guillotine par son contrepoids ? Quatre idées viennent naturellement. La figure @fig:fr-compensations les dessine en coupe à côté de la soupape simple, et son dernier panneau compare ce que chacune laisse au bouton, avec les mêmes hypothèses que le tableau @tab:fr-bouton.

![Les compensations, en coupe et en grammes au bouton (trou 20 × 15 mm, r = 1). Référence : au tiré, la pression plaque la soupape. (a) Une petite soupape pilote ouverte d'abord. (b) Deux soupapes côte à côte. (c) Une soupape équilibrée : deux portées sur une même tige. (d) Un ressort d'aide au bouton. (e) Décollement, mi-course et retour au bouton.](figures/mecanique_compensations_fr.png){#fig:fr-compensations}

**La pilote (a).** Une petite soupape de 6 sur 6 mm couvre un trou percé dans la grande. Le levier la soulève d'abord, par un crochet qui a un peu de jeu ; l'air file par le petit trou, la chambre derrière se met à la pression extérieure, et alors seulement le crochet prend la grande soupape. Le « pluck » du tiré a disparu : le décollement tombe de 224 à 165 g, un gain d'environ un quart. Mais regardez la mi-course : 176 g dans les deux cas. La pilote enlève la pression, qui ne vivait que dans le premier millimètre, et laisse le ressort, qui doit toujours tenir la pointe du poussé. Elle coûte deux soupapes par note.

**Deux soupapes côte à côte (b).** Deux trous de 150 mm² ont la même aire qu'un trou de 300 ; la poussée est la même, le ressort total aussi. Rien n'est gagné, et les pièces sont doublées. On la dessine seulement parce que c'est la première idée que tout le monde a.

**La soupape équilibrée (c).** Ici le marché de la première section est rompu. Deux disques d'aires égales sont fixés sur une même tige, et l'air du soufflet est entre deux plaques : le disque du haut repose sur la plaque du haut, dehors, et la pression sous lui le pousse à s'ouvrir ; le disque du bas repose sur la plaque du bas, dedans, et la même pression le pousse à se fermer. Les deux s'ouvrent en bougeant dans le même sens. Les deux poussées s'annulent, quel que soit le signe de la pression, poussé ou tiré, et le ressort n'a plus à tenir la pointe : seulement à étancher, 0,3 à 0,5 N. Au bouton, cela fait 45 g au décollement et 51 g à mi-course. C'est la seule solution qui atteint 80 g sur un trou de 300 mm². Les ingénieurs de la vapeur la connaissaient sous le nom de soupape à double siège. Son prix est réel : une portée côté soufflet ou un passage étanche pour la tige, deux trous par note, et une conception jamais essayée sur un accordéon, à prouver au banc. Elle est gardée ici comme piste de recherche, pas comme base du Lib RT.

**Le ressort d'aide (d).** Un ressort qui tire le bouton vers le bas avec une force constante se retranche de l'effort, et se retranche tout autant du retour. Avec 44 g de retour au forte poussé, on ne peut lui donner que 5 à 10 g ; le panneau montre 168 g à mi-course et 36 g de retour, au bord d'une touche qui reste en bas. Il n'apporte rien ici.

La leçon de la figure est celle de tout le chapitre. L'effort est dans le trou et dans la pression, les deux grandeurs que la mécanique ne touche pas ; la soupape équilibrée est la seule idée qui y entre, et elle le fait en changeant la porte, pas le levier.

> À compléter (Ewen) : le décollement d'une soupape au tiré, mesuré avec un peson accroché à la soupape et tiré lentement, puis la force à 1, 2, 3 et 5 mm de levée (cales sous son bord). La marche du premier millimètre a-t-elle la taille que prédit la courbe ?

### Les rappels, un seul ressort, et l'espace avant la force

Sur un chromatique, la même note revient sur plusieurs rangées, et le second bouton, le rappel, mène la même soupape par une chaîne plus longue. Deux boutons, une porte : le doigt sentira-t-il la même force sur les deux ? Oui, si les deux chaînes ont le même rapport $r$ et si un seul ressort, celui de la soupape, ramène tout. Chaque pivot acier de plus sur le rappel coûte 0,2 à 1 % d'effort ; trois de plus, 1 à 3 %, soit 2 à 5 g sur 180. Le doigt ne distingue pas une différence de force sous 7 à 10 %. Un second ressort sur le rappel, en revanche, ajouterait toute sa force à ce seul bouton : c'est la seule chose à éviter.

Le temps mort est plus subtil. Une chaîne qu'un ressort tient chargée, le ressort à un bout et le bouton à l'autre, toutes les articulations attachées, n'a aucun temps mort dû à ses jeux : à la descente comme à la remontée, chaque articulation reste appuyée du même côté. Les jeux se montrent plutôt en flottement latéral et en bruit. Un bouton simplement posé sur un levier, avec un espace, a un temps mort égal à cet espace. Au bouton, 0,1 à 0,2 mm se tolèrent, 2 à 4 % de la course ; au-dessus, le doigt sent un vide avant la résistance. Et la levée a son propre budget : la levée au-delà du $1{,}2\,A/P$ utile doit couvrir la flèche du levier sous l'effort de jeu et l'écrasement de la peau et du feutre. Pour 6 mm de levée sur le grand trou, le budget est 0,9 mm ; pour 5,5 mm, 0,4 mm ; pour 5 mm, rien du tout.

### Glisser contre tourner

La v5 grince. Pourquoi une tige d'acier qui coulisse dans un trou imprimé grince-t-elle, quand la même tige qui tourne dans le même trou ne grince pas ?

Le frottement, d'abord. L'acier sur le PLA imprimé a un coefficient de 0,35 à 0,45 au repos et de 0,25 à 0,35 en mouvement. Cet écart suffit au broutage : la tige colle, la chaîne élastique qui la pousse se charge, la tige saute, et le cycle recommence dans le kilohertz. C'est le grincement. Le PTFE (0,08 au repos, 0,05 en mouvement) ou le bronze fritté huilé n'ont presque pas d'écart, et ne broutent pas. Puis les couches : un trou imprimé à la verticale a des marches de 0,18 à 0,24 mm en travers du mouvement, et la tige en franchit une à chaque couche.

Mais le plus grand effet est géométrique, et la figure @fig:fr-tiroir le montre. Quand la force sur la tige est décalée de son axe d'une distance $e$, par un pion par exemple, la tige se met en biais dans son guide de longueur $L$ et s'appuie aux deux bouts avec une force $N = F e / L$. Le frottement agit aux deux bouts, $2 \mu N$, contre le mouvement, si bien que

$$F_{\mathrm{pouss\acute{e}e}} = \frac{F_{\mathrm{utile}}}{1 - 2 \mu e / L}$$

et la tige coince quand $2 \mu e / L$ atteint 1. La v5 a son pion à 5 mm d'un guide de 8 mm, en PLA : le facteur vaut 2,0, le doigt paie double. Si la portée réelle du guide n'est que de 4 mm, avec les chanfreins et les marches de couches, la tige coince par moments. La règle qui en sort est courte : longueur guidée au moins $10 \mu e$, 20 mm pour le PLA et 5 mm pour le PTFE, ou mieux, pousser dans l'axe.

![L'effet tiroir. Une force décalée de e fait porter la tige aux deux bouts de son guide ; l'effort monte comme 1/(1 − 2µe/L) et la tige coince à 2µe/L = 1. Le pointillé est la v5.](figures/mecanique_tiroir_fr.png){#fig:fr-tiroir}

Faisons maintenant tourner la tige. Dans un pivot, le frottement n'agit qu'au rayon de l'axe, la perte est donc $\mu (d/2) / \ell$ pour un bras $\ell$. Avec un axe acier de 2 mm dans du PLA brut ($\mu$ = 0,4) et un bras de 60 mm, la perte est de 0,7 %. Un pivot perd 30 à 100 fois moins qu'un coulissement (tableau @tab:fr-remedes). C'est tout l'argument pour une mécanique où chaque touche est une rotation, contre une tige guidée.

Table: Remèdes pour une tige qui coulisse (effort utile 1, excentrement 5 mm), face à une rotation. {#tab:fr-remedes}
| guide | µ | L (mm) | facteur d'effort |
|---|---|---|---|
| PLA tel qu'imprimé | 0,40 | 8 | × 2,0, broutage |
| PLA allongé | 0,40 | 20 | × 1,25 |
| PA imprimé, percé et alésé | 0,30 | 12 | × 1,33 |
| tube laiton 3 × 2, huilé | 0,19 | 10 | × 1,23 |
| gaine PTFE (gaine Bowden 2 × 4) | 0,08 | 8 | × 1,11, sans broutage |
| **rotation sur axe acier 2 mm, bras 60 mm** | 0,40 | - | × 1,007 |

La v5 a aussi de fines tiges d'acier qui courent en biais entre une équerre imprimée et le levier en aluminium. La correction d'Ewen mérite d'être notée ici, parce qu'elle a corrigé l'analyse : en pratique ces tiges ne flambent pas, et le calcul est d'accord (la charge d'Euler reste au-dessus de l'effort transmis). Leur vrai coût est l'angle. Une tige à 30° du mouvement utile porte 15 % de force en plus et pousse le pivot de côté avec 58 % de l'effort utile ; si un guide reprend cette poussée latérale, un quart de l'effort part en frottement. Une tige en traction n'a aucun de ces soucis : elle ne peut pas flamber, elle s'aligne d'elle-même sur ses deux attaches, elle peut être un fin câble qui passe entre les autres, et la chaîne chargée par le ressort reste tendue, sans temps mort. Il suffit d'attacher la tige de l'autre côté du pivot de l'équerre pour que le doigt la tire au lieu de la pousser.

### Des pivots qui ne branlent pas

Un trou imprimé n'est jamais ce qu'on a dessiné : 0,1 à 0,3 mm trop petit, rond s'il est imprimé à la verticale, ovale d'autant s'il est imprimé couché. La pression de contact n'est pas le problème, 0,5 MPa pour 3 N sur un axe de 2 mm et 3 mm de long, contre 10 MPa admissibles. Le problème est le basculement. Un levier sur un moyeu court balance sur son propre jeu : le bout se déplace du jeu divisé par la longueur du moyeu, fois la longueur du levier (tableau @tab:fr-bascule). 0,05 mm de jeu sur un moyeu de 3 mm déplace le bout d'un levier de 100 mm de 1,7 mm, et avec 5 mm entre leviers, les voisins se touchent.

Table: Déplacement latéral du bout d'un levier de 100 mm (mm), dû au jeu de son moyeu. {#tab:fr-bascule}
| jeu diamétral (mm) | moyeu 2 mm | moyeu 3 mm | moyeu 6 mm | moyeu 9 mm |
|---|---|---|---|---|
| 0,02 | 1,00 | 0,67 | 0,33 | 0,22 |
| 0,05 | 2,50 | 1,67 | 0,83 | 0,56 |
| 0,10 | 5,00 | 3,33 | 2,50 | 1,11 |

Aucun moyeu réaliste ne tient le bout d'un long levier à moins d'un demi-millimètre. L'accordéon a résolu cela depuis longtemps avec un peigne au bout des leviers, des fentes garnies de feutre : le jeu du moyeu ne compte alors plus que pour le bruit. Deux axes alternés, leviers pairs sur l'un et impairs sur l'autre, permettent des moyeux deux fois plus longs. Et un trou alésé ou un tube laiton pressé ramène le jeu lui-même à 0,02 à 0,05 mm.

Il existe un pivot sans jeu et sans frottement : une fine lame d'acier à ressort, pincée des deux côtés, qui fléchit au lieu de tourner. Un levier tourne d'environ 0,1 rad (6 mm de levée sur un bras de 60 mm) ; une lame de 0,15 mm d'épaisseur et 5 mm de long porte alors 309 MPa, sous les 600 à 700 MPa de fatigue de l'acier à ressort, et vit indéfiniment. Son propre couple de rappel est petit, 0,1 N au bras de 60 mm : une aide, pas le ressort. La charnière souple imprimée est sa cousine en plastique : seul le polyamide, 0,4 à 0,6 mm sur 3 à 5 mm, survit à un million de flexions (une touche très jouée en voit 100 000 par an) ; le PLA craquèle après quelques centaines. Et une charnière flue sous la charge permanente du ressort, si bien que sa position de repos dérive : bonne pour de petites équerres, pas pour le pivot principal.

### La raideur, pas la résistance

En quoi faire un levier ? Pas en ce qu'on penserait d'abord. Les contraintes dans un levier sont partout faibles, sous 15 MPa ; rien ne casse. Ce qui compte, c'est combien il fléchit, parce que chaque dixième de millimètre de flèche est pris sur la levée ou ajouté au temps mort. La flèche admissible au bouton est de 0,2 à 0,3 mm. Un levier bascule, bouton d'un côté de l'axe et soupape de l'autre, fléchit comme une console depuis l'axe :

$$\delta = \frac{F L_{b}^{2} (L_{b} + L_{s})}{3 E I}, \qquad I = \frac{b h^{3}}{12}$$

et la largeur $b$ est fixée par l'entraxe des touches : 3,5 mm quand trois rangées se partagent une bande de 15 mm, 6 mm avec deux rangées. Sous l'effort de jeu du grand trou, 1,5 N, un PLA de 3 sur 7 mm fléchit de 0,93 mm sur des bras de 60 + 60 mm : quatre fois trop, et il flue, si bien que les boutons s'enfoncent au fil des mois. L'ASA 3 sur 12 mm tient jusqu'à 60 + 60 mm (0,23 mm) ; le polyamide chargé carbone 2,5 fois mieux ; au-delà de 80 mm, seul le métal à chant tient : l'aluminium 2 sur 8 mm fléchit de 0,16 mm sur 100 + 100 mm.

À chant est l'expression importante. La raideur va comme le cube de la hauteur. La même bande d'aluminium, 8 sur 2 mm, est 16 fois plus souple posée à plat que dressée sur sa tranche : 2,6 mm contre 0,16 mm sous 1,5 N sur 100 + 100 mm. Les photos de la v5 suggèrent des leviers à plat ; si le bouton pousse à la verticale, c'est la pose souple, et c'est la première chose à vérifier (100 g au bout, un comparateur).

### Les ressorts : l'acier ou rien

Pourquoi ne pas imprimer aussi les ressorts ? Parce qu'un plastique sous contrainte permanente oublie sa forme. À 23 °C, le PLA n'est qu'à 35 K sous sa transition vitreuse ; sous quelques mégapascals, ses chaînes glissent lentement, et la déformation imposée devient permanente. Un ressort imprimé perd 20 à 40 % de sa force en quelques semaines, et presque tout en un après-midi à 50 °C, dans une voiture l'été. L'acier à ressort travaille à une fraction de pour cent de déformation sans aucun écoulement, et stocke 20 à 80 fois plus d'énergie par volume. Un ressort acier par soupape, aucun au bouton. Pour une précharge de 1,38 N à un bras de 60 mm et une montée d'au plus 25 % sur la levée : un ressort de torsion sur l'axe en fil de 1,0 à 1,2 mm, de 7 à 10 mm de diamètre, 8 à 12 spires, préchargé de 45 à 100° ; ou un ressort de traction en fil de 0,5 mm, de 5 mm de diamètre, 15 spires, accroché à 25 mm de l'axe. Les ressorts qu'Ewen a déjà servent, une fois leur raideur mesurée avec quelques pièces de monnaie : un ressort raide s'accroche près de l'axe, un souple plus loin.

### Ce que les modèles laissent de côté

La pression sur la soupape qui s'ouvre est un modèle quasi statique de deux orifices en série ; le transitoire au décollement, où l'air qui file sous la portée peut un instant pousser sur toute la soupape (jusqu'à 1,09 N au lieu de 0,60 à 2 kPa), est borné, pas calculé. La section efficace de l'anche, 20 mm², est estimée d'après le débit d'une grosse basse, et devrait être mesurée en chronométrant la vidange du soufflet sur une seule note. Le rendement de 0,9 vaut pour des pivots acier ; 0,95 avec un peigne PTFE, 0,8 avec des pivots PLA bruts. Les leviers sont des poutres de section constante chargées en un point ; un levier évidé est plus souple. Les données des matières imprimées valent à 20 % près, et leur fatigue est un ordre de grandeur : un essai d'endurance vaut mieux que le tableau.

Sous ces limites, il y a une chose qui mérite d'être dite simplement. La première question était : où va l'effort ? La réponse est venue avant qu'aucune pièce ne soit coupée : dans le trou et dans le souffle du musicien, pas dans l'ingéniosité des leviers. La mécanique ne peut qu'ajouter à ce plancher, un peu (2 à 4 % pour une rotation par touche) ou beaucoup (10 à 100 % pour une tige guidée). Une bonne mécanique est celle qui n'ajoute presque rien, et laisse le doigt sentir l'air.

> À compléter (Ewen) : la pointe de pression du jazzman, sur un tube en U relié au soufflet, du pianissimo au sforzando, au poussé et au tiré. C'est le chiffre qui pèse le plus sur tout ce qui précède. Et, si tu le veux, la sensation elle-même : ce que fait la marche du premier millimètre sous le doigt, avant et après avoir su ce qu'elle est.
