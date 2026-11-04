# Apports à la thèse : le registre

Ce qui entre dans la thèse depuis les autres chantiers (accordeur, lutherie, banc, calcul), au fur et à
mesure. Une ligne par résultat : la valeur, son statut, sa source, où elle va dans le manuscrit. Le registre
ne remplace pas le manuscrit, il dit d'où vient chaque chiffre. Une valeur non confirmée reste marquée
comme telle tant qu'une mesure ne l'a pas tranchée. Ce dépôt est public : pas de donnée de client, pas de
séance, pas de secret du moteur privé de l'accordeur.

**Statuts.** *mesuré* : sur vraie anche ou vrai instrument. *mesuré (échantillons)* : sur banque de sons, pas
au soufflet. *relevé CAO* : lu dans un fichier CAO, jamais sur la pièce. *calculé* : formule ou simulation.
*synthèse* : signal fabriqué. *à confirmer* : il manque ce qui est dit.

## Versement du 04/11/2026 (ce qui s'était accumulé depuis le 19/10, et plus ancien jamais versé)

### A. Accordeur : la lecture des anches couplées (audits du 19 au 22/10/2026)

Sources : coffre, `Projets actifs/Accordeur d'accordéon/Savoir/` et `Audits/` ; dépôt privé de l'accordeur,
`docs/CERTIFICAT.md` § 0G.2 et la comparaison du 22/10. Manuscrit : `these_parties_2_a_5_fr.md`, section
« Lire des anches couplées », et `design_theory{,_fr}.lyx`, section « Reading coupled reeds ».

| Résultat | Valeur | Statut | Source |
|---|---|---|---|
| Somme A + B sans couplage, intervalles tempérés | mélange égal aux notes seules à 0,001-0,05 ¢, aucune composante à Ω (54 paires) | mesuré (échantillons) | Savoir, *Superposition - couplage réel ou défaut de calcul* |
| Octave en « notes choisies » | la voix haute est lue comme 2 × la basse, cache le désaccord (jusqu'à 3,3 ¢) | mesuré (échantillons) | idem |
| Part du calcul dans la fluctuation, prises H6 | 10 % (La4, La5) à 50 % (La3 à 0,59 Hz) ; le reste : modulation de phase du tirage, AM réelle, soufflet | mesuré, un instrument | idem |
| Fréquence instantanée d'une somme de deux sinus, rapport r | f_i = fA + Ω·r(r + cos 2πΩt)/(1 + r² + 2r cos 2πΩt) ; moyenne sur un battement entier = fA (r < 1) ; excursion au creux −Ω·r/(1 − r) ; fenêtre non entière : composante à Ω ≈ excursion × abs(sinc(ΩT)) | calculé | idem |
| Défaut dans le régime où le partiel k ne sépare pas | k·Ω < 1,4 Hz ; 1,2 à 1,4 ¢ crête à crête à −6 dB ; à niveaux égaux, pose au milieu fA + Ω/2 puis saut sur une raie (4 ¢) | synthèse | idem |
| Prétraitement d'amplitude (enveloppe, contrôle de gain, compresseur) | n'aide pas ; compresseur : 1,9 Hz lu pour 5 | synthèse | idem |
| Pression commune du soufflet | 0,3 ¢/s sur le H6, s'annule dans le battement | mesuré, un instrument | idem |
| Stabilité du battement contre celle des cents | 0,05 bat/min contre 0,1 à 0,3 ¢ | mesuré, un instrument | idem |
| Conversion à La4 442 Hz | 1 bat/min = 0,017 Hz = 0,065 ¢ ; 0,1 ¢ = 1,5 bat/min | calculé (vérifié le 04/11) | Savoir, *Le battement d'abord* |
| Cible à l'oreille | ±1 bat/min (2 à 3 % d'un tempo) | à confirmer : aucune référence dans la note | idem |
| Raie libre proche d'une anche | à moins de 1/(K·T), ce n'est pas une raie étrangère ; cas H6 à 0,32 Hz de l'anche forte, faux « sûr » de 0,56 ¢ | mesuré (cas), synthèse (0 faux sur 10 000 puis 3 600) | Audits n° 6 et n° 7 |
| Borne de l'AM d'une paire | deux anches à rapport ρ ne modulent l'enveloppe qu'à l'indice ρ | calculé | Audit n° 7 |
| Résidu du partiel 2 sur le H6 | 16 fois trop grand (4,8 % contre 0,3 %), toutes raies, porteuse comprise ; partiel 1 parfait | mesuré, 17 notes, un instrument ; cause à confirmer | Audit n° 7, certificat § 0G.2 |
| Partiel décalé en bloc, testé | partiel 2 : 5,02 % → 4,83 % ; abs(eps_2) médiane 0,025 Hz (max 0,16) ; témoin 0,37 → 0,33 %. Ce n'est pas un partiel décalé constant | mesuré, 17 notes (témoin 20 notes) | certificat § 0G.2 |
| Accord avec ESPRIT, 17 anches | écart type 0,14 ¢, maximum 0,26 ¢, 8 anches sur 17 sous 0,1 ¢ | mesuré, sur boucle (enregistrement rejoué) | comparaison du 22/10 |

### B. Lib RT : cinématique des leviers et rapport 1,05 (26/10 au 04/11/2026)

Détail dans `research/data/librt_leviers_20261026/` et `design_practical/02c_main_gauche_chaine_librt_{fr,en}.md`.
Aucune de ces valeurs n'a été mesurée sur la pièce.

