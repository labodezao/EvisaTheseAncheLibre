# Anches (reedgui)

Décrire une languette par tronçons, voir son profil et ses modes. Reprise de FreeReedGUI
d'Ewen (2020-2021). C'est la seule version vivante : l'ancienne, dans
`Archives\tcl\TKinter` sur le Drive, peut être retirée.

## Lancer

- Double-clic sur `Anches (reedgui).cmd`, ou le raccourci « Anches (reedgui) » du Bureau.
- Ou : `J:\claude\venv\Scripts\python.exe reedgui.py [banque.csv | matrix.txt]`

## Mode d'emploi

1. **Ouvrir** une banque d'anches (`.csv`) ou un ancien `matrix.txt`.
2. Double-clic sur une case du tableau pour la changer. Tout est en mm.
3. Les modes se recalculent seuls : fréquence, note, écart en cents. Un clic sur un mode montre sa déformée.
4. **Enregistrer** range l'anche dans la banque (les autres anches du fichier restent).
5. **Exporter le yaml** prépare le modèle (Elmer, recalage). **Vérifier avec Elmer** : 10 à 30 s.

Matériau : choisir dans la liste (acier, inox, laiton, bronze, plomb, cire), ou écrire
« 200 GPa / 7850 » (module d'Young, masse volumique).

## Le calcul

- Fréquences : poutre d'Euler-Bernoulli **exacte** (matrices de transfert), tronçons à
  largeur et épaisseur variables, masse au bout.
- Contrôle : Rayleigh-Ritz (la méthode de `km.py`), 20 modes de base. C'est une borne haute.
- Option : Elmer en 3D (torsion et flexion dans le plan en plus).
- Le calcul est dans `banc_recherche/languette.py`, le même que pour Elmer et le modèle
  semi-analytique. Tests : `tests/test_reedgui.py`, `tests/test_languette.py`.

## Audit de la version 2021 (03/10/2026)

Ce qui ne marchait pas :
- « Calc and plot » traçait le profil, mais ne calculait aucune fréquence.
- La méthode `km` n'était appelée nulle part, et aurait planté (`Bi`, `Si`, `BL_Sigma` non définis).
- Les champs d'un tronçon ne réécrivaient pas la matrice (fonctions `update_values_*` reliées à rien).
- On ne pouvait pas supprimer le tronçon 1 ; numpy et sympy étaient mélangés.

Ce qui était mal pensé :
- Unités en mètres, écrites `1.00E-03` ; un seul tronçon visible à la fois.
- « Déformée » = flèche sous une force au bout, pas un mode propre.
- 2 modes de base seulement : pour l'anche de `matrix.txt`, 102 Hz au lieu de 67,4 Hz (+51 %).
- sympy pour intégrer des cosh : lent ; coefficients sigma arrondis (faux au-delà du mode 3).

Ce qu'on a gardé : l'anche par tronçons, le format `matrix.txt` (toujours lu), le tracé du
profil et de la déformée, Ouvrir et Enregistrer, Tkinter et matplotlib.
