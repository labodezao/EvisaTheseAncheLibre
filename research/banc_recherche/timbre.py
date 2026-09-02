"""Descripteurs de timbre génériques pour instruments à bourdon.

Généralise les analyses menées sur le corpus OSSO (`scripts/analyse_osso.py`,
`docs/analyse_acoustique_osso.md`) en un outil réutilisable sur **n'importe
quel enregistrement** : le duo, ou des instruments à bourdon — accordéon
diatonique, vielle à roue (chanterelle/trompette/bourdons), bombarde,
cornemuse (biniou kozh). Objectif à terme : ces descripteurs (bande passante
occupée, force de bourdon, série harmonique/inharmonicité) alimentent des
**modèles physiques de synthèse** (source excitée + résonateur), dans l'esprit
de ce que fait OSSO pour l'accordéon avec des oscillateurs analogiques —
cf. `reed_model.py` pour l'anche libre, à étendre aux autres familles.

Tout est **numpy + scipy seuls** (dépendances déjà requises par le paquet,
cf. `pyproject.toml`) : aucun import paresseux nécessaire, testable sans
`librosa`/`parselmouth` — dans l'esprit de `leak.py`. Les fonctions sont pures
(pas d'impression, pas d'I/O) : un appelant (script, GUI, notebook) décide de
la mise en forme.

Attention reproductibilité : ce module n'est **pas** un remplacement des
appels `librosa.feature.*`/`librosa.effects.hpss` utilisés par
`analyse_osso.py` pour produire les chiffres publiés dans l'article OSSO —
une réimplémentation maison de la platitude spectrale ou du HPSS donnerait des
valeurs légèrement différentes de celles de librosa (fenêtrage, tailles de
noyau). `analyse_osso.py` ne réutilise donc de ce module que les calculs
strictement identiques bit à bit (répartition en bandes, spectre de
modulation, correction d'octave métrique). Pour un nouvel enregistrement où
aucun chiffre publié n'est à reproduire, les fonctions ci-dessous (STFT,
platitude, HPSS, bourdon, partiels) sont la voie recommandée.
"""
from __future__ import annotations

import numpy as np
from scipy import stats
from scipy.ndimage import median_filter

# ---- bandes par défaut (reprises de l'étude OSSO) --------------------------
SPECTRAL_BANDS = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
                   (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]

MODULATION_BANDS = [(20, 120, 'grave'), (120, 800, 'bas-médium'),
                     (800, 3000, 'médium'), (3000, 10000, 'aigu')]

SUBDIVISIONS = {0.25: 'ronde', 0.333: 'blanche pointée', 0.5: 'blanche',
                1.0: 'noire', 2.0: 'croche', 4.0: 'double-croche'}


# ==============================================================================
# STFT (numpy seul) et enveloppes temporelles
# ==============================================================================

