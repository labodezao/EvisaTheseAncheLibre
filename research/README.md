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
    stochastic.py           Kramers-Moyal, potentiel, précurseurs, Stuart-Landau, cohérence, Kramers
    ramp.py                 rampes de bifurcation au banc (seuils répétés → diagramme stochastique)
    profile.py              profil statique d'anche au laser (courbure, déflexion)
    transfer.py             2 micros (impédance/absorption) + 4 micros (matrice de transfert, TL)
    ringdown.py             amortissement / facteur Q par décroissance (Matrix Pencil-like)
    material.py             module d'Young par résonance cantilever
    leak.py                 détection de fuite par décroissance de pression
    reed_oscillator.py       anche libre AUTO-OSCILLANTE alimentée en débit :
                             seuil de Hopf prédit par stabilité linéaire,
                             bande d'instabilité (démarrage + étouffement),
                             cycle limite, hystérésis sous-critique
    calibrate.py             calage d'une anche du modèle sur un son mesuré
                             (inverse le décalage dû au ressort d'air)
    hybrid.py                modèle physique GÉNÉRALISÉ (McIntyre-Schumacher-
                             Woodhouse) : anche libre, anche simple, anche double,
                             archet ; perce cylindrique/conique, corde, cavité
    identify.py              identification hybride depuis un son : conicité,
                             position d'archet, pente spectrale, nuance — en
                             séparant ce qui est mesuré de ce qui est supposé
    embedded.py              moteur TEMPS RÉEL embarquable (biquads + non-linéarité)
                             et génération du C pour STM32, sans ordinateur
    timbre.py                descripteurs de timbre génériques (bandes, platitude,
                             HPSS, spectre de modulation, bourdon, partiels/inharmonicité) —
                             généralise l'étude OSSO à tout enregistrement (numpy+scipy seuls)
    sample_extract.py        sample monophonique -> paramètres de modèle physique
                             (f0/vibrato, partiels, résonateur, source, attaque)
    synth_export.py          export du modèle : JSON, en-tête C (STM32), wavetable
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
    analyse_acoustique_osso.md  étude annexe : analyse acoustique du duo OSSO
    sample_vers_modele_physique.md  sample -> modèle physique -> STM32 / Dream
    audit_modele_anche.md    audit complet du modèle physique + corrections
    experiences_a_mener.md   liste des expériences à faire au banc
    references.bib          bibliographie BibTeX (docs + manuscrits LyX)
    figures/                figures générées par les scripts (cf. son README)
  scripts/
    analyse_osso.py         étude OSSO : script reproductible (librosa + Praat)
    diagnostic_reed_model.py  le modèle d'anche auto-oscille-t-il ? (code retour)
    valider_extraction.py   boucle extraction -> resynthèse -> écart spectral
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

### Intégration banc & capture matérielle

- **`ramp`** : `run_threshold_sweep` répète des rampes montée (pousser) /
  descente (tirer) au banc, détecte `μ_on`/`μ_off` par rampe et agrège en
  `threshold_stats` (seuil de bifurcation **stochastique**, moyenne ± écart-type)
  + diagrammes. Onglet **« Bifurcation »** côté acquisition.
- **`profile`** + firmware `SCAN` + onglet **« Profil laser »** : balayage d'un
  **capteur laser de déplacement** sur la table X → forme statique de l'anche,
  **courbure** et déflexion max (validation FEM, chapitre « Static shape »).
- **Voie accéléromètre** : `AudioConfig.accel_channel` + `audio.accel` ;
  capturée et stockée par le DOE (`Point.accel`) — réactive le
  `Mesures_Accelerations` des campagnes historiques.
- **Résonance cohérente** : onglet **« Résonance cohérente »** (charge plusieurs
  WAV, un par intensité de bruit → cohérence vs bruit, optimum).

## Étude annexe — analyse acoustique d'enregistrements (corpus OSSO)

En marge du banc, `scripts/analyse_osso.py` analyse deux pièces du duo breton
**OSSO**, qui transpose le couple biniou-bombarde à des synthétiseurs analogiques
— un cas témoin pour la **répartition des rôles en formation réduite**, question
directement pertinente pour l'accordéon (mélodie, bourdon, harmonie et conduite
rythmique portés par deux sources). Résultats et discussion :
[`docs/analyse_acoustique_osso.md`](docs/analyse_acoustique_osso.md) ; synthèse
d'une page dans `design_practical.lyx` (partie « Timbral elements »).

