# Audit du modèle à deux anches (`coupled_reeds.py`)

Règle de cet audit : **aucun élément n'est accepté parce qu'il est publié.**
Chacun est classé selon d'où il vient, et ce qui n'est ni dérivé ni mesuré
est dit tel quel. Les articles cités ailleurs dans le dépôt (Ricot et al.
2005, Millot & Baumann 2007) ont servi d'**idée de départ**, pas de preuve :
aucun résultat ci-dessous ne repose sur leur autorité, et leurs hypothèses
ne sont pas reprises sans vérification.

Légende :
- **Dérivé** — conséquence directe de lois physiques de base (conservation
  de la masse, Newton, Bernoulli…), avec ses conditions de validité ;
- **Vérifié ici** — contrôlé numériquement ou sur un cas connu ;
- **Hypothèse** — choix de modélisation, plausible mais **non vérifié** ;
- **Deviné** — valeur posée faute de mesure : à remplacer ;
- **Emprunté** — repris d'un résultat publié, **non vérifié par nous**.

---

## 1. Ce qui fait démarrer l'anche — démontré dans le modèle, sans article

Dérivation (linéarisation autour du régime permanent, notations du code) :

- débit par l'écart : `q = α·S(y)·√(2Δp/ρ)` ;
- l'air du chemin (trou, canal, clapet) a une masse `L = ρℓ/S` : une variation
  de débit `δq` y crée `δp = −L·dδq/dt` (en poussé, du côté aval) ;
- si la section **diminue** quand la languette avance (`dS/dy < 0`), une
  avance `δy` réduit le débit, et `L` transforme ce ralentissement en une
  surpression **en phase avec la vitesse** `ẏ` : une force qui relance ;
- à l'inverse, si la section **augmente** quand la languette avance
  (ancienne loi), la même masse d'air freine : amortissement.

Prédiction, faite **avant** la vérification : l'anche démarre avec (1) une
section qui se ferme quand elle avance et (2) une masse d'air sur le chemin,
et il existe une masse optimale (trop de masse découple la languette du
débit). Vérification dans le modèle, une chose retirée à la fois (La4,
1000 Pa, croissance de l'amplitude ; la lame seule s'amortit à −11,1 /s) :

| cas | croissance |
|---|---|
| référence | **+19,0 /s** |
| sans volume balayé par la languette | +19,6 /s |
| sans fente en série (hypothèse §3.4) | +19,7 /s |
| masse d'air du chemin ÷ 10 | −8,4 /s — ne démarre pas |
| masse d'air du chemin × 3 | +4,4 /s — démarre moins bien |
| chambre ÷ 4 / × 4 | +17,3 / +25,2 /s |
| loi « ouverte par le souffle » | −16,3 /s — ne démarre pas |

Les deux ingrédients prédits sont les seuls qui comptent, et l'optimum de
masse est là. **Ce qui n'est PAS démontré** : que la vraie anche fonctionne
ainsi. C'est une prédiction, à confronter aux expériences du §5.

La question qui ne se tranche pas dans un ordinateur, et que toi seul peux
trancher sur l'instrument : **au repos, la pointe de la languette est-elle
levée du côté d'où vient l'air, de sorte que le souffle la pousse d'abord
DANS la fente ?** Tout le modèle repose sur ce point de géométrie.

---

## 2. Vérifications numériques (faites ici)

| élément | contrôle | résultat |
|---|---|---|
| intégrateur RK4 suréchantillonné | pas de 10,4 → 1,3 µs | jeu 437,499 Hz, course 4,174 mm, débit 417,0 cm³/s : identiques à 4 chiffres |
| `dominant_frequency` | sinusoïdes 437,123 et 110,5 Hz | 437,123 / 110,500 |
| `beat_hz` (dérive de phase) | deux sinusoïdes 440 / 441,3 Hz | 1,300 Hz |
| `radiated_power` | débit sinusoïdal connu, formule ρω²Q²/(4πc) | 2,1277·10⁻⁵ contre 2,1279·10⁻⁵ W |

Les outils de mesure du modèle sont justes ; les chiffres qu'ils sortent ne
valent que ce que valent les hypothèses ci-dessous.

