"""Analyse modale d'une anche **multi-tronçon** (Euler-Bernoulli encastré-libre).

Port de `matkm`/`km` (MATLAB/sympy du dossier Drive « anches models ») : l'anche
est découpée en tronçons de géométrie propre (longueur, densité, largeur,
épaisseur, module d'Young). On projette sur les déformées modales du cantilever
uniforme φ_i, on assemble les matrices de masse `M` et de raideur `K` par
intégration des φ_i (masse) et φ_i″ (raideur, ∝ E·b·h³/12) sur chaque tronçon,
puis on résout le problème aux valeurs propres généralisé `K x = ω² M x`.

Prédit les **fréquences propres** — à comparer à la FRF mesurée (`frf.py`) et à
`material.youngs_modulus`. Colonnes d'un tronçon : `[longueur, densité, largeur,
épaisseur, E]`.
"""
from __future__ import annotations

import numpy as np

# Compat numpy 1.x/2.x (`trapz` renommé `trapezoid`).
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

# Racines caractéristiques encastré-libre (β_n·L) et σ_n associés.
BETA_L = (1.87510407, 4.69409113, 7.85475744, 10.99554073, 14.13716839)
SIGMA = (0.7341, 1.0185, 0.9992, 1.0, 1.0)


def bl_sigma(n: int):
    """(β_n·L, σ_n) du mode `n` (1-indexé) ; au-delà de 5, asymptotique."""
    if 1 <= n <= 5:
        return BETA_L[n - 1], SIGMA[n - 1]
    return (2 * n - 1) * np.pi / 2, 1.0


def _phi(k, sigma, x):
    """Déformée modale φ(x) du cantilever (k = β/L)."""
    return (np.cosh(k * x) - np.cos(k * x)
            - sigma * (np.sinh(k * x) - np.sin(k * x)))


def _phi2(k, sigma, x):
    """Dérivée seconde φ″(x) (analytique)."""
    return k ** 2 * (np.cosh(k * x) + np.cos(k * x)
                     - sigma * (np.sinh(k * x) + np.sin(k * x)))


def assemble(sections, n_modes: int = 2, n_quad: int = 400):
    """Assemble (M, K) sur `n_modes` déformées modales du cantilever.

    `sections` : lignes `[longueur, densité, largeur, épaisseur, E]`.
    """
    sec = np.asarray(sections, dtype="float64")
    if sec.ndim == 1:
        sec = sec[None, :]
    L = float(sec[:, 0].sum())
    edges = np.concatenate([[0.0], np.cumsum(sec[:, 0])])
    ks = [bl_sigma(i)[0] / L for i in range(1, n_modes + 1)]
    sg = [bl_sigma(i)[1] for i in range(1, n_modes + 1)]

    M = np.zeros((n_modes, n_modes))
    K = np.zeros((n_modes, n_modes))
    for s in range(sec.shape[0]):
        rho, b, h, E = sec[s, 1], sec[s, 2], sec[s, 3], sec[s, 4]
        x = np.linspace(edges[s], edges[s + 1], n_quad)
        EI = E * b * h ** 3 / 12.0
        rhoA = rho * b * h
        for i in range(n_modes):
            pi, pi2 = _phi(ks[i], sg[i], x), _phi2(ks[i], sg[i], x)
            for j in range(n_modes):
                pj, pj2 = _phi(ks[j], sg[j], x), _phi2(ks[j], sg[j], x)
                M[i, j] += rhoA * _trapz(pi * pj, x)
                K[i, j] += EI * _trapz(pi2 * pj2, x)
    return M, K


def natural_frequencies(sections, n_modes: int = 2):
    """Fréquences propres (Hz) de l'anche multi-tronçon."""
    from scipy.linalg import eigh
    M, K = assemble(sections, n_modes)
    w2 = eigh(K, M, eigvals_only=True)
    w2 = np.clip(w2, 0, None)
    return np.sqrt(w2) / (2.0 * np.pi)


def natural_frequencies_np(sections, n_modes: int = 2):
    """Idem sans scipy : résout `M⁻¹K` (M définie positive)."""
    M, K = assemble(sections, n_modes)
    w2 = np.linalg.eigvals(np.linalg.solve(M, K))
    w2 = np.sort(np.real(w2))
    w2 = np.clip(w2, 0, None)
    return np.sqrt(w2) / (2.0 * np.pi)
