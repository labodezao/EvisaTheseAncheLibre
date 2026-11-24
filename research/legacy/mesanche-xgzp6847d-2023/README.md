# Le banc de mesure de 2023 : le vrai capteur de pression (XGZP6847D)

## D'où ça vient

- `MesAnche_2023-04-07.py`, `xgzp6847d.py`, `testXGZP684D.py`, `mesureancheinit.py` :
  `D:\GoogleDrive\Ingénierie et recherche\Ressources\micropythonn code\` (racine du dossier).
- `MesAnche_2023-03-26_bmp280.py` : même dossier, sous-dossier `mesure Anches\`.
  C'est la version déjà versée dans `research/scripts/legacy/MesAnche.py`.
- `XGZP6847D_brouillon_2023-04-07.py` : sous-dossier `pression\` (premier jet, ne marche pas).
- `sdp810500.py`, `testsdp810500.py`, `sdp810-500pa.py` : décembre 2022, capteur Sensirion
  SDP810-500 Pa (essai précédent).

## Ce que ça change

Le dépôt avait seulement la version du 26/03/2023 de `MesAnche.py`, qui lit un **BMP280**
(pression absolue, environ 1 013 hPa). Les campagnes d'avril et de septembre 2023 ont des
valeurs de 55 à 2 040, qui ne collent pas avec un BMP280.

La version du **07/04/2023** remplace le BMP280 par un **XGZP6847D**, un capteur de pression
**différentielle** (relative à l'air de la pièce). Elle date d'avant les campagnes
`data_d1_L` (13/04/2023), `data_D#0_1_L_2v` (16/04/2023) et `data` (11/09/2023).

Ce que dit le pilote `xgzp6847d.py` :

- `pression = valeur_ADC / 1024` (valeur signée sur 24 bits).
- Le capteur monté est de **−5 à 5 kPa** (confirmé par Ewen). Pour cette gamme la notice du
  fabricant (`pression\XGZP6847D-Pressure-Sensor-V2.5.pdf`, page 9) donne **K = 1024** : l'échelle
  du pilote est juste, et la pression sortie est en **pascals**, à condition de retrancher le zéro
  (voir plus bas). (Une première lecture de la page 10 avait fait croire à une gamme 4 à 8 kPa :
  c'était une erreur, il n'y a pas de facteur à corriger.)
- Au démarrage, le pilote moyenne 80 lectures (`Calc_off`, rangées dans `press_offset`) mais **ne
  retranche pas** ce zéro : `Get_DPress()` rend la valeur brute. `MesAnche` garde de son côté un
  `p0` (une seule lecture). Le fabricant dit qu'un décalage de quelques Pa à vide est normal.
- La « température » enregistrée est celle **de la puce du capteur**, pas celle de l'air.
- Un registre est réglé à la main : `0xA6 = 0x2B` (gain 32, suréchantillonnage 8192). Doute
  secondaire : ce n'est un écart que si l'usine avait posé une autre valeur (non journalisée).

## Ce qui est établi, plausible, à tester

- Établi : le code du 07/04/2023 lit un XGZP6847D de −5 à 5 kPa et le convertit avec K = 1024 ;
  les pressions des campagnes d'avril et de septembre 2023 sont des pascals **une fois le zéro
  retranché**.
- Établi : la campagne `data - e1` (21/01/2023) a été mesurée **avant** ce capteur, avec un
  script qui ne lisait que 2 octets : sa pression (655 partout) n'est pas en pascals. Elle reste à part.
- Plausible : les campagnes d'avril et de septembre 2023 ont été faites avec ce code.
- À tester : le tube en U à eau (1 mm d'eau = 9,8 Pa) en parallèle sur la chambre donnerait le
  zéro et l'échelle d'un coup, lors d'une prochaine mesure.

## Étalonnage a posteriori (24/11/2026)

Lecture seule des enregistrements (`data`, `data_D#0_1_L_2v`, `data_d1_L`, copies du Drive).

- **Le zéro `p0` n'est écrit dans aucun fichier.** `Mes_Full_Mes` ne renvoie que la pression,
  la température de la puce et le débit (6 lignes) : ni `p0` ni `press_offset`.
- **Le zéro ne se retrouve pas essai par essai.** Le clapet s'ouvre à l'échantillon 83 sur 300
  (0,83 s, centiles 5 à 95 : 81 à 84 ; une chute de 30 à 45 % de la pression). Avant l'ouverture
  le ventilateur souffle clapet fermé : la pression lue est celle de la chambre (95 à 2 050 Pa),
  pas celle de l'air libre. La plus basse valeur lue vaut 75 Pa (Si1), 65 (Ré#1 à 2 voix) et
  54,7 (`d1_L`, tout premier essai) ; à la consigne la plus basse du ventilateur, avant ouverture,
  médiane 138 Pa (95 à 145) en Si1 et 132 (93 à 136) en Ré#1. Aucun essai ne montre donc un zéro,
  et la dérive du zéro au fil d'une série n'est pas mesurable.
- **La valeur brute est gardée** : les valeurs sont `ADC / 1024` en flottants 32 bits, donc
  `ADC = valeur × 1024` (entier à l'arrondi près). Ce brut n'a pas son zéro retranché.
- `data_d1_L` : la fin de la ligne pression y contient l'axe du temps (valeurs de 0 à 3) dans
  plus d'un tiers des essais ; on coupe avant. Pas de son dans ce dossier.
- **Étalonnable** : l'échelle (K = 1024, pascals), les écarts de pression entre essais d'une
  même campagne (donc les pentes, un décalage de 10 Pa change peu les pentes par doublement
  de pression), la température de la puce (Si1 30 à 33 °C, Ré#1 22 à 26 °C).
  **Non étalonnable** : le niveau absolu en pascals de chaque essai (zéro inconnu, de l'ordre de
  quelques Pa d'après le fabricant, sans mesure) ; le débit (zéro et échelle non vérifiés) ; la
  pression de `data - e1`.

## Comment relancer

Ce sont des scripts MicroPython pour la carte Pyboard (bus I2C logiciel sur Y9/Y10).
Copier `xgzp6847d.py` et `MesAnche_2023-04-07.py` (renommé `MesAnche.py`) sur la carte,
puis lancer `mesureancheinit.py`. `testXGZP684D.py` affiche la pression en boucle.
Ils ne sont pas exécutés par `banc_recherche`.
