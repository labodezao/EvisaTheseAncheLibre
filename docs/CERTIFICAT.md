# Certificat des lectures « sûres » (v63, 16/10/2026)

Application de l'audit Fable du 15/10/2026 (`J:\claude\audits\2026-10-17-accordeur-fable\RAPPORT-AUDIT.md`, R1 à R14). Règle d'Ewen : un accordeur
professionnel ne dit « sûr » que s'il peut le prouver ; zéro lecture « sûre » fausse (erreur de plus de 0,5 ¢ sur une anche), avec n'importe
quel micro.

## Le défaut de la v62 (mesuré)

Verdict lu comme l'interface le lit (`lireTick` : anche sans marge, phase résolue, prise saine), vérité de la fenêtre lue (R6), notes de
synthèse réalistes sur la grille tempérée (R7 : β ≤ 0,4, AM ≤ 0,2, raie étrangère, agitation, dérive, attaque, désaccord de 3 à 40 ¢) :

| Banc | v62 | v63 |
|---|---|---|
| Plan réaliste de l'audit (160 notes) | 134 posées, 61 premières lectures « sûr » fausses | 75 posées, 0 fausse |
| Hypercube latin, 300 conditions × 4 graines (1 200 notes) | 214 posées sur 300 (1 graine), 156 fausses (73 %) | 354 posées, **0 fausse** (< 0,85 % à 95 %), 512 lectures « sûr », 0 fausse |
| Validation, 64 conditions, graine jamais vue | — | 21 posées, 0 fausse |
| Plan A (criblage 2^(10-5) × 10, Ω = 0,3 ou 40 Hz) | 103 posées, 58 fausses | 0 posée : les extrêmes sont hors du domaine certifié (Ω de 0,2 à 25 Hz) |
| Super musette (3 anches), 300 conditions | 168 posées, 126 fausses (75 %) | 0 posée, « trois anches : lecture à confirmer » (R3, v64) |
| Plan C (chaîne micro : porte, suppression spectrale, compression, ronflement, horloge, bande coupée), 16 cellules × 20 notes | — | horloge calibrée : 0 fausse sur 58 lectures « sûr » ; non calibrée : 2 fausses (le biais d'horloge de 150 ppm vaut 0,26 ¢) ; avec porte : toujours refusé, « le micro a coupé le son » |
| Prise réelle H6 (27 notes du 14/10, vérité = verrou LR) | 9 posées avec vérité, 4 premières lectures fausses | 4 posées, 0 première lecture fausse (écart maximal 0,17 ¢) |
| Prise PC (micro USB, effet vocal Windows) | `gate` détecté : 0 « sûr » (v61) ; sans ce contrôle : 12 posées, 11 fausses | 0 « sûr » ; sans le contrôle de prise : 5 posées, 2 à +0,66 ¢ (écart propre à la chaîne PC, audit § 1.6) |

« Posées » = notes dont une lecture a été dite sûre dans les 6 s. Le temps de pose médian est de 4 à 6 s (la v62 posait en 0,75 s, à tort).
Le temps de pose est l'objet de la v64.

## Ce que fait le certificat (`web/js/dsp/certificat.js`, `nls-bessel.js`)

Une seconde lecture, indépendante du traqueur : le son brut des 3 dernières secondes (anneau de 8 s dans le moteur) est ajusté par le modèle
de deux anches à peigne de Bessel — raies à k f_r + nΩ, indice de modulation de phase proportionnel au rang k (β = 0,1 à 0,37 sur le H6),
modulation d'amplitude, warp commun (dérive et agitation du soufflet, nœuds toutes les 0,5 s) et niveau commun, raie étrangère libre
facultative, amplitudes complexes libres éliminées par moindres carrés (variable projection, jacobienne analytique du warp). Les deux
hypothèses d'étiquette sont ajustées (la seconde raie est une anche ; ou c'est la bande latérale de la première) et leur rapport de
vraisemblance (LLR) dit si l'étiquette est sûre. Fenêtre quelconque (R2). Le calcul est un générateur : 20 itérations (ou 15 ms) par image de
85 ms, il n'arrête jamais l'audio.