Ce script est **autonome** : il n'est pas importé par `banc_recherche` et ne
participe pas aux tests (qui restent numpy seul). Il demande l'extra
`pip install -e ".[musique]"` (librosa, parselmouth, soundfile, matplotlib).
Les **enregistrements ne sont pas versionnés** (droits d'auteur) : le script
s'arrête proprement s'ils sont absents.

### Descripteurs de timbre génériques (`timbre.py`)

`banc_recherche.timbre` généralise les calculs de l'étude OSSO qui n'ont pas
besoin de `librosa` (bandes spectrales, spectre de modulation, correction
d'octave métrique, platitude/rolloff/largeur de bande, HPSS par filtrage
médian) en un module **numpy + scipy seuls**, testé (`tests/test_timbre.py`),
applicable à **n'importe quel enregistrement** — pas seulement OSSO :
`scripts/analyse_osso.py` y délègue désormais ces calculs plutôt que de les
dupliquer. Deux fonctions nouvelles visent la caractérisation d'instruments à
**bourdon** (vielle à roue, cornemuse, accordéon) en vue d'un futur modèle
physique de synthèse (cf. `reed_model.py` pour l'anche libre) :

- `bourdon_strength(S, freqs, bande)` : à quel point une bande est « tenue »
  (stable dans le temps, concentrée en fréquence) — repère automatiquement où
  se trouve le bourdon d'un instrument.
- `harmonic_partials(S, freqs, f0, ...)` : série de partiels mesurée autour de
  `n·f0`, écart en cents à l'harmonique idéale — l'inharmonicité renseigne la
  raideur/l'amortissement du résonateur physique à modéliser.

**Note de reproductibilité** : `timbre.py` ne réimplémente pas les fonctions
`librosa.feature.*`/`librosa.effects.hpss` utilisées pour produire les
chiffres *publiés* de l'article OSSO (fenêtrage et marges différents) —
`analyse_osso.py` ne délègue que les calculs strictement identiques bit à
bit. Pour un nouvel enregistrement, sans chiffre publié à reproduire,
`timbre.py` est la voie recommandée.

## Du sample au modèle physique (STM32 / Dream)

Onglet **« Sample → modèle »** : on importe un **sample monophonique**, on en
extrait les paramètres d'un modèle **source → résonateur** (hauteur et
vibrato, niveaux et attaques des partiels, inharmonicité, biquads du
résonateur, pente de source, part de bruit, loi brillance ↔ niveau), et on
exporte vers une cible embarquée — c'est la démarche des instruments à modèle
physique type SWAM : le sample n'est pas le produit final, c'est une
**mesure**.

- `sample_extract.extract(y, sr)` → `SampleModel` (numpy + scipy seuls).
- `synth_export` → **JSON** (pivot), **en-tête C** pour un modèle tournant sur
  STM32 (biquads, flottant ou Q15), **wavetable** pour un moteur sampleur.

Le point critique est la séparation **source / résonateur** : le résonateur
doit être *invariant avec la note jouée*, sans quoi ce n'en est pas un —
d'où l'enveloppe estimée par les sommets des partiels, et un test dédié.
Fournis **plusieurs notes** du même instrument pour une identification
sérieuse.

`DreamAdapter` est délibérément **non implémenté** : le protocole du firmware
SAM5716 relève de la documentation constructeur, et inventer des registres
donnerait du code qui a l'air juste et ne pilote rien. Voir
[`docs/sample_vers_modele_physique.md`](docs/sample_vers_modele_physique.md)
pour les trois architectures possibles et les questions à poser à Dream.

## Modèle physique d'anche jouable (`reed_oscillator`)

Anche libre **alimentée en débit** (le soufflet impose une vitesse volumique,
la pression en résulte), couplée à une chambre. Le modèle **auto-oscille** et
prédit, pour l'anche de référence (sol2, premier mode 102,1 Hz) :

| Grandeur | Prédiction | À mesurer avec |
|---|---|---|
| Seuil de démarrage `p_on` | 25,8 Pa à 119 Hz | `seuil.detect`, rampe montante |
| Seuil d'extinction `p_off` | 19,4 Pa | rampe descendante |
| **Hystérésis** `p_on/p_off` | **1,33** (sous-critique) | le rapport des deux |
| Seuil d'étouffement | 379,8 Pa | pousser jusqu'à extinction |
| Excursion du bout | 0,96 mm à 1,5× le seuil | stroboscope de l'accordeur |

Le **seuil est prédit** par analyse de stabilité linéaire (`growth_rate`,
`instability_band`) : 1 ms par évaluation contre ~1 s de simulation. Tester
une variante de modèle coûte le temps de l'écrire, plus une après-midi.

Deux mécanismes que le modèle produit sans qu'on les lui demande :
l'**étouffement** quand on pousse trop fort (la languette soufflée hors de la
fente ne module plus le débit), et l'**hystérésis** sous-critique.

