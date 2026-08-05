"""Générateurs de plans d'expériences (façon Minitab « Create Design »).

Renvoie des matrices de runs en **unités codées** (±1, plus 0 et ±α pour les
plans de surface de réponse). Facteurs : nombre `k`.
"""
from __future__ import annotations

from itertools import product

import numpy as np


def full_factorial(levels):
    """Plan factoriel complet. `levels` : liste (par facteur) de niveaux, ou un
    entier k pour un plan 2^k en ±1."""
    if isinstance(levels, int):
        levels = [(-1, 1)] * levels
    return np.array(list(product(*levels)), dtype="float64")


def two_level(k: int):
    """Plan factoriel complet 2^k en ±1."""
    return full_factorial(k)


def fractional_factorial(k_base: int, generators: dict):
    """Plan fractionnaire 2^(k−p). `k_base` facteurs de base (complet 2^k_base) ;
    `generators` = {index_facteur_ajouté: (indices de base à multiplier)}.

    Ex. 2^(4−1) avec D = A·B·C : fractional_factorial(3, {3: (0, 1, 2)}).
    """
    base = two_level(k_base)
    cols = [base[:, i] for i in range(k_base)]
    for idx in sorted(generators):
        prod = np.ones(base.shape[0])
        for i in generators[idx]:
            prod = prod * base[:, i]
        cols.insert(idx, prod)
    return np.column_stack(cols)


# Lignes génératrices de Plackett-Burman (premier vecteur cyclique).
_PB = {
    12: "+-+---+++-+",
    20: "+--++++-+-+-++--++-",
    8: "+++-+--",
}


def plackett_burman(n: int):
    """Plan de Plackett-Burman à `n` runs (n ∈ {8,12,20}) ; renvoie n−1 facteurs."""
    if n not in _PB:
        raise ValueError("n doit valoir 8, 12 ou 20")
    row = [1 if ch == "+" else -1 for ch in _PB[n]]
    m = len(row)
    rows = []
    for i in range(m):
        rows.append(row[-i:] + row[:-i] if i else list(row))
    rows.append([-1] * m)                     # dernière ligne : tous −1
    return np.array(rows, dtype="float64")


def central_composite(k: int, alpha: str | float = "rotatable", n_center: int = 4):
    """Plan composite centré (CCD) : factoriel 2^k + points axiaux ±α + centres."""
    fac = two_level(k)
    if alpha == "rotatable":
        a = fac.shape[0] ** 0.25
    elif alpha == "face":
        a = 1.0
    else:
        a = float(alpha)
    axial = []
    for i in range(k):
        for s in (-a, a):
            row = [0.0] * k
            row[i] = s
            axial.append(row)
    center = [[0.0] * k] * n_center
    return np.vstack([fac, np.array(axial), np.array(center)])


def box_behnken(k: int, n_center: int = 3):
    """Plan de Box-Behnken pour k ≥ 3 : paires de facteurs à ±1, les autres à 0."""
    if k < 3:
        raise ValueError("Box-Behnken nécessite k ≥ 3")
    from itertools import combinations
    rows = []
    for i, j in combinations(range(k), 2):
        for si in (-1, 1):
            for sj in (-1, 1):
                row = [0.0] * k
                row[i], row[j] = si, sj
                rows.append(row)
    rows += [[0.0] * k] * n_center
    return np.array(rows, dtype="float64")


def to_uncoded(coded: np.ndarray, lows, highs):
    """Décode ±1 → unités physiques via (low, high) par facteur."""
    lows, highs = np.asarray(lows, float), np.asarray(highs, float)
    mid = 0.5 * (lows + highs)
    half = 0.5 * (highs - lows)
    return mid + coded * half