---

## 3. Élément par élément

### 3.1 La languette

| élément | origine | statut | réserve |
|---|---|---|---|
| poutre d'Euler-Bernoulli encastrée-libre | dérivé | valide si épaisseur ≪ longueur (0,3 mm / 24 mm : oui) | — |
| **un seul mode** | hypothèse | non vérifié | le 2ᵉ mode (≈ 6,3 f₁) compte dans l'attaque et le timbre ; ignoré |
| lame **uniforme** (`steel_reed`) | hypothèse | faux pour une vraie lame | une vraie lame est profilée — c'est précisément ce que tu grattes. Sa longueur calculée n'est pas sa longueur réelle |
| encastrement parfait | hypothèse | non vérifié | le rivet n'est pas parfait : fréquence réelle plus basse |
| E = 210 GPa, ρ = 7800 kg/m³ | valeurs d'acier usuelles | plausible | acier à ressort : à vérifier par la fréquence de la lame pincée |
| amortissement ζ = 0,004 | **deviné** | non mesuré | mesurable (§5, E5) |
| force = `Δp` uniforme sur toute la face | **hypothèse** | non vérifié | près de l'écart l'air accélère, la pression n'y est pas uniforme ; la répartition réelle est inconnue |

### 3.2 L'écoulement dans l'écart

| élément | origine | statut | réserve |
|---|---|---|---|
| Bernoulli quasi-stationnaire | dérivé, si l'écoulement suit sans retard : nombre de Strouhal f·h/v ≈ 440 × 0,5 mm / 40 m/s ≈ 0,006 ≪ 1 | justifié par l'ordre de grandeur | — |
| **dans le jeu latéral (30 µm)** | — | **invalide** | Reynolds ≈ v·h/ν ≈ 40 × 3·10⁻⁵ / 1,5·10⁻⁵ ≈ 80 : la viscosité y domine, Bernoulli n'est pas le bon régime (écoulement de Poiseuille) |
| contraction α = 0,61 | emprunté (jet 2D stationnaire à arête vive) | non vérifié pour un écart qui oscille | mesurable (§5, E6) |
| débit dans un seul sens (soupape parfaite) | hypothèse | non vérifié | la soupape de cuir a sa masse, fuit, claque ; ignoré |

### 3.3 La section de passage (le cœur du mécanisme)

| élément | origine | statut | réserve |
|---|---|---|---|
| au-dessus de la plaque → dedans → ressortie | géométrie observable | **à confirmer par toi** (§1) | tout en dépend |
| hauteur au bout seulement ; les côtés comptent pour 0,39 × longueur | **simplification de ma part** | grossier | faux près de l'encastrement, où la languette reste dans la plaque quand le bout en sort. À remplacer par l'intégrale le long de la lame, avec le vrai profil de levée |
| levée = 1,5 × épaisseur, plaque = 3 × épaisseur (`steel_reed`) | **deviné** | aucune base | à mesurer (cales, pied à coulisse) |
| jeu latéral 30 µm | **deviné** | — | à mesurer (cale ou lumière rasante) |

### 3.4 La fente en série — mon ajout

Quand la languette est loin de la plaque, l'air est étranglé par la fente
elle-même, en série avec l'écart ; la force sur la languette est alors
réduite à la part de la chute de pression prise par l'écart. **Hypothèse de
ma part, non vérifiée.** Elle ne change pas le démarrage (§1), elle réduit
la course et le débit d'environ 15 %. Interrupteur : `slot_series=False`.

### 3.5 Le chemin de l'air