La liste des expériences de validation est dans
[`docs/experiences_a_mener.md`](docs/experiences_a_mener.md) ; l'audit qui a
mené là — y compris les erreurs commises et corrigées — dans
[`docs/audit_modele_anche.md`](docs/audit_modele_anche.md).

### Onglet « Synthèse physique »
On injecte des sons, on en extrait la hauteur, on cale une languette dont la
**fréquence de jeu** vaut celle du son (le ressort d'air décale la note :
+2,7 demi-tons sur une grosse anche de basse, +0,14 dans le médium), puis on
fait sonner le modèle et on compare les spectres. Sortie = `dq/dt`, le
rayonnement en champ lointain — une anche rayonne par le débit modulé, pas
par la pression de chambre.

## Tous les instruments, et le temps réel sur carte (`hybrid` / `embedded`)

`reed_oscillator` ne modélise qu'une chose : l'anche libre. `hybrid.py`
reprend la même physique dans le cadre qui la dépasse — celui de McIntyre,
Schumacher & Woodhouse (1983) : l'anche, l'archet et le jet de flûte sont
**un seul problème**, un excitateur non linéaire couplé à un résonateur
linéaire.

| famille | excitateur | résonateur | couple |
|---|---|---|---|
| accordéon, harmonica | anche libre | chambre (ressort d'air) | (p, q) |
| clarinette, saxophone | anche simple | perce | (p, q) |
| bombarde, cornemuse | anche double | perce conique étroite | (p, q) |
| violon, vielle à roue | frottement d'archet | corde | (v, F) |

L'accordéon est le cas dégénéré : son résonateur n'a **aucun mode**, juste une
compliance. C'est pour cette raison, et pour elle seule, qu'une anche libre
impose sa hauteur là où une anche de clarinette la reçoit.

```python
from banc_recherche import hybrid, identify, embedded

v = hybrid.build('clarinette', 147.0)        # ou saxophone, bombarde, violon…
r = v.simulate(1.0, level=2500.0, settle=0.3)

ident = identify.identify(son, sr, 'violon') # depuis un vrai enregistrement
print(ident.rapport())                       # mesuré vs supposé, séparés

p = embedded.params_from_voice(ident.voice)
embedded.export_c(p, "firmware/voix/")       # moteur + table, prêt à compiler
```

**Ce que le modèle prédit sans qu'on le lui demande** — même excitateur, seule
la perce change : clarinette +36,8 dB d'écart impairs/pairs (le son creux, le
registre à la douzième), saxophone +3,7 dB (série complète). Sur les cordes,
la loi de Helmholtz `v_archet·(1−β)/β` est retrouvée à 15 % près sans être
codée nulle part, et au-delà de 0,5 N d'archet le modèle devient chaotique —
la borne haute du diagramme de Schelleng, le craquement de l'archet trop
appuyé.

