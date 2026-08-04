"""Rapports signal/bruit de Taguchi (robustesse) — pour un DOE d'anches où l'on
veut une réponse stable malgré les variations (matériau, montage, jeu).

Trois objectifs classiques :
- **plus grand = mieux** : S/N = −10·log₁₀( moyenne(1/y²) )
- **plus petit = mieux** : S/N = −10·log₁₀( moyenne(y²) )
- **nominal = mieux**   : S/N = 10·log₁₀( ȳ² / s² )
"""
from __future__ import annotations

import numpy as np


def sn_larger(y) -> float:
    y = np.asarray(y, dtype="float64")
    return float(-10.0 * np.log10(np.mean(1.0 / y ** 2)))


def sn_smaller(y) -> float:
    y = np.asarray(y, dtype="float64")
    return float(-10.0 * np.log10(np.mean(y ** 2)))


def sn_nominal(y) -> float:
    y = np.asarray(y, dtype="float64")
    m, v = y.mean(), y.var(ddof=1)
    return float(10.0 * np.log10(m ** 2 / v)) if v > 0 else float("inf")


def sn_ratio(y, kind: str = "nominal") -> float:
    return {"larger": sn_larger, "smaller": sn_smaller,
            "nominal": sn_nominal}[kind](y)
