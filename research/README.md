# Banc de recherche — mesure haute précision (Python)

Module **recherche** : banc de mesure et d'essais des anches libres, distinct du
banc d'**accordage** (`../firmware/` + onglet « Banc » de l'accordeur web). Ici
la priorité est la **précision scientifique** et la **reproductibilité** des
plans d'expériences, pas l'ergonomie temps réel.

Ce dossier **modernise** l'ancienne chaîne PC (`MesAnche.py`, `ValControl.py`,
`Mesures.py`, `Data_analysis.py`, `enveloppepraat.py`, `mes_seuil_autoentretien.py`)
qui reposait sur `rshell` + `pyaudio` + HDF5 + Praat lancé à la main. Elle est
remplacée par un **package Python** unique, testable, avec une GUI.

## Ce que fait le banc de recherche

- **Excitation électromagnétique** de l'anche via **OUTTA** et une interface
  **Behringer USB 24 bits** (1 entrée stéréo + 1 entrée mono) — signal analogique
  propre généré côté PC. C'est le point qui **quitte** le firmware ESP32 : le
  micro-contrôleur ne fait plus l'EM.
- **Balayage en fréquence** (sweep) → **diagramme de phase**, **fréquences de
  résonance**, **couplage modes cavité ↔ anche**.
- **Mesure d'impédance** acoustique/mécanique (P/Q) et **puissance hydraulique**
  (P·Q), comme `Data_analysis.py`.
- **Analyse Praat** (via `parselmouth`) : temps de réponse `Tresp`, enveloppe,
  formants F1–F4 (modes de cavité), pitch de référence.
- **Seuil d'auto-entretien** : rampe de pression montante/descendante avec
  hystérésis (reprise de `mes_seuil_autoentretien.py`).
- **Plan d'expériences** Section × Pression × Clapet × Position (DOE complet,
  reprise de `Mesures.py`) avec stockage **HDF5** et export `plan_exp.csv`.

> Le banc de recherche partage le **matériel pneumatique** (soufflet motorisé,
> capteurs, vanne) avec le banc d'accordage : il peut piloter le même firmware
> ESP32-S3 via son lien série/WebSocket pour la partie air, tout en gérant
> l'excitation EM et l'acquisition haute résolution côté PC.

## Architecture

```
research/
  pyproject.toml            dépendances + entry point `banc-recherche`
  requirements.txt          pip (numpy/scipy/parselmouth/h5py/pandas/sounddevice/PyQt6/pyqtgraph)
  banc_recherche/
    __init__.py
    __main__.py             `python -m banc_recherche` → CLI
    cli.py                  ligne de commande (batch, devices, gui)
    config.py               constantes (voies audio, calibrations, grille DOE)
    audio.py                acquisition + génération (Behringer, sounddevice)
    excitation.py           sweep EM, diagramme de phase, résonances
    analysis.py             Praat/parselmouth : praat_calcs (Tresp, formants, pitch, HNR)
    impedance.py            impédance P/Q, puissance P·Q
    seuil.py                seuil d'auto-entretien (rampe + hystérésis)
    bifurcation.py          diagrammes de bifurcation, forme normale de Hopf, hystérésis
    stochastic.py           Kramers-Moyal (drift/diffusion), potentiel effectif, précurseurs
    transfer.py             2 micros (impédance/absorption) + 4 micros (matrice de transfert, TL)
    ringdown.py             amortissement / facteur Q par décroissance (Matrix Pencil-like)
    material.py             module d'Young par résonance cantilever
    leak.py                 détection de fuite par décroissance de pression
    doe.py                  plan d'expériences (2 modes : pression, ou soufflet STROKE pousser/tirer)
    batch.py                analyse par lot d'une campagne HDF5 → plan_exp.csv
    plots.py                tracés de synthèse + graphes DOE (effets, interactions, Pareto, contour)
    doe_analysis/           analyse de plans d'expériences (équivalent Minitab)
      model.py              ajustement factoriel/RSM, ANOVA, effets, R²/R²aj/R²préd
      design.py             générateurs (factoriel, fractionnaire, Plackett-Burman, CCD, Box-Behnken)
      optimize.py           optimiseur de réponses par désirabilité
      taguchi.py            rapports signal/bruit (robustesse)
      stats.py              distributions t/F (p-valeurs) sans scipy
    bench_link.py           lien vers le firmware ESP32 (air : soufflet, vanne, section)
    storage.py              HDF5 + export CSV (schéma `plan_exp`)
    campaigns.py            relecture des campagnes existantes (HDF5/npy de la thèse)
    gui/
      __init__.py
      app.py                GUI UNIQUE PyQt6 à onglets (entry point `banc-recherche`)
  docs/
    design_theory.lyx       manuscrit « Conceptual accordion design : Theory »
    design_practical.lyx     manuscrit (pratique)
    DATA.md                 manifeste : dépôt vs Drive, gros .npy, CAO, fileIds
  scripts/
    legacy/                 sources d'origine vendorisées (référence, non exécutées)
  tests/
    test_analysis.py
    test_impedance.py
```

