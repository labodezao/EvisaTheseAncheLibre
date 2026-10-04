# Thèse, parties II à V : version française

Traduction en français du texte anglais des parties II à V de `design_theory.lyx`
(PR #40, branche `claude/these-parties-2-a-5`), pour relecture. Le manuscrit LyX
reste en anglais ; ce fichier est le miroir, paragraphe par paragraphe. Les
paragraphes en italique « À compléter (Ewen) » sont les mêmes que dans le LyX.
Les deux tableaux sont repris. Les titres de sections sont ceux du manuscrit,
en anglais entre crochets quand ils diffèrent.

---

# Partie II — Le couplage des sommiers [Reed blocks coupling]

Prenez une plaque d'anche hors de son sommier et tenez-la dans la main. Elle
joue, mais elle joue seule. Remettez-la sur le sommier, au-dessus de sa chambre,
sous la table d'harmonie, derrière son clapet, et elle joue avec tout ce qui
l'entoure. Cette partie parle de ce tout : la chambre de bois sous la languette,
le trou de la table au-dessus d'elle, le canal sous le clapet, et l'autre
languette de la même note qui respire le même air. Le facteur choisit tout cela
avec une scie, un ciseau et un pot de cire. La physique dit ce que chaque choix
fait au démarrage de la note, à sa hauteur et à son son.

La méthode de cette partie est celle du chapitre 2. Un modèle par éléments finis
(Elmer) donne la réponse passive de l'air de la chambre, vue depuis la fente de
la languette. Un petit réseau de masses d'air, de ressorts d'air et d'orifices
(le modèle semi-analytique `coupled_reeds`) reçoit ces nombres et fait osciller
la languette. Chaque chiffre cité plus bas est soit un résultat d'éléments finis
sur les chambres du sommier R12, soit une prédiction de ce petit réseau, soit un
chiffre de l'atelier. Le statut de chacun est dit dans le texte, parce que le
petit réseau est connu pour être faux sur plusieurs points (chapitre 2 et audit
du modèle à deux anches, `docs/audit_deux_anches.md`) : ses languettes vont trop
loin, ses débits sont trop grands, et l'expérience de l'anche en sandwich réfute
son mécanisme de démarrage. On garde ses tendances ; pas ses pascals.

## Chapitre — La conception du sommier [Reed block design]

Un sommier est un peigne de bois. Chaque dent du peigne est une cloison, et
entre deux cloisons il y a une chambre. La plaque, avec ses deux languettes,
ferme la chambre d'un côté ; la table d'harmonie, percée d'un trou, la ferme de
l'autre. Dans le sommier R12 étudié ici, chaque chambre est faite de deux cases,
A et B, séparées par une cloison centrale qui change de côté au milieu du
sommier. L'air d'une telle chambre a été maillé en tétraèdres du second ordre et
ses modes calculés avec Elmer, le maillage étant fait avec Gmsh. Les parois et
les plaques sont rigides dans le modèle, les fentes sont fermées (languettes au
repos), l'air est à 20 degrés. Le bout du trou débouche sur un grand volume à
pression nulle, le clapet étant loin.

Ce qui est sorti d'abord, c'est un nombre pour chaque chambre. Avec un trou de 8
par 25 mm à travers une table de 8 mm (dimensions prises dans le petit réseau,
pas mesurées sur l'instrument), la première résonance d'air des douze chambres
du R12 va de 1142 Hz (chambre 1, la plus grande, 18,3 cm³ de cases) à 1575 Hz
(chambre 12, 10,2 cm³). Un second mode, où l'air de la case A bascule contre
l'air de la case B, se trouve entre 1402 et 2017 Hz. Une maille de 2 mm suffit
pour un plan d'expériences : le premier mode de la chambre 12 passe de 1575,5 Hz
à 1574,1 Hz quand on affine la maille de 2 mm à 0,8 mm, soit 0,1 pour cent ou
1,5 cent. Le solveur a été vérifié sur une boîte rigide de 50 par 15 par 10 mm,
où il donne 3430,0 Hz pour le c/2L = 3430 Hz exact, et sur la même boîte ouverte
à un bout (1715,0 ; 5145,0 et 8575,0 Hz pour la série du quart d'onde).

### Sommier collé ou massif [Glues or solid RB]

Un sommier peut être assemblé de pièces, des cloisons collées sur une base, ou
taillé dans une seule pièce de bois. Le facteur sent la différence dans la main
et l'entend, ou croit l'entendre. Que dit là-dessus la physique de ce travail ?
Honnêtement, peu pour l'instant, et il vaut mieux dire ce qu'elle ne dit pas.

Tous les calculs acoustiques de ce travail prennent les parois comme rigides.
Une paroi rigide fait deux choses : elle garde l'air dedans, et elle ne rend rien
à l'air. Une vraie paroi de sommier collé fait ces deux choses imparfaitement.
Un joint de colle qui n'est pas étanche est une fuite, et une cloison mince qui
fléchit ajoute un peu de compliance à la chambre et lui prend un peu d'énergie à
chaque cycle. Le modèle par éléments finis est aussi sans pertes : ses pics de
résonance sont infiniment fins, et les vrais, comme le dit le dépôt, seront plus
ronds. La résistance d'une vraie chambre se recale sur une mesure, elle ne se
calcule pas (section sur la chambre vue de la fente, geste (b) du protocole
expérimental).

Le critère d'atelier pour l'étanchéité d'un sommier est un chiffre du livret de
stage d'Ewen, un critère proposé, pas encore mesuré sur ses instruments : un
sommier collé, nu ou garni de ses plaques, doit fuir moins de 0,05 litre par
minute sous 500 Pa. Pour le mesurer, le débitmètre de la table d'accordage, ou
le test de chute de pression du banc (commande `LEAKTEST` du firmware, analysée
par la fonction `fit_decay` de `banc_recherche/leak.py`, qui ajuste
p(t) = p₀·e^(−t/τ) sur le logarithme de la pression et rend la constante de
temps et une conductance).

*À compléter (Ewen) : y a-t-il une différence mesurable entre une chambre collée
et une chambre massive ? Deux mesures, toutes deux bon marché : la fuite à
500 Pa de chaque sommier à la table d'accordage (débitmètre SFM3000, ou le
gazomètre et le tube en U de l'atelier), et le facteur de qualité d'une chambre
excitée par un petit balayage d'un petit haut-parleur et enregistrée au micro
(ring-down, `banc_recherche/ringdown.py`). Une chambre dont les parois
fléchissent devrait montrer un Q plus bas. Quel sommier, quelle chambre, et
quel jour ?*

### L'organisation du fluide dans la cavité [Fluid organization in cavity]

Suivez l'air. En poussé, il quitte le soufflet, passe par la fente de la
languette, remplit la chambre, monte par le trou de la table dans le canal sous
le clapet, soulève le clapet et sort. En tiré, le même chemin est parcouru dans
l'autre sens : l'air du dehors entre par le clapet, descend le trou, remplit la
chambre, passe l'autre languette de la plaque et finit dans le soufflet, qui est
en dépression. Dans les deux cas la languette est entre deux pressions, et c'est
leur différence qui la pousse hors de sa fente et fait passer l'air.

Chaque élément de ce chemin se mesure au pied à coulisse, et chacun devient une
chose simple dans le modèle. La chambre est un ressort d'air : un volume V donne
une compliance V/(γ·P_atm), où γ est la constante adiabatique de l'air (environ
1,4) et P_atm la pression atmosphérique. Le trou de la table et l'ouverture du
clapet sont des masses d'air, ρ·ℓ/S, où ρ est la masse volumique de l'air, ℓ la
longueur effective du passage (sa longueur réelle plus les corrections
d'extrémité, environ 0,8 fois le rayon équivalent de chaque côté) et S sa
section ; ils portent aussi une perte d'orifice, ρ·q|q|/(2·(C_d·S)²), où q est le
débit et C_d un coefficient de débit. Le canal sous le clapet est un volume
commun aux deux languettes de la note. C'est tout le réseau de `coupled_reeds`,
et tout y est dérivé de la conservation de la masse et de la loi de Bernoulli
pour un passage court d'air incompressible. Ce qui n'est pas dérivé, ce sont les
dimensions : chambre 35 par 15 par 15 mm, trou 8 par 25 par 20 mm, canal 4 cm³,
clapet 3 cm² par 10 mm sont des ordres de grandeur devinés d'un sommier de
médium, et chacun est à relever sur l'instrument.

Un tel réseau à constantes localisées est valable tant que chaque dimension est
petite devant la longueur d'onde : à 440 Hz la longueur d'onde est d'environ
78 cm et une chambre fait 3 cm. Les résonances du réseau sont bien au-dessus des
fondamentales des languettes : chambre et trou vers 2 kHz avec les dimensions
devinées (1142 à 1575 Hz pour les chambres du R12 calculées par Elmer), canal et
clapet vers 5 kHz. Elles colorent les partiels aigus ; elles ne font pas la
note.

#### La section d'ouverture [Section aperture]

Sur le banc de ce travail, l'air ne vient pas d'une main mais d'un moteur, et le
passage entre l'alimentation en air et la languette est une fente ouverte par
une vis. Sa largeur est de 15 mm ; la vis règle sa longueur ; la section est le
produit. Dans le plan d'expériences hérité du banc de 2020 (`Mesures.py`), cette
section est le facteur appelé Section, en 8 pas, croisé avec 8 pas d'angle de
clapet et avec les pas de pression, chaque point étant mesuré dans les deux sens
de pression. C'est l'ouverture dont parle cette section : de combien
l'alimentation est étranglée avant la languette.

Pourquoi est-ce important ? Parce que le soufflet n'est pas une source idéale.
Une source de pression idéale tient sa pression quel que soit le débit ; une
source de débit idéale tient son débit quelle que soit la pression. Un vrai
soufflet, comme la turbine du banc, donne moins de débit quand la pression
monte. Dans le modèle cela s'écrit q = q₀ − p/R : le débit q qui arrive vraiment
est le débit de consigne q₀ moins la pression p divisée par une résistance
interne R. La pente R se lit directement sur le banc : à commande de moteur
fixe, balayer le facteur Section, noter les couples pression et débit, et tracer
la pression en fonction du débit. Une droite verticale est une source de débit,
une horizontale une source de pression, une oblique une source réelle, et sa
pente est R. Le dépôt appelle cette expérience E1 et la met en premier, parce
que chaque amplitude que le modèle prédit en dépend.

La valeur de R dans le modèle a sa propre histoire, et elle vaut d'être
racontée. Elle fut d'abord posée à 2·10⁸ Pa·s/m³ sans aucune mesure. À cette
raideur la languette d'une lame de 55 mm pouvait parcourir 110 mm à pleine
nuance, ce qui est absurde. Un balayage de R a montré que 5·10⁶ Pa·s/m³ donne
des courses d'environ 2 mm sur tout le clavier, et les plus petits écarts de
justesse ; cela correspond à une restriction d'alimentation d'environ 8 mm²,
l'ordre de grandeur d'un canal de sommier. À 2·10⁶ plus rien ne démarre. Le
nombre 5·10⁶ est donc un choix fait pour que le modèle reste dans la plage d'un
vrai accordéon, pas une mesure ; la mesure, c'est E1. Notez aussi que la
pression d'étouffement, au-dessus de laquelle la languette est soufflée hors de
sa fente et s'arrête, ne dépend pas du tout de R dans le modèle à une anche
(379,8 Pa pour la languette de référence, quelle que soit la source) : elle est
fixée par la géométrie de la fente, pas par l'alimentation.

Il y a une seconde ouverture, le trou de la table d'harmonie. Le plan
d'expériences numérique sur les chambres (`research/fem/sommier/seuils_cavite.py`)
balaie sa section de 25 à 400 mm², et un plancher de 100 mm² est gardé dans la
proposition pour le R12, pour ne pas étrangler l'air que la languette consomme.
Ce plancher est une hypothèse, la moitié du trou actuel supposé, à confirmer par
le débit mesuré au banc.

*À compléter (Ewen) : la caractéristique de ta source, pression en fonction du
débit, à commande de moteur fixe et pour les huit pas de Section
(expérience E1), avec le débitmètre SFM3000 et le capteur de pression du banc,
ou un tube en U à eau. Une pente, un nombre. Quel jour ?*

#### Pression et débit : l'impédance [Pressure and Flow : impedance]

L'impédance est un mot pour une question simple : quand je pousse un débit,
quelle pression est-ce que je reçois en retour ? Le rapport des deux est
l'impédance. Le banc de ce travail la mesure de la manière la plus rustique et
la plus utile, à partir du capteur de pression et du débitmètre pendant une
note tenue : `banc_recherche/impedance.py` prend la moyenne de la pression sur
le débit, et aussi le produit des deux, qui est la puissance pneumatique que le
joueur dépense. C'est l'impédance de tout l'instrument vue du soufflet, à
fréquence nulle, et c'est ce que la main sent.

L'impédance acoustique vue par la languette est autre chose, et le chapitre 2
l'a calculée. Quand la languette pousse un petit débit oscillant q à travers sa
fente, la chambre, le trou et le dehors lui rendent une pression p ; le rapport
Z(f) = p/q, fréquence par fréquence, est tout ce que l'entourage fait à la
languette. Elmer résout l'équation de Helmholtz pour l'obtenir et le résultat
est condensé dans la forme de Foster, une masse d'air en série avec une somme de
résonateurs sans pertes. Le résultat principal est un signe. Bien en dessous de
la résonance de la chambre, là où joue chaque languette, la chambre ouverte se
comporte comme une masse d'air : l'air poussé par la languette s'échappe par le
trou et la languette sent son inertie. Une cavité fermée se comporte comme un
ressort. Dans la bande de la languette, la cavité fermée de l'ancien modèle
temporel était fausse de 12 400 pour cent pour l'anche grave, 494 pour cent pour
la médium et 232 pour cent pour l'aiguë ; un résonateur de Foster ramène
l'erreur sous 9 pour cent et deux sous 0,5 pour cent. La chambre d'un sommier
n'est pas une boîte : c'est une masse d'air suspendue à un trou.

Mesurer une impédance acoustique avec presque rien est possible, et le logiciel
est déjà dans le dépôt. La méthode à deux microphones de la norme ISO 10534-2
place deux petits micros dans un tube devant l'échantillon (une chambre, un
clapet, une sourdine) et un haut-parleur à l'autre bout ; du rapport des deux
pressions et de l'écart des micros on tire le coefficient de réflexion,
l'impédance normalisée et l'absorption de l'échantillon
(`banc_recherche/transfer.py`, fonctions `estimate_H12` et
`reflection_impedance`). La carte son du banc offre trois voies, une entrée
stéréo et une mono, ce qui suffit. Le montage lui-même, un tube et deux micros
de mesure bon marché, n'a pas été construit.

*À compléter (Ewen) : la première mesure à deux micros sur une chambre du R12,
le sommier fermé par sa plaque et le trou ouvert, pour comparer à la courbe
Elmer de la même chambre (premier pôle prédit à 1140 Hz pour la chambre 1). Un
tube en plastique, deux micros, le balayage de `frf.py`. Qui prête le second
micro, et quand ?*

#### Le rayonnement acoustique [Acoustic radiation]

Par où sort le son ? Dans le modèle de ce travail, par le clapet. Une petite
ouverture qui respire, petite devant la longueur d'onde, rayonne comme un
monopôle : à une distance r la pression est p(r,t) = ρ/(4πr)·dq_p/dt, où q_p est
le débit par le clapet. C'est dérivé, et valable tant que ka, le produit du
nombre d'onde par le rayon de l'ouverture, reste petit : environ 0,08 à 440 Hz
pour le clapet deviné, et jusqu'à 0,9 vers 5 kHz, où la formule cesse de tenir.
La puissance rayonnée se calcule sur le spectre du débit du clapet avec la
résistance de rayonnement d'une ouverture bafflée, ρω²/(2πc), et elle est
vérifiée numériquement : pour un débit sinusoïdal connu la fonction rend
2,1277·10⁻⁵ W là où la formule ρω²Q²/(4πc) donne 2,1279·10⁻⁵ W.

Une leçon du chapitre 2 est répétée ici parce qu'elle s'oublie facilement. Une
anche libre rayonne par son débit modulé, pas par la pression de sa chambre. Le
spectre à comparer à un micro est celui de dq/dt. Compté ainsi, le modèle à une
anche a douze harmoniques au-dessus de −30 dB ; compté sur la pression de
chambre, et avec le fondamental pris sur le partiel le plus fort, il semblait en
avoir deux. Le modèle n'était pas pauvre ; il était mal lu.

Ce que le modèle dit du rendement, la part du souffle qui devient son, n'est pas
encore à croire. Une version donnait 1,5·10⁻⁵ pour une languette et 2,9·10⁻⁵
pour deux languettes en phase ; une version plus tardive, avec le mécanisme de
la section qui se ferme, donnait 1 à 3 pour cent, que l'audit dit suspect. Les
deux nombres découlent de courses et de débits que l'audit sait déjà trop
grands. Et l'hypothèse que le clapet est la seule source est incomplète : le
soufflet, la caisse et la plaque rayonnent aussi, et rien dans ce travail n'a
mesuré combien.

*À compléter (Ewen) : la puissance acoustique d'une note contre la puissance
pneumatique dépensée, avec un micro calibré (la calibration du micro n'a pas
été faite) et la pression et le débit du banc. Un rapport, pour une anche, à
1,5 fois le seuil. Ce seul nombre jugerait le rendement de tous les modèles.*

### Impédance et problème inverse [Impedance and inverse problem solving]

Le problème direct, c'est calculer ce que fait une géométrie connue. Le problème
inverse, c'est le problème du facteur : à partir de ce qu'on entend ou mesure,
retrouver la géométrie, ou les quelques nombres qui la représentent. Ce travail
le rencontre trois fois, et chaque fois la même règle s'applique : recaler les
paramètres les moins sûrs sur les mesures les plus robustes, et garder les
autres observables comme prédictions. Un modèle ajusté sur tout ne peut plus
être contredit, et alors il n'apprend rien.

D'abord, à partir des éléments finis. Balayer 70 fréquences dans Elmer pour une
chambre a pris 487 s. À la place, les pôles de l'impédance sont pris d'un seul
calcul aux valeurs propres, les résidus de 14 solutions harmoniques loin des
pôles, et la forme de Foster est reconstruite ; sur le même maillage elle
reproduit le balayage à 0,017 pour cent (médiane) en 53 s. Le premier résonateur
donne alors au réseau son volume effectif, V = ρc²/a₁, et la longueur effective
du trou, ℓ = (a₁/ω₁²)·S/ρ, où a₁ et ω₁ sont le résidu et la pulsation de ce
résonateur et S la section du trou. Pour la chambre 1 sous la languette grave :
17,79 cm³ et 25,8 mm, contre 18,26 cm³ de cases géométriques et 8 mm d'épaisseur
réelle. La longueur effective est trois fois la réelle : les corrections
d'extrémité sont la dimension la moins sûre de tout le sommier.

Ensuite, à partir d'une languette pincée sur sa chambre (geste (b) du
chapitre 2). Le décalage de la fréquence pincée, prédit de 1,2 à 3,5 cents vers
le bas, recale la part κ² du volume balayé qui passe vraiment par la chambre ; la
fréquence mesurée du résonateur d'air recale la longueur effective du trou, le
volume étant gardé du dessin ; et l'amortissement de ce résonateur donne la
résistance de perte que le modèle par éléments finis sans pertes n'a pas, par
ζ_H = (R/2)·√(C/L_t) pour une résistance, une compliance et une inertance en
série. La mesure est bon marché, un micro et un cure-dent, et elle porte son
verdict : un décalage du mauvais signe, ou trois fois trop grand, ou un
résonateur à plus de 10 pour cent d'Elmer, voudrait dire que le couplage par la
fente doit être reformulé, pas réajusté.

Enfin, à partir d'un son joué. Ici la réponse honnête est qu'une seule note ne
suffit pas. Ajuster une source et un résonateur sur l'enveloppe d'une note est
sous-déterminé : l'enveloppe passe par les sommets des partiels et mélange les
deux. Le dépôt a mesuré combien de notes il faut pour les séparer, une dizaine
réparties sur la tessiture, parce qu'en dessous de six la résonance est mal
localisée et au-delà de douze le gain devient marginal. L'outil d'identification
tient deux colonnes, ce qui se mesure et ce qui se suppose, et imprime les deux,
parce qu'un paramètre supposé qu'on prend pour mesuré est la façon la plus sûre
de se tromper longtemps. Avant toute optimisation en dix dimensions, un plan de
Plackett-Burman sur les paramètres du modèle dit lesquels comptent.

Un récit d'avertissement a sa place ici, sur le décalage de fréquence comme
mesure de la chambre. Une première version du modèle à une anche prédisait que
la note jouée se tient 16 pour cent au-dessus de la note pincée, avec un volume
effectif de 40 cm³, et proposait de lire le volume dans ce décalage. Le décalage
était réel dans le modèle mais venait d'un terme de volume balayé qu'une anche
libre n'a pas : elle comprimait sa chambre comme un piston, ce qu'une languette
assise dans sa fente ne fait pas. Une fois ce terme retiré, la chambre
géométrique de 7,9 cm³ a suffi au modèle pour démarrer, et le décalage est tombé
à quelques dizaines de cents dans le grave et quelques cents au-dessus (+30 cents
à 102 Hz, +2 cents à 440 Hz dans cette version à cavité fermée), puis a changé de
signe quand le trou de la table est entré dans le réseau. Le problème inverse
ne vaut que ce que vaut le modèle direct qu'il inverse.

### La géométrie du sommier [Reed block geometry]

Quelle profondeur pour une chambre, quelle largeur pour son trou ? Le facteur a
des règles de pouce, souvent héritées. Voici ce que dit un plan d'expériences
numérique sur le petit réseau, ses limites d'abord : un mode de lame, des lames
d'acier uniformes, levée et jeu devinés, un mécanisme de démarrage que
l'expérience du sandwich réfute. Ce qu'on lit, c'est comment le seuil bouge
quand la chambre change, pas la valeur du seuil.

La chambre et son trou forment un résonateur de Helmholtz de fréquence
f_H = (c/2π)·√(S/(V·L_eff)), où c est la vitesse du son, S la section du trou,
V le volume des cases et L_eff la longueur effective du trou, sa longueur réelle
plus une correction d'extrémité de κ fois le rayon équivalent. Face à Elmer, la
formule avec le volume des cases seules est trop haute de 0 à 10 pour cent, et
la correction intérieure vue par Elmer vaut 0,85 à 1,34 fois le rayon équivalent
(moyenne 1,03), ce qui donne κ proche de 1,9 pour les deux bouts ensemble ; les
plans du 3 octobre 2026 ont tourné avec 1,55. La chaîne est celle qu'on voulait :
Elmer recale les longueurs effectives sur la vraie géométrie, le petit réseau
fait le plan.

Le plan balaie le rapport entre la résonance de la chambre et la fréquence de la
lame. Le tableau 1 donne, pour une lame de 700 Hz dans une chambre de 10,2 cm³
(le volume de la chambre 12), la pression de seuil et la justesse au seuil. En
dessous de la résonance, rien ne démarre. À un rapport de 1,1 le seuil est
énorme et la note est tirée loin vers le bas. Entre 1,2 et 1,7 le seuil est le
plus bas ; au-dessus de 2 il remonte. L'étude du 3 octobre 2026 a conclu sur une
fenêtre de 1,2 à 1,7. Le bord bas est lui-même incertain : la lame de 1000 Hz a
son seuil le plus bas à 1,2 (423 Pa) et la lame de 1400 Hz à 1,1 (775 Pa), là où
le plan cesse d'être propre. C'est la fenêtre du facteur : une chambre dont la
résonance se tient une quinte à une sixte mineure au-dessus de la languette la
fait parler le plus facilement. La justesse au seuil raconte l'autre face : plus
la résonance est proche, plus elle tire la note vers le bas, de 36 cents à 1,2 à
6 cents à 2,0. Les mêmes tendances tiennent dans les vraies chambres 1 et 12 du
R12 calculées par Elmer, avec leurs volumes propres.

**Tableau 1.** Seuil et justesse au seuil d'une lame d'acier uniforme de 700 Hz
dans une chambre de 10,2 cm³, quand la section du trou déplace la résonance de la
chambre (petit réseau avec les longueurs effectives d'Elmer ; des tendances, pas
des pascals).

| S (mm²) | f_H (Hz) | f_H/f₁ | p_on (Pa) | justesse (cents) |
|---:|---:|---:|---:|---:|
| 21,7 | 700 | 1,0 | silence | — |
| 27,7 | 770 | 1,1 | 4155 | −144 |
| 35,0 | 840 | 1,2 | 453 | −36 |
| 54,1 | 980 | 1,4 | 234 | −17 |
| 98,8 | 1190 | 1,7 | 227 | −9 |
| 176,2 | 1400 | 2,0 | 350 | −6 |

Appliquée au R12 avec des notes hypothétiques (un rang diatonique en sol, pas
encore confirmé), la fenêtre n'est atteignable avec des cotes usinables que pour
les chambres 8 à 10. Les chambres graves, 1 à 7, ont des résonances de 2,4 à
7,8 fois leurs notes et demanderaient une chambre énorme ou un trou minuscule ;
pour elles la proposition se contente d'éloigner la résonance d'au moins
50 cents des harmoniques 1 à 6 des notes, pour qu'elle ne tire ni la justesse ni
le timbre, et trois chambres (3, 4 et 7) ont leur mode A-contre-B à moins de
20 cents d'un harmonique. Les deux chambres les plus aiguës portent une note
au-dessus de leur résonance, qui ne démarre pas dans le modèle ; la chambre 12
demanderait un volume plus petit que les bornes ne le permettent. Tout cela est
une proposition écrite dans un fichier, rien n'a été changé dans le dessin, et
les notes sont une hypothèse : dès que les vraies notes sont dans
`notes_r12.csv`, tout se recalcule seul.

Deux remarques sur ce que le plan ne peut pas voir. Dans ce réseau le poussé et
le tiré donnent les mêmes taux de croissance, parce que la chaîne est
symétrique ; le modèle ne distingue pas la languette intérieure, dans la case, de
l'extérieure. Et la position de la fente sur la plaque est centrée par défaut, la
pointe de la languette ni vers le trou ni vers le fond : une dimension à mesurer.

*À compléter (Ewen) : les vraies notes des douze chambres du R12
(`notes_r12.csv`), et les vraies dimensions d'un trou de la table d'harmonie et
d'un clapet, au pied à coulisse. Sans elles, le tableau 1 est une tendance sur
un instrument imaginé.*

#### Application : la technique du bend [Application : Bend technics]

Un bend est une note tirée hors de sa hauteur par le joueur, avec les mains ou
le soufflet, et ramenée. Sur une anche libre les leviers sont peu nombreux, et
les modèles de ce travail les nomment.

Le premier levier est la pression. Dans toutes les versions des modèles qui
démarrent, la note baisse quand le joueur pousse plus fort : le modèle à une
anche donne −15,7 cents de 1,3 à 2 fois le seuil, et le réseau à deux anches
quelques cents sous la lame au seuil, descendant encore avec la pression. C'est
le sens que connaît tout joueur. Les nombres sont des prédictions de modèles dont
l'amplitude n'est pas encore bornée correctement ; le signe est robuste.

Le second levier est la chambre, et là le tableau 1 est le guide. Une chambre
accordée loin au-dessus de la languette, comme le sont toutes les chambres
graves du R12, tire à peine la note : dans le plan la justesse bouge d'un ou deux
cents entre 300 et 2000 Pa quand la résonance vaut 1,3 fois la note. Une chambre
accordée près de la languette tire fort : à un rapport de 1,02 la même lame joue
84 cents bas au seuil et 97 cents bas à 2000 Pa, mais son seuil est monté de 208
à 1322 Pa. Une chambre qui bend est une chambre dure à souffler, dans le modèle.
L'expérience à la pâte à modeler (E4 de l'audit, diviser par deux une chambre
loin de la résonance) prédit un démarrage un peu plus difficile et presque
aucun changement de justesse ; elle teste le même point par l'autre côté.

