# Calculs d'écoulement autour d'une languette (Elmer, gmsh — gratuits)

But : trancher ce que le modèle 1D ne sait pas dire — **l'air donne-t-il de
l'énergie à une languette plate et centrée (anche en sandwich) ?** et d'où
viendrait le ton d'écart selon la hauteur des supports.

## Ce qu'il y a

`sandwich2d/` — coupe 2D à travers la largeur de la languette, demi-modèle
(symétrie au milieu), air laminaire incompressible.

| fichier | rôle |
|---|---|
| `geometrie.py` | écrit la géométrie gmsh : `python3 geometrie.py sandwich h_amont_mm h_aval_mm` ou `python3 geometrie.py accordeon plaque_mm levee_mm` |
| `stationnaire.sif` | Elmer : écoulement établi à 1000 Pa → débit à travers la fente |
| `oscillation.sif` | Elmer : languette forcée à ±5 µm, 440 Hz, maillage mobile → force de l'air à chaque pas |
| `bilan.py` | travail de l'air par cycle, amortissement et raideur apportés par l'air, comparés à l'acier |
| `foam/` | le même cas stationnaire pour OpenFOAM (comparaison, voir plus bas) |

Cotes par défaut (celles du modèle 1D, **à remplacer par les tiennes**) :
languette 3,5 × 0,3 mm, jeu 30 µm, supports 0,9 mm.

## Lancer (Linux ; sous Windows, mêmes commandes avec Elmer et gmsh installés)

    python3 geometrie.py sandwich 0.9 0.9 > anche.geo
    gmsh -2 anche.geo -format msh2 -o anche.msh
    ElmerGrid 14 2 anche.msh -autoclean -out elmer
    ElmerSolver stationnaire.sif        # ~20 s
    ElmerSolver oscillation.sif         # ~7 s par pas ; régler Timestep Intervals
    python3 bilan.py .                  # après oscillation

## Elmer ou OpenFOAM — ce qui a été vérifié ici

Même maillage (≈ 21 000 nœuds, 6 µm dans le jeu), même cas stationnaire :

| | Elmer 9.0 | OpenFOAM 1912 |
|---|---|---|
| convergence | 14 itérations, 21 s | non convergé après 6000 itérations (6 min) |
| débit (m²/s par m) | 3,324·10⁻⁴ | incohérent (signe qui change) |
| modèle 1D (Poiseuille + Bernoulli) | 3,336·10⁻⁴ — accord 0,4 % | — |

Pour cet écoulement lent dans des jeux fins, Elmer (éléments finis,
Newton) a convergé tout de suite ; ma mise en données OpenFOAM (SIMPLE,
conditions de pression totale) non. Ce n'est pas un jugement définitif sur
OpenFOAM — un réglage transitoire aurait sans doute marché — mais Elmer
fait le travail, et c'est ta préférence.

**Là où OpenFOAM aurait l'avantage** : les grandes amplitudes. La languette
parcourt ~1 mm le long d'un jeu de 30 µm ; un maillage qui se déforme s'y
écrase. OpenFOAM sait faire glisser deux maillages l'un contre l'autre
(interfaces AMI) et porter un corps sur ressort ; Elmer le fait avec des
conditions « mortar » dont l'usage en écoulement est à vérifier. Pour la
question du **démarrage** (petite amplitude), Elmer suffit.

Constat au passage : dans le jeu de 30 µm, **80 % de la chute de pression
est visqueuse** — Bernoulli seul y serait faux (le modèle 1D en tient
compte depuis `slot_stack.py`).
