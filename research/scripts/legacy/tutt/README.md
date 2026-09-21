# TUTT 4.1 — code source (référence)

Voir `CREDITS.md` d'abord : ces fichiers sont l'œuvre de **B.B. « Ninob »**,
pas la nôtre.

22 sous-programmes Fortran de TUTT 4.1, récupérés du Google Drive d'Ewen
(dossier « TUTT 4.1 les sources »). Ils ne sont **pas compilés ni exécutés**
par ce dépôt : ils servent de référence pour vérifier et documenter la
traduction Python dans `banc_recherche/tutt.py`.

| Fichier | Rôle | Traduit dans |
|---|---|---|
| `Ltran9.for` | ligne de transfert **conique exacte** — `DELTA=(DL−D0)/(D0·L)`, `LTRANS` propage A/B tronçon par tronçon, branche les trous latéraux, calcule Z | `tutt._z_troncon`, `tutt.champ_de_pression` |
| `Perce2.for` | `PERCE` : sections et conicités (`DELTA`, `DELTAP`) de la ligne principale et des trous | `tutt._z_troncon` (inline) |
| `Lczb2.for` | `LCZB` : cheminée effective des trous latéraux — correction intérieure de Nederveen, diamètre effectif pondéré, appliquée seulement si le trou est ouvert | `tutt.cheminee_effective`, `tutt.diametre_effectif_trou` |
| `Lczbe.for` | `LCZBE` : corrections de longueur à l'embouchure (flûtes à bec et traversières) | non traduit — chantier ouvert |
| `Lczbb.for` | `LCZBB` : impédance d'extrémité du bas de ligne | `tutt.input_impedance` (rayonnement du pavillon) |
| `Zbout.for` | `ZBOUT` : impédance de bout — rayonnement (0,35·d) + perte de charge de Stokes | `tutt._z_bout_trou` |
| `bouts2.FOR` | `BOUTS` : orchestre `LCZB`/`LCZBE`/`LCZBB` pour toute la perce à une fréquence donnée | `tutt.champ_de_pression` (orchestration équivalente) |
| `Anche5.for` | `ANCHE` : paramètres d'oscillateur de l'anche (MA, KA) depuis la géométrie ou directement (anche solide) | `tutt.reed_impedance` |
| `Propag4.for` | `PROPAG` : constante de propagation, formule de Kirchhoff (Mason 1928) | `tutt._propagation` |
| `Rayon2.for` | `RAYONN` : puissance rayonnée par les trous ouverts | non traduit |
| `Perte2.for` | `PERTES` : partie réelle de l'impédance, bilan des pertes | non traduit |
| `Librt2.for` | `LIBRTE` : sensibilité de la fréquence aux paramètres d'anche (champ de liberté) | non traduit |
| `Doigt2.for` | `DOIGT` : table des doigtés → tableau CP (0=ouvert, 1=fermé) | `tutt._doigte_en_tableau` |
| `Zero5.for` | `ZERO` : recherche des zéros d'une fonction échantillonnée (racines de Im(Z)) | `tutt.resonances` (recherche d'extrema de \|Z\|) |
| `SATIS.FOR` | `SATIS` : critère de satisfaction global (justesse, timbre, volume, émission, liberté) | non traduit |
| `TIMBRE.FOR` | `TIMBRE` : richesse du timbre (harmonicité des résonances) | non traduit |
| `VOLUME.FOR` | `VOLUME` : rendement sonore | non traduit |
| `EMISS.FOR` | `EMISS` : énergie stockée, facilité d'auto-entretien | non traduit |
| `SURTEN.FOR` | `SURTEN` : coefficient de surtension (facteur Q) | `tutt.resonances` (Q par les pics) |
| `RAZO.FOR`, `RAZOI.FOR`, `RAZOC.FOR` | remise à zéro de tableaux (réel/entier/complexe) | — (numpy) |

Les fichiers d'exemple TUTT (`tutt25.dat`, `justess.out`, etc.) ne sont pas
versionnés ici : ce ne sont pas les nôtres non plus, et ils ne sont
nécessaires qu'à la validation ponctuelle documentée dans
`research/docs/modele_hybride_generalise.md` §10. Les perces d'Ewen, elles,
sont versionnées dans `../perces/`.
