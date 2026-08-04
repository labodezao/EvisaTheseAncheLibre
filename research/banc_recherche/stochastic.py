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


def analytic_signal(sig: np.ndarray) -> np.ndarray:
    """Signal analytique complexe z(t) = x + i·H[x] (Hilbert via FFT, numpy)."""
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
    return np.fft.ifft(X * h)


# ---- Fit direct de Stuart-Landau (coefficient de Landau complexe) ----------
@dataclass
class StuartLandau:
    mu: float            # taux de croissance linéaire Re(λ)  (≈ 0 sur cycle limite)
    omega: float         # pulsation Im(λ)  (≈ 2π f₀)
    a: float             # partie réelle du coefficient de Landau (saturation d'amplitude)
    b: float             # partie imaginaire (glissement de fréquence dépendant de l'amplitude)
    r_limit: float       # amplitude du cycle limite √(μ/a) si μ,a > 0


def fit_complex_amplitude(z: np.ndarray, dt: float) -> StuartLandau:
    """Ajuste la forme normale de Stuart-Landau sur l'amplitude complexe `z(t)` :

        dz/dt = (μ + iω)·z − (a + ib)·|z|²·z

    par régression linéaire complexe. Le **coefficient de Landau** g = a + ib
    donne la saturation (a) et le glissement de fréquence avec l'amplitude (b) —
    c'est ce dernier qui explique le « frequency pulling » de l'anche.
    """
    z = np.asarray(z, dtype="complex128")
    dz = (z[1:] - z[:-1]) / dt
    zc = z[:-1]
    X = np.column_stack([zc, zc * np.abs(zc) ** 2])
    coef, *_ = np.linalg.lstsq(X, dz, rcond=None)
    c1, c2 = coef
    mu, omega = float(c1.real), float(c1.imag)
    a, b = float(-c2.real), float(-c2.imag)
    r = float(np.sqrt(mu / a)) if (a > 0 and mu > 0) else float("nan")
    return StuartLandau(mu, omega, a, b, r)


def stuart_landau_fit(signal, fs: float) -> StuartLandau:
    """Fit de Stuart-Landau depuis un signal réel : passe par le signal
    analytique (amplitude + phase) puis `fit_complex_amplitude`."""
    z = analytic_signal(signal)
    return fit_complex_amplitude(z, 1.0 / fs)


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


# ---- Résonance cohérente (SNR maximal à bruit optimal) ---------------------
def coherence_measure(signal, fs: float = 1.0) -> float:
    """Cohérence = **temps de corrélation** normalisé Σ C(τ)² (C = autocorrélation
    normalisée). Une oscillation régulière garde une autocorrélation persistante
    (valeur élevée) ; un signal désordonné la perd vite (valeur faible). Robuste
    au bruit (contrairement au facteur Q d'un pic, qu'un pic de bruit fausse)."""
    x = np.asarray(signal, dtype="float64")
    x = x - x.mean()
    n = x.size
    F = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(np.abs(F) ** 2)[:n]
    if ac[0] <= 0:
        return 0.0
    ac = ac / ac[0]
    return float(np.sum(ac ** 2))


# Alias historique
spectral_coherence = coherence_measure


@dataclass
class CoherenceResonance:
    noise: np.ndarray
    coherence: np.ndarray
    optimal_noise: float
    max_coherence: float


def coherence_resonance(noise_levels, series_list, fs: float) -> CoherenceResonance:
    """Balaye l'intensité de bruit et cherche le **maximum de cohérence** (le
    propre de la résonance cohérente : un bruit intermédiaire rend l'oscillation
    la plus régulière). `series_list` : une série par niveau de bruit."""
    noise = np.asarray(noise_levels, dtype="float64")
    coh = np.array([coherence_measure(s, fs) for s in series_list])
    k = int(np.nanargmax(coh))
    return CoherenceResonance(noise, coh, float(noise[k]), float(coh[k]))


# ---- Temps de résidence / échappement de Kramers ---------------------------
def residence_times(state, dt: float):
    """Durées de séjour dans chaque état d'une série binaire (0 = muet, 1 = sonne).

    Renvoie {0: [durées], 1: [durées]} en secondes. Près d'un seuil sous-critique,
    le bruit fait sauter entre les deux états (bistabilité)."""
    s = (np.asarray(state) > 0).astype(int)
    out = {0: [], 1: []}
    if s.size == 0:
        return out
    start = 0
    for i in range(1, s.size):
        if s[i] != s[start]:
            out[s[start]].append((i - start) * dt)
            start = i
    out[s[start]].append((s.size - start) * dt)
    return out


def kramers_rate(barrier_dU: float, curv_min: float, curv_barrier: float,
                 D: float) -> float:
    """Taux d'échappement de Kramers (régime suramorti) :

        r = (1/2π)·√(U''(min)·|U''(barrière)|)·exp(−ΔU / D)

    `barrier_dU` = hauteur de barrière ΔU, `D` = intensité du bruit (diffusion)."""
    if D <= 0 or curv_min <= 0 or curv_barrier <= 0:
        return float("nan")
    return (np.sqrt(curv_min * curv_barrier) / (2.0 * np.pi)) * np.exp(-barrier_dU / D)


def _curvature(x, phi, i):
    """Courbure locale U''(x_i) par différence finie centrée."""
    if i <= 0 or i >= len(x) - 1:
        return float("nan")
    h1, h2 = x[i] - x[i - 1], x[i + 1] - x[i]
    return float(2 * (phi[i - 1] / (h1 * (h1 + h2)) - phi[i] / (h1 * h2)
                      + phi[i + 1] / (h2 * (h1 + h2))))


def kramers_from_potential(x, phi, D: float, from_left: bool = True):
    """Taux de Kramers depuis un potentiel double-puits échantillonné : trouve
    le puits de départ, la barrière et calcule ΔU + courbures → `kramers_rate`."""
    x = np.asarray(x, dtype="float64"); phi = np.asarray(phi, dtype="float64")
    mins = potential_minima(x, phi)
    if len(mins) < 2:
        return float("nan")
    left, right = mins[0], mins[-1]
    barrier = left + int(np.argmax(phi[left:right + 1]))
    start = left if from_left else right
    dU = phi[barrier] - phi[start]
    cv_min = _curvature(x, phi, start)
    cv_bar = abs(_curvature(x, phi, barrier))
    return kramers_rate(dU, cv_min, cv_bar, D)