Le troisième levier est le chemin d'air au-dessus de la languette, trou et
clapet. Dans la version du réseau à deux anches avec la section qui se ferme, la
masse d'air de ce chemin fait partie du moteur : divisée par dix, la languette
ne démarre pas ; multipliée par trois, elle démarre moins bien. Un clapet à
moitié fermé change cette masse. Qu'il change aussi la hauteur de plus que le
dixième de cent que l'accordeur de ce travail résout, on ne le sait pas.

*À compléter (Ewen) : au banc, une languette à pression fixe, l'angle du clapet
balayé sur ses huit pas (le facteur Clapet du plan d'expériences), la justesse
lue à l'accordeur en cents à chaque pas. Puis la même chose avec l'escalier de
pression du protocole de soufflerie, en montant et en descendant. Deux courbes,
une après-midi.*

## Chapitre — Le couplage des anches [Reed coupling]

Une languette n'est jamais seule. Elle est couplée à sa plaque, la plaque au
sommier, le sommier à la table d'harmonie, et par l'air à l'autre languette de sa
note. Ce chapitre prend ces couplages un à un, du pot de cire à la paire de voix
qui battent.

### Cire ou clous ? ou… [Wax or nails ? or ...]

De la cire chaude coulée autour de la plaque, ou des clous enfoncés à travers
elle dans le bois avec une bande de cuir dessous : les deux manières de fixer
une plaque ont leurs partisans. Que fait la fixation à la languette ? Deux
choses, en principe. Elle rend la plaque étanche contre le sommier, et elle fixe
la condition aux limites de la plaque, qui est le sol sur lequel la languette
est encastrée.

Sur le second point ce travail a un nombre, et il concerne la languette, pas la
plaque. Dans Elmer, remplacer un encastrement idéal de la languette par le vrai,
un talon appuyé par dessous au rivet, abaisse la première fréquence de 0,3 pour
cent, environ 5 cents. La plaque elle-même est rigide dans tous les modèles de
ce travail ; une plaque tenue seulement par la cire à ses bords peut fléchir, et
rien ici n'a calculé ni mesuré de combien.

Sur le premier point, l'étanchéité, le chiffre est encore le critère d'atelier
proposé : un sommier avec ses plaques, nu ou garni, sous 0,05 litre par minute à
500 Pa. Une fuite au bord d'une plaque est une seconde fente en parallèle avec
la languette ; l'atelier en connaît les symptômes, la pression qui tombe avant la
note et l'attaque molle, et parfois une note voisine qui sonne faiblement sans
qu'on la joue.

*À compléter (Ewen) : une plaque, pincée trois fois cirée et trois fois clouée,
en alternance, avec la chaîne du chapitre 2 (micro à 15 cm, gain fixe,
`pince_modes.py`). La fréquence se mesure à mieux que 0,3 cent et
l'amortissement à 3 pour cent sur des sons de synthèse, mais remonter une plaque
déplace la fréquence de plus que le décalage de la chambre elle-même, d'où
l'alternance. La fixation change-t-elle l'amortissement du premier mode ?
Quelle plaque ?*

### Sommier collé ou vissé [Glued reed block or wise]

Le titre garde un mot français : vis. Un sommier collé sur la table d'harmonie
contre un sommier tenu par des vis, avec un joint entre les deux. Le sommier
collé est étanche par nature et ne se démonte pas ; le sommier vissé se démonte
pour l'accordage et compte sur son joint. La physique de ce travail n'a encore
rien pour comparer les deux, mais elle a le test qui le ferait.

Le test est celui qu'Ewen fait déjà à la table d'accordage, écrit ici pour être
refait pareil. Le sommier est sur la table à pression fixe, toujours la même
pour un type de sommier donné, 500 Pa par exemple ; le débitmètre lit l'air qui
passe. Dix lectures en cinq secondes donnent le débit libre et son écart. Puis
un doigt ou un poids appuie sur le joint, toujours au même endroit avec la même
force, et après trois secondes dix lectures donnent le débit appuyé. La
différence est la fuite de ce joint, en litres par minute. On prend trois
couples, et le joint fuit si la différence dépasse trois fois l'écart au repos
dans les trois. Ce que le test ne voit pas, c'est une fuite ailleurs, que le
doigt ne ferme pas ; pour tout le sommier le test de chute de pression du banc
donne la fuite globale, et l'annexe sur la détection des fuites donne les
moyens d'en localiser une.

*À compléter (Ewen) : la fuite à 500 Pa d'un sommier collé et d'un sommier vissé
du même instrument, par le test ci-dessus. Et une question à laquelle toi seul
peux répondre : quand un sommier vissé est démonté et remonté, une languette
change-t-elle de hauteur de plus que les quelques cents dont la chambre
elle-même la décale ?*

### Montage parallèle ou perpendiculaire [Parallel or perpendicular design]

Les plaques peuvent être couchées sur la table d'harmonie, parallèles à elle, ou
dressées sur les cloisons d'un sommier, perpendiculaires à elle, ce qui est le
montage courant. Ce qui change, c'est la forme de la chambre derrière chaque
languette et le chemin de la fente au trou. La méthode du chapitre 2 est faite
exactement pour cette comparaison, puisque l'impédance d'entrée vue de la fente
se calcule sur n'importe quelle géométrie dessinée ; mais seul le montage
perpendiculaire, le sommier R12, a été dessiné et calculé. Une géométrie de
languette et de cavité dessinée par Ewen en 2020 (le projet Elmer
`Reed_with_cav`, FreeCAD, quatre corps) n'a jamais été calculée, aucun solveur
n'y étant actif ; elle est gardée, non comme doublon mais comme point de départ
de l'autre montage.

Un résultat du chapitre 2 pèse sur le choix sans le trancher. Ce que la
languette sent à sa fréquence, c'est l'inertie de l'air qui s'échappe par le
trou, pas la raideur de la cavité. Une plaque à plat avec un chemin court vers
son trou et une plaque dressée avec une longue case derrière elle donneront à la
languette des masses d'air différentes, et le tableau 1 dit que la masse, par la
résonance qu'elle fixe, déplace le seuil et la justesse. Quel montage est le
meilleur est donc une question de là où tombe sa résonance, et cela se calcule
en quelques minutes dès que le dessin existe.

*À compléter (Ewen) : les cotes d'une chambre à plat d'un instrument que tu as,
pour qu'Elmer donne son impédance vue de la fente à côté de celle d'une chambre
dressée du R12.*

### Associer des anches en parallèle / en série [Associate reeds in parallel / series]

Une note d'accordéon en accord musette, ce sont deux languettes, parfois trois,
qui prennent leur air au même soufflet et le rendent par le même clapet. Elles
partagent l'air, et elles se parlent par lui. C'est l'association en parallèle,
et c'est toute la raison d'être du réseau à deux anches `coupled_reeds` : deux
languettes, deux chambres, deux trous, un canal sous le clapet, un clapet. Le
canal commun aux deux est le couplage ; une option met les deux languettes dans
la même chambre pour le couplage le plus fort.

La première chose que le réseau a apprise, c'est où doit se trouver le moteur de
chaque languette. Dans une version le démarrage des languettes était porté par
une résistance partagée au clapet ; les deux voix se verrouillaient alors à
l'unisson jusqu'à 80 cents de désaccord, ce qu'aucune musette réelle ne fait,
puisqu'une musette bat. Avec le moteur propre à chaque languette, les voix
désaccordées de 20 cents battent à 1,209 Hz, l'écart des lames (1,21 Hz). Le
canal commun couple les voix, mais faiblement ; l'excitation d'une languette lui
est propre.

Ce que le réseau prédit, dans ses deux versions successives, c'est que les voix
se tirent près de l'unisson. Avec le premier mécanisme (la grave de référence,
300 Pa, 4 s), le battement entendu est 27 pour cent plus lent que l'écart des
lames à 1 cent de désaccord, 20 pour cent à 2 cents, 12 pour cent à 3, et égal
à lui à partir de 5 cents. Avec le mécanisme de la section qui se ferme (la4,
1000 Pa), les deux voix se verrouillent sur une fréquence jusqu'à environ
2 cents de désaccord (0,6 Hz), battent 12 pour cent trop lentement à 5 cents, et
librement à 20 cents. Près du verrouillage le battement n'est pas l'écart des
lames mais √(Δ² − Δ_L²), où Δ est le désaccord et Δ_L la plage de verrouillage,
la loi d'Adler pour deux oscillateurs couplés ; le réseau la reproduit sans qu'on
la lui ait dite. C'est la physique derrière un geste de l'accordeur : deux voix
accordées assez près se collent, et la musette meurt. L'accordeur de ce travail
(`web/`) sépare les deux languettes d'une note en une demi-seconde et lit leur
battement ; l'expérience E3 de l'audit accorde une languette l'autre bloquée,
puis la libère, et lit si le battement survit.

