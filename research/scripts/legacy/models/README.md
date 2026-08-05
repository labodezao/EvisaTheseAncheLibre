# Modèles d'anche — sources d'origine (Drive « anches models »)

Tes conversions Python des modèles MATLAB `.m`, gardées comme **référence** du
portage vers le package `banc_recherche`.

## Présent ici
- `km.py` — matrices **K/M des modes propres** (Euler-Bernoulli multi-tronçon,
  intégrales sympy des déformées → `eig` généralisé → fréquences). Porté (et
  rendu rapide par intégration numérique) dans **`banc_recherche/modal.py`**.

## À récupérer si besoin (fileId Drive, dossier « anches models »)
| Fichier | fileId | Rôle | Porté dans |
|---|---|---|---|
| `reedgui.py` | `1WYQOCAjEBBy_3yYj4Au6Aidfd9jhQPlx` | modèle **anche+cavité** complet (RK4) + GUI Tkinter | `banc_recherche/reed_model.py` |
| `reedgui_support.py` | `1h0nAMY4paB3qC7ro4wpBUbFVMQCjkYIg` | fonctions support du modèle | `reed_model.py` |
| `reedgui.py.bak.py` | `1wGktAJShKT8W_yE_jJKiw8-xHv95z_Xd` | sauvegarde | — |
| `mdof_modal_enforced_acceleration_rk4.py` | `1Wv9CzMDBtTeIAoc1KlSh9yHGwlA-kbhn` | RK4 modal multi-DDL (accélération imposée) | `reed_model.py` |
| `matkmgui.py` | `1dE_fJYb4rC4QoNWWlCkbGgbunLxSJHU4` | GUI matrices K/M | `modal.py` + `gui` |

Dossier FRF (mesure de la réponse en fréquence par balayage sinus synchronisé) :
`Python_Synchronized_Swept_Sine.ipynb`, scripts **PyTTa** — portés dans
**`banc_recherche/frf.py`**.

## Correspondance modèle → mesure (le fil de la thèse)
- `km.py` / `modal.py` **prédit** les fréquences propres de l'anche.
- `frf.py` les **mesure** (balayage sinus, quelques euros de matériel : carte son
  + un petit accéléromètre piézo — **pas besoin de vibromètre laser**).
- `reed_model.py` **simule** l'auto-oscillation → portraits de phase, à comparer
  à l'anche réelle (accéléromètre → `phase_space`).
