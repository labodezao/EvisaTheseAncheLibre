# Seuils d'auto-entretien : mesurer où l'anche démarre, s'éteint et se plaque

> Terme de Bernard Bonin. But d'Ewen : **la plage de jeu la plus grande avec le
> seuil le plus bas**, réglage de levée par réglage de levée, pour dimensionner
> les sommiers. Écrit le 03/10/2026.

## Les quatre pressions d'une anche

On monte la pression lentement, puis on redescend.

| Nom | Quand | Ce que ça dit au musicien |
|---|---|---|
| `p_on` (démarre) | en montée, l'anche se met à sonner | le pianissimo le plus doux qu'on peut **attaquer** |
| `p_choke` (se plaque) | en montée, elle se tait alors que la pression monte encore | le fortissimo maximal |
| `p_unchoke` (repart) | en descente, après le plaquage, elle resonne | il faut relâcher jusque-là pour la retrouver |
| `p_off` (s'éteint) | en descente, elle se tait | le pianissimo le plus doux qu'on peut **tenir** |

- **Hystérésis** `p_on - p_off` : si elle est positive, on peut tenir une note
  plus doucement qu'on ne peut l'attaquer. La zone entre `p_off` et `p_on`
  n'est accessible qu'en partant plus fort.
- **Plage utile** `p_choke - p_on`, et **rapport** `p_choke / p_on`.

## Comment l'application décide que « l'anche sonne »

Deux indices à la fois (sinon le souffle, qui monte aussi avec la pression,
passerait pour une note) :

1. le son est **périodique** : clarté NSDF ≥ 0,8 (McLeod et Wyvill, 2005 ;
   le souffle reste sous 0,5) ;
2. le niveau dépasse le **fond de souffle** de 6 dB au moins.

Un changement d'état ne compte que s'il dure 0,15 s (anti-rebond).

## Le matériel

| Quoi | Pour | Prix indicatif |
|---|---|---|
| ESP32-S3 + firmware du banc | lire la pression, piloter la rampe | déjà là |
| BMP280 (déjà là), filtre IIR réglé à 0, 2 ou 4 | pression relative après tare | déjà là |
| ou mieux : Sensirion SDP810-500Pa (I2C, 0x25) | pression différentielle rapide, sans dérive | 25 à 35 € |
| tube en U avec de l'eau + règle | étalonner le capteur (1 mm d'eau = 9,81 Pa) | 0 à 3 € |
| débit : SFM3000 (s'il existe encore), ou vitesse du soufflet × surface, ou diaphragme + capteur différentiel | consommation d'air | 0 à 35 € |
| micro (celui de l'accordeur), place fixe | niveau sonore relatif | déjà là |

La pression doit être lue **au plus près de l'anche** : dans la chambre, par un
petit tube. Pas à la soufflerie (le passage de la soupape fait chuter la
pression).

## Le protocole (une anche)

1. Lancer l'accordeur (micro). Connecter le banc (onglet **Banc**). **Tare**.
2. Carte **Seuils d'auto-entretien** : nommer l'essai (ex. « Mi5 levée 0,6 »).
3. Choisir la source :
   - **manuelle** : on fait la rampe soi-même (soufflerie et vanne, ou soufflet
     joué très lentement) ;
   - **rampe asservie** : l'application envoie des consignes `PRESSURE` en
     triangle (par exemple de 0 à 800 Pa à 10 Pa/s, 3 cycles).
4. **Enregistrer**, monter au-delà du plaquage si possible, redescendre jusqu'au
   silence. **Arrêter et calculer**.
5. **Export CSV**. Puis, sur le PC : `banc-recherche-cli seuils fichier.csv --png fig.png`.

Règles :

- **Deux vitesses de rampe** (par exemple 5 et 20 Pa/s). Deux défauts décalent un
  seuil mesuré en rampe, tous deux proportionnels à la vitesse : le retard du
  capteur (il **cache** l'hystérésis) et le retard à la bifurcation (il la
  **gonfle** ; Bergeot et coll. 2013). La droite seuil(vitesse) prolongée à
  vitesse nulle donne le vrai seuil (`seuil.zero_rate_threshold`).
- **3 cycles au moins** : le seuil d'une anche est **distribué** (bruit), on
  donne moyenne et écart-type.
- **Noter la source** : un soufflet poussé à force constante est une source de
  pression ; un soufflet motorisé à vitesse constante est une source de débit.
  Les seuils ne sont pas les mêmes (le modèle du dépôt le montre :
  `audit_modele_anche.md`, « effet de l'impédance de source »).
- Noter la température (l'acier s'assouplit en chauffant).

## Deux anches ensemble

Le plus sûr, sans calcul : **une bande de papier** bloque l'anche B, on mesure
A ; on bloque A, on mesure B ; puis les deux. `seuil.compare_pair` dit si la
paire démarre plus tôt (la chambre les couple, elles s'aident) ou plus tard
(elles se gênent), et si elle consomme plus ou moins que la somme des deux.

`seuil.reed_presence` sépare les deux anches dans un seul enregistrement
quand leurs fréquences sont assez éloignées (fenêtre ≥ 2 / écart en Hz). Pour
une musette serrée, la fenêtre devient longue (0,7 s pour 3 Hz d'écart) : la
méthode de la bande de papier reste meilleure.

## Plan d'expérience proposé (levée)

| | |
|---|---|
| Facteurs | levée (3 niveaux : basse, normale, haute) ; anche (grave, médium, aigu) |
| Réponses | `p_on`, `p_off`, `p_choke`, `p_unchoke`, plage, débit à 300 Pa, niveau à 300 Pa |
| Répétitions | 3 cycles × 2 vitesses de rampe |
| Durée | environ 2 h pour 9 combinaisons |
| Ce qui contredirait l'hypothèse | si `p_on` ne bouge pas avec la levée, ou si la plage ne dépend pas de la masse de l'anche (voir le rapport de physique) |

La levée se mesure au pied à coulisse (profondeur) ou à la cale d'épaisseur, en
bout d'anche, avant et après chaque essai.

## Où est le code

- `research/banc_recherche/seuil.py` : `frame_features` (niveau, clarté, f0),
  `oscillating`, `ramp_thresholds`, `cycles_thresholds`, `zero_rate_threshold`,
  `bin_curve`, `flow_law`, `effective_area_mm2`, `efficiency_db`,
  `reed_presence`, `compare_pair`, `analyse_run`, `read_bench_csv`.
  Tests : `research/tests/test_seuils_rampe.py`.
- `web/js/seuils.js` (même logique, pour l'application) et la carte de
  l'onglet Banc (`web/js/bench.js`). Tests : `test/seuils.test.mjs`.
- Firmware : `drivers/sdp8xx.py` (optionnel, `ADDR_SDP`), `BMP280_IIR`.

## Références

- A. O. St Hilaire, T. A. Wilson, G. S. Beavers (1971), Aerodynamic excitation
  of the harmonium reed, *J. Fluid Mech.* 49(4), 803-816.
- D. Ricot, R. Caussé, N. Misdariis (2005), Aerodynamic excitation and sound
  production of blown-closed free reeds without acoustic coupling: the example
  of the accordion reed, *J. Acoust. Soc. Am.* 117(4), 2279-2290,
  doi:10.1121/1.1852546.
- B. Bergeot, A. Almeida, C. Vergez, B. Gazengel (2013), Prediction of the
  dynamic oscillation threshold in a clarinet model with a linearly increasing
  blowing pressure, *Nonlinear Dynamics* 73, 521-534.
- P. McLeod, G. Wyvill (2005), A smarter way to find pitch, *Proc. ICMC*.