**Identification depuis un son.** Se mesurent vraiment : la hauteur, la
conicité de la perce (écart pairs/impairs), la position d'archet (le creux
dans la série harmonique donne β = 1/n — bouclage exact à 1/7 et 1/9), la
pente spectrale, la nuance. Restent supposés : la famille d'excitateur, les
dimensions d'anche, la masse de corde. `Identification.rapport()` imprime les
deux colonnes séparément, parce qu'un paramètre supposé qu'on prend pour
mesuré est la façon la plus sûre de se tromper longtemps.

**Temps réel sur STM32.** Le RK4 coûte 114 MFLOP/s par voix — une voix et
demie sur un F4. En passant la partie linéaire en biquads et en ne
suréchantillonnant que la non-linéarité : **32 MFLOP/s**, soit ~5 voix sur un
STM32F4 et ~15 sur un H7. Le portage préserve la hauteur à moins d'un cent
(6,7 cents pour le violon), et le C généré calcule exactement comme la
référence Python (corrélation 1,000000 sur les premiers échantillons). Il
compile sans aucun avertissement en `-Wall -Wextra -Wpedantic`, sans
allocation, sans `printf`, avec `sqrtf` pour seule dépendance à `libm`.

Le Dream SAM5716 n'est pas la bonne puce pour ça : c'est un moteur de lecture
d'échantillons, pas un DSP à boucle de rétroaction. Un STM32 + un codec, même
boîte, même prix, et ça calcule vraiment un modèle physique.

**TUTT comme moteur du résonateur — et une erreur retrouvée dans son
source.** Le calcul d'impédance de perce découpait les cônes en cylindres
empilés. Le cylindre sortait juste, le cône sortait faux d'un demi-ton : au
lieu de l'octave il donnait `tan(kL)=kL`, la signature d'un tube fermé au
petit bout. Le source Fortran de TUTT (`Perce2.for`, `Ltran9.for`) donne la
réponse en trois lignes : un tronçon tronconique porte des ondes
**sphériques**, `p(x) = (A·e^{jkx} + B·e^{−jkx})/(1 + Δx)` avec la conicité
`Δ = (DL−D0)/(D0·L)`, et ce sont les termes en `Δ` — perdus par tout
empilement de cylindres — qui font qu'un cône est un cône. Implémenté tel
quel (`tutt._z_troncon`), le cylindre ne bouge pas et le cône donne enfin
**1 : 2,02 : 3,06 : 4,12**. Un tronçon se traite en un seul pas : plus juste
*et* plus rapide.

La boucle se referme avec la **cavité d'anche** de Ninob (*Modes propres d'un
tronc de cône*) : un cône tronqué a son octave +95 cents trop haute, et
1,5 cm³ de cavité au petit bout la ramène à +2 cents — c'est ce qui permet à
un saxophone d'octavier juste, et le paramètre `reed_volume_m3` existait déjà
sans qu'on sache à quoi il servait.

`clarinette` passe donc par `engine='tutt'` (0,3 cent d'écart médian sur la
tessiture). Les trois coniques gardent la série postulée pour le jeu : la
physique est juste, mais une perce conique idéalisée **à un seul tronçon** a
un fondamental trop faible (2ᵉ sommet 3 dB au-dessus du 1ᵉʳ), et l'anche s'y
accroche — la note sortirait une octave trop haut. Le calcul conique exact
sert à tout ce qui passe par une **vraie** perce. Détail, mesures et ce qui
reste à faire : `docs/modele_hybride_generalise.md`, §9.

