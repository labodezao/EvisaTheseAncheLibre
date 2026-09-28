# Outils d'analyse de l'accordeur

Pour comprendre une session enregistrée par l'accordeur (bouton « Exporter
la session » → ZIP : WAV + CSV + JSON) et vérifier une correction **avant**
de la publier. Principe : ce que la courbe affiche n'est accepté que si le
spectre le confirme — la nature ne ment pas, la mesure si.

| Outil | Rôle |
|---|---|
| `csv_resume.py session.csv` | ce que l'appli a **affiché**, par note et par anche (médiane, étendue, sauts > 1 ¢) |
| `rejoue.mjs session.wav '<réglages>' [t0 t1] [--images]` | rejoue le WAV dans le moteur actuel (hors navigateur) ; `--images` : une ligne par image |
| `bande.py session.wav t0 t1 f_bas f_haut [fenêtre pas]` | **vérité terrain** : les raies réelles d'une bande au cours du temps |
| `esprit.py note.wav [f0] [t0 t1]` | sépare 2–3 anches d'un même ton (musette, trémolo) sous la limite de Fourier |
| `banc_musette.mjs` | banc synthétique musette sur les trois modes (aucun enregistrement) |

Comparer deux versions du moteur : `ENG=chemin/vers/engine.js node test/outils/rejoue.mjs …`
(extraire l'ancienne avec `git show <commit>:web/js/dsp/engine.js`, dans un
dossier qui contient aussi les autres fichiers de `web/js/dsp/` de ce commit).

## Démarche qui a marché (v23 → v27)
1. `csv_resume.py` sur le CSV : repérer le segment suspect (note, anche, instant).
2. `bande.py` autour de la fondamentale (et d'un partiel, p. ex. ×2 ou ×3) : la
   raie existe-t-elle ? bouge-t-elle vraiment ? Deux anches ? Une raie d'une
   AUTRE anche (octave, quinte) à côté ?
3. `rejoue.mjs --images` sur quelques secondes : quelle valeur, quel drapeau
   (M confondue avec l'octave, h maintenue, r estimation rapide).
4. Trouver le **mécanisme physique** (partiels qui se superposent, repli de la
   décimation, inversion du soufflet…) — jamais un réglage sur un fichier :
   ça doit valoir pour tous les accordéons.
5. Écrire un test **synthétique** qui reproduit le mécanisme et échoue sur
   l'ancien moteur (`test/dsp.test.mjs`), corriger, puis rejouer toutes les
   sessions disponibles dans tous les modes pour vérifier qu'il n'y a pas de
   régression.

Dépendances : Node ≥ 18 ; Python 3 avec numpy et scipy (pour `bande.py`, `esprit.py`).
