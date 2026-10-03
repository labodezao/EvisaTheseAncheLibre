# La table d'accordage numérique (2019-2023)

## D'où ça vient

- `table accordage.lyx` (12/07/2021) : `D:\GoogleDrive\Lutherie\Ressources\outils d'aide a la facture instrumentale\table accordage\`.
  L'adresse mail de l'auteur a été retirée de cette copie.
- `tableaccordage.py` (21/01/2021, BMP280 + SFM3000) et `instruacco.py` (05/04/2023,
  XGZP6847D) : `D:\GoogleDrive\Ingénierie et recherche\Ressources\micropythonn code\`.

## Ce que c'est

Le dossier de conception de la table d'accordage : caisse inclinée à 30°, turbine
centrifuge triphasée 24 V pilotée en tension 0-5 V (« ne pas piloter en PWM »), distributeur
deux voies à moteur pas à pas pour souffler ou aspirer avec peu de pertes de charge, capteur
de pression I2C, capteur de débit I2C bidirectionnel jusqu'à 200 L/min (SFM3000),
MicroPython sur STM32, électrovanne pour **mesurer les fuites par la chute de pression**,
écran OLED, électroaimants pour brider la caisse.

C'est l'ancêtre direct du banc d'accordage ESP32-S3 (`firmware/`) et de la méthode des
fuites (`research/docs/fuites_air_methodes.md`).

## Comment relancer

Le `.lyx` s'ouvre avec LyX. Les `.py` sont du MicroPython pour Pyboard (bibliothèques
`nanogui`, `ssd1306`, `step`, `sfm3000` dans le même dossier du Drive).
