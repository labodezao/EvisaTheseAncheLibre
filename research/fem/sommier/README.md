# Acoustique des chambres du sommier (Elmer, Gmsh, petit modèle)

Commencé le 03/10/2026. Rapport complet (pour Ewen) :
`J:\claude\business-os\journal\recherche\sommier-optimisation-acoustique.md`.

La question : comment la chambre d'une anche (son volume, le trou de table d'harmonie qui la
ferme) change le démarrage, la justesse, la puissance et le débit de l'anche, pour dimensionner
les sommiers. Une anche d'abord ; deux anches ensuite.

## Ce qu'il y a

| fichier | rôle |
|---|---|
| `chambre_modes.py` | l'air d'une chambre du sommier générique (cotes lues dans `outils/zw3d/sommier.py`), maillé par Gmsh, modes propres par Elmer (WaveSolver, valeurs propres) ; compare à la formule de Helmholtz |
| `seuils_cavite.py` | plan d'expérience numérique avec `banc_recherche/coupled_reeds.py` (une anche, l'autre bloquée) : seuil de démarrage p_on, étouffement p_haut, justesse au seuil, puis course, débit, puissance rayonnée à 300, 1000, 2000 Pa |
| `resultats/*.csv` | les sorties (séparateur `;`) |

## Lancer (Windows, rien à installer de plus)

    J:\claude\venv\Scripts\python.exe chambre_modes.py              # 12 chambres du R12, ~1 min
    J:\claude\venv\Scripts\python.exe chambre_modes.py --balayage --chambres 1 6 12
    J:\claude\venv\Scripts\python.exe seuils_cavite.py --plan luthier
    J:\claude\venv\Scripts\python.exe seuils_cavite.py --plan rapport

- Elmer 9.0 : `C:\Program Files\Elmer 9.0-Release` (variable `ELMER_HOME` pour un autre chemin).
- Gmsh 4.15 : paquet Python `gmsh`, installé dans `J:\claude\venv` (uv, 03/10/2026).
- Maillages et journaux Elmer : `J:\claude\calculs\chambre_sommier\` (hors du Drive).

## Ce qui a été vérifié

- **Elmer contre la théorie** (boîte 50 x 15 x 10 mm) : parois rigides, 3430,0 Hz pour
  c/2L = 3430 Hz ; un bout ouvert : 1715,0 / 5145,0 / 8575,0 Hz pour c/4L, 3c/4L, 5c/4L.
- **Maillage** (chambre 12) : premier mode 1575,5 Hz (maille 2 mm, 3,5 s), 1574,5 Hz
  (1,2 mm, 34 s), 1574,1 Hz (0,8 mm, 6 min). 2 mm suffit pour un plan (0,1 %, 1,5 cent).
- **Stabilité linéaire contre simulation** (`seuils_cavite.py`) : même seuil (entre 300 et
  500 Pa pour une lame de 1000 Hz) que la simulation temporelle de `coupled_reeds`.
- **Pas d'hystérésis cachée** : une oscillation lancée à 1000 Pa sous un seuil de 1066 Pa tient
  encore à 0,4 s, mais s'éteint en 2 s (taux -1,5 /s). `regime()` rend donc une « allure »
  (établi, s'éteint, croît) ; seules les lignes « établi » sont des régimes.
- **Formule de Helmholtz contre Elmer** : trop haute de 0 à +10 % (volume des cases seules) ;
  correction intérieure du trou vue par Elmer 0,85 à 1,34 x rayon équivalent (moyenne 1,03),
  d'où `--kappa 1.9` par défaut (les plans du 03/10/2026 ont tourné avec 1,55).

## Hypothèses (à lever une par une)

- Parois et plaques rigides, fentes fermées ; air à 20 °C.
- Trou de table : 8 x 25 mm, table 8 mm, soupape loin (correction 0,85 x rayon) : DEVINÉS.
- Pentes du dessus et du fond du R12 non reprises (le script signale les cases entamées).
- `coupled_reeds` : un mode de lame, lame d'acier uniforme (`steel_reed`), levée et jeu
  devinés ; dans ce réseau, poussé et tiré donnent les mêmes taux (chaîne symétrique) : il
  ne distingue pas l'anche intérieure (dans la case) de l'anche extérieure.
