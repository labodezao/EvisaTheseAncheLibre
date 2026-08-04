"""Détection de fuites par **décroissance de pression**.

On pressurise, on ferme la vanne et on coupe le soufflet (commande firmware
`LEAKTEST`), puis on enregistre la pression qui retombe. Une fuite laminaire
donne une décroissance exponentielle `p(t) = p₀·e^{−t/τ}` : le temps
caractéristique `τ` mesure l'étanchéité (τ grand = étanche). Si le volume `V`
est connu, la **conductance de fuite** vaut `G ≈ V/τ` (m³/s par unité de rapport
de pression).

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
