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
- La notice du fabricant (`pression\XGZP6847D-Pressure-Sensor-V2.5.pdf`, page 10) donne le
  facteur K selon la gamme du capteur. **K = 1024 correspond à la gamme 4 à 8 kPa**, et le
  résultat est **en pascals**.
- Au démarrage, le pilote moyenne 80 lectures (`Calc_off`) mais **ne retranche pas** ce zéro :
  `Get_DPress()` rend la valeur brute. `MesAnche` garde ce zéro dans `p0`.
- La « température » enregistrée est celle **de la puce du capteur**, pas celle de l'air.
- Un registre est réglé à la main : `0xA6 = 0x2B` (gain et suréchantillonnage, voir la notice).

## Ce qui est établi, plausible, à tester

- Établi : le code du 07/04/2023 lit un XGZP6847D et le convertit en Pa avec K = 1024.
- Plausible : les campagnes d'avril et de septembre 2023 ont été faites avec ce code. Les
  valeurs 55 à 2 040 Pa collent avec un capteur de 4 à 8 kPa.
- À tester : le modèle exact du capteur monté (sa gamme). Si la gamme n'est pas 4 à 8 kPa,
  le facteur K est faux et les pressions sont fausses d'un facteur 2 ou plus. Test simple :
  le tube en U à eau (1 mm d'eau = 9,8 Pa) en parallèle sur la chambre.
- À tester : la campagne `data - e1` (21/01/2023) est plus ancienne. Elle a peut-être été
  faite avec le SDP810 (décembre 2022) ou le BMP280.

## Comment relancer

Ce sont des scripts MicroPython pour la carte Pyboard (bus I2C logiciel sur Y9/Y10).
Copier `xgzp6847d.py` et `MesAnche_2023-04-07.py` (renommé `MesAnche.py`) sur la carte,
puis lancer `mesureancheinit.py`. `testXGZP684D.py` affiche la pression en boucle.
Ils ne sont pas exécutés par `banc_recherche`.
