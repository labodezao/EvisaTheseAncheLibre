# Anche fermée par le souffle et volume amont : pourquoi le modèle disait l'inverse

> Écrit le 22/11/2026. Code : `banc_recherche/upstream_reed.py`. Tests : `tests/test_upstream_reed.py`.

## Le constat d'atelier (mélodica)

- La cloche d'accordage de 30 cm³ reste muette dans le grave.
- À 121 cm³, c'est mieux.
- L'instrument entier (336 cm³) joue.
- À 30 cm³, l'amplitude est petite.
- À forte pression, la lame se plaque : le son cesse.

## La cause, prouvée

`FreeReedModel` (`reed_oscillator.py`) code une anche que le souffle OUVRE : force +p·Γ, ouverture = bout + levée. Une anche de mélodica ou d'accordéon est FERMÉE par le souffle. Trois preuves :

1. Dans le code, le signe de la force et celui de l'ouverture sont ceux d'une anche qui s'ouvre. `coupled_reeds.py` a l'autre loi (`ReedSetting`, `_area`, `_series`).
2. L'« étouffement » de `FreeReedModel` est proportionnel à `max_open − levée` : 1249, 1110, 833 et 278 Pa pour une levée de 0,05, 0,1, 0,2 et 0,4 mm (max_open 0,5 mm). C'est la lame soufflée grande ouverte, pas une lame plaquée. Test : `test_contraste_etouffement_proportionnel_a_max_open_moins_levee`.
3. La note jouée est AU-DESSUS de la lame avec `FreeReedModel`. Avec la loi fermée elle est en dessous (Fa4 : 345,2 Hz à 600 Pa, 343,0 Hz à 1000 Pa, pour une lame de 349,2 Hz).

Contraste : avec `FreeReedModel`, le seuil MONTE avec le volume (Fa4 : 74 Pa à 30 cm³, 828 Pa à 121 cm³). Avec la loi fermée, la lame ne parle pas à 30 cm³ et parle à 121. Test : `test_contraste_free_reed_model_seuil_monte_avec_le_volume`.

## Les valeurs 23,0 Pa et 119,2 Hz de `audit_modele_anche.md`

Ce n'est pas une régression. Ce sont les défauts du commit f3947d0 : V0 = 40 cm³ et balayage de la lame actif. Ils ont été changés exprès :

- 4b1d09d : V0 = 7,9 cm³ et `sweep_coupling` = 0 (la lame libre ne comprime pas sa chambre) ;
- 616534d : résistance de source R = 5·10⁶.

Le tableau des lignes 326-329 de `audit_modele_anche.md` n'avait pas été mis à jour. Une ligne datée le signale.

## Ce que le nouveau module ajoute

La loi fermée de `coupled_reeds`, avec un volume amont fini, une source à résistance interne R_s, un aval (volume et orifice), un tuyau en ligne en option (24 cellules) et un ballast. Stabilité linéaire (franchissements, position du bout rapportée à la levée, fréquence) et simulation.

Contrôle : volume amont énorme et R_s minuscule redonnent `CoupledReedsModel` (seuil 13,875 contre 13,874 Pa, plaquage 472,046 Pa, 173,18 Hz, amplitude 1,693 mm à 300 Pa).

## Résultats (paramètres supposés, lame de laiton uniforme équivalente)

Levée 0,4 mm, plaque 1,0 mm, jeu 30 µm, R_s 3·10⁶, V_d 1 cm³, orifice 25 mm² sur 6 mm. Tuyau : 1 m, 8 mm. Pressions en Pa : démarrage puis fin (plaquage). Entre parenthèses, la note jouée par rapport à la lame.

| Note | V (cm³) | Sans tuyau | Avec tuyau |
|---|---|---|---|
| Fa3 | 30 | démarre vers 1950 (non concluant) | 385-502, puis 1951 (mode du réseau, 49 Hz) |
| Fa3 | 121 | démarre vers 1950 (non concluant) | 437-493, puis 1951 (23 Hz) |
| Fa3 | 336 | rien | rien |
| Do4 | 30 | rien | 770-1077 (50 Hz) |
| Do4 | 121 | rien | rien |
| Do4 | 336 | 369-1090 (−26 cents) | 367-1093 |
| Fa4 | 30 | rien | 1445-1847 (51 Hz) |
| Fa4 | 121 | 1722-1784 (−28 cents) | rien |
| Fa4 | 336 | 276-1926 (−12 cents) | 288-1928 |
| Fa5 | 30 | rien | rien |
| Fa5 | 121 | dès 666 (−9 cents) | dès 678 |
| Fa5 | 336 | dès 522 (−8 cents) | dès 534 |

À la fin de la bande, le bout est à 0,89 à 0,99 de la levée : la lame est plaquée. Plus la levée est grande, plus le plaquage vient tard (Fa4, 336 cm³ : 1440 Pa pour 0,3 mm, 2409 Pa pour 0,5 mm).

Amplitude établie (simulation, sans tuyau) : Fa5 à 1000 Pa, 0,56 mm à 121 cm³ contre 0,71 mm à 336 cm³. Fa4, 336 cm³ : 0,75 mm à 600 Pa, 0,99 mm à 1000 Pa.

## Ce qui reste faux ou non décidé

- Fa3 ne parle à aucun volume avec la lame uniforme équivalente et se plaque vers 500 Pa. La lame réelle, amincie à la racine, est à modéliser.
- Avec le tuyau, le réseau a des modes à 23-50 Hz : ce ne sont pas des notes.
- Dans certains cas l'amplitude dépasse la levée (0,75 mm pour 0,4 mm) : non validé.
- Les paramètres sont SUPPOSÉS : levée, plaque, jeu, R_s, aval, profil de la lame.
- Toujours absents : le mécanisme de Ricot, Caussé et Misdariis (2005) et l'inertie de l'écoulement amont local.

## Les mesures qui caleraient le modèle

1. La levée, l'épaisseur de la plaque et le jeu, au pied à coulisse et à la cale.
2. Le profil de la lame (épaisseur le long de la lame).
3. `p_on` et `p_choke` à trois volumes (30, 121, 336 cm³), par la méthode de `seuils_auto_entretien.md`.
4. La caractéristique pression-débit de la source (R_s).