**Une vraie perce, jouée par ses doigtés.** Les trous latéraux sont posés
(chaque cheminée est un tuyau de plus, branché en dérivation, ouvert ou fermé
selon le doigté), donc `live.build_instrument_from_bore` sait prendre une
perce — **une seule pièce**, celle du fichier — calculer chacun de ses
doigtés et ranger les notes obtenues sur le clavier. La géométrie ne bouge
pas : ce sont les doigts qui changent la note, comme sur l'instrument. Et la
justesse n'y est **pas** corrigée, contrairement au reste du dépôt : l'écart
entre ce que la perce donne et ce qu'elle devrait donner est précisément le
résultat qu'on vient chercher. C'est le rapport de justesse d'une perce — ce
pour quoi TUTT existe — sauf qu'on peut maintenant aussi l'écouter.

```python
from banc_recherche import tutt, live
dat = tutt.read_dat("ma_bombarde.dat")
inst = live.build_instrument_from_bore(dat, famille='bombarde')
for nom, trous, f_hz, note in inst.fingerings:
    print(nom, round(f_hz, 1), "Hz")
```

## Jouer le modèle au clavier MIDI (`live`)

Tout ce qui précède calcule juste mais **ne joue pas** : `hybrid` intègre en
RK4, `embedded.RealtimeVoice` boucle en Python, et l'un comme l'autre mettent
plusieurs secondes à produire une seconde de son.

La solution était déjà écrite. `embedded` génère un moteur C temps réel pour
le STM32 ; `live.py` le compile en bibliothèque partagée et l'appelle par
`ctypes`. **Le même code que sur la carte**, à vitesse native — et donc, en
prime, une vérification permanente que ce qui part sur la carte fonctionne.

```python
from banc_recherche import live
inst = live.build_instrument('cornemuse', lo=48, hi=84)   # une perce par note
synth = live.Synth(inst, polyphony=6)
synth.note_on(60, velocity=100)
bloc = synth.render(256)                                   # float32, mono
```

Mesuré, à 48 kHz : **×137 le temps réel** à une voix, ×76 à deux, ×40 à
quatre, ×26 à six. Une préparation d'instrument (49 notes, accordage compris)
prend environ trois secondes.

**Chaque note a sa propre géométrie** — c'est un modèle physique, pas un
échantillon transposé. Et chaque note est ensuite **accordée sur le moteur** :
on mesure ce qu'elle joue vraiment, on corrige la cote, on remesure. Un modèle
physique ne joue jamais la fréquence qu'on lui dessine (correction de
pavillon, tirage de l'anche, raideur de la chambre : de 1 à 40 cents selon la
note). Ce qu'on corrige est la **géométrie**, pas la sortie — le timbre et le
transitoire restent ceux de l'instrument accordé. Résultat sur trois octaves,
les sept instruments : **écart médian 0,1 à 0,6 cent**, aucun dépassant 7.

**L'accordéon a fait apprendre quelque chose.** Garder la languette du la
grave pour jouer dans l'aigu ne donne pas un son aigu : ça ne donne aucun
son. Au-dessus de 185 Hz la languette se couchait simplement dans le courant
d'air. Les cotes suivent maintenant la note, par similitude géométrique
(`L, largeur, épaisseur ∝ 1/f`, donc `m ∝ 1/f³`) — et le volume de chambre en
`1/f³`, qui n'est pas un choix mais une conséquence : pour que le couplage
anche↔chambre garde la même force d'une note à l'autre, il faut
`A²/(C·m·ω²)` constant, où l'exposant de la géométrie s'élimine de lui-même.
Ça tombe sur l'ordre de grandeur des cellules d'un vrai sommier.

L'attaque n'est pas une enveloppe plaquée : c'est le temps que met
l'oscillation à s'installer, et un `note_off` ne coupe pas le son — il ramène
la pression à zéro et **l'oscillation s'éteint d'elle-même**, avec son
hystérésis. C'est le point de tout l'exercice.

### Sans GUI, sans MIDI, sans carte : `banc-recherche-jouer`