Une lecture n'est « sûre » que si tous les critères tiennent :

| | Critère | Seuil |
|---|---|---|
| C1 | pas de plage de zéros dans la fenêtre lue (R11) ; sinon la fenêtre repart après elle | 0,4 ms |
| C2 | peigne sain (R10) : résidu relatif du modèle, plancher entre les raies (partiels 1 et 2), indices de modulation | r ≤ 0,05 ; ≤ −28 dB ; β ≤ 0,45 |
| C3 | résolution des raies | K·Ω·T ≥ 1,5 |
| C4 | étiquette | LLR ≥ 25 |
| C6 | stabilité | dérive ≤ 0,5 ¢/s |
| C8 | accord de la lecture du moteur et de la seconde lecture | ≤ 0,3 ¢ |
| C9 | répétabilité : deux ajustements de fenêtres décalées d'au moins 0,5 s | ≤ 0,25 ¢ |

Les seuils ont été réglés sur le plan de calibration (300 conditions), jamais sur une prise réelle ; ils sont vérifiés sur le plan de validation
(autre graine) et sur le H6. Pas certifiée : la lecture reste affichée, « en cours », avec une marge de 1,5 ¢ (jamais « juste », jamais
validée) et UNE ligne qui dit pourquoi (R14) : `verification`, `trous`, `peigne`, `resolution`, `etiquette`, `stabilite`, `accord`, `domaine`, `trois`.

## Les autres recommandations

- **R4** : le partiel de mesure d'un unisson est abaissé quand une raie forte du spectre large bande (à ±60 ¢ du centre, à moins de 14 dB de la
  plus forte) sortirait de la bande du traqueur (`partielPourRaiesVues`, `plan.js`). Le plan d'une note imposée est décidé avant le premier
  spectre : il est revu dès que celui-ci arrive (`planAvecSpectre`). Cas de l'audit (1154 Hz, 8 Hz, 12 ¢) : lu à 0,01 ¢. Reste vrai en v63 :
  une anche désaccordée de 15 ¢ à k = 3 avec un fort indice de modulation voit sa bande latérale prise pour elle (appariement par cibles) ; le
  certificat la refuse (« accord »).
- **R5** (biais de modulation de phase au grave) : le certificat refuse ces lectures (0 faux au lieu de 30 à 50 %) ; la lecture juste est celle de
  la seconde lecture, montrée par l'option de la v64.
- **R6, R7, R8** : bancs `test/outils/pose/bench63.mjs`, `eval63.mjs`, `analyse63.py` (verdict de l'interface, vérité de la fenêtre lue,
  notes sur la grille, plans `plans/*.csv` faits par `outils/doe.py`).
- **R10, R11, R13, R14** : plancher et résidu par note ; fenêtre sans zéros ; micro à bande coupée (la seconde lecture ne dépend d'aucun partiel
  en particulier) ; messages fr/en (`refus …`), colonnes `refus`, `cert_*` du CSV de la section recherche.
- **Non faites en v63** : R3 (modèle à trois anches : la super musette n'est jamais dite sûre), R9 (coût : la seconde lecture prend 0,3 à 1 s de
  calcul sur PC, répartie sur les images), R12 (étalonnage de l'horloge par périphérique : `calibrationPpm` existe, pas l'écran), les temps de
  pose de la méthode (v64).

## Rejouer

```
node test/outils/pose/eval63.mjs --plan=lhs300_calib.csv --reps=4 --nls=0 --out=r.json     # moteur + certificat, verdict de l'interface
node test/outils/pose/analyse63.py r.json                                                  # (python) taux de « sûr » faux, par facteur
node test/outils/pose/runC.mjs --out=c.json                                                # plan C (CALIB=1 : horloge calibrée)
node test/outils/pose/reel_prises.mjs --src=h6|pc [--cert=0]                               # prises réelles du 14/10
node test/certificat.test.mjs
```
