# Chaîne de leviers du LibRT : propositions P1 à P5 (26/10/2026)

Copie de travail pour la thèse. Les cotes sont lues dans la CAO (ZW3D), pas mesurées sur pièce ;
les résultats (courses, rapports, flexions, jeux) sont calculés par les scripts joints.

Origine : `J:\zw3d_travail\librt\propositions_leviers_20261026` (P) et `...\audit_leviers_20261026` (A).
- propositions.json (P, 26/10), calcul_propositions.py (P, 26/10) : propositions P1 à P5.
- calcul_p4_p5.py (P, 26/10), synthese_P1_P5.png (P, 26/10) : calcul P4/P5 et figure de synthèse.
- p5_axe.json (P, 27/10), calcul_p5_axe.py (P, 26/10) : P5 avec le trou sur l'axe de la mécanique.
- p5_questions.json, calcul_p5_questions.py (P/p5_questions, 27/10) : questions de cotes de P5.
- plan_global_trous.json (P, 04/11) : plan global des trous d'attache.
- releve_chaines.json, ligaments.json, calc_flexion_jeux.py (A, 26/10) : relevé des chaînes, ligaments, flexion et jeux.

Les scripts gardent leurs chemins d'origine (J:\zw3d_travail\...) : ils ne se relancent pas tels quels ici.

Décision d'Ewen, entrée "leviers-P5" de decisions.json (27/10/2026) :
> Ewen 26/10/2026 : « P5 est validée, mais garde la même forme et garde le trou sur l'axe de la mécanique ; tu peux décaler toute la tige avec la cote à l'axe si besoin » (trous d'attache le long de l'axe de la bande : A3 -2,1, B2 -1,35, B3 -3,7 mm ; A1 A2 B1 en attente) ; 28/10/2026 : A2 1,25 et B1 8,0 (rapport 1,05 sur l'axe), le bout de la tige suit le trou (MatHautTige 3)