## Une seule GUI (remplace la constellation de scripts)

Avant : une dizaine de scripts séparés lancés à la main (`MesAnche`, `Mesures`,
`Data_analysis`, `enveloppepraat`, `mes_seuil_autoentretien`, `plotsmeasure`,
`valvecontrol`…). Maintenant : **une** application (`banc-recherche`) à onglets,
chacun pilotant un module :

| Onglet | Ancien script | Module |
|---|---|---|
| Connexion / air | `ValControl`/`valvecontrol` | `bench_link` |
| Excitation EM | (AD9833 firmware → PC) | `excitation` |
| Analyse anche | `Data_analysis` / `enveloppepraat` | `analysis.praat_calcs` |
| Impédance | `Data_analysis` | `impedance` |
| Seuil auto-entretien | `mes_seuil_autoentretien` | `seuil` |
| Plan d'expériences | `Mesures` | `doe` + `storage` |
| Campagnes | `Data_analysis` (boucle HDF5) / `plotsmeasure` | `campaigns` + `batch` + `plots` |

L'onglet **Campagnes** rejoue toute une grille déjà mesurée (`batch.analyse_campaign`) :
il reconstruit chaque son, applique `praat_calcs`, calcule l'impédance et écrit
`plan_exp.csv` — exactement les 16 colonnes de l'ancien `Data_analysis.py`.

## Analyse DOE (équivalent Minitab)

`banc_recherche.doe_analysis` reproduit l'essentiel de la suite DOE de Minitab,
**sans dépendance lourde** (p-valeurs t/F via bêta incomplète maison) :

- **Ajuster le modèle** (`model.fit` / `analyze`) : effets principaux +
  interactions [+ termes quadratiques pour surface de réponse], coefficients,
  erreurs-types, T, P, **effets**, **ANOVA** (SS/df/MS/F/P, manque d'ajustement
  + erreur pure si réplicats), **R² / R²-ajusté / R²-prédit (PRESS)**.
- **Graphes** : effets principaux, interactions, **Pareto des effets**, contour
  de réponse (`plots.*`).
- **Générateurs de plans** : factoriel complet/fractionnaire, Plackett-Burman,
  composite centré (CCD), Box-Behnken (`design.*`).
- **Optimiseur** de réponses par **désirabilité** (`optimize`).

- **Taguchi** (`taguchi`) : rapports signal/bruit (plus-grand/plus-petit/
  nominal = mieux) pour la **robustesse** des anches.

Onglet GUI **« Analyse DOE »** : charge un `plan_exp.csv`, choisis facteurs et
réponse → résumé type Minitab (coefficients + ANOVA), boutons effets/Pareto/
optimiseur. En ligne : `da.analyze(df, "Freq0", ["S_plus","P_plus","i_Clap"])`.

## Bifurcation & physique stochastique des anches

L'anche est un **oscillateur auto-entretenu non linéaire** : son seuil
d'oscillation est une **bifurcation de Hopf** (sous-critique ⇒ hystérésis
`p_on > p_off`, typique des anches). Modules dédiés :

- **`bifurcation`** : diagramme amplitude(paramètre) montée/descente, seuils
  `μ_on`/`μ_off`, classification **super/sous-critique**, ajustement de la forme
  normale de Hopf/Stuart-Landau (`A² ∝ μ − μc`).
