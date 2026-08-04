"""Physique **stochastique** des oscillateurs non linéaires appliquée aux anches.

Reconstruction de la dynamique de Langevin à partir de séries temporelles
(approche Friedrich-Peinke), potentiel effectif, signaux précurseurs de
bifurcation (ralentissement critique), et statistiques de seuil stochastique.

Modèle : `dx = D₁(x) dt + √(2 D₂(x)) dW`. Le **drift** `D₁` (force
déterministe) s'annule aux points fixes ; le **potentiel effectif** en révèle la
stabilité (un puits = monostable, deux puits = bistable → bifurcation).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class KramersMoyal:
    x: np.ndarray        # centres des classes (bins)
    drift: np.ndarray    # D₁(x)
    diffusion: np.ndarray  # D₂(x)
    counts: np.ndarray


def kramers_moyal(series, dt: float, bins: int = 25, x_range=None) -> KramersMoyal:
    """Coefficients de Kramers-Moyal D₁, D₂ estimés par moments conditionnels.

    D₁(x) = ⟨Δx | x⟩ / dt ,  D₂(x) = ⟨Δx² | x⟩ / (2 dt), classés sur x.
    """
    x = np.asarray(series, dtype="float64")
    dx = np.diff(x)
    xc = x[:-1]
    lo, hi = (np.min(xc), np.max(xc)) if x_range is None else x_range
    edges = np.linspace(lo, hi, bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(xc, edges) - 1, 0, bins - 1)
    drift = np.full(bins, np.nan)
    diff = np.full(bins, np.nan)
    counts = np.zeros(bins, dtype=int)
    for b in range(bins):
        m = idx == b
        counts[b] = int(m.sum())
        if counts[b] > 1:
            drift[b] = dx[m].mean() / dt
            diff[b] = (dx[m] ** 2).mean() / (2.0 * dt)
    return KramersMoyal(centers, drift, diff, counts)


def potential_from_drift(km: KramersMoyal):
    """Potentiel effectif Φ(x) = −∫ D₁/D₂ dx (Kramers). Minima = états stables ;
    deux minima = bistabilité (signature d'une bifurcation sous-critique)."""
    good = np.isfinite(km.drift) & np.isfinite(km.diffusion) & (km.diffusion > 0)
    x = km.x[good]
    ratio = km.drift[good] / km.diffusion[good]
    if x.size < 2:
        return x, np.zeros_like(x)
    phi = -np.concatenate([[0.0], np.cumsum(0.5 * (ratio[1:] + ratio[:-1]) * np.diff(x))])
    return x, phi - np.min(phi)


def potential_from_pdf(series, bins: int = 50):
    """Potentiel effectif depuis la densité stationnaire : Φ(x) = −ln p(x)."""
    x = np.asarray(series, dtype="float64")
    hist, edges = np.histogram(x, bins=bins, density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])
    good = hist > 0
    phi = -np.log(hist[good])
    return centers[good], phi - np.min(phi)


def potential_minima(x, phi, prominence_frac=0.02):
    """Indices des minima locaux du potentiel (états stables)."""
    phi = np.asarray(phi)
    span = (np.max(phi) - np.min(phi)) or 1.0
    mins = []
    for i in range(1, len(phi) - 1):
        if phi[i] < phi[i - 1] and phi[i] <= phi[i + 1]:
            # profondeur minimale pour éviter le bruit
            left = np.max(phi[:i]) - phi[i]
            right = np.max(phi[i:]) - phi[i]
            if min(left, right) > prominence_frac * span:
                mins.append(i)
    return mins


# ---- Signaux précurseurs de bifurcation (ralentissement critique) ----------
@dataclass
class EarlyWarning:
    param: np.ndarray
    variance: np.ndarray
    autocorr1: np.ndarray    # autocorrélation à retard 1 (AR(1))
    skewness: np.ndarray


def _ar1(x):
    x = np.asarray(x, dtype="float64")
    x = x - x.mean()
    denom = float((x * x).sum())
    return float((x[:-1] * x[1:]).sum() / denom) if denom > 0 else float("nan")


def _skew(x):
    x = np.asarray(x, dtype="float64")
    s = x.std()
    return float((((x - x.mean()) / s) ** 3).mean()) if s > 0 else float("nan")


def early_warning(param_values, series_list) -> EarlyWarning:
    """Indicateurs de ralentissement critique le long d'une rampe : à mesure
    qu'on approche le seuil, **variance et autocorrélation augmentent**.

    `series_list` : une série temporelle (fenêtre) par valeur du paramètre.
    """
    param = np.asarray(param_values, dtype="float64")
    var = np.array([np.var(s) for s in series_list])
    ac1 = np.array([_ar1(s) for s in series_list])
    sk = np.array([_skew(s) for s in series_list])
    return EarlyWarning(param, var, ac1, sk)


def kendall_tau(x, y) -> float:
    """Tau de Kendall (tendance monotone) — score de précurseur (proche de +1 =
    indicateur croissant vers le seuil)."""
    x = np.asarray(x); y = np.asarray(y)
    n = len(x)
    c = d = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(x[j] - x[i]) * np.sign(y[j] - y[i])
            if s > 0:
                c += 1
            elif s < 0:
                d += 1
    tot = c + d
    return (c - d) / tot if tot else float("nan")


# ---- Seuil de bifurcation stochastique -------------------------------------
@dataclass
class ThresholdStats:
    mu_on_mean: float
    mu_on_std: float
    mu_off_mean: float
    mu_off_std: float
    hysteresis_mean: float


def threshold_stats(mu_on_samples, mu_off_samples) -> ThresholdStats:
    """Statistiques du seuil sur des rampes répétées : le bruit rend le point de
    bifurcation **distribué** (moyenne ± écart-type), pas net."""
    on = np.asarray(mu_on_samples, dtype="float64")
    off = np.asarray(mu_off_samples, dtype="float64")
    return ThresholdStats(
        float(np.nanmean(on)), float(np.nanstd(on)),
        float(np.nanmean(off)), float(np.nanstd(off)),
        float(np.nanmean(on) - np.nanmean(off)))