Deux autres prédictions, toutes deux conditionnées à des dimensions devinées :
l'air ne double pas avec deux languettes (1,56 fois le débit d'une seule dans la
première version, presque le double, moins 4 pour cent, dans la seconde), et
deux languettes en phase rayonnent mieux qu'une (rendement 2,9·10⁻⁵ contre
1,5·10⁻⁵, nombres à ne pas croire en valeur absolue, voir la section sur le
rayonnement).

L'association en série, une languette qui passe l'air à une autre par une
cavité partagée, n'a pas été modélisée comme telle. Ce qui s'en approche le plus
est le modèle de la pile de supports de l'audit (`slot_stack.py`), construit
pour les essais d'Ewen où une languette plate découpée dans une tôle d'acier et
prise entre deux plaques joue dans les deux sens, et où deux plaques d'harmonium
montées tête-à-tête jouent aussi dans les deux sens. Ce modèle est honnête sur
son échec : il reproduit le montage ordinaire et refuse de faire jouer le
sandwich, ce qui veut dire que le vrai mécanisme contient quelque chose qu'il
n'a pas, un retard de l'écoulement au bord de la languette et une pression qui
n'est pas uniforme le long d'elle. Une association en série de languettes sera
comprise quand ce mécanisme le sera.

*À compléter (Ewen) : l'expérience E3 sur une note musette de ton instrument,
avec l'accordeur : accorder une languette l'autre bloquée par une bande de
papier, la libérer, lire le battement en battements par minute à 1, 2, 3 et
5 cents de désaccord. Le battement disparaît-il sous environ 2 cents, comme le
dit le modèle ? Et le sandwich : ses cotes, la note pincée de la lame, la note
jouée dans chaque sens en fonction de la pression au tube en U.*

