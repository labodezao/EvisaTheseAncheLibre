# Bornes du soufflet pour le modèle physique (20/11/2026)

Contenu : `soufflet_modele_physique.json`, les bornes de l'étage soufflet (`banc_recherche/soufflet.py`), chacune
avec sa valeur, son unité, son statut et sa source. Le fichier est écrit à partir de `soufflet.BORNES`
(`soufflet.bornes_json()`), plus quelques grandeurs calculées par l'étage.

Statuts : *mesuré* ; *calculé* ; *à confirmer* (écrit dans une source, pas mesuré) ; *non décidé* (ni mesuré ni
écrit : la valeur est provisoire, `provisoire = true`).

## D'où viennent les valeurs mesurées

Les seules valeurs mesurées sont celles du niveau commun de notes tenues. Elles viennent de l'outil audio vers
MIDI d'Ewen (hors dépôt, rapport v3c, lignes 240 à 336), mesurées sur deux enregistrements d'accordéon :

- bande du niveau commun : 8 Hz. Corrélation du niveau de deux notes tenues ensemble : 0,2 à 0,34 de 0,5 à 8 Hz,
  0,00 au-dessus (78 et 12 paires de notes ; rapport l. 247-248) ;
- pentes du niveau commun pendant les tenues, hors attaques et fins, au 99e centile : montée 122 et 76 dB/s,
  descente 159 et 186 dB/s ; bornes retenues 120 et 190 dB/s (rapport l. 249 et 271).

Ce sont des pentes du **niveau sonore**. Le passage à la pression demande la loi niveau sonore contre pression
d'une anche, que personne n'a mesurée : provisoirement, 1 dB de son pour 1 dB de pression.

## Ce qui reste à mesurer

Un changement de sens sur une note tenue (temps mort, creux), la vitesse de la main (filmer la course avec une
règle), la surface efficace (test de chute, S = mg/p), la souplesse des plis (manomètre), la loi niveau sonore
contre pression.