- **`stochastic`** : reconstruction de la dynamique de Langevin par les
  coefficients de **Kramers-Moyal** (drift `D₁`, diffusion `D₂` — approche
  Friedrich-Peinke), **potentiel effectif** (un puits = monostable, deux =
  bistable), **signaux précurseurs** (ralentissement critique : variance et
  autocorrélation croissantes, tau de Kendall), et **statistiques de seuil
  stochastique** (le bruit rend le point de bifurcation distribué).
  - **Fit direct de Stuart-Landau** (`stuart_landau_fit`) : sur l'amplitude
    complexe (signal analytique), régression de `dz/dt = (μ+iω)z − (a+ib)|z|²z`
    → **coefficient de Landau complexe** `a+ib` (a = saturation d'amplitude,
    b = glissement de fréquence dépendant de l'amplitude = « frequency pulling »).
  - **Résonance cohérente** (`coherence_resonance`) : la cohérence (temps de
    corrélation) passe par un **maximum à un bruit intermédiaire** optimal.
  - **Temps de résidence / échappement de Kramers** (`residence_times`,
    `kramers_rate`, `kramers_from_potential`) : près du seuil sous-critique, le
    bruit fait sauter entre l'anche muette et l'anche qui sonne ; taux
    d'échappement `r = (1/2π)√(U″_min·|U″_barr|)·e^{−ΔU/D}`.

Onglet GUI **« Bifurcation »** : diagramme depuis une rampe CSV (param, amp), ou
analyse Kramers-Moyal + potentiel depuis une série temporelle (WAV). Les seuils
mesurés (via `seuil.detect`) et leur dépendance aux facteurs (section, clapet…)
s'analysent ensuite avec `doe_analysis`.

## Pourquoi Python (et pas Java)

L'ancienne chaîne est **entièrement en Python scientifique** : `numpy`, `scipy`,
`parselmouth` (Praat), `h5py`, `pandas`. Réécrire en Java imposerait de recoder
ou d'appeler Praat/numpy par des ponts fragiles, sans gain. On garde Python et on
**structure** : package installable, GUI **PyQt6** + **pyqtgraph** (tracés temps
réel rapides), tests. Si une distribution binaire s'avère nécessaire,
`pyinstaller` couvre le besoin.

## Installation

```bash
cd research
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # ou : pip install -e .
banc-recherche                           # lance la GUI
```

### En ligne de commande (sans GUI)

Pour rejouer une campagne en lot (serveur, reproductibilité) :

```bash
banc-recherche-cli batch data/Measure_dataset_….hdf5 --plots out/   # → plan_exp.csv + figures
banc-recherche-cli devices                                          # liste les entrées audio (Behringer)
banc-recherche-cli gui                                              # équivaut à `banc-recherche`
python -m banc_recherche batch camp.hdf5                            # même CLI via -m
```

### Tests

```bash
pip install pytest && pytest        # impédance, enveloppe/Tresp, DOE, seuil, batch, CLI
```

Les modules à dépendances lourdes (`pandas`, `scipy`, `parselmouth`, `PyQt6`)
sont importés **paresseusement** : le package s'importe et les tests numériques
tournent avec `numpy` seul.

`parselmouth` (Praat) : `pip install praat-parselmouth`. L'interface Behringer
est vue comme un périphérique **ASIO/CoreAudio/ALSA** standard par `sounddevice` ;
sélectionne les voies dans `config.py` (`AUDIO_DEVICE`, `IN_CHANNELS`, `OUT_CHANNELS`).

## Correspondance ancien → nouveau

| Ancien script | Nouveau module |
|---|---|
| `MesAnche.py` (mesure d'une anche) | `audio.py` + `analysis.py` |
| `ValControl.py` (contrôle des actionneurs) | `bench_link.py` |
| `Mesures.py` (DOE Section×Pression×Clapet×Ppos, HDF5) | `doe.py` + `storage.py` |
| `Data_analysis.py` (Praat : Tresp, formants, P/Q, P·Q) | `analysis.py` + `impedance.py` |
| `enveloppepraat.py` (enveloppe) | `analysis.py` |
| `mes_seuil_autoentretien.py` (seuil, hystérésis) | `seuil.py` |
| `plotsmeasure.py` (tracés) | `gui/app.py` (pyqtgraph) |

## État

Squelette posé (modules + signatures + GUI minimale). Le portage du corps de
chaque ancien script se fait module par module ; les tests figent le
comportement numérique attendu (impédance, Tresp) au fil du portage.
