"""Optimiseur de réponses par **désirabilité** (façon Minitab « Response
Optimizer »).

Chaque réponse est convertie en désirabilité d ∈ [0, 1] (maximiser / minimiser /
cible) ; la désirabilité **composite** est la moyenne géométrique. On cherche le
réglage des facteurs qui la maximise sur une grille (ou aléatoire).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np


def d_max(y, low, high, weight=1.0):
    """Plus c'est grand, mieux c'est : 0 sous `low`, 1 au-dessus de `high`."""
    if y <= low:
        return 0.0
    if y >= high:
        return 1.0
    return ((y - low) / (high - low)) ** weight


def d_min(y, low, high, weight=1.0):
    """Plus c'est petit, mieux c'est."""
    if y <= low:
        return 1.0
    if y >= high:
        return 0.0
    return ((high - y) / (high - low)) ** weight


def d_target(y, low, target, high, w_lo=1.0, w_hi=1.0):
    """Cible : 1 à `target`, décroît vers `low` et `high`."""
    if y == target:
        return 1.0
    if low < y < target:
        return ((y - low) / (target - low)) ** w_lo
    if target < y < high:
        return ((high - y) / (high - target)) ** w_hi
    return 0.0


@dataclass
class Goal:
    """Objectif sur une réponse : kind ∈ {'max','min','target'}."""
    predict: object            # callable(values_dict) -> réponse prédite
    kind: str
    low: float
    high: float
    target: float = 0.0
    weight: float = 1.0

    def desirability(self, values):
        y = self.predict(values)
        if self.kind == "max":
            return d_max(y, self.low, self.high, self.weight)
        if self.kind == "min":
            return d_min(y, self.low, self.high, self.weight)
        return d_target(y, self.low, self.target, self.high, self.weight, self.weight)


@dataclass
class OptimResult:
    best: dict                 # réglage optimal des facteurs
    composite: float           # désirabilité composite D
    individual: list           # d de chaque réponse


def optimize(goals, bounds: dict, grid: int = 11) -> OptimResult:
    """Maximise la désirabilité composite sur une grille régulière des facteurs.

    `goals` : liste de `Goal` (mêmes facteurs). `bounds` : {facteur: (min, max)}.
    """
    factors = list(bounds.keys())
    axes = [np.linspace(bounds[f][0], bounds[f][1], grid) for f in factors]
    best_D, best_vals = -1.0, None
    for combo in product(*axes):
        vals = dict(zip(factors, combo))
        ds = [g.desirability(vals) for g in goals]
        D = float(np.prod(ds)) ** (1.0 / len(ds)) if ds else 0.0
        if D > best_D:
            best_D, best_vals, best_ind = D, vals, ds
    return OptimResult(best_vals, best_D, best_ind)