| Résultat | Valeur | Statut | Source |
|---|---|---|---|
| Rapport levée/course, avant correction, six chaînes | A1 0,629 ; A2 1,022 ; A3 1,104 ; B1 0,745 ; B2 1,140 ; B3 1,289 | calculé sur relevé CAO | `propositions.json`, AVANT |
| Rapport après P5 retenue | 1,05 sur 5 chaînes, A1 non tranché (0,629) | calculé sur relevé CAO | `plan_global_trous.json` |
| Levée et effort à 1,05 | 5,25 mm pour 5 mm ; 186 g (177 g × 1,05) | calculé ; base 177 g pour un trou de 300 mm² à confirmer | `propositions.json` |
| Écart petits angles contre exact | jusqu'à 6 % (B2 : 1,213 contre 1,140) | calculé | `propositions.json` |
| Décision | P5 validée, trou sur l'axe de la mécanique, toute la tige décalable | décision d'Ewen, 26/10/2026 | `decisions.json` CAO, `leviers-P5` |
| Temps mort par chaîne | 0,2 à 0,3 mm | calculé ; à mesurer | audit Fable du 26/10 |
| Force de ressort au trou | 2,1 / 4,0 / 5,8 N pour r1 / r2 / r3 | calculé | audit Fable du 26/10 |

### C. Banc 2023 : f0, répétabilité, résistance de la source (analyse du 01/10/2026, jamais versée)

Données : `research/data/mesures_2023/`. Pression en Pa : plausible, unité à confirmer au tube en U. Manuscrit :
`these_parties_2_a_5_fr.md` (section d'ouverture), `experiences_a_mener.md` (E1).

| Résultat | Valeur | Statut |
|---|---|---|
| Sons exploitables | 2 162 (1 024 + 395 + 743), dont 1 388 avec pneumatique lisible | mesuré |
| f0 médiane par campagne | 73,37 Hz (13/04), 77,75 Hz (16/04), 61,66 Hz (11/09) | calculé sur `mesures_2023.csv`, 04/11/2026 |
| Pente de f0 | −1,7 ¢/100 Pa (d1_L), −0,9 (D#0), −1,9 (septembre) ; R² ≈ 0,3 ; jusqu'à −2,5 à 150 mm², environ −1 à 75 mm² | mesuré ; unité à confirmer |
| Répétabilité, deux passages | −0,9 ¢ ± 0,4 (381 paires) ; −0,8 ¢ ± 0,9 (260 paires) | mesuré |
| Dérive thermique | 17,5 → 21,7 °C et 30,3 → 33,0 °C ; environ −0,2 ¢/°C | température mesurée ; pente à confirmer (point témoin manquant) |
| Résistance interne de la source | 9 à 24 Pa par l/min, soit 0,5 à 1,4 × 10⁶ Pa·s/m³ (r = −0,86 à −0,98) | calculé sur mesures ; unité à confirmer |
| Silence à la plus grande section | 180 mm² : muette dans 93 à 100 % des essais (d1_L, septembre) | mesuré |
| Sections réelles | 60 à 150 mm² par pas de 15, puis 180 mm² | relevé dans les scripts |
| Seuil de démarrage d1_L | sous environ 150 Pa ; le modèle prédit 25,8 Pa | mesuré contre calculé |
| Fréquences Praat du HDF5 de septembre | fausses d'environ 5 Hz (56,5 au lieu de 61,7) : ne pas réutiliser | constaté |

### D. Sommier : le vrai trou de table sous le R12 (11/10/2026)

Corrige l'hypothèse des calculs Elmer de `research/fem/sommier/` (trou supposé). N1 et N2 restent à refaire.

| Résultat | Valeur | Statut |
|---|---|---|
| Table | 3 mm (8 mm supposés) | relevé CAO |
| Trous | 2 par note, 12 × 10 mm, entraxe 15 mm, 72 trous | relevé CAO |
| Sous la table | plaque 12 × 8 mm, glissières 12 × 12 mm ; col d'environ 94 à 144 mm² par case, sur environ 9 mm | relevé CAO ; plaque à vérifier (trou de 2 mm de profondeur dans le STL) |
| Levée de soupape | non dessinée | à mesurer sur l'instrument |

### E. Soupapes : essais de 2020 (coffre, `Domaines (permanent)/6-Recherche et ingénieurie/accordeons/etancheité accos/`)

| Résultat | Valeur | Statut |
|---|---|---|
| Effort, accordéon 2 voix, avec tastière | extérieur 81,08, intérieur 102,42 (12 soupapes) | mesuré ; unité non écrite, à confirmer |
| Effort, sans tastière | extérieur 79,75, intérieur 97,33 | mesuré ; unité à confirmer |
| Feutre contre mousse, transitoire de soupape | oscillations au contact, disparues en tastière guidée feutre | mesuré, qualitatif (volts sans étalonnage) |

## Reste à mesurer (geste à l'atelier)

- Levée au comparateur et effort au doigt sur les six chaînes du Lib RT, à la première pièce.
- Anche seule contre anche dans la paire : H6, même note, 8' seul, 8'+ seul, 8'+8', même pression.
- H6 avec Ω·T ≥ 4 s, ou rapport d'anches de 6 à 12 dB, pour le surplus du partiel 2.
- Tube en U à eau (1 mm d'eau ≈ 9,8 Pa) pour l'unité de pression du banc.
