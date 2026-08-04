"""Amortissement et facteur de qualité **Q** par décroissance (ring-down).

Après une excitation EM coupée brutalement, l'anche décroît en `e^{-α t}`. On
estime la fréquence dominante (FFT), puis l'enveloppe analytique (Hilbert via
FFT, numpy seul), et on ajuste la pente de `ln(enveloppe)` sur la partie qui
décroît → taux d'amortissement `α`, amortissement réduit `ζ` et `Q = ω₀/(2α)`.

Couvre « Stored energy / Dissipation », « facteur Q », « amortissement matériau ».
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RingdownResult:
    freq_hz: float       # fréquence dominante
    alpha: float         # taux de décroissance d'amplitude (1/s), env ~ e^{-α t}
    zeta: float          # amortissement réduit ζ = α / ω₀
    q: float             # facteur de qualité Q = ω₀ / (2α) = 1/(2ζ)


def analytic_envelope(sig: np.ndarray) -> np.ndarray:
    """Enveloppe = |signal analytique| via transformée de Hilbert (FFT, numpy)."""
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


def dominant_freq(sig: np.ndarray, fs: float) -> float:
    x = np.asarray(sig, dtype="float64")
    X = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    f = np.fft.rfftfreq(x.size, 1.0 / fs)
    return float(f[np.argmax(X)])


def estimate(sig: np.ndarray, fs: float, fit_lo: float = 0.1,
             fit_hi: float = 0.9) -> RingdownResult:
    """Estime f₀, α, ζ, Q sur la fenêtre `[fit_lo, fit_hi]` (fractions du signal)
    après le pic d'enveloppe (portion en décroissance).
    """
    sig = np.asarray(sig, dtype="float64")
    f0 = dominant_freq(sig, fs)
    env = analytic_envelope(sig)
    peak = int(np.argmax(env))
    tail = env[peak:]
    if tail.size < 8:
        return RingdownResult(f0, float("nan"), float("nan"), float("nan"))
    lo = int(fit_lo * tail.size)
    hi = int(fit_hi * tail.size)
    seg = tail[lo:hi]
    seg = np.where(seg <= 0, 1e-12, seg)
    t = np.arange(lo, hi) / fs
    # ln(env) ≈ ln(A0) − α t  → régression linéaire.
    A = np.vstack([t, np.ones_like(t)]).T
    slope, _ = np.linalg.lstsq(A, np.log(seg), rcond=None)[0]
    alpha = float(-slope)
    w0 = 2.0 * np.pi * f0
    zeta = alpha / w0 if w0 else float("nan")
    q = w0 / (2.0 * alpha) if alpha > 0 else float("inf")
    return RingdownResult(f0, alpha, zeta, q)