Le moteur n'a besoin de rien d'autre qu'un compilateur C. Tout le reste est
optionnel, et la ligne de commande le montre :

```bash
banc-recherche-jouer --liste                    # instruments, sorties, ports MIDI
banc-recherche-jouer cornemuse                  # clavier d'ordinateur
banc-recherche-jouer violon --midi "LPK25"      # vrai clavier MIDI
banc-recherche-jouer accordeon --wav essai.wav  # aucune carte son requise
```

Au clavier d'ordinateur, disposition de tracker (AZERTY par défaut, `--disposition
qwerty` sinon) : `w x c v b n , ;` pour les blanches, `s d g h j` pour les
noires, `1`/`2` pour l'octave, `3`/`4` pour la nuance, `0` pour tout couper.

Un terminal ne signale **pas** le relâchement d'une touche — il n'envoie que
des caractères. C'est donc la **répétition automatique** du clavier qui sert de
touche tenue : tant qu'elle arrive la note reste soufflée, et dès qu'elle
cesse on relâche. Contrainte du terminal, pas du moteur : en MIDI le
relâchement est exact.

`--brut` désactive l'accordage, pour entendre ce que la géométrie donne
avant retouche.

### Windows et macOS

Le source C ne change pas d'un octet — c'est celui qui part sur la carte.
Seuls l'extension du fichier (`.dll`, `.dylib`, `.so`), le compilateur et ses
options diffèrent, et `live.py` s'en occupe.

Sur **Windows**, il faut un compilateur C ; le plus simple est un gcc :

- **MSYS2** → `pacman -S mingw-w64-ucrt-x86_64-gcc`, puis ajouter son `bin/`
  au `PATH` ;
- **w64devkit** — une archive à dézipper, rien à installer ;
- **Visual Studio Build Tools** — ouvrir « x64 Native Tools Command Prompt »
  et lancer depuis là.

Ou, si le compilateur est ailleurs : `set CC=C:\chemin\vers\gcc.exe`.

gcc est cherché **avant** MSVC, et pas par préférence de goût : `gcc -shared`
exporte ses symboles tout seul, là où `cl /LD` n'exporte rien sans qu'on lui
donne la liste. MSVC marche quand même — un `.def` est généré pour lui — mais
c'est un détour. Sous MinGW, `libgcc` est lié statiquement, sinon la DLL se
compile très bien et refuse de se charger dès que MinGW n'est pas dans le
`PATH` du Python qui l'ouvre.

La lecture du clavier passe par `msvcrt` au lieu de `termios` ; la disposition
(AZERTY, QWERTY…) reste l'affaire du système, qui envoie le caractère et non
la position de la touche.

Sur **macOS** : `xcode-select --install` suffit.

Ces chemins sont couverts par des tests qui font croire au module qu'il est
ailleurs — ils tournent donc partout. Mais ils vérifient les commandes
produites, pas un vrai Windows : **le moteur n'a encore tourné que sur
Linux**.

### Onglet « Jouer (MIDI) »

Choisir un instrument, **Préparer**, **▶** pour ouvrir la sortie audio,
brancher un clavier. Molette (CC1) ou contrôleur à vent (CC2/CC11) pour la
nuance, réévaluée à chaque bloc — toutes les 5 ms. Un clavier de test à
l'écran permet de jouer sans matériel MIDI, et l'export WAV enregistre
l'attaque, la tenue et l'extinction physique.

L'entrée MIDI demande `mido` + `python-rtmidi` : `pip install -e ".[live]"`.
Le reste marche sans — le moteur se compile avec le `cc` du système et sort
par `sounddevice`.

### Onglet « Instruments (hybride) »

Choisir une famille, injecter un son (facultatif), écouter, exporter le WAV
ou **le code C pour la carte**. Le rapport affiche le coût embarqué estimé et
le nombre de voix tenables.

Détails, limites assumées et expériences de recalage :
`docs/modele_hybride_generalise.md`.

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
pip install -e ".[musique]"              # optionnel : étude OSSO (librosa…)
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