### La dissipation dans les cavités [Dissipation in cavities]

Où va l'énergie ? Une languette pincée dans l'air sonne des secondes : son
propre amortissement est petit, un taux d'amortissement de 0,004 est la valeur
devinée des modèles, à mesurer par le geste (a) du chapitre 2. Soufflée, la même
languette s'installe dans un cycle d'amplitude fixe en une seconde ou deux :
quelque chose prend de l'énergie à chaque cycle aussi vite que le souffle en
donne. Dans le réseau à deux anches ce quelque chose est nommé : les pertes
d'orifice du trou et du clapet, ρ·q|q|/(2·(C_d·S)²). C'est là que le mouvement
ordonné de l'air devient chaleur, et c'est cette perte qui borne l'amplitude
dans le réseau, sans aucune résistance réglée à la main.

La théorie linéaire explique une chose que le facteur voit sans la nommer. Une
chambre n'aide la languette que si son impédance, à la fréquence de jeu, est
dominée par sa compliance, de sorte que la pression retarde sur le débit d'un
quart de période et que la force sur la languette a une part en phase avec sa
vitesse. Un vrai trou ventile la chambre : sa résonance est au-dessus de tout le
clavier, l'impédance est inertielle presque partout, et la chambre amortit au
lieu d'aider. C'est pourquoi le réseau honnête, avec les vraies pertes et
l'ancienne loi d'ouverture, ne démarrait pas du tout : le taux de croissance
restait négatif quoi qu'on ajoute, à l'amortissement de la lame seule,
−2,64 par seconde, ou plus bas. C'est aussi cohérent avec la mesure de Ricot,
Caussé et Misdariis, qui ont montré qu'une anche d'accordéon démarre même sans
aucun couplage acoustique, par l'aérodynamique de l'écoulement dans sa fente. La
chambre n'est pas le moteur ; le moteur est dans la fente, et la chambre
surtout prend.

