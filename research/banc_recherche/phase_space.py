"""Espace des phases de l'anche à partir de l'**accéléromètre**.

Le portrait « Espace phase 3D » (Position, Vitesse, Accélération) et le portrait
2-DDL (Position vs Vitesse) se reconstruisent depuis l'accélération mesurée
`a(t)` : on intègre une fois → vitesse, deux fois → position. L'intégration se
fait **dans le domaine fréquentiel** avec un passe-haut, qui élimine la dérive
inhérente à l'intégration temporelle (le problème classique de la double
intégration d'un accéléromètre).

Alternative sans capteur dédié : **plongement de Takens** (retards) d'un seul
signal (micro), qui reconstruit un espace des phases topologiquement équivalent.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _integrate_hp(sig, fs, hp_hz):
    """Intègre une fois dans le domaine fréquentiel avec passe-haut à `hp_hz`
    (sans dérive : la composante continue et les très basses fréquences, non
    intégrables proprement, sont coupées)."""
    x = np.asarray(sig, dtype="float64")
    n = x.size
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    w = 2j * np.pi * f
    Y = np.zeros_like(X)
    mask = f >= hp_hz
    Y[mask] = X[mask] / w[mask]      # intégration = division par iω
    return np.fft.irfft(Y, n)


@dataclass
class PhaseSpace:
    t: np.ndarray
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray


def from_acceleration(accel, fs, hp_hz: float = 20.0) -> PhaseSpace:
    """(position, vitesse, accélération) depuis l'accélération mesurée."""
    a = np.asarray(accel, dtype="float64")
    v = _integrate_hp(a, fs, hp_hz)
    x = _integrate_hp(v, fs, hp_hz)
    t = np.arange(a.size) / fs
    return PhaseSpace(t, x, v, a)


def from_position(pos, fs) -> PhaseSpace:
    """(position, vitesse, accélération) depuis une position mesurée (laser)."""
    x = np.asarray(pos, dtype="float64")
    v = np.gradient(x, 1.0 / fs)
    a = np.gradient(v, 1.0 / fs)
    return PhaseSpace(np.arange(x.size) / fs, x, v, a)


def delay_embedding(signal, delay: int, dim: int = 3):
    """Plongement de Takens : reconstruit un espace des phases `dim`-D à partir
    d'un seul signal, par retards de `delay` échantillons. Renvoie (N, dim)."""
    x = np.asarray(signal, dtype="float64")
    n = x.size - (dim - 1) * delay
    if n <= 0:
        raise ValueError("signal trop court pour ce plongement")
    return np.column_stack([x[i * delay: i * delay + n] for i in range(dim)])


def suggest_delay(signal, fs, max_lag_s: float = 0.05) -> int:
    """Retard conseillé pour le plongement : premier zéro de l'autocorrélation."""
    x = np.asarray(signal, dtype="float64") - np.mean(signal)
    maxlag = int(max_lag_s * fs)
    ac = np.correlate(x, x, mode="full")[x.size - 1: x.size - 1 + maxlag]
    ac = ac / (ac[0] or 1.0)
    below = np.where(ac <= 0)[0]
    return int(below[0]) if below.size else max(1, maxlag // 4)
