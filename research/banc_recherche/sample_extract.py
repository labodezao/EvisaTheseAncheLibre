"""Extraction de paramètres de modèle physique depuis un **sample monophonique**.

Principe (celui des instruments à modèle physique type SWAM) : un sample n'est
pas le produit final, c'est une **mesure**. On en extrait les paramètres d'un
modèle **source → résonateur**, qui tourne ensuite en temps réel et se pilote
en continu (souffle, pression de soufflet, expression) au lieu d'être rejoué.

Ce qu'on extrait, et pourquoi c'est ce qu'il faut pour un modèle physique :

- **Hauteur** `f0(t)` et **vibrato** (taux, profondeur) : sépare la hauteur
  nominale du geste expressif — le modèle doit produire le geste, pas le
  rejouer.
- **Partiels** (amplitude de chaque harmonique au cours du temps) : c'est la
  sortie du système ; leur **inharmonicité** renseigne la raideur du
  résonateur (cf. `timbre.harmonic_partials`).
- **Résonateur** : l'enveloppe spectrale **stable** (indépendante de la note)
  = le corps de l'instrument. Exporté en **biquads** (f, Q, gain) : c'est la
  seule forme qui tienne dans un DSP embarqué.
- **Source** : ce qui reste une fois le résonateur retiré = l'excitation
  (anche, archet, roue). Caractérisée par sa **pente spectrale**.
- **Bruit** : part non harmonique (souffle, frottement) par bande.
- **Transitoire** : temps d'attaque **par partiel** — les aigus qui arrivent
  après le fondamental sont une signature physique forte, et c'est ce qui
  manque le plus aux sampleurs.
- **Loi de dynamique** : comment la brillance suit le niveau — la loi de
  commande que le contrôleur continu pilotera.

Tout est en **numpy + scipy seuls** (dépendances de base du paquet) : testable
sans `librosa`/`parselmouth`, exécutable sur une machine modeste. Le chargement
de fichiers audio compressés reste à l'appelant (GUI, script).

Voir `synth_export.py` pour la mise en forme vers une cible embarquée
(STM32 / Dream SAM5716) et `docs/sample_vers_modele_physique.md` pour ce qui
relève du firmware constructeur.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

from . import timbre


# ==============================================================================
# Hauteur : f0(t) par autocorrélation, et vibrato
# ==============================================================================

def detect_f0(y, sr, fmin=50.0, fmax=2000.0, frame=2048, hop=512, threshold=0.3):
    """Suivi de hauteur par autocorrélation normalisée, trame par trame.

    Adapté au **monophonique** (un seul son à la fois), ce qui est exactement
    le cas d'usage : un sample d'instrument isolé.

    Renvoie `(f0, times)` — `f0` en Hz, `nan` sur les trames non voisées
    (autocorrélation trop faible = pas de périodicité franche).
    """
    y = np.asarray(y, dtype='float64')
    if y.size < frame:
        y = np.pad(y, (0, frame - y.size))

    lag_min = max(1, int(sr / fmax))
    lag_max = min(frame - 1, int(sr / fmin))
    n_frames = 1 + (y.size - frame) // hop

    f0 = np.full(n_frames, np.nan)
    for i in range(n_frames):
        seg = y[i * hop:i * hop + frame]
        seg = seg - seg.mean()
        norm = np.dot(seg, seg)
        if norm <= 1e-12:
            continue
        # autocorrélation par FFT (rapide, numpy seul)
        n = int(2 ** np.ceil(np.log2(2 * frame)))
        spec = np.fft.rfft(seg, n)
        acf = np.fft.irfft(spec * np.conj(spec), n)[:lag_max + 1]
        acf /= norm

        if lag_max <= lag_min:
            continue
        window = acf[lag_min:lag_max + 1]
        k = int(np.argmax(window))
        if window[k] < threshold:
            continue
        lag = lag_min + k
        # raffinement parabolique autour du maximum
        if 0 < lag < lag_max:
            a, b, c = acf[lag - 1], acf[lag], acf[lag + 1]
            denom = a - 2 * b + c
            if abs(denom) > 1e-12:
                lag = lag + 0.5 * (a - c) / denom
        f0[i] = sr / lag

    times = np.arange(n_frames) * hop / sr
    return f0, times


def vibrato(f0, times, fmin=2.0, fmax=12.0):
    """Taux (Hz) et profondeur (cents) du vibrato, depuis la déviation de `f0`.

    On passe en cents (échelle logarithmique = perception), on retire la
    tendance lente, et on cherche le pic de modulation dans la bande du
    vibrato instrumental usuel (2–12 Hz).

    Renvoie `{rate_hz, depth_cents, f0_median_hz}`.
    """
    f0 = np.asarray(f0, dtype='float64')
    valid = np.isfinite(f0) & (f0 > 0)
    out = dict(rate_hz=float('nan'), depth_cents=0.0, f0_median_hz=float('nan'))
    if valid.sum() < 8:
        return out

    f0_med = float(np.median(f0[valid]))
    out['f0_median_hz'] = f0_med

    cents = 1200 * np.log2(f0[valid] / f0_med)
    t = np.asarray(times, dtype='float64')[valid]
    if t.size < 8 or (t[-1] - t[0]) <= 0:
        return out

    # retrait de la dérive lente (portamento, justesse) : régression linéaire
    cents = cents - np.polyval(np.polyfit(t, cents, 1), t)

    fps = (t.size - 1) / (t[-1] - t[0])
    spec = np.abs(np.fft.rfft(cents * np.hanning(cents.size)))
    freqs = np.fft.rfftfreq(cents.size, 1.0 / fps)
    band = (freqs >= fmin) & (freqs <= fmax)
    if not np.any(band) or spec[band].max() <= 0:
        return out

    out['rate_hz'] = float(freqs[band][np.argmax(spec[band])])
    # profondeur crête : écart-type x sqrt(2) pour une modulation ~sinusoïdale
    out['depth_cents'] = float(np.std(cents) * np.sqrt(2))
    return out


# ==============================================================================
# Partiels : amplitude de chaque harmonique au cours du temps
# ==============================================================================

def partial_envelopes(y, sr, f0_hz, n_partials=12, n_fft=4096, hop=512, bw_cents=60.0):
    """Amplitude de chaque partiel `n·f0` au cours du temps.

    Pour chaque trame STFT, on somme l'énergie dans une fenêtre étroite autour
    de `n·f0`. C'est la matrice qui pilote une synthèse additive/modale, et
    dont on tire les enveloppes par partiel.

    Renvoie `(amps, times)` — `amps` de forme (n_partials, n_frames).
    """
    S, freqs, hop_used = timbre.stft_mag(y, sr, n_fft=n_fft, hop_length=hop)
    n_frames = S.shape[1]
    amps = np.zeros((n_partials, n_frames))

    for n in range(1, n_partials + 1):
        f_c = n * f0_hz
        if f_c >= freqs[-1]:
            break
        lo = f_c * 2 ** (-bw_cents / 1200)
        hi = f_c * 2 ** (bw_cents / 1200)
        mask = (freqs >= lo) & (freqs <= hi)
        if not np.any(mask):
            continue
        amps[n - 1] = S[mask].max(axis=0)

    times = np.arange(n_frames) * hop_used / sr
    return amps, times


def attack_times(amps, times, threshold=0.9):
    """Temps de montée de chaque partiel (s) : instant où il atteint
    `threshold` de son maximum pour la première fois.

    Un instrument réel n'établit pas tous ses partiels en même temps : les
    aigus arrivent **après** le fondamental. Cet étalement est ce qui rend
    une attaque vivante, et c'est précisément ce qu'un sampleur fige.
    """
    amps = np.asarray(amps, dtype='float64')
    times = np.asarray(times, dtype='float64')
    out = np.full(amps.shape[0], np.nan)
    for k in range(amps.shape[0]):
        peak = amps[k].max()
        if peak <= 1e-12:
            continue
        idx = np.argmax(amps[k] >= threshold * peak)
        out[k] = times[idx]
    return out


# ==============================================================================
# Compression d'enveloppe en points de rupture (format embarqué)
# ==============================================================================

def compress_envelope(times, env, max_points=8, tol=None):
    """Approxime une enveloppe par une ligne brisée de `max_points` au plus.

    Algorithme de Ramer-Douglas-Peucker : on garde récursivement le point le
    plus éloigné de la corde. C'est ce qui permet de tenir une enveloppe dans
    quelques octets de Flash au lieu de milliers de trames.

    Renvoie `[(t, valeur), ...]`, premier et dernier points toujours inclus.
    """
    t = np.asarray(times, dtype='float64')
    e = np.asarray(env, dtype='float64')
    if t.size == 0:
        return []
    if t.size <= 2:
        return [(float(a), float(b)) for a, b in zip(t, e)]

    span = e.max() - e.min()
    if tol is None:
        tol = 0.02 * (span if span > 0 else 1.0)

    keep = {0, t.size - 1}

    def _recurse(i0, i1):
        if i1 <= i0 + 1 or len(keep) >= max_points:
            return
        # distance verticale à la corde (i0 -> i1)
        if t[i1] == t[i0]:
            return
        slope = (e[i1] - e[i0]) / (t[i1] - t[i0])
        chord = e[i0] + slope * (t[i0:i1 + 1] - t[i0])
        dev = np.abs(e[i0:i1 + 1] - chord)
        k = int(np.argmax(dev))
        if dev[k] <= tol:
            return
        idx = i0 + k
        keep.add(idx)
        _recurse(i0, idx)
        _recurse(idx, i1)

    _recurse(0, t.size - 1)
    sel = sorted(keep)[:max_points]
    return [(float(t[i]), float(e[i])) for i in sel]


def adsr_from_envelope(times, env):
    """Ajuste un ADSR grossier sur une enveloppe d'amplitude.

    Volontairement simple : l'ADSR n'est qu'un **repli** quand la cible ne sait
    pas faire mieux. Les points de rupture (`compress_envelope`) sont plus
    fidèles et pas plus coûteux.

    Renvoie `{attack_s, decay_s, sustain_level, release_s, peak}`.
    """
    t = np.asarray(times, dtype='float64')
    e = np.asarray(env, dtype='float64')
    out = dict(attack_s=0.0, decay_s=0.0, sustain_level=0.0, release_s=0.0, peak=0.0)
    if t.size < 3:
        return out

    peak = float(e.max())
    out['peak'] = peak
    if peak <= 1e-12:
        return out

    i_peak = int(np.argmax(e))
    # Attaque = premier passage à 90 % du maximum (et non l'instant du maximum
    # absolu : sur un son tenu, le maximum tombe au hasard dans le plateau et
    # donnerait une attaque fantaisiste de plusieurs secondes).
    i_attack = int(np.argmax(e >= 0.9 * peak))
    out['attack_s'] = float(t[i_attack] - t[0])

    # sustain = niveau médian de la seconde moitié après le pic
    tail = e[i_peak:]
    if tail.size >= 4:
        sustain = float(np.median(tail[tail.size // 2:]))
    else:
        sustain = float(tail[-1]) if tail.size else 0.0
    out['sustain_level'] = sustain / peak

    # decay : du pic jusqu'à atteindre le niveau de sustain (+5 %)
    target = sustain * 1.05
    after = np.nonzero(e[i_peak:] <= target)[0]
    out['decay_s'] = float(t[i_peak + after[0]] - t[i_peak]) if after.size else 0.0

    # release : de la **fin du plateau de sustain** à l'extinction (5 % du pic).
    # (Mesurer « dernier point audible -> fin du fichier » donnerait la longueur
    # du silence final, pas la durée de la chute.)
    audible = np.nonzero(e >= 0.05 * peak)[0]
    if audible.size:
        end_idx = int(audible[-1])
        hold = np.nonzero(e[:end_idx + 1] >= 0.95 * sustain)[0] if sustain > 0 else np.array([])
        start_idx = int(hold[-1]) if hold.size else i_peak
        out['release_s'] = float(max(0.0, t[end_idx] - t[start_idx]))
    return out


# ==============================================================================
# Résonateur : enveloppe spectrale stable -> biquads
# ==============================================================================

def spectral_envelope(S, freqs, f0_hz=None, lifter_ratio=0.5):
    """Enveloppe spectrale par **liftrage cepstral**.

    Sur une note tenue, le spectre porte deux choses superposées : le peigne
    harmonique (espacé de `f0`, il **suit la note**) et l'enveloppe spectrale
    (le corps de l'instrument, **invariant**). Les séparer est indispensable :
    prendre les partiels pour des résonances donnerait un « résonateur » qui
    se déplace avec la hauteur jouée — c'est-à-dire pas un résonateur.

    Le cepstre les sépare naturellement : le peigne, périodique en fréquence,
    se concentre à une quéfrence élevée ; l'enveloppe, lente, aux quéfrences
    basses. On coupe en dessous du peigne et on revient au spectre.

    Un simple lissage par moyenne glissante ne suffit pas : il faudrait une
    fenêtre plus large que `f0`, donc dépendante de la note et destructrice
    dans l'aigu.
    """
    mean_spec = np.asarray(S, dtype='float64').mean(axis=1)
    freqs = np.asarray(freqs, dtype='float64')
    if mean_spec.size < 8:
        return mean_spec

    ref = mean_spec.max()
    if ref <= 0:
        return mean_spec

    # -- Méthode principale : interpolation par les **sommets des partiels**.
    # C'est la définition même du filtre en source-filtre — l'enveloppe est ce
    # qui module l'amplitude des raies. Plus robuste que le cepstre seul, qui
    # se laisse piéger par le trou d'énergie sous le premier partiel (une
    # marche énorme dans le log-spectre, qui déplace le maximum trouvé).
    if f0_hz and np.isfinite(f0_hz) and f0_hz > 0:
        pts_f, pts_a = [], []
        n = 1
        while n * f0_hz < freqs[-1]:
            f_c = n * f0_hz
            lo = f_c * 2 ** (-40 / 1200)
            hi = f_c * 2 ** (40 / 1200)
            mask = (freqs >= lo) & (freqs <= hi)
            if np.any(mask):
                pts_f.append(f_c)
                pts_a.append(float(mean_spec[mask].max()))
            n += 1
        if len(pts_f) >= 3:
            pts_a = np.asarray(pts_a)
            floor = max(pts_a.max() * 1e-8, 1e-30)
            log_a = np.log(np.maximum(pts_a, floor))
            # interpolation linéaire en log-amplitude ; plateau au-delà des
            # partiels extrêmes (on n'invente pas d'énergie hors bande utile)
            return np.exp(np.interp(freqs, np.asarray(pts_f), log_a))

    # -- Repli : liftrage cepstral, quand la hauteur n'est pas connue.
    log_spec = np.log(np.maximum(mean_spec, ref * 1e-8))

    ceps = np.fft.irfft(log_spec)
    n_c = ceps.size
    df = freqs[1] - freqs[0] if freqs.size > 1 else 1.0

    if f0_hz and np.isfinite(f0_hz) and f0_hz > 0 and df > 0:
        # le peigne harmonique a une période de f0/df bins -> quéfrence n_c·df/f0
        q_comb = n_c * df / float(f0_hz)
        q_cut = int(max(2, lifter_ratio * q_comb))
    else:
        q_cut = max(2, n_c // 64)
    q_cut = min(q_cut, n_c // 2 - 1)

    lifted = ceps.copy()
    lifted[q_cut:n_c - q_cut + 1] = 0.0          # cepstre réel : symétrique
    return np.exp(np.fft.rfft(lifted).real)


def resonator_peaks(S, freqs, n_peaks=6, min_freq=80.0, f0_hz=None):
    """Repère les **pics de résonance** de l'enveloppe spectrale.

    L'enveloppe est extraite par liftrage cepstral (`spectral_envelope`), de
    sorte que les maxima trouvés soient ceux du **corps de l'instrument** et
    non les partiels de la note analysée.

    Renvoie `[{freq_hz, gain_db, q}, ...]` trié par fréquence croissante —
    directement convertible en biquads (cf. `synth_export.biquad_peaking`).
    """
    freqs = np.asarray(freqs, dtype='float64')
    env = spectral_envelope(S, freqs, f0_hz=f0_hz)
    if env.size < 3:
        return []

    ref = env.max()
    if ref <= 0:
        return []
    env_db = 20 * np.log10(np.maximum(env, ref * 1e-6) / ref)

    # maxima locaux au-dessus de min_freq
    cand = []
    for i in range(1, env.size - 1):
        if freqs[i] < min_freq:
            continue
        if env[i] > env[i - 1] and env[i] >= env[i + 1]:
            cand.append(i)
    cand.sort(key=lambda i: env[i], reverse=True)
    cand = sorted(cand[:n_peaks])

    out = []
    for i in cand:
        f_c = float(freqs[i])
        # largeur à -3 dB autour du pic -> facteur Q
        target = env_db[i] - 3.0
        lo = i
        while lo > 0 and env_db[lo] > target:
            lo -= 1
        hi = i
        while hi < env.size - 1 and env_db[hi] > target:
            hi += 1
        bw = float(freqs[hi] - freqs[lo])
        q = f_c / bw if bw > 1e-9 else 10.0
        out.append(dict(freq_hz=f_c, gain_db=float(env_db[i]), q=float(np.clip(q, 0.5, 40.0))))
    return out


def source_slope(amps):
    """Pente spectrale de la **source** (dB par octave de rang harmonique).

    Une fois le résonateur retiré, ce qui reste décrit l'excitation : une
    anche douce décroît vite (pente forte), une anche mordante décroît peu.
    C'est le paramètre que la dynamique fera bouger en jeu.
    """
    amps = np.asarray(amps, dtype='float64')
    means = amps.mean(axis=1)
    ranks = np.arange(1, means.size + 1, dtype='float64')
    good = means > (means.max() * 1e-4 if means.max() > 0 else 0)
    if good.sum() < 3:
        return float('nan')
    x = np.log2(ranks[good])
    ydb = 20 * np.log10(means[good] / means[good][0])
    slope, _ = np.polyfit(x, ydb, 1)
    return float(slope)


def brightness_vs_level(y, sr, n_fft=2048, hop=512):
    """Loi **brillance ↔ niveau** : pente du centroïde spectral en fonction du
    niveau (dB). C'est la loi de commande du contrôleur continu — jouer plus
    fort ouvre le spectre, et le modèle doit reproduire *cette* relation-là,
    pas un crossfade entre couches de samples.

    Renvoie `{slope_hz_per_db, r2, centroid_mean_hz}`.
    """
    S, freqs, hop_used = timbre.stft_mag(y, sr, n_fft=n_fft, hop_length=hop)
    cent = timbre.spectral_centroid(S, freqs)
    level = S.sum(axis=0)
    good = level > (level.max() * 0.05 if level.max() > 0 else 0)
    out = dict(slope_hz_per_db=float('nan'), r2=float('nan'),
               centroid_mean_hz=float(np.mean(cent)) if cent.size else float('nan'))
    if good.sum() < 8:
        return out
    level_db = 20 * np.log10(level[good] / level[good].max())
    reg = timbre.centroid_regression(level_db, cent[good])
    out['slope_hz_per_db'] = reg['slope']
    out['r2'] = reg['r2']
    return out


# ==============================================================================
# Modèle complet
# ==============================================================================

@dataclass
class SampleModel:
    """Paramètres extraits d'un sample, prêts à alimenter un modèle physique."""
    name: str = ""
    samplerate: int = 0
    duration_s: float = 0.0

    # hauteur & geste
    f0_hz: float = float('nan')
    vibrato_rate_hz: float = float('nan')
    vibrato_depth_cents: float = 0.0

    # partiels
    n_partials: int = 0
    partial_levels_db: list = field(default_factory=list)   # niveau moyen, rang 1 = 0 dB
    partial_attack_s: list = field(default_factory=list)
    partial_envelopes: list = field(default_factory=list)   # [[(t, a), ...], ...]
    inharmonicity_cents: list = field(default_factory=list)

    # résonateur & source
    resonators: list = field(default_factory=list)          # [{freq_hz, gain_db, q}]
    source_slope_db_per_oct: float = float('nan')

    # bruit & dynamique
    harmonic_pct: float = float('nan')
    percussive_pct: float = float('nan')
    brightness_slope_hz_per_db: float = float('nan')

    # enveloppe globale
    adsr: dict = field(default_factory=dict)
    amplitude_envelope: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def extract(y, sr, name="", n_partials=12, n_resonators=6, max_env_points=8):
    """Extraction complète : sample monophonique -> `SampleModel`.

    `y` doit être **mono** (un seul instrument, une seule note tenue de
    préférence). Aucune I/O ici : l'appelant fournit le signal déjà décodé.
    """
    y = np.asarray(y, dtype='float64')
    if y.ndim > 1:
        y = y.mean(axis=1)
    peak = np.max(np.abs(y)) if y.size else 0.0
    if peak > 0:
        y = y / peak

    m = SampleModel(name=name, samplerate=int(sr), duration_s=float(y.size / sr))

    # -- hauteur & vibrato
    f0_track, f0_times = detect_f0(y, sr)
    vib = vibrato(f0_track, f0_times)
    m.f0_hz = vib['f0_median_hz']
    m.vibrato_rate_hz = vib['rate_hz']
    m.vibrato_depth_cents = vib['depth_cents']

    if not np.isfinite(m.f0_hz) or m.f0_hz <= 0:
        return m      # pas de hauteur exploitable : on s'arrête honnêtement là

    # -- partiels
    amps, p_times = partial_envelopes(y, sr, m.f0_hz, n_partials=n_partials)
    m.n_partials = int(n_partials)

    means = amps.mean(axis=1)
    ref = means[0] if means[0] > 0 else (means.max() or 1.0)
    m.partial_levels_db = [float(20 * np.log10(v / ref)) if v > 0 else -120.0 for v in means]
    m.partial_attack_s = [float(v) for v in attack_times(amps, p_times)]
    m.partial_envelopes = [compress_envelope(p_times, amps[k], max_env_points)
                           for k in range(amps.shape[0])]
    m.source_slope_db_per_oct = source_slope(amps)

    # -- résonateur (enveloppe spectrale stable) et inharmonicité
    S, freqs, _ = timbre.stft_mag(y, sr, n_fft=4096)
    m.resonators = resonator_peaks(S, freqs, n_peaks=n_resonators, f0_hz=m.f0_hz)
    m.inharmonicity_cents = [p['cents'] for p in
                             timbre.harmonic_partials(S, freqs, m.f0_hz, n_partials=n_partials)]

    # -- bruit / dynamique
    m.harmonic_pct, m.percussive_pct = timbre.hpss_energy_ratio(S)
    m.brightness_slope_hz_per_db = brightness_vs_level(y, sr)['slope_hz_per_db']

    # -- enveloppe globale
    # Fenêtre courte (≈ 23 ms) : une attaque d'instrument dure quelques
    # dizaines de ms, la fenêtre RMS par défaut (2048 éch.) la lisserait au
    # point de la rendre inmesurable.
    frame = max(64, int(0.023 * sr))
    hop = max(16, frame // 4)
    rms = timbre.rms_envelope(y, frame_length=frame, hop_length=hop)
    rms_t = np.arange(rms.size) * hop / sr
    m.adsr = adsr_from_envelope(rms_t, rms)
    m.amplitude_envelope = compress_envelope(rms_t, rms, max_env_points)

    return m