Dans la fente elle-même les pertes sont visqueuses, et cela a été vérifié par un
calcul d'écoulement. Dans un jeu de 30 micromètres entre languette et plaque le
nombre de Reynolds est d'environ 80 : l'écoulement est un écoulement de
Poiseuille, pas un jet, et la loi de Bernoulli seule y est fausse. Sur une coupe
en deux dimensions de l'anche en sandwich, Elmer a trouvé que 80 pour cent de la
chute de pression dans ce jeu est visqueuse, et son débit s'accordait à 0,4 pour
cent avec la loi à une dimension, Poiseuille plus Bernoulli, de
`slot_stack.py`. L'air de la fente répond en une microseconde environ, deux mille
fois plus vite qu'une période de la languette, donc l'écoulement dans la fente
est pris comme instantané ; seul l'air que la languette entraîne garde son
inertie, comme masse ajoutée.

Le modèle par éléments finis de la chambre n'a aucune perte, et le dit. La
résistance d'une vraie chambre vient du geste (b) : un résonateur de facteur de
qualité 20, qui est l'ordre utilisé dans les tests de synthèse, perd 40 dB en
25 ms, et l'analyse retrouve son amortissement à 5 pour cent. Au banc, une fuite
se voit comme une chute du facteur de qualité des résonances d'air de
l'instrument fermé, mesurée par un balayage (`frf.py`) et un ring-down ; elle ne
localise pas la fuite mais elle la quantifie.

*À compléter (Ewen) : le facteur de qualité d'une chambre du R12, fermée par sa
plaque, excitée par un balayage d'un petit haut-parleur et enregistrée à 15 cm,
avec et sans la plaque cirée. La résistance de perte qui manque aux modèles,
c'est ce seul nombre.*

## Chapitre — Entropie et état de moindre énergie [Entropy and least energy state]

La question 3 de l'introduction demande si les anches travaillent dans un état
de moindre énergie. La réponse courte de ce travail est non, et la réponse
longue est plus intéressante qu'un oui ne l'aurait été.

Une languette au repos dans sa fente, sans air qui bouge, est dans son état de
moindre énergie : le ressort de la lame est détendu, l'air est immobile. Une
languette qui chante n'est pas dans un tel état. C'est un état stationnaire
tenu en vie par un flux d'énergie : le soufflet donne du travail au rythme de la
pression fois le débit, les orifices et le jeu visqueux transforment presque tout
en chaleur, et une infime part ordonnée s'en va en son. Les modèles de ce
travail mettent cette part entre quelques cent-millièmes et quelques pour cent,
et ne croient ni l'un ni l'autre. Ce qui est sûr, c'est l'architecture : un
oscillateur tenu loin du repos par une source, borné par la dissipation. Un tel
état s'appelle un cycle limite ; c'est un état d'équilibre, pas de minimum.

L'équilibre peut s'écrire. Linéarisé autour de l'équilibre d'une languette tenue
ouverte par la pression, le débit par la fente rétroagit sur la languette avec
un retard fixé par la compliance de la chambre, et la force de pression acquiert
une part en phase avec la vitesse. Dans le modèle à une anche cet
anti-amortissement vaut

    Γ·a·(∂q_out/∂y) / [ (a·∂q_out/∂p)² + ω² ],   a = γ·P_atm / V₀,

où Γ est la surface balayée par la languette, a la raideur du ressort d'air dans
une chambre de volume V₀, ∂q_out/∂y la modulation du débit par la position de
la languette, ∂q_out/∂p sa dépendance à la pression, et ω la pulsation. La
languette démarre quand ce terme dépasse son propre amortissement, 2ζωm, avec ζ
le taux d'amortissement et m la masse modale. La formule dit aussi quand elle
s'arrête : si l'ouverture sature parce que la languette est soufflée hors de sa
fente, la modulation ∂q_out/∂y s'annule et l'anti-amortissement avec elle,
quelle que soit la pression. C'est l'étouffement que connaît tout joueur, et le
modèle l'a produit sans qu'on le lui demande. L'oscillation est bornée des deux
côtés, par trop peu d'énergie et par trop.

Ce que le facteur minimise n'est pas une énergie mais une pression : celle à
laquelle la languette démarre. Le tableau 1 a montré que le seuil est le plus bas
quand la résonance de la chambre se tient 1,2 à 1,7 fois au-dessus de la note.
Le facteur qui trouve cette fenêtre à l'oreille fait ce que le plan
d'expériences fait par le calcul : rendre l'état d'oscillation auto-entretenue
atteignable avec le moins de souffle.

