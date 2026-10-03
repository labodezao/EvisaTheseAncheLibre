# Fuites d'air : un protocole à chaque étape de fabrication

> Écrit le 03/10/2026 pour Ewen. Complète `fuites_air_methodes.md` (les
> méthodes de recherche : lock-in, BOS, Q) par la pratique d'atelier : quoi
> mesurer, avec quoi, dans quel ordre, et quel chiffre viser.
> Bon marché d'abord. Rien d'inventé : les chiffres « proposés » sont à
> étalonner sur les instruments d'Ewen.

## 1. Pourquoi une fuite gâche le jeu (ce qui est sûr, ce qui est probable)

- **Sûr** : chaque fuite consomme de l'air. Le soufflet bouge plus pour le même
  son : plus d'inversions, plus de fatigue.
- **Sûr** : un instrument étanche peut être **mis en pression avant la note**
  (le soufflet tient, on appuie, rien ne bouge). Quand la soupape s'ouvre,
  l'anche reçoit d'un coup toute la pression : l'attaque est franche. Avec une
  fuite, la pression retombe dès qu'on ne pousse plus ; à l'attaque, elle
  repart de presque rien : transitoire mou.
- **Sûr (physique de l'anche)** : une anche démarre à `p_on` mais peut tenir
  jusqu'à `p_off`, plus bas (hystérésis). Le pianissimo le plus doux s'obtient
  en attaquant juste au-dessus de `p_on`. Si la pression d'attaque est
  imprécise (fuite), l'anche ne part pas, ou part trop fort.
- **Probable** : une fuite **près de l'anche** (cire, peau qui ne ferme pas,
  soupape d'à côté) se met en parallèle de l'anche, derrière la soupape et le
  canal : elle fait chuter la pression que l'anche voit vraiment. C'est au
  pianissimo, tout près du seuil, que ça se sent le plus.
- **Probable** : une soupape voisine qui fuit alimente une autre chambre :
  souffle, ou note fantôme quand on pousse fort.

## 2. Un langage commun : le débit de fuite à 500 Pa

- **500 Pa** ≈ 5 cm d'eau ≈ un mezzo-forte. On mesure aussi à 1 500 Pa
  (fortissimo) quand c'est possible.
- On dit la fuite en **L/min à 500 Pa**, et en **trou équivalent** :

  | trou rond | à 100 Pa | à 500 Pa | à 1 500 Pa |
  |---|---|---|---|
  | 0,3 mm | 0,03 L/min | 0,07 L/min | 0,13 L/min |
  | 0,5 mm | 0,09 | 0,20 | 0,35 |
  | 1 mm | 0,37 | 0,82 | 1,4 |
  | 2 mm | 1,5 | 3,3 | 5,7 |

  (orifice, coefficient de débit 0,6 ; `leak.hole_leak_lpm`)
- **Le type de fuite** se lit dans la loi débit-pression `q ∝ p^n` :
  `n ≈ 0,5` = un trou ou une fente courte ; `n ≈ 1` = pores, bois de bout,
  peau, colle poreuse, fente longue. Il suffit de mesurer à deux pressions
  (`leak.leak_flow_curve` le fait sur une chute de pression).

## 3. Le matériel (presque gratuit)

| Objet | Rôle | Prix |
|---|---|---|
| Tube en U en tuyau transparent, eau + goutte de liquide vaisselle, règle | lire la pression (1 mm = 9,81 Pa) | 0 à 3 € |
| **Gazomètre de cuisine** : boîte plastique retournée (~150 cm²) flottant dans un seau d'eau, guidée, lestée | pression constante + débit lu à la règle | 0 € |
| Tuyau silicone 4 mm d'aquarium, raccords en T, robinets 3 voies, clapets | tout raccorder | 5 à 10 € le lot |
| Seringue 60 mL ou poire de tensiomètre | gonfler, aspirer | 1 à 8 € |
| Bâton d'encens | voir l'air sortir (fumée) | 1 € |
| Tuyau à l'oreille (stéthoscope de mécanicien improvisé) | entendre un sifflement | 0 € |
| Plaques d'obturation, cloches, embouts imprimés en 3D (PETG) + mousse EPDM adhésive 3 mm | fermer une pièce, isoler une soupape | quelques € |
| Plaque à trous percés 0,3 / 0,5 / 1 mm | **fuites étalons** : vérifier le banc | 0 € |
| ESP32 + BMP280 (déjà là) ou SDP810-500Pa (25 à 35 €) | chute de pression, cloche, mesure continue | |

**Jamais de flamme** (bougie, briquet) : celluloïd, bois, colle, peau.
**Pas d'eau savonneuse sur le bois, la peau, le carton** : seulement sur métal,
plastique, joints caoutchouc.

## 4. Les montages

### Le gazomètre de cuisine (constant, absolu, sans électronique)

Une boîte retournée flotte dans l'eau, guidée par deux tiges. Sa masse fixe la
pression : `p = m·g / S`. Pour S = 150 cm² et 500 Pa : **m ≈ 0,77 kg** (boîte
comprise). Un tuyau passe sous l'eau et relie l'air de la boîte à la pièce
testée. La pièce fuit : la boîte descend.

- **Débit = S × vitesse de descente.** Avec 150 cm² : **1 L/min = 6,7 cm par
  minute ; 0,1 L/min = 6,7 mm par minute.**
- C'est le **test de chute du soufflet**, en petit. Et le test de chute du
  soufflet, c'est un gazomètre : il suffit de le chiffrer (§ 5, étape 6).
- On s'en sert aussi pour mesurer **le débit d'une anche** : on retire la bande
  qui la bloquait, on lit la descente. C'est la consommation d'air de l'anche
  à cette pression.

### Le tube en U

Deux branches de tuyau transparent sur une planchette graduée. L'écart des
niveaux en millimètres × 9,81 = Pa. Il sert à étalonner tout capteur.

### La chute de pression (ESP32, commande `LEAKTEST`)

Pièce fermée + **volume tampon connu** (bouteille de 1,5 L ou bidon de 5 L) ;
on gonfle à ~600 Pa, on ferme, on enregistre. Avec le volume total, l'onglet
Banc (champ « volume fermé ») et `leak.leak_flow_curve` donnent le débit à
500 Pa, le trou équivalent et `n`.

L'air est un ressort très raide : un petit volume se vide en une fraction de
seconde. D'où le tampon. Temps de chute de 500 à 400 Pa (`leak.decay_time_s`) :

| fuite à 500 Pa | volume 0,2 L | 1,5 L | 5 L |
|---|---|---|---|
| 0,05 L/min | 0,25 s | 1,9 s | 6,3 s |
| 0,1 L/min | 0,13 s | 0,9 s | 3,1 s |
| 0,5 L/min | 0,03 s | 0,2 s | 0,6 s |

Règle simple : **avec une bouteille de 1,5 L, si la pression met plus de 2 s
pour passer de 500 à 400 Pa, la pièce fuit moins de 0,05 L/min.** À 30 % près
(échanges de chaleur) : vérifier avec une fuite étalon.

Pour un instrument entier (≈ 8 L), une fuite de 10 L/min vide la pression en
quelques centièmes de seconde : la chute de pression ne marche pas, c'est le
gazomètre (le soufflet chargé) qui marche.

### La cloche d'accumulation (une soupape à la fois)

Une cloche (pot de 0,4 L, bord en mousse) posée **côté extérieur** sur une
soupape fermée, l'instrument sous pression `P` dedans. La fuite remplit la
cloche : sa pression monte. Un tuyau la relie au tube en U (ou au capteur).

Temps pour atteindre `P/2` (fuite de type orifice) :
`t½ ≈ 0,59 · V · P / (p_atm · Q)`. Avec 0,4 L et 500 Pa : **0,02 L/min → 3,5 s ;
0,002 L/min → 35 s.** Une soupape qui fait monter la cloche à mi-pression en
moins de 3 s fuit plus que 0,02 L/min. `leak.accumulation_flow` donne le débit
par la pente.

### Localiser (une fois qu'on sait que ça fuit)

1. **Fumée d'encens** passée le long des joints, pièce sous pression : la fumée
   est chassée. Ou pièce en dépression : la fumée est aspirée.
2. **Tuyau à l'oreille**, promené à 5 mm des joints, pièce à 1 500 Pa ou plus
   (le bruit d'un jet turbulent croît comme la vitesse puissance 6 à 8,
   Lighthill, soit la pression puissance 3 à 4 : ×3 en pression = +14 à +19 dB).
3. **Micro + détection synchrone** (`fuites_air_methodes.md` § 1) : le soufflet
   motorisé module la pression, le micro promené fait la carte.
4. Bulles de savon : seulement sur métal et plastique.
5. Optionnel : un récepteur ultrason 40 kHz (celui d'un HC-SR04, 1 à 2 €) avec
   un petit montage hétérodyne, ou un détecteur de chauves-souris en kit (15 à
   25 €). Utile surtout pour les toutes petites fuites, à pression élevée.

## 5. Les étapes, dans l'ordre

| # | Étape | Montage | Mesure | Critère proposé (à 500 Pa) |
|---|---|---|---|---|
| 0 | Le banc lui-même | plaque d'obturation sur une vitre, puis fuites étalons | zéro, puis 0,3 / 0,5 / 1 mm | zéro < 0,01 L/min ; étalons à ±20 % |
| 1 | Sommier collé, nu | plaques d'obturation sur les faces ouvertes | gazomètre ; localiser à la fumée | < 0,05 L/min par sommier (< trou de 0,4 mm) |
| 2 | Sommier + plaques d'anches (cire ou vis), fentes bloquées au ruban | idem | idem, dans les deux sens (pression et aspiration) | < 0,05 L/min ; sinon cire, planéité, vis |
| 2 bis | Débit de chaque anche | retirer un ruban à la fois | descente du gazomètre à 100, 300, 500 Pa | c'est une **mesure**, pas un critère : le débit consommé |
| 3 | Table d'harmonie + soupapes | caisson de test sous pression côté sommiers | cloche sur chaque soupape ; monter la pression jusqu'au **décollement** | ≤ 0,02 L/min par soupape ; aucune ne décolle sous 1,5 × la pression maximale de jeu |
| 4 | Caisse assemblée (cadres, mécanique, tirettes de registres) | demi-caisse fermée par une planche au cadre du soufflet | gazomètre ; fumée | < 0,5 L/min |
| 5 | Soufflet seul | deux planches à joint aux cadres | sa propre chute avec une masse connue ; fumée aux coins | < 1 L/min |
| 6 | Instrument complet | soupape d'air fermée, masse connue, prise de pression par un tube | **chute chiffrée** : vitesse × surface efficace, poussé et tiré | voir ci-dessous |

### L'étape 6 en chiffres (le test de chute qu'on fait déjà)

- On suspend l'instrument, une masse connue tire le soufflet, soupape d'air
  fermée, aucune touche.
- On lit la pression (tube en U par la soupape d'air, ou capteur) et l'ouverture
  du soufflet dans le temps (règle et vidéo du téléphone, ou capteur de distance
  VL53L0X, 3 à 5 €).
- **Surface efficace** `S = m·g / p` ; **débit de fuite** `Q = S × vitesse`.
  Deux masses donnent deux pressions, donc `n`.

Ordres de grandeur, pour un soufflet qui balaie 10 L sous ~600 Pa :

| chute complète en | fuite | trou équivalent |
|---|---|---|
| 30 s | 20 L/min | 4,7 mm |
| 60 s | 10 L/min | 3,3 mm |
| 2 min | 5 L/min | 2,4 mm |
| 5 min | 2 L/min | 1,5 mm |

Ce que disent les praticiens (forums et guides de réparation, pas des études) :
moins de 20 à 30 s, il y a une fuite franche à chercher ; un bon instrument
tient au moins 30 s ; un très bon, une minute ou plus.

**Proposition à étalonner** : une anche aiguë au pianissimo consomme
probablement de l'ordre de **1 à 2 L/min** (estimation : aire efficace de 1 à
3 mm² sous 100 Pa ; à mesurer à l'étape 2 bis). Une fuite de 10 L/min (la
« bonne » chute d'une minute) en vaut 4 sous 100 Pa : **plus que l'anche
elle-même**. D'où deux niveaux :

- **niveau « atelier »** : ≤ 10 L/min à 600 Pa (chute de 10 L en plus d'une minute) ;
- **niveau « pianissimo »** : ≤ 2 à 3 L/min (chute en 3 à 5 minutes).

Pour fixer le vrai chiffre : mesurer de la même façon **deux ou trois
instruments qu'Ewen connaît** (un qu'il juge excellent, un médiocre), et pour
chacun le pianissimo le plus doux qu'on obtient sur une note aiguë (niveau au
micro, à distance fixe). Le seuil se place entre les deux.

## 6. Noter chaque essai

Une ligne par mesure (Wenou OS, onglet Expériences, ou le tiroir « Essais et
expériences » du coffre) : date, pièce, étape, pression, montage, débit, trou
équivalent, `n`, ce qui a été corrigé, débit après correction.

## Références et sources

- EN 1779 (Essais non destructifs. Contrôle d'étanchéité. Critères de choix de
  la méthode et de la technique) et EN 13184 (méthode par variation de
  pression) : le cadre industriel (méthode par variation de pression, fuites
  étalons). Normes payantes, non lues en entier : seul leur objet est cité.
- Le test de chute et ses durées : guides de réparation et forums de
  praticiens (par exemple muzicalinstruments.com, « How to Detect an Accordion
  Air Leak » ; accordionists.info, fil « Bellows check »). Ce sont des usages
  d'atelier, pas des mesures publiées.
- M. J. Elejalde-García, E. Macho-Stadler, R. Llanos-Vázquez (2021), Accordion
  acoustics: a study on pitch bending, *Acoustics in Practice* AiP-2021-02
  (EAA) : quand le passage de l'air se rétrécit (soupape à demi ouverte), la
  note baisse et le niveau baisse.
