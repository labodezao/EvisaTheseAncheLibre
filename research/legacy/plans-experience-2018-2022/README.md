# Les plans d'expérience d'Ewen sur les sommiers et la table d'harmonie (2018-2022)

## D'où ça vient

- `plans experience Th.lyx`, `plans_experience_Th.pdf`, `table essais8.pdf` (21/03/2018) :
  `D:\GoogleDrive\Ingénierie et recherche\Ressources\plans experiences\octo\optim th\`.
  Optimisation de la table d'harmonie des Accordinas et Octodynas.
- `sommiers-air.lyx` (03/11/2020, revu le 24/08/2022) et `sommier basse.mpx` (Minitab,
  19/08/2022) : `...\plans experiences\sommiers\`.
- `plans experience.lyx` (03/11/2020) : le modèle de fiche de plan.
- `debitvar.xlsx` (26/03/2020) : `D:\GoogleDrive\Lutherie\Projets\anches doubles\couplage anches cavite\debit variable\`.

## Ce que c'est

**Table d'harmonie (2018).** Les buts sont ceux de la thèse aujourd'hui : un instrument qui
consomme autant d'air dans les graves que dans les aigus ; un seuil de mise en oscillation
qui permet le pianissimo sur toute la gamme ; un timbre homogène ; un transitoire de moins
de 50 ms. Six facteurs géométriques (niveaux dans la fiche), réponses : pression et débit.

**Couplage anche-cavité par excitation magnétique (2020-2022).** GBF + ampli +
électroaimant, déplacement mesuré par un capteur capacitif, un Mi3 plombé. Facteurs :
hauteur sous la plaquette côté lame (10-20 mm), largeur du trou du talon (3-15 mm),
épaisseur du talon (3-50 mm), angle anche / entrée d'air (0-90°). Le plan Minitab est un
**factoriel complet 2⁴ + 1 point central = 17 essais, en ordre aléatoire**. Il est extrait
dans `sommier_basse_plan.csv`. Les colonnes « Volume » et « Réponses » sont **vides** :
le plan n'a pas été mené.

**`debitvar_section_hauteur.csv`** : la section de passage S (mm²) du module à débit
variable en fonction de la hauteur h (mm). Des valeurs manquent entre 16,5 et 27 mm.
Utile pour relire la « section » des campagnes 2023.

## Comment relancer

Le plan 2⁴ + centre peut être relancé tel quel au banc (`banc_recherche.doe`, ou
`doe_analysis.design`). Les `.lyx` s'ouvrent avec LyX. Le `.mpx` s'ouvre avec Minitab ;
c'est une archive zip lisible en JSON.