L'entropie entre dans ce travail en deux endroits, et les deux sont modestes. Le
premier est le mot adiabatique. L'air d'une chambre est comprimé et détendu des
centaines de fois par seconde, trop vite pour échanger de la chaleur avec les
parois ; son entropie reste constante pendant un cycle, et c'est pourquoi le
ressort d'air a la raideur γ·P_atm/V et non P_atm/V. Le second, ce sont les
orifices, où l'entropie est produite : l'énergie cinétique d'un jet qui a passé
un trou n'est pas récupérée de l'autre côté, elle devient chaleur, et le terme
ρ·q|q|/(2·(C_d·S)²) est le compte de cette irréversibilité.

Il y a un troisième endroit où l'idée d'un état de moindre quelque chose
revient, et c'est celui qui compte le plus pour ce livre. Entre la pression où
la languette démarre, p_on, et la pression plus basse où elle s'arrête, p_off,
deux états coexistent : la languette muette et la languette qui chante. Dans le
modèle à une anche le rapport p_on/p_off est sorti à 1,33 (25,8 Pa sur 19,4 Pa,
pour une version du modèle dont les seuils sont connus pour être trop bas dans
le grave) ; le banc mesure les mêmes deux pressions par une rampe montante et
une rampe descendante (`seuil.py`). Aucun des deux états n'est l'état de moindre
quelque chose ; celui où la languette se trouve dépend d'où elle vient. Les
outils du chapitre stochastique du banc de recherche voient cela comme un
potentiel à deux puits, reconstruit à partir de la dérive et de la diffusion
mesurées du signal, et le bruit du souffle comme ce qui peut pousser le système
par-dessus la barrière d'un puits à l'autre. Une anche ne cherche pas sa
moindre énergie. Elle reste où elle est jusqu'à ce que quelque chose, pression
ou bruit, la déplace.

*À compléter (Ewen) : le rapport d'hystérésis d'une vraie languette, par
l'escalier du protocole de soufflerie, en montant puis en descendant, trois
cycles. Si le rapport mesuré est loin de 1,33, le volume effectif et l'impédance
de source sont les deux premiers paramètres à recaler.*

---

# Partie III — Mécanique et soupapes [Mechanics and valves]

L'air qui ne chante pas est le sujet de cette partie. Un accordéon est une boîte
de pression, et chacun de ses joints est un endroit où l'air peut partir sans un
son. Les soupapes, les joints, les clapets et les touches qui les soulèvent
décident de la part du souffle qui arrive aux languettes, et à quelle vitesse.

## Chapitre — Fuites, canaux d'air et soupapes [Leaks, flow channels and valves]

Une soupape, dans la langue de l'atelier, est la peau de cuir ou de plastique
collée sur la fente d'une languette du côté d'où l'air ne vient pas. Quand la
plaque est soufflée par l'autre côté, la peau se soulève et la languette joue ;
quand l'air vient de son côté, la peau ferme la fente de la languette qui doit
rester muette, pour que l'air du soufflet ne se perde pas par elle. La soupape
est la raison pour laquelle une plaque à deux languettes donne une note en poussé
et une en tiré. Dans les modèles de ce travail elle n'apparaît que comme
hypothèse : le débit par la fente est à sens unique, la soupape est parfaite.
L'audit dit ce qui est ignoré : une soupape de cuir a une masse, elle fuit, et
elle claque. Dans le protocole expérimental du chapitre 2 la soupape de la
languette testée est enlevée ou relevée, parce que, couchée sur la fente côté
chambre, elle découplerait la chambre ; le protocole liste la soupape comme un
facteur à part entière, dans aucun modèle encore.

Les chiffres de ce chapitre viennent du livret de stage d'Ewen et de sa
pratique d'atelier. Ce sont des critères proposés, pas encore mesurés sur ses
instruments, et ils sont donnés avec ce statut. Une soupape doit fuir moins de
0,02 litre par minute sous 500 Pa, et aucune soupape ne doit décoller sous
1,5 fois la pression maximale de jeu. Le soufflet seul doit fuir moins de
1 litre par minute à 500 Pa, un sommier collé nu ou garni moins de 0,05, et
l'instrument fermé moins de 0,5. Le tableau 2 traduit une fuite en trou : à
500 Pa, un trou rond de 1 mm laisse passer 0,8 litre par minute. Ces débits
suivent la loi d'un orifice avec un coefficient de contraction proche de 0,6, la
valeur 0,61 employée dans les modèles pour un jet à arête vive ; la vérification
a été faite ici, les chiffres sont ceux du livret.

**Tableau 2.** Trou équivalent d'une fuite à 500 Pa (chiffres d'atelier,
critères proposés).

| diamètre du trou (mm) | fuite (litre par minute) |
|---:|---:|
| 0,3 | 0,07 |
| 0,5 | 0,2 |
| 1 | 0,8 |
| 2 | 3,3 |

Deux instruments ne coûtent rien. Un gazomètre est une boîte retournée qui
flotte dans un seau d'eau : remplie d'air, elle alimente l'instrument et
descend à mesure que l'air fuit, et pour la boîte de l'atelier une descente de
6,7 cm par minute vaut 1 litre par minute. Un tube en U de tuyau transparent à
moitié rempli d'eau et une règle font un manomètre : 1 mm d'eau vaut environ
10 Pa (9,81 Pa exactement). Avec ces deux-là, les critères ci-dessus se
vérifient sur n'importe quel instrument.

Ce qu'une fuite fait à la musique est connu de l'atelier et expliqué par le
réseau. Une fuite en parallèle avec les languettes prend du débit à une source
de résistance finie, donc la pression tombe avant la note : l'attaque est molle,
et un pianissimo part mal. Une soupape qui fuit laisse passer l'air par la fente
de la languette muette de sa plaque, et si cette languette est proche de son
seuil elle sonne faiblement : la note fantôme.

### Transmittance acoustique des soupapes [Acoustic transmittance of valves]

Une soupape fermée, un clapet fermé, une sourdine : chacun est une paroi mince
entre une cavité pleine de son et le dehors. La part du son qui la traverse est
sa transmittance, écrite d'habitude comme une perte par transmission en
décibels. Rien dans ce travail n'en a encore mesuré une ; la méthode et le
logiciel sont prêts, et ils sont bon marché.

La manière rigoureuse est la méthode de la matrice de transfert à quatre
microphones (norme ASTM E2611) : un tube, l'échantillon au milieu, deux micros
en amont et deux en aval, et deux terminaisons différentes pour que les quatre
coefficients de la matrice se séparent. La perte par transmission suit de la
matrice par TL = 20·log₁₀(|T₁₁ + T₁₂/ρc + ρc·T₂₁ + T₂₂|/2) pour un tube de
section constante et un bout anéchoïque, où T₁₁ à T₂₂ sont les quatre
coefficients et ρc l'impédance caractéristique de l'air
(`banc_recherche/transfer.py`, `transfer_matrix_two_load` et `tl_from_matrix`).
La manière bon marché utilise les deux micros du tube d'impédance et compare
les spectres amont et aval, TL = 10·log₁₀(S_in/S_out), une estimation grossière,
honnête de l'être. La carte son a trois voies ; la méthode à quatre micros
demanderait une seconde passe en déplaçant les micros, ou une seconde carte.

Une chose que les modèles disent déjà de la soupape ne concerne pas la
transmittance mais la hauteur, et elle mérite une place ici parce qu'elle est
surprenante. Dans l'audit du modèle à une anche, une ouverture symétrique en la
position de la languette, S = b·|y|, modulait la fente deux fois par période et
le modèle jouait 470 Hz pour une languette de 220 Hz : une octave faux. Le
débit par une anche libre est à sens unique, et dans la lecture des modèles
c'est la soupape qui le rend tel. Que la vraie languette se comporte ainsi sans
sa soupape est une question pour les essais du sandwich, où une languette sans
aucune soupape joue dans les deux sens ; le point demeure que la soupape n'est
pas un accessoire de la plaque mais une partie de ce qui fixe la note.

*À compléter (Ewen) : la perte par transmission d'une soupape de cuir et d'une
soupape de plastique collées sur une plaque, dans un tube à deux micros, par la
méthode grossière d'abord. Une différence de quelques décibels entre les deux
matériaux serait déjà un résultat.*

### Influence du matériau d'étanchéité sur le son rayonné [Sealing material influence of sound radiated]

Cuir ou plastique pour les soupapes, feutre ou mousse pour les joints, cire ou
cuir sous les plaques : les matériaux d'étanchéité se choisissent à la main et
se jugent à l'oreille. Leur influence sur le son rayonné est de deux sortes, et
la seconde est celle qu'on oublie d'habitude.

La première sorte, c'est ce que le matériau laisse passer quand il est censé
fermer. Une fuite est un endroit où l'air s'échappe sans faire de note, et elle
n'est pas silencieuse : un jet par un petit orifice sous pression devient
turbulent et rayonne un sifflement large bande qui monte haut en fréquence,
jusque dans l'ultrason. Dans un enregistrement, le sifflement d'une fuite est
riche là où la voix de la languette et le bruit de la pièce sont pauvres,
au-dessus de quelques kilohertz. C'est la poignée par laquelle l'annexe sur la
détection des fuites l'attrape : filtrer haut, prendre l'enveloppe du
sifflement, et, si la pression du soufflet est modulée à une fréquence lente
connue, ne garder que ce qui clignote à cette fréquence. Le soufflet du banc, qui
fait déjà des courses contrôlées à 2 à 10 Hz, est le modulateur ; la détection
synchrone tient en quelques lignes de code (`banc_recherche/leak.py`, `lockin`
et `leak_map`) ; un micro promené sur la surface donne une carte. Rien de tout
cela n'a encore tourné sur un vrai instrument.