def stft_mag(y, sr, n_fft=2048, hop_length=None):
    """Magnitude STFT en numpy seul (fenêtre de Hann, trames non centrées).

    Renvoie `(S, freqs, hop_length)` avec `S` de forme (n_fft//2+1, n_frames).
    Suffisant pour des descripteurs globaux (bandes, platitude, modulation) ;
    ne cherche pas à reproduire bit à bit `librosa.stft` (qui centre les
    trames par défaut) — voir note de reproductibilité en tête de module.
    """
    y = np.asarray(y, dtype='float64')
    if hop_length is None:
        hop_length = n_fft // 4
    window = np.hanning(n_fft)

    if y.size < n_fft:
        y = np.pad(y, (0, n_fft - y.size))
    n_frames = 1 + (y.size - n_fft) // hop_length

    S = np.empty((n_fft // 2 + 1, n_frames))
    for i in range(n_frames):
        start = i * hop_length
        S[:, i] = np.abs(np.fft.rfft(y[start:start + n_fft] * window))

    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    return S, freqs, hop_length


def rms_envelope(y, frame_length=2048, hop_length=512):
    """Enveloppe RMS par trame (numpy seul)."""
    y = np.asarray(y, dtype='float64')
    if y.size < frame_length:
        return np.array([np.sqrt(np.mean(y ** 2))]) if y.size else np.array([0.0])
    n_frames = 1 + (y.size - frame_length) // hop_length
    out = np.empty(n_frames)
    for i in range(n_frames):
        start = i * hop_length
        seg = y[start:start + frame_length]
        out[i] = np.sqrt(np.mean(seg ** 2))
    return out


# ==============================================================================
# Bandes spectrales (généralise `repartition_bandes` de l'étude OSSO)
# ==============================================================================

def spectral_bands(S, freqs, bands=None):
    """Pourcentage d'énergie spectrale par bande de fréquence.

    Calcul identique à celui utilisé pour l'étude OSSO (§3.1) : `analyse_osso.py`
    délègue ici plutôt que de dupliquer la boucle.
    """
    bands = bands or SPECTRAL_BANDS
    total = float(S.sum()) + 1e-12
    return {(lo, hi): 100.0 * float(S[(freqs >= lo) & (freqs < hi)].sum()) / total
            for lo, hi in bands}


# ==============================================================================
# Descripteurs de timbre (platitude, rolloff, largeur de bande, HPSS)
# ==============================================================================

def spectral_centroid(S, freqs):
    """Centroïde spectral par trame (barycentre du spectre, en Hz)."""
    energy = S.sum(axis=0) + 1e-12
    return (freqs[:, None] * S).sum(axis=0) / energy


def spectral_rolloff(S, freqs, roll_percent=0.85):
    """Fréquence sous laquelle se trouve `roll_percent` de l'énergie, par trame."""
    cum = np.cumsum(S, axis=0)
    total = cum[-1, :] + 1e-12
    thresh = roll_percent * total
    idx = np.argmax(cum >= thresh, axis=0)
    return freqs[idx]


def spectral_bandwidth(S, freqs, centroid=None):
    """Écart-type spectral autour du centroïde, par trame (Hz)."""
    if centroid is None:
        centroid = spectral_centroid(S, freqs)
    energy = S.sum(axis=0) + 1e-12
    dev2 = (freqs[:, None] - centroid[None, :]) ** 2
    return np.sqrt((dev2 * S).sum(axis=0) / energy)


def spectral_flatness(S):
    """Platitude spectrale (moyenne géométrique / moyenne arithmétique), par
    trame. Proche de 0 = tonal ; proche de 1 = bruit."""
    eps = 1e-12
    geo = np.exp(np.mean(np.log(S + eps), axis=0))
    ari = np.mean(S, axis=0) + eps
    return geo / ari


def hpss(S, kernel_harm=17, kernel_perc=17):
    """Sépare harmonique/percussif par filtrage médian (Fitzgerald 2010,
    cf. `docs/references.bib`) : médiane le long du temps pour la référence
    harmonique (garde les raies stables, lisse les transitoires), médiane le
    long de la fréquence pour la référence percussive (garde les transitoires
    larges bande, lisse les raies). Masque doux = ratio des deux références.

    Renvoie `(H, P)`, magnitudes telles que `H + P == S`. Version simplifiée
    (pas de paramètre `margin`) — cf. note de reproductibilité en tête de
    module : ne vise pas à reproduire `librosa.effects.hpss`.
    """
    harm_ref = median_filter(S, size=(1, kernel_harm))
    perc_ref = median_filter(S, size=(kernel_perc, 1))
    eps = 1e-12
    mask_h = harm_ref / (harm_ref + perc_ref + eps)
    return S * mask_h, S * (1.0 - mask_h)


def hpss_energy_ratio(S, **kwargs):
    """Répartition d'énergie harmonique/percussive (%), via `hpss`."""
    H, P = hpss(S, **kwargs)
    eh, ep = float(np.sum(H ** 2)), float(np.sum(P ** 2))
    total = eh + ep + 1e-12
    return 100.0 * eh / total, 100.0 * ep / total


# ==============================================================================
# Spectre de modulation (généralise `spectre_modulation` de l'étude OSSO)
# ==============================================================================

def modulation_spectrum(S, freqs, fps, bands=None, fmin=0.3, fmax=15.0, n_peaks=3):
    """Pics de modulation d'enveloppe par bande — cf. `docs/analyse_acoustique_osso.md`
    §3.4. `fps` = trames/seconde de `S` (`sr / hop_length`).

    Renvoie `{nom_bande: array des fréquences de modulation (Hz), décroissant}`.
    """
    bands = bands or MODULATION_BANDS
    out = {}
    for lo, hi, nom in bands:
        env = S[(freqs >= lo) & (freqs < hi)].sum(axis=0)
        env = env - env.mean()

        spec = np.abs(np.fft.rfft(env * np.hanning(len(env))))
        mfreqs = np.fft.rfftfreq(len(env), 1.0 / fps)

        mask = (mfreqs > fmin) & (mfreqs < fmax)
        idx = np.argsort(spec[mask])[::-1][:n_peaks]
        out[nom] = np.unique(np.round(mfreqs[mask][idx], 2))[::-1]
    return out


def correct_metric_octave(peaks, bpm_candidates, subdivisions=None):
    """Choisit, parmi `bpm_candidates`, le tempo qui aligne le mieux `peaks`
    (Hz, pics de modulation) sur les subdivisions métriques usuelles —
    corrige l'erreur d'octave métrique (cf. §3.5 de l'étude OSSO).

    Renvoie `(meilleur_bpm, erreur_min, erreurs_par_bpm)`.
    """
    subdivisions = subdivisions or SUBDIVISIONS
    errors_by_bpm = {}
    best_bpm, best_err = None, float('inf')
    for bpm in bpm_candidates:
        quarter = bpm / 60.0
        errs = []
        for p in peaks:
            r = p / quarter
            target = min(subdivisions, key=lambda k: abs(k - r))
            errs.append(abs(r - target) / target)
        err = float(np.mean(errs)) if errs else float('nan')
        errors_by_bpm[bpm] = err
        if err < best_err:
            best_bpm, best_err = bpm, err
    return best_bpm, best_err, errors_by_bpm


# ==============================================================================
# Dramaturgie timbrale (régression du centroïde) et dynamique
# ==============================================================================

def centroid_regression(t, y):
    """Régression linéaire d'une série temporelle de centroïde/rolloff —
    quantifie une trajectoire timbrale (ouverture de filtre, etc.), cf. §3.6."""
    slope, intercept, r, p, stderr = stats.linregress(t, y)
    return dict(slope=float(slope), intercept=float(intercept),
                r2=float(r ** 2), p=float(p), stderr=float(stderr))


def crest_factor_db(y):
    """Facteur de crête (dB) : crête / valeur efficace. Faible = compressé."""
    y = np.asarray(y, dtype='float64')
    peak = np.max(np.abs(y))
    rms = np.sqrt(np.mean(y ** 2)) + 1e-12
    return float(20 * np.log10(peak / rms))


def dynamic_range_db(rms, low_pct=10, high_pct=95, floor_db=-40.0):
    """Étendue dynamique (dB, p_high − p_low) sur les passages actifs d'une
    enveloppe RMS (exclut les silences sous `floor_db` relatif au maximum)."""
    db = 20 * np.log10(np.asarray(rms, dtype='float64') + 1e-10)
    active = db[db > db.max() + floor_db]
    if active.size == 0:
        return 0.0
    return float(np.percentile(active, high_pct) - np.percentile(active, low_pct))


def beat_stability(beat_times):
    """Stabilité du battement (% = écart-type / moyenne des intervalles).
    Élevé = tempo instable → risque d'erreur d'octave métrique (§3.5)."""
    d = np.diff(np.asarray(beat_times, dtype='float64'))
    if d.size == 0 or d.mean() == 0:
        return float('nan')
    return float(100.0 * d.std() / d.mean())


# ==============================================================================
# Spécifique « instruments à bourdon » — nouveau, au service de la synthèse
# ==============================================================================

def bourdon_strength(S, freqs, band):
    """Force de bourdon dans une bande : proche de 1 si l'énergie y est stable
    dans le temps et concentrée sur peu de bins (un ton tenu — une trompette
    de vielle, un bourdon de cornemuse, une basse d'accordéon tenue), proche
    de 0 si diffuse, bruitée ou intermittente.

    Combine à parts égales :
    - la **régularité temporelle** de l'enveloppe d'énergie de la bande
      (inverse du coefficient de variation, borné dans (0,1]) ;
    - la **concentration spectrale instantanée** (1 − platitude spectrale,
      moyennée dans le temps, restreinte à la bande).

    Sert à caractériser automatiquement quelle bande porte le bourdon d'un
    instrument (paramètre d'entrée d'un futur modèle physique de résonateur
    entretenu — vielle à roue, cornemuse).
    """
    lo, hi = band
    mask = (freqs >= lo) & (freqs < hi)
    sub = S[mask]
    if sub.shape[0] == 0:
        return 0.0

    env = sub.sum(axis=0)
    if env.mean() <= 1e-12:
        return 0.0
    cv = env.std() / (env.mean() + 1e-12)
    steadiness = 1.0 / (1.0 + cv)

    eps = 1e-12
    geo = np.exp(np.mean(np.log(sub + eps), axis=0))
    ari = np.mean(sub, axis=0) + eps
    flatness_t = geo / ari
    concentration = max(0.0, min(1.0, float(1.0 - np.mean(flatness_t))))

    return float(0.5 * steadiness + 0.5 * concentration)


def harmonic_partials(S, freqs, f0, n_partials=8, tol_cents=50.0, min_rel_mag=0.02):
    """Estime la série de partiels d'un son quasi-harmonique de fondamentale
    `f0` (Hz) : pour chaque rang `n`, cherche le maximum du spectre moyen
    (moyenné dans le temps) dans une fenêtre de `± tol_cents` autour de `n·f0`,
    et calcule l'écart en cents à l'harmonique idéale (inharmonicité).

    `min_rel_mag` : un maximum local dont l'amplitude est en dessous de cette
    fraction du maximum global du spectre est ignoré (nan) — évite de
    rapporter comme « partiel » une simple fuite spectrale (lobe secondaire de
    fenêtre) là où l'instrument ne produit en réalité aucune énergie.

    Paramètre d'entrée typique d'une synthèse additive/modale : l'écart en
    cents de chaque partiel renseigne la raideur/l'amortissement d'un
    résonateur physique (anche, corde, tuyau) par rapport au cas idéal.

    Renvoie une liste de `{n, f_ideal, f_mesure, cents}` (nan si rien trouvé
    dans la fenêtre de recherche, ou si le maximum trouvé est négligeable).
    """
    mean_spec = S.mean(axis=1)
    global_max = float(mean_spec.max()) if mean_spec.size else 0.0
    out = []
    for n in range(1, n_partials + 1):
        f_ideal = n * f0
        lo = f_ideal * 2 ** (-tol_cents / 1200)
        hi = f_ideal * 2 ** (tol_cents / 1200)
        mask = (freqs >= lo) & (freqs <= hi)
        nan_entry = dict(n=n, f_ideal=float(f_ideal), f_mesure=float('nan'), cents=float('nan'))
        if not np.any(mask):
            out.append(nan_entry)
            continue
        idx_local = np.argmax(mean_spec[mask])
        mag = mean_spec[mask][idx_local]
        if global_max > 0 and mag < min_rel_mag * global_max:
            out.append(nan_entry)
            continue
        f_mesure = float(freqs[mask][idx_local])
        cents = float(1200 * np.log2(f_mesure / f_ideal))
        out.append(dict(n=n, f_ideal=float(f_ideal), f_mesure=f_mesure, cents=cents))
    return out
