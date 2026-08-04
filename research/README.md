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
    config.py               constantes (voies audio, calibrations, grille DOE)
    audio.py                acquisition + génération (Behringer, sounddevice)
    excitation.py           sweep EM, diagramme de phase, résonances
    analysis.py             Praat/parselmouth : praat_calcs (Tresp, formants, pitch, HNR)
    impedance.py            impédance P/Q, puissance P·Q
    seuil.py                seuil d'auto-entretien (rampe + hystérésis)
    doe.py                  plan d'expériences (grille, orchestration temps réel)
    batch.py                analyse par lot d'une campagne HDF5 → plan_exp.csv
    plots.py                tracés de synthèse (impédance, Tresp, formants)
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