La seconde sorte, c'est ce que le matériau fait quand il bouge. Une soupape se
soulève et retombe à chaque changement de sens du soufflet ; elle a une masse et
elle claque. Les modèles l'ignorent, et l'accordeur de ce travail détecte
l'inversion du soufflet par un creux net et isolé du signal sans silence, qui
est là où vit le claquement. Une soupape de plastique raide et une de cuir
souple ne retomberont pas de la même façon, et l'attaque de la note après
l'inversion porte la différence. Rien ici ne l'a mesurée.

*À compléter (Ewen) : la même note enregistrée avec sa soupape de cuir, puis
avec une de plastique, à la même pression de soufflet, avec l'export WAV de
l'accordeur ; comparer les spectres au-dessus de 4 kHz pendant la note tenue
(le sifflement) et les 50 premières millisecondes après une inversion (le
claquement). Quelle note, et quel instrument ?*

### Dynamique du clavier [Dynamics of keyboard]

Une touche soulève un clapet. Le clapet est la dernière porte du chemin d'air,
et dans le réseau c'est un orifice : une masse d'air ρ·ℓ/S et une perte, avec
des dimensions devinées de 3 cm² de section, 10 mm de longueur effective et une
levée d'environ 4 mm. Au banc c'est un axe en degrés, balayé de 2 à 22 degrés
dans le plan de 2020 avec un levier de 20 mm, ou remplacé par un clapet fixe et
une électrovanne temporisée quand seule l'arrivée de la pression compte. Le
clavier du banc est une matrice d'électro-aimants sur les boutons, 24 à la main
gauche et 47 à la main droite, maintenus à courant réduit une fois enfoncés ; le
firmware qui le pilote est écrit pour un ESP32-S3 et n'a pas encore été testé
sur le matériel.

Ce que la vitesse de la touche fait à la note est une question de montée de
pression. Dans les simulations la pression du soufflet monte linéairement en
20 ms, une hypothèse sans mesure derrière ; une touche lente donne à la
languette une montée lente et une attaque molle, une touche rapide une marche.
Le temps de réponse de la note, de l'ouverture au son établi, est déjà mesuré
par la chaîne d'analyse du banc de recherche (la grandeur appelée Tresp,
calculée avec Praat par Parselmouth) ; ce qui manque, c'est la position de la
touche en fonction du temps à côté.

Il y a un point plus fin, et c'est une prédiction. Dans la version du réseau à
deux anches avec la section qui se ferme, la masse d'air du chemin au-dessus de
la languette, trou et clapet ensemble, fait partie du mécanisme de démarrage :
cette masse divisée par dix, la languette ne démarre pas, multipliée par trois,
elle démarre moins bien, et il existe un optimum. Un clapet à peine ouvert est
un passage long et mince et une grande masse d'air ; un clapet grand ouvert une
petite. Si la prédiction tient, l'enfoncement de la touche change la facilité du
démarrage, pas seulement la force. L'expérience E2 de l'audit est faite pour le
voir : la pression de démarrage, lue au tube en U, en fonction de la levée du
clapet.

*À compléter (Ewen) : la force et la course d'une touche, avec une cellule de
charge (HX711) et un petit codeur magnétique (AS5600) sur le banc, une nouvelle
voie du firmware proposée dans la carte des mesures mais pas construite. Et
l'expérience E2 : la pression de démarrage d'une languette pour cinq levées de
son clapet, réglées avec des cales. Y a-t-il un optimum, comme le dit le
modèle ?*

### Pédale avec enclenchement manuel de notes type stylo bille

Le titre décrit un dispositif : une pédale, ou un verrou manœuvré à la main, qui
tient une note ouverte comme le bouton d'un stylo à bille tient sa pointe
sortie, une pression pour engager et une pour relâcher. Le but musical est un
bourdon, une note qui continue de sonner pendant que les doigts sont libres. Le
dessin est celui d'Ewen et n'est pas dans le dépôt ; ce qui est ici, c'est ce que
la physique des chapitres précédents dit d'une telle note.

Un clapet verrouillé est une ouverture constante. La languette derrière lui ne
dépend alors que d'une chose, la pression du soufflet, et cette pression est
partagée avec toutes les autres notes jouées. L'audit du modèle à une anche
prend comme hypothèse de travail que le soufflet est une source de débit à
résistance interne finie, pas une source de pression, et en donne la preuve dans
le jeu : à vitesse de soufflet constante, ouvrir un accord fait tomber la
pression, là où une source de pression la tiendrait et doublerait le débit. Un
bourdon coûte donc de la pression à la mélodie, et le coût est le débit de la
languette du bourdon fois la résistance de la source. Les débits que les
modèles donnent par languette (0,1 à 0,4 litre par seconde à 1000 Pa) sont
connus pour être trop grands ; le vrai se lit au débitmètre du banc en une
minute.

La seconde chose que dit la physique concerne les deux sens. Une note
verrouillée sur une plaque à deux languettes fait sonner une languette en
poussé et l'autre en tiré, et les deux languettes d'une plaque sont deux lames
différentes : sur l'instrument d'Ewen lui-même l'accordeur a trouvé des écarts
de 15 à 25 cents entre poussé et tiré sur les mêmes notes. Un bourdon qui doit
rester juste à travers l'inversion du soufflet demande que les deux languettes
de sa plaque soient accordées ensemble plus soigneusement que la mélodie ne le
demande.

*À compléter (Ewen) : le mécanisme lui-même, et sa question pour le banc :
combien de débit la languette du bourdon prend à la pression de jeu, et de
combien la pression disponible pour les autres notes tombe quand il est
verrouillé, mesuré avec le débitmètre et le capteur de pression, ou le tube en
U.*

### Bend en bout de course du clavier

Le second titre nomme une touche avec une course supplémentaire : enfoncée au
bout de sa course ordinaire, la touche ouvre le clapet, et enfoncée plus loin,
elle fait quelque chose de plus, qui bend la note. Que peut être ce quelque
chose ? Les modèles de ce travail nomment trois leviers, dans la sous-section
sur la technique du bend plus haut, et ici ils sont pesés pour une touche.

La touche ne peut pas changer la pression du soufflet ; ce levier appartient au
bras. Elle peut changer l'ouverture du clapet : au-delà de la course ordinaire
elle peut le refermer en partie, ou ouvrir un second passage, plus petit. Dans
le réseau à deux anches cela change la masse d'air du chemin au-dessus de la
languette, que le modèle place dans le mécanisme de démarrage, et l'effet sur la
hauteur n'est pas connu : il peut être sous ce que l'oreille remarque. La touche
peut aussi changer la chambre : un second clapet en bout de course pourrait
ouvrir une case à côté de la chambre, changeant son volume et sa résonance. Le
tableau 1 dit que ce levier n'est fort que quand la résonance de la chambre est
proche de la note, dans un rapport de 1,1 environ, et qu'une telle chambre est
dure à souffler : 1322 Pa de seuil contre 208 Pa à un rapport de 1,3, pour la
même lame dans le plan. Un bend en bout de course est donc, dans le modèle, un
échange entre la profondeur du bend et la facilité de la note, et seule une
mesure dira où l'échange vaut la peine.

*À compléter (Ewen) : le mécanisme que tu as en tête, et une mesure avant de le
construire : avec de la pâte à modeler, réduire le volume d'une chambre en deux
ou trois pas et lire la hauteur de sa languette à l'accordeur à une pression
fixe de l'escalier. Si la hauteur bouge de moins de quelques cents, la chambre
n'est pas le levier pour cette note, et c'est le clapet qu'il faut essayer.*

---

# Partie IV — Couplage du sommier à la table et à la caisse [Reedblock to {Soundboard+box} coupling]

Le sommier ne flotte pas. Il se tient sur la table d'harmonie, et la table
d'harmonie est une paroi de la caisse. Tout ce que la languette fait à l'air,
l'air le fait à ces pièces de bois, et elles répondent. Cette partie a un
chapitre, et c'est surtout une liste de ce qui n'a pas encore été mesuré, avec
la seule chose qui l'a été.

## Chapitre — La table d'harmonie [Soundboard]

La table d'harmonie est la planche sur laquelle le sommier se tient et dans
laquelle les trous des chambres sont percés ; les clapets reposent sur son autre
face. Dans tous les modèles de ce travail elle est rigide, et elle n'entre que
par ses trous. C'est déjà beaucoup : le trou est la partie de la chambre que la
languette sent le plus. Sa longueur effective, calculée par Elmer à partir de
l'impédance vue de la fente, est de 25,8 mm pour la chambre 1, 22,7 mm pour la
chambre 6 et 30,4 mm pour la chambre 12, contre une épaisseur réelle de 8 mm
dans le dessin. Les deux tiers de ce que la languette sent comme masse du trou
sont l'air à ses deux bouts, et le clapet, quand il est près du trou, l'allonge
encore ; le modèle par éléments finis met le clapet loin, et c'est un paramètre
à balayer.

