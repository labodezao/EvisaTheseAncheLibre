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
| `images.mjs son.wav '<réglages>' t0 t1 [bruit_dB]` | chaque image du moteur en JSON (anches, drapeaux, fenêtre du traqueur) ; bruit blanc optionnel |
| `verite_poly.py son.wav t0 t1` | **vérité terrain polyphonique** hors moteur : ESPRIT par amas de raies, anches = partiels dont f/k concordent |
| `compare_poly.py passages_poly.json dossier sortie.json [--bruit]` | moteur contre vérité, image par image, sur la même fenêtre de son ; `resume_poly.py sortie.json [--frise]` pour lire |
| `avant_apres_poly.py avant.json apres.json` | deux sorties de `compare_poly.py` côte à côte (médiane, max, couverture par anche) et la liste de ce qui se dégrade : la mesure d'une correction |
| `boucles_dirks.py passages_poly.json dossier_wav sortie P15 P16 …` | boucle de 28 s de la partie stable de chaque passage, à faire écouter à un autre accordeur ET à l'accordeur (même signal) ; `segments.json` pour la vérité |
| `joue_cable.ps1 -wav boucle.wav` | joue un WAV vers « CABLE Input » (VB-Cable) sans toucher la sortie par défaut de Windows |
| `cable_vb.ps1 -id <point> -visible 1\|0` | active ou désactive un point audio comme le panneau Son, sans droits administrateur |
| `confondu_poly.py passages_poly.json dossier [P03 …]` | 8' confondu avec l'octave : estimation du moteur et sa marge face à la vérité ESPRIT de la même fenêtre, et l'erreur de l'ancienne valeur (la raie commune) |
| `paliers.py session.wav images.jsonl sortie.csv` | paliers de soufflet d'une anche seule (creux, sauts), référence courte de 0,25 s, pente ¢/dB dans le palier, valeur du moteur à +1 s et à la fin (audit du 10/10/2026) |
| `intervalles_reels.mjs son.wav '<réglages>' t0 t1 [t0 t1 …]` | battements d'intervalles (quinte, octave, tierces…) mesurés, voulus et par l'enveloppe, sur des passages réels (§ 4.4) |
| `confondu_grille.mjs separation\|derive\|stable` | 16'+8' de synthèse : erreur des lectures que le moteur dit séparées (selon le temps depuis la séparation), ou part des images confondues dont la vérité est dans la marge, par rapport d'amplitude et par méthode (§ 4.3) |

Essais polyphoniques du 06/10/2026 (18 passages réels, défauts et tests qui échouent) :
`docs/POLYPHONIE-ESSAIS.md` et `test/polyphonie.test.mjs` (`npm run test:poly`, hors `npm test`).

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