| élément | origine | statut | réserve |
|---|---|---|---|
| chambre = compliance V/(γP) | dérivé (air adiabatique, chambre ≪ longueur d'onde : 3 cm ≪ 78 cm à 440 Hz) | valide pour le fondamental | limite vers 5 kHz |
| trou, clapet = masse ρℓ/S + perte d'orifice | dérivé (air incompressible dans un conduit court) | valide | — |
| corrections d'extrémité (≈ 0,8 rayon) | emprunté (conduit circulaire bafflé) | approché pour des trous rectangulaires | — |
| **toutes les dimensions** (chambre 35×15×15 mm, trou 8×25×20 mm, canal 4 cm³, clapet 3 cm² × 10 mm) | **devinées** | aucune mesure | à relever sur ton instrument ; c'est là qu'Elmer peut calculer masses et volumes effectifs d'après la vraie géométrie |
| soufflet = source de pression idéale, montée en 20 ms | hypothèse | non vérifié | le vrai soufflet a sa souplesse et la main ; mesurable au manomètre (§5) |

### 3.6 Le son rayonné

| élément | origine | statut | réserve |
|---|---|---|---|
| monopôle au clapet, ρ/(4πr)·dq/dt | dérivé (petite source, ka ≪ 1) | valide au fondamental (ka ≈ 0,08 à 440 Hz), limite vers 5 kHz (ka ≈ 0,9) | — |
| **seule source : le clapet** | hypothèse | incomplet | le soufflet, la caisse et la plaque rayonnent aussi |
| rendement 1–3 % | sortie du modèle | **suspect** (probablement trop grand) | conséquence des courses trop grandes (§4) |

---

## 4. Ce que le modèle sort, et ce qu'il faut en penser

Ce sont des **prédictions conditionnées aux valeurs devinées**, pas des
faits :

- démarrage de La2 à La5 entre 200 et 1000 Pa, jeu quelques cents sous la
  lame (−4 à −24 ¢), note qui baisse quand on pousse ;
- deux anches La4 à 1000 Pa : verrouillées jusqu'à ~2 ¢ de désaccord,
  battement réduit de 12 % à 5 ¢, libre à 20 ¢ ;
- l'air double presque avec deux anches (−4 %).

**Manifestement faux** : courses de 4–5 mm pour un La4, 0,4 L/s par anche,
rendement de 1–3 %. Quelque chose freine la vraie languette que le modèle
n'a pas (traînée dans le jet ? répartition de pression §3.1 ? section §3.3 ?).
Je ne choisis pas sans mesure.

---

## 5. Expériences pour trancher — sans matériel coûteux

Outils : l'accordeur (téléphone), un **manomètre à eau** (tuyau transparent
en U, une règle : gratuit, 1 mm d'eau ≈ 10 Pa), cales d'épaisseur, pied à
coulisse, pâte à modeler, adhésif.

| # | expérience | ce que le modèle prédit | ce que ça tranche |
|---|---|---|---|
| E1 | fréquence de la lame **pincée** (sans air) puis **jouée** à plusieurs pressions | jouée quelques cents sous la pincée, et qui baisse quand la pression monte | le sens et la taille de l'écart — test direct du mécanisme |
| E2 | pression de démarrage (manomètre) en variant la **levée du clapet** | un optimum : ni trop ouvert, ni trop fermé | le rôle de la masse d'air du chemin (§1) |
| E3 | deux anches d'une note, désaccord faible réglé une à une (l'autre bloquée), puis ensemble | battement qui disparaît sous ~2 ¢ (La4) | le couplage par le canal et le clapet |
| E4 | pâte à modeler dans la chambre (volume ÷ 2) | démarrage un peu plus difficile, justesse presque inchangée | le rôle de la chambre |
| E5 | lame pincée, enregistrée : décroissance | donne ζ | remplace la valeur devinée |
| E6 | levée et jeu mesurés sur quelques anches | — | remplace les valeurs devinées |

E1 et E3 suffisent à contredire le modèle s'il est faux. Le **mode dev** de
l'accordeur (enregistrement WAV + courbe CSV) sert précisément à les garder.

---

## 6. Ce qu'Elmer apporterait — et ce qu'il n'apporterait pas

- **Oui** : calculer, sur la vraie géométrie de la chambre, du trou, du canal
  et du clapet, leurs masses d'air et volumes effectifs et la fréquence de
  Helmholtz (acoustique linéaire, bien maîtrisée). C'est ce qui remplacerait
  les dimensions devinées du §3.5.
- **Non** : le mécanisme de démarrage (écoulement dans l'écart, décollement
  du jet, viscosité dans le jeu) relève de la mécanique des fluides
  instationnaire couplée à la lame — un calcul lourd, dont les résultats
  seraient eux aussi à valider par E1–E3.