Un petit balayage sur la chambre 1 montre combien le trou pèse. En gardant les
cases et en ne changeant que le trou, la première résonance va de 665 Hz (trou
4 par 12,5 mm, table 8 mm, grande correction extérieure) à 1314 Hz (trou 8 par
25 mm, table 4 mm, petite correction). Un facteur quatre sur la section et un
facteur deux sur l'épaisseur déplacent la résonance d'une octave ; le volume de
la chambre, auquel le facteur pense d'habitude en premier, n'a pas été touché.

La table d'harmonie comme plaque vibrante est absente de ce travail, et la
caisse aussi. L'hypothèse du réseau que le clapet est le seul rayonneur est
incomplète, comme le dit l'audit : le soufflet, la caisse et la plaque
rayonnent aussi. Combien, et à quelles fréquences, c'est une mesure qui coûte
un marteau d'impact (un manche de tournevis fera l'affaire), un accéléromètre
piézo de quelques euros collé sur la table, et la troisième voie de la carte
son : la réponse en fréquence du coup à l'accélération donne les modes de la
plaque, leurs fréquences et leur amortissement, avec les mêmes estimateurs que
le banc de recherche emploie déjà pour les languettes (l'inter-spectre de
`excitation.py`, le ring-down et le Matrix Pencil).

*À compléter (Ewen) : la réponse en fréquence de la table d'harmonie d'un
instrument, sommier monté et sommier démonté, au marteau et à l'accéléromètre.
La question à trancher est simple : un mode de la plaque tombe-t-il à quelques
pour cent d'une note de l'instrument, ou de la résonance d'une chambre ? Si
aucun, la table rigide des modèles est une hypothèse honnête pour cet
instrument.*

---

# Partie V — Les autres pièces en jeu [Other parts involved]

Le soufflet qui respire, la grille que le son traverse, la caisse qui tient
tout, les clapets et les sourdines : le reste de l'instrument. Chacun apparaît
dans ce travail comme une hypothèse des modèles, et cette partie dit laquelle,
et ce qui la remplacerait par une mesure.

## Chapitre — Le soufflet [Bellows]

Le soufflet est le poumon. Tout ce qui est en amont de la languette est en lui :
la pression, sa montée, sa chute, son inversion. Les modèles de ce travail le
traitent de la façon la plus simple, et le banc le remplace par un moteur.

### Le soufflet à cadre [Framed bellow]

Un soufflet à cadre, ce sont des plis de carton et de toile, du cuir aux coins,
et un cadre de bois à chaque bout qui reçoit le sommier et la caisse. L'atelier
sait où il fuit : aux coins et au cadre. Le critère proposé du livret est moins
de 1 litre par minute à 500 Pa pour le soufflet seul, fermé sur une planche, ce
qui, par le tableau 2, est l'équivalent d'un trou rond d'un peu plus de 1 mm.

Qu'est-ce que le soufflet pour la languette ? Dans le réseau à deux anches c'est
une source de pression idéale qui monte en 20 ms, une hypothèse sans mesure.
Dans le modèle à une anche c'est une source de débit à résistance interne,
q = q₀ − p/R, et l'audit soutient à partir du jeu que c'est la bonne image : un
vrai soufflet, comme une vraie turbine, donne moins de débit quand la pression
monte. La valeur de R décide de l'amplitude de la note (section sur l'ouverture)
et déplace le seuil : dans une version du modèle à une anche la pression de
démarrage de la languette de référence était de 23,0 Pa avec une source idéale,
25,8 Pa avec R = 2·10⁸ et 35,9 Pa avec 5·10⁷ Pa·s/m³, une source plus molle
aidant moins le démarrage, tandis que la pression d'étouffement restait à
379,8 Pa. Ce sont les nombres d'une version du modèle dont les seuils graves
sont connus pour être bien trop bas ; le sens de l'effet est ce qu'il faut
garder.

Les pressions de jeu d'un accordéon sont de l'ordre de 500 à 3000 Pa, dans les
deux signes ; les seuils des languettes sont loin en dessous, quelques dizaines
à quelques centaines de pascals dans les modèles, là où un vrai instrument en
demande à peu près une centaine à un millier sur tout le clavier. Le soufflet a
aussi une souplesse propre et la main derrière ; l'audit dit que les deux se
mesurent au manomètre et qu'aucun n'est dans un modèle.

Au banc le soufflet est motorisé : un axe pas-à-pas sur une table linéaire, la
seule source d'air, piloté à vitesse donnée ou asservi à une pression,
s'inversant aux bouts de sa course finie de sorte qu'une mesure se fait dans une
passe, poussé et tiré étant les deux signes de pression. Le banc ne marche pas
pour l'instant et n'a jamais été refait ; le firmware existe et n'est pas testé ;
le débitmètre est toujours là. Le même soufflet motorisé est le modulateur de la
méthode d'imagerie de fuite de l'annexe, à 2 à 10 Hz.

*À compléter (Ewen) : deux mesures sur un de tes soufflets, fermé sur une
planche avec une prise de pression. La fuite à 500 Pa, au gazomètre ou au
débitmètre, contre le 1 litre par minute du livret. Et la caractéristique de ton
propre bras comme source : pression en fonction du débit à poussée régulière,
par un orifice connu, lue au tube en U et au gazomètre ; sa pente est le R des
modèles. Quel soufflet, quel jour ?*

## Chapitre — Les éléments de timbre [Timbral elements]

Une fois que la languette a fait le son, plusieurs pièces de l'instrument le
façonnent avant qu'il atteigne l'oreille. Ce chapitre les liste, dit ce que la
physique de ce travail prédirait pour chacune, et admet qu'aucune n'a été
mesurée ici.

### La grille [Grid]

La grille est l'écran percé devant les clapets de la main droite. Le son de
chaque languette la traverse. Physiquement c'est une plaque à beaucoup de trous
et une mince couche d'air derrière : à basse fréquence elle est transparente,
puisque la longueur d'onde est longue devant les trous et la profondeur ; vers
les hautes fréquences les trous agissent comme des masses d'air et la couche
derrière comme un ressort, et la grille devient un filtre dont la coupure
dépend de la fraction de surface ouverte et de la profondeur. Rien dans ce
travail n'a calculé ni mesuré une grille, et aucun nombre n'est donné ici.

*À compléter (Ewen) : une note enregistrée grille posée et grille enlevée,
même position de micro, même pression de soufflet, avec l'export WAV de
l'accordeur ; comparer les deux spectres au-dessus de 2 kHz. La différence, s'il
y en a une, c'est la grille.*

### La caisse de résonance [Resonance box]

Certains instruments mettent un jeu de languettes derrière une seconde chambre
à l'intérieur de la caisse, une caisse de résonance, qui leur donne leur son
plus rond. Physiquement c'est une cavité de plus sur le chemin de l'air, et la
méthode du chapitre 2 s'y applique sans changement : mailler son air, calculer
ses modes et l'impédance vue du trou du sommier. Une prudence : une caisse de
résonance fait plusieurs centimètres, et à un ou deux kilohertz ce n'est plus
petit devant la longueur d'onde ; le réseau à constantes localisées de masses et
de ressorts cesse d'y être valable, alors que le modèle par éléments finis s'en
moque, ayant été vérifié sur un conduit de 100 mm contre la formule exacte à
une erreur relative de 1,3·10⁻⁵. Aucune caisse de résonance n'a été dessinée ni
calculée dans ce travail.

*À compléter (Ewen) : les cotes de la caisse de résonance d'un instrument que tu
peux ouvrir, et l'enregistrement d'une languette à travers elle et hors d'elle,
pour que les modes calculés soient mis en face du spectre mesuré.*

### Clapets et sourdines

Le clapet est la porte de chaque note, et il a eu son mot à dire plusieurs fois
dans ce livre : un orifice de dimensions devinées dans le réseau, le seul
rayonneur du modèle, la masse d'air que le modèle met dans le mécanisme de
démarrage, le dernier endroit où la touche agit. Les tiroirs de registre, qui
ferment des jeux entiers de languettes, sont de la même famille, et l'atelier
les compte parmi les endroits qui fuient. Une sourdine est n'importe quoi,
feutre, bois ou tissu, placé sur le chemin du son pour l'adoucir : un passage
plus long et plus étroit, donc plus de masse d'air et plus de perte, donc moins
d'aigu et un peu moins de tout.

Ce qui est dit des soupapes dans le chapitre sur les fuites s'applique aux
deux : leur transmittance se mesure dans un tube à deux ou quatre micros, le
logiciel est prêt, le montage ne l'est pas. Ce que les modèles prédisent pour le
clapet, un optimum de sa levée pour la facilité du démarrage, c'est
l'expérience E2 et elle n'est pas mesurée.

*À compléter (Ewen) : la perte par transmission d'un tiroir de registre, fermé,
dans le tube à deux micros, par la méthode grossière de `transfer.py`. Et la
levée de tes clapets à touche enfoncée, à la cale d'épaisseur : les 4 mm du
modèle sont une supposition.*
