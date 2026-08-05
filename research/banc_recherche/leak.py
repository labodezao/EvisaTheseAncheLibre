"""Détection de fuites d'air.

1. **Décroissance de pression** (`fit_decay`) : mesure globale d'étanchéité
   (τ, conductance) — commande firmware `LEAKTEST`.
2. **Localisation par détection synchrone / lock-in** (`acoustic_leak_strength`,
   `lockin`) : on module la pression du soufflet à `f_mod` ; chaque fuite
   rayonne un sifflement dont l'intensité clignote à `f_mod`. Le lock-in de
   l'enveloppe du sifflement à `f_mod` extrait la fuite du bruit ambiant (gain
   de S/N énorme) → carte de fuite en promenant un micro. C'est le principe de
   l'amplificateur à détection synchrone appliqué à l'acoustique de fuite, avec
   le **soufflet comme modulateur** — cheap et propre à ce banc.

Couvre l'annexe « Leaks detection » et « Sealing material influence ».
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LeakResult:
    p0: float            # pression initiale (Pa)
    tau: float           # temps caractéristique (s)
    half_life: float     # demi-vie (s)
    conductance: float   # V/τ si volume fourni, sinon NaN


def fit_decay(t: np.ndarray, p: np.ndarray, volume_m3: float | None = None) -> LeakResult:
    """Ajuste `p(t) = p₀·e^{−t/τ}` par régression linéaire sur `ln(p)`.

    `t` en s, `p` en Pa (relatifs, > 0). Ignore les points ≤ 0.
    """
    t = np.asarray(t, dtype="float64")
    p = np.asarray(p, dtype="float64")
    mask = p > 0
    t, p = t[mask], p[mask]
    if t.size < 3:
        return LeakResult(float("nan"), float("nan"), float("nan"), float("nan"))
    A = np.vstack([t, np.ones_like(t)]).T
    slope, intercept = np.linalg.lstsq(A, np.log(p), rcond=None)[0]
    # Pente non significativement négative (bruit numérique) = aucune fuite.
    tau = float(-1.0 / slope) if slope < -1e-9 else float("inf")
    p0 = float(np.exp(intercept))
    half = tau * np.log(2.0) if np.isfinite(tau) else float("inf")
    cond = (volume_m3 / tau) if (volume_m3 and np.isfinite(tau) and tau > 0) else float("nan")
    return LeakResult(p0, tau, half, cond)


# ---- Localisation par détection synchrone (lock-in) ------------------------
def _bandpass(sig, fs, lo, hi):
    """Passe-bande par masque FFT (numpy seul)."""
    x = np.asarray(sig, dtype="float64")
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(x.size, 1.0 / fs)
    X[(f < lo) | (f > hi)] = 0.0
    return np.fft.irfft(X, x.size)


def _envelope(sig):
    """Enveloppe d'amplitude (|signal analytique|, Hilbert par FFT)."""
    x = np.asarray(sig, dtype="float64")
    n = x.size
    X = np.fft.fft(x)
    h = np.zeros(n)
    if n % 2 == 0:
        h[0] = h[n // 2] = 1
        h[1:n // 2] = 2
    else:
        h[0] = 1
        h[1:(n + 1) // 2] = 2
    return np.abs(np.fft.ifft(X * h))


def lockin(sig, fs, f_ref):
    """Détection synchrone : amplitude et phase de la composante de `sig` à
    `f_ref`. Renvoie (R, phase). Rejette tout ce qui ne bat pas à `f_ref`."""
    x = np.asarray(sig, dtype="float64")
    x = x - x.mean()
    t = np.arange(x.size) / fs
    i = np.mean(x * np.cos(2 * np.pi * f_ref * t))     # composante en phase
    q = np.mean(x * np.sin(2 * np.pi * f_ref * t))     # composante en quadrature
    return 2.0 * float(np.hypot(i, q)), float(np.arctan2(q, i))


def acoustic_leak_strength(mic, fs, f_mod, hiss_band=(4000.0, 20000.0)):
    """Force de fuite à la position du micro, par détection synchrone.

    La pression du soufflet est modulée à `f_mod` : on isole la bande de
    sifflement (`hiss_band`), on prend son enveloppe, et on fait le lock-in de
    cette enveloppe à `f_mod`. Grand = fuite proche. Robuste au bruit ambiant.
    """
    hi = min(hiss_band[1], fs / 2 * 0.98)
    band = _bandpass(mic, fs, hiss_band[0], hi)
    env = _envelope(band)
    r, _ = lockin(env, fs, f_mod)
    return r


def leak_map(recordings, fs, f_mod, hiss_band=(4000.0, 20000.0)):
    """Carte de fuite : force par position. `recordings` = liste de (label, mic).
    Renvoie [(label, force)] trié décroissant (la 1re = fuite la plus probable)."""
    out = [(lab, acoustic_leak_strength(m, fs, f_mod, hiss_band)) for lab, m in recordings]
    return sorted(out, key=lambda kv: kv[1], reverse=True)


def tdoa_delay(mic1, mic2, fs):
    """Décalage temporel (s) entre deux micros par corrélation croisée — pour
    trianguler une fuite (le signe indique de quel côté elle est)."""
    a = np.asarray(mic1, dtype="float64"); b = np.asarray(mic2, dtype="float64")
    n = min(a.size, b.size)
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    corr = np.correlate(a, b, mode="full")
    lag = int(np.argmax(corr)) - (n - 1)
    return lag / fs
