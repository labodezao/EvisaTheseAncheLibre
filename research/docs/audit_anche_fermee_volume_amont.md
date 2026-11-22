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

## Ajout du 22/11/2026 : inertie de l'air amont près de la fente (PR 86)

Source : Ricot, Caussé, Misdariis (2005), JASA 117(4), 2279-2290, éq. 5, 8, 9, 10, 18, 19, 20 et annexe B.

Option `gap_inertia="ricot"` de `UpstreamReed` (défaut inchangé au bit près) :
- le débit de fente Q_r devient une variable d'état : `L_r dQ_r/dt = dp − (rho/2)·u·|u|`, `u = Q_r/(alpha·a)`, `L_r = rho·K0/w_eff` (éq. 5 passée de 2D à 3D) ;
- la lame est poussée par la pression de face `(rho/2)·u·|u|` et non plus par dp (éq. 18-19) ;
- `a` est la section série de la loi existante, pour que la limite L_r → 0 rende le modèle d'avant ;
- non repris : le facteur (1 − A1) et les termes A2, A3 de l'éq. 8 (négligeables d'après la fig. 11 de l'article ; A1 ne participe pas à l'excitation) ;
- masse d'air ajoutée (éq. 9) : fonction `added_air_mass`, non appliquée, car la fréquence mesurée dans l'air la contient déjà ;
- intégrateur TR-BDF2 : la constante de temps de Q_r descend à 1e-9 s (jeu de 30 µm), le RK4 ne tient pas.

Vérifications (tests) :
- K0 → 0 : seuils et fréquences du modèle sans inertie ;
- pression imposée : amortissement négatif `c_neg = alpha·G·V0·L_r·(da/dx) / (1 + (omega·tau)²)`, `tau = L_r·Q/(2·dp)`, égal à la valeur propre à 0,1 % ; seuil simulé à ±15 % ;
- cas de l'article (acier, 22,9 × 2,5 mm, 795 Hz, jeu 0,14 mm, levée 0,2 mm, 40 Pa, K0 = 4,5) : auto-oscillation à 794,97 Hz si zeta < 7,25e-4. L'article ne donne ni masse ni amortissement : comparaison qualitative seulement ;
- pas de temps divisé par 2 : écart inférieur à 2 %.

K0 n'est pas réglé. L'article prend 4,5 et le dit arbitraire (choix du point B). La formule de l'article `K0 = ln(2·x_B/e)/pi` avec x_B = 2, 5 ou 10 mm (SUPPOSÉ) donne 1 à 2.

Lame réelle de Fa3 (deux tronçons, m 0,1311 g, k 157,8 N/m, Gamma 30,0 mm², levée 0,4 mm SUPPOSÉE, zeta 0,004 SUPPOSÉ), démarrage / plaquage en Pa :

| V_u (cm³) | sans inertie | K0 géométrique (2, 5, 10 mm) | K0 = 4,5 |
|---|---|---|---|
| 30 | rien | rien | rien |
| 121 | rien | rien | rien |
| 320 | rien | rien | 1048 / 2126 |
| 336 | rien | rien | 899 / 2131 |

K0 = 4,5, régime établi : 336 cm³, 0,334 mm et −49 cents à 1000 Pa (établi en 11,75 s), 0,428 mm et −68 cents à 2000 Pa ; 320 cm³, 0,349 mm et −64 cents à 2000 Pa. Pression imposée, K0 = 4,5 : seuil vers 100 Pa.
Marge de stabilité à 336 cm³, K0 géométrique : max Re(lambda) = −3,96 ; −2,98 ; −2,23 s⁻¹ pour x_B = 2, 5, 10 mm (référence sans inertie : −4,7).

Conclusion : le mécanisme est dans le modèle et va dans le sens de l'atelier (Fa3 muet à 30 et 121 cm³, parlant à 320 et 336), mais seulement avec la valeur arbitraire de K0. Non décidé. Mesures qui tranchent : amortissement de la lame (décroissance libre) et seuil de démarrage du Fa3 instrument fermé.

`modal.assemble` : cause de l'erreur sur lame à deux épaisseurs prouvée (base de Rayleigh-Ritz en modes uniformes : +153 % à 1 mode, +11 % à 6, +1,6 % à 30 ; quadrature et sigma écartés). Correction (modes vrais par éléments de Hermite) et test contre l'équation transcendante à deux tronçons dans la branche `claude/modal-assemble-troncons`, non fusionnée : la lame par défaut `SECTIONS_DEFAULT` passe de 102,1 Hz à sa vraie valeur 15,59 Hz, et `test_la_note_est_celle_de_la_lame` devient rouge (+419 cents) pour une cause non prouvée.

## Ajout du 22/11/2026 : temps d'attaque selon le volume amont

Question d'atelier (octodyna) : un volume amont trop grand donne des attaques molles et en retard.
Calcul : 216 attaques (Fa3 lame réelle, Do4 et Fa4 lames équivalentes ; V_u = 30 à 1500 cm³ ; sans inertie, K0 géométrique, 4,5 et 9 ; 1000 et 1500 Pa). Départ au repos, échelon de pression de source, sans kick. t90 = temps pour 90 % de l'amplitude établie. Paramètres SUPPOSÉS : levée 0,4 mm, zeta 0,004, R_s 3e6.

Résultats à 1500 Pa, K0 = 4,5 (sigma en s⁻¹, t90 en ms) :

| V_u (cm³) | Fa3 sigma | Fa3 t90 | Fa4 sigma | Fa4 t90 | remplissage mesuré (ms) |
|---|---|---|---|---|---|
| 60 | −66,7 | muet | 21,3 | 221 | 4 |
| 121 | −32,5 | muet | 71,3 | 130 | 7 |
| 200 | −10,9 | muet | 92,6 | 105 | 12 |
| 336 | 3,9 | 859 | 106,1 | 102 | 19-20 |
| 500 | 11,2 | 627 | 112,7 | 99 | 27-29 |
| 1000 | 18,9 | 530 | 119,4 | 98 | 54 |
| 1500 | 21,4 | 530 | 121,6 | 119 | 82 |

- Le taux de croissance augmente avec le volume et sature : le modèle ne donne pas d'attaque plus lente de la lame dans un grand volume.
- Seul le temps de mise en pression croît avec V_u (formule R_s·V/(rho·c²), mesuré 2 à 3 fois plus long).
- Sensibilité à K0 (Fa3, 1000 cm³, 1500 Pa) : t90 = 1211 ms sans inertie, 777 géométrique, 530 pour 4,5, 312 pour 9. Volume minimal du Fa3 : 750, 500, 336, 200 cm³.
- Do4 à 1500 Pa : équilibre linéairement stable à tous les volumes, mais oscillation déclenchée par l'échelon pour K0 = 4,5 (dès 1000 cm³) et 9 (dès 336 cm³) : bifurcation sous-critique probable, non étudiée.
- Convergence en pas de temps : t90 à moins de 1 % sur trois cas, 5,9 % sur Fa4, K0 = 4,5, 336 cm³, 1000 Pa.
- Amplitudes de 1,5 à 2,5 mm pour 0,4 mm de levée : hors domaine validé.

Scripts et CSV hors dépôt : `J:\claude\tmp\melodica_impedance\attaque\`.
